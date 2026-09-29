#!/usr/bin/env python3
"""Read-only installation diagnostics for Blank Box Core."""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

from server import CATALOG_SCHEMA_VERSION, VERSION, load_runtime_config


def result(name,status,detail):
    return {'check':name,'status':status,'detail':detail}


def inspect_installation(options):
    checks=[]
    python_ok=sys.version_info>=(3,10)
    checks.append(result('python','pass' if python_ok else 'fail',f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}'))
    web=Path(__file__).resolve().parent/'web'/'index.html'
    checks.append(result('web-client','pass' if web.is_file() else 'fail','bundled web client found' if web.is_file() else 'bundled web client is missing'))

    data=Path(options['data']).expanduser().resolve()
    data_target=data if data.exists() else next((parent for parent in data.parents if parent.exists()),data.parent)
    data_ok=data.is_dir() and os.access(data,os.R_OK|os.W_OK) if data.exists() else data_target.is_dir() and os.access(data_target,os.W_OK)
    checks.append(result('data-directory','pass' if data_ok else 'fail',str(data)))

    catalog=data/'catalog.sqlite3'
    if catalog.exists():
        try:
            with sqlite3.connect(catalog.resolve().as_uri()+'?mode=ro',uri=True) as db:
                integrity=db.execute('PRAGMA integrity_check').fetchone()[0]
                migrations=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'").fetchone()
                schema=int(db.execute('SELECT COALESCE(MAX(version),0) FROM schema_migrations').fetchone()[0]) if migrations else 0
                items_table=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='items'").fetchone()
                items=int(db.execute('SELECT COUNT(*) FROM items').fetchone()[0]) if items_table else 0
            okay=integrity=='ok' and schema<=CATALOG_SCHEMA_VERSION
            detail=f'integrity {integrity}; schema {schema}/{CATALOG_SCHEMA_VERSION}; {items} items'
            checks.append(result('catalog','pass' if okay else 'fail',detail))
        except (OSError,sqlite3.Error) as error:checks.append(result('catalog','fail',f'catalog could not be read: {error}'))
    else:checks.append(result('catalog','pass','new installation; catalog will be created on first start'))

    for index,source in enumerate(options['sources'],1):
        path=Path(source).expanduser().resolve();okay=path.is_dir() and os.access(path,os.R_OK)
        checks.append(result(f'source-{index}','pass' if okay else 'fail',str(path)))
    if options['backup']:
        backup=Path(options['backup']).expanduser().resolve();okay=backup.is_dir() and os.access(backup,os.R_OK|os.W_OK)
        checks.append(result('backup-directory','pass' if okay else 'fail',str(backup)))
    checks.append(result('listener','pass',f"{options['host']}:{options['port']}"))
    return checks


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',help='JSON configuration file (or set BLANKBOX_CONFIG)')
    parser.add_argument('--json',action='store_true',help='Print machine-readable JSON')
    parser.add_argument('--version',action='version',version=f'Blank Box Doctor {VERSION}')
    args=parser.parse_args()
    try:options=load_runtime_config(args.config)
    except (OSError,ValueError) as error:
        if args.json:print(json.dumps({'status':'fail','checks':[result('configuration','fail',str(error))]}))
        else:print(f'[FAIL] configuration: {error}')
        raise SystemExit(1)
    checks=inspect_installation(options);okay=all(check['status']=='pass' for check in checks)
    if args.json:print(json.dumps({'status':'pass' if okay else 'fail','version':VERSION,'checks':checks},indent=2))
    else:
        print(f'Blank Box {VERSION} diagnostics (read-only)')
        for check in checks:print(f"[{check['status'].upper()}] {check['check']}: {check['detail']}")
    raise SystemExit(0 if okay else 1)


if __name__=='__main__':main()
