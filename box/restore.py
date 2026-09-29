#!/usr/bin/env python3
"""Restore a verified Blank Box snapshot into a NEW, EMPTY data directory."""
import argparse,json,sqlite3
from pathlib import Path
from file_safety import reject_links
from server import CATALOG_SCHEMA_VERSION,checked_copy,digest,inside,safe_destination
from maintenance import ASSET_NAMES

def restore_catalog_export(export_file,destination):
    """Restore metadata only; media bytes and service credentials are not included."""
    source=Path(export_file).expanduser()
    if source.is_symlink() or not source.is_file():raise ValueError('Choose a regular Blank Box catalog export file.')
    source=source.resolve(strict=True)
    if any(source.with_name(source.name+suffix).exists() for suffix in ('-wal','-shm')):
        raise ValueError('Choose a completed catalog export, not a live catalog with journal files.')
    destination=reject_links(destination).resolve()
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError('Restore destination must be a new or empty directory.')
    with sqlite3.connect(source.as_uri()+'?mode=ro&immutable=1',uri=True) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Catalog export integrity check failed.')
        version=db.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]
        if not isinstance(version,int) or version>CATALOG_SCHEMA_VERSION:raise ValueError('This catalog export uses an unsupported schema.')
        for table in ('items','physical_releases','owned_copies','package_contents','inventory_links'):
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():
                raise ValueError('This is not a complete Blank Box catalog export.')
        for table in ('connections','auth_sessions','users'):
            if db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]:
                raise ValueError('This file contains account or connection secrets, not a portable export.')
        count=db.execute('SELECT COUNT(*) FROM items').fetchone()[0]
    destination.mkdir(mode=0o700,parents=True,exist_ok=True)
    checked_copy(source,destination/'catalog.sqlite3',digest(source))
    # A catalog-only restore has no managed media or verified backup destination.
    # Retain the exported ownership records, but reset operational backup badges.
    with sqlite3.connect(destination/'catalog.sqlite3') as db:
        for item_id,data in db.execute('SELECT id,data FROM items').fetchall():
            item=json.loads(data)
            if item.get('backup')=='verified':
                item['backup']='none';item.pop('backupVerifiedAt',None)
                db.execute('UPDATE items SET data=? WHERE id=?',(json.dumps(item,ensure_ascii=False),item_id))
        db.execute('DELETE FROM backup_state')
    return count

def restore(snapshot,destination,progress=None):
    snapshot=reject_links(snapshot).resolve(strict=True)
    destination=reject_links(destination).resolve()
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError('Restore destination must be a new or empty directory.')
    base=snapshot.parent.parent
    if snapshot.parent.name!='snapshots' or base.name!='blank-box-backup':raise ValueError('Choose a folder under blank-box-backup/snapshots/.')
    manifest=json.loads((snapshot/'manifest.json').read_text())
    catalog=reject_links(snapshot/'catalog.sqlite3')
    if digest(catalog)!=manifest['catalogSha256']:raise ValueError('Catalog checksum failed. Nothing was restored.')
    with sqlite3.connect(catalog.as_uri()+'?mode=ro&immutable=1',uri=True) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Catalog integrity failed.')
    verified=[]
    for f in manifest['files']:
        rel=Path(f['path'])
        if rel.is_absolute() or '..' in rel.parts or not rel.parts or rel.parts[0]!='media':raise ValueError('Invalid path in backup manifest.')
        source=reject_links(base/rel).resolve(strict=True)
        if not inside(source,base) or not source.is_file() or digest(source)!=f['sha256']:raise ValueError(f'Backup file checksum failed: {rel}')
        verified.append((source,rel,f['sha256']))
    destination.mkdir(parents=True,exist_ok=True,mode=0o700)
    for index,(source,relative,sha) in enumerate(verified,1):
        checked_copy(source,destination/relative,sha)
        if progress:progress('Managed media',index,len(verified)+1)
    checked_copy(catalog,destination/'catalog.sqlite3',manifest['catalogSha256'])
    if progress:progress('Catalog',len(verified)+1,len(verified)+1)
    return len(verified)
