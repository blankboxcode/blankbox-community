# Update Blank Box

We keep Core and metapack updates separate and optional. Your existing library remains usable offline without either. We do not require an update service or background download.

## Trust

Release file inventories and public pack manifests use RSA-PSS with SHA-256 and a 32-byte salt. The installed `release-trust.json` contains the publisher's public key. Keep a trusted release and verify new release bytes using that installed verifier before running a new installer:

```sh
python3 /path/to/trusted/release_files.py /path/to/extracted-new-package
```

Public pack signatures are checked against the installed Core key before activation. Changing a pack database invalidates its signed hash. Changing the signature, publisher identity or manifest is rejected. Keep the trusted key with independent backups. A first download needs independent confirmation of the key fingerprint from the publisher. Publisher key rotation requires a separately reviewed Core/trust update; an imported pack cannot replace the key.

## Update your installation

Choose the [native Linux installation ZIP](https://github.com/blankboxcode/blankbox-community/releases/download/v1.0.0/blankbox-community-1.0.0.zip) or the small [Docker image setup ZIP](https://raw.githubusercontent.com/blankboxcode/blankbox-community/main/downloads/blankbox-docker-1.0.0-1.zip), then extract it into a **new folder**. Keep your current installation and data where they are. Source archives are developer downloads.

Before updating, open **Settings → System & About → Update Blank Box software**, create a complete recovery point on your configured separate backup drive, and wait for it to finish. The web app prepares the backup; the platform installer performs the update. A library recovery point cannot recreate missing linked original files, so back up your source drives separately.

### Native Linux

Open a terminal in the new extracted folder, where `RELEASE.json` and `install-linux.sh` are visible. For the standard installation:

```sh
python3 /opt/blankbox/current/release_files.py . --trusted-key /opt/blankbox/current/release-trust.json
sudo ./install-linux.sh
```

Use your installed paths if you chose a different installation root. The installer keeps your account, library, port, access mode, sources and backup settings. It creates a paired pre-update snapshot, retains the previous application and checks readiness. Open your usual Blank Box address, sign in normally and refresh the browser. Check an existing item, its copies/artwork and your configured sources. Keep the previous release and snapshot.

You only need `setup-linux.sh` again if you also want to change your access mode or port. See [Linux](guides/LINUX.md).

### Docker on Linux

Use the checked updater for an existing Compose installation. For a stack managed by Portainer, follow [Portainer updates](guides/PORTAINER.md#keep-updates-and-the-stack-definition-together). The [local-image migration guide](guides/DOCKER-MIGRATION.md) covers older installations that build their own image.

Use the small Docker image setup ZIP to update or switch from a locally built image. It uses the same application and catalog schema as the current Linux/Docker release; switching delivery methods does not move your library.

1. Keep the current container available. If you stopped or removed it, start it from its existing release folder with its current settings first.
2. Verify the new package using a trusted copy of `release_files.py` from your previous package, following [Trust](#trust).
3. Copy your **existing** `.env` and `compose.override.yaml` or `compose.override.yml` into the new extracted folder. Keep the same project name, image setting, numeric user and data volume or bind folder. Keep other custom Compose files and secret/config files outside the signed package folder, preserving their references. If a path is relative, update it to point to the **same existing file or folder**; moving the release folder must not select a new data location.
4. Open a terminal in the new folder and run:

```sh
./upgrade-docker.sh
```

The helper authenticates the image descriptor, checks the existing project/user/mounts and pulls the exact digest before stopping. It then creates a paired snapshot and checks readiness. Failed activation restores the previous image and snapshot. On success it saves the accepted digest and retained UID/GID in `.env`, including `10001:10001` from older installations. It does not move data or change ownership. New installations use `1000:1000`. If Docker commands need sudo, run `sudo ./upgrade-docker.sh`; host Docker access does not change the container user.

The image updater preserves the incoming `.env` file owner. If an earlier update left it root-owned, correct its intended Linux-user ownership before copying it. Save access settings such as `BLANKBOX_BIND_ADDRESS` and `BLANKBOX_PUBLISHED_PORT` in `.env` so they survive sudo.

If verification reports `Release contains unlisted files.`, the setup folder contains files outside the signed inventory. Only `.env`, `compose.override.yaml` and `compose.override.yml` are allowed additions. Keep other files outside the package folder and preserve any configuration references. Invoking the updater through Bash uses the same verification check.

Sign in at your usual address and check your library. Keep the printed previous image tag and pre-update snapshot. Ordinary `docker compose up` in the accepted setup folder keeps its saved image digest. Changing user IDs or moving storage is a separate operation after the update works. See [Docker](guides/DOCKER.md) for bind mounts and source-folder access.

To continue building locally, use the full Linux/Docker installation ZIP and its local-build updater. Follow [Docker → Optional local build](guides/DOCKER.md#optional-local-build).

### Windows

Our separate Windows download remains the experimental **0.1.0-beta.8** package, schema **20**. This Linux/Docker update does not include a new Windows installer. Follow the guide supplied with the Windows package and do not open an upgraded schema 22 catalog with it.

## Rollback

Version 1.0.0 keeps catalog schema **22**. Existing schema 22 libraries need no migration. Older schema 20 Linux/Docker libraries migrate to schema 22. Existing accounts, covers, copy IDs and reference selections are retained. An older Core cannot read schema 22. Returning to it requires both its application files and its **paired pre-update catalog/assets snapshot**. Preserve any later edits before restoring that earlier state.

For a compatible native Linux rollback:

```sh
sudo /opt/blankbox/current/rollback-linux.sh
```

If the previous Core cannot read the current catalog, this refuses the switch. To deliberately return to the paired pre-update state after preserving later work:

```sh
sudo /opt/blankbox/current/rollback-linux.sh --restore-pre-upgrade-catalog
```

The restore replaces the active catalog with the earlier snapshot and retains an emergency copy of the newer state. Keep that copy with its matching `.assets` directory. Do not combine an older catalog with unrelated packs or receipts.

For Docker, retain the previous image tag and catalog snapshot printed by the updater. Stop the service and restore the paired snapshot with `maintenance.py` from the **newer** image before starting an older image. Keep the same mounts, project and user. The [recovery guide](RECOVERY.md) explains paired snapshots; do not merely change the image tag against an upgraded catalog.

## Metapacks

Download a complete signed `.bbpack` by a channel you trust, transfer it by removable storage if desired, and choose manual import under Settings → Metadata. Public format 5 packs require reader 5. The current reader retains previously installed older local formats for compatibility. All new metapack imports into a public installation must be signed public packs. Previously installed legacy packs remain readable.

Before a pack update, stop Core and make an offline snapshot with the installed lifecycle tool:

```sh
python3 maintenance.py backup --config /path/to/config.json --destination /separate/backup/pre-pack-update.sqlite3
```

Keep the resulting `.assets` directory beside that SQLite file. Restart Core and import the chosen pack. The reader validates bounded archive membership, signatures, database hash, schema, records, aliases and identity constraints before adding an immutable version. It retains previous versions and publishes the new manifest only after the data file is complete. Equal-version conflicts and downgrades are rejected. A failed validation leaves the selected pack unchanged. Confirmed household facts keep prior evidence and IDs; installed packs cannot merge household items from title similarity.

To reverse a pack/catalog change, stop Core and use `maintenance.py restore --config ... --backup ...` with the paired snapshot. The operation refuses a running Core. It retains the current catalog and displaced pack directories. Ordinary pack removal is an explicit Settings choice and keeps saved household knowledge; reinstall remains optional. A full pack is the current update unit. Delta downloads and an online catalog are not required or implemented.
