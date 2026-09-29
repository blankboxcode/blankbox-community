"""Bounded factual catalog details shared by local, provider and pack metadata."""
from __future__ import annotations

from datetime import date
import json
import math
import re

LIST_FIELDS = ('directors', 'writers', 'cast', 'studios', 'languages', 'countries',
               'creators', 'authors', 'publishers', 'collections')
TEXT_FIELDS = ('contentRating', 'releaseType', 'firstPublished', 'firstReleased')
COUNT_FIELDS = ('seasonCount', 'episodeCount', 'pageCount', 'trackCount', 'discCount')
FACT_FIELDS = ('description', 'genre', 'releaseDate', 'duration', 'artist', 'catalogDetails')


def text(value, limit=250):
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or len(value) > limit or any(ord(c) < 32 for c in value):
        return None
    return value


def clean_details(value, *, strict=False):
    if not isinstance(value, dict) or len(json.dumps(value, ensure_ascii=False)) > 65536:
        if strict:
            raise ValueError('Enter bounded catalog details.')
        return {}
    unknown = set(value) - set(LIST_FIELDS + TEXT_FIELDS + COUNT_FIELDS + ('ratings',))
    if strict and unknown:
        raise ValueError('Unsupported catalog detail field.')
    result = {}
    for field in LIST_FIELDS:
        if field not in value:
            continue
        raw = value[field]
        if not isinstance(raw, list) or len(raw) > 100:
            if strict:
                raise ValueError('Enter a bounded list of catalog names.')
            continue
        values = []
        for entry in raw:
            clean = text(entry)
            if clean is None:
                if strict:
                    raise ValueError('Enter catalog names up to 250 characters.')
                continue
            if clean not in values:
                values.append(clean)
        if values:
            result[field] = values
    for field in TEXT_FIELDS:
        if field not in value:
            continue
        clean = text(value[field], 120)
        if clean:
            result[field] = clean
        elif strict:
            raise ValueError('Enter a bounded catalog label.')
    for field in COUNT_FIELDS:
        if field not in value:
            continue
        count = value[field]
        if type(count) is int and 1 <= count <= 100000:
            result[field] = count
        elif strict:
            raise ValueError('Enter a positive catalog count.')
    if 'ratings' in value:
        ratings = value['ratings']
        if not isinstance(ratings, list) or len(ratings) > 10:
            if strict:
                raise ValueError('Enter bounded source-labeled ratings.')
        else:
            accepted = []
            for rating in ratings:
                if not isinstance(rating, dict):
                    if strict:
                        raise ValueError('Include a source and scale for each rating.')
                    continue
                source = text(rating.get('source'), 120)
                score, scale = rating.get('value'), rating.get('scale')
                valid = (source and type(score) in (int, float) and type(scale) in (int, float)
                         and math.isfinite(score) and math.isfinite(scale) and 0 < scale <= 1000
                         and 0 <= score <= scale and set(rating) <= {'source', 'value', 'scale', 'count'})
                count = rating.get('count')
                if count is not None and (type(count) is not int or not 0 <= count <= 1000000000):
                    valid = False
                if not valid:
                    if strict:
                        raise ValueError('Include a valid rating source, value, scale and count.')
                    continue
                clean = {'source': source, 'value': score, 'scale': scale}
                if count is not None:
                    clean['count'] = count
                if clean not in accepted:
                    accepted.append(clean)
            if accepted:
                result['ratings'] = accepted
    return result


