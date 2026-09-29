"""Bounded, offline parsing for user-provided catalog lists and CSV/TSV exports."""
from __future__ import annotations

import csv
import io
import re

MAX_TEXT_BYTES = 3 * 1024 * 1024
MAX_ROWS = 10000
MAX_COLUMNS = 60
FIELDS = ('title', 'kind', 'year', 'format', 'edition', 'barcode', 'location',
          'platform', 'creator', 'publisher', 'condition', 'quantity', 'volume',
          'issue', 'region', 'catalogNumber', 'certificate', 'signed', 'grade',
          'listedPrice', 'sourceType', 'sourcePath',
          'externalItemId', 'externalSourceId')
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
    'uhd': '4K UHD Blu-ray', 'ultra hd blu ray': '4K UHD Blu-ray',
    'game disc': 'Game', 'game cartridge': 'Game', 'games': 'Game',
    'hardcover': 'Hardcover', 'hardback': 'Hardcover', 'paperback': 'Paperback', 'ebook': 'Book',
    'comic book': 'Comic', 'comics': 'Comic', 'lp': 'Vinyl',
}


def _key(value):
    return re.sub(r'[^a-z0-9]', '', str(value).casefold())


def inspect_document(content, input_type):
    if not isinstance(content, str) or len(content.encode('utf-8')) > MAX_TEXT_BYTES:
        raise ValueError('Choose a UTF-8 list smaller than 3 MB.')
    content = content.lstrip('\ufeff')
    if input_type not in ('lines', 'csv', 'tsv'):
        raise ValueError('Choose a pasted list, CSV, or TSV file.')
    if input_type == 'lines':
        rows = [(number, {'Title': line.strip()}) for number, line in enumerate(content.splitlines(), 1) if line.strip()]
        headers = ['Title']
    else:
        try:
            reader = csv.reader(io.StringIO(content, newline=''), delimiter=',' if input_type == 'csv' else '\t', strict=True)
            headers = [header.strip().lstrip('\ufeff') for header in next(reader, [])]
            if not headers or len(headers) > MAX_COLUMNS or any(not header or len(header) > 120 for header in headers):
                raise ValueError('The header row is empty or has invalid columns.')
            if len({_key(header) for header in headers}) != len(headers):
                raise ValueError('Column names must be distinct.')
            rows = []
            for cells in reader:
                if not any(cell.strip() for cell in cells):
                    continue
                if len(cells) != len(headers):
                    raise ValueError(f'Row {len(rows) + 2} has {len(cells)} columns; expected {len(headers)}.')
                rows.append((len(rows) + 2, dict(zip(headers, cells))))
                if len(rows) > MAX_ROWS:
                    raise ValueError(f'Import at most {MAX_ROWS:,} rows at a time.')
        except csv.Error as error:
            raise ValueError(f'This {input_type.upper()} file cannot be read: {error}.') from error
    if not rows:
        raise ValueError('This list has no entries to import.')
    if len(rows) > MAX_ROWS:
        raise ValueError(f'Import at most {MAX_ROWS:,} rows at a time.')
    if any(len(value) > 4000 for _, row in rows for value in row.values()):
        raise ValueError('A cell exceeds the 4,000-character import limit.')
    return headers, rows


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
    return found


def normalize_row(raw, mapping, default_kind, mode, default_format, kinds, formats):
    def field(name):
        value = raw.get(mapping.get(name, ''), '')
        value = value.strip() if isinstance(value, str) else ''
        return value[1:] if value.startswith("'") and len(value) > 1 and value[1] in '=+-@' else value

    title = field('title')
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
        format_kinds = {'dvd':'movie','blu-ray':'movie','4k uhd blu-ray':'movie','vhs':'movie','cd':'music','vinyl':'music','cassette':'music','book':'book','comic':'comic','magazine':'book','game':'game'}
        header = mapping.get('title', '').casefold()
        header_kind = {'movie title':'movie','album title':'music','book title':'book','game title':'game','series title':'tv'}.get(header)
        title_kind = 'tv' if re.search(r'\bS\d{1,2}E\d{1,3}\b', title, re.I) else None
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
              'signed': 120, 'grade': 120, 'listedPrice': 120}
    for name, limit in limits.items():
        value = issue if name == 'issue' else field(name)
        if len(value) > limit:
            raise ValueError(f'{name} is too long.')
        if value:
            details[name] = value
    if physical and kind == 'game' and not details.get('platform'):
        raise ValueError('Games need a console or platform.')
    return {'title': title, 'kind': kind, 'year': int(year) if year else None,
            'physical': physical, 'format': media_format if physical else None,
            'quantity': int(quantity_text) if physical else 1, **details}


def spreadsheet_safe(value):
    text = str(value) if value is not None else ''
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@')) else text
