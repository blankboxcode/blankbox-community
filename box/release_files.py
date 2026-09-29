"""Validate release file inventories without following links."""
import argparse
import hashlib
from pathlib import Path, PurePosixPath
import re
from file_safety import reject_links
from release_auth import verify_signature
import json


def verify(root, allow_configuration=False, trusted_key=None):
    root = reject_links(root)
    manifest = reject_links(root / 'MANIFEST.sha256')
    signature = root / 'MANIFEST.sha256.sig'
    if signature.exists() or (root / 'release-trust.json').exists():
        verify_signature(manifest.read_bytes(), json.loads(reject_links(signature).read_text()), trusted_key)
    recorded = set()
    for line in manifest.read_text(encoding='ascii').splitlines():
        match = re.fullmatch(r'([a-f0-9]{64})  ([A-Za-z0-9_.@/+-]+)', line)
        if not match:
            raise ValueError('Malformed release manifest.')
        relative = PurePosixPath(match[2])
        if relative.is_absolute() or '..' in relative.parts or str(relative) != match[2] or match[2] in recorded:
            raise ValueError('Unsafe or repeated release path.')
        path = reject_links(root / relative)
        if not path.is_file():
            raise ValueError('Missing release file: ' + str(relative))
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1048576), b''):
                digest.update(block)
        if digest.hexdigest() != match[1]:
            raise ValueError('Release checksum mismatch: ' + str(relative))
        recorded.add(match[2])
    ignored = {'MANIFEST.sha256','MANIFEST.sha256.sig'}
    if allow_configuration:
        ignored.update({'.env','compose.override.yaml','compose.override.yml'})
    actual = set()
    for path in root.rglob('*'):
        reject_links(path)
        if '__pycache__' in path.parts:
            continue
        if path.is_file() and path.relative_to(root).as_posix() not in ignored:
            actual.add(path.relative_to(root).as_posix())
    if actual != recorded:
        raise ValueError('Release contains unlisted files.')
    return sorted(recorded)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--allow-configuration', action='store_true')
    parser.add_argument('--trusted-key', type=Path)
    args = parser.parse_args()
    print('Verified', len(verify(args.root, args.allow_configuration, args.trusted_key)), 'release files.')