def clean_facts(value, *, strict=False):
    if not isinstance(value, dict) or set(value) - set(FACT_FIELDS):
        if strict:
            raise ValueError('Unsupported work facts.')
        return {}
    result = {}
    for field in ('description', 'genre', 'artist'):
        raw = value.get(field)
        limit = 5000 if field == 'description' else 500 if field == 'genre' else 250
        if isinstance(raw, str) and raw.strip() and len(raw) <= limit and not any(ord(c) < 32 and c not in '\n\r\t' for c in raw):
            result[field] = raw.strip()
        elif raw not in (None, '') and strict:
            raise ValueError('Invalid factual text.')
    raw = value.get('releaseDate')
    if raw is not None:
        try:
            if not isinstance(raw, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', raw):
                raise ValueError()
            parsed = date.fromisoformat(raw)
            if not 1800 <= parsed.year <= 2200:
                raise ValueError()
            result['releaseDate'] = raw
        except ValueError:
            if strict:
                raise ValueError('Enter a valid factual release date.')
    raw = value.get('duration')
    if raw is not None:
        if type(raw) in (int, float) and math.isfinite(raw) and 0 < raw <= 2678400:
            result['duration'] = raw
        elif strict:
            raise ValueError('Enter a valid duration in seconds.')
    if 'catalogDetails' in value:
        details = clean_details(value['catalogDetails'], strict=strict)
        if details:
            result['catalogDetails'] = details
    return result


def provider_details(entry, provider):
    """Read only facts actually supplied by an attached provider record."""
    details = {}
    if provider == 'jellyfin':
        details['collections'] = entry.get('CollectionNames', [])
        if text(entry.get('CollectionName')):
            details['collections'] = [*details['collections'], entry['CollectionName']] if isinstance(details['collections'], list) else [entry['CollectionName']]
        roles = {'Director': 'directors', 'Writer': 'writers', 'Actor': 'cast', 'Creator': 'creators'}
        for person in entry.get('People', []) if isinstance(entry.get('People'), list) else []:
            if isinstance(person, dict) and person.get('Type') in roles and text(person.get('Name')):
                details.setdefault(roles[person['Type']], []).append(person['Name'])
        studios = entry.get('Studios')
        if isinstance(studios, list):
            details['studios'] = [v['Name'] for v in studios if isinstance(v, dict) and text(v.get('Name'))]
        details['contentRating'] = entry.get('OfficialRating')
        score = entry.get('CommunityRating')
        if type(score) in (int, float):
            details['ratings'] = [{'source': 'Jellyfin community rating', 'value': score, 'scale': 10}]
        if entry.get('Type') == 'MusicAlbum':
            details['trackCount'] = entry.get('ChildCount')
        elif entry.get('Type') == 'Series':
            details['seasonCount'] = entry.get('ChildCount')
    elif provider == 'plex':
        details['collections'] = [v['tag'] for v in entry.get('Collection', []) if isinstance(v, dict) and text(v.get('tag'))] if isinstance(entry.get('Collection'), list) else []
        for key, field in (('Director', 'directors'), ('Writer', 'writers'), ('Role', 'cast'),
                           ('Country', 'countries')):
            values = entry.get(key)
            if isinstance(values, list):
                details[field] = [v['tag'] for v in values if isinstance(v, dict) and text(v.get('tag'))]
        details['studios'] = [entry['studio']] if text(entry.get('studio')) else []
        details['contentRating'] = entry.get('contentRating')
        # Plex may expose scores from different providers. Preserve the labels
        # supplied with each score; do not combine them into one Blank Box score.
        ratings = []
        for key, label in (('rating', 'ratingImage'), ('audienceRating', 'audienceRatingImage')):
            score = entry.get(key)
            source = text(entry.get(label), 120)
            if type(score) in (int, float) and source:
                ratings.append({'source': 'Plex: ' + source, 'value': score, 'scale': 10})
        if ratings:
            details['ratings'] = ratings
        if entry.get('type') == 'album':
            details['trackCount'] = entry.get('leafCount')
        elif entry.get('type') == 'show':
            details['seasonCount'] = entry.get('childCount')
            details['episodeCount'] = entry.get('leafCount')
    return clean_details({k: v[:100] if isinstance(v, list) else v
                          for k, v in details.items() if v not in (None, '', [])})


def provider_identifiers(entry, provider, kind):
    """Explicit provider IDs are lookup evidence, never household merge authority."""
    identifiers = set()
    if provider == 'jellyfin' and isinstance(entry.get('ProviderIds'), dict):
        for namespace, value in entry['ProviderIds'].items():
            identifiers.add((str(namespace).lower(), str(value)))
    elif provider == 'plex' and isinstance(entry.get('Guid'), list):
        for row in entry['Guid']:
            if isinstance(row, dict) and isinstance(row.get('id'), str):
                match = re.fullmatch(r'(imdb|tmdb)://([^/?#]+)', row['id'])
                if match:
                    identifiers.add(match.groups())
    accepted = []
    for namespace, value in sorted(identifiers):
        if namespace == 'imdb' and re.fullmatch(r'tt[0-9]{1,15}', value):
            accepted.append({'namespace': 'imdb', 'value': value})
        elif namespace == 'tmdb' and kind in ('movie', 'tv') and re.fullmatch(r'[0-9]{1,15}', value):
            accepted.append({'namespace': 'tmdb-movie' if kind == 'movie' else 'tmdb-tv', 'value': value})
    return accepted
