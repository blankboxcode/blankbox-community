"""Bounded, offline parsing for user-provided catalog lists and CSV/TSV exports."""
from __future__ import annotations

import csv
import hashlib
import json
import io
import re
from datetime import datetime
from contextlib import contextmanager
from pathlib import Path

MAX_TEXT_BYTES = 100 * 1024 * 1024
MAX_ROWS = 100000
MAX_COLUMNS = 60
FIELDS = ('title', 'kind', 'year', 'format', 'edition', 'barcode', 'location',
          'platform', 'creator', 'publisher', 'condition', 'quantity', 'volume',
          'issue', 'region', 'catalogNumber', 'certificate', 'signed', 'grade',
          'listedPrice', 'sourceType', 'sourcePath',
          'externalItemId', 'externalSourceId', 'season', 'notes', 'releaseDate',
          'country', 'runtimeMinutes', 'importId', 'importProvider')
ALIASES = {
    'title': ('title', 'name', 'movie title', 'album title', 'book title', 'game title', 'series title'),
    'kind': ('media type', 'media kind', 'category', 'kind', 'item type', 'type'),
    'year': ('year', 'release year', 'published year', 'publication year'),
    'format': ('format', 'media format', 'physical format', 'disc format'),
    'edition': ('edition', 'version', 'release', 'variant'),
    'barcode': ('barcode', 'upc', 'ean', 'isbn', 'isbn13', 'isbn 13', 'isbn10', 'isbn 10'),
    'location': ('location', 'physical location', 'shelf', 'storage location'),
    'platform': ('platform', 'console', 'system', 'game system'),
    'creator': ('creator', 'author', 'authors', 'artist', 'director'),
    'publisher': ('publisher', 'studio', 'label'),
    'condition': ('condition',),
    'quantity': ('quantity', 'copies', 'count'),
    'volume': ('volume', 'volume number'),
    'issue': ('issue', 'issue number', '#'),
    'region': ('region',),
    'catalogNumber': ('catalog number', 'catalog no', 'catalogue number'),
    'certificate': ('coa', 'certificate of authenticity'),
    'signed': ('signed', 'signature'),
    'grade': ('cgc', 'grade', 'grading'),
    'listedPrice': ('price', 'listed price', 'paid price'),
    'sourceType': ('source type',),
    'sourcePath': ('original path', 'source path', 'file path'),
    'externalItemId': ('item id', 'blank box item id'),
    'externalSourceId': ('source id', 'blank box source id'),
    'season': ('season', 'tv season'),
    'notes': ('notes', 'comments', 'comment'),
    'releaseDate': ('release date', 'disc release date'),
    'country': ('country', 'release country'),
    'runtimeMinutes': ('runtime', 'runtime minutes'),
    'importId': ('release id', 'import id'),
    'importProvider': ('import provider',),
}
KIND_ALIASES = {
    'movies': 'movie', 'film': 'movie', 'films': 'movie',
    'show': 'tv', 'shows': 'tv', 'tv show': 'tv', 'tv shows': 'tv', 'television': 'tv',
    'album': 'music', 'albums': 'music', 'cd': 'music',
    'books': 'book', 'ebook': 'book', 'ebooks': 'book',
    'comics': 'comic', 'comic book': 'comic', 'comic books': 'comic',
    'games': 'game', 'video game': 'game', 'video games': 'game',
    'photos': 'photo', 'pictures': 'photo', 'home video': 'home-video',
    'documents': 'file', 'files': 'file',
}
FORMAT_ALIASES = {
    'bluray': 'Blu-ray', 'blu ray': 'Blu-ray', 'blu-ray disc': 'Blu-ray',
    '4k': '4K UHD Blu-ray', '4k uhd': '4K UHD Blu-ray',
    '4k ultra hd': '4K UHD Blu-ray', '4k ultra hd blu-ray': '4K UHD Blu-ray',
    'ultra hd': '4K UHD Blu-ray',
    'uhd': '4K UHD Blu-ray', 'ultra hd blu ray': '4K UHD Blu-ray',
    'game disc': 'Game', 'game cartridge': 'Game', 'games': 'Game',
    'hardcover': 'Hardcover', 'hardback': 'Hardcover', 'paperback': 'Paperback', 'ebook': 'Book',
    'comic book': 'Comic', 'comics': 'Comic', 'lp': 'Vinyl',
}


def document_profile(headers):
    keys = {_key(header) for header in headers}
    return 'bluray-com' if {'id', 'title', 'media', 'studio', 'releasedate', 'country', 'year'} <= keys else 'generic'


def _key(value):
    return re.sub(r'[^a-z0-9]', '', str(value).casefold())


