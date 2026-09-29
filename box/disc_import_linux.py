"""Read-only Linux audio-CD access using the kernel's CD-ROM ioctl interface.

This path requires no CD-ripping executable or online service. Matching reads
are a consistency check, not independent proof that a damaged disc was read
accurately. It never writes to the optical device.
"""
from __future__ import annotations

import ctypes
import hashlib
import os
import re
import shutil
import stat
import wave
from contextlib import contextmanager
from pathlib import Path
from disc_id import musicbrainz_disc_id


CDROMREADTOCHDR = 0x5305
CDROMREADTOCENTRY = 0x5306
CDROMREADAUDIO = 0x530E
CDROM_LBA = 0x01
CDROM_LEADOUT = 0xAA
CDDA_SECTOR_BYTES = 2352
READ_CHUNK_FRAMES = 16


class _Address(ctypes.Union):
    _fields_ = [('lba', ctypes.c_int), ('msf', ctypes.c_ubyte * 4)]


class _TocHeader(ctypes.Structure):
    _fields_ = [('first', ctypes.c_ubyte), ('last', ctypes.c_ubyte)]


class _TocEntry(ctypes.Structure):
    _fields_ = [('track', ctypes.c_ubyte), ('adr_ctrl', ctypes.c_ubyte),
                ('format', ctypes.c_ubyte), ('address', _Address),
                ('data_mode', ctypes.c_ubyte)]


class _ReadAudio(ctypes.Structure):
    _fields_ = [('address', _Address), ('format', ctypes.c_ubyte),
                ('frames', ctypes.c_int), ('buffer', ctypes.POINTER(ctypes.c_ubyte))]


@contextmanager
def _open_drive(device):
    if os.name != 'posix' or not isinstance(device, str) or not re.fullmatch(r'/dev/sr\d+', device):
        raise ValueError('Choose an available Linux optical drive.')
    try:
        info = os.stat(device, follow_symlinks=False)
        if not stat.S_ISBLK(info.st_mode):
            raise ValueError('Choose an available Linux optical drive.')
        descriptor = os.open(device, os.O_RDONLY | getattr(os, 'O_CLOEXEC', 0) | getattr(os, 'O_NONBLOCK', 0))
    except OSError as error:
        raise ValueError('Blank Box cannot read this optical drive. Check its permissions and inserted disc.') from error
    try:
        yield descriptor
    finally:
        os.close(descriptor)


def _request(descriptor, code, record):
    libc = ctypes.CDLL(None, use_errno=True)
    libc.ioctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_void_p]
    libc.ioctl.restype = ctypes.c_int
    if libc.ioctl(descriptor, code, ctypes.byref(record)) < 0:
        raise OSError(ctypes.get_errno(), 'The optical drive could not read this disc.')


def _toc(descriptor):
    header = _TocHeader()
    _request(descriptor, CDROMREADTOCHDR, header)
    if header.first != 1 or not 1 <= header.last <= 99:
        raise ValueError('The disc does not have a supported audio-CD track list.')
    starts = []
    identity = bytearray((header.first, header.last))
    for track in [*range(1, header.last + 1), CDROM_LEADOUT]:
        entry = _TocEntry()
        entry.track = track
        entry.format = CDROM_LBA
        _request(descriptor, CDROMREADTOCENTRY, entry)
        if track != CDROM_LEADOUT and (entry.adr_ctrl >> 4) & 0x04:
            raise ValueError('This disc contains a data track. Use file import for readable data discs.')
        lba = int(entry.address.lba)
        starts.append(lba)
        identity.extend(bytes((track, entry.adr_ctrl)))
        identity.extend(lba.to_bytes(4, 'little', signed=True))
    if starts[0] < 0 or starts[-1] > 100 * 60 * 75 or any(end <= start for start, end in zip(starts, starts[1:])):
        raise ValueError('The disc returned invalid track boundaries.')
    return {'trackCount': header.last, 'tocFingerprint': hashlib.sha256(identity).hexdigest(),
            'ranges': list(zip(starts, starts[1:]))}


def probe_linux_cd(device):
    with _open_drive(device) as descriptor:
        toc = _toc(descriptor)
    return {'device': device, 'mediaType': 'audio-cd',
            'trackCount': toc['trackCount'], 'tocFingerprint': toc['tocFingerprint'],
            'discId': musicbrainz_disc_id([start for start, _ in toc['ranges']], toc['ranges'][-1][1])}


def _read_audio(descriptor, lba, frames):
    if lba < 0 or not 1 <= frames <= READ_CHUNK_FRAMES:
        raise ValueError('Invalid audio-CD sector request.')
    data = (ctypes.c_ubyte * (frames * CDDA_SECTOR_BYTES))()
    request = _ReadAudio()
    request.address.lba = lba
    request.format = CDROM_LBA
    request.frames = frames
    request.buffer = ctypes.cast(data, ctypes.POINTER(ctypes.c_ubyte))
    _request(descriptor, CDROMREADAUDIO, request)
    return bytes(data)


def extract_linux_wav(device, expected_fingerprint, expected_tracks, stage, progress=None):
    """Write staged PCM WAV tracks only when read consistency and TOC checks pass."""
    stage = Path(stage)
    stage.mkdir(mode=0o700, parents=True, exist_ok=False)
    if shutil.disk_usage(stage).free < 2 * 1024 ** 3:
        raise ValueError('Allow at least 2 GiB of free space for safe temporary extraction.')
    paths = []
    with _open_drive(device) as descriptor:
        toc = _toc(descriptor)
        if toc['tocFingerprint'] != expected_fingerprint or toc['trackCount'] != expected_tracks:
            raise ValueError('The disc changed before extraction. Nothing was added.')
        for index, (start, end) in enumerate(toc['ranges'], 1):
            path = stage / f'track{index:02d}.wav'
            with wave.open(str(path), 'wb') as output:
                output.setnchannels(2)
                output.setsampwidth(2)
                output.setframerate(44100)
                for lba in range(start, end, READ_CHUNK_FRAMES):
                    frames = min(READ_CHUNK_FRAMES, end - lba)
                    for attempt in range(3):
                        try:
                            first = _read_audio(descriptor, lba, frames)
                            second = _read_audio(descriptor, lba, frames)
                        except OSError:
                            if attempt == 2:
                                raise ValueError('The optical drive could not read audio sectors. Try another drive, cable, or disc. No album was added.') from None
                            continue
                        if first == second:
                            output.writeframesraw(first)
                            break
                        if attempt == 2:
                            raise ValueError('The drive returned inconsistent audio. No album was added.')
            paths.append(path)
            if progress:
                progress(index, expected_tracks)
        if _toc(descriptor)['tocFingerprint'] != expected_fingerprint:
            raise ValueError('The disc changed during extraction. Nothing was added.')
    return paths
