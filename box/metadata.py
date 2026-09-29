"""Private, offline metadata identity foundation for the household catalog.

This module has no network or pack dependency. Adapters and pack readers are
contracts only; importing a provider record is a later, reviewed workflow.
"""
from __future__ import annotations

import json
from metapack_identity import visible_identifiers, physical_namespace, pack_identifier_allowed
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol


METADATA_NAMESPACE = uuid.UUID('3c640b3b-6910-5e9c-a818-c94a9e17d1b1')
LEGACY_FIELDS = ('title', 'kind', 'year', 'releaseDate', 'description', 'genre', 'duration', 'artist', 'catalogDetails')


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def local_work_id(item_id):
    """Stable per-household-item identity, without asserting a global match."""
    return 'bbm:work:' + str(uuid.uuid5(METADATA_NAMESPACE, 'item:' + item_id))


def local_release_id(physical_release_id):
    """Stable local knowledge about one owned physical release, not a provider ID."""
    return 'bbm:release:' + str(uuid.uuid5(METADATA_NAMESPACE, 'physical-release:' + physical_release_id))


def local_digital_release_id(source_id):
    """Stable household edition evidence for one linked or managed file."""
    return 'bbm:release:' + str(uuid.uuid5(METADATA_NAMESPACE, 'digital-source:' + source_id))


def valid_season(value):
    return value is None or value in ('specials', 'complete-series') or isinstance(value, str) and bool(re.fullmatch(r'[1-9][0-9]?', value))


def normalize_title(value):
    return ' '.join(re.findall(r'[^\W_]+', str(value).casefold()))


class MetadataAdapter(Protocol):
    """Future source boundary: adapters supply facts, never household merges."""
    source: str
    source_version: str
    license: str

    def candidates(self, clues: dict) -> list[dict]: ...


class MetadataPackReader(Protocol):
    """Optional, separately stored reference data; no Core runtime dependency."""
    pack_id: str
    pack_version: str

    def search(self, query: str, *, level: str | None = None, limit: int = 20) -> list[dict]: ...
    def close(self) -> None: ...


class MetadataRepository(Protocol):
    """Private catalog boundary shared by future Core services."""
    def create_entity(self, *, kind: str, level: str, title: str, year: int | None = None, work_id: str | None = None) -> str: ...
    def get_entity(self, entity_id: str) -> dict | None: ...
    def set_field(self, entity_id: str, field: str, value, *, source: str = 'owner', source_record_id: str = '', source_version: str = '', license: str = 'unclassified-local', owner_entered: bool = True, from_pack: bool = False) -> None: ...
    def set_identifier(self, entity_id: str, namespace: str, value: str, *, source: str = 'owner', source_record_id: str = '', source_version: str = '', license: str = 'unclassified-local') -> None: ...
    def remove_identifier(self, entity_id: str, namespace: str, value: str, *, source: str = 'owner', source_record_id: str = '') -> int: ...
    def search(self, query: str, *, level: str | None = None, limit: int = 20) -> list[dict]: ...
    def by_identifier(self, namespace: str, value: str) -> list[dict]: ...
    def link_confirmed(self, target_type: str, target_id: str, entity_id: str) -> None: ...


