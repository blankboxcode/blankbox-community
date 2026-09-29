# Run Blank Box with Docker Compose

We provide this path for a Linux host with Docker Engine, the Docker Compose plugin and Python 3.10+ for signature verification. The beta builds its image locally from the verified release package; we do not pull a Blank Box image from a public registry.

## 1. Extract and configure

Use the same `blankbox-community-VERSION.zip` supplied for Linux. The Windows ZIP and source ZIP are not the Docker installation package. Extract the Community ZIP and open a terminal inside the resulting folder; `compose.yaml`, `Dockerfile` and `blankbox.env.example` should be visible. This guide creates a fresh, empty library in a persistent Docker volume. For an existing-library restore drill, first read [Recovery](../RECOVERY.md) and use a separate empty data location.

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

For an initial look at an empty library, you can skip this section and run the startup command below. To add your own folders, first make sure the host paths exist and container UID/GID `10001` can read media and write backups. Use a plain text editor to create the new override file; do not edit the signed `compose.yaml`.

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

Container UID/GID `10001` needs access to those host folders. Do not make private media world-writable.

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

## 3. Build and start

```sh
docker compose up --detach --build --wait --wait-timeout 240
```

This creates:

- A local image named `blankbox-community:local`
- A container named `blankbox-blankbox-1`
- A persistent named volume called `blankbox_blankbox-data`

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

Upgrade from a newly extracted release package:

Copy your existing `.env` and Compose override into the newly extracted folder; keep the same project name and volume. Verify the new package with your installed trusted verifier first (see [Updates](../UPDATES.md)).

```sh
./upgrade-docker.sh
```

The upgrade helper verifies the package, builds a uniquely tagged candidate, stops Core, snapshots SQLite and its installed packs, waits for health, and restores the previous image and catalog if activation fails. On success it advances the configured local image tag so a later ordinary `docker compose up` uses the accepted version. The previous image tag and paired catalog snapshot are printed for manual rollback. Keep both. Do not share one mutable image tag between installations that need independent upgrade schedules.

## Reset or uninstall carefully

`docker compose down` does not remove the library volume. Do not add `--volumes` unless you deliberately intend to erase the Docker Blank Box catalog, recovery key, owner account, and imported media. Verify a separate backup and restore before deleting `blankbox_blankbox-data`.
