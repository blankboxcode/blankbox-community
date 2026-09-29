"""Local collection views and owner activity. No media or provider writes."""
import json
import re
import uuid
from datetime import datetime, timezone
from collecting import format_key

STATUSES = ('not-started', 'in-progress', 'completed')
KINDS = ('movie', 'tv', 'music', 'photo', 'home-video', 'book', 'comic', 'game', 'file')
COLLECTION_KINDS = ('manual', 'series', 'genre', 'seasonal', 'smart')


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def labels(value):
    if not isinstance(value, list) or len(value) > 30:
        raise ValueError('Use up to 30 labels.')
    result = {}
    for label in value:
        if not isinstance(label, str) or not 1 <= len(label.strip()) <= 80:
            raise ValueError('Use labels of 1–80 characters.')
        result.setdefault(label.strip().casefold(), label.strip())
    return list(result.values())


def genres(item):
    return list(dict.fromkeys([part.strip() for part in re.split(r'[·,;|]', item.get('genre') or '') if part.strip()] + item.get('customGenres', []) + item.get('collectionGenres', [])))


def clean_rules(value):
    if not isinstance(value, dict) or set(value) - {'kinds', 'genres', 'formats', 'status', 'yearFrom', 'yearTo'}:
        raise ValueError('Choose supported collection rules.')
    result = {}
    for field in ('kinds', 'genres', 'formats'):
        result[field] = labels(value.get(field, []))
    if set(result['kinds']) - set(KINDS):
        raise ValueError('Choose valid media types.')
    result['status'] = value.get('status', '')
    if result['status'] not in ('', *STATUSES):
        raise ValueError('Choose a valid activity status.')
    for field in ('yearFrom', 'yearTo'):
        year = value.get(field)
        if year is not None and (type(year) is not int or not 1800 <= year <= 2200):
            raise ValueError('Use a year between 1800 and 2200.')
        result[field] = year
    if result['yearFrom'] and result['yearTo'] and result['yearFrom'] > result['yearTo']:
        raise ValueError('The first year must precede the last year.')
    return result


def season_day(value):
    if value in ('', None):
        return ''
    if not isinstance(value, str) or not re.fullmatch(r'\d{2}-\d{2}', value):
        raise ValueError('Use month-day dates, such as 10-01.')
    try:
        datetime.strptime('2000-' + value, '%Y-%m-%d')
    except ValueError as error:
        raise ValueError('Use a valid month and day.') from error
    return value


def season_active(start, end, day):
    if not start or not end:
        return True
    return start <= day <= end if start <= end else day >= start or day <= end


def activity_states(db):
    # Episode events never mark the entire series completed.
    rows = db.execute("SELECT item_id,status,created_at,id FROM activity_events WHERE rowid IN (SELECT MAX(rowid) FROM activity_events WHERE undone_at IS NULL AND episode_key='' GROUP BY item_id)")
    return {row['item_id']: {'status': row['status'], 'updatedAt': row['created_at'], 'eventId': row['id']} for row in rows}


def matches(item, rules, states):
    if rules['kinds'] and item['kind'] not in rules['kinds']:
        return False
    if rules['genres'] and not {label.casefold() for label in rules['genres']} & {label.casefold() for label in genres(item)}:
        return False
    if rules['formats'] and not {format_key(label) for label in rules['formats']} & {format_key(source.get('label', '')) for source in item.get('sources', []) if source.get('type') == 'physical'}:
        return False
    if rules['status'] and states.get(item['id'], {}).get('status', 'not-started') != rules['status']:
        return False
    year = item.get('year')
    return not ((rules['yearFrom'] and (not year or year < rules['yearFrom'])) or (rules['yearTo'] and (not year or year > rules['yearTo'])))


