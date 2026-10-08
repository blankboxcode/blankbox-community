"""Bounded album track evidence, kept on its connected source."""
from __future__ import annotations

import re


def album_tracks(rows, provider, album_id):
    tracks = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        if provider == 'jellyfin':
            if row.get('Type') != 'Audio' or str(row.get('AlbumId', album_id)) != album_id:
                continue
            identifier = str(row.get('Id', ''))
            title, disc, number = row.get('Name'), row.get('ParentIndexNumber'), row.get('IndexNumber')
            duration = row.get('RunTimeTicks')
            divisor = 10_000_000
        else:
            if row.get('type') != 'track' or str(row.get('parentRatingKey', '')) != album_id:
                continue
            identifier = str(row.get('ratingKey', ''))
            title, disc, number = row.get('title'), row.get('parentIndex'), row.get('index')
            duration = row.get('duration')
            divisor = 1000
        pattern = r'[a-zA-Z0-9-]{1,100}' if provider == 'jellyfin' else r'\d{1,20}'
        if not re.fullmatch(pattern, identifier) or identifier in seen:
            continue
        seen.add(identifier)
        def position(value, fallback):
            return value if isinstance(value, int) and not isinstance(value, bool) and 0 < value <= 9999 else fallback
        entry = {'providerItemId': identifier, 'title': str(title or 'Untitled track')[:250],
                 'disc': position(disc, 1), 'number': position(number, None)}
        if isinstance(duration, (int, float)) and not isinstance(duration, bool) and 0 < duration / divisor <= 86400:
            entry['duration'] = round(duration / divisor)
        tracks.append(entry)
    tracks.sort(key=lambda row: (row['disc'], row['number'] or 10000, row['title'], row['providerItemId']))
    return {'provider': provider, 'trackCount': len(tracks), 'tracks': tracks}