def backfill_item(db: sqlite3.Connection, item: dict):
    """Copy current effective facts as legacy evidence; do not rewrite item JSON."""
    item_id = item['id']
    entity_id = local_work_id(item_id)
    when = item.get('addedAt') or timestamp()
    title = str(item.get('title') or 'Untitled')
    db.execute('INSERT OR IGNORE INTO metadata_entities(id,kind,level,work_id,title,title_key,year,origin,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
               (entity_id, item.get('kind') or 'file', 'work', None, title, normalize_title(title), item.get('year'), 'legacy-household', when, when))
    db.execute('INSERT OR IGNORE INTO metadata_links(target_type,target_id,entity_id,relationship,confirmed_at) VALUES(?,?,?,?,?)',
               ('item', item_id, entity_id, 'local-work', when))
    db.execute('UPDATE metadata_entities SET kind=?,title=?,title_key=?,year=?,updated_at=? WHERE id=?',
               (item['kind'], title, normalize_title(title), item.get('year'), timestamp(), entity_id))
    provenance = item.get('metadataProvenance') or {}
    overrides = set(item.get('metadataOverrides') or [])
    # Household categories are separate from provider genres and never enter a
    # distributable pack. Preserve explicit owner provenance in local metadata.
    if 'customGenres' in item:
        db.execute('INSERT INTO metadata_field_values(entity_id,field,value_json,source,source_record_id,source_version,license,imported_at,owner_entered,from_pack) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(entity_id,field,source,source_record_id) DO UPDATE SET value_json=excluded.value_json,imported_at=CASE WHEN metadata_field_values.value_json<>excluded.value_json THEN excluded.imported_at ELSE metadata_field_values.imported_at END',
                   (entity_id,'customGenres',json.dumps(item['customGenres'],ensure_ascii=False),'owner','','','unclassified-local',timestamp(),1,0))
    for field in LEGACY_FIELDS:
        value = item.get(field)
        if value is None or value == '':
            if field in overrides:
                db.execute("DELETE FROM metadata_field_values WHERE entity_id=? AND field=? AND source='owner'", (entity_id, field))
            continue
        detail = provenance.get(field) if isinstance(provenance, dict) else None
        detail = detail if isinstance(detail, dict) else {}
        owner = field in overrides or field=='catalogDetails' and any(key.startswith('catalogDetails.') for key in overrides)
        if field=='catalogDetails' and owner and field not in overrides:
            value={key:value[key] for key in value if 'catalogDetails.'+key in overrides}
        source = 'owner' if owner else 'legacy:' + str(detail.get('source') or 'household')
        db.execute('INSERT INTO metadata_field_values(entity_id,field,value_json,source,source_record_id,source_version,license,imported_at,owner_entered,from_pack) VALUES(?,?,?,?,?,?,?,?,?,?) '
                   'ON CONFLICT(entity_id,field,source,source_record_id) DO UPDATE SET value_json=excluded.value_json,imported_at=CASE WHEN metadata_field_values.value_json<>excluded.value_json THEN excluded.imported_at ELSE metadata_field_values.imported_at END WHERE excluded.owner_entered=1',
                   (entity_id, field, json.dumps(value, ensure_ascii=False), source,
                    '' if owner else str(detail.get('sourceId') or ''), '', 'unclassified-local',
                    str(detail.get('updatedAt') or when), int(owner), 0))
    if 'title' in overrides and item.get('title'):
        db.execute('UPDATE metadata_entities SET title=?,title_key=?,updated_at=? WHERE id=?',
                   (str(item['title']), normalize_title(item['title']), timestamp(), entity_id))
    if 'year' in overrides:
        db.execute('UPDATE metadata_entities SET year=?,updated_at=? WHERE id=?',
                   (item.get('year'), timestamp(), entity_id))
    for role in ('poster', 'backdrop'):
        reference = item.get(role)
        if isinstance(reference, str) and reference:
            db.execute('INSERT OR IGNORE INTO metadata_artwork_refs(entity_id,role,reference,reference_type,source,source_record_id,rights,cache_policy,owner_provided) VALUES(?,?,?,?,?,?,?,?,?)',
                       (entity_id, role, reference, 'remote' if reference.startswith(('https://', 'http://')) else 'local',
                        'legacy-household', '', 'unreviewed-household-reference', 'reference-only', int(role in overrides)))
    sync_source_metadata(db, item)


