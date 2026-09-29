"""Owner collection intentions, separate from owned catalog items."""
from __future__ import annotations

import re
import uuid
import json


KINDS = {'movie', 'tv', 'music', 'book', 'comic', 'game'}
FORMATS_BY_KIND = {
    'movie': {'Any', '4K UHD Blu-ray', 'Blu-ray', 'DVD', 'VHS', 'Betamax', 'LaserDisc', 'Other'},
    'tv': {'Any', '4K UHD Blu-ray', 'Blu-ray', 'DVD', 'VHS', 'Betamax', 'LaserDisc', 'Other'},
    'music': {'Any', 'CD', 'Vinyl', 'Cassette', '8-track', 'MiniDisc', 'Other'},
    'book': {'Any', 'Book', 'Hardcover', 'Paperback', 'Magazine', 'Other'},
    'comic': {'Any', 'Comic', 'Other'},
    'game': {'Any', 'Game', 'Other'},
}


def clean_target(data):
    title = str(data.get('title') or '').strip()
    if not 1 <= len(title) <= 250:
        raise ValueError('Enter a title up to 250 characters.')
    kind = str(data.get('kind') or 'movie')
    if kind not in KINDS:
        raise ValueError('Choose a supported media type.')
    desired_format = str(data.get('format') or 'Any')
    if desired_format not in FORMATS_BY_KIND[kind]:
        raise ValueError('Choose a format for this media type.')
    year = data.get('year')
    if year not in (None, ''):
        year = int(year)
        if not 1800 <= year <= 2200:
            raise ValueError('Enter a valid release year.')
    else:
        year = None
    season = data.get('season') or None
    if season is not None and (kind != 'tv' or not isinstance(season, str) or season not in ('specials', 'complete-series') and not re.fullmatch(r'[1-9][0-9]?', season)):
        raise ValueError('Choose a TV season from 1 to 99, Specials, or Complete series.')
    edition = data.get('edition') or ''
    if not isinstance(edition, str) or len(edition.strip()) > 120:
        raise ValueError('Enter an edition up to 120 characters.')
    return {'title': title, 'kind': kind, 'year': year, 'format': desired_format, 'season': season, 'edition': edition.strip()}


def list_targets(db):
    targets = [dict(row) for row in db.execute('SELECT id,title,kind,year,desired_format AS format,edition,season,work_id AS workId,release_id AS releaseId,created_at AS createdAt FROM collecting_targets ORDER BY created_at DESC,title COLLATE NOCASE')]
    identifiers = {}
    for row in db.execute("SELECT DISTINCT i.entity_id,i.namespace,i.value FROM metadata_identifiers i JOIN collecting_targets t ON t.release_id=i.entity_id WHERE i.namespace IN ('isbn','upc-ean') ORDER BY i.namespace,i.value"):
        identifiers.setdefault(row[0], {'namespace': row[1], 'value': row[2]})
    return [{**target, **({'identifier': identifiers[target['releaseId']]} if target['releaseId'] in identifiers else {})} for target in targets]


def _confirmed_release(db, data, target, work_id):
    release_id = data.get('releaseId')
    if release_id is None:
        return None, work_id
    row = db.execute("SELECT * FROM metadata_entities WHERE id=? AND level='release'", (release_id,)).fetchone() if isinstance(release_id, str) else None
    if not row or row['kind'] != target['kind'] or format_key(row['format']) != format_key(target['format']) or (row['edition'] or '') != target['edition'] or (row['season'] or None) != target['season']:
        raise ValueError('The selected reference edition does not match this intention.')
    if work_id and work_id != row['work_id']:
        raise ValueError('The selected edition belongs to a different work.')
    work_id = _confirmed_work(db, {'workId': row['work_id']}, target)
    return release_id, work_id


