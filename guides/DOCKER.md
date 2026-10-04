# Run Blank Box with Docker Compose

We provide a prebuilt image for a Linux Intel/AMD host with Docker Engine and the Docker Compose plugin. Python 3.10+ verifies the small setup bundle and handles checked updates. Docker pulls the application from `ghcr.io/blankboxcode/blankbox-community`; you do not need a local application build.

Run `docker info` to check access to Docker before installing or updating. If it reports permission denied but `sudo docker info` works, use `sudo` for the Docker commands in this guide and run updates with `sudo ./upgrade-docker.sh`. Blank Box still runs inside its container with the configured non-root UID/GID. Keep your Compose project name and other settings in the installation's `.env`; `sudo` may omit settings exported only in your shell. You do not need to change library ownership or user IDs to fix host Docker access.

## 1. Extract and configure

Download the small [Docker setup ZIP](https://raw.githubusercontent.com/blankboxcode/blankbox-community/main/downloads/blankbox-docker-0.1.0-beta.10-1.zip), extract it and open a terminal inside the resulting folder. You should see `compose.yaml`, `image.json`, `setup-docker.sh` and `blankbox.env.example`. This creates a fresh, empty library in a persistent Docker volume. For an existing installation, use the update steps below. For a recovery drill, read [Recovery](../RECOVERY.md) and use a separate empty data location.

Confirm the publisher key fingerprint independently for a first download, then verify the bundle:

```sh
python3 release_files.py .
```

If you already have a trusted package, use its verifier and key to check this new folder before running new scripts; see [Updates](../UPDATES.md#trust).

Create the local settings file:

```sh
cp -n blankbox.env.example .env
```

The safe default is accessible only from the Docker host:

```dotenv
BLANKBOX_BIND_ADDRESS=127.0.0.1
BLANKBOX_PUBLISHED_PORT=25265
```

To use Blank Box from other devices on a trusted home LAN, change the bind address to `0.0.0.0`. This does not expose the service through your router unless you separately configure port forwarding, which is not recommended.

## 2. Add media and backup mounts

For an initial look at an empty library, you can skip this section and run the startup command below. To add your own folders, first make sure the host paths exist and your container user can read media and write backups. For a new named-volume installation, the default UID/GID is `1000:1000`. To use another UID, follow the correctly owned data-folder example below and set `BLANKBOX_UID`/`BLANKBOX_GID` in your local `.env`, or select the user in your local Compose override. The settings do not change folder ownership. Use a plain text editor to create the new override file; do not edit the signed `compose.yaml`.

Create `compose.override.yaml` with existing media as read-only mounts and a backup destination as a read/write mount:

```yaml
services:
  blankbox:
    environment:
      BLANKBOX_SOURCES: '["/imports/movies", "/imports/photos"]'
      BLANKBOX_BACKUP: /backup
      BLANKBOX_BACKUP_EVERY_HOURS: "24"
    volumes:
      - /srv/media:/imports/movies:ro
      - /srv/photos:/imports/photos:ro
      - /srv/blankbox-backup:/backup:rw
```

The selected container user needs access to those host folders. Keep source media read-only and grant backup access only to the intended account.

The image includes Blank Box's native, read-only audio-CD reader and needs no separate ripping or encoding programs. It imports lossless WAV. Docker does not expose host hardware automatically. On a Linux Docker host with a connected optical drive, use the bundled `compose.disc.yaml` override to grant just that drive, not the whole `/dev` tree. Find its group ID:

```sh
stat -c %g /dev/sr0
```

Choose the `/dev/srN` that actually belongs to your optical drive. Add these lines to the installation's `.env`, replacing the example group ID with the number printed above:

```dotenv
COMPOSE_FILE=compose.yaml:compose.override.yaml:compose.disc.yaml
BLANKBOX_OPTICAL_DEVICE=/dev/sr0
BLANKBOX_OPTICAL_GID=24
```

Then the normal `docker compose` and `./upgrade-docker.sh` commands use the drive override automatically. Keep these `.env` settings when moving to a new release folder. Without a drive, leave these lines out. Optical-drive passthrough and extraction still require a real-device acceptance test; Docker Desktop on Windows is not claimed to expose the host optical drive. Protected video discs remain outside this import path.

## Optional: choose your user and a host data folder

Our new-install default is `1000:1000`. To use a different non-root UID, prepare a dedicated host data folder owned by that user as shown below, and select the IDs in `.env` or `compose.override.yaml`. The default new named volume is initialized for UID 1000; changing the process user alone does not change its ownership. Check your intended Linux account's IDs with `id -u` and `id -g`. Setting `PUID` or `PGID` environment variables does not change the process user; use Compose's `user` setting.

For a **new, empty** data folder on a normal Linux Docker host, replacing these example IDs and path as needed:

```sh
sudo install -d -o 1000 -g 1000 -m 0700 /srv/blankbox/data
```

Add this configuration to `compose.override.yaml`. If it already contains media/backup mounts, add these settings under the same `blankbox` service rather than creating a duplicate service entry:

```yaml
services:
  blankbox:
    user: "1000:1000"
    volumes:
      - type: bind
        source: /srv/blankbox/data
        target: /data
        bind:
          create_host_path: false
```

The bind mount replaces the named volume at `/data`; your other mounts remain. `create_host_path: false` makes a missing or mistyped folder fail instead of silently creating a different empty library. Your media folders need read access and your backup folder needs write access for this chosen user; their ownership does not need to change when existing permissions already allow that access.

The data folder and its contents must belong to the selected UID. Blank Box sets private directory and file permissions at startup; group write access alone is insufficient. The image keeps its application files root-owned and the application filesystem read-only. It does not run a privileged startup routine or recursively change host ownership. Rootless Docker or user-namespace remapping can map container IDs to different host IDs; use the ownership appropriate to that daemon configuration.

**An existing library does not move automatically.** Before changing storage or UID, stop Blank Box and retain a separate recovery copy. Copy the complete stopped `/data` tree into the new dedicated folder, including the catalog, any WAL files, recovery key, managed files and paired packs. Review ownership only on that copied Blank Box data tree. Keep the original volume intact until sign-in, library contents and recovery are checked. Do not use `down --volumes` to migrate data, and do not change ownership of your media drives.

Use a local data filesystem that supports normal permissions and SQLite locking. Do not assume a network share can safely replace local library storage.

## 3. Pull and start

```sh
./setup-docker.sh
```

With the default configuration, this creates:

- The official image pinned to its signed registry digest
- A container named `blankbox-blankbox-1`
- A persistent named volume called `blankbox_blankbox-data`

With the data-folder override, the library persists in the host folder you selected instead.

Read the recovery key used to claim the first owner profile:

```sh
docker compose exec -T blankbox python3 -c 'print(open("/data/access-key.txt").read().strip())'
```

Open `http://127.0.0.1:25265` on the Docker host or `http://SERVER-IP:25265` from an allowed LAN device.

## Optional friendly local name on Linux

When Compose is bound to `0.0.0.0`, a Linux Docker host with Avahi can advertise `http://blankbox.local:25265`:

```sh
sudo apt install avahi-daemon avahi-utils iproute2
sudo ./enable-blankbox-local.sh --port 25265
```

This helper runs on the host, not in the container. It is local-network discovery, not internet exposure or HTTPS.

## Normal operations

View status and logs:

```sh
docker compose ps
docker compose logs --follow blankbox
```

Stop while preserving data:

```sh
docker compose down
```

Start again:

```sh
docker compose up --detach --wait
```

Update or switch from a locally built image using a newly extracted Docker setup bundle:

Copy your existing `.env` and any local Compose overrides into the newly extracted folder; keep the same project name, image setting, user and volume or bind folder. Preserve referenced secret files. If any bind path is relative, make sure it still points to the same existing folder after moving to the new release directory. Verify the new package with your installed trusted verifier first (see [Updates](../UPDATES.md)).

If you also want to change the user or move your data to a host folder, upgrade using your current settings first and check that you can sign in. Then follow the existing-library guidance above for the separate move. Changing those settings before an upgrade can prevent the previous image from reading your library or making its recovery snapshot.

```sh
./upgrade-docker.sh
```

The helper verifies the bundle and signed image descriptor, checks the existing project/user/mounts and pulls the exact image digest before stopping. It then snapshots SQLite and its paired assets, waits for readiness, and saves the accepted digest and UID/GID in `.env`. An existing `10001:10001` library keeps that user; an existing `1000:1000` library keeps 1000. It does not change ownership. Conflicting user or storage settings are refused before stopping the service. If the old container was removed, start the previous release with its current settings first. Failed activation restores the paired catalog and previous image and persists that recovered selection for ordinary `docker compose up`. Keep the printed previous image tag and snapshot. Older beta.8/beta.9 catalogs migrate from schema 20 to 22; an older image needs its pre-update catalog/assets snapshot. See [Rollback](../UPDATES.md#rollback).

## Compose URLs and Docker managers

The ready-to-use [Compose file](https://raw.githubusercontent.com/blankboxcode/blankbox-community/main/deploy/docker-image/compose.yaml) uses `image:` with an exact digest and has no `build:` entry. In a manager that supports a Git repository, use `https://github.com/blankboxcode/blankbox-community`, branch `main`, and Compose path `deploy/docker-image/compose.yaml`. A manager that accepts a Compose file URL can use the linked raw URL. Add your port, user and mount settings as described above. Portainer/Dockhand-specific deployment and update behavior still needs checking in your own setup.

For a **new empty library**, a current Compose plugin with Git URL support can load the file directly:

```sh
docker compose -f 'https://github.com/blankboxcode/blankbox-community.git#main:deploy/docker-image/compose.yaml' up --detach --wait --wait-timeout 240
```

Compose may show the downloaded settings and ask for confirmation. Review them, then choose **Yes** to continue. Use the same `-f` URL for `ps`, `logs` and `exec` commands when using this route. The default project is `blankbox`, port 25265 is bound to this computer, and the persistent volume is `blankbox_blankbox-data`. The setup ZIP also supplies the signature verifier, update helper and local settings files. For an existing library, use its checked update path instead of the fresh-start command. A manager's image-update button does not create a paired catalog snapshot.

## Optional local build

You can still build from the full [Linux / Docker installation ZIP](https://github.com/blankboxcode/blankbox-community/releases/download/v0.1.0-beta.10/blankbox-community-0.1.0-beta.10.zip). Extract and verify that package, then open its folder containing `Dockerfile` and `compose.yaml`:

```sh
cp -n blankbox.env.example .env
docker compose up --detach --build --wait --wait-timeout 240
```

Its bundled `upgrade-docker.sh` builds locally when used with a newer full installation ZIP. The small image setup bundle pulls from the registry. Keep the same project, settings and library when moving between these delivery methods.

## Reset or uninstall carefully

`docker compose down` does not remove the library volume. Do not add `--volumes` unless you deliberately intend to erase the Docker Blank Box catalog, recovery key, owner account, and imported media. Verify a separate backup and restore before deleting `blankbox_blankbox-data`.
