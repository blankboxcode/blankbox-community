"""Bounded, private owner artwork. No remote image fetches or image dependencies."""
from __future__ import annotations

import hashlib
from pathlib import Path

MAX_ARTWORK_BYTES = 512 * 1024
MAX_INPUT_BYTES = 12 * 1024 * 1024
MAX_DIMENSION = 1800
FOLDER_ART_NAMES = ('cover.jpg', 'cover.jpeg', 'cover.png', 'cover.webp',
                    'folder.jpg', 'folder.jpeg', 'folder.png', 'folder.webp',
                    'poster.jpg', 'poster.jpeg', 'poster.png', 'poster.webp')


def jpeg_size(data: bytes) -> tuple[int, int]:
    """Accept an encoded, metadata-free JPEG within the cover limits."""
    if not isinstance(data, bytes) or not 4 <= len(data) <= MAX_ARTWORK_BYTES or data[:2] != b'\xff\xd8' or data[-2:] != b'\xff\xd9':
        raise ValueError('Cover must be a JPEG smaller than 512 KB.')
    offset = 2
    dimensions = None
    while offset < len(data) - 2:
        if data[offset] != 0xff:
            raise ValueError('Cover JPEG is damaged.')
        while offset < len(data) and data[offset] == 0xff:
            offset += 1
        if offset >= len(data):
            break
        marker = data[offset]
        offset += 1
        if marker == 0xda:  # Compressed scan follows; never parse image data as markers.
            break
        if marker in (0x01, 0xd8, 0xd9) or 0xd0 <= marker <= 0xd7:
            continue
        if offset + 2 > len(data):
            raise ValueError('Cover JPEG is damaged.')
        length = int.from_bytes(data[offset:offset + 2], 'big')
        if length < 2 or offset + length > len(data):
            raise ValueError('Cover JPEG is damaged.')
        if 0xe1 <= marker <= 0xef or marker == 0xfe:
            raise ValueError('Remove embedded photo metadata before uploading this cover.')
        if marker in (0xc0, 0xc1, 0xc2):
            if length < 8:
                raise ValueError('Cover JPEG is damaged.')
            height = int.from_bytes(data[offset + 3:offset + 5], 'big')
            width = int.from_bytes(data[offset + 5:offset + 7], 'big')
            if not 1 <= width <= MAX_DIMENSION or not 1 <= height <= MAX_DIMENSION:
                raise ValueError('Cover dimensions must be at most 1800 pixels on each side.')
            dimensions = (width, height)
        offset += length
    if dimensions is None:
        raise ValueError('Cover JPEG has no image dimensions.')
    return dimensions


def artwork_url(item_id: str, sha256: str) -> str:
    return f'/api/artwork/{item_id}/{sha256[:16]}'


def artwork_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def folder_cover_paths(directory: Path, stem: str):
    """Check only conventional names beside one known media file."""
    names = (*FOLDER_ART_NAMES, *(f'{stem}{suffix}' for suffix in ('.jpg', '.jpeg', '.png', '.webp')))
    seen = set()
    for name in names:
        if name.casefold() in seen:
            continue
        seen.add(name.casefold())
        candidate = directory / name
        try:
            if candidate.is_file() and not candidate.is_symlink() and 0 < candidate.stat().st_size <= MAX_INPUT_BYTES:
                yield candidate
        except OSError:
            continue
