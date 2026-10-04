#!/usr/bin/env python3
"""Build and qualify an image using only an approved, signed installation ZIP."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import socket
import stat
import subprocess
import sys
import urllib.request
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'box'))
from release_files import verify


def run(*args, capture=False, **kwargs):
    return subprocess.run(args, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None, **kwargs)


def checksum(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def extract(archive, destination, version):
    prefix = f'blankbox-community-{version}'
    seen = set()
    with zipfile.ZipFile(archive) as source:
        if len(source.infolist()) > 2000 or sum(x.file_size for x in source.infolist()) > 2_000_000_000:
            raise ValueError('Installation archive exceeds the expected bounds.')
        for member in source.infolist():
            name = member.filename.rstrip('/')
            relative = PurePosixPath(name)
            mode = member.external_attr >> 16
            if (not re.fullmatch(r'[A-Za-z0-9_.@/+-]+', name)
                    or relative.is_absolute() or '..' in relative.parts
                    or str(relative) != name or relative.parts[0] != prefix
                    or name in seen or stat.S_ISLNK(mode)):
                raise ValueError('Unsafe or repeated installation archive member.')
            seen.add(name)
            target = destination / relative
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as output, source.open(member) as input_file:
                    shutil.copyfileobj(input_file, output)
                target.chmod(0o755 if mode & 0o111 else 0o644)
    return destination / prefix


def qualify(image, package):
    """Compare the image's application bytes and exercise an isolated fresh library."""
    inventory = run('docker', 'run', '--rm', '--network', 'none', '--read-only',
                    '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                    '--entrypoint', 'python3', image, '-c',
                    'import hashlib,json; from pathlib import Path; '
                    'r=Path("/opt/blankbox"); '
                    'print(json.dumps({str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() '
                    'for p in r.rglob("*") if p.is_file()}))', capture=True)
    files = json.loads(inventory.stdout)
    if not {'server.py', 'RELEASE.json', 'release-trust.json', 'web/index.html'} <= files.keys():
        raise ValueError('Image is missing the reviewed runtime.')
    for relative, digest in files.items():
        expected = package / relative
        if not expected.is_file() or checksum(expected) != digest:
            raise ValueError('Image file differs from the signed installation: ' + relative)
        if any(part in {'.git', 'docs', 'candidates', 'community-support', '__pycache__'} for part in Path(relative).parts):
            raise ValueError('Unexpected development files in the application image.')
    project = 'blankboximagecheck' + uuid.uuid4().hex[:12]
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    # Do not inherit another installation's Compose files, user, image or secrets.
    environment = {k: v for k, v in os.environ.items()
                   if not k.startswith(('BLANKBOX_', 'COMPOSE_'))}
    environment.update(COMPOSE_PROJECT_NAME=project, BLANKBOX_IMAGE=image,
                       BLANKBOX_PUBLISHED_PORT=str(port))
    def compose(*args, capture=False):
        return run('docker', 'compose', *args, cwd=package, env=environment, capture=capture)
    try:
        compose('up', '--detach', '--no-build', '--pull', 'never', '--wait', '--wait-timeout', '240')
        container = compose('ps', '-q', 'blankbox', capture=True).stdout.strip()
        check = ('import os,json; from pathlib import Path; '
                 'assert (os.getuid(),os.getgid())==(1000,1000); '
                 'assert Path("/data/access-key.txt").stat().st_uid==1000; '
                 'from metadata_indexed_pack import public_distribution; '
                 'assert public_distribution(); '
                 'print(json.dumps({"uid":os.getuid(),"gid":os.getgid(),"publicPackPolicy":True}))')
        run('docker', 'exec', container, 'python3', '-c', check)
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/health/ready', timeout=5) as response:
            if response.status != 200:
                raise ValueError('Image did not become ready.')
        runtime = json.loads(run('docker', 'inspect', container, capture=True).stdout)[0]
        host = runtime['HostConfig']
        if not host['ReadonlyRootfs'] or host['Privileged'] or host['CapDrop'] != ['ALL']:
            raise ValueError('Container restrictions were not retained.')
        return {'ready': True, 'defaultUser': '1000:1000', 'runtimeFiles': len(files),
                'signedRuntimeMatches': True, 'publicPackPolicy': True}
    finally:
        compose('down', '--volumes', '--remove-orphans')  # Only this unique test project.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--package', type=Path, help='Use an already downloaded installation ZIP.')
    args = parser.parse_args()
    policy = json.loads(Path(__file__).with_name('current-release.json').read_text())
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    archive = args.package.resolve() if args.package else output / 'installation.zip'
    if not args.package:
        url = (f'https://github.com/{policy["repository"]}/releases/download/'
               f'v{policy["version"]}/blankbox-community-{policy["version"]}.zip')
        with urllib.request.urlopen(url, timeout=60) as source, archive.open('xb') as target:
            shutil.copyfileobj(source, target)
    if checksum(archive) != policy['packageSha256']:
        raise ValueError('Installation ZIP does not match the approved release.')
    package = extract(archive, output, policy['version'])
    verify(package, trusted_key=ROOT / 'box/release-trust.json')
    if checksum(package / 'MANIFEST.sha256') != policy['manifestSha256']:
        raise ValueError('Installation manifest does not match the approved release.')
    release = json.loads((package / 'RELEASE.json').read_text())
    if (release['version'] != policy['version'] or release['platform'] != 'linux-docker'
            or any(release[k] != policy[k] for k in ('catalogSchema', 'minimumPackReader'))):
        raise ValueError('Installation compatibility does not match the approved release.')
    image = f'blankbox-community:review-{policy["version"]}'
    labels = {'org.opencontainers.image.source': 'https://github.com/' + policy['repository'],
              'org.opencontainers.image.revision': policy['sourceRevision'],
              'org.opencontainers.image.version': policy['version'],
              'org.blankbox.release.manifest-sha256': policy['manifestSha256']}
    command = ['docker', 'build', '--platform', policy['platform'], '--provenance=false', '--tag', image]
    for name, value in labels.items():
        command.extend(['--label', f'{name}={value}'])
    command.extend(['--file', str(package / 'Dockerfile'), str(package)])
    run(*command)
    checks = qualify(image, package)
    info = json.loads(run('docker', 'image', 'inspect', image, capture=True).stdout)[0]
    if info['Os'] + '/' + info['Architecture'] != policy['platform']:
        raise ValueError('Built image has the wrong platform.')
    tar = output / 'image.tar.gz'
    process = subprocess.Popen(['docker', 'save', image], stdout=subprocess.PIPE)
    with tar.open('xb') as target, gzip.GzipFile(filename='', fileobj=target, mode='wb', mtime=0) as zipped:
        shutil.copyfileobj(process.stdout, zipped)
    process.stdout.close()
    if process.wait() != 0:
        raise ValueError('Could not save the qualified image.')
    evidence = {**policy, 'imageId': info['Id'], 'localTag': image,
                'archiveSha256': checksum(tar), 'checks': checks,
                'buildRunId': os.environ.get('GITHUB_RUN_ID'),
                'workflowRevision': os.environ.get('GITHUB_SHA')}
    (output / 'image-build.json').write_text(json.dumps(evidence, indent=2) + '\n')
    message = (f'Build run ID: {evidence["buildRunId"] or "local"}\n'
               f'Image archive SHA-256: {evidence["archiveSha256"]}\n'
               f'Image ID: {evidence["imageId"]}\n'
               'The image is tested and saved. Nothing has been published.\n')
    print(message)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        Path(os.environ['GITHUB_STEP_SUMMARY']).write_text('```text\n' + message + '```\n')


if __name__ == '__main__':
    main()
