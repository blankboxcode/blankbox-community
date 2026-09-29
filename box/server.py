#!/usr/bin/env python3
"""Blank Box 0.1: local media catalog, copy-only import, streaming, verified backup.
Python 3.10+, standard library only. Default: loopback; no public listening.
"""
from __future__ import annotations
import argparse, base64, csv, hashlib, http.cookies, http.server, io, json, math, mimetypes, os, re, secrets, shutil, signal, sqlite3, stat, tempfile, threading, time, urllib.parse, urllib.request, uuid
mimetypes.add_type('audio/mp4','.m4b')
from contextlib import contextmanager, nullcontext
from runtime_lock import RuntimeLock
from file_safety import inside, digest, safe_file, open_linked_file, safe_destination, fingerprint, checked_copy, reject_links
from refresh_schedule import RefreshSchedule
from library_browse import LibraryBrowse, VISIBLE_ITEM_CLAUSE, migration_statements
from folder_monitor import monitor_source
from pathlib import Path
from datetime import datetime, timezone
from reader import inspect_reader, read_asset, read_chapter
from disc_import import DiscImportError, STAGING_MARKER, audio_cd_devices, audio_cd_drive_details, cleanup_stale_stages, extract_audio_cd, probe_audio_cd, tool_status
from catalog_lists import FIELDS as LIST_FIELDS, inspect_document, normalize_row, spreadsheet_safe, suggested_mapping
from local_clues import GENERIC, path_clues, proposed_filename
from metadata import SQLiteMetadataRepository, backfill_item, confirm_entity, local_release_id, local_work_id, local_digital_release_id, remove_digital_source_links, sync_digital_releases, sync_owned_releases, sync_source_metadata, valid_season
from metadata_indexed_pack import MAX_BUNDLE_BYTES, MetadataPackSet, StagedMetadataCatalog
from metapack_identity import visible_identifiers, physical_namespace, pack_identifier_allowed
from collecting import FORMATS_BY_KIND, add_target, intention_ownership, list_targets, ownership, ownership_index, remove_target, update_target, title_key as collecting_title_key
from completion import list_sets, save_set, remove_set, set_member_ignored
from collection_discovery import CollectionReferences
from bundled_metadata import install_bundled_packs
from edition_completion import edition_status, reference_summary
from commerce import clean_store_preferences, store_links, store_sources
from tv_catalog import jellyfin_tree, plex_tree
from catalog_details import clean_details, clean_facts, provider_details, provider_identifiers
from barcodes import barcode_keys, clean_barcode
from artwork import MAX_ARTWORK_BYTES, artwork_hash, artwork_url, folder_cover_paths, jpeg_size
from library_collections import activity_history, activity_states, hidden_organization, labels as collection_labels, list_collections, merge_collection_activity, record_activity, restore_organization, save_collection

def product_version():
    """Read the release version without adding a runtime package dependency."""
    local=Path(__file__).resolve().with_name('VERSION')
    if local.is_file():return local.read_text(encoding='utf-8').strip()
    package=Path(__file__).resolve().parent.parent/'package.json'
    if package.is_file():return str(json.loads(package.read_text(encoding='utf-8'))['version'])
    return '0.0.0-development'

VERSION = product_version()
CATALOG_SCHEMA_VERSION = 20
MEDIA_RIGHTS_TERMS_VERSION = '1'
KINDS = {'movie','tv','music','photo','home-video','book','comic','game','file'}
VIDEO_KINDS = {'movie','tv','home-video'}
PHYSICAL_FORMATS = {
    'DVD':('movie','tv'),'Blu-ray':('movie','tv'),'4K UHD Blu-ray':('movie','tv'),
    'VHS':('movie','tv'),'Betamax':('movie','tv'),'LaserDisc':('movie','tv'),
    'CD':('music',),'Vinyl':('music',),'Cassette':('music',),'8-track':('music',),'MiniDisc':('music',),
    'Book':('book',),'Hardcover':('book',),'Paperback':('book',),'Comic':('comic',),'Magazine':('book',),
    'Game':('game',),'Game disc':('game',),'Game cartridge':('game',),'Other':tuple(KINDS),
}
CHUNK = 1024 * 1024
CURRENT_PHYSICAL_FORMATS = ('DVD','Blu-ray','4K UHD Blu-ray','VHS','Betamax','LaserDisc','CD','Vinyl','Cassette','8-track','MiniDisc','Book','Hardcover','Paperback','Comic','Magazine','Game','Other')
DEFAULT_PHYSICAL_FORMATS = ('DVD','Blu-ray','4K UHD Blu-ray','Game','CD','Vinyl','Book','Comic')
COMMON_GAME_PLATFORMS = (
    'PlayStation 5','PlayStation 4','PlayStation 3','PlayStation 2','PlayStation',
    'PlayStation Portable (PSP)','PlayStation Vita',
    'Xbox Series X','Xbox One','Xbox 360','Xbox',
    'Nintendo Switch 2','Nintendo Switch','Nintendo 3DS','Nintendo DS',
    'Nintendo Wii U','Nintendo Wii','Nintendo GameCube','Nintendo 64',
    'Super Nintendo (SNES)','Nintendo Entertainment System (NES)',
    'Game Boy','Game Boy Color','Game Boy Advance',
    'Sega Genesis / Mega Drive','Sega Dreamcast','Sega Saturn','Sega Game Gear',
    'PC (Windows)','Atari 2600',
)
SIDEBAR_SHORTCUTS = ('movie','tv','music','photo','book','comic','game')
HOME_ROWS = ('recently-added','recently-released','movies','tv','music','photos','books','comics','games')
SIDEBAR_DESTINATIONS = ('library','collections','physical',*SIDEBAR_SHORTCUTS)
HOME_HERO_MODES = ('watch','music','book','photos','comics','games')
HOME_HERO_SORTS = ('added','released','az','random')
DEFAULTS = {'helpTipsEnabled':True,'name':'My Blank Box','jellyfinUrl':'','plexUrl':'','immichUrl':'','remoteUrl':'','opticalDrive':'','setupDone':False,'setupVersion':1,'setupMode':'','setupStep':'welcome','mediaProvider':'blankbox','mediaInputs':[],'physicalFormats':list(DEFAULT_PHYSICAL_FORMATS),'physicalLocations':[],'gamePlatforms':list(COMMON_GAME_PLATFORMS),'gamePlatformCatalogVersion':1,'sidebarShortcuts':[],'sidebarShortcutVersion':1,'sidebarOrder':list(SIDEBAR_DESTINATIONS),'streamingServices':[],'remoteProvider':'local','autoImport':False,'autoProviderRefresh':False,'autoFolderCopy':False,'autoSourceIndex':False,'autoImportMinutes':30,'heroWatch':True,'heroMusic':True,'heroBooks':True,'heroPhotos':False,'heroComics':False,'heroGames':False,'homeRows':['recently-added','recently-released'],'homeHeroOrder':list(HOME_HERO_MODES),'homeHeroSort':'added','retailStoreKinds':{},'customRetailStores':[],'mediaRightsAttestation':None}
OWNERSHIP_NAMESPACE = uuid.UUID('9b30c0a0-7830-5cb0-b7bb-b00169de784e')
RUNTIME_CONFIG_KEYS = {'data','sources','backup','host','port','backupEveryHours'}

def configured_sources(value):
    if value in (None,''):return []
    if isinstance(value,str):
        text=value.strip()
        if not text:return []
        if text.startswith('['):
            try:value=json.loads(text)
            except json.JSONDecodeError as error:raise ValueError('BLANKBOX_SOURCES must be a JSON array or an operating-system path list.') from error
        else:value=text.split(os.pathsep)
    if not isinstance(value,list) or any(not isinstance(path,str) or not path.strip() for path in value):raise ValueError('Configured sources must be a list of folder paths.')
    paths=[path.strip() for path in value]
    if len(paths)>100 or len(set(paths))!=len(paths):raise ValueError('Configure each source once, up to 100 folders.')
    return paths

def load_runtime_config(config_path=None,overrides=None,environ=None):
    """Resolve one portable runtime contract: CLI > environment > JSON > defaults."""
    overrides=overrides or {};environ=os.environ if environ is None else environ
    selected_path=config_path or environ.get('BLANKBOX_CONFIG');saved={}
    if selected_path:
        path=Path(selected_path).expanduser()
        if not path.is_file():raise ValueError(f'Configuration file does not exist: {path}')
        if path.stat().st_size>64*1024:raise ValueError('Configuration file is larger than 64 KiB.')
        try:saved=json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as error:raise ValueError(f'Configuration file is not valid JSON: {error.msg}.') from error
        if not isinstance(saved,dict):raise ValueError('Configuration file must contain a JSON object.')
        unknown=set(saved)-RUNTIME_CONFIG_KEYS
        if unknown:raise ValueError('Unknown configuration fields: '+', '.join(sorted(unknown)))
    environment={'data':'BLANKBOX_DATA','sources':'BLANKBOX_SOURCES','backup':'BLANKBOX_BACKUP','host':'BLANKBOX_HOST','port':'BLANKBOX_PORT','backupEveryHours':'BLANKBOX_BACKUP_EVERY_HOURS'}
    defaults={'data':str(Path.home()/'Blank Box'),'sources':[],'backup':None,'host':'127.0.0.1','port':25265,'backupEveryHours':None}
    values={}
    for key in RUNTIME_CONFIG_KEYS:
        if overrides.get(key) is not None:values[key]=overrides[key]
        elif environment[key] in environ:values[key]=environ[environment[key]]
        elif key in saved:values[key]=saved[key]
        else:values[key]=defaults[key]
    values['sources']=configured_sources(values['sources'])
    for key in ('data','host'):
        if not isinstance(values[key],str) or not values[key].strip():raise ValueError(f'{key} must be a non-empty string.')
        values[key]=values[key].strip()
    if values['backup'] in ('',None):values['backup']=None
    elif not isinstance(values['backup'],str):raise ValueError('backup must be a folder path or null.')
    else:values['backup']=values['backup'].strip()
    try:values['port']=int(values['port'])
    except (TypeError,ValueError) as error:raise ValueError('port must be a number from 1 to 65535.') from error
    if not 1<=values['port']<=65535:raise ValueError('port must be a number from 1 to 65535.')
    interval=values['backupEveryHours']
    if interval in ('',None):values['backupEveryHours']=None
    else:
        try:values['backupEveryHours']=float(interval)
        except (TypeError,ValueError) as error:raise ValueError('backupEveryHours must be at least 1.') from error
        if values['backupEveryHours']<1:raise ValueError('backupEveryHours must be at least 1.')
        if not values['backup']:raise ValueError('backupEveryHours requires a backup folder.')
    return values

def now(): return datetime.now(timezone.utc).isoformat()

def provider_timestamp(value):
    """Normalize provider dates without turning a sync time into an added date."""
    try:
        if isinstance(value,(int,float)) and 0<value<32503680000:return datetime.fromtimestamp(value,tz=timezone.utc).isoformat()
        if isinstance(value,str) and value.strip():
            parsed=datetime.fromisoformat(value.strip().replace('Z','+00:00'))
            if parsed.tzinfo is None:parsed=parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).isoformat()
    except (OverflowError,OSError,ValueError):pass
    return None

def provider_release_date(value):
    timestamp=provider_timestamp(value)
    return timestamp[:10] if timestamp else None

def kind_for(name):
    ext=Path(name).suffix.lower()[1:]
    if ext in {'jpg','jpeg','png','webp','heic','heif','avif','tif','tiff','gif'}: return 'photo'
    if ext in {'mp3','flac','wav','ogg','m4a','aac','opus'}: return 'music'
    if ext in {'cbz','cbr'}: return 'comic'
    if ext in {'pdf','epub','mobi','azw','azw3','m4b'}: return 'book'
    if ext in {'mp4','mkv','avi','mov','webm','m4v','mpg','mpeg','vob'}:
        return 'tv' if re.search(r's\d{1,2}e\d{1,3}',name,re.I) else 'home-video' if re.match(r'^(IMG|VID|DSC|MOV)[_\d-]',Path(name).name,re.I) else 'movie'
    return 'file'





def clean_title(name): return re.sub(r'[._]+',' ',Path(name).stem).strip() or Path(name).name
def title_key(value): return re.sub(r'[^a-z0-9]+','',str(value).lower())
def inventory_title_key(value): return ''.join(character for character in str(value).casefold() if character.isalnum())
def title_tokens(value):
    title=EDITION_PATTERN.sub('',str(value or ''))
    title=re.sub(r'[\s([{.-](?:18|19|20|21)\d{2}[\s)\]}.-]*$','',title)
    return tuple(dict.fromkeys(word for word in re.findall(r'[^\W_]+',title.casefold()) if len(word)>=2 and not word.isdigit() and word not in {'the','and','for','with','from','of','an','to'}))[:12]
def sync_item_search(db,item,include_tokens=True):
    db.execute('INSERT INTO item_search(item_id,kind,title_key,year) VALUES(?,?,?,?) ON CONFLICT(item_id) DO UPDATE SET kind=excluded.kind,title_key=excluded.title_key,year=excluded.year',
               (item['id'],item.get('kind','file'),work_title_key(item.get('title')),item.get('year')))
    if include_tokens:
        db.execute('DELETE FROM item_search_tokens WHERE item_id=?',(item['id'],))
        db.executemany('INSERT INTO item_search_tokens(item_id,token) VALUES(?,?)',((item['id'],token) for token in title_tokens(item.get('title'))))
def compatible_media_kinds(left,right): return left==right or left in VIDEO_KINDS and right in VIDEO_KINDS

def inferred_title(name):
    raw=re.sub(r'\s+',' ',clean_title(name)).strip()
    year_match=re.search(r'(?:^|[\s([{.-])((?:18|19|20|21)\d{2})(?=$|[\s)\]}.-])',raw)
    year=int(year_match.group(1)) if year_match else None
    title=raw[:year_match.start()].strip(' .-_([{') if year_match else raw
    title=re.sub(r'\s*[\[(](?:2160p|1080p|720p|480p|uhd|bluray|blu-ray|web-?dl|webrip|remux)[^\])]*[\])]\s*$','',title,flags=re.I).strip()
    return title or raw,year

STANDARD_EDITION = 'Standard or unknown edition'
METADATA_FIELDS = ('title','kind','year','releaseDate','description','poster','backdrop','genre','duration','artist','catalogDetails')

def metadata_snapshot(item):
    return {field:item[field] for field in METADATA_FIELDS if item.get(field) not in (None,'')}

def saved_provider_cover(item,connected):
    """Find a saved, locally proxied provider cover without changing other facts."""
    overrides=item.get('metadataOverrides')
    if item.get('poster') or isinstance(overrides,list) and 'poster' in overrides:return None
    sources=[source for source in item.get('sources',[]) if isinstance(source,dict) and source.get('type') in ('jellyfin','plex')]
    sources.sort(key=lambda source:source.get('id')!=item.get('metadataPreference'))
    for source in sources:
        provider=source['type'];provider_id=str(source.get('providerItemId',''))
        valid=(re.fullmatch(r'[a-zA-Z0-9-]{1,100}',provider_id) if provider=='jellyfin' else re.fullmatch(r'\d{1,20}',provider_id))
        if not valid or not connected.get(provider):continue
        reference=f'/api/{provider}-art/{provider_id}'
        snapshot=source.get('metadataSnapshot')
        if isinstance(snapshot,dict) and snapshot.get('poster')==reference:return source,reference
    return None


def plex_details_url(base, machine_id, provider_id):
    if not isinstance(machine_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,120}',machine_id):
        raise Problem('Plex did not return a valid server identity. Reconnect it in Settings.',502)
    if not re.fullmatch(r'\d{1,20}',str(provider_id)):
        raise Problem('This Plex item has no valid catalog identifier.',404)
    return base.rstrip('/')+'/web/index.html#!/server/'+machine_id+'/details?key='+urllib.parse.quote('/library/metadata/'+str(provider_id),safe='')


def apply_reference_details(db, item, entity_id):
    """Apply a reviewed work's available facts without altering copies or files."""
    entity=db.execute("SELECT * FROM metadata_entities WHERE id=? AND level='work'",(entity_id,)).fetchone()
    if not entity:raise ValueError('Choose a work/title reference for catalog details.')
    values={}
    evidence={}
    catalog_values={}
    for row in db.execute('SELECT * FROM metadata_field_values WHERE entity_id=? ORDER BY owner_entered DESC,imported_at DESC,source,source_record_id',(entity_id,)):
        field=row['field']
        if field in ('catalogDetails','author','publisher'):
            raw=json.loads(row['value_json'])
            details=clean_details(raw) if field=='catalogDetails' else {('authors' if field=='author' else 'publishers'):[raw]} if isinstance(raw,str) and raw.strip() else {}
            for member,value in details.items():catalog_values.setdefault(member,value)
            if details:evidence.setdefault('catalogDetails',dict(row))
            continue
        if field not in METADATA_FIELDS or field=='kind' or field in values:continue
        value=json.loads(row['value_json'])
        if value in (None,''):continue
        values[field]=value;evidence[field]=dict(row)
    if catalog_values:values['catalogDetails']=catalog_values
    for field in ('title','year'):
        if entity[field] not in (None,''):values[field]=entity[field]
    # Artwork remains a separate, reference-only subsystem; never infer covers.
    for row in db.execute('SELECT * FROM metadata_artwork_refs WHERE entity_id=? ORDER BY owner_provided DESC,source,reference',(entity_id,)):
        field='poster' if row['role'] in ('cover','poster') else 'backdrop' if row['role']=='backdrop' else None
        reference=row['reference'];parsed=urllib.parse.urlparse(reference)
        if field and field not in values and (reference.startswith('/') and not reference.startswith('//') or parsed.scheme in ('http','https') and parsed.hostname and not parsed.username and not parsed.password):
            values[field]=reference;evidence[field]=dict(row)
    applied=[]
    limits={'title':250,'description':5000,'genre':500,'artist':250,'releaseDate':80,'poster':2000,'backdrop':2000}
    for field,value in values.items():
        if field in limits and (not isinstance(value,str) or not value.strip() or len(value)>limits[field]):continue
        if field=='year' and (type(value) is not int or not 1800<=value<=2200):continue
        if field=='catalogDetails':
            value=clean_details(value)
            if not value:continue
        if field=='duration' and (type(value) not in (int,float) or not math.isfinite(value) or value<0):continue
        if field in ('poster','backdrop'):
            parsed=urllib.parse.urlparse(value)
            if not (value.startswith('/') and not value.startswith('//') or parsed.scheme in ('http','https') and parsed.hostname and not parsed.username and not parsed.password):continue
        item[field]=value
        fact=evidence.get(field,{})
        item.setdefault('metadataProvenance',{})[field]={'source':fact.get('source') or entity['origin'],'entityId':entity_id,'sourceRecordId':fact.get('source_record_id',''),'sourceVersion':fact.get('source_version',''),'license':fact.get('license') or fact.get('rights','unclassified-local'),'updatedAt':now()}
        applied.append(field)
    cleared=set(applied)|{'catalogDetails.'+key for key in values.get('catalogDetails',{})}
    item['metadataOverrides']=sorted(set(item.get('metadataOverrides',[]))-cleared)
    item['metadataPreference']='blankbox'
    local_cover=(item.get('blankboxMetadataSnapshot') or {}).get('poster')
    item['blankboxMetadataSnapshot']=metadata_snapshot(item)
    if isinstance(local_cover,str) and local_cover.startswith('/api/artwork/'):
        item['blankboxMetadataSnapshot']['poster']=local_cover
        item['poster']=local_cover
    db.execute('UPDATE items SET data=? WHERE id=?',(json.dumps(item),item['id']))
    sync_item_search(db,item)
    backfill_item(db,item)
    return applied


def apply_metadata_choice(item, source):
    """Rebuild effective facts from one selected source and the saved local baseline."""
    snapshot=source.get('metadataSnapshot') or {} if source else {}
    baseline=item.get('blankboxMetadataSnapshot') or {}
    overrides=set(item.get('metadataOverrides',[]))
    provenance=item.setdefault('metadataProvenance',{})
    for field in METADATA_FIELDS:
        if field=='kind' or field in overrides:continue
        if source and snapshot.get(field) not in (None,''):
            value=snapshot[field];origin=source['type'].title()
            if field=='catalogDetails':value={**clean_details(baseline.get(field)),**clean_details(value)}
        elif baseline.get(field) not in (None,''):
            value=baseline[field];origin='Blank Box'
        else:
            value=None;origin='Blank Box' if not source else source['type'].title()
        if field=='catalogDetails':
            value=clean_details(value)
            for override in overrides:
                if not override.startswith('catalogDetails.'):continue
                member=override.split('.',1)[1]
                if member in item.get(field,{}):value[member]=item[field][member]
                else:value.pop(member,None)
            if not value:value=None
        if value is None:item.pop(field,None)
        else:item[field]=value
        provenance[field]={'source':origin,'updatedAt':now(),**({'sourceId':source['id']} if source and origin!='Blank Box' else {})}
EDITION_PATTERN = re.compile(r"\b(director'?s cut|extended (?:cut|edition)|theatrical (?:cut|edition)|final cut|special edition|collector'?s edition|anniversary edition|unrated|remastered)\b",re.I)

def work_title_key(value):
    title=EDITION_PATTERN.sub('',str(value or ''))
    title=re.sub(r'[\s([{.-](?:18|19|20|21)\d{2}[\s)\]}.-]*$','',title)
    return title_key(title) or inventory_title_key(title)

def edition_label(title):
    match=EDITION_PATTERN.search(str(title or ''))
    if not match:return STANDARD_EDITION
    value=match.group(1).strip().lower()
    labels={"director's cut":"Director's Cut",'directors cut':"Director's Cut",'extended cut':'Extended Cut','extended edition':'Extended Edition','theatrical cut':'Theatrical Cut','theatrical edition':'Theatrical Edition','final cut':'Final Cut','special edition':'Special Edition',"collector's edition":"Collector's Edition",'collectors edition':"Collector's Edition",'anniversary edition':'Anniversary Edition','unrated':'Unrated','remastered':'Remastered'}
    return labels.get(value,value.title())

def ensure_item_model(item):
    """Upgrade a catalog record without moving media or changing its identity."""
    changed=False
    versions=item.get('versions')
    if not isinstance(versions,list) or not versions:
        versions=[{'id':uuid.uuid4().hex,'label':edition_label(item.get('title'))}]
        for key in ('year','duration'):
            if key in item:versions[0][key]=item[key]
        item['versions']=versions;changed=True
    valid=[];seen=set()
    for version in versions:
        if not isinstance(version,dict):changed=True;continue
        identifier=version.get('id')
        if not isinstance(identifier,str) or not identifier or identifier in seen:
            identifier=uuid.uuid4().hex;version['id']=identifier;changed=True
        if not isinstance(version.get('label'),str) or not version['label'].strip():
            version['label']=STANDARD_EDITION;changed=True
        seen.add(identifier);valid.append(version)
    if valid!=versions:item['versions']=versions=valid
    if not versions:
        versions=[{'id':uuid.uuid4().hex,'label':STANDARD_EDITION}];item['versions']=versions;changed=True
    default_version=versions[0]['id']
    sources=item.get('sources')
    if not isinstance(sources,list):sources=[];item['sources']=sources;changed=True
    source_ids=set()
    for source in sources:
        if not isinstance(source,dict):continue
        identifier=source.get('id')
        if not isinstance(identifier,str) or not identifier or identifier in source_ids:
            identifier=uuid.uuid4().hex;source['id']=identifier;changed=True
        source_ids.add(identifier)
        if source.get('versionId') not in seen:source['versionId']=default_version;changed=True
        if source.get('type')=='local':
            for key in ('storedPath','sha256','bytes','mime'):
                if key not in source and key in item:source[key]=item[key];changed=True
            wanted='/media/'+urllib.parse.quote(str(item.get('id','')))+'/'+urllib.parse.quote(identifier)
            if source.get('url')!=wanted:source['url']=wanted;changed=True
        if source.get('type') in ('jellyfin','plex','emby') and not source.get('providerItemId'):
            match=re.search(r'(?:details\?id=|/details/)([^&#/?]+)',str(source.get('url','')))
            if match:source['providerItemId']=urllib.parse.unquote(match.group(1));changed=True
    first_local=next((source for source in sources if isinstance(source,dict) and source.get('type')=='local'),None)
    if first_local:
        for key in ('storedPath','sha256','bytes','mime'):
            if key not in item and key in first_local:item[key]=first_local[key];changed=True
    return changed

def ownership_id(record_type,*parts):
    value=':'.join([record_type,*[str(part) for part in parts]])
    return uuid.uuid5(OWNERSHIP_NAMESPACE,value).hex

def physical_edition_label(format_name, edition=None):
    edition = str(edition or '').strip()
    return format_name if not edition or edition.casefold() == format_name.casefold() else f'{format_name} · {edition}'

def season_label(value):
    return 'Complete series' if value=='complete-series' else 'Specials' if value=='specials' else f'Season {value}' if value else ''

def ownership_record_id(value,fallback):
    return value if isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9._:-]{1,120}',value) else fallback

def physical_records(item,source):
    """Project one compatibility source into the normalized ownership graph."""
    source_id=source['id'];version_id=source['versionId'];format_name=str(source.get('label') or 'Physical').strip()[:120] or 'Physical'
    release_id=ownership_record_id(source.get('physicalReleaseId'),ownership_id('physical-release',source_id))
    copy_id=ownership_record_id(source.get('ownedCopyId'),ownership_id('owned-copy',source_id))
    content_id=ownership_record_id(source.get('packageContentId'),ownership_id('package-content',release_id,item['id'],version_id,format_name))
    changed=False
    for key,value in (('physicalReleaseId',release_id),('ownedCopyId',copy_id),('packageContentId',content_id)):
        if source.get(key)!=value:source[key]=value;changed=True
    version=next((candidate for candidate in item.get('versions',[]) if candidate.get('id')==version_id),item.get('versions',[{}])[0])
    release={
        'id':release_id,
        'title':item.get('title','Untitled'),
        'formats':[format_name],
        'editionLabel':version.get('label',STANDARD_EDITION),
        'recordVersion':1,
        'createdAt':item.get('addedAt',now()),
    }
    for key in ('barcode','creator','publisher','platform','region','catalogNumber'):
        if source.get(key):release[key]=source[key]
    copy={
        'id':copy_id,
        'releaseId':release_id,
        'location':str(source.get('location',''))[:250],
        'condition':str(source.get('condition',''))[:120],
        'completeness':str(source.get('completeness','unknown'))[:120] or 'unknown',
        'status':str(source.get('status','owned'))[:40] or 'owned',
        'addedAt':source.get('addedAt') or item.get('addedAt',now()),
        'recordVersion':1,
    }
    content={
        'id':content_id,
        'releaseId':release_id,
        'itemId':item['id'],
        'versionId':version_id,
        'format':format_name,
        'recordVersion':1,
    }
    for key in ('discCount','volumeCount','partLabel'):
        if key in source:content[key]=source[key]
    for key in ('volume','issue'):
        if source.get(key):content[key]=source[key]
    return release,copy,content,changed

def merged_record(row,base,mirrored=()):
    try:existing=json.loads(row[0]) if row else {}
    except (json.JSONDecodeError,TypeError):existing={}
    result={**base,**existing}
    for key in mirrored:result[key]=base[key]
    return result

def prune_physical_ownership(db):
    db.execute('DELETE FROM owned_copies WHERE id NOT IN (SELECT copy_id FROM physical_source_links)')
    db.execute('DELETE FROM physical_releases WHERE id NOT IN (SELECT release_id FROM owned_copies)')
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='metadata_entities'").fetchone():
        db.execute("DELETE FROM metadata_entities WHERE origin='household-copy' AND NOT EXISTS "
                   "(SELECT 1 FROM metadata_links WHERE metadata_links.entity_id=metadata_entities.id AND relationship='local-release')")

def sync_physical_ownership(db,item,*,prune=True):
    """Keep the compatibility source view and normalized physical records aligned."""
    ensure_item_model(item);current=set();changed=False
    for source in item.get('sources',[]):
        if not isinstance(source,dict) or source.get('type')!='physical':continue
        release,copy,content,source_changed=physical_records(item,source);changed=changed or source_changed;current.add(source['id'])
        release_row=db.execute('SELECT data FROM physical_releases WHERE id=?',(release['id'],)).fetchone()
        release=merged_record(release_row,release)
        known_formats=release.get('formats') if isinstance(release.get('formats'),list) else []
        release['formats']=sorted({str(value).strip() for value in [*known_formats,content['format']] if str(value or '').strip()})
        db.execute('INSERT INTO physical_releases(id,data) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',(release['id'],json.dumps(release)))
        copy_row=db.execute('SELECT data FROM owned_copies WHERE id=?',(copy['id'],)).fetchone()
        copy=merged_record(copy_row,copy,('releaseId','location','status'))
        db.execute('INSERT INTO owned_copies(id,release_id,data) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET release_id=excluded.release_id,data=excluded.data',(copy['id'],release['id'],json.dumps(copy)))
        content_row=db.execute('SELECT data FROM package_contents WHERE id=?',(content['id'],)).fetchone()
        content=merged_record(content_row,content,('releaseId','itemId','versionId','format'))
        db.execute('INSERT INTO package_contents(id,release_id,item_id,version_id,data) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET release_id=excluded.release_id,item_id=excluded.item_id,version_id=excluded.version_id,data=excluded.data',(content['id'],release['id'],item['id'],content['versionId'],json.dumps(content)))
        db.execute('INSERT INTO physical_source_links(source_id,copy_id,content_id,item_id) VALUES(?,?,?,?) ON CONFLICT(source_id) DO UPDATE SET copy_id=excluded.copy_id,content_id=excluded.content_id,item_id=excluded.item_id',(source['id'],copy['id'],content['id'],item['id']))
    obsolete=[row for row in db.execute('SELECT source_id,content_id FROM physical_source_links WHERE item_id=?',(item['id'],)) if row[0] not in current]
    for source_id,content_id in obsolete:
        db.execute('DELETE FROM physical_source_links WHERE source_id=?',(source_id,))
        if not db.execute('SELECT 1 FROM physical_source_links WHERE content_id=?',(content_id,)).fetchone():db.execute('DELETE FROM package_contents WHERE id=?',(content_id,))
    if prune:prune_physical_ownership(db)
    return changed

def migrate_physical_ownership(db):
    for identifier,payload in list(db.execute('SELECT id,data FROM items')):
        item=json.loads(payload);ensure_item_model(item)
        if sync_physical_ownership(db,item,prune=False):db.execute('UPDATE items SET data=? WHERE id=?',(json.dumps(item),identifier))
    prune_physical_ownership(db)


CATALOG_MIGRATIONS = (
    (1, 'alpha-catalog-baseline', (
        'CREATE TABLE IF NOT EXISTS items(id TEXT PRIMARY KEY, data TEXT NOT NULL)',
        'CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY CHECK(id=1),data TEXT NOT NULL)',
        'CREATE TABLE IF NOT EXISTS backup_state(id INTEGER PRIMARY KEY CHECK(id=1),data TEXT NOT NULL)',
        'CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,data TEXT NOT NULL)',
        'CREATE TABLE IF NOT EXISTS connections(id TEXT PRIMARY KEY,data TEXT NOT NULL)',
        'CREATE TABLE IF NOT EXISTS hidden_items(id TEXT PRIMARY KEY,data TEXT NOT NULL)',
        'CREATE TABLE IF NOT EXISTS review_queue(id TEXT PRIMARY KEY,data TEXT NOT NULL)',
    )),
    (2, 'physical-ownership-foundation', (
        'CREATE TABLE IF NOT EXISTS physical_releases(id TEXT PRIMARY KEY,data TEXT NOT NULL)',
        'CREATE TABLE IF NOT EXISTS owned_copies(id TEXT PRIMARY KEY,release_id TEXT NOT NULL,data TEXT NOT NULL,FOREIGN KEY(release_id) REFERENCES physical_releases(id) ON DELETE CASCADE)',
        'CREATE TABLE IF NOT EXISTS package_contents(id TEXT PRIMARY KEY,release_id TEXT NOT NULL,item_id TEXT NOT NULL,version_id TEXT NOT NULL,data TEXT NOT NULL,FOREIGN KEY(release_id) REFERENCES physical_releases(id) ON DELETE CASCADE,FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE CASCADE)',
        'CREATE TABLE IF NOT EXISTS physical_source_links(source_id TEXT PRIMARY KEY,copy_id TEXT NOT NULL,content_id TEXT NOT NULL,item_id TEXT NOT NULL,FOREIGN KEY(copy_id) REFERENCES owned_copies(id) ON DELETE CASCADE,FOREIGN KEY(content_id) REFERENCES package_contents(id) ON DELETE CASCADE,FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE CASCADE)',
        'CREATE INDEX IF NOT EXISTS idx_owned_copies_release ON owned_copies(release_id)',
        'CREATE INDEX IF NOT EXISTS idx_package_contents_release ON package_contents(release_id)',
        'CREATE INDEX IF NOT EXISTS idx_package_contents_item ON package_contents(item_id)',
        'CREATE INDEX IF NOT EXISTS idx_physical_source_links_copy ON physical_source_links(copy_id)',
    )),
    (3, 'owner-profile', (
        'CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,username TEXT NOT NULL UNIQUE COLLATE NOCASE,data TEXT NOT NULL)',
    )),
    (4, 'persistent-owner-sessions', (
        'CREATE TABLE IF NOT EXISTS auth_sessions(id_hash TEXT PRIMARY KEY,profile_id TEXT NOT NULL,expires_at INTEGER NOT NULL,created_at TEXT NOT NULL,remember INTEGER NOT NULL DEFAULT 0,FOREIGN KEY(profile_id) REFERENCES users(id) ON DELETE CASCADE)',
        'CREATE INDEX IF NOT EXISTS idx_auth_sessions_expiry ON auth_sessions(expires_at)',
    )),
    (5, 'read-only-source-inventory', (
        'CREATE TABLE IF NOT EXISTS inventory_batches(id TEXT PRIMARY KEY,source_id TEXT NOT NULL,source_path TEXT NOT NULL,root_identity TEXT NOT NULL,status TEXT NOT NULL,started_at TEXT NOT NULL,finished_at TEXT,scanned INTEGER NOT NULL DEFAULT 0,total_bytes INTEGER NOT NULL DEFAULT 0,errors TEXT NOT NULL DEFAULT "[]")',
        'CREATE INDEX IF NOT EXISTS idx_inventory_batches_source ON inventory_batches(source_id,started_at DESC)',
        'CREATE TABLE IF NOT EXISTS inventory_files(batch_id TEXT NOT NULL,relative_path TEXT NOT NULL,kind TEXT NOT NULL,title TEXT NOT NULL,title_key TEXT NOT NULL,year INTEGER,bytes INTEGER NOT NULL,mtime_ns INTEGER NOT NULL,PRIMARY KEY(batch_id,relative_path),FOREIGN KEY(batch_id) REFERENCES inventory_batches(id) ON DELETE CASCADE)',
        'CREATE INDEX IF NOT EXISTS idx_inventory_files_kind ON inventory_files(batch_id,kind,relative_path)',
        'CREATE INDEX IF NOT EXISTS idx_inventory_files_title ON inventory_files(batch_id,title_key,relative_path)',
    )),
    (6, 'reviewed-linked-media', (
        'CREATE TABLE IF NOT EXISTS item_search(item_id TEXT PRIMARY KEY,kind TEXT NOT NULL,title_key TEXT NOT NULL,year INTEGER,FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE CASCADE)',
        'CREATE INDEX IF NOT EXISTS idx_item_search_title_kind ON item_search(title_key,kind,year)',
        'CREATE TABLE IF NOT EXISTS inventory_links(source_id TEXT NOT NULL,relative_path TEXT NOT NULL,item_id TEXT NOT NULL,media_source_id TEXT NOT NULL UNIQUE,linked_at TEXT NOT NULL,PRIMARY KEY(source_id,relative_path),FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE CASCADE)',
        'CREATE INDEX IF NOT EXISTS idx_inventory_links_item ON inventory_links(item_id)',
    )),
    (7, 'reviewed-catalog-lists', (
        'CREATE TABLE IF NOT EXISTS catalog_import_batches(id TEXT PRIMARY KEY,digest TEXT NOT NULL UNIQUE,source_name TEXT NOT NULL,input_type TEXT NOT NULL,mode TEXT NOT NULL,mapping TEXT NOT NULL,created_at TEXT NOT NULL,total INTEGER NOT NULL)',
        'CREATE TABLE IF NOT EXISTS catalog_import_rows(batch_id TEXT NOT NULL,row_number INTEGER NOT NULL,raw TEXT NOT NULL,proposed TEXT,status TEXT NOT NULL,item_id TEXT,error TEXT NOT NULL DEFAULT "",candidates TEXT NOT NULL DEFAULT "[]",PRIMARY KEY(batch_id,row_number),FOREIGN KEY(batch_id) REFERENCES catalog_import_batches(id) ON DELETE CASCADE)',
        'CREATE INDEX IF NOT EXISTS idx_catalog_import_rows_status ON catalog_import_rows(batch_id,status,row_number)',
        'CREATE TABLE IF NOT EXISTS auto_copy_candidates(source_id TEXT NOT NULL,relative_path TEXT NOT NULL,fingerprint TEXT NOT NULL,bytes INTEGER NOT NULL,kind TEXT NOT NULL,status TEXT NOT NULL,discovered_at TEXT NOT NULL,PRIMARY KEY(source_id,relative_path))',
        'CREATE INDEX IF NOT EXISTS idx_auto_copy_candidates_status ON auto_copy_candidates(source_id,status)',
    )),
    (8, 'local-path-clues-and-title-tokens', (
        "ALTER TABLE inventory_files ADD COLUMN clues TEXT NOT NULL DEFAULT '{}'",
        "ALTER TABLE inventory_files ADD COLUMN group_key TEXT NOT NULL DEFAULT ''",
        'CREATE INDEX IF NOT EXISTS idx_inventory_files_group ON inventory_files(batch_id,group_key,relative_path)',
        'CREATE TABLE IF NOT EXISTS item_search_tokens(item_id TEXT NOT NULL,token TEXT NOT NULL,PRIMARY KEY(item_id,token),FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE CASCADE)',
        'CREATE INDEX IF NOT EXISTS idx_item_search_tokens_token ON item_search_tokens(token,item_id)',
    )),
    (9, 'local-metadata-identity-foundation', (
        "CREATE TABLE metadata_entities(id TEXT PRIMARY KEY,kind TEXT NOT NULL,level TEXT NOT NULL CHECK(level IN ('work','release')),work_id TEXT REFERENCES metadata_entities(id),title TEXT NOT NULL,title_key TEXT NOT NULL,year INTEGER,origin TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL, CHECK((level='work' AND work_id IS NULL) OR (level='release' AND work_id IS NOT NULL)))",
        'CREATE INDEX idx_metadata_entities_title ON metadata_entities(title_key,level,year)',
        'CREATE TABLE metadata_identifiers(entity_id TEXT NOT NULL REFERENCES metadata_entities(id) ON DELETE CASCADE,namespace TEXT NOT NULL,value TEXT NOT NULL,source TEXT NOT NULL,source_record_id TEXT NOT NULL DEFAULT "",source_version TEXT NOT NULL DEFAULT "",license TEXT NOT NULL,imported_at TEXT NOT NULL,PRIMARY KEY(entity_id,namespace,value,source,source_record_id))',
        'CREATE INDEX idx_metadata_identifiers_lookup ON metadata_identifiers(namespace,value)',
        'CREATE TABLE metadata_field_values(entity_id TEXT NOT NULL REFERENCES metadata_entities(id) ON DELETE CASCADE,field TEXT NOT NULL,value_json TEXT NOT NULL,source TEXT NOT NULL,source_record_id TEXT NOT NULL DEFAULT "",source_version TEXT NOT NULL DEFAULT "",license TEXT NOT NULL,imported_at TEXT NOT NULL,owner_entered INTEGER NOT NULL DEFAULT 0 CHECK(owner_entered IN (0,1)),from_pack INTEGER NOT NULL DEFAULT 0 CHECK(from_pack IN (0,1)),PRIMARY KEY(entity_id,field,source,source_record_id))',
        'CREATE TABLE metadata_links(target_type TEXT NOT NULL CHECK(target_type IN ("item","physical_release")),target_id TEXT NOT NULL,entity_id TEXT NOT NULL REFERENCES metadata_entities(id) ON DELETE CASCADE,relationship TEXT NOT NULL,confirmed_at TEXT NOT NULL,PRIMARY KEY(target_type,target_id,entity_id,relationship))',
        'CREATE INDEX idx_metadata_links_target ON metadata_links(target_type,target_id)',
        'CREATE TABLE metadata_artwork_refs(entity_id TEXT NOT NULL REFERENCES metadata_entities(id) ON DELETE CASCADE,role TEXT NOT NULL,reference TEXT NOT NULL,reference_type TEXT NOT NULL CHECK(reference_type IN ("local","remote")),source TEXT NOT NULL,source_record_id TEXT NOT NULL DEFAULT "",rights TEXT NOT NULL,cache_policy TEXT NOT NULL,owner_provided INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(entity_id,role,reference,source))',
        "CREATE TRIGGER metadata_item_link_cleanup AFTER DELETE ON items BEGIN DELETE FROM metadata_links WHERE target_type='item' AND target_id=OLD.id; END",
        "CREATE TRIGGER metadata_release_link_cleanup AFTER DELETE ON physical_releases BEGIN DELETE FROM metadata_links WHERE target_type='physical_release' AND target_id=OLD.id; END",
    )),
    (10, 'collection-intentions', (
        'CREATE TABLE collecting_targets(id TEXT PRIMARY KEY,title TEXT NOT NULL,title_key TEXT NOT NULL,kind TEXT NOT NULL,year INTEGER,desired_format TEXT NOT NULL,created_at TEXT NOT NULL)',
        'CREATE INDEX idx_collecting_targets_title ON collecting_targets(kind,title_key,year)',
        'CREATE UNIQUE INDEX idx_collecting_targets_unique ON collecting_targets(kind,title_key,COALESCE(year,-1),desired_format)',
    )),
    (11, 'completion-sets', (
        "CREATE TABLE completion_sets(id TEXT PRIMARY KEY,name TEXT NOT NULL,kind TEXT NOT NULL CHECK(kind IN ('custom','reference')),media_kind TEXT NOT NULL,source TEXT NOT NULL,source_version TEXT NOT NULL DEFAULT '',source_license TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,updated_at TEXT NOT NULL)",
        "CREATE TABLE completion_members(set_id TEXT NOT NULL REFERENCES completion_sets(id) ON DELETE CASCADE,position INTEGER NOT NULL,title TEXT NOT NULL,title_key TEXT NOT NULL,year INTEGER,desired_format TEXT NOT NULL,work_id TEXT REFERENCES metadata_entities(id) ON DELETE SET NULL,ignored INTEGER NOT NULL DEFAULT 0 CHECK(ignored IN (0,1)),PRIMARY KEY(set_id,position))",
        'CREATE INDEX idx_completion_members_work ON completion_members(work_id)',
    )),
    (12, 'release-format-and-edition', (
        'ALTER TABLE metadata_entities ADD COLUMN format TEXT',
        'ALTER TABLE metadata_entities ADD COLUMN edition TEXT',
        'CREATE INDEX idx_metadata_releases_work ON metadata_entities(work_id,level,format,edition)',
    )),
    (13, 'merged-item-aliases', (
        'CREATE TABLE catalog_item_aliases(alias_id TEXT PRIMARY KEY,item_id TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE,created_at TEXT NOT NULL)',
        'CREATE INDEX idx_catalog_item_aliases_item ON catalog_item_aliases(item_id)',
    )),
    (14, 'release-season-and-observed-identifiers', (
        'ALTER TABLE metadata_entities ADD COLUMN season TEXT',
        'CREATE INDEX idx_metadata_releases_season ON metadata_entities(work_id,season,format,edition)',
    )),
    (15, 'intention-work-identity', (
        'ALTER TABLE collecting_targets ADD COLUMN work_id TEXT REFERENCES metadata_entities(id) ON DELETE SET NULL',
        'ALTER TABLE collecting_targets ADD COLUMN season TEXT',
        'DROP INDEX idx_collecting_targets_unique',
        "CREATE UNIQUE INDEX idx_collecting_targets_unique ON collecting_targets(kind,title_key,COALESCE(year,-1),desired_format,COALESCE(season,''))",
        'CREATE INDEX idx_collecting_targets_work ON collecting_targets(work_id)',
    )),
    (16, 'reviewed-digital-release-links', (
        'DROP TRIGGER metadata_item_link_cleanup',
        'DROP TRIGGER metadata_release_link_cleanup',
        'CREATE TABLE metadata_links_v16(target_type TEXT NOT NULL CHECK(target_type IN ("item","physical_release","digital_source")),target_id TEXT NOT NULL,entity_id TEXT NOT NULL REFERENCES metadata_entities(id) ON DELETE CASCADE,relationship TEXT NOT NULL,confirmed_at TEXT NOT NULL,PRIMARY KEY(target_type,target_id,entity_id,relationship))',
        'INSERT INTO metadata_links_v16 SELECT target_type,target_id,entity_id,relationship,confirmed_at FROM metadata_links',
        'DROP TABLE metadata_links',
        'ALTER TABLE metadata_links_v16 RENAME TO metadata_links',
        'CREATE INDEX idx_metadata_links_target ON metadata_links(target_type,target_id)',
        "CREATE TRIGGER metadata_item_link_cleanup AFTER DELETE ON items BEGIN DELETE FROM metadata_links WHERE target_type='item' AND target_id=OLD.id; END",
        "CREATE TRIGGER metadata_release_link_cleanup AFTER DELETE ON physical_releases BEGIN DELETE FROM metadata_links WHERE target_type='physical_release' AND target_id=OLD.id; END",
    )),
    (17, 'local-collections-and-activity', (
        'CREATE TABLE library_collections(id TEXT PRIMARY KEY,data TEXT NOT NULL)',
        'CREATE TABLE library_collection_members(collection_id TEXT NOT NULL REFERENCES library_collections(id) ON DELETE CASCADE,item_id TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE,position INTEGER NOT NULL,PRIMARY KEY(collection_id,item_id))',
        'CREATE INDEX idx_library_collection_items ON library_collection_members(item_id)',
        "CREATE TABLE activity_events(id TEXT PRIMARY KEY,item_id TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE,status TEXT NOT NULL CHECK(status IN ('not-started','in-progress','completed')),episode_key TEXT NOT NULL DEFAULT '',source_id TEXT,version_id TEXT,profile_id TEXT NOT NULL,origin TEXT NOT NULL,created_at TEXT NOT NULL,undone_at TEXT)",
        'CREATE INDEX idx_activity_item ON activity_events(item_id,episode_key)',
    )),
    (18, 'edition-specific-intentions', (
        "ALTER TABLE collecting_targets ADD COLUMN edition TEXT NOT NULL DEFAULT ''",
        'ALTER TABLE collecting_targets ADD COLUMN release_id TEXT REFERENCES metadata_entities(id) ON DELETE SET NULL',
        'DROP INDEX idx_collecting_targets_unique',
        "CREATE UNIQUE INDEX idx_collecting_targets_unique ON collecting_targets(kind,title_key,COALESCE(year,-1),desired_format,COALESCE(season,''),edition,COALESCE(release_id,''))",
    )),
    (19, 'incremental-library-browse-and-folder-monitoring', migration_statements()),
    (20, 'private-owner-artwork', (
        'CREATE TABLE item_artwork(item_id TEXT PRIMARY KEY REFERENCES items(id) ON DELETE CASCADE,sha256 TEXT NOT NULL,width INTEGER NOT NULL,height INTEGER NOT NULL,mime TEXT NOT NULL CHECK(mime="image/jpeg"),image BLOB NOT NULL,updated_at TEXT NOT NULL)',
    )),
)

def apply_catalog_migrations(db):
    """Apply catalog schema changes in order without rewriting household data."""
    if not db.in_transaction:db.execute('BEGIN IMMEDIATE')
    db.execute('CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY,name TEXT NOT NULL,applied_at TEXT NOT NULL)')
    applied={row[0] for row in db.execute('SELECT version FROM schema_migrations')}
    newer=[version for version in applied if version>CATALOG_SCHEMA_VERSION]
    if newer:raise ValueError(f'Catalog schema {max(newer)} is newer than this Blank Box supports ({CATALOG_SCHEMA_VERSION}).')
    for version,name,statements in CATALOG_MIGRATIONS:
        if version in applied:continue
        for statement in statements:db.execute(statement)
        if version==2:migrate_physical_ownership(db)
        if version==6:
            for row in db.execute('SELECT data FROM items'):
                sync_item_search(db,json.loads(row[0]),include_tokens=False)
        if version==8:
            for row in db.execute('SELECT data FROM items'):
                sync_item_search(db,json.loads(row[0]))
        if version==9:
            for row in db.execute('SELECT data FROM items'):
                backfill_item(db,json.loads(row[0]))
        if version==13:
            for row in db.execute('SELECT data FROM items'):
                sync_source_metadata(db,json.loads(row[0]))
        if version==16:
            for row in db.execute('SELECT data FROM items'):
                sync_digital_releases(db,json.loads(row[0]))
        if version==14:
            for row in db.execute('SELECT data FROM items'):
                sync_owned_releases(db,json.loads(row[0]))
        db.execute('INSERT INTO schema_migrations(version,name,applied_at) VALUES(?,?,?)',(version,name,now()))

class SQLiteCatalogRepository:
    """SQLite persistence seam retained behind the current Box API."""
    def __init__(self,path):self.path=Path(path)
    def connect(self):
        db=sqlite3.connect(self.path,timeout=20);db.row_factory=sqlite3.Row;db.execute('PRAGMA foreign_keys=ON');return db
    def list_items(self):
        with self.connect() as db:return [json.loads(row[0]) for row in db.execute('SELECT data FROM items ORDER BY rowid DESC')]
    def save_item(self,item,*,reviewed_metadata_id=None,reviewed_physical_source_id=None,evidence_namespace=None,evidence_value=None,pack_repository=None,retired_release_ids=(),retired_content_ids=()):
        with self.connect() as db:
            new_item=db.execute('SELECT 1 FROM items WHERE id=?',(item['id'],)).fetchone() is None
            db.execute('INSERT INTO items VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',(item['id'],json.dumps(item)))
            if sync_physical_ownership(db,item):db.execute('UPDATE items SET data=? WHERE id=?',(json.dumps(item),item['id']))
            sync_item_search(db,item)
            backfill_item(db,item)
            sync_owned_releases(db,item)
            sync_digital_releases(db,item)
            for content_id in retired_content_ids:
                db.execute('DELETE FROM package_contents WHERE id=? AND NOT EXISTS (SELECT 1 FROM physical_source_links WHERE content_id=?)',(content_id,content_id))
            for release_id in retired_release_ids:
                if db.execute('SELECT 1 FROM physical_releases WHERE id=?',(release_id,)).fetchone():continue
                db.execute("DELETE FROM metadata_links WHERE target_type='physical_release' AND target_id=?",(release_id,))
                local_id=local_release_id(release_id)
                db.execute("DELETE FROM metadata_entities WHERE id=? AND origin='household-copy' AND NOT EXISTS (SELECT 1 FROM metadata_links WHERE entity_id=?)",(local_id,local_id))
            if reviewed_metadata_id:
                if reviewed_metadata_id.startswith('pack:'):
                    if pack_repository is None:raise ValueError('Metadata pack is not available.')
                    reviewed_metadata_id=pack_repository.materialize(db,reviewed_metadata_id)
                entity=db.execute("SELECT kind,level,work_id FROM metadata_entities WHERE id=?",(reviewed_metadata_id,)).fetchone()
                if not entity or entity['kind']!=item.get('kind'):raise ValueError('The selected metadata record has a different media type or is unavailable.')
                if entity['level']=='release':
                    exact=bool(evidence_namespace and evidence_value and db.execute('SELECT 1 FROM metadata_identifiers WHERE entity_id=? AND namespace=? AND value=?',(reviewed_metadata_id,evidence_namespace,evidence_value)).fetchone())
                    if not exact and physical_namespace(evidence_namespace)=='disc-id' and evidence_value:
                        exact=bool(db.execute("SELECT 1 FROM metadata_identifiers WHERE entity_id=? AND namespace IN ('disc-id','musicbrainz-discid') AND value=?",(reviewed_metadata_id,evidence_value)).fetchone())
                    if not exact and evidence_namespace in ('upc-ean','isbn') and evidence_value:
                        keys=set(barcode_keys(evidence_value))
                        for identity in db.execute("SELECT value FROM metadata_identifiers WHERE entity_id=? AND namespace IN ('upc-ean','isbn')",(reviewed_metadata_id,)):
                            try:exact=bool(keys&set(barcode_keys(identity['value'])))
                            except ValueError:continue
                            if exact:break
                    if not exact:
                        raise ValueError('The selected release lacks exact physical identifier evidence. Review it again.')
                    source=next((entry for entry in item['sources'] if entry['id']==reviewed_physical_source_id and entry.get('type')=='physical'),None)
                    if not source or not source.get('physicalReleaseId'):raise ValueError('The reviewed physical copy is missing.')
                    confirm_entity(db,'physical_release',source['physicalReleaseId'],reviewed_metadata_id)
                    confirm_entity(db,'item',item['id'],entity['work_id'])
                else:confirm_entity(db,'item',item['id'],reviewed_metadata_id)
                # Work matching fills catalog facts. An edition-only match on
                # an existing item keeps its separate household detail choice.
                if new_item or entity['level']=='work':
                    apply_reference_details(db,item,entity['work_id'] if entity['level']=='release' else reviewed_metadata_id)
    def load_item(self,identifier):
        with self.connect() as db:row=db.execute('SELECT data FROM items WHERE id=?',(identifier,)).fetchone()
        return json.loads(row[0]) if row else None
    def physical_inventory_summary(self):
        with self.connect() as db:
            releases={row['id']:json.loads(row['data']) for row in db.execute('SELECT id,data FROM physical_releases WHERE id IN (SELECT release_id FROM owned_copies)')}
            copies=list(db.execute('SELECT id,release_id,data FROM owned_copies'))
            contents=list(db.execute('SELECT release_id,item_id,data FROM package_contents WHERE release_id IN (SELECT release_id FROM owned_copies)'))
        copies_per_release={}
        for copy in copies:copies_per_release[copy['release_id']]=copies_per_release.get(copy['release_id'],0)+1
        formats={};disc_count=0;has_disc_count=False;formats_per_release={}
        for row in contents:
            content=json.loads(row['data']);value=content.get('discCount')
            format_name=str(content.get('format','')).strip()
            if format_name:formats_per_release.setdefault(row['release_id'],set()).add(format_name)
            if isinstance(value,int) and value>=0:
                has_disc_count=True;disc_count+=value*copies_per_release.get(row['release_id'],0)
        for release_id,release in releases.items():
            names=formats_per_release.get(release_id)
            if not names:
                values=release.get('formats') if isinstance(release.get('formats'),list) else [release.get('format')]
                names={str(name).strip() for name in values if str(name or '').strip()}
            for name in names:formats[name]=formats.get(name,0)+copies_per_release.get(release_id,0)
        included={(row['release_id'],row['item_id']) for row in contents}
        return {
            'titles':len({row['item_id'] for row in contents}),
            'packages':len(releases),
            'copies':len(copies),
            'includedTitles':len(included),
            'formats':[{'label':label,'count':count} for label,count in sorted(formats.items())],
            **({'discs':disc_count} if has_disc_count else {}),
        }

class Problem(Exception):
    def __init__(self,message,status=400): self.message=message;self.status=status

def password_record(password):
    if not isinstance(password,str) or not 10<=len(password)<=256:raise Problem('Use a password with at least 10 characters.')
    salt=secrets.token_bytes(16);work_factor=2**14
    value=hashlib.scrypt(password.encode('utf-8'),salt=salt,n=work_factor,r=8,p=1,dklen=32)
    return {'algorithm':'scrypt','n':work_factor,'r':8,'p':1,'salt':base64.b64encode(salt).decode(),'hash':base64.b64encode(value).decode()}

def password_matches(password,record):
    try:
        if not isinstance(password,str) or record.get('algorithm')!='scrypt':return False
        salt=base64.b64decode(record['salt'],validate=True);expected=base64.b64decode(record['hash'],validate=True)
        actual=hashlib.scrypt(password.encode('utf-8'),salt=salt,n=int(record['n']),r=int(record['r']),p=int(record['p']),dklen=len(expected))
        return secrets.compare_digest(actual,expected)
    except (KeyError,TypeError,ValueError):return False

class Box:
    def __init__(self,data,sources=(),backup=None,web=None):
        self.data=reject_links(data).resolve();self.data.mkdir(mode=0o700,parents=True,exist_ok=True);os.chmod(self.data,0o700)
        if (self.data/'.restore-in-progress.json').exists():
            raise ValueError('An interrupted restore requires recovery. Resume the recorded snapshot with maintenance.py before starting Core.')
        # Retain interrupted scratch files for deliberate recovery or cleanup.
        # A name or old marker alone cannot prove that every file is disposable.

        for name in ('media','catalog.sqlite3','catalog.sqlite3-wal','catalog.sqlite3-shm','access-key.txt','metadata-packs','metadata-pack-catalog','bundled-metadata-receipt.json'):
            reject_links(self.data/name)
        self.media=self.data/'media';self.media.mkdir(exist_ok=True);os.chmod(self.media,0o700)
        self.dbfile=self.data/'catalog.sqlite3'
        self.catalog=SQLiteCatalogRepository(self.dbfile)
        self.metadata=SQLiteMetadataRepository(self.catalog.connect)
        self.metadata_packs=MetadataPackSet(self.data/'metadata-packs')
        self.bundled_metadata_errors=install_bundled_packs(self.metadata_packs,self.data)
        self.operation_lock=threading.Lock()
        self.inventory_bulk_plan=None
        self.collection_references=CollectionReferences(self.metadata_packs,operation_lock=self.operation_lock)
        self.metadata_pack_catalog=StagedMetadataCatalog(self.data/'metadata-pack-catalog',self.metadata_packs)
        # The Linux service enters through /opt/blankbox/current. Resolve only
        # this trusted code path before applying the no-symlinks policy to the
        # bundled catalog; household media/data paths still reject links.
        self.metadata_bundled_catalog=StagedMetadataCatalog(Path(__file__).resolve().with_name('bundled-metadata'),self.metadata_packs)
        self.web=Path(web or Path(__file__).parent/'web').resolve()
        self.source_roots={}
        for source in sources:
            p=Path(source).expanduser().resolve()
            if not p.is_dir(): raise ValueError(f'Source directory is unavailable: {p}')
            if inside(p,self.data) or inside(self.data,p): raise ValueError('Source and library folders must not contain one another.')
            self.source_roots[hashlib.sha256(str(p).encode()).hexdigest()[:16]]=p
        self.backup_root=Path(backup).expanduser().resolve() if backup else None
        if self.backup_root:
            if not self.backup_root.is_dir(): raise ValueError('Backup destination must be an existing, mounted directory.')
            if inside(self.backup_root,self.data) or inside(self.data,self.backup_root): raise ValueError('Backup destination and library must not overlap.')
            for root in self.source_roots.values():
                if inside(root,self.backup_root) or inside(self.backup_root,root): raise ValueError('Backup destination and source folders must not overlap.')
            self.backup_identity=(self.backup_root.stat().st_dev,self.backup_root.stat().st_ino)
        self.backup_every_hours=None
        self.state_lock=threading.RLock();self.jobs={};self.scans={};self.attempts={};self.auto_seen={};self.auto_processed={};self.plex_identity_cache={}
        self.token_path=self.data/'access-key.txt'
        if not self.token_path.exists():
            fd=os.open(self.token_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w') as f:f.write(secrets.token_urlsafe(32)+'\n')
        self.token=self.token_path.read_text().strip()
        if len(self.token)<32: raise ValueError('The access key must contain at least 32 characters.')
        with self.db() as db:
            db.execute('PRAGMA journal_mode=WAL')
            apply_catalog_migrations(db)
            db.execute("UPDATE inventory_batches SET status='interrupted' WHERE status='running'")
            db.execute('INSERT OR IGNORE INTO settings VALUES(1,?)',(json.dumps(DEFAULTS),))
            stored_settings=json.loads(db.execute('SELECT data FROM settings WHERE id=1').fetchone()[0])
            if 'autoProviderRefresh' not in stored_settings or 'autoFolderCopy' not in stored_settings:
                # Preserve the owner's old combined switch, but allow each task
                # to be disabled independently from this version forward.
                combined=stored_settings.get('autoImport',False)
                stored_settings['autoProviderRefresh']=combined
                # An older combined switch must not begin copying movies,
                # shows, or music after this index-first upgrade.
                stored_settings['autoFolderCopy']=False
                stored_settings['autoImport']=False
                db.execute('UPDATE settings SET data=? WHERE id=1',(json.dumps(stored_settings),))
            if not all(key in stored_settings for key in ('setupVersion','setupMode','setupStep','mediaProvider','mediaInputs','physicalFormats','physicalLocations','gamePlatforms','gamePlatformCatalogVersion','sidebarShortcuts','sidebarShortcutVersion','streamingServices','remoteProvider')):
                migrated={**DEFAULTS,**stored_settings}
                if 'mediaInputs' not in stored_settings:
                    migrated['mediaInputs']=['jellyfin'] if stored_settings.get('mediaProvider')=='jellyfin' else ['hard-drive','digital-files']
                if stored_settings.get('setupDone') and 'setupVersion' not in stored_settings:
                    migrated.update({'setupVersion':1,'setupMode':'advanced','setupStep':'finish'})
                if 'physicalFormats' not in stored_settings:migrated['physicalFormats']=list(CURRENT_PHYSICAL_FORMATS)
                if 'gamePlatformCatalogVersion' not in stored_settings:
                    previous=stored_settings.get('gamePlatforms',[])
                    migrated['gamePlatforms']=list(COMMON_GAME_PLATFORMS)+[name for name in previous if isinstance(name,str) and name.casefold() not in {platform.casefold() for platform in COMMON_GAME_PLATFORMS}]
                    migrated['gamePlatformCatalogVersion']=1
                if 'sidebarShortcutVersion' not in stored_settings:
                    # The prior release showed Games by default. Remove only
                    # that default; retain every customized selection.
                    if stored_settings.get('sidebarShortcuts')==['game']:migrated['sidebarShortcuts']=[]
                    migrated['sidebarShortcutVersion']=1
                db.execute('UPDATE settings SET data=? WHERE id=1',(json.dumps(migrated),))
            normalized_order=list(dict.fromkeys([mode for mode in stored_settings.get('homeHeroOrder',[]) if mode in HOME_HERO_MODES]+list(HOME_HERO_MODES)))
            if stored_settings.get('homeHeroOrder')!=normalized_order:
                current=json.loads(db.execute('SELECT data FROM settings WHERE id=1').fetchone()[0])
                current['homeHeroOrder']=normalized_order
                db.execute('UPDATE settings SET data=? WHERE id=1',(json.dumps(current),))
            # Keep durable catalog records aligned with the product name. This
            # also adds stable edition/source identities. It never moves media.
            for row in db.execute('SELECT id,data FROM items'):
                item=json.loads(row[1]);changed=False
                for source in item.get('sources',[]):
                    if source.get('label') in ('Home box','Your home box'):
                        source['label']='Blank Box';changed=True
                if ensure_item_model(item):changed=True
                if sync_physical_ownership(db,item,prune=False):changed=True
                if changed:db.execute('UPDATE items SET data=? WHERE id=?',(json.dumps(item),row[0]))
            prune_physical_ownership(db)
            for row in db.execute('SELECT id,data FROM jobs ORDER BY rowid DESC LIMIT 25'):
                job=json.loads(row[1])
                if job['status'] in ('queued','running'):
                    job.update(status='interrupted',message='The box restarted. Run this operation again; source files were not changed.')
                    db.execute('UPDATE jobs SET data=? WHERE id=?',(json.dumps(job),row[0]))
                elif job.get('type')=='inventory-bulk-preview' and job.get('preview'):
                    job.update(status='expired',message='The bulk plan expired after restart. Plan the import again.')
                    job.pop('preview',None)
                    db.execute('UPDATE jobs SET data=? WHERE id=?',(json.dumps(job),row[0]))
                self.jobs[row[0]]=job
        os.chmod(self.dbfile,0o600)
        # Resolve interrupted managed-copy removals by matching complete item and
        # source IDs. Both IDs can contain hyphens, so splitting the filename on
        # hyphens can misidentify a live copy and erase it after a crash.
        recorded_items=self.items()
        for p in self.media.rglob('.blank-box-delete-*'):
            matches=[]
            for item in recorded_items:
                for source in item.get('sources',[]):
                    if source.get('type')!='local':continue
                    if p.name.startswith(f".blank-box-delete-{item['id']}-{source.get('id')}-"):
                        matches.append((item,source))
                # Compatibility with the earlier item-only staging name.
                if p.name==f".blank-box-delete-{item['id']}-{Path(item.get('storedPath') or '').name}":
                    source=next((s for s in item.get('sources',[]) if s.get('type')=='local'),None)
                    if source:matches.append((item,source))
            if len(matches)!=1:
                # An orphan or ambiguous staged copy needs human review. Never
                # erase it merely because an ID cannot be parsed or found.
                continue
            item,source=matches[0]
            try:
                relative=source.get('storedPath') or item.get('storedPath')
                if relative:
                    expected=self.media/relative
                    if not expected.exists():os.replace(p,expected)
                    elif digest(expected)==digest(p):p.unlink(missing_ok=True)
            except (KeyError,OSError,ValueError):pass # Preserve the staged copy for recovery.
        # In-progress copies clean up their own temporary files. After a crash,
        # retain remaining files rather than infer deletion intent from a name.
    @property
    def browse(self):
        with self.state_lock:
            if not hasattr(self,'_browse'):self._browse=LibraryBrowse(self)
            return self._browse
    def db(self):
        return self.catalog.connect()
    def items(self):
        return self.catalog.list_items()
    def put_item(self,item):
        ensure_item_model(item)
        self.catalog.save_item(item)
    def get_item(self,id):
        item=self.catalog.load_item(id)
        if not item:raise Problem('Item not found.',404)
        return item
    def managed_path_referenced_elsewhere(self,relative,item_id,source_id=None):
        for other in self.items():
            for source in other.get('sources',[]):
                if source.get('type')!='local':continue
                if other.get('id')==item_id and (source_id is None or source.get('id')==source_id):continue
                if (source.get('storedPath') or other.get('storedPath'))==relative:return True
        return False
    def catalog_schema_version(self):
        with self.db() as db:return int(db.execute('SELECT COALESCE(MAX(version),0) FROM schema_migrations').fetchone()[0])
    def has_profile(self):
        with self.db() as db:return bool(db.execute('SELECT 1 FROM users LIMIT 1').fetchone())
    def create_owner_profile(self,username,display_name,password):
        username=str(username or '').strip();display_name=str(display_name or '').strip()
        if not re.fullmatch(r'[A-Za-z0-9._-]{3,32}',username):raise Problem('Use 3 to 32 letters, numbers, dots, dashes, or underscores for the username.')
        if not 1<=len(display_name)<=60:raise Problem('Enter a display name up to 60 characters.')
        profile={'id':uuid.uuid4().hex,'username':username,'displayName':display_name,'role':'owner','password':password_record(password),'createdAt':now()}
        try:
            with self.db() as db:
                if db.execute('SELECT 1 FROM users LIMIT 1').fetchone():raise Problem('The owner profile is already set up.',409)
                db.execute('INSERT INTO users(id,username,data) VALUES(?,?,?)',(profile['id'],username,json.dumps(profile)))
        except sqlite3.IntegrityError:raise Problem('That username is already in use.',409)
        return self.public_profile(profile)
    def authenticate_profile(self,username,password):
        if not isinstance(username,str) or not isinstance(password,str):return None
        with self.db() as db:row=db.execute('SELECT data FROM users WHERE username=? COLLATE NOCASE',(username.strip(),)).fetchone()
        if not row:return None
        try:profile=json.loads(row[0])
        except (TypeError,json.JSONDecodeError):return None
        return self.public_profile(profile) if password_matches(password,profile.get('password',{})) else None
    def recover_owner_profile(self,username,password):
        if not isinstance(username,str):raise Problem('Enter the owner username.')
        with self.db() as db:
            row=db.execute('SELECT id,data FROM users WHERE username=? COLLATE NOCASE',(username.strip(),)).fetchone()
            if not row:raise Problem('That owner profile was not found.',404)
            profile=json.loads(row['data']);profile['password']=password_record(password);profile['passwordUpdatedAt']=now()
            db.execute('UPDATE users SET data=? WHERE id=?',(json.dumps(profile),row['id']))
            db.execute('DELETE FROM auth_sessions WHERE profile_id=?',(row['id'],))
        return self.public_profile(profile)
    def create_auth_session(self,profile_id,remember=False):
        if not self.profile(profile_id):raise Problem('Owner profile not found.',404)
        token=secrets.token_urlsafe(32);expires=int(time.time()+(60*60*24*90 if remember else 60*60*24))
        with self.db() as db:
            db.execute('DELETE FROM auth_sessions WHERE expires_at<=?',(int(time.time()),))
            db.execute('INSERT INTO auth_sessions(id_hash,profile_id,expires_at,created_at,remember) VALUES(?,?,?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),profile_id,expires,now(),1 if remember else 0))
        return token,expires
    def auth_session_profile(self,token):
        if not token:return None
        key=hashlib.sha256(token.encode()).hexdigest();current=int(time.time())
        with self.db() as db:
            row=db.execute('SELECT profile_id,expires_at FROM auth_sessions WHERE id_hash=?',(key,)).fetchone()
            if not row:return None
            if row['expires_at']<=current:
                db.execute('DELETE FROM auth_sessions WHERE id_hash=?',(key,));return None
            return row['profile_id'] if self.profile(row['profile_id']) else None
    def profile(self,identifier):
        if not identifier:return None
        with self.db() as db:row=db.execute('SELECT data FROM users WHERE id=?',(identifier,)).fetchone()
        if not row:return None
        try:return self.public_profile(json.loads(row[0]))
        except (TypeError,json.JSONDecodeError):return None
    @staticmethod
    def public_profile(profile):
        return {key:profile[key] for key in ('id','username','displayName','role') if key in profile}
    def liveness(self):
        return {'status':'alive','product':'Blank Box','version':VERSION,'apiVersion':1}
    def readiness(self):
        """Return a small, credential-free service check for installers and supervisors."""
        try:
            if not self.web.joinpath('index.html').is_file():raise ValueError('Web client is unavailable.')
            if not self.data.is_dir() or not os.access(self.data,os.R_OK|os.W_OK):raise ValueError('Data directory is unavailable.')
            if not self.media.is_dir() or not os.access(self.media,os.R_OK|os.W_OK):raise ValueError('Media directory is unavailable.')
            with self.db() as db:
                if db.execute('SELECT 1').fetchone()[0]!=1:raise ValueError('Catalog is unavailable.')
            return {'status':'ready','product':'Blank Box','version':VERSION,'apiVersion':1,'catalogSchemaVersion':self.catalog_schema_version()},200
        except (OSError,sqlite3.Error,ValueError):
            return {'status':'not-ready','product':'Blank Box','version':VERSION,'apiVersion':1},503
    def remove_item(self,id):
        item=self.get_item(id);ensure_item_model(item);staged=[]
        try:
            seen_paths=set()
            for media_source in item.get('sources',[]):
                if media_source.get('type')!='local':continue
                relative=media_source.get('storedPath') or item.get('storedPath')
                if not relative or relative in seen_paths:continue
                seen_paths.add(relative)
                if self.managed_path_referenced_elsewhere(relative,item['id']):continue
                source=safe_file(self.media,relative);expected=media_source.get('sha256') or item.get('sha256')
                if expected and digest(source)!=expected:raise Problem('A managed copy changed. Verify or restore it before removing the record.',409)
                pending=source.with_name('.blank-box-delete-'+item['id']+'-'+media_source['id']+'-'+source.name)
                if pending.exists():raise Problem('A previous removal needs recovery before this copy can be removed.',409)
                os.replace(source,pending);staged.append((pending,relative))
            with self.db() as db:
                provider_sources=[source for source in item.get('sources',[]) if source.get('type') in ('jellyfin','plex')]
                organization=hidden_organization(db,item['id']) if provider_sources and len(provider_sources)==len(item.get('sources',[])) else None
                for provider_source in provider_sources:
                    provider=provider_source['type'];provider_id=str(provider_source.get('providerItemId') or item['id'].removeprefix(provider+'-'))
                    hidden_id=provider+'-'+provider_id
                    hidden_item={'id':hidden_id,'title':item.get('title','Untitled'),'kind':item.get('kind','movie'),'year':item.get('year'),'description':item.get('description'),'sources':[provider_source],'addedAt':item.get('addedAt',now())}
                    if item.get('customGenres'):hidden_item['customGenres']=item['customGenres']
                    hidden={'item':hidden_item,'hiddenAt':now(),'source':provider}
                    if organization:hidden['organization']=organization
                    db.execute('INSERT INTO hidden_items VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',(hidden_id,json.dumps(hidden)))
                db.execute("DELETE FROM metadata_artwork_refs WHERE entity_id=? AND source='owner-upload'",(local_work_id(id),))
                db.execute('DELETE FROM items WHERE id=?',(id,))
                for media_source in item.get('sources',[]):
                    if media_source.get('type') in ('local','digital') and media_source.get('id'):
                        remove_digital_source_links(db,media_source['id'])
                prune_physical_ownership(db)
        except Exception:
            for pending,relative in staged:
                if pending.exists():os.replace(pending,self.media/relative)
            raise
        cleanup_pending=False
        for pending,_ in staged:
            try:pending.unlink(missing_ok=True)
            except OSError:cleanup_pending=True;continue
            parent=pending.parent
            while parent!=self.media:
                try:parent.rmdir()
                except OSError:break
                parent=parent.parent
        return {'ok':True,'removedCopy':bool(staged),**({'cleanupPending':True} if cleanup_pending else {})}
    def hidden_records(self,limit=-1,offset=0):
        with self.db() as db:rows=list(db.execute('SELECT id,data FROM hidden_items ORDER BY id LIMIT ? OFFSET ?',(limit,offset)))
        records=[]
        for hidden_id,raw in rows:
            try:
                hidden=json.loads(raw);item=hidden.get('item',{})
                records.append({'id':hidden_id,'title':str(item.get('title') or 'Untitled'),'kind':str(item.get('kind') or 'file'),'source':str(hidden.get('source') or 'Connected source'),'hiddenAt':hidden.get('hiddenAt')})
            except (TypeError,ValueError,AttributeError):
                records.append({'id':hidden_id,'title':'Unreadable hidden record','kind':'file','source':'Unknown','hiddenAt':None})
        return records
    def restore_hidden(self,hidden_id=None):
        if hidden_id is not None and (not isinstance(hidden_id,str) or not hidden_id):raise Problem('Choose a hidden item to restore.')
        with self.db() as db:
            rows=list(db.execute('SELECT id,data FROM hidden_items WHERE id=?',(hidden_id,))) if hidden_id else list(db.execute('SELECT id,data FROM hidden_items'))
            if hidden_id and not rows:raise Problem('That hidden item is no longer available.',404)
            # Validate the whole requested batch before writing any row. A
            # collision must never replace a newer catalog item.
            checked=[]
            for row in rows:
                try:hidden=json.loads(row[1]);item=hidden.get('item')
                except (TypeError,ValueError,AttributeError):raise Problem('A hidden record is damaged. Nothing was restored.',409)
                if not isinstance(item,dict) or item.get('id')!=row[0]:raise Problem('A hidden record is damaged. Nothing was restored.',409)
                if db.execute('SELECT 1 FROM items WHERE id=?',(row[0],)).fetchone():raise Problem('A catalog item already uses this ID. Nothing was overwritten.',409)
                checked.append((row[0],item,hidden.get('organization') or {}))
            for item_id,item,organization in checked:
                ensure_item_model(item);db.execute('INSERT INTO items VALUES(?,?)',(item_id,json.dumps(item)))
                if sync_physical_ownership(db,item):db.execute('UPDATE items SET data=? WHERE id=?',(json.dumps(item),item_id))
                sync_item_search(db,item)
                backfill_item(db,item)
                sync_owned_releases(db,item)
                restore_organization(db,item_id,organization)
                db.execute('DELETE FROM hidden_items WHERE id=?',(item_id,))
        return {'ok':True,'restored':len(rows)}
    def search_matches(self,query,exclude=None,scope='all'):
        query=str(query or '').strip().lower()
        if not 1<=len(query)<=200:raise Problem('Enter a title to search.')
        if scope not in ('all','connected','household'):raise Problem('Choose a valid library source.')
        words=[word for word in re.split(r'\W+',query) if word]
        normalized_query=title_key(query)
        matches=[]
        for item in self.items():
            if item['id']==exclude:continue
            sources=item.get('sources',[])
            connected=any(source.get('type') in ('jellyfin','plex') for source in sources)
            household=not sources or any(source.get('type') not in ('jellyfin','plex') for source in sources)
            if scope=='connected' and not connected or scope=='household' and not household:continue
            haystack=f"{item.get('title','')} {item.get('year','')} {item.get('genre','')}".lower()
            normalized_title=work_title_key(item.get('title'))
            if query not in haystack and not all(word in haystack for word in words) and not (len(normalized_query)>=3 and normalized_query in normalized_title):continue
            public=self.public_item(item)
            public['score']=(100 if item.get('title','').lower()==query or normalized_query==normalized_title else 50)+sum(haystack.count(word) for word in words)
            matches.append(public)
        matches.sort(key=lambda item:(-item['score'],item['title']))
        return {'results':matches[:25]}
    def match_candidates(self,incoming,exclude=None,compatible_kinds=False):
        key=work_title_key(incoming.get('title'))
        if not key:return []
        incoming_kind=incoming.get('kind')
        allowed_kinds={'movie','tv'} if compatible_kinds and incoming_kind in ('movie','tv') else {incoming_kind}
        with self.db() as db:pending_ids={json.loads(row[0]).get('incoming',{}).get('id') for row in db.execute('SELECT data FROM review_queue')}
        candidates=[]
        for item in self.items():
            if item.get('id')==exclude or item.get('id') in pending_ids or item.get('kind') not in allowed_kinds or work_title_key(item.get('title'))!=key:continue
            same_year=bool(item.get('year') and incoming.get('year') and item.get('year')==incoming.get('year'))
            year_conflict=bool(item.get('year') and incoming.get('year') and item.get('year')!=incoming.get('year'))
            if year_conflict:continue
            candidate=self.public_item(item);candidate['matchConfidence']='high' if same_year else 'review'
            same_kind=item.get('kind')==incoming_kind
            candidate['matchReason']='Same title, year, and media type' if same_year and same_kind else ('Same title and media type; confirm the year or edition' if same_kind else 'Same video title; confirm whether this disc belongs with the movie or TV record')
            candidate['metadataScore']=sum(1 for field in METADATA_FIELDS if item.get(field) not in (None,''))+min(len(str(item.get('description','')))//200,5)
            candidates.append(candidate)
        candidates.sort(key=lambda item:(item['matchConfidence']!='high',-item['metadataScore'],item.get('addedAt','')))
        return candidates[:12]
    def provider_owner(self,provider_item_id,provider):
        if not provider_item_id:return None
        for item in self.items():
            for source in item.get('sources',[]):
                if source.get('type')==provider and source.get('providerItemId')==provider_item_id:return item
        return None
    def provider_sync_index(self,provider):
        """Build one catalog lookup for a full provider pass, not one per title."""
        owners={};titles={}
        for item in self.items():
            titles.setdefault((item.get('kind'),work_title_key(item.get('title'))),set()).add(item['id'])
            for source in item.get('sources',[]):
                if source.get('type')==provider and source.get('providerItemId'):
                    owners[source['providerItemId']]=item['id']
        return owners,titles
    def merge_items(self,target_id,incoming,metadata_policy='keep',edition_policy='same',allow_kind_change=False,force_metadata=False):
        if metadata_policy not in ('keep','incoming'):raise Problem('Choose how Blank Box should handle metadata.')
        if edition_policy not in ('same','new'):raise Problem('Choose whether this is the same or a new edition.')
        target=self.get_item(target_id);ensure_item_model(target);ensure_item_model(incoming)
        if target.get('kind')!=incoming.get('kind') and (not allow_kind_change or not compatible_media_kinds(target.get('kind'),incoming.get('kind'))):raise Problem('These records are different kinds of media. Match movies, TV, and video together; keep books, music, photos, and unrelated files separate.')
        overrides=set(target.get('metadataOverrides',[]));provenance=target.setdefault('metadataProvenance',{})
        provider_sources=[source for source in incoming.get('sources',[]) if source.get('type') in ('jellyfin','plex') and source.get('providerItemId')]
        provider_source=next((source for source in provider_sources if source.get('id')==incoming.get('metadataPreference')),next(iter(provider_sources),None))
        if provider_source and not provider_source.get('metadataSnapshot'):
            provider_source['metadataSnapshot']=metadata_snapshot(incoming)
        matching_source=next((source for source in target['sources'] if provider_source and source.get('type')==provider_source.get('type') and source.get('providerItemId')==provider_source.get('providerItemId')),None)
        preferred=target.get('metadataPreference')
        if provider_source and preferred in (None,'blankbox') and not target.get('blankboxMetadataSnapshot'):
            target['blankboxMetadataSnapshot']=metadata_snapshot(target)
        can_apply=force_metadata or preferred is None or preferred in ((matching_source or provider_source or {}).get('id'),)
        for field in METADATA_FIELDS:
            value=incoming.get(field)
            if not can_apply or field in overrides and not force_metadata or value in (None,''):continue
            if metadata_policy=='incoming' or target.get(field) in (None,''):
                target[field]=value
                previous=(incoming.get('metadataProvenance') or {}).get(field)
                provenance[field]=dict(previous) if isinstance(previous,dict) else {'source':incoming.get('metadataProvider','connected source'),'updatedAt':now()}
                if force_metadata:overrides.discard(field)
        if force_metadata:target['metadataOverrides']=sorted(overrides)
        if incoming.get('customGenres'):
            target['customGenres']=collection_labels(list(dict.fromkeys(target.get('customGenres',[])+incoming['customGenres'])))
        incoming_version=incoming['versions'][0]
        if edition_policy=='new':
            label=incoming_version.get('label') or edition_label(incoming.get('title'))
            if label==STANDARD_EDITION:label='Additional edition'
            version={'id':uuid.uuid4().hex,'label':label}
            for field in ('year','duration','notes'):
                if field in incoming_version:version[field]=incoming_version[field]
            target['versions'].append(version);version_id=version['id']
        else:
            wanted=incoming_version.get('label',STANDARD_EDITION)
            version=next((version for version in target['versions'] if version.get('label')==wanted),target['versions'][0])
            version_id=version['id']
        existing_keys={(source.get('type'),source.get('providerItemId'),source.get('sha256'),source.get('sourceId'),source.get('path'),source.get('location')) for source in target['sources']}
        for source in incoming.get('sources',[]):
            identity=(source.get('type'),source.get('providerItemId'),source.get('sha256'),source.get('sourceId'),source.get('path'),source.get('location'))
            if identity in existing_keys:
                current=next(existing for existing in target['sources'] if (existing.get('type'),existing.get('providerItemId'),existing.get('sha256'),existing.get('sourceId'),existing.get('path'),existing.get('location'))==identity)
                for key,value in source.items():
                    if key not in ('id','versionId','storedPath','sha256'):current[key]=value
                continue
            source=dict(source);source['id']=source.get('id') or uuid.uuid4().hex;source['versionId']=version_id
            target['sources'].append(source);existing_keys.add(identity)
        if provider_source and metadata_policy=='keep' and target.get('metadataPreference') is None:
            target['metadataPreference']='blankbox'
        if provider_source and (force_metadata or metadata_policy=='incoming' and preferred is None):
            selected=next((source for source in target['sources'] if source.get('type')==provider_source.get('type') and source.get('providerItemId')==provider_source.get('providerItemId')),None)
            if selected:target['metadataPreference']=selected['id']
        selected=next((source for source in target['sources'] if source.get('id')==target.get('metadataPreference') and source.get('type') in ('jellyfin','plex')),None)
        if selected:apply_metadata_choice(target,selected)
        if metadata_policy=='incoming' or not target.get('metadataMatch'):
            target['metadataMatch']={'type':'library','itemId':incoming.get('id','incoming'),'matchedAt':now()}
        ensure_item_model(target)
        if str(target.get('poster','')).startswith('/media/'+str(incoming.get('id',''))):
            local_source=next((source for source in target['sources'] if source.get('type')=='local' and source.get('url')),None)
            if local_source:target['poster']=local_source['url']
        with self.db() as db:
            if incoming.get('id') and incoming.get('id')!=target['id']:
                incoming_art=db.execute('SELECT sha256,width,height,mime,image,updated_at FROM item_artwork WHERE item_id=?',(incoming['id'],)).fetchone()
                existing_art=db.execute('SELECT sha256 FROM item_artwork WHERE item_id=?',(target['id'],)).fetchone()
                if existing_art:
                    local_cover=artwork_url(target['id'],existing_art['sha256'])
                    target.setdefault('blankboxMetadataSnapshot',metadata_snapshot(target))['poster']=local_cover
                    if str(target.get('poster','')).startswith('/api/artwork/'+incoming['id']+'/'):
                        if target.get('metadataPreference') in (None,'blankbox'):target['poster']=local_cover
                        else:target.pop('poster',None)
                if incoming_art and not existing_art:
                    local_cover=artwork_url(target['id'],incoming_art['sha256'])
                    target.setdefault('blankboxMetadataSnapshot',metadata_snapshot(target))['poster']=local_cover
                    if target.get('metadataPreference') in (None,'blankbox'):
                        target['poster']=local_cover
                    db.execute('INSERT INTO item_artwork VALUES(?,?,?,?,?,?,?)',
                               (target['id'],incoming_art['sha256'],incoming_art['width'],incoming_art['height'],incoming_art['mime'],incoming_art['image'],incoming_art['updated_at']))
                    local_id=local_work_id(target['id'])
                    backfill_item(db,target)
                    db.execute("DELETE FROM metadata_artwork_refs WHERE entity_id=? AND source='owner-upload'",(local_id,))
                    db.execute('INSERT INTO metadata_artwork_refs(entity_id,role,reference,reference_type,source,source_record_id,rights,cache_policy,owner_provided) VALUES(?,?,?,?,?,?,?,?,1)',
                               (local_id,'cover',local_cover,'local','owner-upload',incoming_art['sha256'],'owner-provided','private-local'))
            db.execute('INSERT INTO items VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',(target['id'],json.dumps(target)))
            if sync_physical_ownership(db,target):db.execute('UPDATE items SET data=? WHERE id=?',(json.dumps(target),target['id']))
            sync_item_search(db,target)
            backfill_item(db,target)
            sync_owned_releases(db,target)
            sync_digital_releases(db,target)
            if incoming.get('id') and incoming.get('id')!=target['id']:
                db.execute('UPDATE inventory_links SET item_id=? WHERE item_id=?',(target['id'],incoming['id']))
            if incoming.get('id') and incoming.get('id')!=target['id']:
                incoming_id=incoming['id']
                for link in db.execute("SELECT entity_id,relationship,confirmed_at FROM metadata_links WHERE target_type='item' AND target_id=?",(incoming_id,)).fetchall():
                    kind=db.execute('SELECT kind FROM metadata_entities WHERE id=?',(link['entity_id'],)).fetchone()
                    if kind and kind['kind']==target['kind']:
                        relationship='merged-work' if link['relationship']=='local-work' else link['relationship']
                        db.execute('INSERT OR IGNORE INTO metadata_links VALUES(?,?,?,?,?)',('item',target['id'],link['entity_id'],relationship,link['confirmed_at']))
                db.execute('UPDATE catalog_item_aliases SET item_id=? WHERE item_id=?',(target['id'],incoming_id))
                merge_collection_activity(db,target['id'],incoming_id)
                db.execute("DELETE FROM metadata_artwork_refs WHERE entity_id=? AND source='owner-upload'",(local_work_id(incoming_id),))
                db.execute('DELETE FROM items WHERE id=?',(incoming_id,))
                db.execute('INSERT INTO catalog_item_aliases(alias_id,item_id,created_at) VALUES(?,?,?) ON CONFLICT(alias_id) DO UPDATE SET item_id=excluded.item_id',
                           (incoming_id,target['id'],now()))
            prune_physical_ownership(db)
        return target
    def choose_metadata_source(self,item_id,source_id,replace_edits=False):
        if source_id!='blankbox' and (not isinstance(source_id,str) or not re.fullmatch(r'[A-Za-z0-9._:-]{1,120}',source_id)):
            raise Problem('Choose Blank Box, Jellyfin, or Plex metadata.')
        with self.db() as db:
            row=db.execute('SELECT data FROM items WHERE id=?',(item_id,)).fetchone()
            if not row:raise Problem('That library item was not found.',404)
            item=json.loads(row[0]);source=next((value for value in item.get('sources',[]) if value.get('id')==source_id and value.get('type') in ('jellyfin','plex')),None)
            if source_id!='blankbox' and not source:raise Problem('That connected metadata source is no longer attached.',404)
            if source and item.get('metadataPreference') in (None,'blankbox') and not item.get('blankboxMetadataSnapshot'):
                item['blankboxMetadataSnapshot']=metadata_snapshot(item)
            if source_id=='blankbox' and not item.get('blankboxMetadataSnapshot'):
                # A provider-only item has no earlier household baseline. Copy
                # its current effective facts so Blank Box remains usable offline.
                item['blankboxMetadataSnapshot']=metadata_snapshot(item)
            if replace_edits:
                available=metadata_snapshot(source.get('metadataSnapshot') or {}) if source else metadata_snapshot(item.get('blankboxMetadataSnapshot') or {})
                overrides=set(item.get('metadataOverrides',[]))
                if 'catalogDetails' in overrides and 'catalogDetails' in available:
                    overrides.remove('catalogDetails');overrides.update('catalogDetails.'+key for key in item.get('catalogDetails',{}))
                cleared=(set(available)-{'kind','catalogDetails'})|{'catalogDetails.'+key for key in available.get('catalogDetails',{})}
                item['metadataOverrides']=sorted(overrides-cleared)
            apply_metadata_choice(item,source)
            item['metadataPreference']=source_id
            db.execute('UPDATE items SET data=? WHERE id=?',(json.dumps(item),item_id))
            sync_item_search(db,item)
            backfill_item(db,item)
        return {'ok':True,'item':self.public_item(item)}
    def missing_provider_covers(self):
        connected={provider:bool(self.connection(provider)) for provider in ('jellyfin','plex')}
        count=waiting=0
        with self.db() as db:
            protected={row[0] for row in db.execute('SELECT item_id FROM item_artwork')}
            for row in db.execute('SELECT id,data FROM items'):
                if row['id'] in protected:continue
                item=json.loads(row['data'])
                if saved_provider_cover(item,connected):count+=1
                elif saved_provider_cover(item,{'jellyfin':True,'plex':True}):waiting+=1
        return {'count':count,'waitingForConnection':waiting,'connected':connected}
    def restore_missing_provider_covers(self,expected_count):
        if type(expected_count) is not int or expected_count<1:raise Problem('Review the missing cover count first.')
        def worker(job):
            connected={provider:bool(self.connection(provider)) for provider in ('jellyfin','plex')}
            with self.db() as db:
                protected={row[0] for row in db.execute('SELECT item_id FROM item_artwork')}
                updates=[]
                for row in db.execute('SELECT id,data FROM items'):
                    if row['id'] in protected:continue
                    item=json.loads(row['data']);chosen=saved_provider_cover(item,connected)
                    if not chosen:continue
                    source,reference=chosen
                    item['poster']=reference
                    item.setdefault('metadataProvenance',{})['poster']={'source':source['type'].title(),'sourceId':source['id'],'updatedAt':now()}
                    updates.append((json.dumps(item),row['id']))
                if len(updates)!=expected_count:raise ValueError('The missing cover count changed. Review it again before restoring covers.')
                db.executemany('UPDATE items SET data=? WHERE id=?',updates)
            job['done']=job['total']=len(updates)
            job['message']=f'{len(updates)} missing provider cover links restored. Titles, other metadata, and uploaded covers were unchanged.'
        return self.start_job('restore-provider-covers',worker)
    def save_owner_artwork(self,item_id,image):
        try:width,height=jpeg_size(image)
        except ValueError as error:raise Problem(str(error),415) from error
        checksum=artwork_hash(image);reference=artwork_url(item_id,checksum)
        with self.db() as db:
            row=db.execute('SELECT data FROM items WHERE id=?',(item_id,)).fetchone()
            if not row:raise Problem('That library item was not found.',404)
            item=json.loads(row[0]);backfill_item(db,item)
            local_id=local_work_id(item_id)
            previous=db.execute('SELECT sha256 FROM item_artwork WHERE item_id=?',(item_id,)).fetchone()
            old_reference=artwork_url(item_id,previous['sha256']) if previous else None
            baseline=item.get('blankboxMetadataSnapshot') or metadata_snapshot(item)
            baseline['poster']=reference;item['blankboxMetadataSnapshot']=baseline
            if item.get('metadataPreference') in (None,'blankbox') or item.get('poster')==old_reference:
                item['poster']=reference
                item.setdefault('metadataProvenance',{})['poster']={'source':'Blank Box owner artwork','entityId':local_id,'updatedAt':now()}
            item['metadataOverrides']=sorted(set(item.get('metadataOverrides',[]))-{'poster'})
            db.execute('INSERT INTO item_artwork VALUES(?,?,?,?,?,?,?) ON CONFLICT(item_id) DO UPDATE SET sha256=excluded.sha256,width=excluded.width,height=excluded.height,image=excluded.image,updated_at=excluded.updated_at',
                       (item_id,checksum,width,height,'image/jpeg',image,now()))
            db.execute("DELETE FROM metadata_artwork_refs WHERE entity_id=? AND source='owner-upload'",(local_id,))
            db.execute('INSERT INTO metadata_artwork_refs(entity_id,role,reference,reference_type,source,source_record_id,rights,cache_policy,owner_provided) VALUES(?,?,?,?,?,?,?,?,1)',
                       (local_id,'cover',reference,'local','owner-upload',checksum,'owner-provided','private-local'))
            db.execute('UPDATE items SET data=? WHERE id=?',(json.dumps(item),item_id))
        return {'ok':True,'item':self.public_item(item),'artwork':reference}
    def remove_owner_artwork(self,item_id):
        with self.db() as db:
            row=db.execute('SELECT data FROM items WHERE id=?',(item_id,)).fetchone()
            if not row:raise Problem('That library item was not found.',404)
            item=json.loads(row[0]);previous=db.execute('SELECT sha256 FROM item_artwork WHERE item_id=?',(item_id,)).fetchone()
            if not previous:return {'ok':True,'item':self.public_item(item)}
            reference=artwork_url(item_id,previous['sha256'])
            baseline=item.get('blankboxMetadataSnapshot') or {}
            if baseline.get('poster')==reference:baseline.pop('poster',None)
            item['blankboxMetadataSnapshot']=baseline
            if item.get('poster')==reference:item.pop('poster',None)
            db.execute('DELETE FROM item_artwork WHERE item_id=?',(item_id,))
            db.execute("DELETE FROM metadata_artwork_refs WHERE entity_id=? AND source='owner-upload'",(local_work_id(item_id),))
            db.execute('UPDATE items SET data=? WHERE id=?',(json.dumps(item),item_id))
        return {'ok':True,'item':self.public_item(item)}
    def artwork_candidates(self,item_id):
        item=self.get_item(item_id);result=[];seen=set()
        for source in item.get('sources',[]):
            if source.get('type') not in ('local','digital') or not source.get('id'):continue
            for root,rel,root_identity in self.artwork_locations(item,source):
                for path in folder_cover_paths(root/rel.parent,rel.stem):
                    candidate=rel.parent/path.name
                    try:
                        with open_linked_file(root,str(candidate),root_identity) as opened:
                            if not 0<os.fstat(opened.fileno()).st_size<=12*1024*1024:continue
                    except (OSError,ValueError):continue
                    key=(source['id'],path.name)
                    if key in seen:continue
                    seen.add(key);result.append({'sourceId':source['id'],'name':path.name,'label':source.get('label') or 'Local file'})
                    if len(result)>=8:return result
        return result
    def artwork_locations(self,item,source):
        locations=[]
        if source.get('sourceId') and source.get('path'):
            root=self.source_roots.get(source['sourceId'])
            if root:locations.append((root,source['path'],source.get('rootIdentity')))
        if source.get('type')=='local' and (source.get('storedPath') or item.get('storedPath')):
            locations.append((self.media,source.get('storedPath') or item['storedPath'],None))
        for root,relative,root_identity in locations:
            rel=Path(relative)
            if not rel.is_absolute() and '..' not in rel.parts and '.' not in rel.parts:
                yield root,rel,root_identity
    def open_artwork_candidate(self,item_id,source_id,name):
        item=self.get_item(item_id)
        source=next((entry for entry in item.get('sources',[]) if entry.get('id')==source_id and entry.get('type') in ('local','digital')),None)
        if not source:raise Problem('That source was not found.',404)
        if not isinstance(name,str):raise Problem('That artwork file is unavailable.',404)
        if name not in {entry['name'] for entry in self.artwork_candidates(item_id) if entry['sourceId']==source_id}:
            raise Problem('That artwork file is unavailable.',404)
        for root,rel,root_identity in self.artwork_locations(item,source):
            if name not in {path.name for path in folder_cover_paths(root/rel.parent,rel.stem)}:continue
            try:
                opened=open_linked_file(root,str(rel.parent/name),root_identity)
                if 0<os.fstat(opened.fileno()).st_size<=12*1024*1024:return opened
                opened.close()
            except (OSError,ValueError):continue
        raise Problem('That artwork file is unavailable.',404)
    def queue_review(self,incoming,candidates,source):
        review={'id':uuid.uuid4().hex,'source':source,'incoming':incoming,'candidateIds':[candidate['id'] for candidate in candidates],'createdAt':now()}
        with self.db() as db:db.execute('INSERT INTO review_queue VALUES(?,?)',(review['id'],json.dumps(review)))
        return review
    def reviews(self,limit=100):
        with self.db() as db:rows=list(db.execute('SELECT data FROM review_queue ORDER BY rowid LIMIT ?',(limit,)))
        result=[]
        for row in rows:
            review=json.loads(row[0]);incoming=review.get('incoming',{});candidates=[]
            for candidate_id in review.get('candidateIds',[]):
                try:candidates.append(self.public_item(self.get_item(candidate_id)))
                except Problem:pass
            result.append({'id':review['id'],'source':review.get('source','import'),'createdAt':review.get('createdAt'),'incoming':self.public_item(incoming),'candidates':candidates})
        return result
    def resolve_review(self,review_id,policy,target_id=None):
        if policy not in ('keep','incoming','new-version','separate'):raise Problem('Choose how to handle this match.')
        with self.db() as db:row=db.execute('SELECT data FROM review_queue WHERE id=?',(review_id,)).fetchone()
        if not row:raise Problem('That review is no longer available.',404)
        review=json.loads(row[0]);incoming=review['incoming'];candidate_ids=review.get('candidateIds',[])
        if policy=='separate':
            try:self.get_item(incoming['id'])
            except Problem:self.put_item(incoming)
            result=self.get_item(incoming['id'])
        else:
            target_id=target_id or (candidate_ids[0] if candidate_ids else None)
            if target_id not in candidate_ids:raise Problem('Choose one of the proposed matching records.')
            result=self.merge_items(target_id,incoming,'incoming' if policy=='incoming' else 'keep','new' if policy=='new-version' else 'same',force_metadata=policy=='incoming')
            if review.get('source') in ('Jellyfin','Plex'):
                provider_type=review['source'].lower()
                chosen=next((source['id'] for source in result.get('sources',[]) if source.get('type')==provider_type and source.get('providerItemId')==next((value.get('providerItemId') for value in incoming.get('sources',[]) if value.get('type')==provider_type),None)),None)
                if policy=='incoming' and chosen:
                    self.choose_metadata_source(result['id'],chosen);result=self.get_item(result['id'])
                elif policy=='keep':
                    self.choose_metadata_source(result['id'],'blankbox');result=self.get_item(result['id'])
        with self.db() as db:db.execute('DELETE FROM review_queue WHERE id=?',(review_id,))
        return {'ok':True,'item':self.public_item(result)}
    def resolve_all_reviews(self,policy):
        if policy not in ('keep','incoming','new-version'):raise Problem('Choose a safe consolidation rule.')
        with self.db() as db:ids=[row[0] for row in db.execute('SELECT id FROM review_queue ORDER BY rowid')]
        resolved=0;skipped=0
        for review_id in ids:
            try:self.resolve_review(review_id,policy);resolved+=1
            except Problem:skipped+=1
        return {'ok':True,'resolved':resolved,'skipped':skipped}
    def physical_candidates(self,title,kind):
        # A DVD or Blu-ray may contain a movie or a TV release. Suggest both video
        # categories here, but leave the final consolidation to the owner.
        return self.match_candidates({'title':title,'kind':kind},compatible_kinds=True)
    def physical_reference_matches(self,data):
        """Bounded library review across local, physical and connected sources."""
        title=data.get('title');kind=data.get('kind');year=data.get('year');reference=data.get('referenceId');compatible_video=data.get('compatibleVideoKinds',False)
        if (not isinstance(title,str) or not 1<=len(title.strip())<=250 or not isinstance(kind,str) or kind not in KINDS
                or year is not None and (type(year) is not int or not 1800<=year<=2200)
                or reference is not None and (not isinstance(reference,str) or not 1<=len(reference)<=120)
                or not isinstance(compatible_video,bool)):
            raise Problem('Choose a valid metadata title to check against your library.')
        kinds=('movie','tv') if compatible_video and kind in ('movie','tv') else (kind,)
        linked=self.catalog_resolve('pack' if reference.startswith('pack:') else 'metadata-entity',reference)['itemIds'] if reference else []
        matches={}
        with self.db() as db:
            # Search existing keys, rather than loading every household item.
            for row in db.execute('SELECT i.data FROM item_search s JOIN items i ON i.id=s.item_id '
                                  'WHERE s.title_key=? AND s.kind IN ('+','.join('?' for _ in kinds)+') AND (? IS NULL OR s.year IS NULL OR s.year=?) '
                                  'ORDER BY s.year IS NULL,s.item_id LIMIT 26',(work_title_key(title),*kinds,year,year)):
                item=json.loads(row[0]);matches[item['id']]=item
            for item_id in linked[:25]:
                row=db.execute('SELECT data FROM items WHERE id=?',(item_id,)).fetchone()
                if row:
                    item=json.loads(row[0])
                    if item.get('kind') in kinds:matches[item_id]=item
        ordered=sorted(matches.values(),key=lambda item:(item['id'] not in linked,item.get('kind')!=kind,item.get('year')!=year,item['id']))
        return {'results':[self.public_item(item) for item in ordered[:25]],'moreMatches':len(ordered)>25 or len(linked)>25}
    def public_item(self,item):
        public={key:item[key] for key in ('id','title','kind','year','releaseDate','description','poster','backdrop','genre','customGenres','duration','catalogDetails','versions','sources','bytes','mime','progress','favorite','addedAt','sample','backup','backupVerifiedAt','credit','metadataMatch','metadataOverrides','metadataProvenance','metadataPreference','blankboxMetadataSnapshot','artist','trackCount','discImport') if key in item}
        public['sources']=[]
        for source in item.get('sources',[]):
            if not isinstance(source,dict):continue
            visible={key:value for key,value in source.items() if key not in ('storedPath','sha256','rootIdentity','sourceMtimeNs')}
            visible['itemId']=item['id']
            if source.get('type') in ('local','digital') and source.get('id'):
                # A merge can retain a file source whose stored URL names the
                # former item. Playback always follows the current Media Item ID.
                visible['url']='/media/'+urllib.parse.quote(item['id'],safe='')+'/'+urllib.parse.quote(source['id'],safe='')
            if source.get('type')=='plex' and source.get('id') and source.get('providerItemId'):
                # Resolve existing and new links on explicit launch, never on
                # library browsing. Tokens and server identity stay in Core.
                visible['url']='/api/playback/plex/'+urllib.parse.quote(item['id'],safe='')+'/'+urllib.parse.quote(source['id'],safe='')
            if source.get('type')=='local' and source.get('storedPath'):
                try:visible['available']=safe_file(self.media,source['storedPath']).is_file()
                except (OSError,ValueError):visible['available']=False
            elif source.get('type')=='digital' and source.get('sourceId'):
                root=self.source_roots.get(source['sourceId'])
                try:
                    details=root.stat() if root else None
                    visible['available']=bool(root and root.is_dir() and (not source.get('rootIdentity') or source['rootIdentity']==f'{details.st_dev}:{details.st_ino}') and safe_file(root,source.get('path','')).is_file())
                except (OSError,ValueError):visible['available']=False
            public['sources'].append(visible)
        return public
    def catalog_resolve(self,namespace,value):
        """Resolve recorded identity evidence to household IDs, without guessing."""
        if not isinstance(namespace,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{0,63}',namespace) or not isinstance(value,str) or not 1<=len(value)<=512:
            raise Problem('Choose one valid identity namespace and value.')
        found=set()
        with self.db() as db:
            if namespace=='item':
                if db.execute('SELECT 1 FROM items WHERE id=?',(value,)).fetchone():found.add(value)
                row=db.execute('SELECT item_id FROM catalog_item_aliases WHERE alias_id=?',(value,)).fetchone()
                if row:found.add(row['item_id'])
            elif namespace=='physical-release':
                found.update(row[0] for row in db.execute('SELECT DISTINCT item_id FROM package_contents WHERE release_id=?',(value,)))
            elif namespace=='owned-copy':
                found.update(row[0] for row in db.execute('SELECT DISTINCT p.item_id FROM package_contents p JOIN owned_copies c ON c.release_id=p.release_id WHERE c.id=?',(value,)))
            elif namespace in ('source','version','jellyfin','plex','emby'):
                for row in db.execute('SELECT id,data FROM items'):
                    item=json.loads(row['data'])
                    if namespace=='version':
                        matched=any(version.get('id')==value for version in item.get('versions',[]) if isinstance(version,dict))
                    else:
                        matched=any(source.get('id')==value if namespace=='source' else
                                    source.get('type')==namespace and source.get('providerItemId')==value
                                    for source in item.get('sources',[]) if isinstance(source,dict))
                    if matched:found.add(row['id'])
            else:
                lookup_namespace='blankbox-pack-record' if namespace=='pack' else namespace
                lookup_value=value[5:] if namespace=='pack' and value.startswith('pack:') else value
                if namespace=='pack':
                    parts=lookup_value.split(':',1)
                    keys=[lookup_value]
                    if len(parts)==2:
                        try:keys=[parts[0]+':'+rid for rid in self.metadata_packs.lookup_keys(*parts)]
                        except (ValueError,OSError,sqlite3.Error):pass
                    marks=','.join('?' for _ in keys)
                    entity_ids=[row[0] for row in db.execute(f"SELECT DISTINCT entity_id FROM metadata_identifiers WHERE namespace IN ('blankbox-pack-record','blankbox-pack-alias') AND value IN ({marks})",keys)]
                else:
                    namespaces=('disc-id','musicbrainz-discid') if physical_namespace(lookup_namespace)=='disc-id' else (lookup_namespace,)
                    marks=','.join('?' for _ in namespaces)
                    entity_ids=[row[0] for row in db.execute(f"SELECT DISTINCT entity_id FROM metadata_identifiers WHERE namespace IN ({marks}) AND value=? AND (source NOT LIKE 'pack:%' OR ?=1)",(*namespaces,lookup_value,int(pack_identifier_allowed(physical_namespace(lookup_namespace)))))]
                if namespace=='metadata-entity':entity_ids=[value]
                for entity_id in entity_ids:
                    entity=db.execute('SELECT level,work_id FROM metadata_entities WHERE id=?',(entity_id,)).fetchone()
                    if not entity:continue
                    if entity['level']=='work':
                        found.update(row[0] for row in db.execute("SELECT target_id FROM metadata_links WHERE target_type='item' AND entity_id=?",(entity_id,)))
                    else:
                        direct={row[0] for row in db.execute("SELECT DISTINCT p.item_id FROM metadata_links l JOIN package_contents p ON p.release_id=l.target_id WHERE l.target_type='physical_release' AND l.entity_id=?",(entity_id,))}
                        digital_ids={row[0] for row in db.execute("SELECT target_id FROM metadata_links WHERE target_type='digital_source' AND entity_id=?",(entity_id,))}
                        if digital_ids:
                            for row in db.execute('SELECT id,data FROM items'):
                                if any(source.get('id') in digital_ids and source.get('type') in ('local','digital') for source in json.loads(row['data']).get('sources',[])):
                                    direct.add(row['id'])
                        found.update(direct or {row[0] for row in db.execute("SELECT target_id FROM metadata_links WHERE target_type='item' AND entity_id=?",(entity['work_id'],))})
        item_ids=sorted(found)
        return {'status':'unlinked' if not item_ids else 'matched' if len(item_ids)==1 else 'ambiguous',
                'itemId':item_ids[0] if len(item_ids)==1 else None,'itemIds':item_ids}
    def refresh_confirmed_pack_details(self,pack_id):
        """Refresh saved pack references; retain household IDs and owner choices."""
        refreshed=updated=0
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            rows=db.execute("SELECT entity_id,value FROM metadata_identifiers WHERE namespace='blankbox-pack-record' AND value LIKE ?",(pack_id+':%',)).fetchall()
            for row in rows:
                try:self.metadata_packs.materialize(db,'pack:'+row['value'])
                except ValueError:continue  # Removed candidates keep their confirmed local evidence.
                refreshed+=1
                links=db.execute("SELECT target_id FROM metadata_links WHERE entity_id=? AND target_type='item' AND relationship='confirmed-work'",(row['entity_id'],)).fetchall()
                facts={}
                for fact in db.execute('SELECT field,value_json,source_record_id,source_version,license FROM metadata_field_values WHERE entity_id=? AND source=? ORDER BY imported_at DESC,source_record_id DESC',(row['entity_id'],'pack:'+pack_id)):
                    if fact['field'] in ('description','genre','releaseDate','duration','artist','catalogDetails') and fact['field'] not in facts:facts[fact['field']]=dict(fact)
                for link in links:
                    stored=db.execute('SELECT data FROM items WHERE id=?',(link['target_id'],)).fetchone()
                    if not stored:continue
                    item=json.loads(stored[0]);changed=False
                    for field,fact in facts.items():
                        if field in item.get('metadataOverrides',[]):continue
                        provenance=item.get('metadataProvenance',{}).get(field,{})
                        incoming=json.loads(fact['value_json'])
                        baseline=item.setdefault('blankboxMetadataSnapshot',{})
                        if baseline.get(field) in (None,'') or provenance.get('source')=='pack:'+pack_id:baseline[field]=incoming
                        current=item.get(field)
                        retained_provider_details=field=='catalogDetails' and bool(current) and provenance.get('source')!='pack:'+pack_id
                        if field=='catalogDetails':
                            # A selected provider retains its supplied members;
                            # the reference fills details it does not supply.
                            incoming={**clean_details(incoming),**clean_details(current)} if provenance.get('source')!='pack:'+pack_id else clean_details(incoming)
                            for override in item.get('metadataOverrides',[]):
                                if not override.startswith('catalogDetails.'):continue
                                member=override.split('.',1)[1]
                                if member in (current or {}):incoming[member]=current[member]
                                else:incoming.pop(member,None)
                        elif current not in (None,'') and provenance.get('source')!='pack:'+pack_id:continue
                        if item.get(field)!=incoming:
                            item[field]=incoming
                            if not retained_provider_details:item.setdefault('metadataProvenance',{})[field]={'source':'pack:'+pack_id,'entityId':row['entity_id'],'sourceRecordId':fact['source_record_id'],'sourceVersion':fact['source_version'],'license':fact['license'],'updatedAt':now()}
                            changed=True
                    if changed:
                        db.execute('UPDATE items SET data=? WHERE id=?',(json.dumps(item),item['id']));sync_item_search(db,item);backfill_item(db,item);updated+=1
        return {'refreshedReferences':refreshed,'updatedItems':updated}
    def catalog_identity(self,item_id):
        """One offline view of effective facts and all confirmed source evidence."""
        item=self.get_item(item_id)
        item_id=item['id']
        with self.db() as db:
            rows=db.execute("SELECT DISTINCT e.id,e.level,e.title,e.origin,l.relationship FROM metadata_links l JOIN metadata_entities e ON e.id=l.entity_id WHERE l.target_type='item' AND l.target_id=? "
                            "UNION SELECT DISTINCT e.id,e.level,e.title,e.origin,l.relationship FROM metadata_links l JOIN metadata_entities e ON e.id=l.entity_id JOIN package_contents p ON p.release_id=l.target_id WHERE l.target_type='physical_release' AND p.item_id=? "
                            "UNION SELECT DISTINCT e.id,e.level,e.title,e.origin,'known-edition' AS relationship FROM metadata_entities e JOIN metadata_links l ON l.entity_id=e.work_id WHERE e.level='release' AND l.target_type='item' AND l.target_id=? ORDER BY level,id",(item_id,item_id,item_id)).fetchall()
            digital_ids=[source['id'] for source in item.get('sources',[]) if source.get('type') in ('local','digital') and source.get('id')]
            if digital_ids:
                placeholders=','.join('?' for _ in digital_ids)
                rows+=db.execute('SELECT DISTINCT e.id,e.level,e.title,e.origin,l.relationship FROM metadata_links l JOIN metadata_entities e ON e.id=l.entity_id '
                                 f"WHERE l.target_type='digital_source' AND l.target_id IN ({placeholders})",digital_ids).fetchall()
            references=[];evidence=[];seen_entities=set()
            for row in rows:
                reference=dict(row)
                reference['identifiers']=[{'namespace':identity['namespace'],'value':identity['value']} for identity in visible_identifiers(db.execute('SELECT namespace,value,source FROM metadata_identifiers WHERE entity_id=? ORDER BY namespace,value',(row['id'],)))]
                references.append(reference)
                if row['id'] in seen_entities:continue
                seen_entities.add(row['id'])
                evidence.extend({'entityId':row['id'],'field':fact['field'],'value':json.loads(fact['value_json']),
                                 'source':fact['source'],'sourceRecordId':fact['source_record_id'],
                                 'sourceVersion':fact['source_version'],'ownerEntered':bool(fact['owner_entered']),
                                 'fromPack':bool(fact['from_pack'])}
                                for fact in db.execute('SELECT field,value_json,source,source_record_id,source_version,owner_entered,from_pack FROM metadata_field_values WHERE entity_id=? ORDER BY field,source',(row['id'],)))
        source_keys=('id','type','label','versionId','providerItemId','physicalReleaseId','ownedCopyId','packageContentId')
        source_links=[{'itemId':item_id,**{key:source[key] for key in source_keys if key in source}}
                      for source in item.get('sources',[]) if isinstance(source,dict)]
        effective={key:item[key] for key in ('title','kind','year','releaseDate','description','genre','customGenres','duration','artist','catalogDetails','poster','backdrop') if key in item}
        return {'itemId':item_id,'localWorkId':local_work_id(item_id),'effective':effective,
                'sources':source_links,'references':references,'fieldEvidence':evidence}
    def metadata_editions(self,item_id):
        item=self.get_item(item_id)
        with self.db() as db:
            rows=db.execute('SELECT e.id,e.work_id,e.title,e.year,e.format,e.edition,e.season,e.origin FROM metadata_entities e '
                            "WHERE e.level='release' AND e.work_id IN "
                            "(SELECT entity_id FROM metadata_links WHERE target_type='item' AND target_id=?) "
                            'ORDER BY e.format,e.edition,e.title,e.id',(item_id,)).fetchall()
            physical_links={}
            for row in db.execute("SELECT DISTINCT l.entity_id,l.target_id FROM metadata_links l JOIN package_contents p ON p.release_id=l.target_id WHERE l.target_type='physical_release' AND p.item_id=?",(item_id,)):
                physical_links.setdefault(row[0],[]).append(row[1])
            owned=set(physical_links)
            mappings=[row[0] for row in db.execute("SELECT DISTINCT i.value FROM metadata_identifiers i JOIN metadata_links l ON l.entity_id=i.entity_id WHERE i.namespace='blankbox-pack-record' AND l.target_type='item' AND l.target_id=?",(item_id,))]
            saved={row[0]:row[1] for row in db.execute("SELECT value,entity_id FROM metadata_identifiers WHERE namespace='blankbox-pack-record'")}
            wanted={row[0] for row in db.execute('SELECT release_id FROM collecting_targets WHERE release_id IS NOT NULL')}
            identifiers={}
            for row in db.execute("SELECT entity_id,namespace,value FROM metadata_identifiers WHERE namespace IN ('isbn','upc-ean') ORDER BY namespace,value"):
                identifiers.setdefault(row[0],{'namespace':row[1],'value':row[2]})
            digital_ids=[source['id'] for source in item.get('sources',[]) if source.get('type') in ('local','digital') and source.get('id')]
            digital=set();digital_links={}
            if digital_ids:
                placeholders=','.join('?' for _ in digital_ids)
                for row in db.execute(f"SELECT entity_id,target_id FROM metadata_links WHERE target_type='digital_source' AND target_id IN ({placeholders})",digital_ids):
                    digital.add(row[0]);digital_links.setdefault(row[0],[]).append(row[1])
        physical=[source for source in item.get('sources',[]) if source.get('type')=='physical']
        editions=[]
        records=[dict(row) for row in rows]
        for candidate in self.metadata_packs.work_releases(mappings):
            mapping=candidate['id'][5:]
            if mapping in saved:continue
            records.append(candidate)
        for record in records:
            status=edition_status(record,physical,owned,digital)
            editions.append({**record,**({'identifier':identifiers[record['id']]} if record['id'] in identifiers else {}),
                             'status':status,'wanted':record['id'] in wanted,'physicalReleaseIds':sorted(set(physical_links.get(record['id'],[]))),
                             'digitalSourceIds':sorted(set(digital_links.get(record['id'],[])))})
        return editions
    def metadata_household_links(self,candidates):
        """Resolve reviewed reference IDs to household items without title guessing."""
        for candidate in candidates:
            candidate_id=candidate['id']
            namespace='pack' if candidate_id.startswith('pack:') else 'metadata-entity'
            candidate['householdItemIds']=self.catalog_resolve(namespace,candidate_id)['itemIds']
            for identifier in candidate.get('identifiers',[]):
                candidate['householdItemIds']=sorted(set(candidate['householdItemIds'])|set(self.catalog_resolve(identifier['namespace'],identifier['value'])['itemIds']))
            if candidate.get('level')=='release' and candidate.get('work_id'):
                parent=candidate['work_id']
                parent_namespace='pack' if parent.startswith('pack:') else 'metadata-entity'
                candidate['householdItemIds']=sorted(set(candidate['householdItemIds'])|set(self.catalog_resolve(parent_namespace,parent)['itemIds']))
        return candidates
    def physical_data(self,data):
        title=str(data.get('title','')).strip();format=data.get('format');kind=data.get('kind','movie');year=data.get('year')
        if not title or len(title)>250 or format not in PHYSICAL_FORMATS or kind not in KINDS or kind not in PHYSICAL_FORMATS[format]:raise Problem('Check the physical copy details and media type.')
        if year is not None and (not isinstance(year,int) or not 1800<=year<=2200):raise Problem('Enter a valid year.')
        season=data.get('season') or None
        if not valid_season(season) or season and kind!='tv':raise Problem('Choose a valid TV season or leave it unspecified.')
        source={'type':'physical','label':format,'location':str(data.get('location','')).strip()[:250],'addedAt':now()}
        if season:source['season']=season
        limits={'edition':120,'barcode':80,'condition':120,'creator':250,'publisher':250,'platform':120,'volume':80,'issue':80,'region':80,'catalogNumber':120}
        for key,limit in limits.items():
            value=data.get(key,'')
            if not isinstance(value,str) or len(value)>limit:raise Problem(f'Invalid {key}.')
            if value.strip():source[key]=value.strip()
        if kind=='game' and source.get('platform') in (None,'__custom__'):raise Problem('Choose a console or platform for this game.')
        return title,kind,year,source
    def edit_physical_sources(self,item,rows):
        """Edit owned copies without changing sibling copies or confirmed release identity."""
        ensure_item_model(item)
        physical={source['id']:source for source in item.get('sources',[]) if source.get('type')=='physical'}
        if not isinstance(rows,list) or len(rows)!=len(physical) or any(not isinstance(row,dict) for row in rows):
            raise Problem('Physical copies changed. Reopen this item before saving.')
        ids=[row.get('sourceId') for row in rows]
        if any(not isinstance(identifier,str) for identifier in ids) or len(set(ids))!=len(ids) or set(ids)!=set(physical):raise Problem('Physical copies changed. Reopen this item before saving.')
        limits={'format':120,'edition':120,'season':20,'barcode':80,'condition':120,'creator':250,'publisher':250,'platform':120,
                'volume':80,'issue':80,'region':80,'catalogNumber':120,'location':250}
        identity=('format','edition','season','barcode','creator','publisher','platform','volume','issue','region','catalogNumber')
        originals={identifier:dict(source) for identifier,source in physical.items()}
        old_versions={version['id']:dict(version) for version in item.get('versions',[])}
        release_map={};version_map={};retired_releases=set();retired_contents=set()
        for row in rows:
            values={}
            for key,limit in limits.items():
                value=row.get(key,'')
                if not isinstance(value,str) or len(value)>limit:raise Problem(f'Invalid physical {key}.')
                values[key]=value.strip()
            if values['format'] not in PHYSICAL_FORMATS or item['kind'] not in PHYSICAL_FORMATS[values['format']]:
                raise Problem('That physical format does not fit this media type.')
            if item['kind']=='game' and values['platform'] in ('','__custom__'):raise Problem('Choose a console or platform for this game.')
            if not valid_season(values['season'] or None) or values['season'] and item['kind']!='tv':raise Problem('Choose a valid TV season or leave it unspecified.')
            source=physical[row['sourceId']];original=originals[row['sourceId']]
            before=(original.get('label',''),*[original.get(key,'') or '' for key in identity[1:]])
            after=tuple(values[key] for key in identity)
            for key in limits:
                target='label' if key=='format' else key
                if values[key]:source[target]=values[key]
                else:source.pop(target,None)
            if before==after:continue
            old_release=original.get('physicalReleaseId')
            old_content=original.get('packageContentId')
            if old_release:retired_releases.add(old_release)
            if old_content:retired_contents.add(old_content)
            release_key=(old_release or original['id'],after)
            source['physicalReleaseId']=release_map.setdefault(release_key,uuid.uuid4().hex)
            source.pop('packageContentId',None)
            old_version=original.get('versionId');version_key=(old_version,after)
            shared=any(other['id']!=original['id'] and other.get('versionId')==old_version for other in originals.values()) or any(other.get('type')!='physical' and other.get('versionId')==old_version for other in item['sources'])
            if shared:
                if version_key not in version_map:
                    version_map[version_key]=uuid.uuid4().hex
                    item['versions'].append({'id':version_map[version_key],'label':' · '.join(value for value in (physical_edition_label(values['format'],values['edition']),season_label(values['season'])) if value),
                                             'format':values['format'],'edition':values['edition'] or None,
                                             **({'season':values['season']} if values['season'] else {}),
                                             **({'year':old_versions[old_version]['year']} if old_version in old_versions and old_versions[old_version].get('year') else {})})
                source['versionId']=version_map[version_key]
            else:
                version=next((version for version in item['versions'] if version['id']==old_version),None)
                if version:
                    version.update(label=' · '.join(value for value in (physical_edition_label(values['format'],values['edition']),season_label(values['season'])) if value),format=values['format'],edition=values['edition'] or None)
                    if values['season']:version['season']=values['season']
                    else:version.pop('season',None)
        used={source.get('versionId') for source in item['sources']}
        item['versions']=[version for version in item['versions'] if version['id'] in used] or item['versions'][:1]
        return retired_releases,retired_contents
    def edit_digital_sources(self,item,rows):
        """Edit file display and edition facts without touching observed files or copies."""
        ensure_item_model(item)
        digital={source['id']:source for source in item.get('sources',[]) if source.get('type') in ('local','digital')}
        if not isinstance(rows,list) or len(rows)!=len(digital) or any(not isinstance(row,dict) for row in rows):
            raise Problem('Digital sources changed. Reopen this item before saving.')
        ids=[row.get('sourceId') for row in rows]
        if any(not isinstance(identifier,str) for identifier in ids) or len(set(ids))!=len(ids) or set(ids)!=set(digital):
            raise Problem('Digital sources changed. Reopen this item before saving.')
        desired={}
        for row in rows:
            label,edition=row.get('label'),row.get('edition')
            if not isinstance(label,str) or not 1<=len(label.strip())<=120 or not isinstance(edition,str) or len(edition)>120:
                raise Problem('Enter a valid file label and edition.')
            desired[row['sourceId']]=(label.strip(),edition.strip())
        for row in rows:
            source=digital[row['sourceId']]
            for field,limit in (('creator',250),('publisher',250),('platform',120),('volume',80),('issue',80),('region',80),('catalogNumber',120),('barcode',80)):
                if field not in row:continue
                value=row[field]
                if not isinstance(value,str) or len(value)>limit:raise Problem('Enter valid digital release details.')
                if value.strip():source[field]=value.strip()
                else:source.pop(field,None)
        originals={identifier:dict(source) for identifier,source in digital.items()}
        versions={version['id']:version for version in item.get('versions',[])}
        shared_new={}
        for source_id,source in digital.items():
            label,edition=desired[source_id]
            source['label']=label
            if edition:source['edition']=edition
            else:source.pop('edition',None)
            old=originals[source_id]
            if edition==(old.get('edition') or ''):continue
            version_id=old.get('versionId');version=versions.get(version_id)
            if not version:continue
            wanted=edition or 'Standard or unknown edition'
            if version.get('label')==wanted:continue
            sharing=[other for other in item['sources'] if other.get('versionId')==version_id]
            all_same=all(other.get('type') in ('local','digital') and desired.get(other.get('id'),('',None))[1]==edition for other in sharing)
            if all_same:
                version['label']=wanted
                if edition:version['edition']=edition
                else:version.pop('edition',None)
                version.pop('format',None)
                continue
            key=(version_id,edition)
            if key not in shared_new:
                replacement={key:value for key,value in version.items() if key not in ('id','label','format','edition')}
                replacement.update(id=uuid.uuid4().hex,label=wanted)
                if edition:replacement['edition']=edition
                item['versions'].append(replacement)
                shared_new[key]=replacement['id']
            source['versionId']=shared_new[key]
        used={source.get('versionId') for source in item['sources']}
        item['versions']=[version for version in item['versions'] if version['id'] in used] or item['versions'][:1]
    def move_physical_location(self,from_location,to_location):
        from_location=str(from_location or '').strip();to_location=str(to_location or '').strip()
        if not from_location or not to_location or len(from_location)>250 or len(to_location)>250:raise Problem('Choose valid current and new shelf locations.')
        if from_location==to_location:raise Problem('Choose a different destination.')
        moved_copies=0;moved_titles=0
        with self.db() as db:
            rows=list(db.execute('SELECT id,data FROM items'))
            for row in rows:
                item=json.loads(row['data']);changed=False
                for source in item.get('sources',[]):
                    if source.get('type')=='physical' and source.get('location')==from_location:
                        source['location']=to_location;moved_copies+=1;changed=True
                if changed:
                    moved_titles+=1;ensure_item_model(item);sync_physical_ownership(db,item)
                    db.execute('UPDATE items SET data=? WHERE id=?',(json.dumps(item),row['id']))
            settings={**DEFAULTS,**json.loads(db.execute('SELECT data FROM settings WHERE id=1').fetchone()[0])}
            saved=[value for value in settings.get('physicalLocations',[]) if value.casefold()!=from_location.casefold()]
            if not any(value.casefold()==to_location.casefold() for value in saved):saved.append(to_location)
            settings['physicalLocations']=sorted(saved,key=str.casefold)
            db.execute('UPDATE settings SET data=? WHERE id=1',(json.dumps(settings),))
        return {'ok':True,'movedCopies':moved_copies,'movedTitles':moved_titles}
    def remember_physical_choices(self,source):
        additions=(('physicalLocations',source.get('location')),('gamePlatforms',source.get('platform')))
        if not any(value for _,value in additions):return
        with self.db() as db:
            settings={**DEFAULTS,**json.loads(db.execute('SELECT data FROM settings WHERE id=1').fetchone()[0])};changed=False
            for key,value in additions:
                value=str(value or '').strip()
                if value and not any(saved.casefold()==value.casefold() for saved in settings.get(key,[])):
                    settings.setdefault(key,[]).append(value);settings[key].sort(key=str.casefold);changed=True
            if changed:db.execute('UPDATE settings SET data=? WHERE id=1',(json.dumps(settings),))
    def save_reviewed_physical(self,item,source,data):
        metadata_id=data.get('metadataEntityId')
        if metadata_id is not None and (not isinstance(metadata_id,str) or not 1<=len(metadata_id)<=120):
            raise Problem('Choose a valid metadata candidate.')
        ensure_item_model(item)
        try:
            self.catalog.save_item(item,reviewed_metadata_id=metadata_id,reviewed_physical_source_id=source['id'],
                                   evidence_namespace='isbn' if item.get('kind')=='book' else 'upc-ean',
                                   evidence_value=source.get('barcode'),pack_repository=self.metadata_packs)
        except (ValueError,sqlite3.IntegrityError) as error:raise Problem(str(error)) from error
    def attach_physical(self,id,data):
        title,kind,year,source=self.physical_data(data);item=self.get_item(id)
        if item.get('kind')!=kind and {item.get('kind'),kind}!={'movie','tv'}:raise Problem('Choose a compatible media type or keep this as a separate title.')
        ensure_item_model(item)
        version_id=data.get('versionId')
        if not data.get('newEdition') and version_id is not None and version_id not in {version['id'] for version in item['versions']}:
            raise Problem('Choose an edition already attached to this title.')
        selected_version=version_id or item['versions'][0]['id']
        if data.get('newEdition'):
            entered=str(data.get('editionLabel') or '').strip()
            if entered and entered != source['label'] and not source.get('edition'):
                source['edition']=entered[:120]
            same_labels=[existing for existing in item['sources'] if existing.get('type')=='physical' and existing.get('label')==source['label'] and (existing.get('edition') or '').casefold()==(source.get('edition') or '').casefold() and existing.get('season')==source.get('season')]
            if same_labels and not any(any(existing.get(key) and source.get(key) and existing[key]!=source[key] for key in ('barcode','region','catalogNumber','platform')) for existing in same_labels):
                raise Problem('This format and edition is already on the title. Add another owned copy of the existing edition, or enter a distinguishing barcode or release detail.')
            label=' · '.join(value for value in (physical_edition_label(source['label'],source.get('edition')),season_label(source.get('season'))) if value)
            if any(version.get('label')==label for version in item['versions']):
                detail=source.get('barcode') or source.get('catalogNumber') or source.get('region') or source.get('platform')
                label=f'{label} · {detail}' if detail else label
            version={'id':uuid.uuid4().hex,'label':label,
                     'format':source['label'],'edition':source.get('edition') or None}
            if source.get('season'):version['season']=source['season']
            if year:version['year']=year
            item['versions'].append(version);source['versionId']=version['id']
        else:
            matching=[existing for existing in item['sources'] if existing.get('type')=='physical' and existing.get('versionId')==selected_version]
            if not matching:
                raise Problem('Choose a physical edition already on this title, or create a new edition.')
            if any(existing.get('label')!=source['label'] or (existing.get('edition') or '').casefold()!=(source.get('edition') or '').casefold() or existing.get('season')!=source.get('season') for existing in matching):
                raise Problem('This copy has a different format, edition, or TV season. Create a new edition for it.')
            source['versionId']=selected_version
            source['physicalReleaseId']=matching[0]['physicalReleaseId']
        source['id']=uuid.uuid4().hex
        item.setdefault('sources',[]).append(source)
        if year and not item.get('year'):item['year']=year
        self.save_reviewed_physical(item,source,data);self.remember_physical_choices(source);return {'ok':True,'item':self.public_item(item)}
    def remove_physical(self,id,source):
        if not isinstance(source,dict) or source.get('type')!='physical':raise Problem('Choose a physical copy to remove.')
        item=self.get_item(id);sources=item.get('sources',[])
        index=next((index for index,current in enumerate(sources) if source.get('id') and current.get('id')==source.get('id')),-1)
        if index<0:index=next((index for index,current in enumerate(sources) if all(current.get(key)==source.get(key) for key in ('type','label','location'))),-1)
        if index<0:raise Problem('That physical copy is no longer attached.')
        if len(sources)==1:raise Problem('This is the only source. Remove the item from its details screen instead.')
        removed=sources.pop(index);version_id=removed.get('versionId')
        if version_id and not any(current.get('versionId')==version_id for current in sources) and len(item.get('versions',[]))>1:item['versions']=[version for version in item['versions'] if version.get('id')!=version_id]
        self.put_item(item);return {'ok':True,'item':self.public_item(item)}
    def remove_source(self,item_id,source_id):
        item=self.get_item(item_id);ensure_item_model(item)
        index=next((index for index,source in enumerate(item['sources']) if source.get('id')==source_id),-1)
        if index<0:raise Problem('That source is no longer attached.',404)
        if len(item['sources'])==1:return {**self.remove_item(item_id),'item':None}
        source=item['sources'][index];staged=None
        if source.get('type')=='local':
            relative=source.get('storedPath') or item.get('storedPath')
            if not relative:raise Problem('The managed source has no stored file.',409)
            managed=safe_file(self.media,relative);expected=source.get('sha256') or item.get('sha256')
            if expected and digest(managed)!=expected:raise Problem('The managed copy changed. Verify or restore it before removing the source.',409)
            if not self.managed_path_referenced_elsewhere(relative,item['id'],source['id']):
                staged=managed.with_name('.blank-box-delete-'+item['id']+'-'+source['id']+'-'+managed.name)
                if staged.exists():raise Problem('A previous removal needs recovery before this copy can be removed.',409)
                os.replace(managed,staged)
        try:
            removed=item['sources'].pop(index);version_id=removed.get('versionId')
            if version_id and not any(current.get('versionId')==version_id for current in item['sources']) and len(item['versions'])>1:item['versions']=[version for version in item['versions'] if version.get('id')!=version_id]
            hidden_id=None;hidden=None
            if removed.get('type') in ('jellyfin','plex') and removed.get('providerItemId'):
                provider=removed['type'];hidden_id=provider+'-'+removed['providerItemId'];hidden={'item':{'id':hidden_id,'title':item.get('title','Untitled'),'kind':item.get('kind','movie'),'year':item.get('year'),'description':item.get('description'),'sources':[removed],'addedAt':now()},'hiddenAt':now(),'source':provider}
            remaining_local=next((current for current in item['sources'] if current.get('type')=='local'),None)
            for key in ('storedPath','sha256','bytes','mime'):
                if remaining_local and key in remaining_local:item[key]=remaining_local[key]
                elif key in item:item.pop(key,None)
            if item.get('poster')==source.get('url'):
                if remaining_local and str(remaining_local.get('mime','')).startswith('image/'):item['poster']=remaining_local.get('url')
                else:item.pop('poster',None)
            if item.get('metadataPreference')==removed.get('id'):
                apply_metadata_choice(item,None)
                item['metadataPreference']='blankbox'
            ensure_item_model(item)
            with self.db() as db:
                if hidden_id:db.execute('INSERT INTO hidden_items VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',(hidden_id,json.dumps(hidden)))
                db.execute('UPDATE items SET data=? WHERE id=?',(json.dumps(item),item['id']))
                if sync_physical_ownership(db,item):db.execute('UPDATE items SET data=? WHERE id=?',(json.dumps(item),item['id']))
                if removed.get('type')=='digital' and removed.get('sourceId'):
                    db.execute('DELETE FROM inventory_links WHERE media_source_id=?',(removed.get('id'),))
                if removed.get('type') in ('local','digital') and removed.get('id'):
                    remove_digital_source_links(db,removed['id'])
        except Exception:
            if staged and staged.exists():os.replace(staged,self.media/(source.get('storedPath') or item.get('storedPath')))
            raise
        if staged:
            try:staged.unlink(missing_ok=True)
            except OSError:return {'ok':True,'removedCopy':True,'cleanupPending':True,'item':self.public_item(item)}
        return {'ok':True,'removedCopy':bool(staged),'item':self.public_item(item)}
    def get_settings(self):
        with self.db() as db:return {**DEFAULTS,**json.loads(db.execute('SELECT data FROM settings WHERE id=1').fetchone()[0])}
    def collection_reference_mappings(self):
        mappings={}
        with self.db() as db:
            for row in db.execute("SELECT l.target_id,i.value FROM metadata_links l JOIN metadata_identifiers i ON i.entity_id=l.entity_id WHERE l.target_type='item' AND i.namespace='blankbox-pack-record'"):
                mappings.setdefault(row[0],[]).append('pack:'+row[1])
        return mappings
    def collection_recommendations(self,items=None,targets=None,operation_owned=False):
        if items is None:
            with self.db() as db:pending={json.loads(row[0]).get('incoming',{}).get('id') for row in db.execute('SELECT data FROM review_queue')}
            items=[self.public_item(item) for item in self.items() if item['id'] not in pending]
        with self.db() as db:
            if targets is None:targets=list_targets(db)
            targets=[{**target,'packWorkIds':['pack:'+row[0] for row in db.execute("SELECT value FROM metadata_identifiers WHERE entity_id=? AND namespace='blankbox-pack-record'",(target.get('workId'),))]} for target in targets]
            dismissed=json.loads(db.execute('SELECT data FROM settings WHERE id=1').fetchone()[0]).get('dismissedCollectionRecommendations',[])
            accepted={json.loads(row[0]).get('recommendationId') for row in db.execute('SELECT data FROM library_collections')}
        groups=self.collection_references.recommend(items,self.collection_reference_mappings(),targets,set(dismissed)|accepted,operation_owned=operation_owned)
        return {'recommendations':groups,
                'indexStatus':'unavailable' if self.collection_references.failure else 'building' if self.collection_references.pending or self.collection_references.deferred else 'ready',
                'packCoverage':self.collection_references.coverage,'packErrors':self.metadata_packs.errors()+self.bundled_metadata_errors+([self.collection_references.failure] if self.collection_references.failure else [])}
    def save_collection_recommendation(self,data,operation_owned=False):
        group=next((g for g in self.collection_recommendations(operation_owned=operation_owned)['recommendations'] if g['id']==data.get('recommendationId')),None)
        if not group:raise ValueError('This recommendation changed. Refresh and review it again.')
        selected=data.get('memberKeys')
        if not isinstance(selected,list) or not selected or any(not isinstance(v,str) for v in selected) or len(set(selected))!=len(selected):raise ValueError('Choose the titles to include.')
        lookup={m['key']:m for m in group['members']}
        if set(selected)-set(lookup):raise ValueError('A selected reference changed. Reopen the recommendation.')
        members=[lookup[k] for k in selected]
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if any(json.loads(r[0]).get('recommendationId')==group['id'] for r in db.execute('SELECT data FROM library_collections')):
                return {'ok':True,'alreadySaved':True}
            collection_id,set_id=self._save_recommended_collection(db,group,members,data.get('name',group['name']))
        return {'ok':True,'id':collection_id,'setId':set_id}
    def _save_recommended_collection(self,db,group,members,name,available=None,materialized=None):
        materialized={} if materialized is None else materialized
        prepared=[]
        for member in members:
            work_id=member.get('workId')
            if work_id and work_id.startswith('pack:'):
                if work_id not in materialized:materialized[work_id]=self.metadata_packs.materialize(db,work_id)
                work_id=materialized[work_id]
            if member['status']=='library' and len(member['itemIds'])==1:work_id=local_work_id(member['itemIds'][0])
            prepared.append({**member,'workId':work_id})
        set_id=save_set(db,{'name':name,'mediaKind':group['kind'],'members':prepared,'recommendationSource':group['source']+':'+group['basis']},now())
        item_ids=list(dict.fromkeys(i for m in members if m['status']=='library' for i in m['itemIds']))
        collection_id=save_collection(db,{'name':name,'kind':'series' if group['basis']=='title-pattern' else 'manual','memberIds':item_ids},available)
        row=json.loads(db.execute('SELECT data FROM library_collections WHERE id=?',(collection_id,)).fetchone()[0])
        row.update(completionSetId=set_id,recommendationId=group['id'],recommendationBasis=group['basis'],recommendationMemberIds=item_ids)
        db.execute('UPDATE library_collections SET data=? WHERE id=?',(json.dumps(row),collection_id))
        return collection_id,set_id
    def approve_collection_recommendations(self,identifiers):
        if not isinstance(identifiers,list) or not 1<=len(identifiers)<=60 or any(not isinstance(v,str) or not re.fullmatch(r'recommendation-[0-9a-f]{24}',v) for v in identifiers) or len(set(identifiers))!=len(identifiers):
            raise Problem('Choose up to 60 distinct current suggestions.')
        def worker(job):
            job.update(total=len(identifiers),message='Preparing suggested collections');self.save_job(job)
            groups={g['id']:g for g in self.collection_recommendations(operation_owned=True)['recommendations']}
            with self.db() as db:
                db.execute('BEGIN IMMEDIATE')
                existing={json.loads(r[0]).get('recommendationId') for r in db.execute('SELECT data FROM library_collections')}
                if set(identifiers)-existing-groups.keys():raise ValueError('Suggestions changed. Refresh and try again.')
                selected=[groups[i] for i in identifiers if i not in existing]
                if db.execute('SELECT COUNT(*) FROM library_collections').fetchone()[0]+len(selected)>500:raise ValueError('The household collection limit is 500.')
                available={r[0] for r in db.execute('SELECT id FROM items')};materialized={};created=[]
                for group in selected:
                    collection_id,_=self._save_recommended_collection(db,group,group['members'],group['name'],available,materialized)
                    created.append(collection_id)
            job.update(done=len(identifiers),createdCollectionIds=created,created=len(created),skipped=len(identifiers)-len(created),message=f'{len(created)} editable collections and plans created · {len(identifiers)-len(created)} already saved')
        return self.start_job('collection-approval',worker)
    def collection_suggestions(self,items,indexed,targets,sets):
        """Organize reviewed set gaps and exploratory local-pack creator leads."""
        groups=[]
        wanted_releases={target.get('releaseId') for target in targets if target.get('releaseId')}
        with self.db() as db:
            eligible={row[0] for row in db.execute("SELECT DISTINCT l.target_id FROM metadata_links l WHERE l.target_type='item' AND (EXISTS (SELECT 1 FROM metadata_entities r WHERE r.level='release' AND r.work_id=l.entity_id) OR EXISTS (SELECT 1 FROM metadata_identifiers i WHERE i.entity_id=l.entity_id AND i.namespace='blankbox-pack-record'))")}
            for item in items:
                if item['id'] not in eligible:continue
                editions=self.metadata_editions(item['id'])
                gaps=[]
                for release in editions:
                    if release['origin'] in ('household-copy','household-file') or release['status'] not in ('missing','review'):continue
                    if release['format'] not in FORMATS_BY_KIND.get(item.get('kind'),set()):continue
                    if release['id'] in wanted_releases:continue
                    mapping=release['id'][5:] if release['id'].startswith('pack:') else None
                    if mapping and db.execute("SELECT 1 FROM collecting_targets t JOIN metadata_identifiers i ON i.entity_id=t.release_id WHERE i.namespace='blankbox-pack-record' AND i.value=?",(mapping,)).fetchone():continue
                    work_id=release['work_id']
                    if work_id.startswith('pack:'):
                        resolved=db.execute("SELECT e.id,e.title,e.year FROM metadata_identifiers i JOIN metadata_entities e ON e.id=i.entity_id WHERE i.namespace='blankbox-pack-record' AND i.value=?",(work_id[5:],)).fetchone()
                    else:resolved=db.execute('SELECT id,title,year FROM metadata_entities WHERE id=?',(work_id,)).fetchone()
                    if not resolved:continue
                    gaps.append({'title':resolved['title'],'kind':item['kind'],'year':resolved['year'],'format':release['format'] or 'Any',
                                 'edition':release['edition'],'season':release['season'],'workId':resolved['id'],'releaseId':release['id'],
                                 'status':release['status'],'itemIds':[item['id']],'reason':'known release of linked work; reference coverage may be incomplete'})
                if gaps:groups.append({'id':'editions:'+item['id'],'name':f"Editions of {item['title']}",'kind':item['kind'],
                                       'basis':'known-editions','source':'local-reference','items':gaps,'summary':reference_summary(editions)})
        for entry in sets:
            rows=[{**member,'reason':'reviewed set membership' if entry['kind']=='reference' else 'your saved collection set'}
                  for member in entry['members'] if member['outcome'] in ('missing','review','wanted')]
            if rows:groups.append({'id':'set:'+entry['id'],'name':entry['name'],'kind':entry['mediaKind'],
                                   'basis':'reviewed-membership' if entry['kind']=='reference' else 'saved-set',
                                   'source':entry['source'],'items':rows})
        creators={'book':set(),'music':set()}
        for item in items:
            if item.get('kind')=='book':
                creators['book'].update(str(source['creator']).strip() for source in item.get('sources',[]) if source.get('type')=='physical' and isinstance(source.get('creator'),str) and source['creator'].strip())
            if item.get('kind')=='music' and isinstance(item.get('artist'),str) and item['artist'].strip():creators['music'].add(item['artist'].strip())
        leads=self.metadata_packs.creator_candidates(creators,limit=120)
        by_creator={}
        saved={(target.get('kind'),collecting_title_key(target.get('title','')),target.get('year'),target.get('format')) for target in targets}
        for lead in leads:
            candidate={key:lead[key] for key in ('title','kind','year','format')}
            state=ownership(candidate,indexed)
            if state['status']=='owned-format' or (lead['kind'],collecting_title_key(lead['title']),lead['year'],'Any') in saved:continue
            key=(lead['kind'],lead['creator'])
            by_creator.setdefault(key,[]).append({**lead,'status':'review' if state['status'].startswith('possible-') else 'candidate',
                                                   'itemIds':state['itemIds'],'reason':'same recorded creator; work candidate from installed pack'})
        for (kind,creator),rows in sorted(by_creator.items()):
            groups.append({'id':'creator:'+kind+':'+creator,'name':f'More by {creator}','kind':kind,'basis':'creator-candidates',
                           'source':rows[0]['source'],'items':rows[:50]})
        with self.db() as db:
            for item in items:
                if item.get('kind')!='tv':continue
                sources=[source for source in item.get('sources',[]) if source.get('type') in ('jellyfin','plex') and source.get('tvCatalog')]
                source=next((source for source in sources if source.get('id')==item.get('metadataPreference')),None) or next(iter(sources),None)
                if not source:continue
                work_id=local_work_id(item['id'])
                work=db.execute("SELECT title FROM metadata_entities WHERE id=? AND level='work'",(work_id,)).fetchone()
                if not work or collecting_title_key(work['title'])!=collecting_title_key(item.get('title','')):work_id=None
                rows=[]
                physical=[copy for copy in item.get('sources',[]) if copy.get('type')=='physical']
                for season in source['tvCatalog'].get('seasons',[]):
                    number=season.get('number')
                    if not isinstance(number,int) or not 0<=number<=99:continue
                    season_key='specials' if number==0 else str(number)
                    if any(copy.get('season') in (season_key,'complete-series') for copy in physical):continue
                    if any(target.get('kind')=='tv' and target.get('season')==season_key and (
                        target.get('workId')==work_id if work_id and target.get('workId') else
                        collecting_title_key(target.get('title',''))==collecting_title_key(item.get('title','')) and
                        (target.get('year') is None or item.get('year') is None or target['year']==item['year'])
                    ) for target in targets):continue
                    rows.append({'title':item['title'],'kind':'tv','year':item.get('year'),'format':'Any','season':season_key,
                                 'workId':work_id,'status':'review' if any(not copy.get('season') for copy in physical) else 'missing-season',
                                 'itemIds':[item['id']],'reason':'season listed by connected catalog; no matching physical season recorded'})
                if rows:groups.append({'id':'tv-seasons:'+item['id'],'name':f"Seasons of {item['title']}",'kind':'tv',
                                       'basis':'provider-seasons','source':source['type'],'items':rows})
        return groups
    def backup_info(self):
        with self.db() as db:r=db.execute('SELECT data FROM backup_state WHERE id=1').fetchone()
        result=json.loads(r[0]) if r else {}
        result.update(configured=bool(self.backup_root),sameDevice=bool(self.backup_root and self.backup_root.exists() and self.backup_root.stat().st_dev==self.data.stat().st_dev))
        if self.backup_root:result['path']=str(self.backup_root)
        if self.backup_every_hours:result['everyHours']=self.backup_every_hours
        return result
    def capabilities(self):
        return {
            'apiVersion':1,
            'productVersion':VERSION,
            'catalogSchemaVersion':self.catalog_schema_version(),
            'mode':'box',
            'features':{
                'library':{'supported':True,'configured':True},
                'localPlayback':{'supported':True,'configured':True,'directPlay':True,'transcoding':False},
                'localMetadata':{'supported':True,'configured':True,'modelVersion':2},
                'physicalCollection':{'supported':True,'configured':True,'modelVersion':1},
                'managedImports':{'supported':True,'configured':bool(self.source_roots)},
                'verifiedBackups':{'supported':True,'configured':bool(self.backup_root)},
                'jellyfinCatalog':{'supported':True,'configured':bool(self.connection('jellyfin'))},
                'plexCatalog':{'supported':True,'configured':bool(self.connection('plex'))},
                'ownerProfile':{'supported':True,'configured':self.has_profile()},
                'immichCatalog':{'supported':False,'reason':'Immich catalog integration is not available in this build.'},
                'storageHealth':{'supported':False,'reason':'Drive health is not available in this build.'},
                'multiUser':{'supported':False,'reason':'Household profiles are not available in this build.'},
            },
        }
    def browse_summary(self):
        """Bounded start page; rich item details and collections are separate reads."""
        ready=self.browse.prepare();settings=self.get_settings();ids=[]
        options=[{'limit':5}, {'limit':5,'released':True,'sort':'year'}]
        options.extend({'view':kind,'limit':5} for kind in ('movie','tv','music','photo','book','comic','game'))
        hero_sort={'released':'year','az':'az'}.get(settings.get('homeHeroSort'),'recent')
        for key,kinds in [('heroWatch',('movie','tv')),('heroMusic',('music',)),('heroBooks',('book',)),('heroPhotos',('photo','home-video')),('heroComics',('comic',)),('heroGames',('game',))]:
            if settings.get(key):options.extend({'kind':kind,'limit':5,'sort':hero_sort} for kind in kinds)
        if ready:
            for value in options:ids.extend(item['id'] for item in self.browse.page(value)['items'])
        with self.browse.lock,self.db() as db:
            items=self.browse._cards(db,list(dict.fromkeys(ids)))
            where=VISIBLE_ITEM_CLAUSE
            counts={r[0]:r[1] for r in db.execute('SELECT kind,COUNT(*) FROM browse_documents d WHERE '+where+' GROUP BY kind')}
            totals=db.execute('SELECT COUNT(*),COALESCE(SUM(digital),0) FROM browse_documents d WHERE '+where).fetchone()
            facets=self.browse.facets(db)
            collection_count=db.execute('SELECT COUNT(*) FROM library_collections').fetchone()[0]
            hidden_count=db.execute('SELECT COUNT(*) FROM hidden_items').fetchone()[0]
            review_count=db.execute('SELECT COUNT(*) FROM review_queue').fetchone()[0]
        storage=shutil.disk_usage(self.data)
        physical=self.catalog.physical_inventory_summary()
        return {'mode':'box','version':VERSION,'collectionPlanningAvailable':True,'pagedLibrary':True,'items':items,
                'summary':{'titles':totals[0],'physicalCopies':physical['copies'],'digitalOrConnectedSources':totals[1],'physicalFormats':physical['formats']},
                'kindCounts':counts,'facets':facets,'collectionCount':collection_count,'collections':[],
                'settings':settings,'physicalInventory':physical,'hiddenItems':hidden_count,'hiddenRecords':self.hidden_records(50),
                'reviews':[],'reviewCount':review_count,
                'sources':[{'id':key,'name':root.name or str(root),'path':str(root),'available':root.is_dir()} for key,root in self.source_roots.items()],
                **self.job_state(),'browseIndexStatus':'unavailable' if self.browse.failure else 'ready' if ready else 'building',
                'storage':{'total':storage.total,'used':storage.used,'free':storage.free},'backup':self.backup_info()}

    def public_state(self):
        storage=shutil.disk_usage(self.data)
        with self.db() as db:
            review_count=db.execute('SELECT COUNT(*) FROM review_queue').fetchone()[0]
            pending_ids={json.loads(row[0]).get('incoming',{}).get('id') for row in db.execute('SELECT data FROM review_queue')}
        items=[self.public_item(item) for item in self.items() if item.get('id') not in pending_ids]
        items=self.collection_references.genre_projection(items,self.collection_reference_mappings())
        with self.db() as db:
            activity=activity_states(db)
            collections=list_collections(db,items,activity)
        for item in items:item['activity']=activity.get(item['id'],{'status':'not-started'})
        with self.state_lock:jobs=list(self.jobs.values())[::-1][:15]
        hidden_records=self.hidden_records()
        return {'mode':'box','version':VERSION,'collectionPlanningAvailable':True,'collections':collections,'settings':self.get_settings(),'items':items,'physicalInventory':self.catalog.physical_inventory_summary(),'hiddenItems':len(hidden_records),'hiddenRecords':hidden_records,'reviews':self.reviews(),'reviewCount':review_count,'sources':[{'id':id,'name':p.name or str(p),'path':str(p),'available':p.is_dir()} for id,p in self.source_roots.items()],'jobs':jobs,'storage':{'total':storage.total,'used':storage.used,'free':storage.free},'backup':self.backup_info()}
    def save_job(self,job):
        with self.state_lock:
            with self.db() as db:db.execute('INSERT INTO jobs VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',(job['id'],json.dumps(job)))
            self.jobs[job['id']]=dict(job)
    def job_state(self):
        with self.state_lock:jobs=list(self.jobs.values())[::-1][:15]
        browse_status=self.browse.status()
        with self.db() as db:revision=db.execute("SELECT value FROM browse_state WHERE key='revision'").fetchone()[0]
        return {'jobs':jobs,'catalogRevision':revision,'browseIndexStatus':browse_status,'collectionIndexStatus':'unavailable' if self.collection_references.failure else 'building' if self.collection_references.pending or self.collection_references.deferred and self.operation_lock.locked() else 'ready'}
    @contextmanager
    def exclusive_operation(self):
        if not self.operation_lock.acquire(blocking=False):raise Problem('Another library operation is running. Wait for it to finish.',409)
        try:yield
        finally:self.operation_lock.release()
    def start_job(self,type,worker):
        if not self.operation_lock.acquire(blocking=False):raise Problem('Another library operation is running. Wait for it to finish.',409)
        job={'id':uuid.uuid4().hex,'type':type,'status':'queued','done':0,'total':0,'errors':[],'createdAt':now(),'message':'Starting…'}
        try:self.save_job(job)
        except BaseException:self.operation_lock.release();raise
        def run():
            try:
                job['status']='running';self.save_job(job);worker(job)
                job['status']='complete' if not job['errors'] else 'partial'
            except Exception as e:
                job['status']='failed';job['message']=str(e);job['errors'].append(str(e))
            finally:
                # Publish the terminal status only after the operation becomes
                # available, so a client cannot observe "complete" and then
                # receive a false conflict when starting the next operation.
                self.operation_lock.release()
                job['finishedAt']=now()
                self.save_job(job)
        threading.Thread(target=run,daemon=True).start()
        return {'id':job['id']}
    def disc_status(self):
        details=audio_cd_drive_details();devices=[entry['device'] for entry in details];tools=tool_status()
        return {'platform':'windows' if os.name=='nt' else 'linux' if os.name=='posix' else 'other','devices':devices,'driveDetails':details,'tools':tools,
                'ready':bool(any(entry['readable'] for entry in details) and os.name in ('nt','posix')),
                'message':('Insert an audio CD, then choose a drive.' if any(entry['readable'] for entry in details)
                           else 'Blank Box can see the optical drive but cannot read it. Check drive access and close other disc applications.' if devices and os.name=='nt'
                           else 'Blank Box can see the optical drive but cannot read it. Grant the service account access to the cdrom group.' if devices
                           else 'No optical drive is available to Blank Box. Connect or pass through a drive to this host.')}
    def disc_probe(self,device):
        try:return probe_audio_cd(device)
        except DiscImportError as error:raise Problem(str(error)) from error
    def catalog_audio_cd(self,data):
        """Record an observed audio CD and physical copy without reading audio sectors."""
        title=data.get('title');artist=data.get('artist');location=data.get('location','')
        fingerprint=data.get('tocFingerprint');metadata_id=data.get('metadataEntityId');item_id=data.get('itemId')
        if not isinstance(title,str) or not 1<=len(title.strip())<=250 or not isinstance(artist,str) or not 1<=len(artist.strip())<=250:
            raise Problem('Enter an album title and artist before cataloging the CD.')
        if not isinstance(location,str) or len(location)>250:raise Problem('Enter a valid physical location.')
        if not isinstance(fingerprint,str) or not re.fullmatch(r'[0-9a-f]{64}',fingerprint):raise Problem('Identify the disc again before cataloging it.')
        if metadata_id is not None and (not isinstance(metadata_id,str) or not 1<=len(metadata_id)<=120):raise Problem('Choose a valid music metadata candidate.')
        probe=self.disc_probe(data.get('device'))
        if probe['tocFingerprint']!=fingerprint:raise Problem('The disc changed. Identify it again before cataloging.',409)
        for existing in self.items():
            if any(source.get('type')=='physical' and source.get('tocFingerprint')==fingerprint for source in existing.get('sources',[])):
                if existing['id']==item_id:return {'ok':True,'item':self.public_item(existing),'alreadyLinked':True}
                raise Problem('This disc is already cataloged. Choose that album to digitize it or add another copy through Physical media.',409)
        if item_id is not None:
            if not isinstance(item_id,str):raise Problem('Choose a music album.')
            item=self.get_item(item_id)
            if item.get('kind')!='music':raise Problem('A CD can only link to a music album.')
        else:item={'id':uuid.uuid4().hex,'title':title.strip(),'kind':'music','artist':artist.strip(),'sources':[],'addedAt':now(),
                   'description':'A physical audio CD in your collection. No local tracks have been copied.'}
        source={'id':uuid.uuid4().hex,'type':'physical','label':'CD','location':location.strip(),'tocFingerprint':fingerprint,
                'discId':probe.get('discId'),'addedAt':now()}
        item.setdefault('sources',[]).append(source)
        if not item.get('artist'):item['artist']=artist.strip()
        if not item.get('trackCount'):item['trackCount']=probe['trackCount']
        ensure_item_model(item)
        try:self.catalog.save_item(item,reviewed_metadata_id=metadata_id,reviewed_physical_source_id=source['id'],
                                   evidence_namespace='musicbrainz-discid',evidence_value=probe.get('discId'),pack_repository=self.metadata_packs)
        except (ValueError,sqlite3.IntegrityError) as error:raise Problem(str(error)) from error
        self.remember_physical_choices(source)
        return {'ok':True,'item':self.public_item(item)}
    def import_audio_cd(self,data):
        device=data.get('device');fingerprint=data.get('tocFingerprint')
        title=data.get('title','');artist=data.get('artist','');track_titles=data.get('trackTitles')
        location=data.get('location','');item_id=data.get('itemId');metadata_id=data.get('metadataEntityId')
        if metadata_id is not None and (not isinstance(metadata_id,str) or len(metadata_id)>120):raise Problem('Choose a valid music metadata candidate.')
        if not isinstance(title,str) or len(title.strip())>250:raise Problem('Enter an album title up to 250 characters.')
        if not isinstance(artist,str) or len(artist.strip())>250:raise Problem('Enter an artist up to 250 characters.')
        if not isinstance(location,str) or len(location)>250:raise Problem('Enter a valid physical location.')
        if not isinstance(track_titles,list) or not track_titles or len(track_titles)>99 or any(not isinstance(name,str) or len(name.strip())>250 for name in track_titles):raise Problem('Enter valid track titles up to 250 characters.')
        if not isinstance(fingerprint,str) or not re.fullmatch(r'[0-9a-f]{64}',fingerprint):raise Problem('Read the disc again before importing.')
        if data.get('confirmRights') is not True:raise Problem('Confirm you are authorized to make this local copy.')
        if item_id is not None:
            if not isinstance(item_id,str):raise Problem('Choose a valid album.')
            existing=self.get_item(item_id)
            if existing.get('kind')!='music':raise Problem('A CD can only link to a music album.')
        title=title.strip() or 'Untitled audio CD';artist=artist.strip() or 'Unknown artist';track_titles=[name.strip() or f'Track {index:02d}' for index,name in enumerate(track_titles,1)]
        probe=self.disc_probe(device)
        if probe['tocFingerprint']!=fingerprint or probe['trackCount']!=len(track_titles):raise Problem('The disc changed. Read it again before importing.',409)
        if metadata_id:
            if metadata_id.startswith('pack:'):
                try:pack,record=self.metadata_packs.record(*metadata_id.split(':')[1:])
                except (ValueError,TypeError,OSError):raise Problem('The selected metadata pack is unavailable.') from None
                entity={'kind':record['kind'],'level':record['level'],'identifiers':record.get('identifiers',[])} if record else None
            else:entity=self.metadata.get_entity(metadata_id)
            if not entity or entity['kind']!='music':raise Problem('Choose a music metadata candidate.')
            if entity['level']=='release' and (not probe.get('discId') or not any(physical_namespace(identifier['namespace'])=='disc-id' and identifier['value']==probe['discId'] for identifier in entity['identifiers'])):
                raise Problem('That release does not have this CD’s Disc ID. Review the release candidates again.')
        if any(item.get('discImport',{}).get('tocFingerprint')==fingerprint for item in self.items()):raise Problem('This disc was already imported. Open its album in Music.',409)
        cataloged=next((item for item in self.items() if any(source.get('type')=='physical' and source.get('tocFingerprint')==fingerprint for source in item.get('sources',[]))),None)
        if cataloged and cataloged['id']!=item_id:raise Problem('This CD is already cataloged. Link the digitized tracks to that album.',409)
        def worker(job):
            again=probe_audio_cd(device)
            if again['tocFingerprint']!=fingerprint:raise DiscImportError('The disc changed before extraction. Nothing was added.')
            job.update(total=len(track_titles),message='Reading audio tracks from the disc');self.save_job(job)
            with tempfile.TemporaryDirectory(prefix='blankbox-disc-',dir=self.data) as scratch:
                (Path(scratch)/STAGING_MARKER).write_text(STAGING_MARKER,encoding='ascii')
                def progress(done,total):
                    job.update(done=done,message=f'Imported {done} of {total} lossless tracks');self.save_job(job)
                tracks,format_name,mime,extraction=extract_audio_cd(device,fingerprint,len(track_titles),Path(scratch)/'tracks',title,artist,track_titles,progress)
                if probe_audio_cd(device)['tocFingerprint']!=fingerprint:raise DiscImportError('The disc changed during extraction. Nothing was added.')
                album=self.get_item(item_id) if item_id else {'id':uuid.uuid4().hex,'title':title,'kind':'music','sources':[],'addedAt':now()}
                if album.get('kind')!='music':raise DiscImportError('The destination album changed during extraction.')
                if any(item.get('discImport',{}).get('tocFingerprint')==fingerprint for item in self.items()):raise DiscImportError('This disc was imported in another operation.')
                sources=list(album.get('sources',[]))
                physical_source=next((source for source in sources if source.get('type')=='physical' and source.get('tocFingerprint')==fingerprint),None)
                if physical_source is None:
                    physical_source={'id':uuid.uuid4().hex,'type':'physical','label':'CD','location':location.strip(),'tocFingerprint':fingerprint,'discId':probe.get('discId'),'addedAt':now()}
                    sources.append(physical_source)
                added=[];created=[]
                try:
                    for index,path in enumerate(tracks,1):
                        sha=digest(path);relative=Path('music')/sha/f'track{index:02d}{path.suffix}'
                        target=safe_destination(self.media,relative);existed=target.exists()
                        checked_copy(path,target,sha)
                        if not existed:created.append((target,sha))
                        added.append({'id':uuid.uuid4().hex,'type':'local','label':'Blank Box',
                                      'storedPath':relative.as_posix(),'sha256':sha,'bytes':path.stat().st_size,'mime':mime,
                                      'trackNumber':index,'trackTitle':track_titles[index-1],'artist':artist,'addedAt':now(),
                                      'extraction':extraction,'encodingVerified':format_name=='FLAC'})
                    album.pop('backupVerifiedAt',None)
                    album.update(title=title,artist=artist,trackCount=len(tracks),sources=sources+added,backup='none',
                                 discImport={'tocFingerprint':fingerprint,'format':format_name,'extraction':extraction,
                                             'discId':probe.get('discId'),'encodingVerified':format_name=='FLAC','discAccuracyVerified':False,'importedAt':now()})
                    if location.strip():self.remember_physical_choices(physical_source)
                    ensure_item_model(album)
                    self.catalog.save_item(album,reviewed_metadata_id=metadata_id,reviewed_physical_source_id=physical_source['id'],evidence_namespace='musicbrainz-discid',evidence_value=probe.get('discId'),pack_repository=self.metadata_packs)
                except Exception:
                    # Revert only files created by this job, and only if unchanged.
                    for target,sha in created:
                        try:
                            if target.is_file() and digest(target)==sha:target.unlink()
                        except OSError:pass
                    raise
                job.update(done=len(tracks),itemId=album['id'],message=f'{len(tracks)} lossless {format_name} tracks added to {title}. Disc accuracy not independently checked.')
        return self.start_job('disc-import',worker)
    def scan(self,source_id,selected_paths=None):
        root=self.source_roots.get(source_id)
        if not root or not root.is_dir():raise Problem('This source is unavailable.')
        def worker(job):
            candidates=[];records=[];hashes={source.get('sha256') or item.get('sha256') for item in self.items() for source in item.get('sources',[]) if source.get('type')=='local' and (source.get('sha256') or item.get('sha256'))}
            if selected_paths is not None:candidates=list(selected_paths)
            else:
                def walk_error(e):job['errors'].append(str(e))
                for folder,dirs,files in os.walk(root,followlinks=False,onerror=walk_error):
                    dirs[:]=[n for n in dirs if not n.startswith('.') and not (Path(folder)/n).is_symlink()]
                    for name in sorted(files):
                        p=Path(folder)/name
                        if name.startswith('.') or p.is_symlink() or not p.is_file():continue
                        candidates.append(p.relative_to(root).as_posix())
                        if len(candidates)>100000:raise ValueError('Source exceeds the V1 limit of 100,000 files. Choose a smaller source folder.')
            job['total']=len(candidates);self.save_job(job)
            for index,rel in enumerate(candidates):
                try:
                    p=safe_file(root,rel);before=p.stat();sha=digest(p)
                    if selected_paths is not None and selected_paths[rel]!=fingerprint(before):raise ValueError('File changed since discovery. Wait for the next stable check.')
                    if fingerprint(before)!=fingerprint(p.stat()):raise ValueError('File changed while scanning.')
                    kind=kind_for(rel);title,year=inferred_title(rel);incoming={'title':title,'kind':kind,**({'year':year} if year else {})}
                    records.append({'id':uuid.uuid4().hex,'name':rel,'title':title,'year':year,'bytes':before.st_size,'kind':kind,'duplicate':sha in hashes,'sha256':sha,'stat':fingerprint(before),'candidates':self.match_candidates(incoming)})
                    hashes.add(sha)
                except (OSError,ValueError) as e:job['errors'].append(f'{rel}: {e}')
                job['done']=index+1;job['message']=f"Read {index+1} of {len(candidates)} files"
                if index%10==0:self.save_job(job)
            with self.state_lock:
                self.scans[job['id']]={'sourceId':source_id,'files':records}
                while len(self.scans)>3:self.scans.pop(next(iter(self.scans)))
            job['message']=f'{len(records)} readable files found. Review before importing.'
        return self.start_job('scan',worker)
    def refresh_tasks(self):
        settings=self.get_settings();tasks=[]
        if settings.get('autoSourceIndex'):tasks.extend('index:'+key for key in self.source_roots)
        if settings.get('autoFolderCopy') and not settings.get('autoSourceIndex') and self.source_roots:tasks.append('folders')
        for provider in ('jellyfin','plex'):
            if settings.get('autoProviderRefresh') and self.connection(provider):tasks.append(provider)
        return tasks
    def refresh_task(self,task):
        if task.startswith('index:'):return self.monitor_source(task[6:])
        if task=='folders':return self.auto_import()
        if task=='jellyfin':return self.sync_saved_jellyfin()
        if task=='plex':return self.sync_saved_plex()
        raise Problem('Unknown refresh source.')
    def refresh_failure(self,task,error):
        kind='source-monitor' if task.startswith('index:') else 'auto-discovery' if task=='folders' else task
        self.save_job({'id':uuid.uuid4().hex,'type':kind,'status':'failed','done':0,'total':0,'createdAt':now(),'finishedAt':now(),'message':str(error),'errors':[str(error)]})
    def monitor_source(self,source_id):
        return monitor_source(self,source_id)
    def index_source(self,source_id,resume_id=None):
        """Persist a read-only source inventory. This never opens media bytes or changes items."""
        root=self.source_roots.get(source_id)
        if not root or not root.is_dir():raise Problem('This source is unavailable.')
        root_stat=root.stat();identity=f'{root_stat.st_dev}:{root_stat.st_ino}'
        if resume_id is not None:
            if not isinstance(resume_id,str) or not re.fullmatch(r'[0-9a-f]{32}',resume_id):raise Problem('Invalid inventory batch.')
            with self.db() as db:previous=db.execute('SELECT * FROM inventory_batches WHERE id=?',(resume_id,)).fetchone()
            if not previous or previous['source_id']!=source_id or previous['source_path']!=str(root):raise Problem('Inventory batch not found.',404)
            if previous['root_identity']!=identity:raise Problem('The source changed. Start a fresh inventory instead.',409)
            if previous['status'] not in ('interrupted','partial','failed'):raise Problem('This inventory cannot be resumed.',409)
            batch_id=resume_id
        else:batch_id=uuid.uuid4().hex
        def worker(job):
            errors=[];pending=[];seen=0
            count=int(previous['scanned']) if resume_id else 0
            total_bytes=int(previous['total_bytes']) if resume_id else 0
            def flush():
                nonlocal count,total_bytes
                if not pending:return
                with self.db() as db:
                    for record in pending:
                        inserted=db.execute('INSERT OR IGNORE INTO inventory_files(batch_id,relative_path,kind,title,title_key,year,bytes,mtime_ns,clues,group_key) VALUES(?,?,?,?,?,?,?,?,?,?)',record)
                        if inserted.rowcount:
                            count+=1;total_bytes+=record[6]
                    db.execute('UPDATE inventory_batches SET scanned=?,total_bytes=?,errors=? WHERE id=?',(count,total_bytes,json.dumps(errors[:20]),batch_id))
                pending.clear();job.update(done=count,total=0,message=f'{count} files inventoried; no files copied');self.save_job(job)
            try:
                with self.db() as db:
                    if resume_id:db.execute("UPDATE inventory_batches SET status='running',finished_at=NULL WHERE id=?",(batch_id,))
                    else:db.execute('INSERT INTO inventory_batches(id,source_id,source_path,root_identity,status,started_at) VALUES(?,?,?,?,?,?)',(batch_id,source_id,str(root),identity,'running',now()))
                def walk_error(error):
                    if len(errors)<20:errors.append(str(error))
                for folder,dirs,files in os.walk(root,followlinks=False,onerror=walk_error):
                    if not inside(Path(folder).resolve(),root):
                        dirs.clear();continue
                    dirs[:]=sorted(name for name in dirs if not name.startswith('.') and not (Path(folder)/name).is_symlink())
                    for name in sorted(files):
                        if name.startswith('.'):continue
                        path=Path(folder)/name
                        try:
                            details=path.stat(follow_symlinks=False)
                            if not stat.S_ISREG(details.st_mode):continue
                            relative=path.relative_to(root).as_posix()
                            kind=kind_for(relative);raw_title,raw_year=inferred_title(name)
                            clues=path_clues(relative,kind,raw_title,raw_year);title=clues['title'];year=clues['year']
                            pending.append((batch_id,relative,kind,title,inventory_title_key(title),year,details.st_size,details.st_mtime_ns,json.dumps(clues),clues['groupKey']))
                            seen+=1
                            if seen>1000000:raise Problem('This source exceeds the current inventory limit of 1,000,000 files. Split it into smaller configured folders.')
                            if len(pending)>=250:flush()
                        except OSError as error:
                            if len(errors)<20:errors.append(f'{name}: {error}')
                flush()
                if not root.is_dir() or f'{root.stat().st_dev}:{root.stat().st_ino}'!=identity:
                    raise Problem('The source changed or disconnected during inventory. Reconnect it before resuming.')
                with self.db() as db:db.execute('UPDATE inventory_batches SET status=?,finished_at=?,errors=? WHERE id=?',('partial' if errors else 'complete',now(),json.dumps(errors[:20]),batch_id))
                if errors:job['errors'].extend(errors)
                job['message']=f'{job["done"]} files inventoried without copying media.'
            except Exception:
                flush()
                with self.db() as db:db.execute("UPDATE inventory_batches SET status='interrupted',finished_at=?,errors=? WHERE id=?",(now(),json.dumps(errors[:20]),batch_id))
                raise
        result=self.start_job('inventory',worker)
        return {**result,'batchId':batch_id}
    def inventory(self,source_id,limit=30,offset=0,kind=None,query='',group='',unlinked_only=False):
        if source_id not in self.source_roots:raise Problem('Choose a configured source.')
        if not isinstance(limit,int) or not 1<=limit<=100 or not isinstance(offset,int) or not 0<=offset<=1000000:raise Problem('Invalid inventory page.')
        if kind and kind not in KINDS:raise Problem('Unknown media type.')
        if not isinstance(query,str) or len(query)>100:raise Problem('Search is too long.')
        if not isinstance(group,str) or len(group)>600:raise Problem('Invalid clue group.')
        if not isinstance(unlinked_only,bool):raise Problem('Invalid inventory filter.')
        with self.db() as db:
            batch=db.execute('SELECT * FROM inventory_batches WHERE source_id=? ORDER BY started_at DESC,rowid DESC LIMIT 1',(source_id,)).fetchone()
            if not batch:return {'batch':None,'files':[],'total':0,'counts':[]}
            conditions=['f.batch_id=?'];params=[batch['id']]
            if kind:conditions.append('f.kind=?');params.append(kind)
            if group:conditions.append('f.group_key=?');params.append(group)
            key=inventory_title_key(query)
            if key:conditions.append('f.title_key>=? AND f.title_key<?');params.extend((key,key+'\U0010ffff'))
            if unlinked_only:conditions.append("(l.item_id IS NULL OR NOT EXISTS(SELECT 1 FROM items i,json_each(i.data,'$.sources') js WHERE i.id=l.item_id AND json_extract(js.value,'$.id')=l.media_source_id AND json_extract(js.value,'$.bytes')=f.bytes AND json_extract(js.value,'$.sourceMtimeNs')=f.mtime_ns))")
            where=' AND '.join(conditions)
            joined=' FROM inventory_files f LEFT JOIN inventory_links l ON l.source_id=? AND l.relative_path=f.relative_path WHERE '+where
            total=db.execute('SELECT COUNT(*)'+joined,(source_id,*params)).fetchone()[0]
            rows=db.execute('SELECT f.relative_path,f.kind,f.title,f.year,f.bytes,f.mtime_ns,f.clues,f.group_key,l.item_id AS linked_item_id,CASE WHEN l.item_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM items i,json_each(i.data,\'$.sources\') js WHERE i.id=l.item_id AND json_extract(js.value,\'$.id\')=l.media_source_id AND json_extract(js.value,\'$.bytes\')=f.bytes AND json_extract(js.value,\'$.sourceMtimeNs\')=f.mtime_ns) THEN 1 ELSE 0 END AS needs_review'+joined+' ORDER BY f.relative_path LIMIT ? OFFSET ?',(source_id,*params,limit,offset)).fetchall()
            counts=db.execute('SELECT kind,COUNT(*) AS count FROM inventory_files WHERE batch_id=? GROUP BY kind ORDER BY count DESC',(batch['id'],)).fetchall()
            groups=db.execute('SELECT f.group_key AS groupKey,MIN(f.title) AS title,MIN(f.kind) AS kind,COUNT(*) AS count,SUM(CASE WHEN l.item_id IS NULL THEN 1 ELSE 0 END) AS unlinked FROM inventory_files f LEFT JOIN inventory_links l ON l.source_id=? AND l.relative_path=f.relative_path WHERE f.batch_id=? AND f.group_key<>? GROUP BY f.group_key HAVING COUNT(*)>1 ORDER BY unlinked DESC,count DESC LIMIT 40',(source_id,batch['id'],'')).fetchall()
        return {'batch':{'id':batch['id'],'sourceId':batch['source_id'],'status':batch['status'],'startedAt':batch['started_at'],'finishedAt':batch['finished_at'],'scanned':batch['scanned'],'totalBytes':batch['total_bytes'],'errors':json.loads(batch['errors'])},'files':[{**dict(row),'clues':json.loads(row['clues']) if row['clues'] else {},'groupKey':row['group_key']} for row in rows],'total':total,'counts':[dict(row) for row in counts],'groups':[dict(row) for row in groups]}
    def inventory_record(self,batch_id,relative_path):
        if not isinstance(batch_id,str) or not re.fullmatch(r'[0-9a-f]{32}',batch_id):raise Problem('Choose an indexed batch.')
        if not isinstance(relative_path,str) or not 1<=len(relative_path)<=4096:raise Problem('Choose an indexed file.')
        with self.db() as db:
            batch=db.execute('SELECT * FROM inventory_batches WHERE id=?',(batch_id,)).fetchone()
            record=db.execute('SELECT * FROM inventory_files WHERE batch_id=? AND relative_path=?',(batch_id,relative_path)).fetchone()
        if not batch or not record:raise Problem('This file is not in the selected inventory.',404)
        if batch['source_id'] not in self.source_roots:raise Problem('This source is no longer configured.',409)
        return batch,record
    def inventory_candidates(self,title,kind,year=None):
        key=work_title_key(title)
        if not key or kind not in KINDS:return []
        allowed=('movie','tv') if kind in ('movie','tv') else (kind,)
        with self.db() as db:
            placeholders=','.join('?' for _ in allowed)
            rows=db.execute('SELECT i.data,s.title_key FROM item_search s JOIN items i ON i.id=s.item_id WHERE s.title_key=? AND s.kind IN ('+placeholders+') ORDER BY i.rowid DESC LIMIT 30',(key,*allowed)).fetchall()
            if len(key)>=4 and len(rows)<12:
                rows+=db.execute('SELECT i.data,s.title_key FROM item_search s JOIN items i ON i.id=s.item_id WHERE s.title_key>=? AND s.title_key<? AND s.kind IN ('+placeholders+') AND s.title_key<>? ORDER BY i.rowid DESC LIMIT 30',(key,key+'\U0010ffff',*allowed,key)).fetchall()
            if len(rows)<12:
                seen={json.loads(row['data'])['id'] for row in rows}
                for candidate_kind in allowed:
                    for candidate_id in self.token_candidate_ids(db,title,candidate_kind,year):
                        if candidate_id in seen:continue
                        candidate=db.execute('SELECT i.data,s.title_key FROM item_search s JOIN items i ON i.id=s.item_id WHERE i.id=?',(candidate_id,)).fetchone()
                        if candidate:rows.append(candidate);seen.add(candidate_id)
            pending={json.loads(row[0]).get('incoming',{}).get('id') for row in db.execute('SELECT data FROM review_queue')}
        candidates=[]
        for row in rows:
            item=json.loads(row[0])
            if item['id'] in pending or year and item.get('year') and item['year']!=year:continue
            candidate=self.public_item(item)
            exact=row['title_key']==key
            candidate['matchConfidence']='high' if exact and year and item.get('year')==year and item.get('kind')==kind else 'review'
            candidate['matchReason']='Same title, year, and media type' if candidate['matchConfidence']=='high' else 'Shared title words; confirm this is the same work' if not exact and not row['title_key'].startswith(key) else 'Partial title suggestion; confirm this is the same work' if not exact else 'Same title; confirm the edition and media type'
            candidates.append(candidate)
        return candidates[:12]
    def token_candidate_ids(self,db,title,kind,year=None):
        tokens=title_tokens(title)
        if len(tokens)<2:return []
        placeholders=','.join('?' for _ in tokens)
        rows=db.execute('SELECT s.item_id,COUNT(*) AS overlap FROM item_search_tokens t JOIN item_search s ON s.item_id=t.item_id WHERE t.token IN ('+placeholders+') AND s.kind=? AND (s.year=? OR s.year IS NULL OR ? IS NULL) GROUP BY s.item_id HAVING overlap>=2 ORDER BY overlap DESC,s.title_key LIMIT 12',(*tokens,kind,year,year)).fetchall()
        return [row['item_id'] for row in rows]
    def list_candidate_ids(self,db,title,kind,year=None):
        key=work_title_key(title)
        if not key:return []
        rows=db.execute('SELECT item_id FROM item_search WHERE title_key=? AND kind=? AND (year=? OR year IS NULL OR ? IS NULL) LIMIT 12',(key,kind,year,year)).fetchall()
        ids=[row['item_id'] for row in rows]
        if len(key)>=4 and len(ids)<12:
            rows=db.execute('SELECT item_id FROM item_search WHERE title_key>=? AND title_key<? AND kind=? AND title_key<>? AND (year=? OR year IS NULL OR ? IS NULL) LIMIT 12',(key,key+'\U0010ffff',kind,key,year,year)).fetchall()
            ids.extend(row['item_id'] for row in rows)
        if len(ids)<12:ids.extend(candidate_id for candidate_id in self.token_candidate_ids(db,title,kind,year) if candidate_id not in ids)
        return ids[:12]
    def inventory_review(self,batch_id,relative_path,title=None,kind=None,year=None):
        batch,record=self.inventory_record(batch_id,relative_path)
        title=record['title'] if title is None else title
        kind=record['kind'] if kind is None else kind
        # An explicit null clears an unreliable year inferred from the filename.
        if not isinstance(title,str) or not 1<=len(title.strip())<=250:raise Problem('Enter a title up to 250 characters.')
        if kind not in KINDS:raise Problem('Choose a media type.')
        if year is not None and (isinstance(year,bool) or not isinstance(year,int) or not 1800<=year<=2200):raise Problem('Enter a valid year.')
        with self.db() as db:link=db.execute('SELECT item_id FROM inventory_links WHERE source_id=? AND relative_path=?',(batch['source_id'],record['relative_path'])).fetchone()
        return {'record':{'path':record['relative_path'],'title':title.strip(),'kind':kind,'year':year,'bytes':record['bytes'],'clues':json.loads(record['clues']) if record['clues'] else {},'groupKey':record['group_key']},'sourceId':batch['source_id'],'linkedItemId':link[0] if link else None,'candidates':self.inventory_candidates(title,kind,year)}
    def rename_preview(self,batch_id,relative_path,title,kind,year):
        review=self.inventory_review(batch_id,relative_path,title,kind,year)
        batch,record=self.inventory_record(batch_id,relative_path)
        clues=review['record']['clues']
        try:proposed=proposed_filename(relative_path,title.strip(),year,kind,clues)
        except ValueError as error:raise Problem(str(error)) from error
        root=self.source_roots[batch['source_id']]
        try:target=safe_destination(root,proposed)
        except ValueError as error:raise Problem(str(error),409) from error
        return {'originalPath':relative_path,'proposedPath':proposed,'changed':proposed!=relative_path,
                'collision':proposed!=relative_path and (target.exists() or target.is_symlink()),'bytes':record['bytes'],
                'message':'Preview only. Blank Box has not renamed or moved the original file.'}
    def inventory_link(self,data,_lock_held=False,_db=None,_bulk_fast=False):
        if data.get('confirm') is not True:raise Problem('Review and confirm this file before linking it.')
        batch,record=self.inventory_record(data.get('batchId'),data.get('path'))
        title=data.get('title');kind=data.get('kind');year=data.get('year');target_id=data.get('targetId');metadata_id=data.get('metadataEntityId')
        if not isinstance(title,str) or not 1<=len(title.strip())<=250:raise Problem('Enter a title up to 250 characters.')
        if kind not in KINDS:raise Problem('Choose a media type.')
        if year is not None and (isinstance(year,bool) or not isinstance(year,int) or not 1800<=year<=2200):raise Problem('Enter a valid year.')
        if target_id is not None and (not isinstance(target_id,str) or not re.fullmatch(r'[A-Za-z0-9._:-]{1,120}',target_id)):raise Problem('Choose a valid library item.')
        if metadata_id is not None and (not isinstance(metadata_id,str) or len(metadata_id)>120):raise Problem('Choose a valid metadata candidate.')
        if not _lock_held and not self.operation_lock.acquire(blocking=False):raise Problem('Another file operation is running. Wait for it to finish.',409)
        try:
            root=self.source_roots[batch['source_id']]
            try:root_stat=root.stat()
            except OSError as error:raise Problem('The source drive is unavailable. Reconnect it and index again.',409) from error
            if f'{root_stat.st_dev}:{root_stat.st_ino}'!=batch['root_identity']:raise Problem('The drive changed since inventory. Index it again.',409)
            try:path=safe_file(root,record['relative_path']);details=path.stat()
            except (OSError,ValueError) as error:raise Problem('The indexed file is unavailable or its path changed. Index again.',409) from error
            if details.st_size!=record['bytes'] or details.st_mtime_ns!=record['mtime_ns']:raise Problem('The file changed since inventory. Index it again.',409)
            source_id=ownership_id('indexed-source',batch['source_id'],record['relative_path'])
            with (nullcontext(_db) if _db is not None else self.db()) as db:
                linked=db.execute('SELECT item_id FROM inventory_links WHERE source_id=? AND relative_path=?',(batch['source_id'],record['relative_path'])).fetchone()
                if linked:
                    if target_id and linked['item_id']!=target_id:raise Problem('This file is linked to another item. Remove that link before changing it.',409)
                    item=json.loads(db.execute('SELECT data FROM items WHERE id=?',(linked['item_id'],)).fetchone()[0])
                    source=next((s for s in item.get('sources',[]) if s.get('id')==source_id),None)
                    if not source:raise Problem('This file link is inconsistent. Review its item sources.',409)
                    if source.get('bytes')==record['bytes'] and source.get('sourceMtimeNs')==record['mtime_ns']:
                        return {'ok':True,'alreadyLinked':True,**({'itemId':item['id']} if _bulk_fast else {'item':self.public_item(item)})}
                    source.update(bytes=record['bytes'],sourceMtimeNs=record['mtime_ns'],rootIdentity=batch['root_identity'])
                    if item.get('kind')!=kind:raise Problem('The linked item has a different media type. Review its source before changing it.',409)
                    db.execute('UPDATE items SET data=? WHERE id=?',(json.dumps(item),item['id']))
                    sync_digital_releases(db,item)
                    return {'ok':True,'changed':True,**({'itemId':item['id']} if _bulk_fast else {'item':self.public_item(item)})}
                if target_id:
                    row=db.execute('SELECT data FROM items WHERE id=?',(target_id,)).fetchone()
                    if not row:raise Problem('That library item is no longer available.',404)
                    item=json.loads(row[0]);ensure_item_model(item)
                    if item.get('kind')!=kind and not (item.get('kind') in ('movie','tv') and kind in ('movie','tv')):raise Problem('This file and library item have different media types.',409)
                    if year and item.get('year') and item['year']!=year:raise Problem('The release years differ. Review this match again.',409)
                else:
                    item={'id':uuid.uuid4().hex,'title':title.strip(),'kind':kind,'sources':[],'addedAt':now(),'backup':'none'}
                    if year:item['year']=year
                    ensure_item_model(item)
                mime=mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
                clues=json.loads(record['clues']) if record['clues'] else {}
                source={'id':source_id,'versionId':item['versions'][0]['id'],'type':'digital','label':root.name or 'Connected drive','sourceId':batch['source_id'],'rootIdentity':batch['root_identity'],'path':record['relative_path'],'sourceMtimeNs':record['mtime_ns'],'bytes':record['bytes'],'mime':mime,'url':'/media/'+urllib.parse.quote(item['id'])+'/'+source_id,'addedAt':now()}
                if kind=='tv':
                    if isinstance(clues.get('season'),int):source['season']='specials' if clues['season']==0 else str(clues['season'])
                    if isinstance(clues.get('episode'),int):source['episodeNumber']=clues['episode']
                    if isinstance(clues.get('episodeEnd'),int):source['episodeEnd']=clues['episodeEnd']
                if kind=='music':
                    if isinstance(clues.get('trackNumber'),int):source['trackNumber']=clues['trackNumber']
                    if isinstance(clues.get('trackTitle'),str) and clues['trackTitle'].strip():source['trackTitle']=clues['trackTitle'].strip()
                    if isinstance(clues.get('artist'),str) and clues['artist'].strip():source['artist']=clues['artist'].strip()
                if kind=='book' and (clues.get('audioBook') or path.suffix.casefold()=='.m4b'):source['audioBook']=True
                if isinstance(clues.get('quality'),str):source['quality']=clues['quality']
                item['sources'].append(source)
                if not target_id:
                    item['bytes']=record['bytes'];item['mime']=mime
                    if kind=='photo' and mime.startswith('image/'):item['poster']=source['url']
                db.execute('INSERT INTO items(id,data) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',(item['id'],json.dumps(item)))
                if _bulk_fast:
                    # This lane adds only a digital observation. Existing physical
                    # ownership and title facts were not changed by this link.
                    if not target_id:
                        sync_item_search(db,item)
                        backfill_item(db,item)
                else:
                    if sync_physical_ownership(db,item):db.execute('UPDATE items SET data=? WHERE id=?',(json.dumps(item),item['id']))
                    sync_item_search(db,item)
                    backfill_item(db,item)
                    sync_owned_releases(db,item)
                if metadata_id:
                    try:
                        local_id=self.metadata_packs.materialize(db,metadata_id) if metadata_id.startswith('pack:') else metadata_id
                        confirm_entity(db,'item',item['id'],local_id)
                        apply_reference_details(db,item,local_id)
                    except (ValueError,OSError) as error:raise Problem(str(error),409) from error
                db.execute('INSERT INTO inventory_links(source_id,relative_path,item_id,media_source_id,linked_at) VALUES(?,?,?,?,?)',(batch['source_id'],record['relative_path'],item['id'],source_id,now()))
            return {'ok':True,**({'itemId':item['id']} if _bulk_fast else {'item':self.public_item(item)})}
        finally:
            if not _lock_held:self.operation_lock.release()
    def inventory_link_selected(self,data):
        paths=data.get('paths');target_id=data.get('targetId');batch_id=data.get('batchId')
        if not isinstance(paths,list) or not 2<=len(paths)<=100 or len(paths)!=len(set(map(str,paths))):
            raise Problem('Select 2 to 100 distinct indexed files for one title.')
        if not isinstance(target_id,str) or not re.fullmatch(r'[A-Za-z0-9._:-]{1,120}',target_id):
            raise Problem('Choose an existing Media Item.')
        if data.get('confirm') is not True or data.get('confirmedCount')!=len(paths):
            raise Problem('Review the selected files and confirm their count.')
        with self.exclusive_operation():
            target=self.get_item(target_id)
            if target.get('title')!=data.get('targetTitle'):
                raise Problem('The chosen title changed. Review the selection again.',409)
            prepared=[];source_id=None;root_identity=None
            for relative_path in paths:
                batch,record=self.inventory_record(batch_id,relative_path)
                if source_id is None:
                    source_id=batch['source_id'];root_identity=batch['root_identity']
                    root=self.source_roots[source_id]
                    try:root_stat=root.stat()
                    except OSError as error:raise Problem('The source drive is unavailable. Reconnect it and index again.',409) from error
                    if f'{root_stat.st_dev}:{root_stat.st_ino}'!=root_identity:raise Problem('The drive changed since inventory. Index it again.',409)
                if batch['source_id']!=source_id or batch['root_identity']!=root_identity:
                    raise Problem('Select files from one current source inventory.',409)
                if record['kind']!=target.get('kind'):
                    raise Problem('The selection includes a different media type. Review that file separately.',409)
                try:path=safe_file(root,record['relative_path']);details=path.stat()
                except (OSError,ValueError) as error:raise Problem('An indexed file is unavailable or its path changed. Index again.',409) from error
                if details.st_size!=record['bytes'] or details.st_mtime_ns!=record['mtime_ns']:
                    raise Problem('A selected file changed since inventory. Index again.',409)
                prepared.append(record)
            with self.db() as db:
                for record in prepared:
                    linked=db.execute('SELECT item_id FROM inventory_links WHERE source_id=? AND relative_path=?',(source_id,record['relative_path'])).fetchone()
                    if linked and linked['item_id']!=target_id:
                        raise Problem('A selected file belongs to another Media Item. Review that item first.',409)
                for record in prepared:
                    self.inventory_link({'batchId':batch_id,'path':record['relative_path'],'title':target['title'],'kind':record['kind'],'year':None,'targetId':target_id,'confirm':True},_lock_held=True,_db=db,_bulk_fast=True)
                linked_item=json.loads(db.execute('SELECT data FROM items WHERE id=?',(target_id,)).fetchone()['data'])
                sync_digital_releases(db,linked_item)
            return {'ok':True,'item':self.public_item(self.get_item(target_id)),'linkedCount':len(prepared)}
    def inventory_bulk_group(self,record):
        key=work_title_key(record['title'])
        kind=record['kind'];year=record['year'] or ''
        clues=json.loads(record['clues']) if record['clues'] else {}
        if kind=='tv':
            folders=Path(record['relative_path']).parts[:-1]
            show=folders[-2] if len(folders)>1 and re.fullmatch(r'season[ ._-]*\d{1,2}',folders[-1],re.I) else folders[-1] if folders else ''
            return f'{kind}|{key}|{year}|{inventory_title_key(show)}',clues
        if kind=='music':return f'{kind}|{key}|{year}|{inventory_title_key(clues.get("artist",""))}',clues
        return f'{kind}|{key}|{year}',clues
    def inventory_bulk_preview(self,source_id,retry_unmatched=False):
        """Plan conservative in-place links against one complete inventory."""
        if source_id not in self.source_roots:raise Problem('Choose a configured source.')
        if not isinstance(retry_unmatched,bool):raise Problem('Invalid bulk review mode.')
        def worker(job):
            job['sourceId']=source_id
            with self.db() as db:
                batch=db.execute('SELECT * FROM inventory_batches WHERE source_id=? ORDER BY started_at DESC,rowid DESC LIMIT 1',(source_id,)).fetchone()
                if not batch or batch['status']!='complete':raise Problem('Finish a complete source inventory before planning a bulk import.',409)
                rows=db.execute("SELECT f.*,l.item_id AS linked_item_id,CASE WHEN l.item_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM items i,json_each(i.data,'$.sources') js WHERE i.id=l.item_id AND json_extract(js.value,'$.id')=l.media_source_id AND json_extract(js.value,'$.bytes')=f.bytes AND json_extract(js.value,'$.sourceMtimeNs')=f.mtime_ns) THEN 1 ELSE 0 END AS changed_link FROM inventory_files f LEFT JOIN inventory_links l ON l.source_id=? AND l.relative_path=f.relative_path WHERE f.batch_id=? ORDER BY f.relative_path",(source_id,batch['id'])).fetchall()
                revision=db.execute("SELECT value FROM browse_state WHERE key='revision'").fetchone()[0]
            root=self.source_roots[source_id];details=root.stat()
            if f'{details.st_dev}:{details.st_ino}'!=batch['root_identity']:raise Problem('The source drive changed since inventory. Index it again.',409)
            groups={};already=0
            for row in rows:
                group,clues=self.inventory_bulk_group(row)
                entry=groups.setdefault(group,{'rows':[],'linked':set(),'clues':clues})
                entry['rows'].append(row)
                if row['linked_item_id'] and not row['changed_link']:entry['linked'].add(row['linked_item_id']);already+=1
            actions=[];review=[];counts={'inventoryFiles':len(rows),'alreadyLinked':already,'matchExisting':0,'newTitles':0,'newTitleFiles':0,'packReferences':0,'needsReview':0,'linkFiles':0,'linkBytes':0}
            changed=[row for row in rows if row['changed_link']]
            counts['needsReview']=len(changed)
            for row in changed[:10]:review.append({'path':row['relative_path'],'title':row['title'],'kind':row['kind'],'reason':'Previously linked file changed; confirm its source again'})
            job['total']=len(groups);self.save_job(job)
            with self.db() as db:
                for index,(group,entry) in enumerate(groups.items(),1):
                    pending=[row for row in entry['rows'] if not row['linked_item_id']]
                    if pending:
                        row=pending[0];kind=row['kind'];title=row['title'];year=row['year'];key=work_title_key(title);clues=entry['clues']
                        meaningful=len(key)>=4 and not GENERIC.fullmatch(title.strip()) and not any(part.casefold() in {'sample','samples','extras','bonus','trailers'} for part in Path(row['relative_path']).parts) and not re.search(r'(?i)\b(sample|trailer|bonus|featurette|behind[ ._-]+the[ ._-]+scenes)\b',Path(row['relative_path']).stem)
                        strong=meaningful and (kind=='movie' and year is not None or kind=='tv' and isinstance(clues.get('episode'),int) or kind=='music' and bool(clues.get('artist')) and 'album folder' in clues.get('evidence',[]) or kind=='book' and Path(row['relative_path']).suffix.casefold() in ('.epub','.pdf'))
                        allowed=('movie','tv') if kind in ('movie','tv') else (kind,)
                        exact=[]
                        if key:
                            query='SELECT i.id,i.data FROM item_search s JOIN items i ON i.id=s.item_id WHERE s.title_key=? AND s.kind IN ('+','.join('?' for _ in allowed)+') LIMIT 21'
                            exact=[json.loads(candidate['data']) for candidate in db.execute(query,(key,*allowed))]
                        target=None;mode='review';metadata_id=None
                        if len(entry['linked'])==1:
                            linked_id=next(iter(entry['linked']))
                            target=next((candidate for candidate in exact if candidate['id']==linked_id),None)
                            if target and target.get('kind')==kind and (not year or not target.get('year') or target['year']==year):mode='existing'
                        elif len(entry['linked'])>1:mode='review'
                        elif len(exact)==1 and strong:
                            candidate=exact[0]
                            same_year=year is not None and candidate.get('year')==year
                            same_artist=kind=='music' and inventory_title_key(candidate.get('artist',''))==inventory_title_key(clues.get('artist',''))
                            if candidate.get('kind')==kind and (same_year or kind=='tv' and not year and isinstance(clues.get('episode'),int) or same_artist and not year):
                                target=candidate;mode='existing'
                        if mode=='review' and not exact and not entry['linked'] and not any(row['changed_link'] for row in entry['rows']) and (strong or kind=='movie' and meaningful):
                            fuzzy=self.token_candidate_ids(db,title,kind,year)
                            if not fuzzy:
                                mode='new'
                                if year is not None:
                                    try:options=self.metadata_packs.candidates(title=title,kind=kind,year=year,limit=25)
                                    except (OSError,ValueError,sqlite3.Error):options=[]
                                    pack=[option for option in options if option.get('level')=='work' and option.get('year')==year and work_title_key(option.get('title'))==key]
                                    if len(pack)==1:metadata_id=pack[0]['id']
                                    elif len(pack)>1:mode='review'
                        # The first pass stays conservative when a book has
                        # weak filename evidence. After the owner reviews the
                        # remaining queue, a second explicit pass may create a
                        # new book/audiobook only when there is no candidate,
                        # no existing link, and no changed-file warning.
                        if (mode=='review' and retry_unmatched and not exact and not self.list_candidate_ids(db,title,kind,year) and not entry['linked']
                                and not any(row['changed_link'] for row in entry['rows'])
                                and kind in ('book','comic') and meaningful):
                            mode='new'
                        if mode=='review':
                            counts['needsReview']+=len(pending)
                            if len(review)<10:review.append({'path':row['relative_path'],'title':title,'kind':kind,'reason':'Several or uncertain title matches, or insufficient file clues'})
                        else:
                            if mode=='new':
                                counts['newTitles']+=1;counts['newTitleFiles']+=len(pending)
                                if metadata_id:counts['packReferences']+=1
                            else:counts['matchExisting']+=len(pending)
                            for file in pending:
                                actions.append({'batchId':batch['id'],'path':file['relative_path'],'title':file['title'],'kind':file['kind'],'year':file['year'],'group':group,'mode':mode,'targetId':target['id'] if target else None,'metadataEntityId':metadata_id})
                                counts['linkFiles']+=1;counts['linkBytes']+=file['bytes']
                    job['done']=index
                    if index%25==0 or index==len(groups):
                        job['message']=f'{index} of {len(groups)} title groups planned; {counts["linkFiles"]} safe file links, {counts["needsReview"]} for review'
                        self.save_job(job)
            plan={'id':uuid.uuid4().hex,'sourceId':source_id,'batchId':batch['id'],'rootIdentity':batch['root_identity'],'catalogRevision':revision,'createdAt':time.time(),'actions':actions,'counts':counts}
            self.inventory_bulk_plan=plan
            job['preview']={'id':plan['id'],'batchId':batch['id'],'expiresAt':plan['createdAt']+3600,'retryUnmatched':retry_unmatched,'counts':counts,'reviewSamples':review}
            job['message']=f'{counts["linkFiles"]} files can be linked in place; {counts["needsReview"]} need review. No media was copied.'
        return self.start_job('inventory-bulk-preview',worker)
    def inventory_bulk_commit(self,data):
        plan=self.inventory_bulk_plan
        if not plan or data.get('previewId')!=plan['id'] or time.time()-plan['createdAt']>3600:raise Problem('This bulk preview expired. Build a new preview.',409)
        if data.get('confirmBulk') is not True or data.get('warningAccepted') is not True or data.get('confirmedFileCount')!=plan['counts']['linkFiles']:
            raise Problem('Review the file count and matching warning before starting the bulk import.')
        def worker(job):
            job['sourceId']=plan['sourceId']
            with self.db() as db:
                batch=db.execute('SELECT status,root_identity FROM inventory_batches WHERE id=? AND source_id=?',(plan['batchId'],plan['sourceId'])).fetchone()
                revision=db.execute("SELECT value FROM browse_state WHERE key='revision'").fetchone()[0]
            root=self.source_roots.get(plan['sourceId'])
            if not batch or batch['status']!='complete' or not root or not root.is_dir() or f'{root.stat().st_dev}:{root.stat().st_ino}'!=plan['rootIdentity'] or revision!=plan['catalogRevision']:
                raise Problem('The catalog, inventory, or source drive changed since preview. Build a new preview.',409)
            created={};job.update(total=len(plan['actions']),matchedExisting=0,newTitles=0,linked=0,skipped=0)
            self.save_job(job)
            groups={}
            for action in plan['actions']:groups.setdefault(action['group'],[]).append(action)
            for group,actions in groups.items():
                for start in range(0,len(actions),50):
                    chunk=actions[start:start+50];local_target=created.get(group)
                    linked=matched=new_titles=skipped=0;errors=[]
                    with self.db() as db:
                        for action in chunk:
                            db.execute('SAVEPOINT bulk_file')
                            try:
                                target=action['targetId'] if action['mode']=='existing' else local_target
                                result=self.inventory_link({'batchId':action['batchId'],'path':action['path'],'title':action['title'],'kind':action['kind'],'year':action['year'],
                                                            **({'targetId':target} if target else {}),
                                                            **({'metadataEntityId':action['metadataEntityId']} if action['mode']=='new' and not target and action['metadataEntityId'] else {}),
                                                            'confirm':True},_lock_held=True,_db=db,_bulk_fast=True)
                                if action['mode']=='new' and local_target is None:
                                    local_target=result['itemId'];new_titles+=1
                                if action['mode']=='existing':matched+=1
                                linked+=1
                            except (OSError,ValueError,KeyError,sqlite3.Error,Problem) as error:
                                db.execute('ROLLBACK TO SAVEPOINT bulk_file')
                                skipped+=1
                                if len(errors)<20:errors.append(f'{action["path"]}: {error}')
                            finally:db.execute('RELEASE SAVEPOINT bulk_file')
                    if local_target is not None:created[group]=local_target
                    job['linked']+=linked;job['matchedExisting']+=matched;job['newTitles']+=new_titles;job['skipped']+=skipped;job['done']+=len(chunk)
                    if len(job['errors'])<20:job['errors'].extend(errors[:20-len(job['errors'])])
                    job['message']=f'{job["linked"]} linked in place · {job["newTitles"]} new titles · {job["skipped"]} skipped · {len(job["errors"])} reported errors'
                    self.save_job(job)
            job['message']+='; unresolved files remain in the inventory for review.'
        result=self.start_job('inventory-bulk-link',worker)
        self.inventory_bulk_plan=None
        return result
    def list_inspect(self,data):
        try:headers,rows=inspect_document(data.get('content'),data.get('inputType'))
        except ValueError as error:raise Problem(str(error)) from error
        return {'headers':headers,'mapping':suggested_mapping(headers),'total':len(rows),'sample':[{'rowNumber':number,'values':raw} for number,raw in rows[:3]]}
    def list_stage(self,data):
        content=data.get('content');input_type=data.get('inputType');mapping=data.get('mapping')
        mode=data.get('mode');default_kind=data.get('defaultKind');default_format=data.get('defaultFormat','')
        source_name=data.get('sourceName') or 'Pasted list'
        if not isinstance(source_name,str) or not 1<=len(source_name.strip())<=120:raise Problem('Choose a list name up to 120 characters.')
        if mode not in ('titles','physical','source'):raise Problem('Choose titles only, physical copies, or a mapped source-type column.')
        if default_kind not in (*KINDS,'auto'):raise Problem('Choose a default media type or automatic review.')
        if default_format and default_format not in PHYSICAL_FORMATS:raise Problem('Choose a known physical format.')
        try:headers,rows=inspect_document(content,input_type)
        except ValueError as error:raise Problem(str(error)) from error
        if input_type=='lines':mapping={'title':'Title'}
        if not isinstance(mapping,dict) or any(field not in LIST_FIELDS or column not in headers for field,column in mapping.items()) or 'title' not in mapping:
            raise Problem('Map at least the title column to a column in this file.')
        if len(set(mapping.values()))!=len(mapping):raise Problem('Map each column only once.')
        if mode=='source' and 'sourceType' not in mapping:raise Problem('Map the Source Type column for mixed Blank Box exports.')
        if default_kind=='comic' and mode=='physical' and mapping.get('issue') and input_type in ('csv','tsv'):
            # Collector exports may use title-only section headers followed by
            # issue rows. Preserve the series/run heading for matching, but do
            # not turn it into a physical copy.
            section='';prepared=[]
            for row_number,raw in rows:
                issue=str(raw.get(mapping['issue'],'')).strip()
                title=str(raw.get(mapping['title'],'')).strip()
                other=[value for column,value in raw.items() if column!=mapping['title'] and str(value).strip()]
                if not title and not issue:continue  # Footer totals are not collection entries.
                if title and not issue and not other:
                    section=title;continue
                if title and issue and section and re.sub(r'\s*\(\d{4}\)$','',section).casefold()==title.casefold():
                    raw={**raw,mapping['title']:section}
                prepared.append((row_number,raw))
            rows=prepared
            if not rows:raise Problem('No issue rows were found below the section headings.')
        identity=json.dumps({'inputType':input_type,'content':content,'mapping':mapping,'mode':mode,'defaultKind':default_kind,'defaultFormat':default_format,'sourceName':source_name.strip()},sort_keys=True,ensure_ascii=False)
        digest_value=hashlib.sha256(identity.encode('utf-8')).hexdigest()
        with self.db() as db:
            previous=db.execute('SELECT id FROM catalog_import_batches WHERE digest=?',(digest_value,)).fetchone()
            if previous:return self.list_page(previous['id'])
        if not self.operation_lock.acquire(blocking=False):raise Problem('Another file operation is running. Wait for it to finish.',409)
        try:
            batch_id=uuid.uuid4().hex
            seen=set()
            with self.db() as db:
                db.execute('INSERT INTO catalog_import_batches VALUES(?,?,?,?,?,?,?,?)',(batch_id,digest_value,source_name.strip(),input_type,mode,json.dumps(mapping),now(),len(rows)))
                for row_number,raw in rows:
                    proposed=None;error='';status='ready';candidate_ids=[]
                    try:
                        proposed=normalize_row(raw,mapping,default_kind,mode,default_format,KINDS,PHYSICAL_FORMATS)
                        key=(proposed['kind'],work_title_key(proposed['title']),proposed['year'])
                        duplicate=key in seen;seen.add(key)
                        candidate_ids=self.list_candidate_ids(db,proposed['title'],proposed['kind'],proposed['year'])
                        if candidate_ids or duplicate:status='review'
                    except ValueError as cause:
                        error=str(cause);status='error'
                    db.execute('INSERT INTO catalog_import_rows(batch_id,row_number,raw,proposed,status,item_id,error,candidates) VALUES(?,?,?,?,?,?,?,?)',
                               (batch_id,row_number,json.dumps(raw,ensure_ascii=False),json.dumps(proposed,ensure_ascii=False) if proposed else None,status,None,error,json.dumps(candidate_ids)))
            return self.list_page(batch_id)
        finally:self.operation_lock.release()
    def list_classify(self,data):
        batch_id=data.get('batchId');row_number=data.get('rowNumber');kind=data.get('kind');default_format=data.get('format','')
        if not isinstance(batch_id,str) or not re.fullmatch(r'[0-9a-f]{32}',batch_id):raise Problem('Choose a staged list.')
        if not isinstance(row_number,int) or isinstance(row_number,bool) or row_number<1:raise Problem('Choose a list row.')
        if kind not in KINDS:raise Problem('Choose a media type for this row.')
        if default_format and default_format not in PHYSICAL_FORMATS:raise Problem('Choose a known physical format.')
        if not self.operation_lock.acquire(blocking=False):raise Problem('Another file operation is running. Wait for it to finish.',409)
        try:
            with self.db() as db:
                batch=db.execute('SELECT * FROM catalog_import_batches WHERE id=?',(batch_id,)).fetchone()
                row=db.execute('SELECT * FROM catalog_import_rows WHERE batch_id=? AND row_number=?',(batch_id,row_number)).fetchone()
                if not batch or not row:raise Problem('That list row was not found.',404)
                if row['status'] in ('committed','skipped'):raise Problem('This row has already been handled.',409)
                mapping=json.loads(batch['mapping']);raw=json.loads(row['raw']);review_raw={**raw}
                if mapping.get('kind'):review_raw[mapping['kind']]=kind
                if default_format and mapping.get('format'):review_raw[mapping['format']]=default_format
                try:proposed=normalize_row(review_raw,mapping,kind,batch['mode'],default_format,KINDS,PHYSICAL_FORMATS)
                except ValueError as cause:raise Problem(str(cause)) from cause
                candidates=self.list_candidate_ids(db,proposed['title'],proposed['kind'],proposed['year'])
                status='review' if candidates else 'ready'
                db.execute('UPDATE catalog_import_rows SET proposed=?,status=?,error=?,candidates=? WHERE batch_id=? AND row_number=?',
                           (json.dumps(proposed,ensure_ascii=False),status,'',json.dumps(candidates),batch_id,row_number))
            return self.list_page(batch_id)
        finally:self.operation_lock.release()
    def list_page(self,batch_id=None,limit=25,offset=0,status=None):
        if not isinstance(limit,int) or not 1<=limit<=100 or not isinstance(offset,int) or not 0<=offset<=1000000:raise Problem('Invalid list page.')
        if status and status not in ('ready','review','error','committed','skipped'):raise Problem('Invalid list filter.')
        with self.db() as db:
            if batch_id is None:batch=db.execute('SELECT * FROM catalog_import_batches ORDER BY rowid DESC LIMIT 1').fetchone()
            elif isinstance(batch_id,str) and re.fullmatch(r'[0-9a-f]{32}',batch_id):batch=db.execute('SELECT * FROM catalog_import_batches WHERE id=?',(batch_id,)).fetchone()
            else:raise Problem('Invalid list batch.')
            if not batch:return {'batch':None,'rows':[],'total':0,'counts':{}}
            counts={row['status']:row['count'] for row in db.execute('SELECT status,COUNT(*) AS count FROM catalog_import_rows WHERE batch_id=? GROUP BY status',(batch['id'],))}
            where='batch_id=?'+(' AND status=?' if status else '')
            params=(batch['id'],status) if status else (batch['id'],)
            total=db.execute('SELECT COUNT(*) FROM catalog_import_rows WHERE '+where,params).fetchone()[0]
            rows=[]
            for row in db.execute('SELECT * FROM catalog_import_rows WHERE '+where+' ORDER BY row_number LIMIT ? OFFSET ?',(*params,limit,offset)):
                proposed=json.loads(row['proposed']) if row['proposed'] else None
                candidate_ids=json.loads(row['candidates'])
                if row['status']=='review' and proposed:
                    candidate_ids=list(dict.fromkeys([*candidate_ids,*self.list_candidate_ids(db,proposed['title'],proposed['kind'],proposed['year'])]))[:12]
                candidates=[]
                for candidate_id in candidate_ids:
                    item=db.execute('SELECT data FROM items WHERE id=?',(candidate_id,)).fetchone()
                    if item:
                        record=json.loads(item['data']);exact=work_title_key(record['title'])==work_title_key(proposed['title']) if proposed else False
                        prefix=work_title_key(record['title']).startswith(work_title_key(proposed['title'])) if proposed else False
                        candidates.append({'id':record['id'],'title':record['title'],'kind':record['kind'],'year':record.get('year'),'matchReason':'Exact title' if exact else 'Partial title suggestion; review before attaching' if prefix else 'Shared title words; review before attaching'})
                rows.append({'rowNumber':row['row_number'],'raw':json.loads(row['raw']),'proposed':proposed,
                             'status':row['status'],'error':row['error'],'itemId':row['item_id'],'candidates':candidates})
        return {'batch':{'id':batch['id'],'sourceName':batch['source_name'],'inputType':batch['input_type'],'mode':batch['mode'],'createdAt':batch['created_at'],'total':batch['total']},'rows':rows,'total':total,'counts':counts}
    def list_commit(self,data):
        if data.get('confirm') is not True:raise Problem('Review and confirm these catalog changes first.')
        batch_id=data.get('batchId');choice=data.get('choice');row_number=data.get('rowNumber');target_id=data.get('targetId');metadata_id=data.get('metadataEntityId')
        if choice not in ('ready','new','attach','skip'):raise Problem('Choose how this list row should be handled.')
        if not isinstance(batch_id,str) or not re.fullmatch(r'[0-9a-f]{32}',batch_id):raise Problem('Choose a staged list.')
        if choice!='ready' and (not isinstance(row_number,int) or isinstance(row_number,bool) or row_number<1):raise Problem('Choose a list row.')
        if choice=='attach' and (not isinstance(target_id,str) or not re.fullmatch(r'[A-Za-z0-9._:-]{1,120}',target_id)):raise Problem('Choose a matching library item.')
        if metadata_id is not None and (choice not in ('new','attach') or not isinstance(metadata_id,str) or len(metadata_id)>120):raise Problem('Choose one metadata candidate for a reviewed row.')
        if not self.operation_lock.acquire(blocking=False):raise Problem('Another file operation is running. Wait for it to finish.',409)
        try:
            committed=skipped=needs_review=0
            with self.db() as db:
                batch=db.execute('SELECT * FROM catalog_import_batches WHERE id=?',(batch_id,)).fetchone()
                if not batch:raise Problem('This staged list was not found.',404)
                selected=(db.execute("SELECT * FROM catalog_import_rows WHERE batch_id=? AND status='ready' ORDER BY row_number LIMIT 200",(batch_id,)).fetchall()
                          if choice=='ready' else db.execute('SELECT * FROM catalog_import_rows WHERE batch_id=? AND row_number=?',(batch_id,row_number)).fetchall())
                if not selected and choice!='ready':raise Problem('That list row was not found.',404)
                for row in selected:
                    if row['status'] in ('committed','skipped'):continue
                    if row['status']=='error':raise Problem('Correct the column mapping and stage the list again before importing this row.',409)
                    if choice=='ready' and row['status']!='ready':continue
                    if choice=='skip':
                        db.execute("UPDATE catalog_import_rows SET status='skipped' WHERE batch_id=? AND row_number=?",(batch_id,row['row_number']));skipped+=1;continue
                    proposed=json.loads(row['proposed']);key=work_title_key(proposed['title'])
                    current=self.list_candidate_ids(db,proposed['title'],proposed['kind'],proposed['year'])
                    if choice=='ready' and current:
                        db.execute("UPDATE catalog_import_rows SET status='review',candidates=? WHERE batch_id=? AND row_number=?",(json.dumps(current),batch_id,row['row_number']));needs_review+=1;continue
                    if choice=='attach':
                        if target_id not in current:raise Problem('That item is no longer a matching title. Review the row again.',409)
                        record=db.execute('SELECT data FROM items WHERE id=?',(target_id,)).fetchone()
                        if not record:raise Problem('The matching item was removed. Review again.',409)
                        item=json.loads(record['data']);ensure_item_model(item)
                    else:
                        item={'id':uuid.uuid4().hex,'title':proposed['title'],'kind':proposed['kind'],'sources':[],
                              'addedAt':now(),'backup':'none','metadataOverrides':[],'importedTitleUnconfirmed':True}
                        if proposed['year']:
                            item['year']=proposed['year']
                        if proposed.get('creator') and proposed['kind']=='music':item['artist']=proposed['creator']
                        if proposed.get('edition'):item['versions']=[{'id':uuid.uuid4().hex,'label':proposed['edition']}]
                        ensure_item_model(item)
                    if proposed['physical']:
                        for index in range(proposed['quantity']):
                            source={'id':ownership_id('list-physical',batch_id,row['row_number'],index),'versionId':item['versions'][0]['id'],
                                    'type':'physical','label':proposed['format'],'addedAt':now(),'listBatchId':batch_id,'listRowNumber':row['row_number']}
                            for field in ('edition','barcode','location','platform','creator','publisher','condition','volume','issue','region','catalogNumber','certificate','signed','grade','listedPrice'):
                                if proposed.get(field):source[field]=proposed[field]
                            item['sources'].append(source)
                    else:
                        item['sources'].append({'id':ownership_id('list-catalog',batch_id,row['row_number']),'versionId':item['versions'][0]['id'],
                                                'type':'catalog','label':'Imported list: '+batch['source_name'],'path':proposed.get('sourcePath') or f"Row {row['row_number']}",
                                                'addedAt':now(),'listBatchId':batch_id,'listRowNumber':row['row_number']})
                    db.execute('INSERT INTO items(id,data) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',(item['id'],json.dumps(item,ensure_ascii=False)))
                    if sync_physical_ownership(db,item):db.execute('UPDATE items SET data=? WHERE id=?',(json.dumps(item,ensure_ascii=False),item['id']))
                    sync_item_search(db,item)
                    backfill_item(db,item)
                    sync_owned_releases(db,item)
                    if metadata_id:
                        try:
                            local_id=self.metadata_packs.materialize(db,metadata_id) if metadata_id.startswith('pack:') else metadata_id
                            confirm_entity(db,'item',item['id'],local_id)
                            apply_reference_details(db,item,local_id)
                        except (ValueError,OSError) as error:raise Problem(str(error),409) from error
                    db.execute("UPDATE catalog_import_rows SET status='committed',item_id=? WHERE batch_id=? AND row_number=?",(item['id'],batch_id,row['row_number']))
                    committed+=1
            return {'ok':True,'committed':committed,'skipped':skipped,'needsReview':needs_review,**self.list_page(batch_id)}
        finally:self.operation_lock.release()
    def export_catalog_csv(self):
        columns=('Title','Media Type','Year','Source Type','Format','Edition','Barcode','Location','Platform',
                 'Creator','Publisher','Condition','Quantity','Volume','Issue','Region','Catalog Number','COA','Signed','CGC','Price',
                 'Original Path','Item ID','Source ID')
        output=io.StringIO(newline='');writer=csv.DictWriter(output,fieldnames=columns);writer.writeheader()
        for item in self.items():
            for source in item.get('sources',[]) or [{}]:
                row={'Title':item.get('title'),'Media Type':item.get('kind'),'Year':item.get('year'),'Source Type':source.get('type'),
                     'Format':source.get('label') if source.get('type')=='physical' else '',
                     'Edition':source.get('edition') or next((version.get('label') for version in item.get('versions',[]) if version.get('id')==source.get('versionId')),''),
                     'Barcode':source.get('barcode'),'Location':source.get('location'),'Platform':source.get('platform'),
                     'Creator':source.get('creator') or item.get('artist'),'Publisher':source.get('publisher'),
                     'Condition':source.get('condition'),'Quantity':1,'Volume':source.get('volume'),'Issue':source.get('issue'),
                     'Region':source.get('region'),'Catalog Number':source.get('catalogNumber'),
                     'COA':source.get('certificate'),'Signed':source.get('signed'),'CGC':source.get('grade'),'Price':source.get('listedPrice'),
                     'Original Path':source.get('path'),'Item ID':item.get('id'),'Source ID':source.get('id')}
                writer.writerow({key:spreadsheet_safe(value) for key,value in row.items()})
        return output.getvalue().encode('utf-8-sig')
    def export_catalog_snapshot(self,destination):
        """Create a portable, media-free, full-fidelity catalog snapshot."""
        destination=reject_links(destination)
        if destination.exists():raise ValueError('Choose a new export file.')
        created=False
        try:
            descriptor=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            os.close(descriptor);created=True
            with self.db() as source,sqlite3.connect(destination) as exported:source.backup(exported)
            with sqlite3.connect(destination) as exported:
                for table in ('connections','auth_sessions','users'):
                    exported.execute('DELETE FROM '+table)
                exported.commit()
                exported.execute('VACUUM')
                result=exported.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()
                if result and result[0]:raise ValueError('Catalog export checkpoint failed.')
                if exported.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Catalog export integrity check failed.')
                if exported.execute('PRAGMA journal_mode=DELETE').fetchone()[0].lower()!='delete':
                    raise ValueError('Catalog export could not be made standalone.')
            os.chmod(destination,0o600)
            return destination.stat().st_size
        except Exception:
            if created:destination.unlink(missing_ok=True)
            raise
    def import_scan(self,scan_id,selected_ids,policy='keep',decisions=None):
        with self.state_lock:scan=self.scans.get(scan_id)
        if not scan:raise Problem('This scan has expired. Scan the source again.')
        if not isinstance(selected_ids,list) or not selected_ids or len(selected_ids)>100000:raise Problem('Select at least one file, up to 100,000.')
        if policy not in ('keep','incoming','new-version','separate','review'):raise Problem('Choose how matching records should be handled.')
        if decisions is None:decisions={}
        if not isinstance(decisions,dict):raise Problem('Invalid import review choices.')
        chosen=set(selected_ids);records=[f for f in scan['files'] if f['id'] in chosen]
        if len(records)!=len(chosen):raise Problem('Some selected files are not part of this scan.')
        root=self.source_roots[scan['sourceId']]
        def worker(job):
            job.update(total=len(records),copied=0,duplicates=0,consolidated=0,newVersions=0,reviewCount=0)
            known={}
            for known_item in self.items():
                ensure_item_model(known_item)
                for known_source in known_item.get('sources',[]):
                    known_hash=known_source.get('sha256') or known_item.get('sha256')
                    if known_source.get('type')=='local' and known_hash:known[known_hash]=(known_item,known_source)
            for index,record in enumerate(records):
                try:
                    sha=record['sha256'];src=safe_file(root,record['name'])
                    if tuple(record['stat'])!=fingerprint(src.stat()):raise ValueError('Source changed since scan. Scan again.')
                    if sha in known:
                        known_item,known_source=known[sha];existing=self.media/(known_source.get('storedPath') or known_item['storedPath'])
                        if not existing.is_file() or digest(existing)!=sha:raise ValueError('Existing imported copy is missing or changed. Restore it before retrying.')
                        # Source revalidation avoids trusting an old scan for a duplicate.
                        if digest(src)!=sha:raise ValueError('Source changed since scan. Scan again.')
                        reference={'id':uuid.uuid4().hex,'versionId':known_source.get('versionId'),'type':'catalog','label':root.name or 'Source folder','sourceId':scan['sourceId'],'path':record['name'],'addedAt':now()}
                        if not any(source.get('type')=='catalog' and source.get('label')==reference['label'] and source.get('path')==reference['path'] for source in known_item.get('sources',[])):
                            known_item['sources'].append(reference);self.put_item(known_item)
                        job['duplicates']+=1
                    else:
                        if shutil.disk_usage(self.data).free<record['bytes']+64*1024*1024:raise ValueError('Not enough free space for this file plus the safety margin.')
                        safe_name=re.sub(r'[^\w .()\[\]-]','_',src.name)[:180]
                        relative=Path(record['kind'])/sha/safe_name;target=self.media/relative
                        checked_copy(src,target,sha)
                        id=uuid.uuid4().hex;mime=mimetypes.guess_type(src.name)[0] or 'application/octet-stream'
                        root_stat=root.stat();root_identity=f'{root_stat.st_dev}:{root_stat.st_ino}'
                        added_at=now();version={'id':uuid.uuid4().hex,'label':edition_label(clean_title(src.name))};item={'id':id,'title':record.get('title') or clean_title(src.name),'kind':record['kind'],'versions':[version],'bytes':record['bytes'],'sha256':sha,'mime':mime,'storedPath':relative.as_posix(),'sources':[{'type':'local','label':'Blank Box','versionId':version['id'],'sourceId':scan['sourceId'],'rootIdentity':root_identity,'path':record['name'],'storedPath':relative.as_posix(),'sha256':sha,'bytes':record['bytes'],'mime':mime,'addedAt':added_at}],'addedAt':added_at,'backup':'none'}
                        if record.get('year'):item['year']=record['year']
                        if record['kind']=='photo' and mime in ('image/jpeg','image/png','image/webp','image/gif','image/avif'):item['poster']='/media/'+id
                        self.put_item(item);job['copied']+=1
                        candidates=self.match_candidates(item,exclude=item['id'])
                        choice=decisions.get(record['id'],{}) if policy=='review' else {}
                        selected_policy=choice.get('policy',policy)
                        target_id=choice.get('targetId') or (candidates[0]['id'] if candidates else None)
                        if candidates and target_id and selected_policy in ('keep','incoming','new-version'):
                            metadata_policy='incoming' if selected_policy=='incoming' else 'keep'
                            edition_policy='new' if selected_policy=='new-version' else 'same'
                            item=self.merge_items(target_id,item,metadata_policy,edition_policy);job['consolidated']+=1
                            if edition_policy=='new':job['newVersions']+=1
                        elif candidates and policy=='review' and not choice:
                            self.queue_review(item,candidates,root.name or 'Folder import');job['reviewCount']+=1
                        local_source=next(source for source in item['sources'] if source.get('sha256')==sha)
                        known[sha]=(item,local_source)
                    with self.db() as db:
                        db.execute("UPDATE auto_copy_candidates SET status='handled' WHERE source_id=? AND relative_path=? AND fingerprint=?",
                                   (scan['sourceId'],record['name'],json.dumps(record['stat'])))
                except (OSError,ValueError,KeyError) as e:job['errors'].append(f"{record['name']}: {e}")
                job['done']=index+1;job['message']=f"{job['copied']} copied · {job['consolidated']} consolidated · {job['newVersions']} new editions · {job['duplicates']} exact copies linked · {job['reviewCount']} awaiting review · {len(job['errors'])} errors";self.save_job(job)
        return self.start_job('import',worker)
    def auto_import(self):
        """Discover stable personal files; never copy them without owner approval."""
        if not self.source_roots:raise Problem('Configure at least one source before enabling automatic discovery.')
        def worker(job):
            found=waiting=seen=0
            for source_id,root in self.source_roots.items():
                if not root.is_dir():
                    job['errors'].append(f'{root.name or root}: source is unavailable');continue
                with self.db() as db:
                    existing={row['relative_path']:(row['fingerprint'],row['status']) for row in db.execute('SELECT relative_path,fingerprint,status FROM auto_copy_candidates WHERE source_id=?',(source_id,))}
                updates=[]
                def flush():
                    if not updates:return
                    with self.db() as db:
                        db.executemany('INSERT INTO auto_copy_candidates VALUES(?,?,?,?,?,?,?) ON CONFLICT(source_id,relative_path) DO UPDATE SET fingerprint=excluded.fingerprint,bytes=excluded.bytes,kind=excluded.kind,status=excluded.status,discovered_at=excluded.discovered_at',updates)
                    updates.clear()
                def walk_error(error):job['errors'].append(str(error))
                for folder,dirs,files in os.walk(root,followlinks=False,onerror=walk_error):
                    dirs[:]=[name for name in dirs if not name.startswith('.') and not (Path(folder)/name).is_symlink()]
                    for name in sorted(files):
                        path=Path(folder)/name
                        if name.startswith('.') or path.is_symlink() or not path.is_file():continue
                        if path.suffix.casefold() in ('.nfo','.srt','.ass','.ssa','.sub','.idx','.sfv','.md5','.sha256'):continue
                        rel=path.relative_to(root).as_posix();kind=kind_for(rel)
                        if kind not in ('photo','home-video','file'):continue
                        try:stat=path.stat()
                        except OSError as error:job['errors'].append(f'{rel}: {error}');continue
                        observed=json.dumps(fingerprint(stat))
                        prior=existing.pop(rel,None)
                        status=('pending' if prior and prior[0]==observed and prior[1]=='waiting'
                                else prior[1] if prior and prior[0]==observed and prior[1] in ('pending','handled') else 'waiting')
                        updates.append((source_id,rel,observed,stat.st_size,kind,status,now()))
                        if len(updates)>=500:flush()
                        if status=='pending':found+=1
                        elif status=='waiting':waiting+=1
                        seen+=1
                        if seen>100000:raise ValueError('Automatic discovery exceeds the V1 limit of 100,000 personal files.')
                flush()
                missing=[(source_id,rel) for rel,(_,status) in existing.items() if status not in ('missing','handled')]
                if missing:
                    with self.db() as db:db.executemany("UPDATE auto_copy_candidates SET status='missing' WHERE source_id=? AND relative_path=?",missing)
            job.update(total=found+waiting,done=found+waiting,copied=0,waiting=waiting,message=f'{found} ready for copy review · {waiting} waiting for a stable second check. No files were copied.')
        return self.start_job('auto-discovery',worker)
    def auto_copy_page(self,source_id):
        if source_id not in self.source_roots:raise Problem('Choose a connected source.')
        with self.db() as db:
            summary=db.execute("SELECT COUNT(*) AS count,COALESCE(SUM(bytes),0) AS bytes FROM auto_copy_candidates WHERE source_id=? AND status='pending'",(source_id,)).fetchone()
            rows=[{'path':row['relative_path'],'bytes':row['bytes'],'kind':row['kind']} for row in db.execute("SELECT relative_path,bytes,kind FROM auto_copy_candidates WHERE source_id=? AND status='pending' ORDER BY relative_path LIMIT 12",(source_id,))]
        return {'count':summary['count'],'bytes':summary['bytes'],'files':rows}
    def auto_copy_scan(self,source_id):
        if source_id not in self.source_roots:raise Problem('Choose a connected source.')
        with self.db() as db:
            paths={row['relative_path']:tuple(json.loads(row['fingerprint'])) for row in db.execute("SELECT relative_path,fingerprint FROM auto_copy_candidates WHERE source_id=? AND status='pending' ORDER BY relative_path LIMIT 100",(source_id,))}
        if not paths:raise Problem('No stable personal files are waiting for review.')
        return self.scan(source_id,paths)
    def backup_indexed(self,data):
        if not self.backup_root:raise Problem('Configure a backup destination before backing up selected files.')
        if data.get('confirmPersonalFiles') is not True:raise Problem('Confirm the selected file count and size before backup.')
        batch_id=data.get('batchId');paths=data.get('paths')
        if not isinstance(paths,list) or not 1<=len(paths)<=100 or len(set(map(str,paths)))!=len(paths):raise Problem('Select 1 to 100 distinct indexed personal files.')
        if any(not isinstance(path,str) for path in paths):raise Problem('Select indexed file paths.')
        records=[];total=0;batch=None
        for path in paths:
            found,record=self.inventory_record(batch_id,path)
            if batch is None:batch=found
            if record['kind'] not in ('photo','home-video','file'):raise Problem('Only selected personal files can be backed up through this action.')
            records.append((path,int(record['bytes']),int(record['mtime_ns'])))
            total+=int(record['bytes'])
        if data.get('confirmedCount')!=len(records) or data.get('confirmedBytes')!=total:raise Problem('The selected file count or size changed. Review the selection again.',409)
        return self._backup_indexed_records(batch,records,'backup-indexed')
    def backup_indexed_all_preview(self,source_id):
        if not self.backup_root:raise Problem('Configure a backup destination before backing up personal files.')
        if source_id not in self.source_roots:raise Problem('Choose a connected source.')
        with self.db() as db:
            batch=db.execute('SELECT * FROM inventory_batches WHERE source_id=? ORDER BY started_at DESC,rowid DESC LIMIT 1',(source_id,)).fetchone()
            if not batch or batch['status'] not in ('complete','partial'):raise Problem('Finish indexing this source before backing up all personal files.')
            result=db.execute("SELECT COUNT(*) AS count,COALESCE(SUM(bytes),0) AS bytes FROM inventory_files WHERE batch_id=? AND kind IN ('photo','home-video','file')",(batch['id'],)).fetchone()
        return {'batchId':batch['id'],'sourceId':source_id,'count':result['count'],'bytes':result['bytes'],'partial':batch['status']=='partial'}
    def backup_indexed_all(self,data):
        preview=self.backup_indexed_all_preview(data.get('sourceId'))
        if data.get('confirmPersonalFiles') is not True or data.get('batchId')!=preview['batchId'] or data.get('confirmedCount')!=preview['count'] or data.get('confirmedBytes')!=preview['bytes']:
            raise Problem('Indexed personal-file counts changed. Review the backup total again.',409)
        if not preview['count']:raise Problem('This source has no indexed photos, home videos, or personal files.')
        with self.db() as db:
            batch=db.execute('SELECT * FROM inventory_batches WHERE id=?',(preview['batchId'],)).fetchone()
            records=[(row['relative_path'],int(row['bytes']),int(row['mtime_ns'])) for row in db.execute("SELECT relative_path,bytes,mtime_ns FROM inventory_files WHERE batch_id=? AND kind IN ('photo','home-video','file') ORDER BY relative_path",(preview['batchId'],))]
        return self._backup_indexed_records(batch,records,'backup-indexed-all')
    def _backup_indexed_records(self,batch,records,job_type):
        root=self.source_roots[batch['source_id']]
        def check_roots():
            if not root.is_dir() or f'{root.stat().st_dev}:{root.stat().st_ino}'!=batch['root_identity']:raise ValueError('The source drive changed. Index it again.')
            if not self.backup_root.is_dir() or (self.backup_root.stat().st_dev,self.backup_root.stat().st_ino)!=self.backup_identity:raise ValueError('The backup drive is missing or changed. Reconnect it and restart Blank Box.')
        check_roots()
        def worker(job):
            job['total']=len(records);job['done']=0
            base=safe_destination(self.backup_root,Path('blank-box-backup')/'indexed-personal'/batch['source_id'])
            manifest={'version':1,'createdAt':now(),'batchId':batch['id'],'sourceId':batch['source_id'],'files':[]}
            for index,(path,size,mtime) in enumerate(records):
                check_roots()
                source=safe_file(root,path);details=source.stat()
                if details.st_size!=size or details.st_mtime_ns!=mtime:raise ValueError(f'Indexed file changed: {path}. Index it again.')
                target=safe_destination(base,path)
                # New copies are hashed while writing and verified before the
                # exclusive commit. Existing copies need a source hash to prove
                # that the saved bytes still match without replacing them.
                expected=None
                if target.exists():
                    before=fingerprint(source.stat())
                    expected=digest(source)
                    if fingerprint(source.stat())!=before:raise ValueError(f'Indexed file changed during verification: {path}. Index it again.')
                expected=checked_copy(source,target,expected)
                manifest['files'].append({'path':path,'bytes':size,'sha256':expected})
                job['done']=index+1;job['message']=f'Verified {index+1} of {len(records)} personal files';self.save_job(job)
            check_roots()
            manifests=safe_destination(self.backup_root,Path('blank-box-backup')/'indexed-personal-manifests');manifests.mkdir(parents=True,exist_ok=True)
            manifest_path=safe_destination(manifests,uuid.uuid4().hex+'.json')
            with manifest_path.open('x') as output:json.dump(manifest,output,indent=2)
            job['message']=f'{len(records)} personal files verified on the backup drive. Catalog backup is a separate action.'
        return self.start_job(job_type,worker)
    def backup(self):
        if not self.backup_root:raise Problem('Restart the box with a backup destination configured.')
        self._check_backup_destination()
        return self.start_job('backup',self._backup_worker)
    def _check_backup_destination(self):
        if not self.backup_root or not self.backup_root.is_dir() or (self.backup_root.stat().st_dev,self.backup_root.stat().st_ino)!=self.backup_identity:
            raise ValueError('Backup drive is missing or changed. Reconnect it and restart the box.')
    def _backup_worker(self,job):
        self._check_backup_destination();base=safe_destination(self.backup_root,'blank-box-backup');base.mkdir(exist_ok=True)
        items=self.items();entries=[]
        for item in items:
            ensure_item_model(item)
            for source in item.get('sources',[]):
                if source.get('type')=='local' and (source.get('storedPath') or item.get('storedPath')):entries.append((item,source))
        job['total']=len(entries)+1
        manifest={'version':VERSION,'createdAt':now(),'files':[]}
        verified_ids=set()
        for index,(item,media_source) in enumerate(entries):
            self._check_backup_destination();relative=media_source.get('storedPath') or item['storedPath'];expected=media_source.get('sha256') or item['sha256'];source=safe_file(self.media,relative);dest=safe_destination(base,Path('media')/relative)
            if digest(source)!=expected:raise ValueError(f"Primary file changed or missing: {item['title']}")
            if dest.exists():
                if digest(dest)!=expected:raise ValueError(f"Backup copy changed: {item['title']}. Existing backup was not overwritten.")
            else:checked_copy(source,dest,expected)
            verified_ids.add(item['id']);manifest['files'].append({'itemId':item['id'],'sourceId':media_source.get('id'),'path':'media/'+relative,'sha256':expected,'bytes':media_source.get('bytes') or item.get('bytes',source.stat().st_size)})
            job['done']=index+1;job['message']=f'Verified {index+1} of {len(entries)} media files';self.save_job(job)
        verified_at=now()
        for item in items:
            if item['id'] in verified_ids:item['backup']='verified';item['backupVerifiedAt']=verified_at;self.put_item(item)
        snap=safe_destination(base,Path('snapshots')/uuid.uuid4().hex);snap.mkdir(parents=True)
        # SQLite's backup API captures a consistent live database, including WAL.
        with self.db() as srcdb,sqlite3.connect(snap/'catalog.sqlite3') as destdb:srcdb.backup(destdb)
        # Connections and password hashes are local secrets. A restored portable
        # catalog is claimed again with its new access key.
        with sqlite3.connect(snap/'catalog.sqlite3') as clean:
            if clean.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Catalog backup integrity check failed.')
            clean.execute('DELETE FROM connections');clean.execute('DELETE FROM auth_sessions');clean.execute('DELETE FROM users');clean.commit();clean.execute('VACUUM')
        # The portable restore copies the main database file, not a SQLite WAL.
        # Checkpoint after redaction so neither passwords nor provider keys can
        # remain only in the WAL and then reappear in a restored box.
        with sqlite3.connect(snap/'catalog.sqlite3') as checkpoint:
            result=checkpoint.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()
            if result and result[0]:raise ValueError('Catalog backup checkpoint could not complete.')
            if checkpoint.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Catalog backup integrity check failed after redaction.')
        manifest['catalogSha256']=digest(snap/'catalog.sqlite3')
        (snap/'manifest.json').write_text(json.dumps(manifest,indent=2))
        self._check_backup_destination()
        with self.db() as db:db.execute('INSERT INTO backup_state VALUES(1,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',(json.dumps({'lastVerified':now(),'verifiedItems':len(entries),'snapshot':str(snap)}),))
        job['done']=job['total'];job['message']=f'{len(entries)} media files and the catalog verified. Snapshot: {snap.name}'
        return snap
    def full_recovery_point(self):
        self._check_backup_destination()
        def worker(job):
            from maintenance import snapshot_assets
            snap=self._backup_worker(job)
            self._check_backup_destination()
            completed=job['done']
            job['message']='Copying and verifying installed offline packs';self.save_job(job)
            def progress(done,total):
                job['total']=completed+total+1;job['done']=completed+done
                job['message']=f'Verified {done} of {total} pack assets';self.save_job(job)
            assets=snapshot_assets(self.data,snap/'catalog.sqlite3',progress)
            inventory=assets/'inventory.json'
            (snap/'full-recovery.json').write_text(json.dumps({'version':1,'createdAt':now(),'catalogSha256':digest(snap/'catalog.sqlite3'),'assetInventorySha256':digest(inventory),'assets':assets.name},indent=2))
            job['done']=job['total']
            job['message']=f'Complete recovery point verified: {snap.name}. Linked source files remain on their drives and are not included.'
        return self.start_job('full-recovery',worker)
    def full_recovery_points(self):
        if not self.backup_root:return []
        self._check_backup_destination()
        root=safe_destination(self.backup_root,Path('blank-box-backup')/'snapshots')
        if not root.is_dir():return []
        points=[]
        for path in sorted(root.iterdir(),reverse=True):
            if not re.fullmatch(r'[0-9a-f]{32}',path.name) or path.is_symlink() or not path.is_dir() or not (path/'full-recovery.json').is_file():continue
            try:
                record=json.loads((path/'full-recovery.json').read_text())
                points.append({'id':path.name,'createdAt':record['createdAt']})
            except (OSError,ValueError,KeyError):continue
        return sorted(points,key=lambda point:point['createdAt'],reverse=True)[:20]
    def prepare_full_restore(self,identifier):
        if not isinstance(identifier,str) or not re.fullmatch(r'[0-9a-f]{32}',identifier):raise Problem('Choose a complete recovery point.')
        self._check_backup_destination()
        source=safe_destination(self.backup_root,Path('blank-box-backup')/'snapshots'/identifier)
        if not source.is_dir() or not (source/'full-recovery.json').is_file():raise Problem('Complete recovery point was not found.')
        target=safe_destination(self.data,Path('restore-review')/identifier)
        if target.exists():raise Problem('A review copy already exists at this location. Choose another recovery point or review that copy first.',409)
        def worker(job):
            from restore import restore_full
            self._check_backup_destination()
            job['message']='Checking recovery point and preparing an empty review copy';self.save_job(job)
            def progress(stage,done,total):
                job['total']=total;job['done']=done
                job['message']=f'{stage}: {done} of {total} files';self.save_job(job)
            count=restore_full(source,target,progress)
            job['done']=job['total']=1
            job['message']=f'Restored {count} managed files, catalog and installed packs to {target}. The current library is unchanged.'
        return self.start_job('prepare-full-restore',worker)
    def connection(self,provider):
        with self.db() as db:row=db.execute('SELECT data FROM connections WHERE id=?',(provider,)).fetchone()
        if not row:return None
        try:value=json.loads(row[0])
        except (TypeError,json.JSONDecodeError):return None
        return value if isinstance(value,dict) else None
    def jellyfin_item(self,entry,base):
        jid=str(entry.get('Id',''))
        if not re.fullmatch(r'[a-zA-Z0-9-]{1,100}',jid):return None
        source={'type':'jellyfin','label':'Jellyfin','providerItemId':jid,'url':base+'/web/#/details?id='+urllib.parse.quote(jid)}
        source_added=provider_timestamp(entry.get('DateCreated'))
        if source_added:source['addedAt']=source_added
        item={'id':'jellyfin-'+jid,'title':str(entry.get('Name') or 'Untitled'),'kind':{'Series':'tv','MusicAlbum':'music'}.get(entry.get('Type'),'movie'),'year':entry.get('ProductionYear'),'description':str(entry.get('Overview',''))[:5000],'sources':[source],'addedAt':now(),'metadataProvider':'Jellyfin'}
        release_date=provider_release_date(entry.get('PremiereDate'))
        if release_date:item['releaseDate']=release_date
        genres=entry.get('Genres') or []
        if isinstance(genres,list):
            genre=', '.join(value.strip() for value in genres[:30] if isinstance(value,str) and value.strip())[:500]
            if genre:item['genre']=genre
        runtime=entry.get('RunTimeTicks')
        if type(runtime) in (int,float) and math.isfinite(runtime) and runtime>0:item['duration']=runtime/10000000
        if entry.get('ImageTags',{}).get('Primary'):item['poster']='/api/jellyfin-art/'+jid
        artist=entry.get('AlbumArtist') or next(iter(entry.get('Artists') or []),None)
        if item['kind']=='music' and isinstance(artist,str) and artist.strip():item['artist']=artist.strip()[:250]
        details=provider_details(entry,'jellyfin')
        if details:item['catalogDetails']=details
        identifiers=provider_identifiers(entry,'jellyfin',item['kind'])
        if identifiers:source['metadataIdentifiers']=identifiers
        source['metadataSnapshot']=metadata_snapshot(item)
        ensure_item_model(item);item['metadataPreference']=source['id'];return item
    def sync_saved_jellyfin(self,policy='review'):
        connection=self.connection('jellyfin')
        if not connection:raise Problem('Connect Jellyfin once in Settings before refreshing its catalog.')
        return self.sync_jellyfin(str(connection.get('url','')),connection.get('key'),policy)
    def refresh_item_sources(self,item_id):
        if not self.operation_lock.acquire(blocking=False):raise Problem('Another file operation is running. Wait for it to finish.',409)
        try:
            item=self.get_item(item_id);ensure_item_model(item)
            provider_sources=[source for source in item.get('sources',[]) if source.get('type') in ('jellyfin','plex')]
            if not provider_sources:raise Problem('This item has no connected catalog source to refresh.')
            refreshed=[];labels=[]
            for source in provider_sources:
                provider=source.get('type');connection=self.connection(provider)
                if not connection:raise Problem(f"Reconnect {provider.title()} in Settings before refreshing this item.")
                base=str(connection.get('url','')).rstrip('/');key=connection.get('key')
                provider_id=str(source.get('providerItemId',''))
                marker=provider+':'+provider_id
                if marker in refreshed:continue
                if provider=='jellyfin':
                    if not re.fullmatch(r'[a-zA-Z0-9-]{1,100}',provider_id):raise Problem('This Jellyfin source is missing its item identifier. Sync the full catalog once to repair it.')
                    params=urllib.parse.urlencode({'Ids':provider_id,'Fields':'Overview,ProductionYear,PremiereDate,DateCreated,People,Studios,Genres,ProviderIds','Limit':1})
                    data=self.jelly_request(base+'/Items?'+params,key);entry=next((entry for entry in data.get('Items',[]) if str(entry.get('Id',''))==provider_id),None)
                    incoming=self.jellyfin_item(entry,base) if entry else None;label='Jellyfin'
                else:
                    if not re.fullmatch(r'\d{1,20}',provider_id):raise Problem('This Plex source is missing its item identifier. Sync the full catalog once to repair it.')
                    data=self.plex_request(base+'/library/metadata/'+provider_id,key);entry=next(iter(data.get('MediaContainer',{}).get('Metadata',[])),None)
                    incoming=self.plex_item(entry,base) if entry else None;label='Plex'
                if not incoming:raise Problem(f'{label} no longer returned this item. The existing Blank Box record was left unchanged.',404)
                item=self.merge_items(item['id'],incoming,'incoming','same',allow_kind_change=True);refreshed.append(marker)
                if label not in labels:labels.append(label)
            return {'ok':True,'item':self.public_item(item),'refreshedSources':labels}
        finally:self.operation_lock.release()
    def refresh_tv_catalog(self,item_id,source_id=None):
        item=self.get_item(item_id);ensure_item_model(item)
        if item.get('kind')!='tv':raise Problem('Choose a TV series to load seasons and episodes.')
        sources=[source for source in item.get('sources',[]) if source.get('type') in ('jellyfin','plex') and source.get('providerItemId')]
        if source_id:
            source=next((row for row in sources if row.get('id')==source_id),None)
            if not source:raise Problem('That TV source is no longer attached.',404)
        else:
            source=next((row for row in sources if row.get('id')==item.get('metadataPreference')),None) or next(iter(sources),None)
        if not source:raise Problem('Connect a Jellyfin or Plex series to load episodes.')
        provider=source['type'];provider_id=str(source['providerItemId']);connection=self.connection(provider)
        if not connection:raise Problem(f'Reconnect {provider.title()} in Settings before loading episodes.')
        base=str(connection.get('url','')).rstrip('/');key=connection.get('key')
        if provider=='jellyfin':
            if not re.fullmatch(r'[a-zA-Z0-9-]{1,100}',provider_id):raise Problem('The Jellyfin series ID is invalid.')
            season_data=self.jelly_request(base+'/Shows/'+provider_id+'/Seasons',key)
            seasons=season_data.get('Items',[])
            episodes=[];offset=0
            while True:
                query=urllib.parse.urlencode({'StartIndex':offset,'Limit':500,'Fields':'Overview,PremiereDate'})
                page=self.jelly_request(base+'/Shows/'+provider_id+'/Episodes?'+query,key)
                rows=page.get('Items',[]);episodes.extend(rows);offset+=len(rows)
                if not rows or offset>=page.get('TotalRecordCount',offset):break
                if offset>=5000:raise Problem('This series exceeds the supported 5,000-episode view.')
            catalog=jellyfin_tree(seasons,episodes)
        else:
            if not re.fullmatch(r'\d{1,20}',provider_id):raise Problem('The Plex series ID is invalid.')
            def pages(path):
                rows=[];offset=0
                while True:
                    query=urllib.parse.urlencode({'X-Plex-Container-Start':offset,'X-Plex-Container-Size':500})
                    page=self.plex_request(base+path+'?'+query,key).get('MediaContainer',{})
                    chunk=page.get('Metadata',[]);rows.extend(chunk);offset+=len(chunk)
                    if not chunk or offset>=page.get('totalSize',offset):break
                    if offset>=5000:raise Problem('This series exceeds the supported 5,000-episode view.')
                return rows
            seasons=pages('/library/metadata/'+provider_id+'/children')
            episodes=pages('/library/metadata/'+provider_id+'/grandchildren')
            catalog=plex_tree(seasons,episodes)
        if not isinstance(catalog.get('seasons'),list):raise Problem('The TV catalog response was invalid.')
        catalog['updatedAt']=now()
        with self.db() as db:
            current=db.execute('SELECT data FROM items WHERE id=?',(item['id'],)).fetchone()
            if not current:raise Problem('That TV item is no longer in the library.',404)
            item=json.loads(current[0])
            attached=next((row for row in item.get('sources',[]) if row.get('id')==source['id'] and row.get('providerItemId')==provider_id),None)
            if not attached:raise Problem('That TV source changed while episodes were loading.',409)
            attached['tvCatalog']=catalog
            db.execute('UPDATE items SET data=? WHERE id=?',(json.dumps(item),item['id']))
        return {'ok':True,'tvCatalog':catalog,'sourceId':source['id']}
    def sync_jellyfin(self,url,key,policy='review'):
        parsed=urllib.parse.urlparse(url)
        if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:raise Problem('Use a valid Jellyfin address without credentials, query, or fragment.')
        if not isinstance(key,str) or not (8<=len(key)<=200):raise Problem('Enter a valid Jellyfin API key.')
        if policy not in ('review','keep','incoming','new-version','separate'):raise Problem('Choose how matching Jellyfin records should be handled.')
        base=url.rstrip('/')
        def worker(job):
            settings=self.get_settings();settings['jellyfinUrl']=base
            with self.db() as db:hidden_ids={row[0] for row in db.execute('SELECT id FROM hidden_items')}
            collected=[];offset=0
            while True:
                params=urllib.parse.urlencode({'Recursive':'true','IncludeItemTypes':'Movie,Series,MusicAlbum','Fields':'Overview,ProductionYear,PremiereDate,DateCreated,People,Studios,Genres,ProviderIds,ChildCount','StartIndex':offset,'Limit':200})
                data=self.jelly_request(base+'/Items?'+params,key)
                entries=data.get('Items',[])
                for entry in entries:
                    item=self.jellyfin_item(entry,base)
                    if not item or item['id'] in hidden_ids:continue
                    collected.append(item)
                offset+=len(entries)
                job.update(total=int(data.get('TotalRecordCount',offset)),done=offset,message=f'Read {offset} Jellyfin items');self.save_job(job)
                if not entries or offset>=data.get('TotalRecordCount',offset):break
                if offset>50000:raise ValueError('This Jellyfin library exceeds the V1 sync limit.')
            with self.db() as db:
                db.execute('INSERT INTO connections VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',('jellyfin',json.dumps({'url':base,'key':key})))
                db.execute('UPDATE settings SET data=? WHERE id=1',(json.dumps(settings),))
            job.update(consolidated=0,newVersions=0,reviewCount=0,added=0,refreshed=0)
            owners,titles=self.provider_sync_index('jellyfin')
            for incoming in collected:
                provider_id=incoming['sources'][0].get('providerItemId');owner_id=owners.get(provider_id)
                if owner_id:
                    refreshed=self.merge_items(owner_id,incoming,'incoming','same',allow_kind_change=True);job['refreshed']+=1
                    with self.db() as db:already_pending=any(json.loads(row[0]).get('incoming',{}).get('id')==refreshed['id'] for row in db.execute('SELECT data FROM review_queue'))
                    if already_pending:continue
                    if not any(item_id!=refreshed['id'] for item_id in titles.get((refreshed.get('kind'),work_title_key(refreshed.get('title'))),())):continue
                    candidates=self.match_candidates(refreshed,exclude=refreshed['id'])
                    if not candidates or policy=='separate':continue
                    if policy=='review':self.queue_review(refreshed,candidates,'Jellyfin');job['reviewCount']+=1;continue
                    self.merge_items(candidates[0]['id'],refreshed,'incoming' if policy=='incoming' else 'keep','new' if policy=='new-version' else 'same');job['consolidated']+=1
                    if policy=='new-version':job['newVersions']+=1
                    continue
                candidates=self.match_candidates(incoming)
                if not candidates or policy=='separate':
                    self.put_item(incoming);job['added']+=1;owners[provider_id]=incoming['id'];titles.setdefault((incoming.get('kind'),work_title_key(incoming.get('title'))),set()).add(incoming['id']);continue
                if policy=='review':self.queue_review(incoming,candidates,'Jellyfin');job['reviewCount']+=1;continue
                self.merge_items(candidates[0]['id'],incoming,'incoming' if policy=='incoming' else 'keep','new' if policy=='new-version' else 'same');job['consolidated']+=1
                if policy=='new-version':job['newVersions']+=1
            job['message']=f"{job['added']} new · {job['consolidated']} consolidated · {job['newVersions']} new editions · {job['refreshed']} refreshed · {job['reviewCount']} awaiting review. Playback opens Jellyfin."
        return self.start_job('jellyfin',worker)
    def jelly_request(self,url,key,binary=False):
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,*args,**kwargs):raise ValueError('Use the final Jellyfin URL; redirects are not followed.')
        if not isinstance(key,str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,200}',key):raise Problem('Enter a valid Jellyfin API key.')
        request=urllib.request.Request(url,headers={'Authorization':f'MediaBrowser Token="{key}"','Accept':'image/*' if binary else 'application/json'})
        with urllib.request.build_opener(NoRedirect).open(request,timeout=20) as response:
            data=response.read(10*1024*1024+1)
            if len(data)>10*1024*1024:raise ValueError('Jellyfin response is too large.')
            return (data,response.headers.get_content_type()) if binary else json.loads(data)
    def plex_identity(self,base,key):
        if not isinstance(key,str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,300}',key):
            raise Problem('Reconnect Plex with a valid token in Settings.',400)
        cache_key=(base,hashlib.sha256(key.encode()).hexdigest())
        with self.state_lock:cached=self.plex_identity_cache.get(cache_key)
        if cached and cached[1]>time.monotonic():return cached[0]
        try:
            response=self.plex_request(base+'/identity',key)
            machine_id=response.get('MediaContainer',{}).get('machineIdentifier')
            plex_details_url(base,machine_id,'1')
        except (OSError,ValueError,urllib.error.URLError) as error:
            raise Problem('Blank Box could not reach your Plex server. Check its connection in Settings or open Plex directly.',502) from error
        with self.state_lock:
            self.plex_identity_cache.clear()
            self.plex_identity_cache[cache_key]=(machine_id,time.monotonic()+300)
        return machine_id
    def plex_playback_url(self,item_id,source_id):
        item=self.get_item(item_id)
        source=next((row for row in item.get('sources',[]) if row.get('id')==source_id and row.get('type')=='plex'),None)
        if not source:raise Problem('This Plex source is no longer attached to the item.',404)
        connection=self.connection('plex')
        if not connection:raise Problem('Reconnect Plex in Settings before opening this source.',404)
        base=str(connection.get('url','')).rstrip('/');parsed=urllib.parse.urlparse(base)
        if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise Problem('Reconnect Plex using its server address in Settings.',400)
        provider_id=str(source.get('providerItemId',''))
        if not re.fullmatch(r'\d{1,20}',provider_id):raise Problem('This Plex catalog ID is invalid. Refresh its connected source.',404)
        machine_id=self.plex_identity(base,connection.get('key',''))
        return plex_details_url(base,machine_id,provider_id)
    def plex_item(self,entry,base,machine_id=None):
        if not isinstance(entry,dict):return None
        provider_id=str(entry.get('ratingKey',''))
        if not re.fullmatch(r'\d{1,20}',provider_id):return None
        plex_type=str(entry.get('type','')).lower();kind={'show':'tv','album':'music'}.get(plex_type,'movie')
        source={'type':'plex','label':'Plex','providerItemId':provider_id,'url':plex_details_url(base,machine_id,provider_id) if machine_id else base+'/web/index.html'}
        source_added=provider_timestamp(entry.get('addedAt'))
        if source_added:source['addedAt']=source_added
        item={'id':'plex-'+provider_id,'title':str(entry.get('title') or 'Untitled'),'kind':kind,'year':entry.get('year'),'description':str(entry.get('summary',''))[:5000],'sources':[source],'addedAt':now(),'metadataProvider':'Plex'}
        release_date=provider_release_date(entry.get('originallyAvailableAt'))
        if release_date:item['releaseDate']=release_date
        genres=entry.get('Genre') or []
        if isinstance(genres,list):
            genre=', '.join(value['tag'].strip() for value in genres[:30] if isinstance(value,dict) and isinstance(value.get('tag'),str) and value['tag'].strip())[:500]
            if genre:item['genre']=genre
        runtime=entry.get('duration')
        if type(runtime) in (int,float) and math.isfinite(runtime) and runtime>0:item['duration']=runtime/1000
        if entry.get('thumb'):item['poster']='/api/plex-art/'+provider_id
        if kind=='music' and isinstance(entry.get('parentTitle'),str) and entry['parentTitle'].strip():item['artist']=entry['parentTitle'].strip()[:250]
        details=provider_details(entry,'plex')
        if details:item['catalogDetails']=details
        identifiers=provider_identifiers(entry,'plex',item['kind'])
        if identifiers:source['metadataIdentifiers']=identifiers
        source['metadataSnapshot']=metadata_snapshot(item)
        ensure_item_model(item);item['metadataPreference']=source['id'];return item
    def sync_saved_plex(self,policy='review'):
        connection=self.connection('plex')
        if not connection:raise Problem('Connect Plex once in Settings before refreshing its catalog.')
        return self.sync_plex(str(connection.get('url','')),connection.get('key'),policy)
    def sync_plex(self,url,key,policy='review'):
        parsed=urllib.parse.urlparse(url)
        if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:raise Problem('Use a valid Plex server address without credentials, query, or fragment.')
        if not isinstance(key,str) or not (8<=len(key)<=300):raise Problem('Enter a valid Plex token.')
        if policy not in ('review','keep','incoming','new-version','separate'):raise Problem('Choose how matching Plex records should be handled.')
        base=url.rstrip('/')
        def worker(job):
            settings=self.get_settings();settings['plexUrl']=base
            machine_id=self.plex_identity(base,key)
            with self.db() as db:hidden_ids={row[0] for row in db.execute('SELECT id FROM hidden_items')}
            sections=self.plex_request(base+'/library/sections',key).get('MediaContainer',{}).get('Directory',[]);collected=[]
            supported=[section for section in sections if section.get('type') in ('movie','show','artist')]
            for index,section in enumerate(supported):
                section_key=str(section.get('key',''))
                if not re.fullmatch(r'\d{1,20}',section_key):continue
                suffix='/all'+('?type=9' if section.get('type')=='artist' else '')
                entries=self.plex_request(base+'/library/sections/'+section_key+suffix,key).get('MediaContainer',{}).get('Metadata',[])
                for entry in entries:
                    item=self.plex_item(entry,base,machine_id)
                    if item and item['id'] not in hidden_ids:collected.append(item)
                job.update(total=len(supported),done=index+1,message=f"Read {len(collected)} Plex items from {index+1} of {len(supported)} libraries");self.save_job(job)
                if len(collected)>50000:raise ValueError('This Plex library exceeds the V1 sync limit.')
            with self.db() as db:
                db.execute('INSERT INTO connections VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',('plex',json.dumps({'url':base,'key':key,'machineIdentifier':machine_id})))
                db.execute('UPDATE settings SET data=? WHERE id=1',(json.dumps(settings),))
            job.update(consolidated=0,newVersions=0,reviewCount=0,added=0,refreshed=0)
            owners,titles=self.provider_sync_index('plex')
            for incoming in collected:
                provider_id=incoming['sources'][0].get('providerItemId');owner_id=owners.get(provider_id)
                if owner_id:
                    refreshed=self.merge_items(owner_id,incoming,'incoming','same',allow_kind_change=True);job['refreshed']+=1
                    with self.db() as db:already_pending=any(json.loads(row[0]).get('incoming',{}).get('id')==refreshed['id'] for row in db.execute('SELECT data FROM review_queue'))
                    if already_pending:continue
                    if not any(item_id!=refreshed['id'] for item_id in titles.get((refreshed.get('kind'),work_title_key(refreshed.get('title'))),())):continue
                    candidates=self.match_candidates(refreshed,exclude=refreshed['id'])
                    if not candidates or policy=='separate':continue
                    if policy=='review':self.queue_review(refreshed,candidates,'Plex');job['reviewCount']+=1;continue
                    self.merge_items(candidates[0]['id'],refreshed,'incoming' if policy=='incoming' else 'keep','new' if policy=='new-version' else 'same');job['consolidated']+=1
                    if policy=='new-version':job['newVersions']+=1
                    continue
                candidates=self.match_candidates(incoming)
                if not candidates or policy=='separate':
                    self.put_item(incoming);job['added']+=1;owners[provider_id]=incoming['id'];titles.setdefault((incoming.get('kind'),work_title_key(incoming.get('title'))),set()).add(incoming['id']);continue
                if policy=='review':self.queue_review(incoming,candidates,'Plex');job['reviewCount']+=1;continue
                self.merge_items(candidates[0]['id'],incoming,'incoming' if policy=='incoming' else 'keep','new' if policy=='new-version' else 'same');job['consolidated']+=1
                if policy=='new-version':job['newVersions']+=1
            job['message']=f"{job['added']} new · {job['consolidated']} consolidated · {job['newVersions']} new editions · {job['refreshed']} refreshed · {job['reviewCount']} awaiting review. Playback opens Plex."
        return self.start_job('plex',worker)
    def plex_request(self,url,key,binary=False):
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,*args,**kwargs):raise ValueError('Use the final Plex server URL; redirects are not followed.')
        if not isinstance(key,str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,300}',key):raise Problem('Enter a valid Plex token.')
        headers={'X-Plex-Token':key,'X-Plex-Client-Identifier':'blank-box-core','X-Plex-Product':'Blank Box','Accept':'image/*' if binary else 'application/json'}
        request=urllib.request.Request(url,headers=headers)
        with urllib.request.build_opener(NoRedirect).open(request,timeout=20) as response:
            data=response.read(10*1024*1024+1)
            if len(data)>10*1024*1024:raise ValueError('Plex response is too large.')
            return (data,response.headers.get_content_type()) if binary else json.loads(data)
    def action(self,data,profile_id='household',_exclusive=False):
        action=data.get('action')
        if not _exclusive and action in ('collection-recommendation-save','metadata-pack-install-catalog','metadata-pack-install-bundled','metadata-pack-remove','metadata-pack-refresh-confirmed','consolidate-selected','consolidate-selected-many'):
            with self.exclusive_operation():return self.action(data,profile_id,_exclusive=True)
        if action=='collection-recommendations':return self.collection_recommendations()
        if action=='collection-recommendations-approve':return self.approve_collection_recommendations(data.get('recommendationIds'))
        if action=='collection-recommendation-save':
            try:return self.save_collection_recommendation(data,operation_owned=True)
            except (ValueError,sqlite3.IntegrityError) as error:raise Problem(str(error)) from error
        if action=='collection-recommendation-dismiss':
            identifier=data.get('recommendationId')
            if not isinstance(identifier,str) or not re.fullmatch(r'recommendation-[0-9a-f]{24}',identifier):raise Problem('Choose a valid recommendation.')
            with self.db() as db:
                settings=json.loads(db.execute('SELECT data FROM settings WHERE id=1').fetchone()[0])
                settings['dismissedCollectionRecommendations']=list(dict.fromkeys([*settings.get('dismissedCollectionRecommendations',[]),identifier]))[-500:]
                db.execute('UPDATE settings SET data=? WHERE id=1',(json.dumps(settings),))
            return {'ok':True}
        if action=='disc-household':
            value=data.get('discId');fingerprint=data.get('tocFingerprint')
            if not isinstance(value,str) or len(value)>100 or not isinstance(fingerprint,str) or not re.fullmatch(r'[0-9a-f]{64}',fingerprint):raise Problem('Identify the disc first.')
            with self.db() as db:
                rows=db.execute("SELECT DISTINCT i.data FROM items i,json_each(i.data,'$.sources') s WHERE json_extract(i.data,'$.kind')='music' AND json_extract(s.value,'$.type')='physical' AND ((?<>'' AND json_extract(s.value,'$.discId')=?) OR json_extract(s.value,'$.tocFingerprint')=?) LIMIT 30",(value,value,fingerprint)).fetchall()
            return {'items':[self.public_item(json.loads(r[0])) for r in rows]}
        if action=='barcode-lookup':
            try:values=barcode_keys(data.get('barcode'))
            except ValueError as error:raise Problem(str(error)) from error
            candidates={}
            errors=[]
            for value in values:
                for namespace in ('upc-ean','isbn'):
                    for candidate in self.metadata.candidates(namespace=namespace,value=value,limit=30):candidates[candidate['id']]=candidate
                    try:
                        for candidate in self.metadata_packs.candidates(namespace=namespace,value=value,limit=30):candidates[candidate['id']]=candidate
                    except (ValueError,OSError):errors.append('An installed reference pack could not be read. Manual entry still works.')
            household=[]
            for item in self.items():
                for source in item.get('sources',[]):
                    if source.get('type')!='physical' or not source.get('barcode'):continue
                    try:matched=set(values)&set(barcode_keys(source['barcode']))
                    except ValueError:continue
                    if matched:household.append(item['id']);break
            return {'barcode':clean_barcode(data['barcode']),'householdItemIds':household,'candidates':self.metadata_household_links(list(candidates.values())[:50]),'warnings':list(dict.fromkeys(errors))}
        if action in ('collection-save','collection-remove','activity-set','activity-history','activity-undo'):
            try:
                with self.db() as db:
                    db.execute('BEGIN IMMEDIATE')
                    if action=='collection-save':
                        identifier=save_collection(db,data)
                        row=json.loads(db.execute('SELECT data FROM library_collections WHERE id=?',(identifier,)).fetchone()[0])
                        if row['kind'] in ('genre','smart','seasonal'):
                            projected=self.collection_references.genre_projection([self.public_item(i) for i in self.items()],self.collection_reference_mappings())
                            row['referenceGenres']={**row.get('referenceGenres',{}),**{i['id']:i['collectionGenres'] for i in projected if i.get('collectionGenreBasis') not in ('household','unknown') and i.get('collectionGenres')}}
                            db.execute('UPDATE library_collections SET data=? WHERE id=?',(json.dumps(row),identifier))
                        return {'ok':True,'id':identifier}
                    if action=='collection-remove':
                        if not isinstance(data.get('id'),str) or data.get('confirm') is not True:raise ValueError('Confirm the collection to remove.')
                        if not db.execute('DELETE FROM library_collections WHERE id=?',(data['id'],)).rowcount:raise ValueError('Collection not found.')
                        return {'ok':True}
                    item=self.get_item(data.get('id'))
                    scope=data.get('scopeKey')
                    if scope is not None and (item['kind']!='tv' or not isinstance(scope,str) or not re.fullmatch(r'S(?:0|[1-9]\d{0,2})',scope)):
                        raise ValueError('Choose a valid TV season.')
                    if scope is not None and action=='activity-set' and data.get('episodeKey')!=scope:
                        raise ValueError('Record status for the selected season.')
                    if action=='activity-set':record_activity(db,item,data,profile_id)
                    if action=='activity-undo':
                        if not isinstance(data.get('eventId'),str):raise ValueError('Choose an activity event.')
                        if scope is not None and not db.execute('SELECT 1 FROM activity_events WHERE id=? AND item_id=? AND episode_key=?',(data['eventId'],item['id'],scope)).fetchone():
                            raise ValueError('Activity event does not belong to this season.')
                        if not db.execute('UPDATE activity_events SET undone_at=COALESCE(undone_at,?) WHERE id=? AND item_id=?',(now(),data['eventId'],item['id'])).rowcount:raise ValueError('Activity event not found.')
                    events=activity_history(db,item['id'],scope=scope)
                    result={'ok':True,'events':events,'activity':activity_states(db).get(item['id'],{'status':'not-started'})}
                    if scope is not None:
                        current=db.execute('SELECT id,status,created_at FROM activity_events WHERE item_id=? AND episode_key=? AND undone_at IS NULL ORDER BY rowid DESC LIMIT 1',(item['id'],scope)).fetchone()
                        result['scopeActivity']={'status':current['status'],'eventId':current['id'],'updatedAt':current['created_at']} if current else {'status':'not-started'}
                    return result
            except ValueError as error:raise Problem(str(error)) from error
        if action=='catalog-resolve':return self.catalog_resolve(data.get('namespace'),data.get('value'))
        if action=='catalog-identity':
            item_id=data.get('itemId')
            if not isinstance(item_id,str) or not item_id:raise Problem('Choose a library title.')
            return {'identity':self.catalog_identity(item_id)}
        if action=='metadata-search':
            title=data.get('title','');kind=data.get('kind');year=data.get('year');namespace=data.get('namespace');value=data.get('value');scope=data.get('scope','all');exclude_item_id=data.get('excludeItemId')
            if not isinstance(title,str) or len(title)>250 or kind is not None and kind not in KINDS or year is not None and (not isinstance(year,int) or isinstance(year,bool) or not 1800<=year<=2200):raise Problem('Enter a valid metadata search.')
            if scope not in ('all','packs','saved') or exclude_item_id is not None and (not isinstance(exclude_item_id,str) or not 1<=len(exclude_item_id)<=120):raise Problem('Choose a valid metadata source and item.')
            if namespace is not None or value is not None:
                if not isinstance(namespace,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{0,63}',namespace) or not isinstance(value,str) or not 1<=len(value)<=512:raise Problem('Enter an identifier namespace and value.')
            elif not title.strip():raise Problem('Enter a title or identifier.')
            try:
                candidates=self.metadata.candidates(title=title.strip(),kind=kind,year=year,namespace=namespace,value=value,limit=50) if scope!='packs' else []
                if exclude_item_id and candidates:
                    with self.db() as db:
                        linked={row[0] for row in db.execute("SELECT entity_id FROM metadata_links WHERE target_type='item' AND target_id=?",(exclude_item_id,))}
                    candidates=[candidate for candidate in candidates if candidate['id'] not in linked]
                if scope!='saved':candidates.extend(self.metadata_packs.candidates(title=title.strip(),kind=kind,year=year,namespace=namespace,value=value,limit=max(0,50-len(candidates))))
            except ValueError as error:raise Problem(str(error)) from error
            if scope=='all':
                installed=[row for row in candidates if row['id'].startswith('pack:')]
                saved={row['id']:row for row in candidates if not row['id'].startswith('pack:')}
                with self.db() as db:
                    for row in installed:
                        keys=[key[5:] for key in row.get('lookupIds',[row['id']])]
                        marks=','.join('?' for _ in keys)
                        linked={v[0] for v in db.execute(f"SELECT entity_id FROM metadata_identifiers WHERE namespace IN ('blankbox-pack-record','blankbox-pack-alias') AND value IN ({marks})",keys)}
                        for entity_id in linked:
                            existing=saved.get(entity_id)
                            if existing:
                                corrections=db.execute('SELECT field,value_json FROM metadata_field_values WHERE entity_id=? AND owner_entered=1',(entity_id,)).fetchall()
                                if corrections:
                                    # Keep independently edited saved records selectable.
                                    # Their owner facts never disappear behind a pack row.
                                    for field,value in corrections:existing[field]=json.loads(value)
                                    continue
                                for field in ('description','genre','releaseDate','duration','catalogDetails','creator'):
                                    if not row.get(field) and existing.get(field):row[field]=existing[field]
                                del saved[entity_id]
                candidates=[*saved.values(),*installed]
            return {'candidates':self.metadata_household_links(candidates)}
        if action=='metadata-editions':
            item_id=data.get('itemId')
            if not isinstance(item_id,str) or not item_id:raise Problem('Choose a library title.')
            editions=self.metadata_editions(item_id)
            return {'workId':local_work_id(item_id),'editions':editions,'editionSummary':reference_summary(editions)}
        if action=='metadata-pack-list':
            try:catalog_packs=self.metadata_pack_catalog.list();catalog_error=''
            except (ValueError,OSError) as error:catalog_packs=[];catalog_error=str(error)
            try:
                bundled={row['id']:row for row in self.metadata_bundled_catalog.list()}
                bundled.update({row['id']:row for row in catalog_packs});catalog_packs=list(bundled.values())
            except (ValueError,OSError) as error:catalog_error=catalog_error or str(error)
            return {'packs':self.metadata_packs.list(),'packErrors':self.metadata_packs.errors()+self.bundled_metadata_errors,
                    'catalogPacks':catalog_packs,'catalogError':catalog_error,
                    'bundledProofAvailable':(Path(__file__).with_name('music-proof-pack.json')).is_file()}
        if action=='metadata-pack-install-catalog':
            try:
                catalog=self.metadata_pack_catalog if data.get('packId') in {row['id'] for row in self.metadata_pack_catalog._entries()} else self.metadata_bundled_catalog
                manifest=catalog.install(data.get('packId'))
            except (ValueError,OSError,sqlite3.Error) as error:raise Problem(str(error)) from error
            return {'ok':True,'manifest':manifest,**self.refresh_confirmed_pack_details(manifest['id'])}
        if action=='metadata-pack-refresh-confirmed':
            pack_id=data.get('packId')
            if pack_id not in {pack['id'] for pack in self.metadata_packs.list()}:raise Problem('Choose an installed metadata pack.')
            return {'ok':True,**self.refresh_confirmed_pack_details(pack_id)}
        if action=='metadata-pack-install-bundled':
            if data.get('packId')!='music-proof':raise Problem('Choose a bundled metadata pack.')
            try:
                path=Path(__file__).with_name('music-proof-pack.json')
                pack=json.loads(path.read_text(encoding='utf-8'))
                if pack.get('manifest',{}).get('id')!='music-proof':raise ValueError('Bundled metadata pack is invalid.')
                manifest=self.metadata_packs.install(pack)
            except (ValueError,OSError,json.JSONDecodeError) as error:raise Problem(str(error)) from error
            return {'ok':True,'manifest':manifest}
        if action=='metadata-pack-remove':
            try:self.metadata_packs.remove(data.get('packId'))
            except (ValueError,OSError) as error:raise Problem(str(error)) from error
            return {'ok':True}
        if action=='metadata-create':
            title=data.get('title');kind=data.get('kind');level=data.get('level','work');year=data.get('year');work_id=data.get('workId')
            if not isinstance(title,str) or not 1<=len(title.strip())<=250 or kind not in KINDS or level not in ('work','release') or year is not None and (not isinstance(year,int) or isinstance(year,bool) or not 1800<=year<=2200):raise Problem('Enter a valid manual title, type, and year.')
            try:entity_id=self.metadata.create_entity(kind=kind,level=level,title=title,year=year,work_id=work_id,format=data.get('format'),edition=data.get('edition'),season=data.get('season'))
            except ValueError as error:raise Problem(str(error)) from error
            return {'ok':True,'entity':self.metadata.get_entity(entity_id)}
        if action=='metadata-get':
            if not isinstance(data.get('id'),str):raise Problem('Choose a metadata record.')
            entity=self.metadata.get_entity(data.get('id'))
            if not entity:raise Problem('Metadata record not found.',404)
            return {'entity':entity}
        if action=='metadata-release-remove':
            entity_id=data.get('id')
            if not isinstance(entity_id,str) or data.get('confirm') is not True:raise Problem('Confirm the local edition reference to remove.')
            with self.db() as db:
                entity=db.execute("SELECT id FROM metadata_entities WHERE id=? AND level='release' AND origin='manual'",(entity_id,)).fetchone()
                if not entity:raise Problem('Only a manual release reference can be removed.')
                if db.execute('SELECT 1 FROM metadata_links WHERE entity_id=?',(entity_id,)).fetchone() or db.execute('SELECT 1 FROM metadata_identifiers WHERE entity_id=?',(entity_id,)).fetchone():
                    raise Problem('This release has confirmed links or identifiers. Unlink those before removing its reference.')
                db.execute('DELETE FROM metadata_entities WHERE id=?',(entity_id,))
            return {'ok':True}
        if action=='metadata-edit':
            entity_id=data.get('id');field=data.get('field');value=data.get('value')
            if not isinstance(entity_id,str):raise Problem('Choose a metadata record.')
            if field not in ('title','year','description','genre','artist','duration','releaseDate','format','edition','season','author','publisher','platform','catalogDetails') or field=='title' and (not isinstance(value,str) or not 1<=len(value.strip())<=250) or field=='year' and value is not None and (not isinstance(value,int) or isinstance(value,bool) or not 1800<=value<=2200):raise Problem('Choose a valid factual metadata field and value.')
            if field in ('description','genre','artist','releaseDate','author','publisher','platform') and not isinstance(value,str) or field=='duration' and value is not None and (not isinstance(value,(int,float)) or isinstance(value,bool) or value<0):raise Problem('Enter a valid metadata value.')
            if field=='catalogDetails':
                try:value=clean_details(value,strict=True)
                except ValueError as error:raise Problem(str(error)) from error
            if isinstance(value,str) and len(value)>5000:raise Problem('Metadata value is too long.')
            with self.db() as db:
                owned=db.execute("SELECT target_id FROM metadata_links WHERE entity_id=? AND target_type='item' AND relationship='local-work'",(entity_id,)).fetchone()
            if owned and field in ('title','year','description','genre','artist','catalogDetails','releaseDate','duration'):
                self.action({'action':'update','id':owned['target_id'],field:value})
                return {'ok':True,'entity':self.metadata.get_entity(entity_id)}
            try:self.metadata.set_field(entity_id,field,value)
            except ValueError as error:raise Problem(str(error)) from error
            return {'ok':True,'entity':self.metadata.get_entity(entity_id)}
        if action in ('metadata-identifier-add','metadata-identifier-remove','metadata-identifier-update'):
            entity_id=data.get('id');namespace=data.get('namespace');value=data.get('value')
            if not isinstance(entity_id,str) or not isinstance(namespace,str) or not isinstance(value,str):raise Problem('Choose an existing metadata record and identifier.')
            try:
                if action=='metadata-identifier-add':self.metadata.set_identifier(entity_id,namespace,value)
                elif action=='metadata-identifier-remove':self.metadata.remove_identifier(entity_id,namespace,value)
                else:self.metadata.replace_identifier(entity_id,namespace,value,data.get('newValue'))
            except (ValueError,sqlite3.IntegrityError) as error:raise Problem(str(error)) from error
            return {'ok':True,'entity':self.metadata.get_entity(entity_id)}
        if action in ('metadata-confirm','metadata-unlink'):
            if data.get('confirm') is not True:raise Problem('Review and confirm the metadata identity first.')
            target_type=data.get('targetType');target_id=data.get('targetId');entity_id=data.get('entityId')
            if not all(isinstance(value,str) and value for value in (target_type,target_id,entity_id)):raise Problem('Choose a metadata record and library target.')
            apply_details=data.get('applyDetails',False)
            if not isinstance(apply_details,bool) or apply_details and (action!='metadata-confirm' or target_type!='item'):
                raise Problem('Apply catalog details only when confirming a work/title match.')
            item=None;applied=[];local_id=entity_id
            try:
                if action=='metadata-confirm':
                    with self.db() as db:
                        db.execute('BEGIN IMMEDIATE')
                        if entity_id.startswith('pack:'):local_id=self.metadata_packs.materialize(db,entity_id)
                        confirm_entity(db,target_type,target_id,local_id)
                        if apply_details:
                            item=json.loads(db.execute('SELECT data FROM items WHERE id=?',(target_id,)).fetchone()[0])
                            applied=apply_reference_details(db,item,local_id)
                else:self.metadata.unlink_confirmed(target_type,target_id,entity_id)
            except ValueError as error:raise Problem(str(error)) from error
            return {'ok':True,'links':self.metadata.links(target_type,target_id),**({'localEntityId':local_id} if entity_id.startswith('pack:') else {}),**({'item':self.public_item(item),'appliedFields':applied} if item else {})}
        if action=='collecting-add':
            with self.db() as db:
                work_id=data.get('workId')
                if isinstance(work_id,str) and work_id.startswith('pack:'):
                    work_id=self.metadata_packs.materialize(db,work_id)
                release_id=data.get('releaseId')
                if isinstance(release_id,str) and release_id.startswith('pack:'):
                    release_id=self.metadata_packs.materialize(db,release_id)
                prepared=data
                if release_id and not data.get('title'):
                    release=db.execute("SELECT * FROM metadata_entities WHERE id=? AND level='release'",(release_id,)).fetchone()
                    if not release:raise ValueError('Choose a known reference edition.')
                    work=db.execute("SELECT * FROM metadata_entities WHERE id=? AND level='work'",(release['work_id'],)).fetchone()
                    if not work:raise ValueError('The edition work is unavailable.')
                    prepared={**data,'title':work['title'],'kind':work['kind'],'year':work['year'],'format':release['format'],
                              'edition':release['edition'] or '','season':release['season']}
                    work_id=work['id']
                return {'ok':True,**add_target(db,{**prepared,'workId':work_id,'releaseId':release_id},now())}
        if action=='collecting-update':
            try:
                with self.db() as db:return {'ok':True,'updated':update_target(db,data)}
            except sqlite3.IntegrityError as error:raise Problem('That title and format are already on your list.') from error
        if action=='collecting-remove':
            if data.get('confirmId')!=data.get('id'):raise Problem('Confirm the exact intention before removing it.')
            with self.db() as db:return {'ok':True,'removed':remove_target(db,data.get('id'))}
        if action=='completion-set-save':
            try:
                with self.db() as db:
                    identifier=save_set(db,data,now())
                    for row in db.execute('SELECT id,data FROM library_collections').fetchall():
                        record=json.loads(row['data'])
                        if record.get('completionSetId')==identifier:
                            record['name']=data['name'].strip();record['updatedAt']=now()
                            db.execute('UPDATE library_collections SET data=? WHERE id=?',(json.dumps(record),row['id']))
                    return {'ok':True,'id':identifier}
            except (ValueError,sqlite3.IntegrityError) as error:raise Problem(str(error)) from error
        if action=='completion-set-remove':
            if data.get('confirmId')!=data.get('id'):raise Problem('Confirm the exact completion set before removing it.')
            with self.db() as db:return {'ok':True,'removed':remove_set(db,data.get('id'))}
        if action=='completion-member-ignore':
            with self.db() as db:return {'ok':True,'updated':set_member_ignored(db,data.get('setId'),data.get('position'),data.get('ignored'))}
        if action=='commerce-links':return {'mode':'search-links','storeLinks':store_links(data,self.get_settings())}
        if action=='commerce-sources':
            settings=self.get_settings()
            return {'storeSources':store_sources(settings),'customStoreSources':settings.get('customRetailStores',[])}
        if action=='commerce-save-sources':
            try:enabled,custom=clean_store_preferences(data.get('packagedSources'),data.get('customSources'))
            except ValueError as error:raise Problem(str(error)) from error
            with self.db() as db:
                settings=json.loads(db.execute('SELECT data FROM settings WHERE id=1').fetchone()[0])
                settings.update(retailStoreKinds=enabled,customRetailStores=custom)
                db.execute('UPDATE settings SET data=? WHERE id=1',(json.dumps(settings),))
            return {'ok':True,'storeSources':store_sources(settings),'customStoreSources':custom}
        if action=='disc-status':return self.disc_status()
        if action=='disc-probe':return self.disc_probe(data.get('device'))
        if action=='disc-catalog':return self.catalog_audio_cd(data)
        if action=='disc-import':return self.import_audio_cd(data)
        if action=='scan':return self.scan(data.get('sourceId'))
        if action=='auto-discovery':return self.auto_import()
        if action=='auto-copy-scan':return self.auto_copy_scan(data.get('sourceId'))
        if action=='list-inspect':return self.list_inspect(data)
        if action=='list-stage':return self.list_stage(data)
        if action=='list-classify':return self.list_classify(data)
        if action=='list-commit':return self.list_commit(data)
        if action=='inventory':return self.index_source(data.get('sourceId'),data.get('resumeId'))
        if action=='inventory-bulk-preview':return self.inventory_bulk_preview(data.get('sourceId'),data.get('retryUnmatched',False))
        if action=='inventory-bulk-commit':return self.inventory_bulk_commit(data)
        if action=='source-monitor':return self.monitor_source(data.get('sourceId'))
        if action=='inventory-review':return self.inventory_review(data.get('batchId'),data.get('path'),data.get('title'),data.get('kind'),data.get('year'))
        if action=='rename-preview':return self.rename_preview(data.get('batchId'),data.get('path'),data.get('title'),data.get('kind'),data.get('year'))
        if action=='inventory-link':return self.inventory_link(data)
        if action=='inventory-link-selected':return self.inventory_link_selected(data)
        if action=='backup-indexed':return self.backup_indexed(data)
        if action=='backup-indexed-all-preview':return self.backup_indexed_all_preview(data.get('sourceId'))
        if action=='backup-indexed-all':return self.backup_indexed_all(data)
        if action=='import':
            if data.get('confirmCopy') is not True:raise Problem('Review and confirm the managed copies before importing.')
            return self.import_scan(data.get('scanId'),data.get('selectedIds'),data.get('policy','keep'),data.get('decisions'))
        if action=='backup':return self.backup()
        if action=='full-recovery':return self.full_recovery_point()
        if action=='full-recovery-points':return {'points':self.full_recovery_points()}
        if action=='prepare-full-restore':return self.prepare_full_restore(data.get('id'))
        if action=='jellyfin':return self.sync_jellyfin(str(data.get('url','')),data.get('key'),data.get('policy','review'))
        if action=='plex':return self.sync_plex(str(data.get('url','')),data.get('key'),data.get('policy','review'))
        if action=='refresh-item':return self.refresh_item_sources(data.get('id'))
        if action=='tv-catalog-refresh':return self.refresh_tv_catalog(data.get('id'),data.get('sourceId'))
        if action=='metadata-choice':
            if data.get('confirm') is not True:raise Problem('Review and confirm the metadata source first.')
            replace_edits=data.get('replaceEdits',False)
            if not isinstance(replace_edits,bool):raise Problem('Choose whether to apply the selected details.')
            return self.choose_metadata_source(data.get('id'),data.get('sourceId'),replace_edits)
        if action=='missing-provider-covers':return self.missing_provider_covers()
        if action=='restore-provider-covers':
            if data.get('confirm') is not True:raise Problem('Confirm the missing cover count first.')
            return self.restore_missing_provider_covers(data.get('expectedCount'))
        if action=='artwork-candidates':return {'candidates':self.artwork_candidates(data.get('id'))}
        if action=='artwork-remove':
            if data.get('confirm') is not True:raise Problem('Confirm removal of this local cover.')
            return self.remove_owner_artwork(data.get('id'))
        if action=='resolve-review':return self.resolve_review(data.get('reviewId'),data.get('policy'),data.get('targetId'))
        if action=='resolve-all-reviews':
            with self.exclusive_operation():return self.resolve_all_reviews(data.get('policy'))
        if action=='physical-reference-matches':return self.physical_reference_matches(data)
        if action=='match-search':return self.search_matches(data.get('query'),data.get('exclude'),data.get('sourceScope','all'))
        if action=='match':
            item=self.get_item(data.get('id'));match=self.get_item(data.get('matchId'))
            if item['id']==match['id']:raise Problem('Choose a different catalog item.')
            if data.get('keepMatchId') is True:
                sources=item.get('sources',[])
                if (not any(source.get('type')=='digital' for source in sources)
                    or any(source.get('type') not in ('digital','catalog') for source in sources)
                    or len(item.get('versions',[]))!=1
                    or item.get('metadataOverrides') or item.get('blankboxMetadataSnapshot')
                    or item.get('discImport') or item.get('favorite') or item.get('progress')):
                    raise Problem('This title has owner details or editions that need individual match review.',409)
                merged=self.merge_items(match['id'],item,'keep','same',allow_kind_change=True)
                return {'ok':True,'item':self.public_item(merged),'consolidated':True}
            # The Match button is an explicit owner decision. It may also correct a
            # record that physical intake initially classified as movie instead of TV.
            merged=self.merge_items(item['id'],match,'incoming','same',allow_kind_change=True,force_metadata=True)
            connected=[source for source in match.get('sources',[]) if source.get('type') in ('jellyfin','plex') and source.get('providerItemId')]
            selected=next((source for source in connected if source.get('id')==match.get('metadataPreference')),next(iter(connected),None))
            if selected:
                attached=next((source for source in merged['sources'] if source.get('type')==selected['type'] and source.get('providerItemId')==selected['providerItemId']),None)
                if attached:
                    self.choose_metadata_source(merged['id'],attached['id']);merged=self.get_item(merged['id'])
            return {'ok':True,'item':self.public_item(merged),'consolidated':True}
        if action=='consolidate-selected':
            if data.get('confirm') is not True:raise Problem('Review both Media Items before consolidating.',400)
            target_id=data.get('targetId');incoming_id=data.get('incomingId')
            if not isinstance(target_id,str) or not isinstance(incoming_id,str) or target_id==incoming_id:raise Problem('Select two distinct Media Items.',400)
            target=self.get_item(target_id);incoming=self.get_item(incoming_id)
            if target.get('title')!=data.get('targetTitle') or incoming.get('title')!=data.get('incomingTitle'):raise Problem('A selected title changed. Review both items again.',409)
            if target.get('kind')!=incoming.get('kind'):raise Problem('Select two titles of the same media type.',400)
            if len(incoming.get('versions',[]))!=1 or incoming.get('metadataOverrides') or incoming.get('blankboxMetadataSnapshot') or incoming.get('discImport') or incoming.get('favorite') or incoming.get('progress'):
                raise Problem('This title has editions or owner details that need individual match review.',409)
            conflicting=('year','releaseDate','description','genre','artist','duration','catalogDetails')
            if any(target.get(field) not in (None,'',{},[]) and incoming.get(field) not in (None,'',{},[]) and target.get(field)!=incoming.get(field) for field in conflicting):
                raise Problem('These titles have different catalog facts. Review the match individually.',409)
            incoming_label=incoming['versions'][0].get('label') or STANDARD_EDITION
            same_edition=any((version.get('label') or STANDARD_EDITION)==incoming_label for version in target.get('versions',[]))
            merged=self.merge_items(target_id,incoming,'keep','same' if same_edition else 'new')
            return {'ok':True,'item':self.public_item(merged),'consolidated':True}
        if action=='consolidate-selected-many':
            rows=data.get('incoming');target_id=data.get('targetId')
            if not isinstance(rows,list) or not 1<=len(rows)<=100 or not isinstance(target_id,str):
                raise Problem('Select 1 to 100 split titles and one existing destination title.')
            if data.get('confirm') is not True or data.get('confirmedCount')!=len(rows):
                raise Problem('Review and confirm the number of titles to consolidate.')
            target=self.get_item(target_id)
            if target.get('title')!=data.get('targetTitle'):
                raise Problem('The destination title changed. Review it again.',409)
            incoming=[];seen=set()
            for row in rows:
                if not isinstance(row,dict) or not isinstance(row.get('id'),str) or row['id'] in seen or row['id']==target_id:
                    raise Problem('Choose distinct split titles, excluding the destination.',400)
                seen.add(row['id']);item=self.get_item(row['id'])
                if item.get('title')!=row.get('title'):raise Problem('A selected title changed. Review it again.',409)
                sources=item.get('sources',[])
                if (item.get('kind')!=target.get('kind') or not sources
                    or not any(source.get('type')=='digital' for source in sources)
                    or any(source.get('type') not in ('digital','catalog') for source in sources)
                    or len(item.get('versions',[]))!=1 or item.get('metadataOverrides')
                    or item.get('blankboxMetadataSnapshot') or item.get('discImport')
                    or item.get('favorite') or item.get('progress')):
                    raise Problem('A selected title has a different media type, editions, or owner details. Review it individually.',409)
                incoming.append(item)
            completed=0
            for item in incoming:
                try:self.merge_items(target_id,item,'keep','same')
                except Exception as error:
                    raise Problem(f'Consolidated {completed} of {len(incoming)} titles before stopping: {error}',409) from error
                completed+=1
            return {'ok':True,'item':self.public_item(self.get_item(target_id)),'consolidatedCount':completed}
        if action=='delete':
            if not data.get('id') or data.get('confirmId')!=data.get('id'):raise Problem('Confirm the exact item before removing it.',400)
            if data.get('cancelPhysicalIntake'):
                item=self.get_item(data['id']);sources=item.get('sources',[])
                if len(sources)!=1 or sources[0].get('type')!='physical' or not data.get('physicalSourceId') or sources[0].get('id')!=data.get('physicalSourceId'):
                    raise Problem('This title now has other sources or copies. Open its details and remove only the physical copy you intended to undo.',409)
            return self.remove_item(data['id'])
        if action=='remove-source':
            if not data.get('sourceId') or data.get('confirmSourceId')!=data.get('sourceId'):raise Problem('Confirm the exact source before removing it.',400)
            return self.remove_source(data.get('id'),data['sourceId'])
        if action=='restore-hidden':return self.restore_hidden(data.get('id'))
        if action=='media-rights-accept':
            if data.get('confirm') is not True or data.get('termsVersion')!=MEDIA_RIGHTS_TERMS_VERSION:
                raise Problem('Read and confirm the current media-use acknowledgement.')
            with self.db() as db:
                db.execute('BEGIN IMMEDIATE')
                settings={**DEFAULTS,**json.loads(db.execute('SELECT data FROM settings WHERE id=1').fetchone()[0])}
                existing=settings.get('mediaRightsAttestation')
                if not isinstance(existing,dict) or existing.get('accepted') is not True or existing.get('termsVersion')!=MEDIA_RIGHTS_TERMS_VERSION:
                    existing={'accepted':True,'acceptedAt':now(),'termsVersion':MEDIA_RIGHTS_TERMS_VERSION}
                    settings['mediaRightsAttestation']=existing
                    db.execute('UPDATE settings SET data=? WHERE id=1',(json.dumps(settings),))
            return {'ok':True,'mediaRightsAttestation':existing}
        if action=='settings':
            value=data.get('settings',{})
            if not isinstance(value,dict):raise Problem('Invalid settings.')
            current_settings=self.get_settings()
            name=str(value.get('name','')).strip()
            if not 1<=len(name)<=60:raise Problem('Enter a library name up to 60 characters.')
            auto_import=value.get('autoImport',False);auto_minutes=value.get('autoImportMinutes',current_settings.get('autoImportMinutes',30))
            if not isinstance(auto_import,bool) or isinstance(auto_minutes,bool) or not isinstance(auto_minutes,(int,float)) or not 1<=auto_minutes<=1440:raise Problem('Automatic import interval must be between 1 minute and 24 hours.')
            auto_provider=value.get('autoProviderRefresh',auto_import)
            auto_folder=value.get('autoFolderCopy',auto_import)
            auto_index=value.get('autoSourceIndex',current_settings.get('autoSourceIndex',False))
            if not isinstance(auto_provider,bool) or not isinstance(auto_folder,bool) or not isinstance(auto_index,bool):raise Problem('Automatic refresh choices must be on or off.')
            hero_watch=value.get('heroWatch',current_settings.get('heroWatch',True))
            hero_music=value.get('heroMusic',True);hero_books=value.get('heroBooks',True)
            hero_photos=value.get('heroPhotos',False);hero_comics=value.get('heroComics',False);hero_games=value.get('heroGames',False)
            if any(not isinstance(choice,bool) for choice in (hero_watch,hero_music,hero_books,hero_photos,hero_comics,hero_games)):raise Problem('Home feature settings must be on or off.')
            setup_done=value.get('setupDone',False);setup_version=value.get('setupVersion',1)
            if not isinstance(setup_done,bool) or setup_version!=1:raise Problem('Invalid setup version or completion state.')
            setup_mode=value.get('setupMode','');setup_step=value.get('setupStep','welcome');media_provider=value.get('mediaProvider','blankbox');remote_provider=value.get('remoteProvider','local')
            if setup_mode not in ('','managed','advanced') or setup_step not in ('welcome','media','connect','protection','access','finish'):raise Problem('Invalid setup progress.')
            if media_provider not in ('blankbox','jellyfin','plex','emby') or remote_provider not in ('local','blankbox-connect','tailscale','wireguard','custom'):raise Problem('Invalid setup provider.')
            if media_provider=='emby' or remote_provider=='blankbox-connect':raise Problem('That provider is planned but not available in this build.')
            media_inputs=value.get('mediaInputs',[]);allowed_inputs={'dvd','cd','usb','hard-drive','digital-files','addon','jellyfin','plex','emby'}
            if not isinstance(media_inputs,list) or any(not isinstance(item,str) or item not in allowed_inputs for item in media_inputs) or len(media_inputs)>len(allowed_inputs) or len(set(media_inputs))!=len(media_inputs):raise Problem('Invalid media input selection.')
            physical_formats=value.get('physicalFormats',current_settings.get('physicalFormats',list(DEFAULT_PHYSICAL_FORMATS)))
            if not isinstance(physical_formats,list) or any(not isinstance(item,str) or item not in CURRENT_PHYSICAL_FORMATS for item in physical_formats) or len(physical_formats)>len(CURRENT_PHYSICAL_FORMATS) or len(set(physical_formats))!=len(physical_formats):raise Problem('Invalid physical format selection.')
            def saved_values(key,limit):
                values=value.get(key,current_settings.get(key,[]))
                if not isinstance(values,list) or len(values)>100 or any(not isinstance(item,str) or not item.strip() or len(item.strip())>limit for item in values):raise Problem(f'Invalid {key}.')
                cleaned=[item.strip() for item in values]
                if len({item.casefold() for item in cleaned})!=len(cleaned):raise Problem(f'Choose each {key} value once.')
                return cleaned
            physical_locations=saved_values('physicalLocations',250);game_platforms=saved_values('gamePlatforms',120)
            platform_catalog_version=value.get('gamePlatformCatalogVersion',current_settings.get('gamePlatformCatalogVersion',1))
            if platform_catalog_version!=1:raise Problem('Invalid game platform catalog version.')
            sidebar_shortcuts=value.get('sidebarShortcuts',current_settings.get('sidebarShortcuts',[]))
            shortcut_version=value.get('sidebarShortcutVersion',current_settings.get('sidebarShortcutVersion',1))
            if shortcut_version!=1:raise Problem('Invalid sidebar shortcut version.')
            if not isinstance(sidebar_shortcuts,list) or len(sidebar_shortcuts)>len(SIDEBAR_SHORTCUTS) or any(not isinstance(item,str) or item not in SIDEBAR_SHORTCUTS for item in sidebar_shortcuts) or len(set(sidebar_shortcuts))!=len(sidebar_shortcuts):raise Problem('Choose each sidebar shortcut once.')
            sidebar_order=value.get('sidebarOrder',current_settings.get('sidebarOrder',DEFAULTS['sidebarOrder']))
            if not isinstance(sidebar_order,list) or len(sidebar_order)>len(SIDEBAR_DESTINATIONS) or any(not isinstance(item,str) or item not in SIDEBAR_DESTINATIONS for item in sidebar_order) or len(set(sidebar_order))!=len(sidebar_order):raise Problem('Choose each library link once. Home and tools stay fixed.')
            sidebar_order=list(dict.fromkeys(sidebar_order+list(SIDEBAR_DESTINATIONS)))
            home_rows=value.get('homeRows',current_settings.get('homeRows',DEFAULTS['homeRows']))
            if not isinstance(home_rows,list) or len(home_rows)>len(HOME_ROWS) or any(not isinstance(item,str) or item not in HOME_ROWS for item in home_rows) or len(set(home_rows))!=len(home_rows):raise Problem('Choose each Home row once.')
            home_hero_order=value.get('homeHeroOrder',current_settings.get('homeHeroOrder',DEFAULTS['homeHeroOrder']))
            if not isinstance(home_hero_order,list) or len(home_hero_order)!=len(HOME_HERO_MODES) or any(not isinstance(item,str) or item not in HOME_HERO_MODES for item in home_hero_order) or len(set(home_hero_order))!=len(HOME_HERO_MODES):raise Problem('Choose each featured media type once.')
            home_hero_sort=value.get('homeHeroSort',current_settings.get('homeHeroSort',DEFAULTS['homeHeroSort']))
            if home_hero_sort not in HOME_HERO_SORTS:raise Problem('Choose a supported feature order.')
            optical_drive=value.get('opticalDrive',current_settings.get('opticalDrive',''))
            drive_pattern=r'[A-Z]:' if os.name=='nt' else r'/dev/sr\d+'
            if not isinstance(optical_drive,str) or (optical_drive and (len(optical_drive)>32 or not re.fullmatch(drive_pattern,optical_drive) and optical_drive!=current_settings.get('opticalDrive',''))):
                raise Problem('Choose a detected optical drive or automatic selection.')
            if optical_drive and optical_drive not in audio_cd_devices() and optical_drive!=current_settings.get('opticalDrive',''):
                raise Problem('That optical drive is not currently connected.')
            streaming_services=value.get('streamingServices',[]);allowed_streaming={'netflix','prime-video','disney-plus','youtube','spotify','apple-tv'}
            if not isinstance(streaming_services,list) or any(not isinstance(item,str) or item not in allowed_streaming for item in streaming_services) or len(streaming_services)>len(allowed_streaming) or len(set(streaming_services))!=len(streaming_services):raise Problem('Invalid streaming service selection.')
            help_tips=value.get('helpTipsEnabled',current_settings.get('helpTipsEnabled',True))
            if not isinstance(help_tips,bool):raise Problem('Help tips must be on or off.')
            attestation=current_settings.get('mediaRightsAttestation')
            if not isinstance(attestation,dict) or attestation.get('accepted') is not True or attestation.get('termsVersion')!=MEDIA_RIGHTS_TERMS_VERSION:
                requested=value.get('mediaRightsAttestation')
                attestation={'accepted':True,'acceptedAt':now(),'termsVersion':MEDIA_RIGHTS_TERMS_VERSION} if isinstance(requested,dict) and requested.get('accepted') is True and requested.get('termsVersion')==MEDIA_RIGHTS_TERMS_VERSION else None
            if setup_done and not current_settings.get('setupDone') and not attestation:
                raise Problem('Confirm the media-use acknowledgement before finishing setup.')
            settings={**DEFAULTS,'helpTipsEnabled':help_tips,'name':name,'opticalDrive':optical_drive,'setupDone':setup_done,'setupVersion':1,'setupMode':setup_mode,'setupStep':setup_step,'mediaProvider':media_provider,'mediaInputs':media_inputs,'physicalFormats':physical_formats,'physicalLocations':physical_locations,'gamePlatforms':game_platforms,'gamePlatformCatalogVersion':1,'sidebarShortcuts':sidebar_shortcuts,'sidebarShortcutVersion':1,'sidebarOrder':sidebar_order,'streamingServices':streaming_services,'remoteProvider':remote_provider,'autoImport':auto_folder,'autoProviderRefresh':auto_provider,'autoFolderCopy':auto_folder,'autoSourceIndex':auto_index,'autoImportMinutes':int(auto_minutes),'heroWatch':hero_watch,'heroMusic':hero_music,'heroBooks':hero_books,'heroPhotos':hero_photos,'heroComics':hero_comics,'heroGames':hero_games,'homeRows':home_rows,'homeHeroOrder':home_hero_order,'homeHeroSort':home_hero_sort,'retailStoreKinds':current_settings.get('retailStoreKinds',{}),'customRetailStores':current_settings.get('customRetailStores',[]),'mediaRightsAttestation':attestation}
            for key in ('jellyfinUrl','plexUrl','immichUrl','remoteUrl'):
                url=value.get(key,'')
                if not isinstance(url,str) or len(url)>2000:raise Problem('Invalid service address.')
                p=urllib.parse.urlparse(url)
                if url and (p.scheme not in ('http','https') or not p.hostname or p.username or p.password):raise Problem('Use an http or https address without embedded credentials.')
                settings[key]=url
            with self.db() as db:
                db.execute('BEGIN IMMEDIATE')
                latest=json.loads(db.execute('SELECT data FROM settings WHERE id=1').fetchone()[0]).get('mediaRightsAttestation')
                if isinstance(latest,dict) and latest.get('accepted') is True and latest.get('termsVersion')==MEDIA_RIGHTS_TERMS_VERSION:
                    settings['mediaRightsAttestation']=latest
                db.execute('UPDATE settings SET data=? WHERE id=1',(json.dumps(settings),))
            return {'ok':True}
        if action=='physical-check':
            title,kind,_,_=self.physical_data(data);return {'candidates':self.physical_candidates(title,kind)}
        if action=='attach-physical':return self.attach_physical(data.get('id'),data)
        if action=='remove-physical':return self.remove_physical(data.get('id'),data.get('source'))
        if action=='move-physical-location':return self.move_physical_location(data.get('fromLocation'),data.get('toLocation'))
        if action=='physical':
            title,kind,year,source=self.physical_data(data)
            genre=data.get('genre','');description=data.get('description','')
            if not isinstance(genre,str) or len(genre)>500 or not isinstance(description,str) or len(description)>5000:raise Problem('Check the catalog details you entered.')
            item={'id':uuid.uuid4().hex,'title':title,'kind':kind,'year':year,'genre':genre.strip(),'sources':[source],'addedAt':now(),'description':description.strip() or 'A physical copy in your collection. This record does not include a digital copy.'}
            item['versions']=[{'id':uuid.uuid4().hex,'label':physical_edition_label(source['label'],source.get('edition')),
                               'format':source['label'],'edition':source.get('edition') or None,
                               **({'year':year} if year else {})}]
            if source.get('season'):
                item['versions'][0]['season']=source['season']
                item['versions'][0]['label']+=' · '+season_label(source['season'])
            self.save_reviewed_physical(item,source,data);self.remember_physical_choices(source);return {'ok':True,'item':item}
        if action=='update-source-progress':
            item=self.get_item(data.get('id'))
            source_id=data.get('sourceId');progress=data.get('progress')
            source=next((row for row in item.get('sources',[]) if row.get('id')==source_id),None)
            if (item.get('kind')!='book' or not isinstance(source_id,str) or not source_id or
                source is None or source.get('type') not in ('local','digital') or
                not (source.get('audioBook') or str(source.get('mime') or '').startswith('audio/') or
                     str(source.get('path') or '').lower().endswith(('.m4b','.m4a','.mp3','.aac','.flac','.ogg','.opus','.wav'))) or
                isinstance(progress,bool) or not isinstance(progress,(float,int)) or not 0<=progress<=1):
                raise Problem('Choose an audiobook source and valid listening progress.')
            source['playbackProgress']=progress
            self.catalog.save_item(item)
            return {'ok':True,'item':self.public_item(item)}
        if action=='update':
            id=data.get('id');item=self.get_item(id);before_fields=metadata_snapshot(item)
            if 'favorite' in data:
                if not isinstance(data['favorite'],bool):raise Problem('Invalid favorite value.')
                item['favorite']=data['favorite']
            if 'customGenres' in data:
                try:item['customGenres']=collection_labels(data['customGenres'])
                except ValueError as error:raise Problem(str(error)) from error
            if 'progress' in data:
                if not isinstance(data['progress'],(float,int)) or not 0<=data['progress']<=1:raise Problem('Invalid progress.')
                item['progress']=data['progress']
            if 'kind' in data:
                if data['kind'] not in KINDS:raise Problem('Invalid media type.')
                item['kind']=data['kind']
                if any(source.get('type')=='physical' and item['kind'] not in PHYSICAL_FORMATS.get(source.get('label'),()) for source in item.get('sources',[])) and 'physicalSources' not in data:
                    raise Problem('This media type does not fit an owned physical format.')
            if 'title' in data:
                if not isinstance(data['title'],str) or not 1<=len(data['title'].strip())<=250:raise Problem('Enter a title up to 250 characters.')
                item['title']=data['title'].strip()
            if 'year' in data:
                year=data['year']
                if year is not None and (not isinstance(year,int) or not 1800<=year<=2200):raise Problem('Enter a valid year.')
                if year is None:item.pop('year',None)
                else:item['year']=year
            for key,limit in (('description',5000),('genre',500)):
                if key in data:
                    value=data[key]
                    if not isinstance(value,str) or len(value)>limit:raise Problem(f'Invalid {key}.')
                    if value.strip():item[key]=value.strip()
                    else:item.pop(key,None)
            if 'artist' in data:
                value=data['artist']
                if item.get('kind')!='music' or not isinstance(value,str) or len(value)>250:raise Problem('Enter a valid music artist.')
                if value.strip():item['artist']=value.strip()
                else:item.pop('artist',None)
            for field in ('releaseDate','duration','catalogDetails'):
                if field not in data:continue
                if data[field] in (None,'',{}):item.pop(field,None);continue
                try:item[field]=clean_facts({field:data[field]},strict=True)[field]
                except (ValueError,KeyError) as error:raise Problem('Enter valid catalog details, release date, or runtime.') from error
            if 'trackTitles' in data:
                rows=data['trackTitles']
                tracks={source['id']:source for source in item.get('sources',[]) if source.get('type')=='local' and source.get('trackNumber') and source.get('id')}
                if item.get('kind')!='music' or not item.get('discImport') or not isinstance(rows,list) or len(rows)!=len(tracks):raise Problem('Review every imported track name.')
                if any(not isinstance(row,dict) or not isinstance(row.get('sourceId'),str) or not isinstance(row.get('title'),str) or not 1<=len(row['title'].strip())<=250 for row in rows):raise Problem('Enter a valid title for each track.')
                if {row['sourceId'] for row in rows}!=set(tracks):raise Problem('Track list changed. Reopen this album before saving.')
                for row in rows:tracks[row['sourceId']]['trackTitle']=row['title'].strip()
            if 'location' in data:
                location=data['location']
                if not isinstance(location,str) or len(location)>250:raise Problem('Invalid shelf location.')
                for source in item.get('sources',[]):
                    if source.get('type')=='physical':source['location']=location.strip()
            if 'tvSeasons' in data:
                physical_versions={source.get('versionId') for source in item.get('sources',[]) if source.get('type')=='physical'}
                editable={version['id']:version for version in item.get('versions',[]) if version['id'] not in physical_versions}
                rows=data['tvSeasons']
                if item.get('kind')!='tv' or not isinstance(rows,list) or len(rows)!=len(editable) or any(not isinstance(row,dict) or not isinstance(row.get('versionId'),str) or not isinstance(row.get('season'),str) or not valid_season(row['season'] or None) for row in rows) or {row['versionId'] for row in rows}!=set(editable):
                    raise Problem('Review the TV season for each nonphysical version.')
                for row in rows:
                    if row['season']:editable[row['versionId']]['season']=row['season']
                    else:editable[row['versionId']].pop('season',None)
            retired_releases=retired_contents=()
            if 'physicalSources' in data:
                retired_releases,retired_contents=self.edit_physical_sources(item,data['physicalSources'])
            if 'digitalSources' in data:
                self.edit_digital_sources(item,data['digitalSources'])
            changed={key for key in ('title','kind','year','description','genre','artist','releaseDate','duration') if key in data and before_fields.get(key)!=item.get(key)}
            if 'catalogDetails' in data:
                before_details=before_fields.get('catalogDetails') or {};after_details=item.get('catalogDetails') or {}
                changed.update('catalogDetails.'+key for key in set(before_details)|set(after_details) if before_details.get(key)!=after_details.get(key))
            if changed:item['metadataOverrides']=sorted(set(item.get('metadataOverrides',[]))|changed)
            self.catalog.save_item(item,retired_release_ids=retired_releases,retired_content_ids=retired_contents)
            return {'ok':True,'item':self.public_item(item)}
        raise Problem('Unknown action.')

class Handler(http.server.BaseHTTPRequestHandler):
    server_version=f'Blank Box/{VERSION}'
    @property
    def box(self):return self.server.box
    def log_message(self,format,*args):pass # Do not log paths, keys, or media names.
    def end_headers(self):
        self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer');self.send_header('X-Frame-Options','SAMEORIGIN');super().end_headers()
    def json(self,value,status=200,cookie=None):
        payload=json.dumps(value,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(payload)))
        if cookie:self.send_header('Set-Cookie',cookie)
        self.end_headers()
        if self.command!='HEAD':self.wfile.write(payload)
    def authenticated(self):
        return self.session_profile_id() is not None
    def session_profile_id(self):
        try:
            cookies=http.cookies.SimpleCookie(self.headers.get('Cookie',''));sid=cookies.get('blank_box_session');value=sid.value if sid else ''
            return self.box.auth_session_profile(value)
        except http.cookies.CookieError:return None
    def create_session(self,profile_id,remember=False):
        sid,_=self.box.create_auth_session(profile_id,remember)
        secure='; Secure' if self.headers.get('X-Forwarded-Proto')=='https' else ''
        lifetime='; Max-Age=7776000' if remember else ''
        return sid,f'blank_box_session={sid}; HttpOnly; SameSite=Strict; Path=/{lifetime}{secure}'
    def do_HEAD(self):self.do_GET()
    def do_GET(self):
        try:
            parsed=urllib.parse.urlparse(self.path);path=urllib.parse.unquote(parsed.path)
            if path=='/health/live':return self.json(self.box.liveness())
            if path=='/health/ready':
                payload,status=self.box.readiness();return self.json(payload,status)
            if path=='/api/auth/status':return self.json({'hasProfile':self.box.has_profile(),'accessKeyAvailable':True})
            if path.startswith('/api/') or path.startswith('/media/'):
                if not self.authenticated():return self.json({'error':'Unlock Blank Box to continue.'},401)
            if path.startswith('/api/playback/plex/'):
                parts=path.split('/')
                if len(parts)!=6 or not parts[4] or not parts[5]:raise Problem('Plex playback address not found.',404)
                url=self.box.plex_playback_url(parts[4],parts[5])
                self.send_response(302);self.send_header('Location',url);self.send_header('Cache-Control','private,no-store');self.send_header('Content-Length','0');self.end_headers();return
            if path.startswith('/api/reader/'):
                parts=[part for part in path.split('/') if part]
                if len(parts) not in (4,6) or parts[:2]!=['api','reader']:
                    raise Problem('Reader address not found.',404)
                item=self.box.get_item(parts[2])
                source=next((candidate for candidate in item.get('sources',[]) if candidate.get('id')==parts[3] and candidate.get('type') in ('local','digital')),None)
                if not source:raise Problem('This reader source was not found.',404)
                with self.open_media_source(item,source) as opened:
                    try:catalog=inspect_reader(opened,source.get('path') or source.get('storedPath'))
                    except ValueError as error:raise Problem(str(error),415) from error
                    if len(parts)==4:
                        return self.json({'format':catalog['format'],'total':catalog['total'],'chapters':[{'title':chapter['title']} for chapter in catalog['chapters']]})
                    if not parts[5].isdigit():raise Problem('Reader page not found.',404)
                    index=int(parts[5])
                    if parts[4]=='chapter':
                        try:return self.json(read_chapter(opened,catalog,index))
                        except ValueError as error:raise Problem(str(error),404) from error
                    if parts[4]=='asset':
                        try:data,mime=read_asset(opened,catalog,index)
                        except ValueError as error:raise Problem(str(error),404) from error
                        self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','private,no-store');self.send_header('Content-Security-Policy',"sandbox; default-src 'none'");self.end_headers()
                        if self.command!='HEAD':self.wfile.write(data)
                        return
                    raise Problem('Reader address not found.',404)
            if path=='/api/v1/capabilities':return self.json(self.box.capabilities())
            if path=='/api/jobs':return self.json(self.box.job_state())
            if path=='/api/library/summary':
                state=self.box.browse_summary();profile_id=self.session_profile_id()
                if profile_id!='recovery':state['profile']=self.box.profile(profile_id)
                return self.json(state)
            if path=='/api/library/items':
                args={k:v[0] for k,v in urllib.parse.parse_qs(parsed.query).items()}
                try:return self.json(self.box.browse.page(args))
                except ValueError as error:raise Problem(str(error)) from error
            if path=='/api/library/reviews':return self.json({'reviews':self.box.reviews()})
            if path=='/api/library/hidden':
                args=urllib.parse.parse_qs(parsed.query)
                try:offset=int(args.get('offset',['0'])[0])
                except ValueError:raise Problem('Invalid hidden-items page.')
                if not 0<=offset<=1000000:raise Problem('Invalid hidden-items page.')
                return self.json({'records':self.box.hidden_records(50,offset)})
            if path=='/api/library/selection':
                ids=urllib.parse.parse_qs(parsed.query).get('id',[])
                if not 1<=len(ids)<=100 or any(len(v)>120 for v in ids):raise Problem('Choose up to 100 titles.')
                with self.box.db() as db:return self.json({'items':self.box.browse._cards(db,ids)})
            if path=='/api/library/item':
                identifier=urllib.parse.parse_qs(parsed.query).get('id',[''])[0]
                item=self.box.public_item(self.box.get_item(identifier))
                item=self.box.collection_references.genre_projection([item],self.box.collection_reference_mappings())[0]
                with self.box.db() as db:item['activity']=activity_states(db).get(identifier,{'status':'not-started'})
                return self.json({'item':item})
            if path=='/api/library/collections':
                args=urllib.parse.parse_qs(parsed.query)
                try:return self.json({'collection':self.box.browse.collection_edit(args['id'][0])} if args.get('id') else self.box.browse.collection_page())
                except ValueError as error:raise Problem(str(error)) from error
            if path=='/api/library':
                state=self.box.public_state();profile_id=self.session_profile_id()
                if profile_id!='recovery':state['profile']=self.box.profile(profile_id)
                return self.json(state)
            if path=='/api/collecting':
                with self.box.db() as db:targets=list_targets(db)
                items=self.box.public_state()['items'];indexed=ownership_index(items)
                with self.box.db() as db:
                    sets=list_sets(db,indexed,targets)
                    targets=[{**target,**intention_ownership(db,target,indexed)} for target in targets]
                suggestions=self.box.collection_suggestions(items,indexed,targets,sets)
                return self.json({'targets':targets,'sets':sets,'suggestions':suggestions,**self.box.collection_recommendations(items,targets)})
            if path=='/api/scan':
                id=urllib.parse.parse_qs(parsed.query).get('id',[''])[0]
                with self.box.state_lock:scan=self.box.scans.get(id)
                if not scan:raise Problem('Scan not found.',404)
                return self.json({'files':[{k:v for k,v in f.items() if k not in ('stat','sha256')} for f in scan['files']]})
            if path=='/api/inventory':
                args=urllib.parse.parse_qs(parsed.query)
                try:limit=int(args.get('limit',['30'])[0]);offset=int(args.get('offset',['0'])[0])
                except ValueError:raise Problem('Invalid inventory page.')
                return self.json(self.box.inventory(args.get('sourceId',[''])[0],limit,offset,args.get('kind',[''])[0] or None,args.get('q',[''])[0],args.get('group',[''])[0],args.get('unlinked',['0'])[0]=='1'))
            if path=='/api/auto-copy':
                args=urllib.parse.parse_qs(parsed.query)
                return self.json(self.box.auto_copy_page(args.get('sourceId',[''])[0]))
            if path=='/api/list-imports':
                args=urllib.parse.parse_qs(parsed.query)
                try:limit=int(args.get('limit',['25'])[0]);offset=int(args.get('offset',['0'])[0])
                except ValueError:raise Problem('Invalid list page.')
                return self.json(self.box.list_page(args.get('batchId',[None])[0],limit,offset,args.get('status',[None])[0]))
            if path=='/api/catalog/export.sqlite3':
                with tempfile.TemporaryDirectory(prefix='blankbox-catalog-export-') as directory:
                    exported=Path(directory)/'blankbox-catalog.sqlite3'
                    size=self.box.export_catalog_snapshot(exported)
                    self.send_response(200);self.send_header('Content-Type','application/vnd.sqlite3')
                    self.send_header('Content-Length',str(size))
                    self.send_header('Content-Disposition','attachment; filename="blankbox-catalog.sqlite3"')
                    self.send_header('Cache-Control','private, no-store');self.end_headers()
                    if self.command!='HEAD':
                        with exported.open('rb') as stream:
                            for part in iter(lambda:stream.read(CHUNK),b''):self.wfile.write(part)
                return
            if path=='/api/catalog/export.csv':
                payload=self.box.export_catalog_csv()
                self.send_response(200);self.send_header('Content-Type','text/csv; charset=utf-8');self.send_header('Content-Length',str(len(payload)))
                self.send_header('Content-Disposition','attachment; filename="blankbox-catalog.csv"')
                self.send_header('Cache-Control','private, no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers()
                if self.command!='HEAD':self.wfile.write(payload)
                return
            if path.startswith('/api/jellyfin-art/'):
                id=path.rsplit('/',1)[-1]
                if not re.fullmatch(r'[a-zA-Z0-9-]{1,100}',id):raise Problem('Invalid artwork ID.')
                with self.box.db() as db:row=db.execute('SELECT data FROM connections WHERE id=?',('jellyfin',)).fetchone()
                if not row:raise Problem('Jellyfin is not connected.',404)
                connection=json.loads(row[0]);data,mime=self.box.jelly_request(connection['url']+'/Items/'+id+'/Images/Primary?maxWidth=500',connection['key'],binary=True)
                if mime not in ('image/jpeg','image/png','image/webp','image/avif'):raise Problem('Unsupported artwork.',415)
                self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Cache-Control','private,max-age=3600');self.send_header('Content-Length',str(len(data)));self.end_headers()
                if self.command!='HEAD':self.wfile.write(data)
                return
            if path.startswith('/api/plex-art/'):
                id=path.rsplit('/',1)[-1]
                if not re.fullmatch(r'\d{1,20}',id):raise Problem('Invalid artwork ID.')
                connection=self.box.connection('plex')
                if not connection:raise Problem('Plex is not connected.',404)
                data,mime=self.box.plex_request(connection['url']+'/library/metadata/'+id+'/thumb',connection['key'],binary=True)
                if mime not in ('image/jpeg','image/png','image/webp','image/avif'):raise Problem('Unsupported artwork.',415)
                self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Cache-Control','private,max-age=3600');self.send_header('Content-Length',str(len(data)));self.end_headers()
                if self.command!='HEAD':self.wfile.write(data)
                return
            if path.startswith('/api/artwork/'):
                parts=path.split('/')
                if len(parts)!=5 or not re.fullmatch(r'[A-Za-z0-9_-]{1,120}',parts[3]) or not re.fullmatch(r'[0-9a-f]{16}',parts[4]):raise Problem('Artwork not found.',404)
                with self.box.db() as db:row=db.execute('SELECT sha256,image FROM item_artwork WHERE item_id=?',(parts[3],)).fetchone()
                if not row or row['sha256'][:16]!=parts[4]:raise Problem('Artwork not found.',404)
                image=row['image']
                self.send_response(200);self.send_header('Content-Type','image/jpeg');self.send_header('Content-Length',str(len(image)))
                self.send_header('Cache-Control','private,max-age=31536000,immutable');self.end_headers()
                if self.command!='HEAD':self.wfile.write(image)
                return
            if path.startswith('/api/artwork-candidate/'):
                parts=path.split('/')
                if len(parts)!=6:raise Problem('Artwork file not found.',404)
                with self.box.open_artwork_candidate(parts[3],parts[4],parts[5]) as opened:
                    mime=mimetypes.guess_type(parts[5])[0] or 'application/octet-stream'
                    return self.stream_opened(opened,parts[5],mime,media=True)
            if path.startswith('/media/'):
                parts=[part for part in path.split('/') if part]
                if len(parts) not in (2,3):raise Problem('This media address is invalid.',404)
                item=self.box.get_item(parts[1]);source=None
                if len(parts)==3:
                    source=next((candidate for candidate in item.get('sources',[]) if candidate.get('id')==parts[2] and candidate.get('type') in ('local','digital')),None)
                    if source is None:raise Problem('This media source was not found.',404)
                if source is None:source=next((candidate for candidate in item.get('sources',[]) if candidate.get('type')=='local'),None)
                if not source:raise Problem('This item has no local file.',404)
                with self.open_media_source(item,source) as opened:
                    return self.stream_opened(opened,Path(source.get('path') or source.get('storedPath') or 'media').name,source.get('mime') or item.get('mime') or 'application/octet-stream',media=True)
            if path.startswith('/api/'):raise Problem('Endpoint not found.',404)
            if path=='/credits':path='/credits.html'
            target=(self.box.web/path.lstrip('/')).resolve()
            if not inside(target,self.box.web):raise Problem('Not found.',404)
            if path=='/' or not target.suffix:target=self.box.web/'index.html'
            if not target.is_file():raise Problem('Not found.',404)
            return self.stream(target,mimetypes.guess_type(target.name)[0] or 'application/octet-stream')
        except Problem as e:self.json({'error':e.message},e.status)
        except (BrokenPipeError,ConnectionResetError):pass
        except (OSError,ValueError,KeyError) as e:self.json({'error':str(e)},400)
        except Exception:self.json({'error':'The request could not be completed.'},500)
    def open_media_source(self,item,source):
        """Resolve an authenticated catalog source, never a client-supplied path."""
        if source.get('type')=='digital':
            root=self.box.source_roots.get(source.get('sourceId'))
            if not root:raise Problem('This linked source is no longer configured.',404)
            try:
                opened=open_linked_file(root,source.get('path',''),source.get('rootIdentity'))
                details=os.fstat(opened.fileno())
                if details.st_size!=source.get('bytes') or details.st_mtime_ns!=source.get('sourceMtimeNs'):
                    opened.close();raise Problem('This linked file changed. Index and review it again.',409)
                return opened
            except (OSError,ValueError):raise Problem('This linked file is unavailable or changed. Reconnect or index the drive again.',409)
        relative=source.get('storedPath') or item.get('storedPath')
        if not relative:raise Problem('This item has no local file.',404)
        try:return open_linked_file(self.box.media,relative)
        except (OSError,ValueError):raise Problem('This managed file is unavailable. Check storage or restore its backup.',409)
    def stream(self,path,mime,media=False):
        with open(path,'rb') as opened:return self.stream_opened(opened,path.name,mime,media)
    def stream_opened(self,opened,filename,mime,media=False):
        size=os.fstat(opened.fileno()).st_size;start=0;end=size-1;status=200
        range_header=self.headers.get('Range')
        if range_header:
            match=re.fullmatch(r'bytes=(\d*)-(\d*)',range_header)
            if not match or (not match[1] and not match[2]):return self.range_error(size)
            if match[1]:start=int(match[1]);end=min(int(match[2]),size-1) if match[2] else size-1
            else:
                suffix=int(match[2]);start=max(size-suffix,0)
                if suffix==0:return self.range_error(size)
            if start>=size or start>end:return self.range_error(size)
            status=206
        safe_inline=mime.startswith('video/') or mime.startswith('audio/') or mime in ('image/jpeg','image/png','image/webp','image/gif','image/avif','application/pdf')
        self.send_response(status);self.send_header('Content-Type',mime if not media or safe_inline else 'application/octet-stream');self.send_header('Content-Length',str(max(0,end-start+1)));self.send_header('Accept-Ranges','bytes');self.send_header('Cache-Control','private,no-store' if media else 'no-cache')
        if status==206:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        if media:
            encoded_name=urllib.parse.quote(filename);self.send_header('Content-Disposition',f"{'inline' if safe_inline else 'attachment'}; filename*=UTF-8''{encoded_name}")
            self.send_header('Content-Security-Policy',"sandbox; default-src 'none'; style-src 'unsafe-inline'")
        self.end_headers()
        if self.command=='HEAD':return
        opened.seek(start);remaining=end-start+1
        while remaining>0:
            chunk=opened.read(min(CHUNK,remaining))
            if not chunk:break
            self.wfile.write(chunk);remaining-=len(chunk)
    def range_error(self,size):
        self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.send_header('Content-Length','0');self.end_headers()
    def do_POST(self):
        try:
            # Same-origin writes only. No CORS and no browser-accessible token endpoints.
            origin=self.headers.get('Origin')
            if origin and urllib.parse.urlparse(origin).netloc!=self.headers.get('Host'):raise Problem('Cross-origin requests are not accepted.',403)
            path=urllib.parse.urlparse(self.path).path
            if path=='/api/metadata-pack/upload':
                if not self.authenticated():raise Problem('Unlock Blank Box to continue.',401)
                if self.headers.get('Content-Type','').split(';')[0]!='application/vnd.blankbox.metadata-pack+zip':raise Problem('Choose a Blank Box metadata pack file.',415)
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=MAX_BUNDLE_BYTES:raise Problem('Metadata pack is too large or empty.',413)
                try:
                    with self.box.exclusive_operation():
                        manifest=self.box.metadata_packs.install_bundle(self.rfile.read(size))
                        refreshed=self.box.refresh_confirmed_pack_details(manifest['id'])
                except (ValueError,OSError,sqlite3.Error) as error:raise Problem(str(error)) from error
                return self.json({'ok':True,'manifest':manifest,**refreshed})
            if path.startswith('/api/artwork/upload/'):
                if not self.authenticated():raise Problem('Unlock Blank Box to continue.',401)
                item_id=path.rsplit('/',1)[-1]
                if not re.fullmatch(r'[A-Za-z0-9_-]{1,120}',item_id):raise Problem('Choose a library title.')
                if self.headers.get('Content-Type','').split(';')[0]!='image/jpeg':raise Problem('Upload a prepared JPEG cover.',415)
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=MAX_ARTWORK_BYTES:raise Problem('Cover must be smaller than 512 KB.',413)
                return self.json(self.box.save_owner_artwork(item_id,self.rfile.read(size)))
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise Problem('Use application/json.',415)
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=8*1024*1024:raise Problem('Request is too large or empty.',413)
            data=json.loads(self.rfile.read(size))
            if not isinstance(data,dict):raise Problem('Invalid request.')
            if path=='/api/login':
                ip=self.client_address[0]
                with self.box.state_lock:
                    attempts=[t for t in self.box.attempts.get(ip,[]) if time.time()-t<60]
                    if len(attempts)>=10:raise Problem('Too many attempts. Try again in one minute.',429)
                    profile=self.box.authenticate_profile(data.get('username'),data.get('password'));profile_id=profile.get('id') if profile else None
                    if not profile_id:
                        self.box.attempts[ip]=attempts+[time.time()];raise Problem('That username or password did not match.',401)
                    self.box.attempts.pop(ip,None)
                remember=data.get('remember',False)
                if not isinstance(remember,bool):raise Problem('Invalid sign-in preference.')
                _,cookie=self.create_session(profile_id,remember)
                return self.json({'ok':True,**({'profile':profile} if profile else {})},cookie=cookie)
            if path=='/api/claim-profile':
                supplied=data.get('accessKey','')
                if not isinstance(supplied,str) or not secrets.compare_digest(supplied,self.box.token):raise Problem('That recovery key did not match.',401)
                profile=self.box.create_owner_profile(data.get('username'),data.get('displayName'),data.get('password'))
                remember=data.get('remember',True)
                if not isinstance(remember,bool):raise Problem('Invalid sign-in preference.')
                _,cookie=self.create_session(profile['id'],remember)
                return self.json({'ok':True,'profile':profile},cookie=cookie)
            if path=='/api/recover-profile':
                supplied=data.get('accessKey','')
                if not isinstance(supplied,str) or not secrets.compare_digest(supplied,self.box.token):raise Problem('That recovery key did not match.',401)
                profile=self.box.recover_owner_profile(data.get('username'),data.get('password'))
                remember=data.get('remember',True)
                if not isinstance(remember,bool):raise Problem('Invalid sign-in preference.')
                _,cookie=self.create_session(profile['id'],remember)
                return self.json({'ok':True,'profile':profile},cookie=cookie)
            if not self.authenticated():raise Problem('Unlock Blank Box to continue.',401)
            if path!='/api/library':raise Problem('Endpoint not found.',404)
            return self.json(self.box.action(data,profile_id=self.session_profile_id()))
        except Problem as e:self.json({'error':e.message},e.status)
        except (json.JSONDecodeError,ValueError,TypeError):self.json({'error':'Check your request details.'},400)
        except (BrokenPipeError,ConnectionResetError):pass
        except Exception:self.json({'error':'The operation could not be started. Check Blank Box and try again.'},500)

def main():
    parser=argparse.ArgumentParser(description='Blank Box personal media system: copy-only imports, playback, and backup')
    parser.add_argument('--config',help='JSON configuration file (or set BLANKBOX_CONFIG)')
    parser.add_argument('--data',help='Blank Box data directory')
    parser.add_argument('--source',action='append',help='Existing source folder; repeat for multiple drives')
    parser.add_argument('--backup',help='Existing mounted backup directory')
    parser.add_argument('--backup-every-hours',type=float,help='Run a verified backup this often while the box is running (for example, 24)')
    parser.add_argument('--host',help='Address to listen on (default: 127.0.0.1)');parser.add_argument('--port',type=int,help='Port to listen on (default: 25265)')
    parser.add_argument('--version',action='version',version=f'Blank Box {VERSION}')
    parser.add_argument('--check-startup',action='store_true',help='Validate initialization while stopped, then exit')
    args=parser.parse_args()
    try:
        options=load_runtime_config(args.config,{
            'data':args.data,'sources':args.source,'backup':args.backup,
            'backupEveryHours':args.backup_every_hours,'host':args.host,'port':args.port,
        })
        runtime_lock=RuntimeLock(options['data'])
        box=Box(options['data'],options['sources'],options['backup'])
    except (OSError,ValueError) as error:parser.error(str(error))
    if args.check_startup:
        try:
            ready,status=box.readiness()
            if status!=200 or ready.get('status')!='ready':raise ValueError('Core readiness failed.')
            print('Core startup validation passed.')
        finally:runtime_lock.__exit__()
        return
    stop=threading.Event()
    if options['backupEveryHours'] is not None:
        box.backup_every_hours=options['backupEveryHours']
        def scheduled_backup():
            while not stop.wait(options['backupEveryHours']*3600):
                try:box.backup()
                except (Problem,OSError,ValueError):
                    print('Scheduled backup could not start. Check Storage & backup and the destination drive.',flush=True)
        threading.Thread(target=scheduled_backup,daemon=True).start()
    def scheduled_refreshes():
        schedule=RefreshSchedule()
        while not stop.wait(15):
            settings=box.get_settings()
            interval=max(60,float(settings.get('autoImportMinutes',30))*60)
            tasks=box.refresh_tasks()
            task=schedule.next_task(time.monotonic(),interval,tasks,box.operation_lock.locked())
            if task is None:continue
            try:
                box.refresh_task(task)
            except (Problem,OSError,ValueError) as error:
                if isinstance(error,Problem) and error.status==409 and box.operation_lock.locked():
                    schedule.retry(time.monotonic())
                    continue
                box.refresh_failure(task,error)
            schedule.dispatched(time.monotonic())
    threading.Thread(target=scheduled_refreshes,daemon=True).start()
    server=http.server.ThreadingHTTPServer((options['host'],options['port']),Handler);server.box=box;server.daemon_threads=True
    shutting_down=threading.Event()
    def request_shutdown(signum=None,frame=None):
        if shutting_down.is_set():return
        shutting_down.set();print('\nStopping Blank Box. Incomplete copies remain uncommitted.',flush=True)
        # BaseServer.shutdown must run outside the serve_forever thread.
        threading.Thread(target=server.shutdown,daemon=True).start()
    for signal_name in ('SIGINT','SIGTERM'):
        shutdown_signal=getattr(signal,signal_name,None)
        if shutdown_signal is not None:
            try:signal.signal(shutdown_signal,request_shutdown)
            except (OSError,ValueError):pass
    print(f"Blank Box {VERSION} is ready at http://{options['host']}:{options['port']}",flush=True)
    print(f'Your access key is in {box.token_path}',flush=True)
    print('Use a private network or Tailscale Serve for other devices. Use an authenticated HTTPS reverse proxy for access beyond your private network.',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:request_shutdown()
    finally:stop.set();server.server_close();runtime_lock.__exit__()
if __name__=='__main__':main()
