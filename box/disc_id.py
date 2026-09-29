"""Standard MusicBrainz Disc ID from a real audio-CD table of contents.

Inputs are track and lead-out LBA positions, not Blank Box's SHA-256
tocFingerprint. The 150-frame lead-in is applied only for the Disc ID.
"""
from __future__ import annotations

import base64
import hashlib


def musicbrainz_disc_id(track_lbas: list[int], leadout_lba: int, first_track: int = 1) -> str:
    if (not isinstance(first_track, int) or isinstance(first_track, bool) or not 1 <= first_track <= 99 or
            not 1 <= len(track_lbas) <= 100 - first_track or
            any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in track_lbas) or
            not isinstance(leadout_lba, int) or isinstance(leadout_lba, bool) or
            any(right <= left for left, right in zip(track_lbas, track_lbas[1:])) or
            leadout_lba <= track_lbas[-1]):
        raise ValueError('Invalid audio-CD TOC for a MusicBrainz Disc ID.')
    last_track = first_track + len(track_lbas) - 1
    offsets = [leadout_lba + 150, *([0] * (first_track - 1)),
               *[lba + 150 for lba in track_lbas], *([0] * (100 - first_track - len(track_lbas)))]
    payload = f'{first_track:02X}{last_track:02X}' + ''.join(f'{offset:08X}' for offset in offsets)
    encoded = base64.b64encode(hashlib.sha1(payload.encode('ascii')).digest()).decode('ascii')
    return encoded.replace('+', '.').replace('/', '_').replace('=', '-')
