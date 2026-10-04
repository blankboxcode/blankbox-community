#!/usr/bin/env python3
"""Publish a selected, qualified Actions image artifact without rebuilding it."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request

POLICY = json.loads(Path(__file__).with_name('current-release.json').read_text())


def selected_run():
    run_id = os.environ.get('BUILD_RUN_ID', '')
    archive_hash = os.environ.get('IMAGE_ARCHIVE_SHA256', '')
    if not re.fullmatch(r'[1-9][0-9]*', run_id) or not re.fullmatch(r'[a-f0-9]{64}', archive_hash):
        raise ValueError('Enter the build run ID and its exact image archive SHA-256.')
    request = urllib.request.Request(
        f'https://api.github.com/repos/{POLICY["repository"]}/actions/runs/{run_id}',
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
                 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        run = json.load(response)
    if (run['event'] != 'workflow_dispatch' or run['conclusion'] != 'success'
            or run['path'] != '.github/workflows/docker-image-build.yml'
            or run['repository']['full_name'] != POLICY['repository']
            or run['head_sha'] != os.environ['GITHUB_SHA']):
        raise ValueError('Select a successful build from this exact repository revision.')
    print('Selected a successful, matching build run.')
    return run_id, archive_hash


def command(*args, **kwargs):
    return subprocess.run(args, text=True, check=True, **kwargs)


def publish(directory):
    run_id, expected = selected_run()
    archive = directory / 'image.tar.gz'
    with archive.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    evidence = json.loads((directory / 'image-build.json').read_text())
    if (digest != expected or evidence['archiveSha256'] != expected
            or evidence['buildRunId'] != run_id
            or evidence['workflowRevision'] != os.environ['GITHUB_SHA']
            or any(evidence.get(k) != v for k, v in POLICY.items())
            or evidence['checks'].get('signedRuntimeMatches') is not True
            or evidence['checks'].get('ready') is not True):
        raise ValueError('Downloaded image artifact does not match the selected qualified build.')
    registry = 'ghcr.io/' + POLICY['repository']
    tag = registry + ':' + POLICY['version']
    command('docker', 'load', '--input', str(archive))
    result = command('docker', 'image', 'inspect', evidence['imageId'], stdout=subprocess.PIPE)
    image = json.loads(result.stdout)[0]
    labels = image['Config']['Labels']
    if (image['Id'] != evidence['imageId'] or image['Os'] + '/' + image['Architecture'] != POLICY['platform']
            or labels.get('org.opencontainers.image.source') != 'https://github.com/' + POLICY['repository']
            or labels.get('org.opencontainers.image.revision') != POLICY['sourceRevision']
            or labels.get('org.blankbox.release.manifest-sha256') != POLICY['manifestSha256']
            or labels.get('org.opencontainers.image.version') != POLICY['version']):
        raise ValueError('Loaded image does not match the approved runtime and source.')
    command('docker', 'login', 'ghcr.io', '--username', os.environ['GITHUB_ACTOR'],
            '--password-stdin', input=os.environ['GH_TOKEN'] + '\n', stdout=subprocess.PIPE)
    try:
        existing = subprocess.run(['docker', 'manifest', 'inspect', tag], text=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if existing.returncode == 0:
            raise ValueError('This version tag already exists. It will not be overwritten.')
        if not any(text in existing.stderr.lower() for text in ('manifest unknown', 'no such manifest', 'name unknown')):
            raise ValueError('Could not establish that the registry tag is unused: ' + existing.stderr)
        command('docker', 'tag', evidence['imageId'], tag)
        pushed = command('docker', 'push', tag, stdout=subprocess.PIPE)
        print(pushed.stdout)
        matches = re.findall(r'digest: (sha256:[a-f0-9]{64})', pushed.stdout)
        if len(matches) != 1:
            raise ValueError('Image was pushed, but its digest could not be recorded. Do not rerun publication.')
        pinned = registry + '@' + matches[0]
        command('docker', 'manifest', 'inspect', pinned, stdout=subprocess.PIPE)
        publication = {**evidence, 'image': pinned, 'versionTag': tag}
        (directory / 'publication.json').write_text(json.dumps(publication, indent=2) + '\n')
        message = (f'Published image: {pinned}\nVersion tag: {tag}\n'
                   'Make the GitHub package Public, then verify an anonymous pull before announcing installation.\n')
        print(message)
        if os.environ.get('GITHUB_STEP_SUMMARY'):
            Path(os.environ['GITHUB_STEP_SUMMARY']).write_text('```text\n' + message + '```\n')
    finally:
        command('docker', 'logout', 'ghcr.io', stdout=subprocess.PIPE)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-run', action='store_true')
    parser.add_argument('--artifact', type=Path)
    args = parser.parse_args()
    if args.check_run:
        selected_run()
    elif args.artifact:
        publish(args.artifact)
    else:
        parser.error('Choose --check-run or --artifact.')