def sync_source_metadata(db: sqlite3.Connection, item: dict):
    """Retain attached provider facts on the local work without changing display choice."""
    entity_id = local_work_id(item['id'])
    when = item.get('addedAt') or timestamp()
    for source in item.get('sources', []):
        if not isinstance(source, dict) or source.get('type') not in ('jellyfin', 'plex', 'emby'):
            continue
        source_id = source.get('id')
        snapshot = source.get('metadataSnapshot')
        if not isinstance(source_id, str) or not source_id or not isinstance(snapshot, dict):
            continue
        for identifier in source.get('metadataIdentifiers', []):
            if not isinstance(identifier,dict) or not isinstance(identifier.get('namespace'),str) or not isinstance(identifier.get('value'),str):continue
            db.execute('INSERT OR IGNORE INTO metadata_identifiers VALUES(?,?,?,?,?,?,?,?)',
                       (entity_id,identifier['namespace'],identifier['value'],'provider:'+source['type'],source_id,'','private-provider-snapshot',when))
        for field in LEGACY_FIELDS:
            value = snapshot.get(field)
            if value is None or value == '':
                continue
            db.execute('INSERT INTO metadata_field_values(entity_id,field,value_json,source,source_record_id,source_version,license,imported_at,owner_entered,from_pack) VALUES(?,?,?,?,?,?,?,?,?,?) '
                       'ON CONFLICT(entity_id,field,source,source_record_id) DO UPDATE SET value_json=excluded.value_json,imported_at=CASE WHEN metadata_field_values.value_json<>excluded.value_json THEN excluded.imported_at ELSE metadata_field_values.imported_at END',
                       (entity_id, field, json.dumps(value, ensure_ascii=False), 'provider:' + source['type'],
                        source_id, '', 'private-provider-snapshot', source.get('addedAt') or when, 0, 0))


def sync_owned_releases(db: sqlite3.Connection, item: dict):
    """Keep owner-entered release facts beside, and linked to, physical ownership."""
    work_id = local_work_id(item['id'])
    versions = {version['id']: version for version in item.get('versions', [])}
    cleared_identifiers = set()
    for source in item.get('sources', []):
        if not isinstance(source, dict) or source.get('type') != 'physical' or not source.get('physicalReleaseId'):
            continue
        physical_id = source['physicalReleaseId']
        contents = {row[0] for row in db.execute('SELECT item_id FROM package_contents WHERE release_id=?', (physical_id,))}
        if contents != {item['id']}:
            continue  # Multi-title packages cannot assert a single work release.
        entity_id = local_release_id(physical_id)
        existing = db.execute('SELECT work_id FROM metadata_entities WHERE id=?', (entity_id,)).fetchone()
        if existing and existing['work_id'] != work_id:
            continue
        format_name = str(source.get('label') or '').strip()[:120] or None
        version_label = str(versions.get(source.get('versionId'), {}).get('label') or '').strip()
        edition = str(source.get('edition') or '').strip()[:120] or None
        season = source.get('season') or versions.get(source.get('versionId'), {}).get('season')
        season = season if item['kind'] == 'tv' and valid_season(season) else None
        if not edition and not season and version_label and version_label not in ('Standard or unknown edition', format_name):
            edition = version_label
        when = source.get('addedAt') or timestamp()
        db.execute('INSERT INTO metadata_entities(id,kind,level,work_id,title,title_key,year,origin,created_at,updated_at,format,edition,season) '
                   'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET format=excluded.format,edition=excluded.edition,season=excluded.season',
                   (entity_id, item['kind'], 'release', work_id, item.get('title') or 'Untitled',
                    normalize_title(item.get('title') or 'Untitled'), item.get('year'), 'household-copy', when, timestamp(), format_name, edition, season))
        db.execute('INSERT OR IGNORE INTO metadata_links(target_type,target_id,entity_id,relationship,confirmed_at) VALUES(?,?,?,?,?)',
                   ('physical_release', physical_id, entity_id, 'local-release', when))
        for field, value in (('format', format_name), ('edition', edition)):
            if value:
                db.execute('INSERT INTO metadata_field_values(entity_id,field,value_json,source,source_record_id,source_version,license,imported_at,owner_entered,from_pack) '
                           'VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(entity_id,field,source,source_record_id) DO NOTHING',
                           (entity_id, field, json.dumps(value, ensure_ascii=False), 'owner', physical_id, '', 'unclassified-local', when, 1, 0))
        if season:
            db.execute('INSERT INTO metadata_field_values(entity_id,field,value_json,source,source_record_id,source_version,license,imported_at,owner_entered,from_pack) VALUES(?,?,?,?,?,?,?,?,?,?) '
                       'ON CONFLICT(entity_id,field,source,source_record_id) DO NOTHING',
                       (entity_id, 'season', json.dumps(season), 'owner', physical_id, '', 'unclassified-local', when, 1, 0))
        for field in ('creator', 'publisher', 'platform', 'region', 'catalogNumber'):
            value = source.get(field)
            if isinstance(value, str) and value.strip():
                db.execute('INSERT INTO metadata_field_values(entity_id,field,value_json,source,source_record_id,source_version,license,imported_at,owner_entered,from_pack) VALUES(?,?,?,?,?,?,?,?,?,?) '
                           'ON CONFLICT(entity_id,field,source,source_record_id) DO NOTHING',
                           (entity_id, 'author' if field == 'creator' and item['kind'] == 'book' else field, json.dumps(value.strip(), ensure_ascii=False), 'owner', physical_id, '', 'unclassified-local', when, 1, 0))
        barcode = source.get('barcode')
        if physical_id not in cleared_identifiers:
            db.execute("DELETE FROM metadata_identifiers WHERE entity_id=? AND source='owner-observed' AND source_record_id=?",
                       (entity_id, physical_id))
            cleared_identifiers.add(physical_id)
        if isinstance(barcode, str) and barcode.strip():
            namespace = 'isbn' if item['kind'] == 'book' else 'upc-ean'
            db.execute('INSERT OR IGNORE INTO metadata_identifiers(entity_id,namespace,value,source,source_record_id,source_version,license,imported_at) VALUES(?,?,?,?,?,?,?,?)',
                       (entity_id, namespace, barcode.strip(), 'owner-observed', physical_id, '', 'unclassified-local', when))