def restore_full(snapshot,destination,progress=None):
    """Prepare a complete, verified library recovery in an empty directory."""
    snapshot=reject_links(snapshot).resolve(strict=True)
    marker=reject_links(snapshot/'full-recovery.json')
    if not marker.is_file():raise ValueError('Choose a complete recovery point.')
    point=json.loads(marker.read_text())
    if point.get('version')!=1 or point.get('assets')!='catalog.sqlite3.assets':raise ValueError('Unsupported complete recovery point.')
    catalog=reject_links(snapshot/'catalog.sqlite3')
    if not catalog.is_file() or digest(catalog)!=point.get('catalogSha256'):raise ValueError('Complete recovery catalog checksum failed.')
    with sqlite3.connect(catalog.as_uri()+'?mode=ro&immutable=1',uri=True) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Complete recovery catalog integrity failed.')
        version=db.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]
        if not isinstance(version,int) or version>CATALOG_SCHEMA_VERSION:raise ValueError('This recovery catalog uses an unsupported schema.')
    assets=reject_links(snapshot/point['assets'])
    inventory=reject_links(assets/'inventory.json')
    if not assets.is_dir() or not inventory.is_file() or digest(inventory)!=point.get('assetInventorySha256'):
        raise ValueError('Complete recovery pack inventory checksum failed.')
    hashes=json.loads(inventory.read_text())
    if not isinstance(hashes,dict):raise ValueError('Invalid pack inventory.')
    actual={p.relative_to(assets).as_posix() for p in assets.rglob('*') if p.is_file() and p.name!='inventory.json'}
    if actual!=set(hashes):raise ValueError('Recovery pack inventory differs from its snapshot.')
    verified=[]
    for name,sha in hashes.items():
        if not isinstance(name,str) or not isinstance(sha,str) or len(sha)!=64:raise ValueError('Invalid pack inventory entry.')
        relative=Path(name)
        if relative.is_absolute() or '..' in relative.parts or not relative.parts or relative.parts[0] not in ASSET_NAMES:
            raise ValueError('Unsafe recovery asset path.')
        source=reject_links(assets/relative)
        if not source.is_file() or digest(source)!=sha:raise ValueError('Recovery pack checksum failed.')
        verified.append((source,relative,sha))
    count=restore(snapshot,destination,progress)
    destination=reject_links(destination).resolve(strict=True)
    for index,(source,relative,sha) in enumerate(verified,1):
        checked_copy(source,safe_destination(destination,relative),sha)
        if progress:progress('Offline packs',index,len(verified))
    # A review copy has no configured backup destination of its own yet.
    with sqlite3.connect(destination/'catalog.sqlite3') as db:
        for item_id,data in db.execute('SELECT id,data FROM items').fetchall():
            item=json.loads(data)
            if item.get('backup')=='verified':
                item['backup']='none';item.pop('backupVerifiedAt',None)
                db.execute('UPDATE items SET data=? WHERE id=?',(json.dumps(item,ensure_ascii=False),item_id))
        db.execute('DELETE FROM backup_state')
    return count
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('snapshot');p.add_argument('destination');mode=p.add_mutually_exclusive_group();mode.add_argument('--catalog-only',action='store_true',help='Restore a downloaded catalog export without media bytes');mode.add_argument('--full',action='store_true',help='Restore a complete recovery point with its installed packs');a=p.parse_args()
    if a.catalog_only:
        count=restore_catalog_export(a.snapshot,a.destination)
        print(f'Restored {count} catalog items in {a.destination}. Media files and connection credentials were not included.')
    elif a.full:
        count=restore_full(a.snapshot,a.destination)
        print(f'Restored and checked {count} managed files, the catalog and installed packs in {a.destination}. Review before switching Core to this location.')
    else:
        count=restore(a.snapshot,a.destination)
        print(f'Restored and checked {count} media files and the catalog in {a.destination}. Start Blank Box with --data pointing there.')
