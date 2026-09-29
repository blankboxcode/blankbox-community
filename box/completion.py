"""Household completion sets. Reference membership is reviewed metadata, never retail inventory."""
from __future__ import annotations

import json
import re
import uuid

from collecting import clean_target, format_key, ownership, title_key


def _set_id(value):
    return isinstance(value, str) and re.fullmatch(r'set-[0-9a-f]{32}', value) is not None


def save_set(db, data, timestamp):
    name = str(data.get('name') or '').strip()
    kind = data.get('mediaKind')
    members = data.get('members')
    if not 1 <= len(name) <= 120 or kind not in ('movie', 'tv', 'music', 'book', 'comic', 'game'):
        raise ValueError('Give the set a name and supported media type.')
    if not isinstance(members, list) or not 1 <= len(members) <= 200:
        raise ValueError('A completion set needs 1 to 200 titles.')
    cleaned = []
    seen = set()
    for member in members:
        if not isinstance(member, dict):
            raise ValueError('Review each completion-set title.')
        target = clean_target({**member, 'kind': kind})
        work_id = member.get('workId') or None
        if work_id is not None:
            if not isinstance(work_id, str):
                raise ValueError('Review the metadata work identity before saving this set.')
            row = db.execute("SELECT 1 FROM metadata_entities WHERE id=? AND level='work' AND kind=?", (work_id, kind)).fetchone()
            if not row:
                raise ValueError('Review the metadata work identity before saving this set.')
        # Distinct works can share a title, year, and format; only exact repeats collapse.
        key = (title_key(target['title']), target['year'], target['format'], work_id)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append((target, work_id))
    identifier = data.get('id')
    if identifier is not None:
        if not _set_id(identifier) or not db.execute("SELECT 1 FROM completion_sets WHERE id=? AND kind='custom'", (identifier,)).fetchone():
            raise ValueError('Choose an editable custom set.')
        db.execute('UPDATE completion_sets SET name=?,media_kind=?,updated_at=? WHERE id=?', (name, kind, timestamp, identifier))
        db.execute('DELETE FROM completion_members WHERE set_id=?', (identifier,))
    else:
        identifier = 'set-' + uuid.uuid4().hex
        db.execute('INSERT INTO completion_sets(id,name,kind,media_kind,source,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',
                   (identifier, name, 'custom', kind, 'owner', timestamp, timestamp))
    for position, (target, work_id) in enumerate(cleaned):
        db.execute('INSERT INTO completion_members(set_id,position,title,title_key,year,desired_format,work_id) VALUES(?,?,?,?,?,?,?)',
                   (identifier, position, target['title'], title_key(target['title']), target['year'], target['format'], work_id))
    # Owner-approved organizing provenance, never an external completeness claim.
    if data.get('recommendationSource'):
        source = data['recommendationSource']
        if not isinstance(source, str) or len(source) > 160:
            raise ValueError('Choose a valid collection reference source.')
        db.execute('UPDATE completion_sets SET source=? WHERE id=?', (source, identifier))
    return identifier


def remove_set(db, identifier):
    if not _set_id(identifier):
        raise ValueError('Choose a completion set.')
    return db.execute('DELETE FROM completion_sets WHERE id=?', (identifier,)).rowcount > 0


def set_member_ignored(db, identifier, position, ignored):
    if not _set_id(identifier) or not isinstance(position, int) or isinstance(position, bool) or position < 0 or not isinstance(ignored, bool):
        raise ValueError('Choose a completion-set title and ignored state.')
    return db.execute('UPDATE completion_members SET ignored=? WHERE set_id=? AND position=?',
                      (int(ignored), identifier, position)).rowcount > 0