def list_collections(db, items, states=None, day=None):
    from completion import list_sets
    from collecting import list_targets, ownership_index
    states = activity_states(db) if states is None else states
    available = {item['id']: item for item in items if not item.get('sample')}
    members = {}
    for row in db.execute('SELECT collection_id,item_id FROM library_collection_members ORDER BY position,rowid'):
        members.setdefault(row['collection_id'], []).append(row['item_id'])
    result = []
    planned={entry['id']:entry for entry in list_sets(db,ownership_index(items),list_targets(db))} if db.execute("SELECT 1 FROM library_collections WHERE data LIKE '%completionSetId%' LIMIT 1").fetchone() else {}
    for row in db.execute('SELECT id,data FROM library_collections ORDER BY rowid DESC'):
        collection = json.loads(row['data'])
        explicit = [identifier for identifier in members.get(row['id'], []) if identifier in available]
        if collection['kind'] in ('manual', 'series'):
            ids=explicit
        else:
            ids=[]
            for identifier,item in available.items():
                fallback=collection.get('referenceGenres',{}).get(identifier,[])
                if fallback and not item.get('genre') and 'genre' not in item.get('metadataOverrides',[]):
                    item={**item,'collectionGenres':list(dict.fromkeys([*item.get('collectionGenres',[]),*fallback]))}
                if matches(item,collection['rules'],states):ids.append(identifier)
        completion=planned.get(collection.get('completionSetId'))
        if completion:
            included=[m for m in completion['members'] if not m['ignored']]
            linked=[m for m in included if m['itemIds'] and not m['ownershipStatus'].startswith('possible-')]
            ids=list(dict.fromkeys([*(i for i in ids if i not in collection.get('recommendationMemberIds',[])), *(i for m in linked for i in m['itemIds'] if i in available)]))
            collection['completionCounts']={'library':len(linked),'known':len(included),'wanted':sum(m['outcome']=='wanted' for m in included),'review':sum(m['outcome']=='review' for m in included)}
        result.append({**collection, 'memberIds': explicit, 'itemIds': ids, 'active': season_active(collection['startDay'], collection['endDay'], day or datetime.now().strftime('%m-%d'))})
    return result


def save_collection(db, data, available=None):
    identifier = data.get('id')
    existing = db.execute('SELECT data FROM library_collections WHERE id=?', (identifier,)).fetchone() if isinstance(identifier, str) else None
    if identifier is not None and not existing:
        raise ValueError('Collection changed. Reopen it before saving.')
    if not existing and db.execute('SELECT COUNT(*) FROM library_collections').fetchone()[0] >= 500:
        raise ValueError('The household collection limit is 500.')
    name, kind = data.get('name'), data.get('kind')
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120 or kind not in COLLECTION_KINDS:
        raise ValueError('Enter a collection name and type.')
    rules = clean_rules(data.get('rules', {}))
    member_ids = data.get('memberIds', [])
    if not isinstance(member_ids, list) or len(member_ids) > 10000 or any(not isinstance(value, str) for value in member_ids) or len(set(member_ids)) != len(member_ids):
        raise ValueError('Review the selected collection members.')
    if available is None:available = {row[0] for row in db.execute('SELECT id FROM items')}
    if set(member_ids) - available:
        raise ValueError('A selected title is no longer in the library.')
    if kind not in ('manual', 'series') and member_ids:
        raise ValueError('Rule collections calculate membership automatically.')
    start, end = season_day(data.get('startDay')), season_day(data.get('endDay'))
    if bool(start) != bool(end) or kind != 'seasonal' and (start or end):
        raise ValueError('Use both dates for a seasonal collection.')
    when = timestamp()
    identifier = identifier or uuid.uuid4().hex
    record = {'id': identifier, 'name': name.strip(), 'kind': kind, 'rules': rules, 'startDay': start, 'endDay': end, 'createdAt': json.loads(existing[0])['createdAt'] if existing else when, 'updatedAt': when}
    if existing:
        record.update({field: value for field, value in json.loads(existing[0]).items() if field in ('completionSetId', 'recommendationId', 'referenceGenres', 'recommendationBasis','recommendationMemberIds')})
        if record.get('completionSetId') and kind in ('manual','series'):
            from completion import list_sets
            from collecting import list_targets,ownership_index
            items=[json.loads(row[0]) for row in db.execute('SELECT data FROM items')]
            entry=next((e for e in list_sets(db,ownership_index(items),list_targets(db)) if e['id']==record['completionSetId']),None)
            old_ids={row[0] for row in db.execute('SELECT item_id FROM library_collection_members WHERE collection_id=?',(identifier,))}
            if entry:old_ids.update(i for member in entry['members'] for i in member['itemIds'])
            # Explicit removal from an accepted collection also excludes that title goal.
            for member in entry['members'] if entry else []:
                if set(member['itemIds']) & (old_ids-set(member_ids)):
                    db.execute('UPDATE completion_members SET ignored=1 WHERE set_id=? AND position=?',(entry['id'],member['position']))
    db.execute('INSERT INTO library_collections VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data', (identifier, json.dumps(record)))
    db.execute('DELETE FROM library_collection_members WHERE collection_id=?', (identifier,))
    db.executemany('INSERT INTO library_collection_members VALUES(?,?,?)', [(identifier, item_id, position) for position, item_id in enumerate(member_ids)])
    return identifier


