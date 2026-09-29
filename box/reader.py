"""Read-only EPUB and CBZ views for files already managed by Blank Box.

Archives are never extracted to disk. Only bounded text and raster-image entries
are returned to the authenticated browser; active EPUB content is discarded.
"""
from __future__ import annotations

import posixpath
import re
import stat
import urllib.parse
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

MAX_ENTRIES = 5000
MAX_ARCHIVE_CONTENT = 2 * 1024 * 1024 * 1024
MAX_XML = 2 * 1024 * 1024
MAX_CHAPTER = 3 * 1024 * 1024
MAX_IMAGE = 40 * 1024 * 1024
IMAGE_MIMES = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp', '.gif': 'image/gif', '.avif': 'image/avif'}


def _local_name(tag):
    return tag.rsplit('}', 1)[-1].lower()


def _safe_entry(name):
    return bool(name) and not name.startswith('/') and '\\' not in name and all(part not in ('', '.', '..') for part in name.split('/'))


def _reference(base, href):
    value = urllib.parse.unquote(urllib.parse.urlsplit(href).path)
    if not value or value.startswith('/') or '\\' in value:
        raise ValueError('This book contains an invalid internal address.')
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(base), value))
    if not _safe_entry(resolved):
        raise ValueError('This book contains an invalid internal address.')
    return resolved


def _entries(archive):
    if len(archive.infolist()) > MAX_ENTRIES:
        raise ValueError('This archive has too many entries for the reader.')
    entries = {}
    total = 0
    for entry in archive.infolist():
        if entry.is_dir():
            continue
        if not _safe_entry(entry.filename) or stat.S_IFMT(entry.external_attr >> 16) == stat.S_IFLNK:
            raise ValueError('This archive contains an unsafe entry.')
        if entry.flag_bits & 1:
            raise ValueError('Encrypted archives are not supported by the reader.')
        if entry.filename in entries:
            raise ValueError('This archive contains duplicate entries.')
        total += entry.file_size
        if total > MAX_ARCHIVE_CONTENT or len(entries) >= MAX_ENTRIES:
            raise ValueError('This archive is too large for the reader.')
        entries[entry.filename] = entry
    return entries


def _read(archive, entry, limit):
    if entry.file_size > limit:
        raise ValueError('A page or chapter is too large for the reader.')
    with archive.open(entry) as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError('A page or chapter is too large for the reader.')
    return data


def _xml(archive, entries, name):
    entry = entries.get(name)
    if not entry:
        raise ValueError('This EPUB is missing a required book file.')
    data = _read(archive, entry, MAX_XML)
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('EPUB entities and document types are not supported.')
    try:
        return ElementTree.fromstring(data)
    except ElementTree.ParseError as error:
        raise ValueError('This EPUB has invalid book metadata.') from error


def _natural_key(value):
    return [int(part) if part.isdigit() else part.casefold() for part in re.split(r'(\d+)', value)]


def inspect_reader(path, filename=None):
    """Return a bounded internal table of readable chapters or comic pages."""
    suffix = Path(filename or path).suffix.lower()
    if suffix not in ('.epub', '.cbz'):
        raise ValueError('Only EPUB books and CBZ comics open in this reader.')
    try:
        with zipfile.ZipFile(path) as archive:
            entries = _entries(archive)
            if suffix == '.cbz':
                pages = sorted((name for name in entries if Path(name).suffix.lower() in IMAGE_MIMES), key=_natural_key)
                if not pages:
                    raise ValueError('This comic has no supported image pages.')
                return {'format': 'cbz', 'chapters': [], 'assets': pages, 'total': len(pages)}

            container = _xml(archive, entries, 'META-INF/container.xml')
            rootfile = next((node.attrib.get('full-path') for node in container.iter() if _local_name(node.tag) == 'rootfile'), None)
            if not rootfile or rootfile not in entries or not _safe_entry(rootfile):
                raise ValueError('This EPUB has no readable package file.')
            package = _xml(archive, entries, rootfile)
            manifest = {}
            spine = []
            for node in package.iter():
                tag = _local_name(node.tag)
                if tag == 'item':
                    identifier, href = node.attrib.get('id'), node.attrib.get('href')
                    if identifier and href:
                        manifest[identifier] = {'path': _reference(rootfile, href), 'type': node.attrib.get('media-type', ''), 'properties': node.attrib.get('properties', '')}
                elif tag == 'itemref' and node.attrib.get('idref'):
                    spine.append(node.attrib['idref'])
            chapters = []
            for identifier in spine:
                item = manifest.get(identifier)
                if item and item['path'] in entries and (item['type'] == 'application/xhtml+xml' or Path(item['path']).suffix.lower() in ('.xhtml', '.html', '.htm')):
                    chapters.append({'path': item['path'], 'title': f'Chapter {len(chapters) + 1}'})
            if not chapters or len(chapters) > 1000:
                raise ValueError('This EPUB has no readable chapters.')
            names = {chapter['path']: chapter for chapter in chapters}
            for item in manifest.values():
                if 'nav' not in item['properties'].split() and item['type'] != 'application/x-dtbncx+xml':
                    continue
                if item['path'] not in entries:
                    continue
                try:
                    navigation = _xml(archive, entries, item['path'])
                    for node in navigation.iter():
                        tag = _local_name(node.tag)
                        if tag not in ('a', 'content'):
                            continue
                        href = node.attrib.get('href') or node.attrib.get('src')
                        if not href:
                            continue
                        target = _reference(item['path'], href)
                        if target in names:
                            label = ''.join(node.itertext()).strip() if tag == 'a' else ''
                            if label:
                                names[target]['title'] = label[:160]
                except ValueError:
                    pass  # A malformed optional table of contents does not hide readable chapters.
            images = sorted((name for name in entries if Path(name).suffix.lower() in IMAGE_MIMES))
            return {'format': 'epub', 'chapters': chapters, 'assets': images, 'total': len(chapters)}
    except (zipfile.BadZipFile, zipfile.LargeZipFile) as error:
        raise ValueError('This book or comic is not a readable ZIP archive.') from error


