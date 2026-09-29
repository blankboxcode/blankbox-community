# Independent updates

We keep Core and metapack updates separate and optional. Your existing library remains usable offline without either. We do not require an update service or background download.

## Trust

Release file inventories and public pack manifests use RSA-PSS with SHA-256 and a 32-byte salt. The installed `release-trust.json` contains the publisher's public key. Keep a trusted release and verify new release bytes using that installed verifier before running a new installer:

```sh
python3 /path/to/trusted/release_files.py /path/to/extracted-new-package
```

Public pack signatures are checked against the installed Core key before activation. Changing a pack database invalidates its signed hash. Changing the signature, publisher identity or manifest is rejected. Keep the trusted key with independent backups. A first download needs independent confirmation of the key fingerprint from the publisher. Publisher key rotation requires a separately reviewed Core/trust update; an imported pack cannot replace the key.

## Core

In **Settings → System & About → Update Blank Box software**, create a complete recovery point on a configured separate backup drive and wait for its job to finish. This is a preparation step. Blank Box's unprivileged service cannot replace operating-system application files. Verify the new package from a trusted source and run its platform installer as the machine administrator; do not give the web service installation privileges.

Stop Core before offline maintenance. Install into an immutable release directory using the platform guide. Preserve config, selected port, data and earlier code. Upgrade snapshots pair the SQLite catalog with installed packs, staged pack files and the bootstrap receipt. Failed Linux/Docker activation attempts recover the earlier release and snapshot. Check `/health/ready` and sign in before considering an upgrade complete. Windows currently requires foreground startup and manual acceptance; its startup task runs only after sign-in.

Use `rollback-linux.sh` or `rollback-windows.ps1` for a compatible rollback. A schema downgrade requires the explicit pre-upgrade restore option. That replaces catalog state with the earlier snapshot, so preserve later edits first. Recovery makes an additional copy of the catalog before replacement. Do not mix a catalog and pack set with an older reader that cannot understand them.

## Metapacks

Download a complete signed `.bbpack` by a channel you trust, transfer it by removable storage if desired, and choose manual import under Settings → Metadata. Public format 5 packs require reader 5. The current reader retains previously installed older local formats for compatibility. All new metapack imports into a public installation must be signed public packs. Previously installed legacy packs remain readable.

Before a pack update, stop Core and make an offline snapshot with the installed lifecycle tool:

```sh
python3 maintenance.py backup --config /path/to/config.json --destination /separate/backup/pre-pack-update.sqlite3
```

Keep the resulting `.assets` directory beside that SQLite file. Restart Core and import the chosen pack. The reader validates bounded archive membership, signatures, database hash, schema, records, aliases and identity constraints before adding an immutable version. It retains previous versions and publishes the new manifest only after the data file is complete. Equal-version conflicts and downgrades are rejected. A failed validation leaves the selected pack unchanged. Confirmed household facts keep prior evidence and IDs; installed packs cannot merge household items from title similarity.

To reverse a pack/catalog change, stop Core and use `maintenance.py restore --config ... --backup ...` with the paired snapshot. The operation refuses a running Core. It retains the current catalog and displaced pack directories. Ordinary pack removal is an explicit Settings choice and keeps saved household knowledge; reinstall remains optional. A full pack is the current update unit. Delta downloads and an online catalog are not required or implemented.
