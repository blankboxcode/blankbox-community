"""Read-only audio-CD import for Linux and Windows. No protected-video copying."""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import subprocess
import time
from pathlib import Path


TRACK_LINE = re.compile(r'^\s*(\d+)\.\s+\d+\s+\[\d{1,3}:\d{2}\.\d{2}\]', re.MULTILINE)
TOC_TRACK_LINE = re.compile(r'^\s*(\d+)\.\s+(\d+)\s+\[\d{1,3}:\d{2}\.\d{2}\]\s+(\d+)\s+\[\d{1,3}:\d{2}\.\d{2}\]', re.MULTILINE)
TOC_TOTAL_LINE = re.compile(r'^TOTAL\s+(\d+)\s+\[', re.MULTILINE)
MAX_TRACKS = 99
STAGING_MARKER = '.blankbox-disc-import-stage-v1'


class DiscImportError(ValueError):
    pass


def cleanup_stale_stages(data_root, max_age_seconds=24 * 60 * 60):
    """Remove only marked, expired import scratch dirs. Never touch source media."""
    root = Path(data_root).resolve()
    removed = 0
    for path in root.glob('blankbox-disc-*'):
        marker = path / STAGING_MARKER
        try:
            if path.is_symlink() or not path.is_dir() or path.resolve().parent != root:
                continue
            if marker.is_symlink() or not marker.is_file() or marker.read_text(encoding='ascii') != STAGING_MARKER:
                continue
            if time.time() - path.stat().st_mtime < max_age_seconds:
                continue
            shutil.rmtree(path)
            removed += 1
        except (OSError, UnicodeError):
            continue
    return removed


def audio_cd_devices():
    """Only kernel optical block devices, never arbitrary user-supplied paths."""
    if os.name == 'nt':
        from disc_import_windows import windows_cd_devices
        return windows_cd_devices()
    if os.name != 'posix' or not Path('/sys/class/block').is_dir():
        return []
    found = []
    for path in sorted(Path('/dev').glob('sr[0-9]*')):
        if not re.fullmatch(r'sr\d+', path.name):
            continue
        try:
            if stat.S_ISBLK(path.stat().st_mode) and not path.is_symlink():
                found.append(str(path))
        except OSError:
            continue
    return found


def audio_cd_drive_details():
    """Human-readable labels for available optical drives."""
    if os.name == 'nt':
        from disc_import_windows import windows_cd_drive_details
        return windows_cd_drive_details()
    details = []
    for device in audio_cd_devices():
        block = Path('/sys/class/block') / Path(device).name / 'device'
        parts = []
        for field in ('vendor', 'model'):
            try:
                value = (block / field).read_text(encoding='utf-8').strip()
                if value:
                    parts.append(value)
            except OSError:
                pass
        details.append({'device': device, 'label': f"{' '.join(parts) or 'Optical drive'} ({device})",
                        'readable': os.access(device, os.R_OK)})
    return details


def tool_status():
    return {'cdparanoia': bool(shutil.which('cdparanoia')), 'flac': bool(shutil.which('flac'))}


def require_device(device):
    if not isinstance(device, str) or os.name == 'posix' and not re.fullmatch(r'/dev/sr\d+', device):
        raise DiscImportError('Choose an available optical drive.')
    # Some USB optical drives briefly leave /dev after a TOC query. Keep the
    # allowlist check, but permit a bounded re-enumeration before giving up.
    deadline = time.monotonic() + 15
    was_missing = False
    while True:
        if device in audio_cd_devices():
            if was_missing:
                time.sleep(2)  # Let the reconnected drive finish media detection.
            return device
        was_missing = True
        if time.monotonic() >= deadline:
            raise DiscImportError('Choose an available optical drive.')
        time.sleep(0.25)


def disc_id_from_cdparanoia(output):
    """Use the actual TOC offsets reported by cdparanoia, never a fingerprint."""
    from disc_id import musicbrainz_disc_id
    rows = [(int(track), int(length), int(start)) for track, length, start in TOC_TRACK_LINE.findall(output)]
    total = TOC_TOTAL_LINE.search(output)
    if not total or not rows or [row[0] for row in rows] != list(range(1, len(rows) + 1)):
        raise DiscImportError('The audio-CD TOC lacks the offsets required for a Disc ID.')
    starts = [row[2] for row in rows]
    leadout = int(total.group(1))
    if any(start + length != end for (_, length, start), end in zip(rows, [*starts[1:], leadout])):
        raise DiscImportError('The audio-CD TOC returned inconsistent track offsets.')
    return musicbrainz_disc_id(starts, leadout)


