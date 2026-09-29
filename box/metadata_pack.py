"""Small, validated offline reference packs, separate from the private catalog.

V1 intentionally accepts only CC0 factual records and no artwork bytes or URLs.
The pack format is a replaceable input format, never a household identity.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import uuid
from pathlib import Path
from file_safety import reject_links

from metadata import normalize_title, timestamp
from metapack_identity import (validate_identity_policy, native_record_id,
                              pack_identifier_allowed, physical_namespace)

PACK_ID = re.compile(r'[a-z][a-z0-9-]{0,63}\Z')
RECORD_ID = re.compile(r'[A-Za-z0-9._-]{1,100}\Z')
MAX_PACK_BYTES = 8 * 1024 * 1024
MAX_RECORDS = 10000


def records_digest(records):
    return hashlib.sha256(json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


def validate_pack(pack):
    if not isinstance(pack, dict) or not isinstance(pack.get('manifest'), dict) or not isinstance(pack.get('records'), list):
        raise ValueError('Invalid metadata pack.')
    manifest, records = pack['manifest'], pack['records']
    local_identity=validate_identity_policy(manifest)
    pack_id, version = manifest.get('id'), manifest.get('version')
    if (manifest.get('format') != 1 or not isinstance(pack_id, str) or not PACK_ID.fullmatch(pack_id)
            or not isinstance(version, str) or not re.fullmatch(r'[1-9][0-9]{0,9}', version)
            or manifest.get('license') != 'CC0-1.0' or not isinstance(manifest.get('source'), str)
            or not manifest['source'].strip() or not isinstance(manifest.get('sourceVersion'), str)
            or not isinstance(manifest.get('sourceUrl'), str)
            or not 1 <= len(records) <= MAX_RECORDS or manifest.get('recordCount') != len(records)
            or manifest.get('recordsSha256') != records_digest(records)):
        raise ValueError('Metadata pack manifest, license, or checksum is invalid.')
    ids = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError('Invalid metadata pack record.')
        rid, level, title = record.get('id'), record.get('level'), record.get('title')
        if (not isinstance(rid, str) or not RECORD_ID.fullmatch(rid) or rid in ids
                or level not in ('work', 'release') or record.get('kind') != 'music'
                or not isinstance(title, str) or not 1 <= len(title.strip()) <= 250
                or record.get('year') is not None and (type(record['year']) is not int or not 1800 <= record['year'] <= 2200)
                or not isinstance(record.get('fields', {}), dict) or not isinstance(record.get('identifiers', []), list)):
            raise ValueError('Invalid or duplicate music record in metadata pack.')
        ids.add(rid)
        if local_identity and not re.fullmatch(r'bbp-[0-9a-f]{32}',rid):
            raise ValueError('An offline sample record requires a Blank Box ID.')
        for field, value in record.get('fields', {}).items():
            if field not in ('artist', 'releaseDate', 'barcode', 'format', 'edition') or not isinstance(value, str) or len(value) > (120 if field in ('format', 'edition') else 250) or field in ('format', 'edition') and level != 'release':
                raise ValueError('Unsupported metadata pack field.')
        for identifier in record.get('identifiers', []):
            if (not isinstance(identifier, dict) or identifier.get('namespace') not in ('musicbrainz-release-group', 'musicbrainz-release', 'musicbrainz-discid', 'disc-id', 'upc-ean')
                    or not isinstance(identifier.get('value'), str) or not 1 <= len(identifier['value']) <= 120):
                raise ValueError('Unsupported metadata pack identifier.')
            if local_identity and (not pack_identifier_allowed(identifier['namespace']) or '://' in identifier['value']):
                raise ValueError('Website identifiers are not supported in this offline sample.')
    by_id = {record['id']: record for record in records}
    for record in records:
        parent = record.get('workId')
        if record['level'] == 'release' and (not isinstance(parent, str) or parent not in by_id or by_id[parent]['level'] != 'work'):
            raise ValueError('A release requires a work in the same pack.')
        if record['level'] == 'work' and parent is not None:
            raise ValueError('A work cannot have a release parent.')
    return manifest


def candidate_id(pack_id, record_id):
    return f'pack:{pack_id}:{record_id}'


class LocalMetadataPacks:
    def __init__(self, root):
        self.root = reject_links(root)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)

    def _path(self, pack_id):
        if not isinstance(pack_id, str) or not PACK_ID.fullmatch(pack_id):
            raise ValueError('Invalid metadata pack ID.')
        return self.root / (pack_id + '.json')

    def available(self):
        for path in sorted(self.root.glob('*.json')):
            try:
                yield self._read(path)
            except (ValueError, OSError, UnicodeError, json.JSONDecodeError):
                continue  # Optional pack failure cannot interrupt private-catalog search.

    def list(self):
        return [pack['manifest'] for pack in self.available()]

    def errors(self):
        failures = []
        for path in sorted(self.root.glob('*.json')):
            try:
                self._read(path)
            except (ValueError, OSError, UnicodeError, json.JSONDecodeError):
                failures.append(path.stem)
        return failures

    def _read(self, path):
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_PACK_BYTES:
            raise ValueError('Metadata pack file is invalid.')
        pack = json.loads(path.read_text(encoding='utf-8'))
        validate_pack(pack)
        return pack

    def install(self, pack):
        from metadata_indexed_pack import public_distribution
        if public_distribution():
            raise ValueError('This installation requires publisher-signed public metapack imports.')
        manifest = validate_pack(pack)
        raw = json.dumps(pack, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
        if len(raw) > MAX_PACK_BYTES:
            raise ValueError('Metadata pack exceeds the V1 size limit.')
        target = self._path(manifest['id'])
        if target.exists():
            try:
                previous = self._read(target)['manifest']
            except (ValueError, OSError, UnicodeError, json.JSONDecodeError):
                previous = None  # A reviewed install can repair a damaged pack.
            if previous:
                if int(manifest['version']) < int(previous['version']):
                    raise ValueError('An older metadata pack cannot replace an installed version.')
                if manifest['version'] == previous['version']:
                    if manifest['recordsSha256'] != previous['recordsSha256']:
                        raise ValueError('The installed pack version has different contents.')
                    return previous
        staged = self.root / ('.' + uuid.uuid4().hex + '.partial')
        staged_created = False
        try:
            with open(staged, 'xb') as output:
                staged_created = True
                output.write(raw)
                output.flush()
                os.fsync(output.fileno())
            self._read(staged)
            os.replace(staged, target)
        finally:
            if staged_created:staged.unlink(missing_ok=True)
        return manifest

    def remove(self, pack_id):
        path = self._path(pack_id)
        if not path.is_file() or path.is_symlink():
            raise ValueError('Metadata pack is not installed.')
        path.unlink()

    def record(self, pack_id, record_id):
        if not isinstance(record_id, str) or not RECORD_ID.fullmatch(record_id):
            raise ValueError('Invalid metadata record ID.')
        pack = self._read(self._path(pack_id))
        record=next((record for record in pack['records'] if record['id']==record_id),None)
        if record is None and pack['manifest'].get('identityPolicy'):
            record=next((record for record in pack['records'] if record['id']==native_record_id(record_id)),None)
        return pack,record

    def candidates(self, *, title='', kind=None, year=None, namespace=None, value=None, limit=50):
        if limit <= 0:
            return []
        results = []
        key = normalize_title(title)
        for pack in self.available():
            for record in pack['records']:
                if kind and record['kind'] != kind:
                    continue
                identifier_match = bool(namespace and value and any(physical_namespace(entry['namespace']) == physical_namespace(namespace) and entry['value'] == value for entry in record.get('identifiers', [])))
                title_match = bool(key and normalize_title(record['title']).startswith(key))
                if (namespace and value and not identifier_match) or (not namespace and not title_match):
                    continue
                exact = key and normalize_title(record['title']) == key
                evidence = 'exact identifier' if identifier_match else 'title and year' if exact and year == record.get('year') and year is not None else 'exact title' if exact else 'title prefix'
                results.append({'id': candidate_id(pack['manifest']['id'], record['id']), 'kind': record['kind'], 'level': record['level'],
                                'work_id': candidate_id(pack['manifest']['id'], record['workId']) if record['level'] == 'release' else None,
                                'title': record['title'], 'year': record.get('year'), 'origin': 'pack:' + pack['manifest']['id'],
                                'evidence': [evidence], 'confidence': 'identifier' if identifier_match else 'review', 'requiresReview': True})
                if len(results) >= limit:
                    return results
        return results

    def materialize(self, db: sqlite3.Connection, candidate):
        parts = candidate.split(':') if isinstance(candidate, str) else []
        if len(parts) != 3 or parts[0] != 'pack':
            raise ValueError('Invalid pack candidate.')
        pack, record = self.record(parts[1], parts[2])
        if record is None:
            raise ValueError('Pack candidate is no longer available.')
        def persist(source_record):
            mapping = f"{parts[1]}:{source_record['id']}"
            existing = db.execute("SELECT entity_id FROM metadata_identifiers WHERE namespace='blankbox-pack-record' AND value=? LIMIT 1", (mapping,)).fetchone()
            if not existing and pack['manifest'].get('identityPolicy'):
                # Match only an already confirmed mapping to this exact old ID.
                # Never infer household identity from a title or physical clue.
                compatible={r['entity_id'] for r in db.execute("SELECT entity_id,value FROM metadata_identifiers WHERE namespace='blankbox-pack-record' AND value LIKE ?",(parts[1]+':%',))
                            if native_record_id(r['value'].split(':',1)[1])==source_record['id']}
                if len(compatible)>1:raise ValueError('Saved pack identity is ambiguous; review the existing references.')
                if compatible:existing={'entity_id':next(iter(compatible))}
            parent = persist(next(entry for entry in pack['records'] if entry['id'] == source_record['workId'])) if source_record['level'] == 'release' else None
            entity_id = existing['entity_id'] if existing else 'bbm:' + source_record['level'] + ':' + str(uuid.uuid4())
            when = timestamp()
            facts = source_record.get('fields', {})
            if not existing:db.execute('INSERT INTO metadata_entities(id,kind,level,work_id,title,title_key,year,origin,created_at,updated_at,format,edition) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                       (entity_id, 'music', source_record['level'], parent, source_record['title'], normalize_title(source_record['title']), source_record.get('year'), 'pack:' + parts[1], when, when,
                        facts.get('format') if source_record['level'] == 'release' else None,
                        facts.get('edition') if source_record['level'] == 'release' else None))
            provenance = ('pack:' + parts[1], source_record['id']+'@pack-v'+pack['manifest']['version'], pack['manifest']['sourceVersion'], pack['manifest']['license'], when)
            for field, value in {'title': source_record['title'], **({'year': source_record['year']} if source_record.get('year') else {}), **source_record.get('fields', {})}.items():
                db.execute('INSERT OR IGNORE INTO metadata_field_values VALUES(?,?,?,?,?,?,?,?,?,?)',
                           (entity_id, field, json.dumps(value, ensure_ascii=False), *provenance, 0, 1))
            for identifier in [*source_record.get('identifiers', []), {'namespace': 'blankbox-pack-record', 'value': mapping}]:
                db.execute('INSERT OR IGNORE INTO metadata_identifiers VALUES(?,?,?,?,?,?,?,?)',
                           (entity_id, identifier['namespace'], identifier['value'], *provenance))
            return entity_id
        return persist(record)
