"""Windows audio-CD reader using read-only optical-drive control requests.

This adapter creates lossless PCM WAV files with the Python standard library.
It never writes to the optical drive and does not read protected video content.
"""
from __future__ import annotations

import ctypes
import hashlib
import os
import re
import shutil
import struct
import wave
from contextlib import contextmanager
from pathlib import Path
from disc_id import musicbrainz_disc_id


CDDA_SECTOR_BYTES = 2352
FRAMES_PER_SECOND = 75
READ_CHUNK_FRAMES = 16
IOCTL_CDROM_READ_TOC_EX = 0x00024054
IOCTL_CDROM_RAW_READ = 0x0002403E


def parse_audio_toc(data):
    """Parse a Windows CDROM_TOC response requested in MSF address format."""
    if len(data) < 20:
        raise ValueError('No readable audio-CD track list was found.')
    length = int.from_bytes(data[:2], 'big') + 2
    first, last = data[2], data[3]
    if first != 1 or not 1 <= last <= 99:
        raise ValueError('The disc does not have a supported audio-CD track list.')
    end = 4 + (last + 1) * 8
    if length < end or len(data) < end:
        raise ValueError('The disc returned an incomplete track list.')
    starts = []
    for index in range(last + 1):
        entry = data[4 + index * 8:12 + index * 8]
        if entry[2] != (index + 1 if index < last else 0xAA):
            raise ValueError('The disc returned an inconsistent track list.')
        if index < last and entry[1] & 0x04:
            raise ValueError('This disc contains a data track. Use file import for readable data discs.')
        minute, second, frame = entry[5:8]
        if second >= 60 or frame >= FRAMES_PER_SECOND:
            raise ValueError('The disc returned an invalid track address.')
        starts.append((minute * 60 + second) * FRAMES_PER_SECOND + frame - 150)
    if starts[0] < 0 or starts[-1] > 100 * 60 * FRAMES_PER_SECOND or any(end <= start for start, end in zip(starts, starts[1:])):
        raise ValueError('The disc returned invalid track boundaries.')
    fingerprint = hashlib.sha256(data[2:end]).hexdigest()
    return {'trackCount': last, 'tocFingerprint': fingerprint,
            'ranges': list(zip(starts, starts[1:]))}


def _kernel32():
    if os.name != 'nt':
        raise OSError('Windows optical access is available only on Windows.')
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetLogicalDrives.argtypes = []
    kernel.GetLogicalDrives.restype = wintypes.DWORD
    kernel.GetDriveTypeW.argtypes = [wintypes.LPCWSTR]
    kernel.GetDriveTypeW.restype = wintypes.UINT
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                   ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.DeviceIoControl.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p,
                                       wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                                       ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
    kernel.DeviceIoControl.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    return kernel


def windows_cd_devices():
    if os.name != 'nt':
        return []
    kernel = _kernel32()
    mask = kernel.GetLogicalDrives()
    return [f'{chr(65 + index)}:' for index in range(26)
            if mask & (1 << index) and kernel.GetDriveTypeW(f'{chr(65 + index)}:\\') == 5]


def windows_cd_drive_details():
    details = []
    for device in windows_cd_devices():
        try:
            with _open_drive(device):
                readable = True
        except (OSError, ValueError):
            readable = False
        details.append({'device': device, 'label': f'Optical drive ({device})', 'readable': readable})
    return details


@contextmanager
def _open_drive(device):
    if not isinstance(device, str) or not re.fullmatch(r'[A-Z]:', device) or device not in windows_cd_devices():
        raise ValueError('Choose an available Windows optical drive.')
    kernel = _kernel32()
    handle = kernel.CreateFileW('\\\\.\\' + device, 0x80000000, 3, None, 3, 0, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ValueError('Blank Box cannot read this optical drive. Check drive access and close other disc applications.')
    try:
        yield kernel, handle
    finally:
        kernel.CloseHandle(handle)


def _control(kernel, handle, code, payload, length):
    from ctypes import wintypes
    incoming = ctypes.create_string_buffer(payload) if payload else None
    outgoing = ctypes.create_string_buffer(length)
    returned = wintypes.DWORD()
    success = kernel.DeviceIoControl(handle, code, incoming, len(payload), outgoing,
                                     length, ctypes.byref(returned), None)
    if not success:
        raise OSError(ctypes.get_last_error(), 'The optical drive could not read this disc.')
    return outgoing.raw[:returned.value]


def _toc(kernel, handle):
    # CDROM_READ_TOC_EX_FORMAT_TOC with Msf=1, for unambiguous track positions.
    return parse_audio_toc(_control(kernel, handle, IOCTL_CDROM_READ_TOC_EX,
                                    b'\x80\x00\x00\x00', 804))


def probe_windows_cd(device):
    with _open_drive(device) as (kernel, handle):
        result = _toc(kernel, handle)
    return {'device': device, 'mediaType': 'audio-cd',
            'trackCount': result['trackCount'], 'tocFingerprint': result['tocFingerprint'],
            'discId': musicbrainz_disc_id([start for start, _ in result['ranges']], result['ranges'][-1][1])}


def _read_audio(kernel, handle, lba, frames):
    if lba < 0 or not 1 <= frames <= READ_CHUNK_FRAMES:
        raise ValueError('Invalid audio-CD sector request.')
    payload = struct.pack('<qII', lba * 2048, frames, 2)  # CDDA track mode.
    data = _control(kernel, handle, IOCTL_CDROM_RAW_READ, payload, frames * CDDA_SECTOR_BYTES)
    if len(data) != frames * CDDA_SECTOR_BYTES:
        raise OSError('The optical drive returned an incomplete audio block.')
    return data


def extract_windows_wav(device, expected_fingerprint, expected_tracks, stage, progress=None):
    """Read each audio block twice; reject inconsistent reads instead of hiding errors."""
    stage = Path(stage)
    stage.mkdir(mode=0o700, parents=True, exist_ok=False)
    if shutil.disk_usage(stage).free < 2 * 1024 ** 3:
        raise ValueError('Allow at least 2 GiB of free space for safe temporary extraction.')
    paths = []
    with _open_drive(device) as (kernel, handle):
        toc = _toc(kernel, handle)
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
                            first = _read_audio(kernel, handle, lba, frames)
                            second = _read_audio(kernel, handle, lba, frames)
                        except OSError:
                            if attempt == 2:
                                raise ValueError('The drive could not reliably read this audio CD. No album was added.') from None
                            continue
                        if first == second:
                            output.writeframesraw(first)
                            break
                        if attempt == 2:
                            raise ValueError('The drive returned inconsistent audio. No album was added.')
            paths.append(path)
            if progress:
                progress(index, expected_tracks)
        if _toc(kernel, handle)['tocFingerprint'] != expected_fingerprint:
            raise ValueError('The disc changed during extraction. Nothing was added.')
    return paths
