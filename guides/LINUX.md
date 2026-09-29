# Install Blank Box on Linux

We recommend this path for a dedicated Debian or Ubuntu-class Blank Box. It requires Python 3.10 or newer and systemd.

## 1. Extract the release

Use `blankbox-community-0.1.0-beta.8.zip` for Linux. The Windows ZIP is for Windows; the source ZIP is for building from source. Verify the published SHA-256 checksum, then extract the Community ZIP. In your file manager, open the resulting `blankbox-community-0.1.0-beta.8` folder and choose **Open in Terminal**. Check that `setup-linux.sh` and `RELEASE.json` are in that folder before running the next command. For a restore-only test of an existing library, follow [Recovery](../RECOVERY.md) instead of installing into the restore destination.

## 2. Run the setup wizard

Run:

```sh
sudo ./setup-linux.sh
```

The terminal wizard asks whether to install/update or uninstall, which port to use, and whether Blank Box should be available only on that computer, on the trusted home network, or at the optional `blankbox.local` address.

If you choose `blankbox.local`, install the discovery packages first:

```sh
sudo apt update
sudo apt install python3 avahi-daemon avahi-utils iproute2
```

The wizard is the recommended path. For scripting or advanced administration, the lower-level installer remains available:

```sh
sudo ./install-linux.sh                 # this computer only
sudo ./install-linux.sh --lan-access    # trusted LAN
sudo ./install-linux.sh --enable-local-name
```

The friendly name is optional. If another device already owns `blankbox.local`, use a different name with `sudo ./enable-blankbox-local.sh --name myblankbox.local --port 25265`.

## 3. Open Blank Box

- Same computer: `http://127.0.0.1:25265`
- Friendly local address when enabled: `http://blankbox.local:25265`
- LAN fallback: `http://SERVER-IP:25265`

The installer prints the recovery-key path. Use this key to claim the first owner profile and keep it for password recovery. Read it on the server with:

```sh
sudo cat /var/lib/blankbox/access-key.txt
```

Treat the recovery key like a password. Normal sign-in uses the owner username and password, not this key.

## What the installer creates

```text
/opt/blankbox/releases/     immutable application versions
/opt/blankbox/current       active-version link
/etc/blankbox/config.json   configuration
/var/lib/blankbox/          catalog, recovery key, imported media, upgrade backups
/etc/systemd/system/blankbox.service
```

Blank Box runs as the dedicated `blankbox` account. Source folders need read access for that account. Backup destinations need read and write access. Do not make private media world-writable.

## Add source and backup folders

You can use the new empty library before adding a source. When you are ready, mount the media and backup drives on the Linux computer and make sure the folders already exist. Open the configuration in a terminal with `sudo nano /etc/blankbox/config.json` (or your preferred editor). The following paths are examples: replace them with your real mounted folders, and omit any source you do not use. In nano, press Ctrl+O, Enter, then Ctrl+X to save and exit. The main fields are:

```json
{
  "data": "/var/lib/blankbox",
  "sources": ["/mnt/media", "/mnt/photos"],
  "backup": "/mnt/blankbox-backup",
  "host": "0.0.0.0",
  "port": 25265,
  "backupEveryHours": 24
}
```

Validate and restart:

```sh
sudo -u blankbox python3 /opt/blankbox/current/doctor.py --config /etc/blankbox/config.json
sudo systemctl restart blankbox
curl http://127.0.0.1:25265/health/ready
```

## Audio-CD import (experimental)

The guided `setup-linux.sh` installer includes audio-CD import by default and gives the dedicated `blankbox` service user access to the optical-drive group when available. It does not install a CD-ripping program or require an online service or subscription. The scriptable installer grants access unless `--no-audio-cd` is passed. If you deliberately opted out, rerun Blank Box setup and accept optical-drive access.

The service account must be allowed to read the optical drive. Do not grant broader disk access or make the device world-writable. Choose a preferred drive in **Settings → Optical drive**, or select one per import under **Import Media → Disc Import**. Identify the inserted audio CD, confirm the track list, and start the lossless import. Placeholder album and track names work; edit them in Blank Box later. Keep the disc inserted until the job completes. The built-in reader produces uncompressed WAV. If both `cdparanoia` and `flac` were already installed by the owner, the existing FLAC path remains available. Matching reads are a consistency check, not independent disc-accuracy certification. Automatic metadata and artwork are not required or included.

Data/photo discs can be mounted read-only and added as normal source folders for reviewed file import. Protected commercial DVD/Blu-ray copying and Live Disc playback are not part of audio-CD import.

## Upgrade and rollback

Extract the newer package and run its `setup-linux.sh` again, then choose **Install or update**. The installer verifies the package, snapshots the catalog, activates the new immutable release, and waits for readiness. Existing configuration and data are preserved.

Roll back the most recent compatible upgrade with:

```sh
sudo /opt/blankbox/current/rollback-linux.sh
```

Do not use `--restore-pre-upgrade-catalog` unless you accept losing catalog changes made after that upgrade.

## Stop or uninstall

Stop without removing data:

```sh
sudo systemctl disable --now blankbox
```

To uninstall, rerun the extracted setup wizard:

```sh
sudo ./setup-linux.sh
```

Choose **Uninstall Blank Box**. Uninstall removes startup registration and retains application, configuration, data and unrelated files. Permanent file removal is a separate manual action after verifying a backup.

Do not permanently delete `/var/lib/blankbox` until you have completed and verified a restore elsewhere.
