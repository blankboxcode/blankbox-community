"""Provider TV trees kept as source evidence on one household series item."""
from __future__ import annotations

import re


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if 0 <= number <= 999 else None


def _text(value, limit=250):
    return str(value).strip()[:limit] if isinstance(value, str) else ''


def _date(value):
    return value[:10] if isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value[:10]) else None


def _tree(season_rows, episode_rows, provider):
    seasons = {}
    for row in season_rows:
        number = _number(row.get('number'))
        if number is None:
            continue
        seasons[number] = {'number': number, 'title': _text(row.get('title')) or ('Specials' if number == 0 else f'Season {number}'), 'episodes': []}
    seen = set()
    for row in episode_rows:
        season = _number(row.get('season'))
        number = _number(row.get('number'))
        provider_id = _text(row.get('id'), 100)
        if season is None or number is None or not provider_id or (season, number, provider_id) in seen:
            continue
        seen.add((season, number, provider_id))
        entry = seasons.setdefault(season, {'number': season, 'title': 'Specials' if season == 0 else f'Season {season}', 'episodes': []})
        entry['episodes'].append({'number': number, 'title': _text(row.get('title')) or f'Episode {number}',
                                  'description': _text(row.get('description'), 3000), 'airDate': _date(row.get('airDate')),
                                  'providerItemId': provider_id})
    result = list(seasons.values())
    for season in result:
        season['episodes'].sort(key=lambda row: (row['number'], row['providerItemId']))
    result.sort(key=lambda row: row['number'])
    return {'provider': provider, 'seasons': result, 'episodeCount': sum(len(row['episodes']) for row in result)}


def jellyfin_tree(seasons, episodes):
    return _tree(({'number': row.get('IndexNumber'), 'title': row.get('Name')} for row in seasons if isinstance(row, dict)),
                 ({'season': row.get('ParentIndexNumber'), 'number': row.get('IndexNumber'), 'id': row.get('Id'),
                   'title': row.get('Name'), 'description': row.get('Overview'), 'airDate': row.get('PremiereDate')}
                  for row in episodes if isinstance(row, dict)), 'jellyfin')


def plex_tree(seasons, episodes):
    season_numbers = {str(row.get('ratingKey')): _number(row.get('index')) for row in seasons if isinstance(row, dict)}
    return _tree(({'number': row.get('index'), 'title': row.get('title')} for row in seasons if isinstance(row, dict)),
                 ({'season': season_numbers.get(str(row.get('parentRatingKey')), row.get('parentIndex')),
                   'number': row.get('index'), 'id': row.get('ratingKey'), 'title': row.get('title'),
                   'description': row.get('summary'), 'airDate': row.get('originallyAvailableAt')}
                  for row in episodes if isinstance(row, dict)), 'plex')
