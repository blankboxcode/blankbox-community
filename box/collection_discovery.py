"""Editable collection recommendations derived from local references, never identity merges."""
from __future__ import annotations

from collections import defaultdict, OrderedDict
import hashlib
import json
import re
import sqlite3
import threading
import unicodedata

from library_collections import genres
from metadata_indexed_pack import _db


def key(value):
    folded = unicodedata.normalize('NFKD', str(value)).casefold()
    return ' '.join(re.findall(r'[^\W_]+', ''.join(c for c in folded if not unicodedata.combining(c))))


def roots(title):
    """Title patterns are proposals; genres/keywords never prove a franchise."""
    result = set()
    for separator in (':', ' and ', ' & '):
        before, found, _ = title.partition(separator)
        if found and len(key(before)) >= 5:
            result.add(key(before))
    numbered = re.sub(r'\s+(?:(?:part|vol\.?|volume|chapter)\s*)?(?:\d+|II|III|IV|V|VI|VII|VIII|IX|X)(?:\s*[:—-].*)?$', '', title, flags=re.I)
    if numbered != title and len(key(numbered)) >= 5:
        result.add(key(numbered))
    tokens = key(title).split()
    # A common two-word prefix is useful evidence, but stays explicitly reviewable.
    if len(tokens) >= 3 and tokens[0] not in ('the', 'a', 'an') and tokens[1] not in ('of', 'in', 'on', 'and', 'to', 'is', 'at', 'with'):
        result.add(' '.join(tokens[:2]))
    return {value for value in result if value not in ('the movie', 'the film', 'the story', 'the last', 'the first')}


def group_id(kind, basis, name):
    return 'recommendation-' + hashlib.sha256(f'{kind}:{basis}:{key(name)}'.encode()).hexdigest()[:24]


