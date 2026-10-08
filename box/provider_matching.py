"""Conservative connected-title identity and edition clues, without network reads."""
import re
import unicodedata
from collections import defaultdict

PROVIDERS=('jellyfin','plex','emby')
EDITION_TAG=re.compile(r'\{edition-([^{}]{1,120})\}',re.I)
CUT=re.compile(r"\b(director'?s cut|extended (?:cut|edition)|theatrical (?:cut|edition)|final cut|special edition|collector'?s edition|anniversary edition|unrated|remastered)\b",re.I)


def key(value):
    text=unicodedata.normalize('NFKD',str(value or '')).casefold()
    return ''.join(char for char in text if char.isalnum() and not unicodedata.combining(char))


def split_title(value,edition=None):
    title=str(value or '').strip()
    tag=EDITION_TAG.search(title)
    edition=str(edition or (tag.group(1) if tag else '')).strip()[:120]
    title=EDITION_TAG.sub('',title)
    title=re.sub(r'\s+',' ',title).strip(' ._-')
    # A combined cut remains its own work rather than borrowing one part's ID.
    if key(edition)=='supercut' and 'supercut' not in key(title):title+=' Supercut'
    return title,edition


def title_key(item):
    title,_=split_title(item.get('title'))
    if item.get('kind')!='music':title=CUT.sub('',title)
    title=re.sub(r'\s*[\[(](?:18|19|20|21)\d{2}[\])]\s*$','',title)
    return key(title)


def identifiers(item):
    accepted={'imdb','tmdb-movie' if item.get('kind')=='movie' else 'tmdb-tv'} if item.get('kind') in ('movie','tv') else set()
    return {(row.get('namespace'),row.get('value')) for source in item.get('sources',[]) if source.get('type') in PROVIDERS for row in source.get('metadataIdentifiers',[]) if isinstance(row,dict) and row.get('namespace') in accepted and isinstance(row.get('value'),str) and row['value']}


def composite(item):
    return 'supercut' in key(item.get('title')) or any(key(source.get('edition'))=='supercut' for source in item.get('sources',[]))


def clear_match(left,right):
    """Return a reason only when the saved evidence can safely join the titles."""
    kind=left.get('kind')
    if kind!=right.get('kind') or kind not in ('movie','tv','music'):return None
    if any(item.get('providerMatchPolicy')=='separate' for item in (left,right)):return None
    if not all(any(source.get('type') in PROVIDERS for source in item.get('sources',[])) for item in (left,right)):return None
    if composite(left)!=composite(right):return None
    if left.get('progress') and right.get('progress') and left['progress']!=right['progress']:return None
    edits_a,edits_b=set(left.get('metadataOverrides',[])),set(right.get('metadataOverrides',[]))
    if not (edits_a<=edits_b or edits_b<=edits_a):return None
    # Do not discard incompatible household edits while joining provider facts.
    for field in set(left.get('metadataOverrides',[]))|set(right.get('metadataOverrides',[])):
        def value(item):
            result=item
            for part in field.split('.'):
                result=result.get(part) if isinstance(result,dict) else None
            return result
        a_value,b_value=value(left),value(right)
        if a_value not in (None,'') and b_value not in (None,'') and a_value!=b_value:return None
    a,b=identifiers(left),identifiers(right)
    if any(len({value for ns,value in values if ns==namespace})>1 for values in (a,b) for namespace,_ in values):return None
    for namespace in {namespace for namespace,_ in a}&{namespace for namespace,_ in b}:
        if {value for ns,value in a if ns==namespace}.isdisjoint(value for ns,value in b if ns==namespace):return None
    years=(left.get('year'),right.get('year'))
    known=all(type(year) is int for year in years)
    if kind=='music':
        if not left.get('artist') or not right.get('artist') or key(left['artist'])!=key(right['artist']):return None
        if title_key(left)!=title_key(right) or not known or abs(years[0]-years[1])>1:return None
        return 'Same album title, artist and edition; release years agree or differ by one'
    if a&b and (not known or abs(years[0]-years[1])<=1):return 'Same supplied movie or series identifier'
    if title_key(left)!=title_key(right):return None
    if composite(left) and (not known or years[0]==years[1]):return 'Same separately named combined cut'
    if known and years[0]==years[1]:return 'Same title, year and media type, with no conflicting identifiers'
    return None


def consolidation_groups(items):
    """Bound work to identity/title buckets; reject conflicting bridge matches."""
    by_id={item['id']:item for item in items};buckets=defaultdict(set)
    for item in items:
        if item.get('kind') not in ('movie','tv','music'):continue
        buckets[(item['kind'],'title',title_key(item),key(item.get('artist')) if item['kind']=='music' else '')].add(item['id'])
        for namespace,value in identifiers(item):buckets[(item['kind'],namespace,value)].add(item['id'])
    groups={identifier:{identifier} for identifier in by_id};pairs=set()
    for bucket in buckets.values():
        if len(bucket)>200:continue
        ids=sorted(bucket)
        for index,left in enumerate(ids):
            for right in ids[index+1:]:pairs.add((left,right))
    eligible={pair for pair in pairs if clear_match(by_id[pair[0]],by_id[pair[1]])}
    neighbors=defaultdict(set)
    for left,right in eligible:neighbors[left].add(right);neighbors[right].add(left)
    ambiguous=set()
    for identifier,adjacent in neighbors.items():
        ids=sorted(adjacent)
        if any((left,right) not in eligible for index,left in enumerate(ids) for right in ids[index+1:]):ambiguous.add(identifier)
    for left,right in sorted(eligible):
        if left in ambiguous or right in ambiguous:continue
        a,b=groups[left],groups[right]
        if a is b or not all(clear_match(by_id[x],by_id[y]) for x in a for y in b):continue
        merged=a|b
        for identifier in merged:groups[identifier]=merged
    result={tuple(sorted(group)) for group in groups.values() if len(group)>1}
    return [list(group) for group in sorted(result)]
