"""Rebuildable, incremental catalog projection for bounded everyday reads.

The item JSON remains authoritative. Triggers invalidate affected documents in
the same transaction as owner/provider writes, including writes outside Box.
"""
import json
import re
import threading
import unicodedata
from datetime import datetime
from library_collections import activity_states, genres, list_collections


# Evaluate the review queue once per page/summary. A correlated JSON scan per
# title makes even a modest pending review queue stall large libraries.
VISIBLE_ITEM_CLAUSE = "d.item_id NOT IN (SELECT COALESCE(json_extract(r.data,'$.incoming.id'),'') FROM review_queue r)"


def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value)).casefold() if not unicodedata.combining(c))


MIGRATION = (
    "CREATE TABLE browse_documents(item_id TEXT PRIMARY KEY REFERENCES items(id) ON DELETE CASCADE,data TEXT NOT NULL,title_key TEXT NOT NULL,search_key TEXT NOT NULL,kind TEXT NOT NULL,added TEXT NOT NULL,released TEXT NOT NULL,edition TEXT NOT NULL,favorite INTEGER NOT NULL,digital INTEGER NOT NULL,sample INTEGER NOT NULL)",
    "CREATE INDEX browse_added ON browse_documents(added DESC,item_id)",
    "CREATE INDEX browse_title ON browse_documents(title_key,item_id)",
    "CREATE INDEX browse_release ON browse_documents(released DESC,item_id)",
    "CREATE INDEX browse_kind_added ON browse_documents(kind,added DESC,item_id)",
    "CREATE TABLE browse_genres(item_id TEXT NOT NULL REFERENCES browse_documents(item_id) ON DELETE CASCADE,label TEXT NOT NULL,key TEXT NOT NULL,PRIMARY KEY(item_id,key))",
    "CREATE INDEX browse_genre_key ON browse_genres(key,item_id)",
    "CREATE TABLE browse_physical(item_id TEXT NOT NULL REFERENCES browse_documents(item_id) ON DELETE CASCADE,facet TEXT NOT NULL,label TEXT NOT NULL,location TEXT NOT NULL,copies INTEGER NOT NULL,PRIMARY KEY(item_id,facet,location))",
    "CREATE INDEX browse_physical_location ON browse_physical(location,item_id)",
    "CREATE TABLE browse_dirty(item_id TEXT PRIMARY KEY)",
    "CREATE TABLE browse_state(key TEXT PRIMARY KEY,value TEXT NOT NULL)",
    "INSERT INTO browse_state VALUES('revision','0')",
    "INSERT INTO browse_dirty SELECT id FROM items",
    "CREATE TABLE monitored_files(source_id TEXT NOT NULL,path TEXT NOT NULL,root_identity TEXT NOT NULL,bytes INTEGER NOT NULL,mtime_ns INTEGER NOT NULL,seen_at REAL NOT NULL,PRIMARY KEY(source_id,path))",
    "CREATE INDEX browse_metadata_entity_links ON metadata_links(entity_id,target_type,target_id)",
)


def migration_statements():
    result=list(MIGRATION)
    for table in ('items','review_queue','activity_events','metadata_links','metadata_identifiers','metadata_field_values','library_collections','library_collection_members','completion_sets','completion_members','collecting_targets'):
        for event in ('INSERT','UPDATE','DELETE'):
            record='OLD' if event=='DELETE' else 'NEW'
            dirty=''
            if table=='items':dirty=f'INSERT INTO browse_dirty SELECT {record}.id WHERE NOT EXISTS(SELECT 1 FROM browse_dirty WHERE item_id={record}.id);'
            elif table=='activity_events':dirty=f'INSERT INTO browse_dirty SELECT {record}.item_id WHERE NOT EXISTS(SELECT 1 FROM browse_dirty WHERE item_id={record}.item_id);'
            elif table=='metadata_links':dirty=f"INSERT INTO browse_dirty SELECT {record}.target_id WHERE {record}.target_type='item' AND NOT EXISTS(SELECT 1 FROM browse_dirty WHERE item_id={record}.target_id);"
            elif table in ('metadata_identifiers','metadata_field_values'):
                entities=f'l.entity_id={record}.entity_id' if event!='UPDATE' else '(l.entity_id=NEW.entity_id OR l.entity_id=OLD.entity_id)'
                dirty=f"INSERT INTO browse_dirty SELECT DISTINCT l.target_id FROM metadata_links l WHERE l.target_type='item' AND {entities} AND NOT EXISTS(SELECT 1 FROM browse_dirty WHERE item_id=l.target_id);"
            result.append(f"CREATE TRIGGER browse_{table}_{event.lower()} AFTER {event} ON {table} BEGIN {dirty} UPDATE browse_state SET value=CAST(value AS INTEGER)+1 WHERE key='revision'; END")
    return tuple(result)


