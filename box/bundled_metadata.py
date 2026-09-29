"""Install explicitly bundled offline packs once, preserving household choices."""
from pathlib import Path
import hashlib
import io
import json
import os
import re
import sqlite3
import zipfile
import uuid
from file_safety import reject_links


def install_bundled_packs(packs, data, directory=None):
    directory = Path(directory) if directory else Path(__file__).with_name('bundled-metadata')
    manifest_path = directory / 'catalog.json'
    if not manifest_path.is_file():
        return []
    receipt_path = reject_links(Path(data) / 'bundled-metadata-receipt.json')
    try:
        receipt = json.loads(receipt_path.read_text()) if receipt_path.is_file() else {}
        manifest = json.loads(manifest_path.read_text())
        entries = manifest['packs']
        if manifest.get('format') != 1 or not isinstance(entries, list) or len(entries) > 10:
            raise ValueError('Invalid bundled pack catalog.')
        if not isinstance(receipt, dict):
            raise ValueError('Invalid bundled pack receipt.')
    except (OSError, ValueError, KeyError, TypeError):
        return ['Bundled metadata could not be read. Core remains usable without packs.']
    installed = {entry['id'] for entry in packs.list()}
    existing_household = False
    catalog = Path(data) / 'catalog.sqlite3'
    if catalog.is_file():
        try:
            with sqlite3.connect(catalog.resolve().as_uri()+'?mode=ro',uri=True) as db:
                tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                existing_household=any(db.execute('SELECT 1 FROM '+table+' LIMIT 1').fetchone() for table in ('items','users') if table in tables)
        except sqlite3.Error:
            return ['Bundled metadata could not inspect the catalog. Core will not change installed packs.']
    errors = []
    for entry in entries:
        try:
            identifier, name, digest = entry['id'], entry['file'], entry['sha256']
            if not isinstance(identifier, str) or not re.fullmatch(r'[a-z0-9-]{1,80}', identifier):
                raise ValueError('Invalid bundled pack identity.')
            if not isinstance(name, str) or not re.fullmatch(r'[a-z0-9.-]+\.bbpack', name) or not isinstance(digest, str) or not re.fullmatch(r'[a-f0-9]{64}', digest):
                raise ValueError('Invalid bundled pack file.')
            if identifier in receipt:
                continue  # Removal stays removed, including after an app upgrade.
            if identifier not in installed and not existing_household:
                path = directory / name
                if path.is_symlink() or not path.is_file() or path.stat().st_size > 64 * 1024 * 1024:
                    raise ValueError('Bundled pack is unavailable.')
                payload = path.read_bytes()
                if hashlib.sha256(payload).hexdigest() != digest:
                    raise ValueError('Bundled pack checksum failed.')
                # Check the declared identity before any installation mutation.
                with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                    if json.loads(archive.read('manifest.json'))['id'] != identifier:
                        raise ValueError('Bundled pack identity changed.')
                packs.install_bundle(payload)
                installed.add(identifier)
            receipt[identifier] = {'sha256': digest, 'status': 'existing-household-preserved' if existing_household else 'initialized'}
            stage = receipt_path.with_name('.receipt-'+uuid.uuid4().hex+'.partial')
            fd=os.open(stage,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            try:
                with os.fdopen(fd,'w') as stream:
                    stream.write(json.dumps(receipt,sort_keys=True)+'\n');stream.flush();os.fsync(stream.fileno())
                reject_links(receipt_path)
                os.replace(stage,receipt_path)
            finally:stage.unlink(missing_ok=True)
        except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile):
            errors.append('A bundled metadata pack could not be installed. Core remains usable without it.')
    return errors
