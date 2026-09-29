#!/usr/bin/env python3
"""Offline catalog lifecycle helpers for Blank Box installers."""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import shutil
import time
import uuid
from pathlib import Path

from server import load_runtime_config
from file_safety import reject_links, checked_copy, digest
from runtime_lock import RuntimeLock


def resolved_data(config):
    return Path(load_runtime_config(config)['data']).expanduser().resolve()


def verify_catalog(path, *, immutable=False):
    path=Path(path).resolve()
    if not path.is_file():raise ValueError(f'Catalog does not exist: {path}')
    # A frozen backup can be verified on storage where SQLite cannot create
    # journal sidecars. A live catalog must still include its WAL transactions.
    with sqlite3.connect(path.as_uri()+('?mode=ro&immutable=1' if immutable else '?mode=ro'),uri=True) as db:
        result=db.execute('PRAGMA integrity_check').fetchone()[0]
    if result!='ok':raise ValueError(f'Catalog integrity check failed: {result}')


ASSET_NAMES = ('metadata-packs', 'metadata-pack-catalog', 'bundled-metadata-receipt.json')


def snapshot_assets(data, destination, progress=None):
    directory = destination.with_name(destination.name + '.assets')
    directory.mkdir(mode=0o700)
    files=[]
    for name in ASSET_NAMES:
        source = reject_links(Path(data) / name)
        if source.is_dir():
            (directory / name).mkdir(mode=0o700)
            for path in source.rglob('*'):
                reject_links(path)
                if path.is_file():
                    files.append((path,directory / name / path.relative_to(source)))
        elif source.is_file():
            files.append((source,directory / name))
    for index,(source,target) in enumerate(files,1):
        checked_copy(source,target,digest(source))
        if progress:progress(index,len(files))
    hashes = {p.relative_to(directory).as_posix(): digest(p) for p in directory.rglob('*') if p.is_file()}
    (directory / 'inventory.json').write_text(json.dumps(hashes, sort_keys=True) + '\n')
    return directory


def backup_catalog(data, destination):
    source = reject_links(Path(data) / 'catalog.sqlite3')
    destination = reject_links(destination)
    if not source.is_file():
        return None
    verify_catalog(source)
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if destination.exists() or destination.with_name(destination.name + '.assets').exists():
        raise ValueError(f'Backup already exists: {destination}')
    temporary = destination.with_name('.' + destination.name + '.' + uuid.uuid4().hex + '.partial')
    temporary_created = False
    try:
        descriptor=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        os.close(descriptor);temporary_created=True
        with sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True) as current, sqlite3.connect(temporary) as saved:
            current.backup(saved)
        verify_catalog(temporary)
        os.chmod(temporary, 0o600)
        snapshot_assets(data, destination)
        checked_copy(temporary, destination, digest(temporary))
        return destination
    finally:
        if temporary_created:temporary.unlink(missing_ok=True)


def restore_assets(data, backup):
    directory = reject_links(backup.with_name(backup.name + '.assets'))
    if not directory.is_dir():
        # Historical snapshots did not include packs. Never guess a compatible set.
        if any((data / name).exists() for name in ASSET_NAMES):
            raise ValueError('This historical snapshot has no paired pack files. Recover its matching packs separately.')
        return
    hashes = json.loads((directory / 'inventory.json').read_text())
    expected = {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file() and p.name != 'inventory.json'}
    if expected != set(hashes):
        raise ValueError('Recovery pack inventory differs from its snapshot.')
    for name, sha in hashes.items():
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts or relative.parts[0] not in ASSET_NAMES:
            raise ValueError('Unsafe recovery asset path.')
        if digest(reject_links(directory / relative)) != sha:
            raise ValueError('Recovery pack checksum failed.')
    stage = data / ('.restore-assets-' + uuid.uuid4().hex)
    stage.mkdir(mode=0o700)
    for name, sha in hashes.items():
        checked_copy(directory / name, stage / name, sha)
    for name in ASSET_NAMES:
        if (directory / name).is_dir():
            (stage / name).mkdir(mode=0o700, exist_ok=True)
    retained = data / 'upgrades' / ('before-assets-' + uuid.uuid4().hex)
    retained.mkdir(mode=0o700, parents=True)
    changed = []
    try:
        for name in ASSET_NAMES:
            target = reject_links(data / name)
            if target.exists():
                os.rename(target, retained / name)
            changed.append(name)
            if (stage / name).exists():
                os.rename(stage / name, target)
    except BaseException:
        for name in reversed(changed):
            if (data / name).exists():
                os.rename(data / name, stage / name)
            if (retained / name).exists():
                os.rename(retained / name, data / name)
        raise
    finally:
        if not any(stage.iterdir()):
            stage.rmdir()