def _linked_ownership(db, member):
    work_id = member['work_id']
    if not work_id:
        return None
    # A household item's own local work identifies it as surely as a confirmed reference work.
    rows = db.execute("SELECT i.id,i.data,l.relationship FROM metadata_links l JOIN items i ON i.id=l.target_id WHERE l.target_type='item' AND l.relationship IN ('confirmed-work','local-work') AND l.entity_id=?", (work_id,)).fetchall()
    if not rows:
        return None
    items = list({row[0]: json.loads(row[1]) for row in rows}.values())
    sources = [source for item in items for source in item.get('sources', []) if source.get('type') == 'physical']
    desired = member['desired_format']
    status = 'owned-format' if sources and (desired == 'Any' or any(format_key(source.get('label')) == format_key(desired) for source in sources)) else 'owned-other-format' if sources else 'library-only'
    basis = 'confirmed-work' if any(row[2] == 'confirmed-work' for row in rows) else 'local-work'
    return {'status': status, 'itemIds': [item['id'] for item in items], 'matchBasis': basis}


def list_sets(db, indexed_items, targets):
    wanted = {}
    for target in targets:
        if target.get('season'):
            continue  # A wanted season is not a wanted whole series.
        key = (target['kind'], title_key(target['title']), target['year'], target['format'])
        wanted.setdefault(key, set()).add(target.get('workId'))
        wanted.setdefault((target['kind'],title_key(target['title']),target['year'],'Any'),set()).add(target.get('workId'))
    result = []
    for row in db.execute('SELECT * FROM completion_sets ORDER BY updated_at DESC,name COLLATE NOCASE'):
        entry = dict(row)
        member_rows = [dict(member) for member in db.execute('SELECT * FROM completion_members WHERE set_id=? ORDER BY position', (entry['id'],))]
        member_keys = {}
        for member in member_rows:
            key = (member['title_key'], member['year'], member['desired_format'])
            member_keys.setdefault(key, set()).add(member['work_id'])
        ambiguous_keys = {key for key, work_ids in member_keys.items() if len(work_ids) > 1}
        members = []
        for member in member_rows:
            candidate = {'title': member['title'], 'kind': entry['media_kind'], 'year': member['year'], 'format': member['desired_format']}
            linked = _linked_ownership(db, member)
            if linked:
                owned = linked
            else:
                owned = ownership(candidate, indexed_items)
                if member['work_id'] and owned['status'] != 'missing':
                    # Title/year may point to a different work; do not certify the
                    # explicit reference identity without a household work link.
                    owned = {**owned, 'status': owned['status'] if owned['status'].startswith('possible-') else 'possible-' + owned['status'], 'matchBasis': 'title-year-hint'}
            status = owned['status']
            key = (member['title_key'], member['year'], member['desired_format'])
            intent_ids = wanted.get((entry['media_kind'], *key), set())
            intent_ambiguous = key in ambiguous_keys and bool(intent_ids) and member['work_id'] not in intent_ids
            is_wanted = bool(intent_ids) and not intent_ambiguous and (not member['work_id'] or member['work_id'] in intent_ids or None in intent_ids and key not in ambiguous_keys)
            outcome = 'ignored' if member['ignored'] else 'owned' if status == 'owned-format' else 'library' if status=='library-only' and member['desired_format']=='Any' and entry['source'].startswith(('installed-packs:','household-sources:')) else 'wanted' if is_wanted else 'review' if intent_ambiguous or status.startswith('possible-') else 'missing'
            members.append({'position': member['position'], 'title': member['title'], 'kind': entry['media_kind'], 'year': member['year'], 'format': member['desired_format'], 'workId': member['work_id'], 'ignored': bool(member['ignored']), 'outcome': outcome, 'ownershipStatus': status, 'itemIds': owned['itemIds'], 'matchBasis': owned.get('matchBasis', 'title-year'), 'intentMatchAmbiguous': intent_ambiguous})
        result.append({'id': entry['id'], 'name': entry['name'], 'kind': entry['kind'], 'mediaKind': entry['media_kind'], 'source': entry['source'], 'sourceVersion': entry['source_version'], 'sourceLicense': entry['source_license'], 'createdAt': entry['created_at'], 'updatedAt': entry['updated_at'], 'members': members})
    return result