class CollectionReferences:
    """Rebuildable reference-only SQLite cache, separate from household identity.

    Cache compact organizing clues only. Pack removal invalidates it; confirmed
    facts and owner-approved collection snapshots live in the household catalog.
    """
    def __init__(self, packs, cache=None, operation_lock=None):
        from pathlib import Path
        self.packs = packs
        self.cache = Path(cache) if cache else packs.root.parent / 'collection-reference-cache.sqlite3'
        self.lock = threading.RLock()
        self.stamp = None
        self.index = None
        self.coverage = []
        self.worker = None
        self.pending = False
        self.failure = ''
        self.deferred = False
        self.operation_lock = operation_lock or threading.Lock()
        self.prepare_lock = threading.Lock()
        self.match_cache = OrderedDict()
        self.projection_cache = OrderedDict()
        self.recommendation_cache = None

    def ready(self):
        """Large first indexes build in the background; basic library reads stay fast."""
        with self.prepare_lock:
            if self.pending or self.failure:
                return False
            installed = self.packs.indexed.list()
            stamp = self.pack_stamp(installed)
            if self.stamp == stamp:
                return self.index is not None
            if sum(m['recordCount'] for m in installed) > 10000:
                self.pending = True
                def build():
                    try:
                        with self.operation_lock:self.refresh()
                    except (sqlite3.Error,OSError,ValueError,TypeError):self.failure='Collection references could not be indexed. Your local collections remain available.'
                    finally:self.pending=False
                self.worker=threading.Thread(target=build,daemon=True,name='collection-reference-index')
                self.worker.start()
                return False
        try:self.refresh()
        except (sqlite3.Error,OSError,ValueError,TypeError):
            self.failure='Collection references could not be indexed. Your local collections remain available.'
            return False
        return self.index is not None

    @staticmethod
    def pack_stamp(installed):
        return json.dumps({'cacheFormat':3,'packs':[(m['id'],m['version'],m['databaseSha256']) for m in installed]},sort_keys=True)

    def refresh(self):
        import os
        installed = self.packs.indexed.available()
        stamp = self.pack_stamp([m for m,_ in installed])
        with self.lock:
            if stamp == self.stamp:
                return
            self.match_cache.clear()
            self.projection_cache.clear()
            self.recommendation_cache = None
            if self.index:
                self.index.close()
                self.index = None
            if self.cache.is_file():
                try:
                    db = sqlite3.connect(self.cache,check_same_thread=False)
                    stored = dict(db.execute('SELECT key,value FROM meta'))
                    if stored.get('stamp') == stamp and db.execute('PRAGMA quick_check').fetchone()[0] == 'ok':
                        self.index, self.stamp, self.coverage = db, stamp, json.loads(stored['coverage'])
                        self.index.row_factory = sqlite3.Row
                        return
                    db.close()
                except (sqlite3.Error, OSError, ValueError):
                    pass
            stage = self.cache.with_suffix('.building')
            stage.unlink(missing_ok=True)
            coverage = []
            with sqlite3.connect(stage) as target:
                target.executescript("""PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;
                    CREATE TABLE refs(id TEXT PRIMARY KEY,kind TEXT,title TEXT,year INTEGER,genre TEXT,identifiers TEXT,directors TEXT,studios TEXT,source TEXT,version TEXT);
                    CREATE TABLE aliases(kind TEXT,title_key TEXT,id INTEGER);
                    CREATE TABLE record_aliases(alias TEXT PRIMARY KEY,id INTEGER);
                    CREATE TABLE groups(kind TEXT,basis TEXT,root TEXT,id INTEGER);
                    CREATE TABLE identifiers(kind TEXT,namespace TEXT,value TEXT,id INTEGER);
                    CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT);
                """)
                for manifest, path in installed:
                    tagged = 0
                    with _db(path) as db:
                        rich = manifest['format'] in (4,5)
                        query = """SELECT w.record_id,w.title,w.original_title,w.year,
                            json_extract(d.fields_json,'$.genre') AS genre,
                            json_extract(d.fields_json,'$.catalogDetails.studios') AS studios,
                            json_extract(d.fields_json,'$.catalogDetails.directors') AS directors
                            FROM works w LEFT JOIN work_details d ON d.record_id=w.record_id""" if rich else """SELECT record_id,title,original_title,year,
                            NULL AS genre,NULL AS studios,NULL AS directors FROM works"""
                        for row in db.execute(query):
                            rid = 'pack:' + manifest['id'] + ':' + row['record_id']
                            tagged += bool(row['genre'])
                            cursor=target.execute('INSERT INTO refs VALUES(?,?,?,?,?,?,?,?,?,?)',
                                (rid,manifest['kind'],row['title'],row['year'],row['genre'],'[]',row['directors'] or '[]',row['studios'] or '[]',manifest['id'],manifest['version']))
                            parent_id=cursor.lastrowid
                            target.executemany('INSERT INTO aliases VALUES(?,?,?)',
                                ((manifest['kind'],alias,parent_id) for alias in {key(row['title']), key(row['original_title'] or row['title'])}))
                            if manifest['kind'] in ('movie','book','tv','comic','game'):
                                target.executemany('INSERT INTO groups VALUES(?,?,?,?)',
                                    ((manifest['kind'],'title-pattern',root,parent_id) for root in roots(row['title'])))
                            if manifest['kind'] == 'movie':
                                for studio in json.loads(row['studios'] or '[]'):
                                    if isinstance(studio,str) and 2 <= len(studio) <= 100 and not any(c in studio for c in ('[',']','\\','"')):
                                        target.execute('INSERT INTO groups VALUES(?,?,?,?)',('movie','studio',key(studio),parent_id))
                        if rich:
                            target.executemany('INSERT INTO identifiers VALUES(?,?,?,?)',
                                ((manifest['kind'],ns,value,target.execute('SELECT rowid FROM refs WHERE id=?',('pack:'+manifest['id']+':'+rid,)).fetchone()[0])
                                 for rid,ns,value in db.execute('SELECT i.record_id,i.namespace,i.value FROM record_identifiers i JOIN works w ON w.record_id=i.record_id')
                                 if ns in ('imdb','tmdb-movie','tmdb-tv','openlibrary-work','musicbrainz-release-group')))
                        if manifest['format']==5:
                            for old,canonical in db.execute('SELECT alias_id,canonical_id FROM record_aliases'):
                                row=target.execute('SELECT rowid FROM refs WHERE id=?',('pack:'+manifest['id']+':'+canonical,)).fetchone()
                                if row:target.execute('INSERT INTO record_aliases VALUES(?,?)',('pack:'+manifest['id']+':'+old,row[0]))
                        coverage.append({'id':manifest['id'],'kind':manifest['kind'],'version':manifest['version'],
                                         'works':manifest['recordCount'],'genreRecords':int(tagged)})
                target.executescript("""CREATE INDEX aliases_lookup ON aliases(kind,title_key);
                    CREATE INDEX groups_lookup ON groups(kind,basis,root);
                    CREATE INDEX groups_anchor ON groups(id);
                    CREATE INDEX identifiers_lookup ON identifiers(kind,namespace,value);
                    CREATE INDEX identifiers_parent ON identifiers(id);
                    INSERT INTO groups SELECT DISTINCT g.kind,g.basis,g.root,a.id FROM groups g JOIN aliases a ON a.kind=g.kind AND a.title_key=g.root
                    WHERE g.basis='title-pattern' AND NOT EXISTS(SELECT 1 FROM groups old WHERE old.kind=g.kind AND old.basis=g.basis AND old.root=g.root AND old.id=a.id);
                    DELETE FROM groups WHERE (kind,basis,root) IN (SELECT kind,basis,root FROM groups GROUP BY kind,basis,root HAVING COUNT(DISTINCT id)<2);
                """)
                coverage.extend({'id':m['id'],'kind':m.get('kind','music'),'version':m['version'],'works':m['recordCount'],'genreRecords':0} for m in self.packs.legacy.list())
                target.executemany('INSERT INTO meta VALUES(?,?)',[('stamp',stamp),('coverage',json.dumps(coverage))])
                target.commit()
                target.execute('VACUUM')
            os.chmod(stage,0o600)
            os.replace(stage,self.cache)
            self.index = sqlite3.connect(self.cache,check_same_thread=False)
            self.index.row_factory = sqlite3.Row
            self.stamp, self.coverage = stamp, coverage

    def record(self, row):
        record = dict(row)
        record.pop('row_id',None)
        record['genres'] = genres({'genre':row['genre']})
        record['directors'] = json.loads(row['directors'])
        record['studios'] = json.loads(row['studios'])
        record['identifiers'] = [tuple(v) for v in self.index.execute('SELECT namespace,value FROM identifiers WHERE id=?',(row['row_id'],))]
        return record

    def matching(self, item, mappings=()):
        signature=self.lookup_signature(item,mappings)
        identifiers=set(signature[-1])
        if signature in self.match_cache:
            self.match_cache.move_to_end(signature)
            return self.match_cache[signature]
        result=self._matching(item,mappings,identifiers)
        self.match_cache[signature]=result
        if len(self.match_cache)>16384:self.match_cache.popitem(last=False)
        return result

    @staticmethod
    def lookup_signature(item,mappings=()):
        identifiers={(v.get('namespace'),v.get('value')) for source in item.get('sources',[]) for v in source.get('metadataIdentifiers',[]) if isinstance(v.get('namespace'),str) and isinstance(v.get('value'),str)}
        return (item['kind'],key(item['title']),item.get('year'),tuple(sorted(mappings)),tuple(sorted(identifiers)))

    def projections(self, items, mappings):
        """Fetch compact organizing clues in bounded SQL batches, retaining no item data."""
        pending={}
        for item in items:
            signature=self.lookup_signature(item,mappings.get(item['id'],[]))
            if signature in self.projection_cache:
                self.projection_cache.move_to_end(signature)
                continue
            if signature[3] or signature[4]:
                rows,basis=self.matching(item,mappings.get(item['id'],[]))
                choices={tuple(sorted(r['genres'])) for r in rows if r['genres']} if basis!='ambiguous-reference' else set()
                self.projection_cache[signature]=(next(iter(choices)) if len(choices)==1 else (),basis if len(choices)==1 else 'unknown',tuple(r['id'] for r in rows),basis)
            elif item.get('year') is None:
                self.projection_cache[signature]=((),'unknown',(),'unknown')
            else:pending[signature]=None
        signatures=list(pending)
        for offset in range(0,len(signatures),250):
            chunk=signatures[offset:offset+250];found=defaultdict(list)
            params=[value for signature in chunk for value in signature[:3]]
            query='WITH requested(kind,title_key,year) AS (VALUES '+','.join('(?,?,?)' for _ in chunk)+''')
                SELECT q.kind,q.title_key,q.year,r.id,r.genre,r.directors
                FROM requested q JOIN aliases a ON a.kind=q.kind AND a.title_key=q.title_key
                JOIN refs r ON r.rowid=a.id AND r.year=q.year'''
            for row in self.index.execute(query,params):found[tuple(row[:3])].append(row)
            for signature in chunk:
                rows=found[signature[:3]]
                directors={tuple(sorted(map(key,json.loads(r['directors'])))) for r in rows if json.loads(r['directors'])}
                if len(directors)>1:rows=[]
                choices={tuple(sorted(genres({'genre':r['genre']}))) for r in rows if r['genre']}
                basis='title-year-candidate' if rows else 'unknown'
                self.projection_cache[signature]=(next(iter(choices)) if len(choices)==1 else (),basis if len(choices)==1 else 'unknown',tuple(r['id'] for r in rows),basis)
        while len(self.projection_cache)>131072:self.projection_cache.popitem(last=False)

    def _matching(self, item, mappings, identifiers):
        explicit = list({row['id']:self.record(row) for identifier in mappings for row in self.index.execute(
            'SELECT rowid AS row_id,* FROM refs WHERE id=? OR rowid IN (SELECT id FROM record_aliases WHERE alias=?)',(identifier,identifier))}.values())
        if explicit:
            return explicit,'ambiguous-reference' if len({r['year'] for r in explicit if r['year'] is not None})>1 else 'confirmed-reference'
        exact = {row['id']:self.record(row) for ns,value in identifiers for row in self.index.execute(
            'SELECT r.rowid AS row_id,r.* FROM identifiers i JOIN refs r ON r.rowid=i.id WHERE i.kind=? AND i.namespace=? AND i.value=?',(item['kind'],ns,value))}
        if exact:
            rows=list(exact.values())
            return rows,'ambiguous-reference' if len({r['year'] for r in rows if r['year'] is not None})>1 else 'provider-identifier'
        rows = [self.record(row) for row in self.index.execute('SELECT r.rowid AS row_id,r.* FROM aliases a JOIN refs r ON r.rowid=a.id WHERE a.kind=? AND a.title_key=? AND r.year=?',
            (item['kind'],key(item['title']),item.get('year')))] if item.get('year') is not None else []
        directors = {tuple(sorted(map(key,r['directors']))) for r in rows if r['directors']}
        return (rows,'title-year-candidate') if rows and len(directors)<=1 else ([], 'unknown')

    def genre_projection(self, items, mappings):
        if not items:return []
        if not self.ready():return [{**item,'collectionGenres':genres(item),'collectionGenreBasis':'household'} for item in items]
        with self.lock:
            result=[]
            for offset in range(0,len(items),1000):
                chunk=items[offset:offset+1000]
                self.projections([item for item in chunk if not item.get('genre') and 'genre' not in item.get('metadataOverrides',[])],mappings)
                for original in chunk:
                    item=dict(original)
                    own=genres(item)
                    if item.get('genre') or 'genre' in item.get('metadataOverrides',[]):
                        item['collectionGenres'],item['collectionGenreBasis']=own,'household'
                    else:
                        signature=self.lookup_signature(item,mappings.get(item['id'],[]))
                        clue=self.projection_cache.get(signature)
                        values,basis=clue[:2]
                        item['collectionGenres']=list(dict.fromkeys([*own,*values]))
                        item['collectionGenreBasis']=basis if values else 'household' if own else 'unknown'
                    result.append(item)
            return result

    @staticmethod
    def members(records):
        """Group visible references without changing any pack or household ID."""
        parent = {r['id']: r['id'] for r in records}
        lookup = {r['id']: r for r in records}
        def find(identifier):
            while parent[identifier] != identifier:
                parent[identifier] = parent[parent[identifier]]
                identifier = parent[identifier]
            return identifier
        tokens = {}
        for record in records:
            for token in record['identifiers']:
                token = (record['kind'], tuple(token))
                other = tokens.get(token)
                if other and (lookup[other]['year'] is None or record['year'] is None or lookup[other]['year'] == record['year']):
                    parent[find(record['id'])] = find(other)
                else:
                    tokens[token] = record['id']
        same_title = defaultdict(list)
        for record in records:
            if record['year'] is not None:
                same_title[(record['kind'], key(record['title']), record['year'])].append(record)
        for rows in same_title.values():
            directors = {tuple(sorted(map(key, r['directors']))) for r in rows if r['directors']}
            if len(directors) <= 1:
                for row in rows[1:]:
                    parent[find(row['id'])] = find(rows[0]['id'])
        merged = defaultdict(list)
        for row in records:
            merged[find(row['id'])].append(row)
        return sorted(merged.values(), key=lambda rows: (rows[0]['year'] or 9999, rows[0]['title'].casefold()))

    def recommend(self, items, mappings, targets, excluded=(), operation_owned=False):
        excluded={value for value in excluded if isinstance(value,str)}
        if not self.ready():return [g for g in self.provider_recommendations(items) if g['id'] not in excluded][:60]
        with self.lock:
            digest=hashlib.sha256()
            for item in items:
                digest.update(json.dumps([item['id'],item['kind'],item['title'],item.get('year'),mappings.get(item['id'],[]),item.get('catalogDetails',{}).get('collections',[]),
                    [(s.get('metadataIdentifiers',[]),s.get('metadataSnapshot',{}).get('catalogDetails',{}).get('collections',[])) for s in item.get('sources',[])]],sort_keys=True).encode())
            digest.update(json.dumps(targets,sort_keys=True).encode())
            digest.update(json.dumps(sorted(excluded)).encode())
            fingerprint=digest.hexdigest()
            if self.recommendation_cache and self.recommendation_cache[0]==fingerprint:
                self.deferred=False
                return self.recommendation_cache[1]
            if not operation_owned and not self.operation_lock.acquire(blocking=False):
                self.deferred=True
                return []
            self.deferred=False
            try:
                item_refs, anchors = {}, set()
                for offset in range(0,len(items),1000):
                    chunk=items[offset:offset+1000];self.projections(chunk,mappings)
                    for item in chunk:
                        signature=self.lookup_signature(item,mappings.get(item['id'],[]))
                        clue=self.projection_cache.get(signature)
                        identifiers,basis=clue[2:]
                        for identifier in identifiers:item_refs.setdefault(identifier, []).append((item['id'], basis))
                        anchors.update(identifiers)
                result = []
                group_keys=defaultdict(int)
                anchor_list=sorted(anchors)
                for offset in range(0,len(anchor_list),800):
                    chunk=anchor_list[offset:offset+800]
                    placeholders=','.join('?' for _ in chunk)
                    for row in self.index.execute(f'SELECT g.kind,g.basis,g.root,COUNT(DISTINCT g.id) FROM groups g JOIN refs r ON r.rowid=g.id WHERE r.id IN ({placeholders}) GROUP BY g.kind,g.basis,g.root',chunk):
                        group_keys[tuple(row[:3])]+=row[3]
                ranked=sorted((g for g in group_keys if group_id(*g) not in excluded),key=lambda g:(g[1]=='studio',-group_keys[g],len(g[2]),g))
                for kind,basis,root in ranked[:240]:
                    raw=list(self.index.execute('SELECT DISTINCT r.rowid AS row_id,r.* FROM groups g JOIN refs r ON r.rowid=g.id WHERE g.kind=? AND g.basis=? AND g.root=? LIMIT 1001',(kind,basis,root)))
                    if len(raw)>1000:continue
                    records={row['id']:self.record(row) for row in raw}
                    grouped = self.members(list(records.values()))
                    if not 2 <= len(grouped) <= 200:
                        continue
                    alias_counts=defaultdict(int)
                    for rows in grouped:
                        for alias in {key(r['title']) for r in rows}:alias_counts[(alias,rows[0]['year'])]+=1
                    members = []
                    for rows in grouped:
                        primary = sorted(rows, key=lambda r: (-len(r['genres']), -len(r['directors']), r['id']))[0]
                        ids = sorted({item_id for row in rows for item_id, _ in item_refs.get(row['id'], [])})
                        aliases = {key(r['title']) for r in rows}
                        reference_ids={r['id'] for r in rows}
                        eligible=[t for t in targets if t['kind']==kind and not t.get('season')]
                        intended=any(reference_ids & ({t.get('workId')} | set(t.get('packWorkIds',[]))) for t in eligible)
                        hinted=[t for t in eligible if not t.get('packWorkIds') and key(t['title']) in aliases and t.get('year')==primary['year']]
                        ambiguous_hint=bool(hinted) and any(alias_counts[(key(t['title']),primary['year'])]>1 for t in hinted)
                        intended=intended or bool(hinted) and not ambiguous_hint
                        evidence = sorted({b for row in rows for _, b in item_refs.get(row['id'], [])})
                        state = 'review' if 'ambiguous-reference' in evidence else 'library' if len(ids)==1 else 'review' if ids else 'wanted' if intended else 'review' if ambiguous_hint else 'missing'
                        members.append({'key': hashlib.sha256('|'.join(sorted(r['id'] for r in rows)).encode()).hexdigest()[:24],
                                        'title': primary['title'], 'kind': kind, 'year': primary['year'], 'format': 'Any',
                                        'workId': primary['id'], 'candidateIds': sorted(r['id'] for r in rows),
                                        'creators':primary['directors'],
                                        'itemIds': ids, 'status': state, 'matchBasis': evidence, 'reason': 'recorded studio' if basis == 'studio' else 'shared title pattern'})
                    known = len(members)
                    years=defaultdict(list)
                    for member in members:
                        if member['year'] is not None:years[member['year']].append(member)
                    if basis=='title-pattern':
                        for parallel in years.values():
                            if len(parallel)>1:
                                for member in parallel:
                                    member['membershipReview']='Same-year titles may be separate works or alternate names. Review membership.'
                    in_library = sum(m['status'] == 'library' for m in members)
                    # Prefer human title spelling from the reference, with no fixed franchise catalog.
                    title = next(iter(records.values()))['title']
                    display = next((studio for r in records.values() for studio in r['studios'] if key(studio)==root),root.title()) + ' movies' if basis == 'studio' else title[:len(root)].strip() + ' series'
                    result.append({'id': group_id(kind, basis, root), 'name': display, 'kind': kind,
                                   'basis': basis, 'source': 'installed-packs', 'coverage': 'known-references-only',
                                   'counts': {'library': in_library, 'known': known, 'wanted': sum(m['status'] == 'wanted' for m in members),
                                              'review': sum(m['status'] == 'review' for m in members)}, 'members': members})
                result.extend(g for g in self.provider_recommendations(items) if g['id'] not in excluded)
                # Avoid several nested title-pattern suggestions with identical memberships.
                seen, unique = set(), []
                for group in sorted(result, key=lambda g: (g['basis'] == 'studio', -g['counts']['library'], len(g['name']), g['name'])):
                    signature = (group['kind'], group['basis'], tuple(sorted(m['key'] for m in group['members'])))
                    if signature not in seen:
                        unique.append(group)
                        seen.add(signature)
                self.recommendation_cache=(fingerprint,unique[:60])
                return self.recommendation_cache[1]
            finally:
                if not operation_owned:self.operation_lock.release()

    @staticmethod
    def provider_recommendations(items):
            # Supplied labels have household scope, not a missing-title universe.
            result=[]
            provider_groups = defaultdict(list)
            for item in items:
                labels = set(item.get('catalogDetails', {}).get('collections', []))
                for source in item.get('sources', []):
                    labels.update(source.get('metadataSnapshot', {}).get('catalogDetails', {}).get('collections', []))
                for label in labels:
                    provider_groups[(item['kind'], label)].append(item)
            for (kind, label), rows in provider_groups.items():
                if not 2 <= len(rows) <= 200:
                    continue
                members = [{'key': row['id'], 'title': row['title'], 'kind': kind, 'year': row.get('year'), 'format': 'Any',
                            'itemIds': [row['id']], 'status': 'library', 'candidateIds': [], 'reason': 'saved collection label',
                            'workId': None, 'matchBasis': ['provider-collection']} for row in rows]
                result.append({'id': group_id(kind, 'provider-collection', label), 'name': label, 'kind': kind,
                               'basis': 'provider-collection', 'source': 'household-sources', 'coverage': 'household-only',
                               'counts': {'library': len(rows), 'known': len(rows), 'wanted': 0, 'review': 0}, 'members': members})
            return result