def remove_digital_source_links(db: sqlite3.Connection, source_id: str):
    """Retire a file's local evidence after the source is removed."""
    db.execute("DELETE FROM metadata_links WHERE target_type='digital_source' AND target_id=?", (source_id,))
    local_id = local_digital_release_id(source_id)
    db.execute("DELETE FROM metadata_entities WHERE id=? AND origin='household-file' AND NOT EXISTS (SELECT 1 FROM metadata_links WHERE entity_id=?)", (local_id, local_id))


def sync_digital_releases(db: sqlite3.Connection, item: dict):
    """Keep owner-entered digital editions separate from file observations and works."""
    work_id = local_work_id(item['id'])
    versions = {version['id']: version for version in item.get('versions', [])}
    for source in item.get('sources', []):
        if not isinstance(source, dict) or source.get('type') not in ('local', 'digital') or not source.get('id'):
            continue
        source_id = source['id']
        edition = str(source.get('edition') or '').strip()[:120]
        local_id = local_digital_release_id(source_id)
        owner_fields={field:source.get(field) for field in ('edition','creator','publisher','platform','volume','issue','region','catalogNumber','barcode') if source.get(field)}
        if not owner_fields:
            db.execute("DELETE FROM metadata_links WHERE target_type='digital_source' AND target_id=? AND entity_id=? AND relationship='local-release'", (source_id, local_id))
            db.execute("DELETE FROM metadata_entities WHERE id=? AND origin='household-file' AND NOT EXISTS (SELECT 1 FROM metadata_links WHERE entity_id=?)", (local_id, local_id))
            continue
        version = versions.get(source.get('versionId'), {})
        season = version.get('season') if item.get('kind') == 'tv' and valid_season(version.get('season')) else None
        when = source.get('addedAt') or timestamp()
        title = item.get('title') or 'Untitled'
        db.execute('INSERT INTO metadata_entities(id,kind,level,work_id,title,title_key,year,origin,created_at,updated_at,format,edition,season) '
                   'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET kind=excluded.kind,work_id=excluded.work_id,title=excluded.title,title_key=excluded.title_key,year=excluded.year,updated_at=excluded.updated_at,edition=excluded.edition,season=excluded.season',
                   (local_id, item['kind'], 'release', work_id, title, normalize_title(title), item.get('year'), 'household-file', when, timestamp(), 'Digital file', edition, season))
        db.execute('INSERT OR IGNORE INTO metadata_links(target_type,target_id,entity_id,relationship,confirmed_at) VALUES(?,?,?,?,?)',
                   ('digital_source', source_id, local_id, 'local-release', when))
        db.execute('INSERT INTO metadata_field_values(entity_id,field,value_json,source,source_record_id,source_version,license,imported_at,owner_entered,from_pack) '
                   'VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(entity_id,field,source,source_record_id) DO UPDATE SET value_json=excluded.value_json,imported_at=excluded.imported_at',
                   (local_id, 'edition', json.dumps(edition, ensure_ascii=False), 'owner', source_id, '', 'unclassified-local', timestamp(), 1, 0))
        for field in ('creator','publisher','platform','volume','issue','region','catalogNumber','barcode'):
            value=source.get(field)
            if not value:
                db.execute("DELETE FROM metadata_field_values WHERE entity_id=? AND field=? AND source='owner' AND source_record_id=?",(local_id,field,source_id))
            else:
                db.execute('INSERT INTO metadata_field_values(entity_id,field,value_json,source,source_record_id,source_version,license,imported_at,owner_entered,from_pack) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(entity_id,field,source,source_record_id) DO UPDATE SET value_json=excluded.value_json,imported_at=excluded.imported_at',
                           (local_id,field,json.dumps(value,ensure_ascii=False),'owner',source_id,'','unclassified-local',timestamp(),1,0))
        db.execute("DELETE FROM metadata_identifiers WHERE entity_id=? AND source='owner' AND source_record_id=?",(local_id,source_id))
        if source.get('barcode'):
            db.execute('INSERT OR IGNORE INTO metadata_identifiers(entity_id,namespace,value,source,source_record_id,source_version,license,imported_at) VALUES(?,?,?,?,?,?,?,?)',
                       (local_id,'isbn' if item['kind']=='book' else 'upc-ean',source['barcode'],'owner',source_id,'','unclassified-local',timestamp()))
        for field, value in (('fileExtension', Path(str(source.get('path') or '')).suffix.lower().lstrip('.')), ('mimeHint', source.get('mime'))):
            if isinstance(value, str) and value:
                db.execute('INSERT INTO metadata_field_values(entity_id,field,value_json,source,source_record_id,source_version,license,imported_at,owner_entered,from_pack) '
                           'VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(entity_id,field,source,source_record_id) DO UPDATE SET value_json=excluded.value_json,imported_at=excluded.imported_at',
                           (local_id, field, json.dumps(value), 'observed-file', source_id, '', 'local-observation', timestamp(), 0, 0))


