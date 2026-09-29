"""Bounded, read-only SQLite reference packs beside the household catalog.

Older owner-installed formats remain readable. Public format-5 bundles require
a publisher signature before their bounded database validation.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sqlite3
import unicodedata
import uuid
import zipfile
from pathlib import Path

from metadata import normalize_title, timestamp
from release_auth import verify_signature, manifest_bytes
from file_safety import reject_links, checked_copy
from metadata_pack import LocalMetadataPacks
from catalog_details import clean_facts
from metapack_identity import (alias_keys, pack_name, validate_alias_evidence,
                              validate_identity_policy, validate_local_record,
                              validate_local_provenance, pack_identifier_allowed, native_record_id)


def public_distribution():
    release=Path(__file__).with_name('RELEASE.json')
    if not release.is_file():return False
    return json.loads(release.read_text()).get('channel') in ('beta','release-candidate','release')


PACK_ID = re.compile(r'[a-z][a-z0-9-]{0,63}\Z')
RECORD_ID = re.compile(r'[A-Za-z0-9:._-]{1,100}\Z')
MAX_BUNDLE_BYTES = 64 * 1024 * 1024
MAX_DATABASE_BYTES = 256 * 1024 * 1024
MAX_RECORDS = 250000
PACK_KINDS = {'movie-work-candidates': 'movie', 'tv-work-candidates': 'tv',
              'music-work-candidates': 'music', 'book-work-candidates': 'book',
              'comic-work-candidates': 'comic', 'game-work-candidates': 'game'}


def _fold_title(value):
    return ''.join(character for character in unicodedata.normalize('NFKD', value.casefold())
                   if character.isalnum() and not unicodedata.combining(character))


def _within_edits(left, right, maximum):
    """Bounded title spelling check; candidates are always left for review."""
    if abs(len(left) - len(right)) > maximum:
        return None
    previous = list(range(len(right) + 1))
    for index, character in enumerate(left, 1):
        current = [index]
        for column, other in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[column] + 1,
                               previous[column - 1] + (character != other)))
        if min(current) > maximum:
            return None
        previous = current
    return previous[-1] if previous[-1] <= maximum else None


def _db(path):
    connection = sqlite3.connect(path.resolve().as_uri() + '?mode=ro&immutable=1', uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA query_only=ON')
    connection.execute('PRAGMA trusted_schema=OFF')
    return connection


def _manifest(value):
    if not isinstance(value, dict):
        raise ValueError('The pack manifest is invalid.')
    pack_id, version = value.get('id'), value.get('version')
    if (value.get('format') not in (2, 3, 4, 5) or not isinstance(pack_id, str) or not PACK_ID.fullmatch(pack_id)
            or not isinstance(version, str) or not re.fullmatch(r'[1-9][0-9]{0,9}', version)
            or PACK_KINDS.get(pack_id) != value.get('kind') or value.get('distribution') not in ('private-review','public')
            or value.get('license') not in ({'CC0-1.0'} if pack_id == 'music-work-candidates' else {'owner-private-review','LicenseRef-Blank-Box-Personal-Use'})
            or not isinstance(value.get('displayName'), str) or not 1 <= len(value['displayName']) <= 100
            or not isinstance(value.get('source'), str) or not value['source'].strip()
            or not isinstance(value.get('sourceVersion'), str) or not value['sourceVersion'].strip()
            or not isinstance(value.get('sourceSnapshot'), str) or not value['sourceSnapshot'].strip()
            or not isinstance(value.get('sourceIndexSha256'), str)
            or not re.fullmatch(r'[0-9a-f]{64}', value['sourceIndexSha256'])
            or not isinstance(value.get('databaseSha256'), str)
            or not re.fullmatch(r'[0-9a-f]{64}', value['databaseSha256'])
            or type(value.get('databaseBytes')) is not int or not 1 <= value['databaseBytes'] <= MAX_DATABASE_BYTES
            or type(value.get('recordCount')) is not int or not 1 <= value['recordCount'] <= MAX_RECORDS):
        raise ValueError('The pack format, scope, or checksum is invalid.')
    if value['format'] == 3 and (type(value.get('releaseCount')) is not int or not 1 <= value['releaseCount'] <= MAX_RECORDS):
        raise ValueError('The pack release count is invalid.')
    if value['format'] == 4 and (type(value.get('releaseCount')) is not int or not 0 <= value['releaseCount'] <= MAX_RECORDS):
        raise ValueError('The enriched pack release count is invalid.')
    if value['format']==5 and (type(value.get('aliasCount')) is not int or not 0<=value['aliasCount']<=MAX_RECORDS or not isinstance(value.get('description'),str) or not 1<=len(value['description'])<=500 or type(value.get('releaseCount')) is not int or not 0<=value['releaseCount']<=MAX_RECORDS):
        raise ValueError('The offline metapack description or counts are invalid.')
    if value.get('distribution') == 'public':
        if value.get('format') != 5 or value.get('minimumReader') != 5:
            raise ValueError('This public metapack requires a different reader.')
        verify_signature(manifest_bytes(value), value.get('publisherSignature', {}))
    validate_identity_policy(value)
    return value


def _validate_database(path, manifest):
    local_identity=validate_identity_policy(manifest)
    if path.is_symlink() or not path.is_file() or path.stat().st_size != manifest['databaseBytes']:
        raise ValueError('The pack database size does not match its manifest.')
    with _db(path) as db:
        if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise ValueError('The pack database is damaged.')
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if tables - ({'works','releases','work_details','record_identifiers','pack_meta','work_search',
                     'work_search_data','work_search_idx','work_search_docsize','work_search_config'} | ({'record_aliases'} if manifest['format']==5 else set())):
            raise ValueError('The pack contains unsupported hidden tables.')
        if not {'works', 'work_search', 'pack_meta'}.issubset(tables):
            raise ValueError('The pack search index is missing.')
        if manifest['format'] == 3 or manifest['format'] in (4,5) and manifest['releaseCount']:
            if 'releases' not in tables or db.execute('SELECT count(*) FROM releases').fetchone()[0] != manifest['releaseCount']:
                raise ValueError('The pack release table or count is invalid.')
            required = {'record_id', 'work_record_id', 'title', 'year', 'format', 'edition', 'season',
                        'barcode_namespace', 'barcode', 'source_key', 'review_status'}
            if not required.issubset({row[1] for row in db.execute('PRAGMA table_info(releases)')}):
                raise ValueError('The pack release fields are invalid.')
            if db.execute("SELECT count(*) FROM releases WHERE review_status!='needs_review' OR length(title)<1 OR length(title)>250 OR length(format)<1 OR length(format)>120 OR length(record_id)<1 OR length(record_id)>100 OR length(source_key)<1 OR length(source_key)>200 OR barcode_namespace NOT IN ('isbn','upc-ean') OR length(barcode)<1 OR length(barcode)>80 OR year<1800 OR year>2200 OR length(COALESCE(edition,''))>120 OR (season IS NOT NULL AND season NOT IN ('specials','complete-series') AND (season NOT GLOB '[1-9]' AND season NOT GLOB '[1-9][0-9]'))").fetchone()[0]:
                raise ValueError('The pack contains invalid release clues.')
            if db.execute('SELECT count(*) FROM releases r LEFT JOIN works w ON w.record_id=r.work_record_id WHERE w.record_id IS NULL').fetchone()[0]:
                raise ValueError('The pack contains a release without its work.')
            if db.execute('SELECT count(*) FROM releases r JOIN works w ON w.record_id=r.record_id').fetchone()[0]:
                raise ValueError('The pack reuses a work ID for a release.')
            for record in db.execute('SELECT record_id,work_record_id,barcode_namespace,barcode,season FROM releases'):
                if not RECORD_ID.fullmatch(record['record_id']) or not RECORD_ID.fullmatch(record['work_record_id']):
                    raise ValueError('The pack contains an invalid release ID.')
                if record['barcode_namespace'] == 'isbn' and manifest['kind'] != 'book' or record['barcode_namespace'] == 'upc-ean' and manifest['kind'] == 'book':
                    raise ValueError('The pack release identifier does not fit its media type.')
                if record['season'] and manifest['kind'] != 'tv':
                    raise ValueError('Only a TV release can name a season.')
            if local_identity and db.execute("SELECT 1 FROM releases WHERE source_key!='blankbox:'||record_id OR (record_id NOT LIKE 'bbp:%' AND record_id NOT LIKE 'bbp-%') LIMIT 1").fetchone():
                raise ValueError('An offline edition requires a Blank Box source key.')
        if manifest['format'] in (4,5):
            if not {'work_details', 'record_identifiers'}.issubset(tables):
                raise ValueError('The enriched pack facts are missing.')
            if {row[1] for row in db.execute('PRAGMA table_info(work_details)')} != {'record_id', 'fields_json', 'provenance_json'}:
                raise ValueError('The enriched pack factual fields are invalid.')
            if {row[1] for row in db.execute('PRAGMA table_info(record_identifiers)')} != {'record_id', 'namespace', 'value'}:
                raise ValueError('The enriched pack identifier fields are invalid.')
            known = {row[0] for row in db.execute('SELECT record_id FROM works')}
            if 'releases' in tables:
                known.update(row[0] for row in db.execute('SELECT record_id FROM releases'))
            for row in db.execute('SELECT * FROM work_details'):
                try:
                    facts = json.loads(row['fields_json'])
                    provenance = json.loads(row['provenance_json'])
                    if row['record_id'] not in known or len(row['fields_json']) > 65536:
                        raise ValueError('Unlinked or oversized facts.')
                    if clean_facts(facts, strict=True) != facts:
                        raise ValueError('Noncanonical factual values.')
                    if (not isinstance(provenance, dict) or set(provenance) != {'source', 'record'}
                            or not isinstance(provenance['source'], str) or not 1 <= len(provenance['source']) <= 120
                            or not isinstance(provenance['record'], str) or not 1 <= len(provenance['record']) <= 200):
                        raise ValueError('Missing factual provenance.')
                    if local_identity:validate_local_provenance(provenance,row['record_id'])
                except (ValueError, TypeError) as error:
                    raise ValueError('The enriched pack contains invalid facts or provenance.') from error
            for row in db.execute('SELECT * FROM record_identifiers'):
                if local_identity and (not pack_identifier_allowed(row['namespace']) or '://' in row['value']):
                    raise ValueError('Website identifiers are not supported in this offline pack.')
                if (row['record_id'] not in known or not isinstance(row['namespace'], str)
                        or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{0,63}', row['namespace'])
                        or not isinstance(row['value'], str) or not 1 <= len(row['value']) <= 512):
                    raise ValueError('The enriched pack contains an invalid identifier.')
        if manifest['format']==5:
            work_ids={row[0] for row in db.execute('SELECT record_id FROM works')}
            if 'record_aliases' not in tables or {r[1] for r in db.execute('PRAGMA table_info(record_aliases)')}!={'alias_id','canonical_id','evidence_json'}:
                raise ValueError('The offline metapack alias table is invalid.')
            if db.execute('SELECT COUNT(*) FROM record_aliases').fetchone()[0]!=manifest['aliasCount']:
                raise ValueError('The offline metapack alias count is invalid.')
            if db.execute('SELECT COUNT(*) FROM (SELECT canonical_id FROM record_aliases GROUP BY canonical_id HAVING COUNT(*)>128)').fetchone()[0]:
                raise ValueError('Too many aliases for one metadata record.')
            for alias in db.execute('SELECT * FROM record_aliases'):
                if (not RECORD_ID.fullmatch(alias['alias_id']) or not RECORD_ID.fullmatch(alias['canonical_id'])
                        or alias['alias_id'] in known or alias['canonical_id'] not in work_ids):
                    raise ValueError('The offline metapack has a missing, reused or chained alias.')
                evidence=validate_alias_evidence(alias['evidence_json'],alias['alias_id'],clean_facts)
                if local_identity:
                    validate_local_record(evidence['record'])
                    validate_local_provenance(evidence['provenance'],alias['alias_id'])
                    if any(not pack_identifier_allowed(v['namespace']) for v in evidence['identifiers']):
                        raise ValueError('Website identifiers are not supported in offline aliases.')
                if evidence['record'].get('media_type') != ('tv_series' if manifest['kind']=='tv' else manifest['kind']):
                    raise ValueError('The offline metapack alias is for another media type.')
        index_sql = db.execute("SELECT sql FROM sqlite_master WHERE name='work_search'").fetchone()[0] or ''
        if not re.search(r'\bUSING\s+fts5\s*\(', index_sql, re.I) or "content='works'" not in index_sql.lower():
            raise ValueError('The pack search index is not a supported FTS5 index.')
        if db.execute('SELECT count(*) FROM work_search_idx').fetchone()[0] < 1:
            raise ValueError('The pack search index is empty.')
        if db.execute("SELECT count(*) FROM sqlite_master WHERE type IN ('trigger','view')").fetchone()[0]:
            raise ValueError('The pack contains unsupported database objects.')
        meta = dict(db.execute('SELECT key,value FROM pack_meta'))
        expected_format = {2: 'internal-preview-sqlite-1', 3: 'internal-preview-sqlite-2', 4: 'internal-preview-sqlite-3', 5:'offline-metapack-sqlite-1'}[manifest['format']]
        if (meta.get('pack_id') != manifest['id'] or meta.get('pack_format') != expected_format
                or meta.get('builder_snapshot') != manifest['sourceSnapshot']
                or meta.get('distribution') != ('owner-installed-offline' if manifest['format']==5 else 'internal-preview-only')):
            raise ValueError('The pack database does not match its manifest.')
        if db.execute('SELECT count(*) FROM works').fetchone()[0] != manifest['recordCount']:
            raise ValueError('The pack record count does not match its manifest.')
        source_kind = 'tv_series' if manifest['kind'] == 'tv' else manifest['kind']
        if db.execute('SELECT count(*) FROM works WHERE media_type!=?', (source_kind,)).fetchone()[0]:
            raise ValueError('The pack contains the wrong media type.')
        if db.execute("SELECT count(*) FROM works WHERE review_status!='needs_review' OR length(title)<1").fetchone()[0]:
            raise ValueError('The pack contains unsupported candidate records.')
        if db.execute('SELECT count(*) FROM works WHERE length(record_id)>100 OR length(source_key)<1 OR length(source_key)>200 OR length(title)>250 OR year<1800 OR year>2200').fetchone()[0]:
            raise ValueError('The pack contains invalid candidate fields.')
        for (encoded,) in db.execute('SELECT source_ids_json FROM works'):
            try:
                details = json.loads(encoded)
            except (TypeError, ValueError) as error:
                raise ValueError('The pack contains invalid source evidence.') from error
            if manifest['kind'] in ('music', 'book'):
                if not isinstance(details, dict) or not isinstance(details.get('creator'), str) or not 1 <= len(details['creator']) <= 250:
                    raise ValueError('The pack is missing creator evidence.')
        if local_identity:
            for record in db.execute('SELECT record_id,source_key,source_ids_json FROM works'):
                validate_local_record(record)
        db.execute("SELECT w.record_id FROM work_search s JOIN works w ON w.rowid=s.rowid WHERE work_search MATCH 'test' LIMIT 1").fetchall()


class IndexedMetadataPacks:
    def __init__(self, root):
        self.root = reject_links(root)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._verified = {}

    def _entries(self):
        for path in sorted(self.root.glob('*.indexed.json')):
            try:
                if path.is_symlink() or not path.is_file() or path.stat().st_size > 32768:
                    raise ValueError('Invalid pack manifest.')
                manifest = _manifest(json.loads(path.read_text(encoding='utf-8')))
                database = path.with_suffix('').with_suffix('.sqlite')
                if database.is_symlink() or not database.is_file() or database.stat().st_size != manifest['databaseBytes']:
                    raise ValueError('Pack database missing or changed.')
                state = database.stat()
                stamp = (state.st_dev, state.st_ino, state.st_size, state.st_mtime_ns, manifest['databaseSha256'])
                if self._verified.get(database) != stamp:
                    digest = hashlib.sha256()
                    with database.open('rb') as opened:
                        for block in iter(lambda: opened.read(1024 * 1024), b''):
                            digest.update(block)
                    if digest.hexdigest() != manifest['databaseSha256']:
                        raise ValueError('Pack database checksum changed.')
                    self._verified[database] = stamp
                yield manifest, database, None, path
            except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as error:
                yield None, None, str(error), path

    def available(self):
        latest = {}
        for manifest, database, error, _ in self._entries():
            if not error and (manifest['id'] not in latest or int(manifest['version']) > int(latest[manifest['id']][0]['version'])):
                latest[manifest['id']] = (manifest, database)
        return [latest[key] for key in sorted(latest)]

    def list(self):
        return [manifest for manifest, _ in self.available()]

    def errors(self):
        return sorted({pack_id for _, _, error, path in self._entries() if error
                       for pack_id in PACK_KINDS if path.name.startswith(pack_id + '-v')})

    def has(self, pack_id):
        return any(manifest['id'] == pack_id for manifest, _ in self.available())

    def owns(self, pack_id):
        return pack_id in PACK_KINDS and any(
            re.fullmatch(re.escape(pack_id) + r'-v[1-9][0-9]*-[0-9a-f]{12}\.indexed\.json', path.name)
            for path in self.root.glob('*.indexed.json'))

    def _current(self, pack_id):
        return next(((manifest, path) for manifest, path in self.available() if manifest['id'] == pack_id), None)

    def install_bundle(self, payload):
        if not isinstance(payload, bytes) or not 1 <= len(payload) <= MAX_BUNDLE_BYTES:
            raise ValueError('The metadata pack file is too large or empty.')
        try:
            bundle = zipfile.ZipFile(io.BytesIO(payload))
        except (OSError, zipfile.BadZipFile) as error:
            raise ValueError('The metadata pack file is not a valid bundle.') from error
        with bundle:
            if sorted(bundle.namelist()) != ['data.sqlite', 'manifest.json']:
                raise ValueError('The metadata pack bundle has unexpected files.')
            info = bundle.getinfo('data.sqlite')
            if bundle.getinfo('manifest.json').file_size > 32768:
                raise ValueError('The metadata pack manifest is too large.')
            if info.file_size > MAX_DATABASE_BYTES or info.file_size < 1:
                raise ValueError('The metadata pack database is too large.')
            try:
                manifest = _manifest(json.loads(bundle.read('manifest.json')))
                if public_distribution() and manifest.get('distribution')!='public':
                    raise ValueError('This installation requires publisher-signed public metapack imports.')
            except (zipfile.BadZipFile, RuntimeError) as error:
                raise ValueError('The metadata pack manifest is damaged.') from error
            if info.file_size != manifest['databaseBytes']:
                raise ValueError('The metadata pack size does not match its manifest.')
            current = self._current(manifest['id'])
            if current and int(manifest['version']) < int(current[0]['version']):
                raise ValueError('An older metadata pack cannot replace the installed version.')
            if current and manifest['version'] == current[0]['version']:
                if manifest != current[0]:
                    raise ValueError('The installed pack version has different contents or provenance.')
                return current[0]
            staged = self.root / ('.' + uuid.uuid4().hex + '.partial')
            digest = hashlib.sha256()
            size = 0
            staged_created = False
            try:
                with bundle.open('data.sqlite') as incoming, staged.open('xb') as output:
                    staged_created = True
                    for block in iter(lambda: incoming.read(1024 * 1024), b''):
                        size += len(block)
                        if size > MAX_DATABASE_BYTES:
                            raise ValueError('The metadata pack database is too large.')
                        digest.update(block)
                        output.write(block)
                    output.flush()
                    os.fsync(output.fileno())
                if size != manifest['databaseBytes'] or digest.hexdigest() != manifest['databaseSha256']:
                    raise ValueError('The metadata pack checksum did not match.')
                _validate_database(staged, manifest)
                stem = f"{manifest['id']}-v{manifest['version']}-{digest.hexdigest()[:12]}"
                destination = self.root / (stem + '.sqlite')
                notice = self.root / (stem + '.indexed.json')
                if notice.exists():
                    raise ValueError('The metadata pack version already exists.')
                checked_copy(staged, destination, digest.hexdigest())
                part_notice = self.root / ('.' + uuid.uuid4().hex + '.partial')
                notice_created = False
                try:
                    with part_notice.open('x',encoding='utf-8') as stream:
                        notice_created = True
                        stream.write(json.dumps(manifest,sort_keys=True)+'\n');stream.flush();os.fsync(stream.fileno())
                    os.link(part_notice,notice)
                finally:
                    if notice_created:part_notice.unlink(missing_ok=True)
                return manifest
            except (zipfile.BadZipFile, EOFError, RuntimeError) as error:
                raise ValueError('The metadata pack database is damaged.') from error
            finally:
                if staged_created:staged.unlink(missing_ok=True)

    def remove(self, pack_id):
        if not self.owns(pack_id):
            raise ValueError('Metadata pack is not installed.')
        for notice in self.root.glob('*.indexed.json'):
            if not re.fullmatch(re.escape(pack_id) + r'-v[1-9][0-9]*-[0-9a-f]{12}\.indexed\.json', notice.name):
                continue
            path = notice.with_suffix('').with_suffix('.sqlite')
            notice.unlink()
            path.unlink(missing_ok=True)
            self._verified.pop(path, None)

    def _record(self, pack_id, record_id):
        if not isinstance(record_id, str) or not RECORD_ID.fullmatch(record_id):
            raise ValueError('Invalid metadata record ID.')
        current = self._current(pack_id)
        if not current:
            raise ValueError('The metadata pack is unavailable.')
        manifest, path = current
        with _db(path) as db:
            canonical,keys=alias_keys(db,manifest,record_id)
            row = db.execute('SELECT * FROM works WHERE record_id=?', (canonical,)).fetchone()
            if row:
                record=self._record_details(db,manifest,row)
                record['lookup_record_ids']=keys
                record['canonical_record_id']=canonical
                if record_id!=canonical:
                    evidence=json.loads(db.execute('SELECT evidence_json FROM record_aliases WHERE alias_id=?',(record_id,)).fetchone()[0])
                    record['record_id']=record_id
                    record['source_key']=evidence['record']['source_key']
                return manifest,record
            if manifest['format'] == 3 or manifest['format'] in (4,5) and manifest['releaseCount']:
                row = db.execute('SELECT * FROM releases WHERE record_id=?', (record_id,)).fetchone()
                if row:return manifest, self._record_details(db, manifest, row)
            return manifest, None

    @staticmethod
    def _record_details(db, manifest, row):
        record = dict(row)
        if manifest['format'] in (4,5):
            detail = db.execute('SELECT fields_json,provenance_json FROM work_details WHERE record_id=?', (row['record_id'],)).fetchone()
            if detail:
                record['facts'] = json.loads(detail[0])
                record['factProvenance'] = json.loads(detail[1])
            record['identifiers'] = [{'namespace': namespace, 'value': value} for namespace, value in
                                     db.execute('SELECT namespace,value FROM record_identifiers WHERE record_id=? ORDER BY namespace,value', (row['record_id'],))]
        canonical,keys=alias_keys(db,manifest,row['record_id'])
        record['lookup_record_ids']=keys
        record['canonical_record_id']=canonical
        return record

    @staticmethod
    def _candidate_context(manifest,record):
        return {'packName':pack_name(manifest['id']),'packVersion':manifest['version'],
                'lookupIds':[f"pack:{manifest['id']}:{rid}" for rid in record.get('lookup_record_ids',[record['record_id']])]}

    def candidates(self, *, title='', kind=None, year=None, namespace=None, value=None, limit=50):
        if limit <= 0:return []
        if namespace or value:
            if not namespace or not value:return []
            results=[]
            for manifest,path in self.available():
                if kind and manifest['kind'] != kind:continue
                try:
                    with _db(path) as db:
                        if manifest['format'] in (4,5):
                            found = db.execute('SELECT record_id FROM record_identifiers WHERE namespace=? AND value=? LIMIT ?', (namespace,value,max(0,limit-len(results)))).fetchall()
                            seen = set()
                            for identifier, in found:
                                row = db.execute('SELECT * FROM works WHERE record_id=?', (identifier,)).fetchone()
                                if row:
                                    record = self._record_details(db, manifest, row)
                                    results.append({'id': f"pack:{manifest['id']}:{identifier}", 'kind': manifest['kind'], 'level': 'work',
                                                    'work_id': None, 'title': row['title'], 'year': row['year'], 'origin': 'pack:' + manifest['id'],
                                                    'evidence': ['exact identifier'], 'candidateRef': identifier, 'confidence': 'identifier',
                                                    'requiresReview': True, **self._candidate_context(manifest,record), 'identifiers': record.get('identifiers', []), **record.get('facts', {})})
                                elif manifest['releaseCount']:
                                    row = db.execute('SELECT * FROM releases WHERE record_id=?', (identifier,)).fetchone()
                                    if row:results.append(self._release_candidate(manifest,self._record_details(db,manifest,row),'exact identifier'))
                                seen.add(identifier)
                            if manifest['releaseCount'] and namespace in ('isbn', 'upc-ean'):
                                for row in db.execute('SELECT * FROM releases WHERE barcode_namespace=? AND barcode=? LIMIT ?', (namespace,value,max(0,limit-len(results)))):
                                    if row['record_id'] not in seen:
                                        results.append(self._release_candidate(manifest,self._record_details(db,manifest,row),'exact identifier'))
                        elif manifest['format'] == 3 and namespace in ('isbn', 'upc-ean'):
                            for row in db.execute('SELECT * FROM releases WHERE barcode_namespace=? AND barcode=? LIMIT ?', (namespace,value,max(0,limit-len(results)))):
                                results.append(self._release_candidate(manifest,row,'exact identifier'))
                except (sqlite3.Error,OSError,ValueError):continue
                if len(results)>=limit:break
            return results
        tokens = re.findall(r'[^\W_]+', title.casefold())[:12]
        if not tokens:
            return []
        expression = ' '.join('"' + token.replace('"', '') + '"' for token in tokens)
        wanted = normalize_title(title)
        folded = _fold_title(title)
        results = []
        for manifest, path in self.available():
            if kind and manifest['kind'] != kind:
                continue
            try:
                with _db(path) as db:
                    rows = db.execute('''SELECT w.record_id,w.title,w.year,w.source_ids_json FROM work_search s
                                         JOIN works w ON w.rowid=s.rowid
                                         WHERE work_search MATCH ?
                                         ORDER BY (w.title = ? COLLATE NOCASE) DESC,
                                                  (w.year = ?) DESC,
                                                  bm25(work_search) LIMIT 100''',
                                      (expression, title, year)).fetchall()
                    exact_rows = [row for row in rows if normalize_title(row['title']) == wanted]
                    visible = exact_rows if exact_rows else rows[:15]
                    fuzzy = False
                    if not any(_fold_title(row['title']) == folded for row in rows) and len(folded) >= 4:
                        # Existing bundles have a token FTS index. Use short
                        # token prefixes to bound the typo pool without a pack
                        # migration, then verify spelling in memory. No fuzzy
                        # result is ever an automatic identity assertion.
                        pool = {}
                        for token in sorted(set(tokens), key=len, reverse=True)[:3]:
                            if len(token) < 3:
                                continue
                            prefix = token[:4] if len(token) >= 5 else token[:3]
                            for row in db.execute('''SELECT w.record_id,w.title,w.year,w.source_ids_json
                                FROM work_search s JOIN works w ON w.rowid=s.rowid
                                WHERE work_search MATCH ? LIMIT 1000''', (prefix + '*',)):
                                pool[row['record_id']] = row
                        maximum = 1 if len(folded) < 8 else 2
                        ranked = []
                        for row in pool.values():
                            distance = _within_edits(folded, _fold_title(row['title']), maximum)
                            if distance is not None:
                                ranked.append((distance, row['year'] != year if year is not None else False,
                                               row['title'].casefold(), row['record_id'], row))
                        ranked.sort(key=lambda entry: entry[:4])
                        if ranked:
                            visible = [entry[4] for entry in ranked[:15]]
                            fuzzy = True
                    for row in visible:
                        details = json.loads(row['source_ids_json'])
                        creator = details.get('creator') if isinstance(details, dict) else None
                        exact = normalize_title(row['title']) == wanted
                        same_year = year is not None and row['year'] == year
                        reason = ('title formatting' if _fold_title(row['title']) == folded else 'close title spelling') if fuzzy else 'title and year' if exact and same_year else 'exact title' if exact else 'title terms'
                        detail = self._record_details(db,manifest,row)
                        results.append({'id': f"pack:{manifest['id']}:{row['record_id']}", 'kind': manifest['kind'],
                                        'level': 'work', 'work_id': None, 'title': row['title'], 'year': row['year'],
                                        'origin': 'pack:' + manifest['id'], 'evidence': [reason],
                                        'candidateRef': row['record_id'],
                                        **({'creator': creator} if isinstance(creator, str) and creator else {}),
                                        'confidence': 'title-year' if exact and same_year else 'review',
                                        'requiresReview': True, **self._candidate_context(manifest,detail), 'identifiers': detail.get('identifiers', []), **detail.get('facts', {})})
                        if len(results) >= limit:
                            return results
                    if manifest['format'] == 3 or manifest['format'] in (4,5) and manifest['releaseCount']:
                        for row in db.execute('''SELECT r.* FROM releases r JOIN works w ON w.record_id=r.work_record_id
                            JOIN work_search s ON s.rowid=w.rowid WHERE work_search MATCH ? LIMIT 30''',(expression,)):
                            results.append(self._release_candidate(manifest,self._record_details(db,manifest,row),'title terms; release identifier available'))
                            if len(results)>=limit:return results
            except (sqlite3.Error, OSError, ValueError, TypeError):
                continue  # A damaged optional pack never blocks household search.
        return results

    @staticmethod
    def _release_candidate(manifest,row,reason):
        return {'id':f"pack:{manifest['id']}:{row['record_id']}",'kind':manifest['kind'],
                'level':'release','work_id':f"pack:{manifest['id']}:{row['work_record_id']}",
                'title':row['title'],'year':row['year'],'format':row['format'],'edition':row['edition'],
                'season':row['season'],'origin':'pack:'+manifest['id'],'evidence':[reason],
                'candidateRef':row['record_id'],'identifier':{'namespace':row['barcode_namespace'],'value':row['barcode']},
                'confidence':'identifier' if reason=='exact identifier' else 'review','requiresReview':True,
                **IndexedMetadataPacks._candidate_context(manifest,dict(row)),
                **({'catalogDetails': row['facts']['catalogDetails']} if isinstance(row,dict) and row.get('facts',{}).get('catalogDetails') else {}),
                **({'identifiers': row['identifiers']} if isinstance(row,dict) and row.get('identifiers') else {})}

    def materialize(self, db, candidate):
        parts = candidate.split(':', 2) if isinstance(candidate, str) else []
        if len(parts) != 3 or parts[0] != 'pack':
            raise ValueError('Invalid pack candidate.')
        manifest, record = self._record(parts[1], parts[2])
        if not record:
            raise ValueError('The metadata candidate is no longer available.')
        mapping = parts[1] + ':' + record['record_id']
        existing = db.execute("SELECT entity_id FROM metadata_identifiers WHERE namespace='blankbox-pack-record' AND value=? LIMIT 1", (mapping,)).fetchone()
        if not existing and manifest['format']==5:
            mappings=[parts[1]+':'+key for key in record.get('lookup_record_ids',[])]
            if mappings:
                marks=','.join('?' for _ in mappings)
                found=db.execute(f"SELECT DISTINCT entity_id FROM metadata_identifiers WHERE namespace='blankbox-pack-record' AND value IN ({marks})",mappings).fetchall()
                if len(found)==1:existing=found[0]
        if existing:
            self._materialize_details(db, manifest, record, existing['entity_id'])
            return existing['entity_id']
        if 'work_record_id' in record:
            parent_id=self.materialize(db,f"pack:{manifest['id']}:{record['work_record_id']}")
            entity_id='bbm:release:'+str(uuid.uuid4())
            when=timestamp()
            db.execute('INSERT INTO metadata_entities(id,kind,level,work_id,title,title_key,year,origin,created_at,updated_at,format,edition,season) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       (entity_id,manifest['kind'],'release',parent_id,record['title'],normalize_title(record['title']),record['year'],'pack:'+manifest['id'],when,when,record['format'],record['edition'],record['season']))
            source_version=f"{manifest['sourceVersion']}; snapshot={manifest['sourceSnapshot']}; index-sha256={manifest['sourceIndexSha256']}"
            provenance=('pack:'+manifest['id'],record['source_key'],source_version,manifest['license'],when)
            for field in ('title','year','format','edition','season'):
                value=record[field]
                if value is not None and value!='':
                    db.execute('INSERT INTO metadata_field_values VALUES(?,?,?,?,?,?,?,?,?,?)',
                               (entity_id,field,json.dumps(value,ensure_ascii=False),*provenance,0,1))
            for namespace,value in (('blankbox-pack-record',mapping),(record['barcode_namespace'],record['barcode'])):
                db.execute('INSERT INTO metadata_identifiers VALUES(?,?,?,?,?,?,?,?)',
                           (entity_id,namespace,value,*provenance))
            self._materialize_details(db,manifest,record,entity_id)
            return entity_id
        entity_id = 'bbm:work:' + str(uuid.uuid4())
        when = timestamp()
        db.execute('INSERT INTO metadata_entities(id,kind,level,work_id,title,title_key,year,origin,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
                   (entity_id, manifest['kind'], 'work', None, record['title'], normalize_title(record['title']),
                    record['year'], 'pack:' + manifest['id'], when, when))
        source_version = f"{manifest['sourceVersion']}; snapshot={manifest['sourceSnapshot']}; index-sha256={manifest['sourceIndexSha256']}"
        provenance = ('pack:' + manifest['id'], record['source_key'], source_version, manifest['license'], when)
        for field, value in {'title': record['title'], **({'year': record['year']} if record['year'] else {})}.items():
            db.execute('INSERT INTO metadata_field_values VALUES(?,?,?,?,?,?,?,?,?,?)',
                       (entity_id, field, json.dumps(value, ensure_ascii=False), *provenance, 0, 1))
        details = json.loads(record['source_ids_json'])
        creator = details.get('creator') if isinstance(details, dict) else None
        if isinstance(creator, str) and creator and manifest['kind'] in ('music', 'book'):
            field = 'artist' if manifest['kind'] == 'music' else 'author'
            db.execute('INSERT INTO metadata_field_values VALUES(?,?,?,?,?,?,?,?,?,?)',
                       (entity_id, field, json.dumps(creator, ensure_ascii=False), *provenance, 0, 1))
        db.execute('INSERT INTO metadata_identifiers VALUES(?,?,?,?,?,?,?,?)',
                   (entity_id, 'blankbox-pack-record', mapping, *provenance))
        self._materialize_details(db,manifest,record,entity_id)
        return entity_id

    @staticmethod
    def _materialize_details(db, manifest, record, entity_id):
        """Refresh one selected record, retaining its local ID and prior evidence."""
        if manifest['format'] not in (4,5):
            return
        when = timestamp()
        detail = record.get('factProvenance', {'source': manifest['source'], 'record': record['source_key']})
        source_version = f"{manifest['sourceVersion']}; snapshot={manifest['sourceSnapshot']}; index-sha256={manifest['sourceIndexSha256']}"
        # A new pack version is new evidence, so it never overwrites a prior
        # confirmed version's fields or a household owner correction.
        source_version += '; factual-source=' + detail['source']
        source_record = str(detail['record']) + '@pack-v' + manifest['version']
        provenance = ('pack:' + manifest['id'], source_record, source_version, manifest['license'], when)
        if manifest['format']==5:
            for key in record.get('lookup_record_ids',[]):
                db.execute('INSERT OR IGNORE INTO metadata_identifiers VALUES(?,?,?,?,?,?,?,?)',
                           (entity_id,'blankbox-pack-alias',manifest['id']+':'+key,*provenance))
        for field,value in clean_facts(record.get('facts', {}), strict=True).items():
            db.execute('INSERT INTO metadata_field_values VALUES(?,?,?,?,?,?,?,?,?,?) '
                       'ON CONFLICT(entity_id,field,source,source_record_id) DO UPDATE SET value_json=excluded.value_json,source_version=excluded.source_version,imported_at=CASE WHEN metadata_field_values.value_json<>excluded.value_json THEN excluded.imported_at ELSE metadata_field_values.imported_at END',
                       (entity_id,field,json.dumps(value,ensure_ascii=False),*provenance,0,1))
        for identifier in record.get('identifiers', []):
            db.execute('INSERT OR IGNORE INTO metadata_identifiers VALUES(?,?,?,?,?,?,?,?)',
                       (entity_id,identifier['namespace'],identifier['value'],*provenance))


class MetadataPackSet:
    """Keep the installed format-1 CD proof and indexed packs behind one API."""
    def __init__(self, root):
        self.legacy = LocalMetadataPacks(root)
        self.indexed = IndexedMetadataPacks(Path(root) / 'indexed')
        self.root = self.legacy.root

    def list(self):
        return self.legacy.list() + self.indexed.list()

    def errors(self):
        return self.legacy.errors() + self.indexed.errors()

    def install(self, pack):
        return self.legacy.install(pack)

    def install_bundle(self, payload):
        return self.indexed.install_bundle(payload)

    def remove(self, pack_id):
        return self.indexed.remove(pack_id) if self.indexed.owns(pack_id) else self.legacy.remove(pack_id)

    def candidates(self, *, title='', kind=None, year=None, namespace=None, value=None, limit=50):
        first = self.legacy.candidates(title=title, kind=kind, year=year, namespace=namespace, value=value, limit=limit)
        return first + self.indexed.candidates(title=title, kind=kind, year=year, namespace=namespace,
                                                value=value, limit=max(0, limit - len(first)))

    def materialize(self, db, candidate):
        parts = candidate.split(':', 2) if isinstance(candidate, str) else []
        if len(parts) != 3:
            raise ValueError('Invalid pack candidate.')
        return self.indexed.materialize(db, candidate) if self.indexed.has(parts[1]) else self.legacy.materialize(db, candidate)

    def creator_candidates(self, creators, limit=100):
        """Exploratory work leads for exact creators already recorded by the owner."""
        result=[]
        for manifest,path in self.indexed.available():
            kind=manifest['kind']
            wanted={value.casefold() for value in creators.get(kind, set()) if isinstance(value,str) and value.strip()}
            if kind not in ('book','music') or not wanted:continue
            try:
                with _db(path) as db:
                    for wanted_creator in sorted(wanted):
                        rows=db.execute("SELECT record_id,title,year,source_ids_json FROM works WHERE lower(json_extract(source_ids_json,'$.creator'))=? ORDER BY title COLLATE NOCASE,record_id LIMIT 20",(wanted_creator,)).fetchall()
                        for row in rows:
                            creator=json.loads(row['source_ids_json']).get('creator')
                            result.append({'workId':f"pack:{manifest['id']}:{row['record_id']}",'title':row['title'],'kind':kind,
                                           'year':row['year'],'creator':creator,'source':'pack:'+manifest['id'],
                                           'sourceVersion':manifest['version'],'format':'Any'})
                            if len(result)>=limit:return result
            except (sqlite3.Error,OSError,ValueError,TypeError):continue
        return result

    def work_releases(self, mappings, limit=500):
        """Read sibling releases of an explicitly linked work without catalog writes."""
        result = []
        if not mappings:
            return result
        for pack in self.legacy.available():
            pack_id=pack['manifest']['id']
            keys={value[len(pack_id)+1:] for value in mappings if value.startswith(pack_id+':')}
            if pack['manifest'].get('identityPolicy'):
                available={r['id'] for r in pack['records']}
                keys={key if key in available else native_record_id(key) for key in keys}
            if not keys:continue
            for record in pack['records']:
                if record['level']!='release' or record['workId'] not in keys:continue
                facts=record.get('fields',{})
                identifier=next((row for row in record.get('identifiers',[]) if row['namespace']=='upc-ean'),None)
                result.append({'id':f"pack:{pack_id}:{record['id']}",'kind':record['kind'],'level':'release',
                               'work_id':f"pack:{pack_id}:{record['workId']}",'title':record['title'],'year':record.get('year'),
                               'format':facts.get('format'),'edition':facts.get('edition'),'season':None,'origin':'pack:'+pack_id,
                               **({'identifier':identifier} if identifier else {}),'coverage':'known-references-only'})
                if len(result)>=limit:return result
        for manifest, path in self.indexed.available():
            keys = [value[len(manifest['id']) + 1:] for value in mappings if value.startswith(manifest['id'] + ':')]
            if manifest['format'] not in (3, 4, 5) or not manifest.get('releaseCount') or not keys:
                continue
            try:
                with _db(path) as db:
                    keys={alias_keys(db,manifest,key)[0] for key in keys}
                    for key in sorted(keys):
                        for row in db.execute('SELECT * FROM releases WHERE work_record_id=? ORDER BY format,edition,record_id LIMIT ?', (key, limit - len(result))):
                            candidate = self.indexed._release_candidate(manifest, self.indexed._record_details(db,manifest,row), 'release of confirmed work; exact copy needs review')
                            candidate['coverage'] = 'known-references-only'
                            result.append(candidate)
                            if len(result) >= limit:
                                return result
            except (sqlite3.Error, OSError, ValueError, TypeError):
                continue
        return result

    def lookup_keys(self,pack_id,record_id):
        current=self.indexed._current(pack_id)
        if not current:
            try:
                _,record=self.legacy.record(pack_id,record_id)
                return list(dict.fromkeys([record_id,record['id']])) if record else [record_id]
            except (ValueError,OSError):return [record_id]
        manifest,path=current
        with _db(path) as db:return alias_keys(db,manifest,record_id)[1]

    def record(self, pack_id, record_id):
        return self.indexed._record(pack_id,record_id)[1] if self.indexed.has(pack_id) else self.legacy.record(pack_id, record_id)


class StagedMetadataCatalog:
    """Owner-managed offline pack shelf; future downloads can stage here safely.

    Catalog files are never household metadata. The installer still validates
    the complete SQLite pack before activation, and an absent shelf is normal.
    """

    def __init__(self, root, installed):
        self.root = reject_links(root)
        self.installed = installed

    def _entries(self):
        notice = self.root / 'catalog.json'
        if not notice.exists():
            return []
        if self.root.is_symlink() or notice.is_symlink() or not notice.is_file() or notice.stat().st_size > 32768:
            raise ValueError('The staged metadata catalog is invalid.')
        try:
            catalog = json.loads(notice.read_text(encoding='utf-8'))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ValueError('The staged metadata catalog is unreadable.') from error
        rows = catalog.get('packs') if isinstance(catalog, dict) and catalog.get('format') == 1 else None
        if not isinstance(rows, list) or len(rows) > 16:
            raise ValueError('The staged metadata catalog has an unsupported format.')
        entries = []
        seen = set()
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError('The staged metadata catalog has an invalid entry.')
            pack_id, version = row.get('id'), row.get('version')
            if (pack_id not in PACK_KINDS or not isinstance(version, str)
                    or not re.fullmatch(r'[1-9][0-9]{0,9}', version) or pack_id in seen
                    or row.get('file') != f'{pack_id}-v{version}.bbpack'
                    or not isinstance(row.get('sha256'), str) or not re.fullmatch(r'[0-9a-f]{64}', row['sha256'])
                    or type(row.get('bytes')) is not int or not 1 <= row['bytes'] <= MAX_BUNDLE_BYTES):
                raise ValueError('The staged metadata catalog has an invalid entry.')
            seen.add(pack_id)
            entries.append(row)
        return entries

    def _bundle(self, row):
        path = self.root / row['file']
        if path.is_symlink() or not path.is_file() or path.stat().st_size != row['bytes']:
            raise ValueError(f"The staged {row['id']} pack is missing or changed.")
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != row['sha256']:
            raise ValueError(f"The staged {row['id']} pack checksum changed.")
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                if sorted(archive.namelist()) != ['data.sqlite', 'manifest.json'] or archive.getinfo('manifest.json').file_size > 32768:
                    raise ValueError('The staged pack has unexpected files.')
                manifest = _manifest(json.loads(archive.read('manifest.json')))
        except (OSError, zipfile.BadZipFile, RuntimeError, json.JSONDecodeError) as error:
            raise ValueError(f"The staged {row['id']} pack is unreadable.") from error
        if manifest['id'] != row['id'] or manifest['version'] != row['version']:
            raise ValueError('The staged pack does not match its catalog entry.')
        return manifest, payload

    def list(self):
        installed = {row['id']: row for row in self.installed.list()}
        results = []
        for row in self._entries():
            try:
                manifest, _ = self._bundle(row)
            except (OSError, ValueError, KeyError, TypeError) as error:
                results.append({'id': row['id'], 'version': row['version'], 'status': 'damaged', 'error': str(error)})
                continue
            current = installed.get(row['id'])
            if not current:
                status = 'available'
            elif int(current['version']) < int(manifest['version']):
                status = 'update'
            elif int(current['version']) > int(manifest['version']):
                status = 'installed-newer'
            elif current.get('databaseSha256') != manifest['databaseSha256']:
                status = 'conflict'
            else:
                status = 'installed'
            results.append({**manifest, 'bundleBytes': row['bytes'], 'status': status})
        return results

    def install(self, pack_id):
        if not isinstance(pack_id, str) or pack_id not in PACK_KINDS:
            raise ValueError('Choose a staged metadata pack.')
        row = next((entry for entry in self._entries() if entry['id'] == pack_id), None)
        if row is None:
            raise ValueError('That metadata pack is not staged for installation.')
        _, payload = self._bundle(row)
        return self.installed.install_bundle(payload)
