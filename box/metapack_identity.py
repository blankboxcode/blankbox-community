"""Product names and compatibility aliases for installed offline metadata."""
import json
import re
import hashlib

IDENTITY_POLICY='blankbox-and-physical-v1'
PHYSICAL_IDENTIFIERS={'isbn','upc-ean','issn','disc-id','toc-fingerprint'}
PACK_SOURCE='Blank Box Offline Metapacks'

def validate_identity_policy(manifest):
    policy=manifest.get('identityPolicy')
    if policy is not None and policy!=IDENTITY_POLICY:
        raise ValueError('Unsupported offline pack identity policy.')
    coverage=manifest.get('releaseCoverage',{})
    if policy and (not isinstance(coverage,dict) or any(not isinstance(value,dict) for value in coverage.values())):
        raise ValueError('Invalid offline edition coverage.')
    if policy and (manifest.get('source')!=PACK_SOURCE or manifest.get('sourceUrl') or
                   'inputSources' in manifest or 'editionInputSha256' in manifest or
                   any('sourceWorkKey' in value for value in coverage.values())):
        raise ValueError('Website references belong in the private build audit.')
    return bool(policy)

def validate_local_record(record):
    if not record['record_id'].startswith(('bbp:','bbp-')) or record['source_key']!='blankbox:'+record['record_id']:
        raise ValueError('An offline record requires a Blank Box source key.')
    details=json.loads(record['source_ids_json'])
    if details!=[] and (not isinstance(details,dict) or set(details)!={'creator'}):
        raise ValueError('Website record IDs are not supported in this offline pack.')

def validate_local_provenance(provenance,record_id):
    if provenance!={'source':PACK_SOURCE,'record':record_id}:
        raise ValueError('An offline record requires Blank Box provenance.')

def native_record_id(value):
    return 'bbp-'+hashlib.sha256(('blank-box-offline-record-v1\0'+value).encode()).hexdigest()[:32]

def physical_namespace(value):
    return 'disc-id' if value=='musicbrainz-discid' else value

def pack_identifier_allowed(namespace):
    return namespace in PHYSICAL_IDENTIFIERS or namespace.startswith('blankbox-')

def visible_identifiers(rows):
    """Historical pack website mappings remain private, never active sources."""
    result=[];seen=set()
    for value in rows:
        row=dict(value);namespace=physical_namespace(row['namespace'])
        if row.get('source','').startswith('pack:'):
            if not pack_identifier_allowed(namespace):continue
            if namespace in ('blankbox-pack-record','blankbox-pack-alias') and row['value'].startswith('music-proof:') and not row['value'].split(':',1)[1].startswith('bbp-'):continue
        row['namespace']=namespace
        key=(namespace,row['value'],row.get('source',''))
        if key not in seen:result.append(row);seen.add(key)
    return result

PACK_NAMES = {
    'movie-work-candidates': 'Movies', 'tv-work-candidates': 'TV Shows',
    'book-work-candidates': 'Books', 'music-work-candidates': 'Music',
    'comic-work-candidates': 'Comics', 'game-work-candidates': 'Games',
    'music-proof': 'Audio CD matching sample',
}
PACK_DESCRIPTIONS = {
    'movie': 'Movie titles, descriptions, genres, release dates, ratings and credits for offline matching.',
    'tv': 'TV series, genres, creators, first-air dates and available season and episode counts.',
    'book': 'Book titles and authors, with publication details and available ISBN editions.',
    'music': 'Album titles, artists and release types. Audio CD editions use separate release identifiers.',
}


def pack_name(pack_id):
    return PACK_NAMES.get(pack_id, pack_id)


def alias_keys(db, manifest, record_id):
    """One direct canonical mapping; never traverse arbitrary alias chains."""
    if manifest['format'] != 5:return record_id, [record_id]
    row=db.execute('SELECT canonical_id FROM record_aliases WHERE alias_id=?',(record_id,)).fetchone()
    canonical=row[0] if row else record_id
    keys=[canonical,*[r[0] for r in db.execute('SELECT alias_id FROM record_aliases WHERE canonical_id=? ORDER BY alias_id',(canonical,))]]
    return canonical,keys


def validate_alias_evidence(encoded, alias_id, clean_facts):
    if not isinstance(encoded,str) or len(encoded)>131072:raise ValueError('Oversized alias provenance.')
    evidence=json.loads(encoded)
    if not isinstance(evidence,dict) or set(evidence)!={'basis','record','facts','identifiers','provenance'}:raise ValueError('Invalid alias provenance.')
    if not isinstance(evidence['basis'],list) or not evidence['basis'] or any(v not in ('shared-identifier','matching-release-date-and-runtime','matching-director-and-runtime','same-identified-edition') for v in evidence['basis']):raise ValueError('Invalid alias evidence.')
    if not isinstance(evidence['record'],dict) or evidence['record'].get('record_id')!=alias_id:raise ValueError('Invalid original alias record.')
    record=evidence['record']
    required={'record_id','media_type','title','original_title','year','source_key','source_ids_json','review_status'}
    if set(record) not in (required,required|{'search_titles'}):raise ValueError('Unexpected original alias fields.')
    if (not isinstance(record.get('source_key'),str) or not 1<=len(record['source_key'])<=200
            or not isinstance(record.get('title'),str) or not 1<=len(record['title'])<=250
            or type(record.get('year')) not in (int,type(None)) or record.get('year') is not None and not 1800<=record['year']<=2200):raise ValueError('Invalid original alias fields.')
    if clean_facts(evidence['facts'],strict=True)!=evidence['facts']:raise ValueError('Invalid original alias facts.')
    identifiers=evidence['identifiers']
    if not isinstance(identifiers,list) or len(identifiers)>128:raise ValueError('Invalid original alias identifiers.')
    for value in identifiers:
        if not isinstance(value,dict) or set(value)!={'namespace','value'} or not isinstance(value['namespace'],str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{0,63}',value['namespace']) or not isinstance(value['value'],str) or not 1<=len(value['value'])<=512:raise ValueError('Invalid original alias identifier.')
    provenance=evidence['provenance']
    if (not isinstance(provenance,dict) or set(provenance)!={'source','record'}
            or not isinstance(provenance['source'],str) or not 1<=len(provenance['source'])<=120
            or not isinstance(provenance['record'],str) or not 1<=len(provenance['record'])<=200):raise ValueError('Invalid original alias factual provenance.')
    return evidence