def _confirmed_work(db, data, target):
    work_id = data.get('workId')
    if work_id is None:
        return None
    if not isinstance(work_id, str):
        raise ValueError('Review the selected metadata work.')
    row = db.execute("SELECT id,title,kind,year FROM metadata_entities WHERE id=? AND level='work'", (work_id,)).fetchone()
    if not row or row['kind'] != target['kind'] or title_key(row['title']) != title_key(target['title']) or row['year'] and target['year'] and row['year'] != target['year']:
        raise ValueError('The selected metadata work does not match this intention.')
    return work_id


def add_target(db, data, timestamp):
    target = clean_target(data)
    work_id = _confirmed_work(db, data, target)
    release_id, work_id = _confirmed_release(db, data, target, work_id)
    # An exact saved intent is idempotent, including the desired format.
    key = (target['kind'], title_key(target['title']), target['year'], target['format'], target['season'], target['edition'], release_id)
    row = db.execute('SELECT id FROM collecting_targets WHERE kind=? AND title_key=? AND year IS ? AND desired_format=? AND season IS ? AND edition=? AND release_id IS ?', key).fetchone()
    if row:
        existing = db.execute('SELECT work_id FROM collecting_targets WHERE id=?', (row[0],)).fetchone()[0]
        if existing and work_id and existing != work_id:
            raise ValueError('This title has a different confirmed work identity. Review the intention.')
        if work_id and not existing:
            db.execute('UPDATE collecting_targets SET work_id=? WHERE id=?', (work_id, row[0]))
        return {'id': row[0], 'alreadySaved': True}
    identifier = 'intent-' + uuid.uuid4().hex
    result = db.execute('INSERT OR IGNORE INTO collecting_targets(id,title,title_key,kind,year,desired_format,created_at,work_id,season,edition,release_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                        (identifier, target['title'], title_key(target['title']), target['kind'], target['year'], target['format'], timestamp, work_id, target['season'], target['edition'], release_id))
    if result.rowcount:
        return {'id': identifier, 'alreadySaved': False}
    saved = db.execute('SELECT id FROM collecting_targets WHERE kind=? AND title_key=? AND year IS ? AND desired_format=? AND season IS ? AND edition=? AND release_id IS ?', key).fetchone()
    return {'id': saved[0], 'alreadySaved': True}


def remove_target(db, identifier):
    if not isinstance(identifier, str) or not re.fullmatch(r'intent-[0-9a-f]{32}', identifier):
        raise ValueError('Choose an intention to remove.')
    result = db.execute('DELETE FROM collecting_targets WHERE id=?', (identifier,))
    return result.rowcount > 0


def update_target(db, data):
    identifier = data.get('id')
    if not isinstance(identifier, str) or not re.fullmatch(r'intent-[0-9a-f]{32}', identifier):
        raise ValueError('Choose an intention to edit.')
    target = clean_target(data)
    current = db.execute('SELECT * FROM collecting_targets WHERE id=?', (identifier,)).fetchone()
    if not current:
        return False
    work_id = _confirmed_work(db, data, target) if 'workId' in data else current['work_id'] if current['kind'] == target['kind'] and title_key(current['title']) == title_key(target['title']) and current['year'] == target['year'] else None
    unchanged = work_id == current['work_id'] and target['format'] == current['desired_format'] and target['edition'] == current['edition'] and target['season'] == current['season']
    release_id, work_id = _confirmed_release(db, {'releaseId': data.get('releaseId', current['release_id'] if unchanged else None)}, target, work_id)
    result = db.execute('UPDATE collecting_targets SET title=?,title_key=?,kind=?,year=?,desired_format=?,work_id=?,season=?,edition=?,release_id=? WHERE id=?',
                        (target['title'], title_key(target['title']), target['kind'], target['year'], target['format'], work_id, target['season'], target['edition'], release_id, identifier))
    return result.rowcount > 0


def intention_ownership(db, target, indexed_items):
    if target.get('releaseId'):
        rows = db.execute("SELECT DISTINCT p.item_id FROM metadata_links l JOIN package_contents p ON p.release_id=l.target_id WHERE l.target_type='physical_release' AND l.entity_id=?", (target['releaseId'],)).fetchall()
        if rows:
            return {'status': 'owned-edition', 'itemIds': [r[0] for r in rows], 'matchBasis': 'confirmed-release'}
    work_id = target.get('workId')
    if work_id:
        rows = db.execute("SELECT i.data FROM metadata_links l JOIN items i ON i.id=l.target_id WHERE l.target_type='item' AND l.relationship IN ('confirmed-work','local-work') AND l.entity_id=?", (work_id,)).fetchall()
        if rows:
            items = [json.loads(row[0]) for row in rows]
            physical = [source for item in items for source in item.get('sources', []) if source.get('type') == 'physical']
            status = physical_status(physical, target)
            if target.get('releaseId') and status == 'owned-format':
                status = 'possible-owned-edition'
            return {'status': status, 'itemIds': [item['id'] for item in items], 'matchBasis': 'confirmed-work'}
    result = ownership(target, indexed_items)
    if work_id and result['status'] != 'missing':
        result = {**result, 'status': result['status'] if result['status'].startswith('possible-') else 'possible-' + result['status'], 'matchBasis': 'title-year-hint'}
    return result


def title_key(value):
    """Planner match key that ignores punctuation and spacing ('Spider-Man' == 'Spiderman').

    It is stored in collecting_targets and completion_members and backs their unique
    index, so changing it needs a migration. It only proposes matches; identity comes
    from confirmed metadata work links, not from this key or metadata.normalize_title.
    """
    return ''.join(character for character in value.casefold() if character.isalnum())


def format_key(value):
    key = title_key(str(value or ''))
    return '4kuhdbluray' if key == '4kuhd' else key


def physical_status(physical, target):
    edition = target.get('edition')
    wanted = target.get('format', 'Any')
    if physical and (edition or target.get('releaseId')) and wanted != 'Any':
        matching = [source for source in physical if format_key(source.get('label')) == format_key(wanted)]
        generic_book = target.get('kind') == 'book' and wanted in ('Book', 'Hardcover', 'Paperback') and any(source.get('label') in ('Book', 'Hardcover', 'Paperback') and 'Book' in (wanted, source.get('label')) for source in physical)
        if not matching:
            return 'possible-owned-edition' if generic_book else 'owned-other-format'
        physical = matching
    if edition:
        exact = [source for source in physical if (source.get('edition') or '').casefold() == edition.casefold()]
        if exact:
            physical = exact
        elif any(not source.get('edition') for source in physical):
            return 'possible-owned-edition'
        elif physical:
            return 'owned-other-edition'
    season = target.get('season')
    if season:
        matches = [source for source in physical if source.get('season') == 'complete-series' or season != 'complete-series' and source.get('season') == season]
        if not matches:
            if any(not source.get('season') for source in physical):return 'possible-owned-season'
            return 'missing-season' if physical else 'library-only'
        physical = matches
    return 'owned-format' if physical and (wanted == 'Any' or any(format_key(source.get('label')) == format_key(wanted) for source in physical)) else 'owned-other-format' if physical else 'library-only'


def ownership_index(items):
    index = {}
    for item in items:
        index.setdefault((item.get('kind'), title_key(item.get('title', ''))), []).append(item)
    return index


def ownership(candidate, items):
    """Conservative status: exact title/year only; unknown years need review."""
    index = items if isinstance(items, dict) else ownership_index(items)
    matches = index.get((candidate['kind'], title_key(candidate['title'])), [])
    if not matches:
        return {'status': 'missing', 'itemIds': []}
    if candidate.get('year'):
        matches = [item for item in matches if item.get('year') in (None, candidate['year'])]
    if not matches:
        return {'status': 'possible-year-mismatch', 'itemIds': [item['id'] for item in index[(candidate['kind'], title_key(candidate['title']))]]}
    physical = [source for item in matches for source in item.get('sources', []) if source.get('type') == 'physical']
    status = physical_status(physical, candidate)
    if any(item.get('year') is None for item in matches) or candidate.get('year') is None:
        status = 'possible-' + status
    return {'status': status, 'itemIds': [item['id'] for item in matches]}