class _ChapterText(HTMLParser):
    def __init__(self, chapter_path, assets):
        super().__init__(convert_charrefs=True)
        self.chapter_path = chapter_path
        self.assets = {name: index for index, name in enumerate(assets)}
        self.blocks = []
        self.parts = []
        self.kind = 'p'
        self.skip = 0

    def _flush(self):
        text = ''.join(self.parts).strip()
        if text and len(self.blocks) < 10000:
            self.blocks.append({'kind': self.kind, 'text': text[:12000]})
        self.parts = []
        self.kind = 'p'

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'iframe', 'object', 'svg'):
            self.skip += 1
            return
        if self.skip:
            return
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'blockquote', 'pre'):
            self._flush()
            self.kind = tag
        elif tag == 'br':
            self.parts.append('\n')
        elif tag == 'img':
            self._flush()
            values = dict(attrs)
            try:
                target = _reference(self.chapter_path, values.get('src', ''))
            except ValueError:
                return
            if target in self.assets and len(self.blocks) < 10000:
                self.blocks.append({'kind': 'image', 'asset': self.assets[target], 'alt': values.get('alt', '')[:200]})

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'iframe', 'object', 'svg'):
            self.skip = max(0, self.skip - 1)
            return
        if not self.skip and tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'blockquote', 'pre', 'div', 'section'):
            self._flush()

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def read_chapter(path, catalog, index):
    if catalog['format'] != 'epub' or not 0 <= index < catalog['total']:
        raise ValueError('Chapter not found.')
    name = catalog['chapters'][index]['path']
    try:
        with zipfile.ZipFile(path) as archive:
            entries = _entries(archive)
            entry = entries.get(name)
            if not entry:
                raise ValueError('Chapter not found.')
            data = _read(archive, entry, MAX_CHAPTER)
    except (zipfile.BadZipFile, zipfile.LargeZipFile) as error:
        raise ValueError('This chapter could not be read.') from error
    # XHTML 1.1 EPUB chapters commonly declare a passive HTML document type.
    # HTMLParser does not fetch external DTDs or execute markup. Still reject
    # entity declarations and internal subsets before parsing any text.
    upper = data.upper()
    if b'<!ENTITY' in upper:
        raise ValueError('Active EPUB content is not supported.')
    declarations = re.findall(br'<!DOCTYPE[^>]*>', upper)
    if b'<!DOCTYPE' in re.sub(br'<!DOCTYPE[^>]*>', b'', upper) or any(
        b'[' in declaration or len(declaration) > 600 or not re.fullmatch(br'<!DOCTYPE\s+HTML(?:\s+[^<>\[\]]+)?\s*>', declaration)
        for declaration in declarations
    ):
        raise ValueError('Active EPUB content is not supported.')
    parser = _ChapterText(name, catalog['assets'])
    parser.feed(data.decode('utf-8', errors='replace'))
    parser._flush()
    return {'title': catalog['chapters'][index]['title'], 'blocks': parser.blocks}


def read_asset(path, catalog, index):
    if not 0 <= index < len(catalog['assets']):
        raise ValueError('Page not found.')
    name = catalog['assets'][index]
    try:
        with zipfile.ZipFile(path) as archive:
            entries = _entries(archive)
            entry = entries.get(name)
            if not entry:
                raise ValueError('Page not found.')
            data = _read(archive, entry, MAX_IMAGE)
    except (zipfile.BadZipFile, zipfile.LargeZipFile) as error:
        raise ValueError('This page could not be read.') from error
    return data, IMAGE_MIMES[Path(name).suffix.lower()]