def record_activity(db, item, data, profile_id='household'):
    status, identifier = data.get('status'), data.get('eventId')
    if status not in STATUSES or not isinstance(identifier, str) or not re.fullmatch(r'[A-Za-z0-9-]{1,80}', identifier):
        raise ValueError('Choose an activity status and event ID.')
    episode = data.get('episodeKey', '')
    if not isinstance(episode, str) or episode and (item['kind'] != 'tv' or not re.fullmatch(r'(?:S(?:0|[1-9]\d{0,2})|S\d{1,3}E\d{1,4})', episode)):
        raise ValueError('Choose a TV season such as S1 or episode such as S1E1.')
    references = {}
    for key, choices in (('sourceId', {source.get('id') for source in item.get('sources', [])}), ('versionId', {version['id'] for version in item.get('versions', [])})):
        value = data.get(key)
        if value is not None and (not isinstance(value, str) or value not in choices):
            raise ValueError('The selected edition or source is no longer available.')
        references[key] = value
    old = db.execute('SELECT item_id,status,episode_key FROM activity_events WHERE id=?', (identifier,)).fetchone()
    if old:
        if tuple(old) != (item['id'], status, episode):
            raise ValueError('This activity event ID has already been used.')
        return identifier
    db.execute('INSERT INTO activity_events(id,item_id,status,episode_key,source_id,version_id,profile_id,origin,created_at) VALUES(?,?,?,?,?,?,?,?,?)',
               (identifier, item['id'], status, episode, references['sourceId'], references['versionId'], profile_id, 'manual', timestamp()))
    return identifier


def activity_history(db, item_id, limit=50, scope=None):
    query='SELECT * FROM activity_events WHERE item_id=?';params=[item_id]
    if scope is not None:
        query+=' AND episode_key=?';params.append(scope)
    query+=' ORDER BY rowid DESC LIMIT ?';params.append(limit)
    return [{'id': row['id'], 'itemId': row['item_id'], 'status': row['status'], 'episodeKey': row['episode_key'], 'sourceId': row['source_id'], 'versionId': row['version_id'], 'profileId': row['profile_id'], 'origin': row['origin'], 'createdAt': row['created_at'], 'undoneAt': row['undone_at']} for row in db.execute(query,params)]


def merge_collection_activity(db, target_id, incoming_id):
    for row in db.execute('SELECT collection_id,position FROM library_collection_members WHERE item_id=?', (incoming_id,)).fetchall():
        db.execute('INSERT OR IGNORE INTO library_collection_members VALUES(?,?,?)', (row['collection_id'], target_id, row['position']))
    db.execute('UPDATE activity_events SET item_id=? WHERE item_id=?', (target_id, incoming_id))


def hidden_organization(db, item_id):
    return {'events': [dict(row) for row in db.execute('SELECT * FROM activity_events WHERE item_id=?', (item_id,))],
            'memberships': [dict(row) for row in db.execute('SELECT collection_id,position FROM library_collection_members WHERE item_id=?', (item_id,))]}


def restore_organization(db, item_id, saved):
    for row in saved.get('memberships', []):
        if db.execute('SELECT 1 FROM library_collections WHERE id=?', (row['collection_id'],)).fetchone():
            db.execute('INSERT OR IGNORE INTO library_collection_members VALUES(?,?,?)', (row['collection_id'], item_id, row['position']))
    for row in saved.get('events', []):
        db.execute('INSERT OR IGNORE INTO activity_events(id,item_id,status,episode_key,source_id,version_id,profile_id,origin,created_at,undone_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
                   (row['id'], item_id, row['status'], row['episode_key'], row['source_id'], row['version_id'], row['profile_id'], row['origin'], row['created_at'], row['undone_at']))