def confirm_entity(db: sqlite3.Connection, target_type: str, target_id: str, entity_id: str):
    """Validate and store an owner decision inside the caller's catalog transaction."""
    if target_type not in ('item', 'physical_release', 'digital_source'):
        raise ValueError('Unsupported metadata link target.')
    table = 'items' if target_type == 'item' else 'physical_releases'
    level = 'work' if target_type == 'item' else 'release'
    target = db.execute('SELECT * FROM ' + table + ' WHERE id=?', (target_id,)).fetchone() if target_type != 'digital_source' else None
    source_item = None
    if target_type == 'digital_source':
        for row in db.execute('SELECT id,data FROM items'):
            item = json.loads(row['data'])
            if any(source.get('id') == target_id and source.get('type') in ('local', 'digital') for source in item.get('sources', [])):
                if source_item is not None:
                    raise ValueError('The digital source ID is ambiguous.')
                source_item = item
        target = source_item
    entity = db.execute('SELECT kind,work_id FROM metadata_entities WHERE id=? AND level=?', (entity_id, level)).fetchone()
    if not target:
        raise ValueError('Link target does not exist.')
    if not entity:
        raise ValueError('Metadata level does not match the target.')
    if target_type == 'item' and json.loads(target['data']).get('kind') != entity['kind']:
        raise ValueError('The metadata and library item have different media types.')
    if target_type == 'physical_release':
        kinds = {json.loads(row[0]).get('kind') for row in db.execute('SELECT i.data FROM package_contents AS p JOIN items AS i ON i.id=p.item_id WHERE p.release_id=?', (target_id,))}
        if kinds and entity['kind'] not in kinds:
            raise ValueError('The metadata and physical copy have different media types.')
    if target_type == 'digital_source' and source_item['kind'] != entity['kind']:
        raise ValueError('The metadata and digital file have different media types.')
    db.execute('INSERT OR IGNORE INTO metadata_links VALUES(?,?,?,?,?)',
               (target_type, target_id, entity_id, 'confirmed-' + level, timestamp()))
    if target_type == 'digital_source':
        db.execute('INSERT OR IGNORE INTO metadata_links VALUES(?,?,?,?,?)',
                   ('item', source_item['id'], entity['work_id'], 'confirmed-work', timestamp()))