@contextmanager
def document_rows(content, input_type):
    """Validate and iterate without retaining the complete uploaded file."""
    if isinstance(content, Path):
        if not content.is_file() or content.is_symlink() or content.stat().st_size > MAX_TEXT_BYTES:
            raise ValueError('Choose a UTF-8 list up to 100 MB.')
        stream = content.open('r', encoding='utf-8-sig', newline='')
    elif isinstance(content, str) and len(content.encode('utf-8')) <= MAX_TEXT_BYTES:
        stream = io.StringIO(content.lstrip('\ufeff'), newline='')
    else:
        raise ValueError('Choose a UTF-8 list up to 100 MB.')
    with stream:
        if input_type not in ('lines', 'csv', 'tsv'):
            raise ValueError('Choose a pasted list, CSV, or TSV file.')
        try:
            reader = stream if input_type == 'lines' else csv.reader(stream, delimiter=',' if input_type == 'csv' else '\t', strict=True)
            headers = ['Title'] if input_type == 'lines' else [header.strip().lstrip('\ufeff') for header in next(reader, [])]
            if not headers or len(headers) > MAX_COLUMNS or any(not header or len(header) > 120 for header in headers):
                raise ValueError('The header row is empty or has invalid columns.')
            if len({_key(header) for header in headers}) != len(headers):
                raise ValueError('Column names must be distinct.')
            def records():
                count = 0
                for number, entry in enumerate(reader, 1):
                    cells = [entry.strip()] if input_type == 'lines' else entry
                    if not any(cell.strip() for cell in cells):
                        continue
                    if len(cells) != len(headers):
                        raise ValueError(f'Row {count + 2} has {len(cells)} columns; expected {len(headers)}.')
                    count += 1
                    if count > MAX_ROWS:
                        raise ValueError(f'Import at most {MAX_ROWS:,} rows at a time.')
                    if any(len(value) > 4000 for value in cells):
                        raise ValueError('A cell exceeds the 4,000-character import limit.')
                    yield (number if input_type == 'lines' else count + 1), dict(zip(headers, cells))
                if not count:
                    raise ValueError('This list has no entries to import.')
            yield headers, records()
        except UnicodeError as error:
            raise ValueError('Save this collection as UTF-8 CSV, TSV or plain text, then try again.') from error
        except csv.Error as error:
            raise ValueError(f'This {input_type.upper()} file cannot be read: {error}.') from error


def inspect_document(content, input_type):
    with document_rows(content, input_type) as (headers, rows):
        return headers, list(rows)


def inspect_document_summary(content, input_type):
    sample = []
    total = 0
    with document_rows(content, input_type) as (headers, rows):
        for number, raw in rows:
            total += 1
            if len(sample) < 3:
                sample.append((number, raw))
    return headers, total, sample


def document_digest(content, options):
    """Keep the prior batch identity, including exact input bytes and mapping."""
    digest = hashlib.sha256()
    digest.update(b'{"content": "')
    if isinstance(content, Path):
        with content.open('r', encoding='utf-8', newline='') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), ''):
                digest.update(json.dumps(chunk, ensure_ascii=False)[1:-1].encode('utf-8'))
    else:
        digest.update(json.dumps(content, ensure_ascii=False)[1:-1].encode('utf-8'))
    digest.update(b'", ')
    digest.update(json.dumps(options, sort_keys=True, ensure_ascii=False)[1:].encode('utf-8'))
    return digest.hexdigest()


def suggested_mapping(headers):
    available = {_key(header): header for header in headers}
    found = {}
    for field in FIELDS:
        for alias in ALIASES[field]:
            if _key(alias) in available:
                found[field] = available[_key(alias)]
                break
    if 'edition' not in found:
        found['edition'] = next((header for header in headers if _key(header).startswith('variant')), None)
        if found['edition'] is None:
            found.pop('edition', None)
    if document_profile(headers) == 'bluray-com':
        found['format'] = available['media']
        found['importId'] = available['id']
        if 'purchaseprice' in available:
            found['listedPrice'] = available['purchaseprice']
    return found