def probe_audio_cd(device):
    device = require_device(device)
    if os.name == 'nt':
        from disc_import_windows import probe_windows_cd
        try:
            return probe_windows_cd(device)
        except (OSError, ValueError) as error:
            raise DiscImportError(str(error)) from error
    from disc_import_linux import probe_linux_cd
    try:
        return probe_linux_cd(device)
    except (OSError, ValueError) as native_error:
        if not shutil.which('cdparanoia'):
            raise DiscImportError(str(native_error)) from native_error
    for attempt in range(3):
        if attempt:
            require_device(device)
        try:
            result = subprocess.run(
                ['cdparanoia', '-d', device, '-Q'], capture_output=True, text=True,
                timeout=30, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            if attempt == 2:
                raise DiscImportError('The drive could not read the disc table of contents.') from error
            time.sleep(2)
            continue
        output = (result.stdout + result.stderr)[:64 * 1024]
        toc_lines = [line.strip() for line in output.splitlines() if TRACK_LINE.match(line)]
        tracks = [int(value) for value in TRACK_LINE.findall(output)]
        if result.returncode == 0 and tracks and tracks == list(range(1, len(tracks) + 1)) and len(tracks) <= MAX_TRACKS:
            break
        if attempt == 2:
            raise DiscImportError('No readable audio-CD track list was found. Data and video discs use other import paths.')
        time.sleep(2)
    identified = {}
    try:
        identified = {'discId': disc_id_from_cdparanoia(output)}
    except (DiscImportError, ValueError):
        pass  # Existing import still works when a drive omits usable offsets.
    return {'device': device, 'mediaType': 'audio-cd', 'trackCount': len(tracks),
            'tocFingerprint': hashlib.sha256('\n'.join(toc_lines).encode()).hexdigest(), **identified}


def extract_flac(device, expected_tracks, stage, album, artist, track_titles, progress=None):
    """Return staged FLAC paths. A successful FLAC -V verifies encoding, not disc accuracy."""
    require_device(device)
    if not all(tool_status().values()):
        raise DiscImportError('Audio CD import needs cdparanoia and flac installed on this Linux host.')
    stage = Path(stage)
    stage.mkdir(mode=0o700, parents=True, exist_ok=False)
    if shutil.disk_usage(stage).free < 2 * 1024 ** 3:
        raise DiscImportError('Allow at least 2 GiB of free space for safe temporary extraction.')
    try:
        with open(stage / 'rip.stderr', 'wb') as diagnostic:
            rip = subprocess.run(
                ['cdparanoia', '-d', device, '-B', '-w', '-X', '-l', 'extraction.log'],
                cwd=stage, stdout=subprocess.DEVNULL, stderr=diagnostic, timeout=7200, check=False,
            )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise DiscImportError('Disc extraction did not finish. No album was added.') from error
    if rip.returncode:
        with open(stage / 'rip.stderr', 'rb') as diagnostic:
            diagnostic.seek(max(0, diagnostic.seek(0, os.SEEK_END) - 32768))
            tail = diagnostic.read()
        if b'No such device' in tail:
            raise DiscImportError('The optical drive disconnected while reading. Try another drive or cable. No album was added.')
        raise DiscImportError('Disc extraction reported an error. No album was added.')
    numbered = []
    for path in stage.glob('track*.cdda.wav'):
        match = re.fullmatch(r'track(\d+)\.cdda\.wav', path.name)
        if match:
            numbered.append((int(match.group(1)), path))
    numbered.sort(key=lambda pair: pair[0])
    wavs = [path for _, path in numbered]
    if ([number for number, _ in numbered] != list(range(1, expected_tracks + 1))
            or any(not path.is_file() or path.stat().st_size < 44 for path in wavs)):
        raise DiscImportError('The extracted track count did not match the disc. No album was added.')
    return encode_flac(wavs, stage, album, artist, track_titles, progress)


def encode_flac(wavs, stage, album, artist, track_titles, progress=None):
    """Encode staged WAV tracks and verify the resulting FLAC bitstreams."""
    encoded = []
    for index, wav in enumerate(wavs, 1):
        target = stage / f'track{index:02d}.flac'
        try:
            result = subprocess.run(
                ['flac', '-V', '-5', '--no-delete-input-file',
                 '-T', f'ALBUM={album}', '-T', f'ARTIST={artist}',
                 '-T', f'TITLE={track_titles[index - 1]}', '-T', f'TRACKNUMBER={index}',
                 '-o', str(target), str(wav)],
                capture_output=True, text=True, timeout=1800, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise DiscImportError(f'FLAC verification failed for track {index}. No album was added.') from error
        if result.returncode or not target.is_file() or not target.stat().st_size:
            raise DiscImportError(f'FLAC verification failed for track {index}. No album was added.')
        encoded.append(target)
        if progress:
            progress(index, len(wavs))
    return encoded


def extract_audio_cd(device, fingerprint, expected_tracks, stage, album, artist, track_titles, progress=None):
    """Return (files, format, mime, extraction method) for a supported host."""
    if os.name == 'nt':
        from disc_import_windows import extract_windows_wav
        try:
            paths = extract_windows_wav(device, fingerprint, expected_tracks, stage, progress)
        except (OSError, ValueError) as error:
            raise DiscImportError(str(error)) from error
        return paths, 'WAV', 'audio/wav', 'windows-cdda'
    from disc_import_linux import extract_linux_wav, probe_linux_cd
    try:
        native = probe_linux_cd(device)
    except (OSError, ValueError):
        native = None
    if native and native['tocFingerprint'] == fingerprint:
        try:
            paths = extract_linux_wav(device, fingerprint, expected_tracks, stage, None if shutil.which('flac') else progress)
        except (OSError, ValueError) as error:
            raise DiscImportError(str(error)) from error
        if shutil.which('flac'):
            return encode_flac(paths, stage, album, artist, track_titles, progress), 'FLAC', 'audio/flac', 'linux-cdda'
        return paths, 'WAV', 'audio/wav', 'linux-cdda'
    if not all(tool_status().values()):
        raise DiscImportError('The drive cannot use native CD reads and optional cdparanoia/FLAC tools are unavailable.')
    if probe_audio_cd(device)['tocFingerprint'] != fingerprint:
        raise DiscImportError('The disc changed before extraction. Nothing was added.')
    paths = extract_flac(device, expected_tracks, stage, album, artist, track_titles, progress)
    if probe_audio_cd(device)['tocFingerprint'] != fingerprint:
        raise DiscImportError('The disc changed during extraction. Nothing was added.')
    return paths, 'FLAC', 'audio/flac', 'cdparanoia'