class SQLiteMetadataRepository:
    """Local entity and evidence operations; linking requires explicit review."""

    def __init__(self, connect):
        self.connect = connect

    def create_entity(self, *, kind, level, title, year=None, work_id=None, format=None, edition=None, season=None):
        if level not in ('work', 'release') or not str(title).strip():
            raise ValueError('A work or release needs a title.')
        if level == 'work' and work_id is not None or level == 'release' and not work_id:
            raise ValueError('Only releases reference a work.')
        if level == 'work' and (format or edition):
            raise ValueError('Format and edition belong to a release, not a work.')
        if not valid_season(season) or season is not None and (kind != 'tv' or level != 'release'):
            raise ValueError('A season belongs to a TV release.')
        for value in (format, edition):
            if value is not None and (not isinstance(value, str) or len(value.strip()) > 120):
                raise ValueError('Enter a valid release format and edition.')
        entity_id = 'bbm:' + level + ':' + str(uuid.uuid4())
        with self.connect() as db:
            if work_id and not db.execute("SELECT 1 FROM metadata_entities WHERE id=? AND level='work' AND kind=?", (work_id, kind)).fetchone():
                raise ValueError('The release work does not exist.')
            if level == 'release' and format:
                existing = db.execute("SELECT id FROM metadata_entities WHERE level='release' AND origin='manual' AND work_id=? "
                                      "AND format=? COLLATE NOCASE AND COALESCE(edition,'')=? COLLATE NOCASE AND COALESCE(season,'')=? LIMIT 1",
                                      (work_id, format.strip(), (edition or '').strip(), season or '')).fetchone()
                if existing:
                    return existing['id']
            when = timestamp()
            db.execute('INSERT INTO metadata_entities(id,kind,level,work_id,title,title_key,year,origin,created_at,updated_at,format,edition,season) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       (entity_id, kind, level, work_id, title.strip(), normalize_title(title), year, 'manual', when, when,
                        format.strip() or None if format else None, edition.strip() or None if edition else None, season))
            self._set_field(db, entity_id, 'title', title.strip(), 'owner', owner_entered=True)
            if year is not None:
                self._set_field(db, entity_id, 'year', year, 'owner', owner_entered=True)
            for field, value in (('format', format), ('edition', edition), ('season', season)):
                if value and value.strip():
                    self._set_field(db, entity_id, field, value.strip(), 'owner', owner_entered=True)
        return entity_id

    @staticmethod
    def _set_field(db, entity_id, field, value, source, *, source_record_id='', source_version='', license='unclassified-local', owner_entered=False, from_pack=False):
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}', field or '') or field in ('poster', 'backdrop', 'artwork') or not source or not db.execute('SELECT 1 FROM metadata_entities WHERE id=?', (entity_id,)).fetchone():
            raise ValueError('Choose an existing entity, field, and source.')
        db.execute('INSERT INTO metadata_field_values(entity_id,field,value_json,source,source_record_id,source_version,license,imported_at,owner_entered,from_pack) VALUES(?,?,?,?,?,?,?,?,?,?) '
                   'ON CONFLICT(entity_id,field,source,source_record_id) DO UPDATE SET value_json=excluded.value_json,source_version=excluded.source_version,license=excluded.license,imported_at=excluded.imported_at,owner_entered=excluded.owner_entered,from_pack=excluded.from_pack',
                   (entity_id, field, json.dumps(value, ensure_ascii=False), source, source_record_id, source_version, license, timestamp(), int(owner_entered), int(from_pack)))

    def set_field(self, entity_id, field, value, *, source='owner', source_record_id='', source_version='', license='unclassified-local', owner_entered=True, from_pack=False):
        with self.connect() as db:
            self._set_field(db, entity_id, field, value, source, source_record_id=source_record_id,
                            source_version=source_version, license=license, owner_entered=owner_entered, from_pack=from_pack)
            if field == 'title' and source == 'owner':
                db.execute('UPDATE metadata_entities SET title=?,title_key=?,updated_at=? WHERE id=?', (value, normalize_title(value), timestamp(), entity_id))
            elif field == 'year' and source == 'owner':
                db.execute('UPDATE metadata_entities SET year=?,updated_at=? WHERE id=?', (value, timestamp(), entity_id))
            elif field in ('format', 'edition', 'season') and source == 'owner':
                entity = db.execute('SELECT level,kind FROM metadata_entities WHERE id=?', (entity_id,)).fetchone()
                if not entity or entity['level'] != 'release' or value is not None and (not isinstance(value, str) or len(value.strip()) > 120) or field == 'season' and (entity['kind'] != 'tv' or not valid_season(value)):
                    raise ValueError('Format, edition, or season is invalid for this release.')
                db.execute(f'UPDATE metadata_entities SET {field}=?,updated_at=? WHERE id=?',
                           (value.strip() or None if value else None, timestamp(), entity_id))

    def set_identifier(self, entity_id, namespace, value, *, source='owner', source_record_id='', source_version='', license='unclassified-local'):
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{0,63}', namespace or '') or not isinstance(value, str) or not 1 <= len(value) <= 512 or not source:
            raise ValueError('Identifier namespace, value, and source are required.')
        with self.connect() as db:
            db.execute('INSERT INTO metadata_identifiers(entity_id,namespace,value,source,source_record_id,source_version,license,imported_at) VALUES(?,?,?,?,?,?,?,?) '
                       'ON CONFLICT(entity_id,namespace,value,source,source_record_id) DO UPDATE SET source_version=excluded.source_version,license=excluded.license,imported_at=excluded.imported_at',
                       (entity_id, namespace, value, source, source_record_id, source_version, license, timestamp()))

    def remove_identifier(self, entity_id, namespace, value, *, source='owner', source_record_id=''):
        with self.connect() as db:
            return db.execute('DELETE FROM metadata_identifiers WHERE entity_id=? AND namespace=? AND value=? AND source=? AND source_record_id=?',
                              (entity_id, namespace, value, source, source_record_id)).rowcount

    def replace_identifier(self, entity_id, namespace, old_value, new_value, *, source='owner', source_record_id=''):
        """Replace one mapping atomically without disturbing other candidates."""
        if not isinstance(new_value, str) or not 1 <= len(new_value) <= 512:
            raise ValueError('Enter an identifier value.')
        with self.connect() as db:
            row = db.execute('SELECT source_version,license FROM metadata_identifiers WHERE entity_id=? AND namespace=? AND value=? AND source=? AND source_record_id=?',
                             (entity_id, namespace, old_value, source, source_record_id)).fetchone()
            if not row:
                raise ValueError('The identifier mapping is no longer present.')
            db.execute('INSERT OR IGNORE INTO metadata_identifiers(entity_id,namespace,value,source,source_record_id,source_version,license,imported_at) VALUES(?,?,?,?,?,?,?,?)',
                       (entity_id, namespace, new_value, source, source_record_id, row['source_version'], row['license'], timestamp()))
            db.execute('DELETE FROM metadata_identifiers WHERE entity_id=? AND namespace=? AND value=? AND source=? AND source_record_id=?',
                       (entity_id, namespace, old_value, source, source_record_id))

    def candidates(self, *, title='', kind=None, year=None, namespace=None, value=None, limit=20):
        """Return evidence for review, never a merge or an inferred release."""
        if not 1 <= limit <= 100:
            raise ValueError('Invalid candidate limit.')
        if namespace and value:
            matches = self.by_identifier(namespace, value)[:limit]
            evidence = 'exact identifier'
        else:
            matches = self.search(title, limit=limit)
            evidence = 'title'
        wanted = normalize_title(title)
        results = []
        for entity in matches:
            if kind and entity['kind'] != kind:
                continue
            exact_title = bool(wanted and normalize_title(entity['title']) == wanted)
            same_year = year is not None and entity['year'] == year
            reason = evidence if evidence == 'exact identifier' else 'title and year' if exact_title and same_year else 'exact title' if exact_title else 'title prefix'
            results.append({**entity, 'evidence': [reason], 'confidence': 'identifier' if evidence == 'exact identifier' else 'title-year' if same_year and exact_title else 'review', 'requiresReview': True})
        return results

    def search(self, query, *, level=None, limit=20):
        if level not in (None, 'work', 'release') or not 1 <= limit <= 100:
            raise ValueError('Invalid search level or limit.')
        key = normalize_title(query)
        if not key:
            return []
        with self.connect() as db:
            rows = db.execute('SELECT id,kind,level,work_id,title,year,origin,format,edition,season FROM metadata_entities WHERE (? IS NULL OR level=?) AND title_key LIKE ? ORDER BY CASE WHEN title_key=? THEN 0 ELSE 1 END,title LIMIT ?',
                              (level, level, key + '%', key, limit)).fetchall()
        return [dict(row) for row in rows]

    def get_entity(self, entity_id):
        with self.connect() as db:
            row = db.execute('SELECT * FROM metadata_entities WHERE id=?', (entity_id,)).fetchone()
            if not row:
                return None
            entity = dict(row)
            entity['fields'] = [{**dict(value), 'value': json.loads(value['value_json'])} for value in db.execute('SELECT * FROM metadata_field_values WHERE entity_id=? ORDER BY field,owner_entered DESC,source', (entity_id,))]
            entity['identifiers'] = visible_identifiers(db.execute('SELECT * FROM metadata_identifiers WHERE entity_id=? ORDER BY namespace,value', (entity_id,)))
            entity['artworkRefs'] = [dict(value) for value in db.execute('SELECT * FROM metadata_artwork_refs WHERE entity_id=? ORDER BY role', (entity_id,))]
            return entity

    def by_identifier(self, namespace, value):
        with self.connect() as db:
            namespaces=('disc-id','musicbrainz-discid') if physical_namespace(namespace)=='disc-id' else (namespace,)
            marks=','.join('?' for _ in namespaces)
            rows = db.execute(f"SELECT DISTINCT e.id,e.kind,e.level,e.work_id,e.title,e.year,e.origin,e.format,e.edition,e.season FROM metadata_identifiers i JOIN metadata_entities e ON e.id=i.entity_id WHERE i.namespace IN ({marks}) AND i.value=? AND (i.source NOT LIKE 'pack:%' OR ?=1) ORDER BY e.title,e.id", (*namespaces,value,int(pack_identifier_allowed(physical_namespace(namespace))))).fetchall()
        return [dict(row) for row in rows]

    def link_confirmed(self, target_type, target_id, entity_id):
        with self.connect() as db:
            confirm_entity(db, target_type, target_id, entity_id)

    def unlink_confirmed(self, target_type, target_id, entity_id):
        if target_type not in ('item', 'physical_release', 'digital_source'):
            raise ValueError('Unsupported metadata link target.')
        relationship = 'confirmed-' + ('work' if target_type == 'item' else 'release')
        with self.connect() as db:
            return db.execute('DELETE FROM metadata_links WHERE target_type=? AND target_id=? AND entity_id=? AND relationship=?',
                              (target_type, target_id, entity_id, relationship)).rowcount

    def links(self, target_type, target_id):
        with self.connect() as db:
            return [dict(row) for row in db.execute('SELECT l.*,e.level,e.title,e.year,e.kind FROM metadata_links l JOIN metadata_entities e ON e.id=l.entity_id WHERE l.target_type=? AND l.target_id=? ORDER BY l.relationship,l.confirmed_at', (target_type, target_id))]