def restore_catalog(data,backup):
    data=reject_links(data);backup=reject_links(backup).resolve();verify_catalog(backup,immutable=True);data.mkdir(mode=0o700,parents=True,exist_ok=True)
    target=reject_links(data/'catalog.sqlite3');temporary=data/('.catalog-restore-'+uuid.uuid4().hex+'.partial')
    temporary_created=False
    try:
        descriptor=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        os.close(descriptor);temporary_created=True
        if target.exists():
            backup_catalog(data,data/'upgrades'/('pre-restore-'+uuid.uuid4().hex+'.sqlite3'))
        for suffix in ('-wal','-shm'):reject_links(target.with_name(target.name+suffix))
        with sqlite3.connect(backup.as_uri()+'?mode=ro&immutable=1',uri=True) as saved,sqlite3.connect(temporary) as restored:saved.backup(restored)
        verify_catalog(temporary);os.chmod(temporary,0o600)
        journal=reject_links(data/'.restore-in-progress.json')
        journal.write_text(json.dumps({'backup':str(backup),'catalogSha256':digest(backup)})+'\n')
        restore_assets(data,backup)
        for suffix in ('-wal','-shm'):target.with_name(target.name+suffix).unlink(missing_ok=True)
        os.replace(temporary,target)
        journal.unlink()
    finally:
        if temporary_created:temporary.unlink(missing_ok=True)


def state_path(data):return Path(data)/'upgrade-state.json'


def write_state(data,previous,current,backup,status='active'):
    data=Path(data);path=state_path(data);temporary=data/('.upgrade-state-'+uuid.uuid4().hex+'.partial')
    value={'formatVersion':1,'status':status,'previousRelease':str(Path(previous).resolve()),'currentRelease':str(Path(current).resolve()),'catalogBackup':str(Path(backup).resolve()) if backup else None,'updatedAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    temporary_created=False
    try:
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        temporary_created=True
        with os.fdopen(fd,'w',encoding='utf-8') as stream:json.dump(value,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if temporary_created:temporary.unlink(missing_ok=True)
    return value


def read_state(data):
    path=state_path(data)
    if not path.is_file():raise ValueError('No completed Blank Box upgrade is available to roll back.')
    value=json.loads(path.read_text(encoding='utf-8'))
    required={'formatVersion','status','previousRelease','currentRelease','catalogBackup','updatedAt'}
    if not isinstance(value,dict) or set(value)!=required or value['formatVersion']!=1:raise ValueError('Upgrade state is not recognized.')
    return value


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    for name in ('data-path','state'):
        command=sub.add_parser(name);command.add_argument('--config')
    backup=sub.add_parser('backup');backup.add_argument('--config');backup.add_argument('--destination',required=True)
    restore=sub.add_parser('restore');restore.add_argument('--config');restore.add_argument('--backup',required=True)
    write=sub.add_parser('write-state');write.add_argument('--config');write.add_argument('--previous',required=True);write.add_argument('--current',required=True);write.add_argument('--backup');write.add_argument('--status',default='active',choices=('active','rolled-back','pending'))
    field=sub.add_parser('state-field');field.add_argument('--config');field.add_argument('--field',required=True,choices=('status','previousRelease','currentRelease','catalogBackup'))
    args=parser.parse_args()
    try:
        data=resolved_data(args.config)
        if args.command=='data-path':print(data)
        elif args.command=='backup':
            with RuntimeLock(data):saved=backup_catalog(data,args.destination)
            print(saved or '')
        elif args.command=='restore':
            with RuntimeLock(data):restore_catalog(data,args.backup)
            print('Catalog restored and verified; any prior catalog was retained in upgrades.')
        elif args.command=='write-state':print(json.dumps(write_state(data,args.previous,args.current,args.backup,args.status)))
        elif args.command=='state':print(json.dumps(read_state(data),indent=2))
        elif args.command=='state-field':
            value=read_state(data)[args.field];print('' if value is None else value)
    except (OSError,ValueError,sqlite3.Error,json.JSONDecodeError) as error:raise SystemExit(str(error))


if __name__=='__main__':main()