def normalize_row(raw, mapping, default_kind, mode, default_format, kinds, formats, profile='generic'):
    def field(name):
        value = raw.get(mapping.get(name, ''), '')
        value = value.strip() if isinstance(value, str) else ''
        return value[1:] if value.startswith("'") and len(value) > 1 and value[1] in '=+-@' else value

    title = field('title')
    original_title = title
    if profile == 'bluray-com' and FORMAT_ALIASES.get(field('format').casefold()) == '4K UHD Blu-ray':
        title = re.sub(r'\s+4K$', '', title, flags=re.I).rstrip()
    year = field('year')
    if not year and not (default_kind == 'comic' or field('kind').casefold() in ('comic', 'comics')):
        inferred = re.search(r'\s*\((18\d{2}|19\d{2}|20\d{2}|21\d{2})\)\s*$', title)
        if inferred:
            title = title[:inferred.start()].rstrip()
            year = inferred.group(1)
    if not 1 <= len(title) <= 250:
        raise ValueError('Enter a title up to 250 characters.')
    kind_text = field('kind').casefold() or default_kind
    if kind_text == 'auto':
        format_hint = field('format').casefold() or (default_format.casefold() if mode == 'physical' else '')
        format_hint = FORMAT_ALIASES.get(format_hint,format_hint).casefold()
        format_kinds = {'dvd':'movie','blu-ray':'movie','4k uhd blu-ray':'movie','vhs':'movie','cd':'music','vinyl':'music','cassette':'music','book':'book','comic':'comic','magazine':'book','game':'game'}
        header = mapping.get('title', '').casefold()
        header_kind = {'movie title':'movie','album title':'music','book title':'book','game title':'game','series title':'tv'}.get(header)
        title_kind = 'tv' if re.search(r'\b(?:S\d{1,2}E\d{1,3}|season\s+\d{1,2})\b', title, re.I) or field('season') else None
        kind_text = title_kind or header_kind or format_kinds.get(format_hint) or ''
        if not kind_text:
            raise ValueError('Media type is unclear. Choose a type for this row before adding it.')
    kind = KIND_ALIASES.get(kind_text, kind_text)
    if kind not in kinds:
        raise ValueError(f'Unknown media type: {kind_text[:60]}. Choose a type in the column map.')
    if year and (not year.isdigit() or not 1800 <= int(year) <= 2200):
        raise ValueError('Release year must be between 1800 and 2200.')
    issue = field('issue')
    if kind == 'comic' and not issue and mode == 'physical':
        # Plain collector lists commonly use "Action Comics 557". Limit this
        # inference to comics so numbered movie/game titles remain untouched.
        match = re.fullmatch(r'(.+?)\s+#?(\d{1,5}(?:[A-Za-z])?)', title)
        if match:
            title, issue = match.group(1).strip(), match.group(2)
    if kind == 'comic' and issue and not title.casefold().endswith(f'#{issue}'.casefold()):
        title = f'{title} #{issue}'
    source_type = field('sourceType').casefold()
    physical = mode == 'physical' or mode == 'source' and source_type == 'physical'
    format_text = field('format') or default_format
    media_format = next((value for value in formats if value.casefold() == format_text.casefold()), None)
    media_format = media_format or FORMAT_ALIASES.get(format_text.casefold())
    if physical and (not media_format or kind not in formats[media_format]):
        raise ValueError('Choose a physical format compatible with this media type.')
    quantity_text = field('quantity') or '1'
    if not quantity_text.isdigit() or not 1 <= int(quantity_text) <= 50:
        raise ValueError('Quantity must be between 1 and 50.')
    details = {}
    limits = {'edition': 120, 'barcode': 80, 'location': 250, 'platform': 120,
              'creator': 250, 'publisher': 250, 'condition': 120, 'volume': 80,
              'issue': 80, 'region': 80, 'catalogNumber': 120, 'sourcePath': 4096,
              'externalItemId': 120, 'externalSourceId': 120, 'certificate': 120,
              'signed': 120, 'grade': 120, 'listedPrice': 120, 'notes': 4000,
              'country': 120, 'importId': 120, 'importProvider': 120}
    for name, limit in limits.items():
        value = issue if name == 'issue' else field(name)
        if len(value) > limit:
            raise ValueError(f'{name} is too long.')
        if value:
            details[name] = value
    season = field('season')
    if not season and kind == 'tv':
        match = re.search(r'\bseason\s+(\d{1,2})\b', title, re.I)
        if match:
            season = str(int(match.group(1)))
    if season:
        season = {'complete series': 'complete-series', 'specials': 'specials'}.get(season.casefold(), season)
        if kind != 'tv' or season not in ('complete-series', 'specials') and not re.fullmatch(r'[1-9][0-9]?', season):
            raise ValueError('Choose a TV season from 1 to 99, specials, or complete-series.')
        details['season'] = season
    release_date = field('releaseDate')
    if release_date:
        parsed = None
        for layout in ('%Y-%m-%d', '%b %d, %Y', '%B %d, %Y'):
            try:
                parsed = datetime.strptime(release_date, layout).date()
                break
            except ValueError:
                pass
        if parsed is None or not 1800 <= parsed.year <= 2200:
            raise ValueError('Use a valid disc release date, such as 2026-09-29.')
        details['releaseDate'] = parsed.isoformat()
    runtime = field('runtimeMinutes')
    if runtime:
        if not re.fullmatch(r'\d{1,5}(?:\.\d{1,2})?', runtime) or not 0 < float(runtime) <= 44640:
            raise ValueError('Runtime must be a positive number of minutes.')
        details['duration'] = float(runtime) * 60
    if profile == 'bluray-com':
        details['importProvider'] = 'blu-ray.com'
        details['importedTitle'] = original_title
        details['importDetails'] = raw.copy()
        if details.get('importId') and not details['importId'].isdigit():
            raise ValueError('The blu-ray.com release ID must be numeric.')
    if physical and kind == 'game' and not details.get('platform'):
        raise ValueError('Games need a console or platform.')
    return {'title': title, 'kind': kind, 'year': int(year) if year else None,
            'physical': physical, 'format': media_format if physical else None,
            'quantity': int(quantity_text) if physical else 1, **details}


def row_identity(proposed):
    """Repeated collection rows, without collapsing seasons or editions."""
    names = ('kind', 'title', 'year', 'physical', 'format', 'edition', 'barcode',
             'season', 'platform', 'volume', 'issue', 'region', 'importProvider', 'importId')
    return tuple(str(proposed.get(name) or '').strip().casefold() for name in names)


def spreadsheet_safe(value):
    text = str(value) if value is not None else ''
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@')) else text
