#!/usr/bin/env python3
"""Activate a signed, digest-pinned image while preserving the existing library."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import uuid

from release_auth import manifest_bytes, verify_signature
from release_files import verify


class UpdateError(RuntimeError):
    pass


def image_descriptor(path, trust):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 16384:
        raise UpdateError('The image descriptor must be a bounded regular file.')
    descriptor = json.loads(path.read_text())
    verify_signature(manifest_bytes(descriptor), descriptor['publisherSignature'], trust)
    if (descriptor.get('format') != 1 or descriptor.get('deliveryRevision') != 1
            or descriptor.get('platform') != 'linux/amd64' or descriptor.get('apiVersion') != 1
            or descriptor.get('repository') != 'blankboxcode/blankbox-community'
            or not re.fullmatch(r'[a-z0-9][a-z0-9.:-]*/[a-z0-9/_.-]+@sha256:[a-f0-9]{64}', descriptor.get('image', ''))
            or not re.fullmatch(r'\d+\.\d+\.\d+(?:-(?:beta|rc)\.\d+)?', descriptor.get('version', ''))
            or not re.fullmatch(r'[a-f0-9]{40}', descriptor.get('sourceRevision', ''))
            or not all(re.fullmatch(r'[a-f0-9]{64}', descriptor.get(k, '')) for k in ('packageSha256', 'manifestSha256'))
            or not isinstance(descriptor.get('catalogSchema'), int)
            or not isinstance(descriptor.get('minimumPackReader'), int)):
        raise UpdateError('Unsupported or malformed signed image descriptor.')
    return descriptor


class Updater:
    def __init__(self, root, descriptor, wait=240):
        self.root = root
        self.descriptor = descriptor
        self.wait = str(wait)
        self.environment = os.environ.copy()
        self.previous = None
        self.user = None
        self.snapshot = None
        self.previous_tag = None

    def run(self, *arguments, capture=True, environment=None):
        result = subprocess.run(arguments, cwd=self.root, env=environment or self.environment,
                                text=True, stdout=subprocess.PIPE if capture else None,
                                stderr=subprocess.PIPE if capture else None)
        if result.returncode:
            message = (result.stderr or result.stdout or '').strip()
            raise UpdateError(f'{arguments[0]} failed: {message}')
        return result.stdout.strip() if capture else ''

    def compose(self, *arguments, image=None, capture=True):
        environment = self.environment.copy()
        if image:
            environment['BLANKBOX_IMAGE'] = image
        return self.run('docker', 'compose', *arguments, environment=environment, capture=capture)

    def inspect(self, target):
        return json.loads(self.run('docker', 'inspect', target))[0]

    def identity(self, image, selected_user):
        arguments = ['docker', 'run', '--rm', '--network', 'none', '--read-only',
                     '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges']
        if selected_user:
            arguments += ['--user', selected_user]
        arguments += ['--entrypoint', 'python3', image, '-c',
                      'import os; u,g=os.getuid(),os.getgid(); '
                      'assert u>0, "Blank Box must run as a non-root user"; print(f"{u}:{g}")']
        result = self.run(*arguments)
        if not re.fullmatch(r'[1-9][0-9]*:[0-9]+', result):
            raise UpdateError('Could not resolve the existing non-root UID/GID.')
        return result

    def config(self, image=None):
        return json.loads(self.compose('config', '--format', 'json', image=image))

    def require_same_mounts(self, config, current):
        desired = {}
        for mount in config['services']['blankbox'].get('volumes', []):
            kind, source, target = mount['type'], mount.get('source'), mount['target']
            if kind == 'volume':
                source = config.get('volumes', {}).get(source, {}).get('name')
            elif kind == 'bind':
                if not source or not Path(source).exists():
                    raise UpdateError('A configured bind folder is missing; no update was activated.')
                source = str(Path(source).resolve())
            else:
                raise UpdateError('Review this unsupported storage mount before updating.')
            desired[target] = (kind, source, bool(mount.get('read_only', False)))
        for category in ('secrets', 'configs'):
            for entry in config['services']['blankbox'].get(category, []):
                name = entry['source']
                source = config.get(category, {}).get(name, {}).get('file')
                if not source or not Path(source).is_file():
                    raise UpdateError('A referenced secret/config file is missing or unsupported; no update was activated.')
                target = entry.get('target') or name
                if not target.startswith('/'):
                    target = ('/run/secrets/' if category == 'secrets' else '/') + target
                desired[target] = ('bind', str(Path(source).resolve()), True)
        existing = {m['Destination']: (m['Type'], m.get('Name') if m['Type'] == 'volume' else m['Source'], not m['RW'])
                    for m in current['Mounts'] if m['Type'] != 'tmpfs'}
        if '/data' not in desired or desired != existing:
            raise UpdateError('The configured storage differs from the running container. Keep the same data, media and backup mounts while updating; no update was activated.')

    def check_image(self):
        candidate = self.descriptor['image']
        self.run('docker', 'pull', '--platform', self.descriptor['platform'], candidate, capture=False)
        image = self.inspect(candidate)
        labels = image['Config'].get('Labels') or {}
        expected = {'org.opencontainers.image.source': 'https://github.com/' + self.descriptor['repository'],
                    'org.opencontainers.image.revision': self.descriptor['sourceRevision'],
                    'org.opencontainers.image.version': self.descriptor['version'],
                    'org.blankbox.release.manifest-sha256': self.descriptor['manifestSha256']}
        if (candidate not in image.get('RepoDigests', [])
                or image['Os'] + '/' + image['Architecture'] != self.descriptor['platform']
                or any(labels.get(k) != v for k, v in expected.items())):
            raise UpdateError('Pulled image does not match the signed release identity.')
        release = json.loads(self.run('docker', 'run', '--rm', '--network', 'none', '--read-only',
                                     '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                                     '--entrypoint', 'python3', candidate, '-c',
                                     'from pathlib import Path; print(Path("/opt/blankbox/RELEASE.json").read_text())'))
        if any(release.get(k) != self.descriptor[k] for k in ('version', 'catalogSchema', 'minimumPackReader')):
            raise UpdateError('Pulled image compatibility differs from the signed descriptor.')

    def prepared_settings(self, image):
        path = self.root / '.env'
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise UpdateError('The local .env must be a regular file.')
        original = path.stat() if path.exists() else self.root.stat()
        text = path.read_text() if path.exists() else ''
        text = ''.join(line for line in text.splitlines(keepends=True)
                       if not re.match(r'^\s*(?:export\s+)?BLANKBOX_(?:IMAGE|UID|GID)\s*=', line))
        if text and not text.endswith('\n'):
            text += '\n'
        uid, gid = self.user.split(':')
        text += f'BLANKBOX_IMAGE={image}\nBLANKBOX_UID={uid}\nBLANKBOX_GID={gid}\n'
        # Prepare outside the signed bundle. Persist only after successful readiness.
        file = tempfile.NamedTemporaryFile(mode='w', dir=self.root.parent,
                                           prefix='.blankbox-settings-', delete=False)
        temporary = Path(file.name)
        try:
            with file:
                file.write(text)
                file.flush()
                os.fsync(file.fileno())
            if os.geteuid() == 0:
                os.chown(temporary, original.st_uid, original.st_gid)
            return temporary
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise

    def ready(self, image):
        self.compose('up', '--detach', '--no-build', '--pull', 'never', '--wait',
                     '--wait-timeout', self.wait, image=image, capture=False)
        ids = self.compose('ps', '--all', '-q', 'blankbox', image=image).splitlines()
        if len(ids) != 1:
            raise UpdateError('Expected one Blank Box container after activation.')
        result = self.inspect(ids[0])
        if result['Image'] != self.inspect(image)['Id'] or result['State'].get('Health', {}).get('Status') != 'healthy':
            raise UpdateError('The expected Blank Box image did not become healthy.')

    def update(self):
        try:
            daemon = json.loads(self.run('docker', 'info', '--format', '{{json .}}'))
        except UpdateError as error:
            raise UpdateError('Cannot access Docker. If Docker commands require sudo on this host, run sudo ./upgrade-docker.sh. Keep Compose settings in .env.\n' + str(error)) from error
        architecture = {'x86_64': 'amd64', 'aarch64': 'arm64'}.get(daemon['Architecture'], daemon['Architecture'])
        if daemon['OSType'] + '/' + architecture != self.descriptor['platform']:
            raise UpdateError('This image is qualified for Linux/amd64; the Docker host has a different platform.')
        self.compose('version')
        ids = self.compose('ps', '--all', '-q', 'blankbox').splitlines()
        if len(ids) != 1:
            raise UpdateError('No single existing Blank Box container was found. Keep the previous container running and use the same Compose project; a new installation uses docker compose up.')
        current = self.inspect(ids[0])
        if not current['State']['Running']:
            raise UpdateError('Start the previous Blank Box container with its existing settings before updating.')
        self.previous = current['Image']
        previous_release = json.loads(self.run('docker', 'run', '--rm', '--network', 'none', '--read-only',
                                             '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                                             '--entrypoint', 'python3', self.previous, '-c',
                                             'from pathlib import Path; print(Path("/opt/blankbox/RELEASE.json").read_text())'))
        if any(previous_release.get(k, 0) > self.descriptor[k] for k in ('catalogSchema', 'minimumPackReader')):
            raise UpdateError('The selected image is older than the current catalog/pack compatibility. Use a paired manual rollback; no update was activated.')
        self.user = self.identity(self.previous, current['Config']['User'])
        uid, gid = self.user.split(':')
        for key, value in [('BLANKBOX_UID', uid), ('BLANKBOX_GID', gid)]:
            if key in os.environ and os.environ[key] != value:
                raise UpdateError('Shell UID/GID settings differ from the running container; no update was activated.')
            self.environment[key] = value
        config = self.config(image=self.previous)
        if config['name'] != current['Config']['Labels'].get('com.docker.compose.project'):
            raise UpdateError('The Compose project differs from the running container.')
        if self.identity(self.previous, config['services']['blankbox'].get('user', '')) != self.user:
            raise UpdateError('The configured user differs from the running container; no update was activated.')
        self.require_same_mounts(config, current)
        self.check_image()  # Network and identity checks finish while the old service is available.
        if self.identity(self.descriptor['image'], config['services']['blankbox'].get('user', '')) != self.user:
            raise UpdateError('The candidate cannot use the existing UID/GID; no update was activated.')
        temporary = self.prepared_settings(self.descriptor['image'])
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        previous_tag = 'blankbox-community:previous-' + timestamp + '-' + uuid.uuid4().hex[:8]
        self.previous_tag = previous_tag
        stopped = False
        try:
            self.run('docker', 'tag', self.previous, previous_tag)
            print(f'Keeping user {self.user} and the existing storage. Pull verified; stopping for a paired snapshot.', flush=True)
            stopped = True
            self.compose('stop', 'blankbox', image=self.previous, capture=False)
            destination = f'/data/upgrades/pre-registry-{timestamp}-{uuid.uuid4().hex[:8]}.sqlite3'
            self.snapshot = self.compose('run', '--rm', '--no-deps', '--pull', 'never',
                                         '--entrypoint', 'python3', 'blankbox', '/opt/blankbox/maintenance.py',
                                         'backup', '--destination', destination, image=self.previous)
            if self.snapshot != destination:
                raise UpdateError('The snapshot tool did not return its expected recovery path.')
            self.ready(self.descriptor['image'])
            os.replace(temporary, self.root / '.env')
        except BaseException:
            if stopped:
                try:
                    if self.snapshot:
                        self.compose('stop', 'blankbox', image=self.descriptor['image'], capture=False)
                        # Candidate maintenance understands both sides of its catalog migration.
                        self.compose('run', '--rm', '--no-deps', '--pull', 'never', '--entrypoint', 'python3',
                                     'blankbox', '/opt/blankbox/maintenance.py', 'restore', '--backup', self.snapshot,
                                     image=self.descriptor['image'], capture=False)
                    self.ready(previous_tag)
                    restored_settings = self.prepared_settings(previous_tag)
                    try:
                        os.replace(restored_settings, self.root / '.env')
                    finally:
                        restored_settings.unlink(missing_ok=True)
                    print('The previous image and its paired catalog were restored.', file=sys.stderr)
                except BaseException as recovery_error:
                    raise UpdateError(f'Recovery did not complete: {recovery_error}\n'
                                      f'Previous image retained: {previous_tag}\n'
                                      f'Paired snapshot: {self.snapshot or "snapshot creation did not finish"}\n'
                                      'The library and images have not been deleted. Inspect Docker logs and keep these recovery files.') from recovery_error
            raise
        finally:
            temporary.unlink(missing_ok=True)
        print(f'Blank Box is ready. Accepted image: {self.descriptor["image"]}\n'
              f'Previous image: {previous_tag}\nPaired pre-update snapshot: {self.snapshot}\n'
              'Keep the previous image and snapshot. Your settings now select the accepted image.')

    def install(self):
        try:
            daemon = json.loads(self.run('docker', 'info', '--format', '{{json .}}'))
        except UpdateError as error:
            raise UpdateError('Cannot access Docker. If Docker requires sudo, run sudo ./setup-docker.sh.\n' + str(error)) from error
        architecture = {'x86_64': 'amd64', 'aarch64': 'arm64'}.get(daemon['Architecture'], daemon['Architecture'])
        if daemon['OSType'] + '/' + architecture != self.descriptor['platform']:
            raise UpdateError('This image requires a Linux/amd64 Docker host.')
        if self.compose('ps', '--all', '-q', 'blankbox'):
            raise UpdateError('A Blank Box container already exists in this project. Use ./upgrade-docker.sh for an existing installation.')
        config = self.config(image=self.descriptor['image'])
        mounts = config['services']['blankbox'].get('volumes', [])
        if any(m['type'] == 'bind' and not Path(m['source']).exists() for m in mounts):
            raise UpdateError('A configured bind folder is missing; no container was started.')
        self.check_image()
        self.user = self.identity(self.descriptor['image'], config['services']['blankbox'].get('user', ''))
        data = [m for m in mounts if m['target'] == '/data']
        if len(data) != 1 or (data[0]['type'] == 'volume' and self.user != '1000:1000'):
            raise UpdateError('For a custom UID/GID, use a correctly owned bind folder at /data.')
        temporary = self.prepared_settings(self.descriptor['image'])
        try:
            self.ready(self.descriptor['image'])
            os.replace(temporary, self.root / '.env')
        finally:
            temporary.unlink(missing_ok=True)
        print('Blank Box is ready. Open your configured address and claim your account using the recovery key in /data/access-key.txt.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trusted-key', type=Path)
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    verify(root, allow_configuration=True, trusted_key=args.trusted_key)
    descriptor = image_descriptor(root / 'image.json', args.trusted_key)
    if args.verify_only:
        print('Verified signed image descriptor:', descriptor['image'])
        return
    updater = Updater(root, descriptor)
    if args.install:
        updater.install()
    else:
        updater.update()


if __name__ == '__main__':
    try:
        main()
    except (UpdateError, ValueError, KeyError, OSError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