def compact(item):
    result={k:item[k] for k in ('id','title','kind','year','digitalPlatforms','releaseDate','poster','backdrop','genre','customGenres','collectionGenres','collectionGenreBasis','duration','progress','favorite','addedAt','sample','artist','metadataPreference','activity') if k in item}
    result['description']=str(item.get('description') or '')[:400]
    # Rich source snapshots, episode/track trees and edition details are fetched
    # only when a title is opened. All physical rows remain for accurate rules.
    fields=('packageType','packageTitle','physicalReleaseId','ownedCopyId','packaging','releaseLabel','id','type','label','url','mime','available','addedAt','edition','location','platform','barcode','discId','creator','season','providerItemId','metadataIdentifiers')
    result['sources']=[{k:s[k] for k in fields if k in s} for s in item.get('sources',[]) if s.get('type')=='physical']
    selected=[];types=set()
    for source in item.get('sources',[]):
        if source.get('type')=='physical':continue
        if source.get('type') not in types or source.get('id')==item.get('metadataPreference'):
            selected.append({k:source[k] for k in fields if k in source});types.add(source.get('type'))
    result['sources'] += selected
    result['browseSummary']=True
    return result


class LibraryBrowse:
    def __init__(self, box):
        self.box=box
        self.lock=threading.RLock()
        self.worker=None
        self.failure=''
        self.collection_cache=None

    def prepare(self):
        refs=self.box.collection_references
        ready=refs.ready()
        stamp=refs.stamp if ready else None
        with self.lock, self.box.db() as db:
            projection=db.execute("SELECT value FROM browse_state WHERE key='projection'").fetchone()
            if not projection or projection[0]!='4':
                db.execute('INSERT OR IGNORE INTO browse_dirty SELECT id FROM items')
                db.execute("INSERT INTO browse_state VALUES('projection','4') ON CONFLICT(key) DO UPDATE SET value=excluded.value")
            prior=db.execute("SELECT value FROM browse_state WHERE key='packs'").fetchone()
            if ready and (not prior or prior[0]!=stamp):
                db.execute('INSERT OR IGNORE INTO browse_dirty SELECT id FROM items')
                db.execute("INSERT INTO browse_state VALUES('packs',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(stamp,))
            count=db.execute('SELECT COUNT(*) FROM browse_dirty').fetchone()[0]
            if not count:return True
            if count<=500 and not self.worker:
                self._sync(db,500)
                return True
            if not self.worker:
                self.failure=''
                self.worker=threading.Thread(target=self._background,daemon=True)
                self.worker.start()
            return False

    def _background(self):
        try:
            with self.box.operation_lock:
                while True:
                    with self.lock, self.box.db() as db:
                        if not db.execute('SELECT 1 FROM browse_dirty LIMIT 1').fetchone():break
                        self._sync(db,500)
        except Exception as error:self.failure=str(error)
        finally:
            with self.lock:self.worker=None

    def _sync(self,db,limit):
        if not db.in_transaction:db.execute('BEGIN IMMEDIATE')
        ids=[r[0] for r in db.execute('SELECT item_id FROM browse_dirty LIMIT ?',(limit,))]
        if not ids:return
        marks=','.join('?' for _ in ids)
        rows=[json.loads(r[0]) for r in db.execute(f'SELECT data FROM items WHERE id IN ({marks})',ids)]
        mappings={}
        for row in db.execute(f"SELECT l.target_id,i.value FROM metadata_links l JOIN metadata_identifiers i ON i.entity_id=l.entity_id WHERE l.target_type='item' AND i.namespace='blankbox-pack-record' AND l.target_id IN ({marks})",ids):mappings.setdefault(row[0],[]).append('pack:'+row[1])
        projected=self.box.collection_references.genre_projection(rows,mappings)
        states={}
        for row in db.execute(f"SELECT item_id,status,created_at,id FROM activity_events WHERE rowid IN (SELECT MAX(rowid) FROM activity_events WHERE undone_at IS NULL AND episode_key='' AND item_id IN ({marks}) GROUP BY item_id)",ids):states[row['item_id']]={'status':row['status'],'updatedAt':row['created_at'],'eventId':row['id']}
        for item in projected:
            item['activity']=states.get(item['id'],{'status':'not-started'})
            card=compact(item)
            added=max([item.get('addedAt','')]+[s.get('addedAt','') for s in item.get('sources',[])])
            released=item.get('releaseDate') or (str(item['year'])+'-01-01' if item.get('year') else '')
            edition=' '.join(sorted(s.get('edition','') for s in item.get('sources',[])))
            text=' '.join([item.get('title',''),item.get('genre',''),str(item.get('year') or ''),item.get('description',''),*genres(item),*[str(s.get(k) or '') for s in item.get('sources',[]) for k in ('packageTitle','packaging','releaseLabel','label','edition','volume','issue','region','catalogNumber','mime','location','path','barcode','creator','publisher','platform')]])
            text+=' '+' '.join(str(record.get(key) or '') for record in item.get('digitalPlatforms',[]) for key in ('platform','status','notes'))
            digital=int(any(s.get('type') in ('local','digital','jellyfin','plex','emby') for s in item.get('sources',[])))
            db.execute('INSERT INTO browse_documents VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(item_id) DO UPDATE SET data=excluded.data,title_key=excluded.title_key,search_key=excluded.search_key,kind=excluded.kind,added=excluded.added,released=excluded.released,edition=excluded.edition,favorite=excluded.favorite,digital=excluded.digital,sample=excluded.sample',(item['id'],json.dumps(card),normalized(item['title']),normalized(text),item['kind'],added,released,normalized(edition),bool(item.get('favorite')),digital,bool(item.get('sample'))))
            db.execute('DELETE FROM browse_genres WHERE item_id=?',(item['id'],))
            db.executemany('INSERT OR IGNORE INTO browse_genres VALUES(?,?,?)',[(item['id'],g,normalized(g)) for g in genres(item)])
            db.execute('DELETE FROM browse_physical WHERE item_id=?',(item['id'],))
            physical={}
            for source in item.get('sources',[]):
                if source.get('type')!='physical':continue
                label=(source.get('platform') or 'Platform not set') if item['kind']=='game' else (source.get('label') or 'Other')
                facet=('platform:' if item['kind']=='game' else 'format:')+label
                key=(facet,label,source.get('location','').strip() or 'Location not set')
                physical[key]=physical.get(key,0)+1
            db.executemany('INSERT INTO browse_physical VALUES(?,?,?,?,?)',[(item['id'],*k,v) for k,v in physical.items()])
        db.execute(f'DELETE FROM browse_dirty WHERE item_id IN ({marks})',ids)
        db.execute("UPDATE browse_state SET value=CAST(value AS INTEGER)+1 WHERE key='revision'")

    def status(self):
        return 'unavailable' if self.failure else 'building' if not self.prepare() else 'ready'

    def _cards(self,db,ids):
        result=[]
        for identifier in ids:
            row=db.execute('SELECT data FROM items WHERE id=?',(identifier,)).fetchone()
            if not row:continue
            item=self.box.public_item(json.loads(row[0]))
            stored=db.execute('SELECT data FROM browse_documents WHERE item_id=?',(identifier,)).fetchone()
            card=compact(item)
            if stored:
                projected=json.loads(stored[0])
                card.update({k:projected[k] for k in ('collectionGenres','collectionGenreBasis','activity') if k in projected})
            result.append(card)
        return result

    def page(self,options):
        ready=self.prepare()
        try:limit=int(options.get('limit',60));offset=int(options.get('offset',0))
        except (TypeError,ValueError):raise ValueError('Invalid library page.')
        if not 1<=limit<=100 or not 0<=offset<=1000000:raise ValueError('Invalid library page.')
        q=options.get('q','');kind=options.get('kind','');view=options.get('view','library');sort=options.get('sort','recent')
        if not isinstance(q,str) or len(q)>200 or kind not in ('','movie','tv','music','photo','home-video','book','comic','game','file') or sort not in ('recent','az','year','edition'):raise ValueError('Invalid library filter.')
        conditions=[VISIBLE_ITEM_CLAUSE]
        params=[]
        if options.get('excludeSamples') in (True,'true','1'):conditions.append('d.sample=0')
        if kind:conditions.append('d.kind=?');params.append(kind)
        elif view=='photo' and not q:conditions.append("d.kind IN ('photo','home-video')")
        elif view in ('movie','tv','music','book','comic','game') and not q:conditions.append('d.kind=?');params.append(view)
        if q:conditions.append('instr(d.search_key,?)>0');params.append(normalized(q))
        if options.get('favorites') in (True,'true','1'):conditions.append('d.favorite=1')
        genre=options.get('genre','');status=options.get('status','');facet=options.get('facet','all')
        if not isinstance(genre,str) or len(genre)>80 or status not in ('','not-started','in-progress','completed') or not isinstance(facet,str) or len(facet)>300:raise ValueError('Invalid library filter.')
        if genre:conditions.append('EXISTS(SELECT 1 FROM browse_genres g WHERE g.item_id=d.item_id AND g.key=?)');params.append(normalized(genre))
        if status:conditions.append("json_extract(d.data,'$.activity.status')=?");params.append(status)
        if options.get('released') in (True,'true','1'):conditions.extend(["d.digital>0","json_extract(d.data,'$.releaseDate') IS NOT NULL"])
        order={'az':'d.title_key,d.item_id','year':'d.released DESC,d.item_id','edition':'d.edition,d.title_key,d.item_id','recent':'d.added DESC,d.item_id'}[sort]
        with self.lock,self.box.db() as db:
            collection=options.get('collection','')
            if collection:
                group=next((g for g in self.collections(db) if g['id']==collection),None)
                if not group:raise ValueError('This collection is no longer available.')
                db.execute('CREATE TEMP TABLE selected_members(item_id TEXT PRIMARY KEY,position INTEGER)')
                db.executemany('INSERT INTO selected_members VALUES(?,?)',[(v,i) for i,v in enumerate(group['itemIds'])])
                conditions.append('d.item_id IN (SELECT item_id FROM selected_members)')
                order='(SELECT position FROM selected_members WHERE item_id=d.item_id),d.item_id'
            physical=view=='physical' and not q
            shelf=physical and options.get('shelves') in (True,'true','1')
            base='browse_documents d'
            copies_expression='p.copies'
            if physical:
                standalone=options.get('standalonePhysical') in (True,'true','1')
                source_clause="json_extract(s.value,'$.type')='physical' AND COALESCE(json_extract(s.value,'$.packageType'),'')<>'box-set' AND (CASE WHEN d.kind='game' THEN 'platform:'||COALESCE(NULLIF(json_extract(s.value,'$.platform'),''),'Platform not set') ELSE 'format:'||COALESCE(NULLIF(json_extract(s.value,'$.label'),''),'Other') END)=p.facet AND COALESCE(NULLIF(trim(json_extract(s.value,'$.location')),''),'Location not set')=p.location"
                if shelf:base+=' JOIN browse_physical p ON p.item_id=d.item_id'
                clause='p.item_id=d.item_id'
                if facet!='all':clause+=' AND p.facet=?';params.append(facet)
                if standalone:
                    clause+=' AND EXISTS(SELECT 1 FROM json_each(d.data,\'$.sources\') s WHERE '+source_clause+')'
                    if shelf:
                        conditions.append('EXISTS(SELECT 1 FROM json_each(d.data,\'$.sources\') s WHERE '+source_clause+')')
                        copies_expression='(SELECT COUNT(*) FROM json_each(d.data,\'$.sources\') s WHERE '+source_clause+')'
                conditions.append(('p.facet=?' if facet!='all' else '1') if shelf else 'EXISTS(SELECT 1 FROM browse_physical p WHERE '+clause+')')
            where=' AND '.join(conditions)
            base_query=' FROM '+base+' WHERE '+where
            count_query='SELECT COUNT(*)'+base_query if not shelf else 'SELECT COUNT(*) FROM (SELECT d.item_id,p.location'+base_query+' GROUP BY d.item_id,p.location)'
            total=db.execute(count_query,params).fetchone()[0]
            if shelf:
                rows=db.execute('SELECT d.item_id,p.location,SUM('+copies_expression+') copies'+base_query+' GROUP BY d.item_id,p.location ORDER BY p.location,'+order+' LIMIT ? OFFSET ?',(*params,limit,offset)).fetchall()
            else:rows=db.execute('SELECT d.item_id'+base_query+' ORDER BY '+order+' LIMIT ? OFFSET ?',(*params,limit,offset)).fetchall()
            ids=list(dict.fromkeys(r['item_id'] for r in rows));items=self._cards(db,ids)
            groups=[]
            if shelf:
                for row in rows:
                    group=next((g for g in groups if g['location']==row['location']),None)
                    if not group:
                        # Count all copies at this filtered location, not just this page.
                        copies=db.execute('SELECT SUM('+copies_expression+')'+base_query+' AND p.location=?',(*params,row['location'])).fetchone()[0]
                        group={'location':row['location'],'copies':copies,'entries':[]};groups.append(group)
                    group['entries'].append({'itemId':row['item_id'],'copies':row['copies']})
            return {'items':items,'total':total,'offset':offset,'limit':limit,'shelfGroups':groups,'indexStatus':'unavailable' if self.failure else 'ready' if ready else 'building'}

    def facets(self,db):
        sources=" FROM browse_documents d,json_each(d.data,'$.sources') s WHERE json_extract(s.value,'$.type')='physical'"
        identity="COALESCE(json_extract(s.value,'$.ownedCopyId'),d.item_id||':'||json_extract(s.value,'$.id'))"
        label="CASE WHEN d.kind='game' THEN COALESCE(NULLIF(json_extract(s.value,'$.platform'),''),'Platform not set') ELSE COALESCE(NULLIF(json_extract(s.value,'$.label'),''),'Other') END"
        facet="(CASE WHEN d.kind='game' THEN 'platform:' ELSE 'format:' END)||("+label+")"
        location="COALESCE(NULLIF(trim(json_extract(s.value,'$.location')),''),'Location not set')"
        return {'genres':[r[0] for r in db.execute('SELECT MIN(label) FROM browse_genres GROUP BY key ORDER BY key')],
                'physicalFacets':[dict(r) for r in db.execute('SELECT '+facet+' id,'+label+' label,d.kind,COUNT(DISTINCT '+identity+') count'+sources+' GROUP BY '+facet+',d.kind ORDER BY label')],
                'locations':[dict(r) for r in db.execute('SELECT '+location+' location,COUNT(DISTINCT '+identity+') copies'+sources+' GROUP BY location ORDER BY location')]}

    def collections(self,db):
        revision=db.execute("SELECT value FROM browse_state WHERE key='revision'").fetchone()[0]
        stamp=(revision,datetime.now().strftime('%m-%d'))
        if self.collection_cache and self.collection_cache[0]==stamp:return self.collection_cache[1]
        items=[json.loads(r[0]) for r in db.execute('SELECT data FROM browse_documents d WHERE '+VISIBLE_ITEM_CLAUSE)]
        groups=list_collections(db,items)
        self.collection_cache=(stamp,groups)
        return groups

    def collection_page(self):
        self.prepare()
        with self.lock,self.box.db() as db:
            groups=self.collections(db)
            return {'collections':[{**{k:v for k,v in g.items() if k not in ('itemIds','memberIds','referenceGenres','recommendationMemberIds')},'itemIds':[],'memberIds':[],'titleCount':len(g['itemIds']),'covers':self._cards(db,g['itemIds'][:3])} for g in groups]}

    def collection_edit(self,identifier):
        self.prepare()
        with self.lock,self.box.db() as db:
            group=next((g for g in self.collections(db) if g['id']==identifier),None)
            if not group:raise ValueError('This collection is no longer available.')
            return {**group,'referenceGenres':None,'recommendationMemberIds':None}
