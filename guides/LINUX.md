# Install Blank Box on Linux

We recommend this path for a dedicated Debian or Ubuntu-class Blank Box. It requires Python 3.10 or newer and systemd.

## 1. Extract the release

Use `blankbox-community-0.1.0-beta.10.zip` for Linux. The Windows ZIP is for Windows; the source ZIP is for building from source. Follow [download verification](../UPDATES.md#trust), then extract the Community ZIP. In your file manager, open the resulting `blankbox-community-0.1.0-beta.10` folder and choose **Open in Terminal**. Check that `setup-linux.sh` and `RELEASE.json` are in that folder before running the next command. For an existing installation, jump to [Upgrade and rollback](#upgrade-and-rollback). For a restore-only test of an existing library, follow [Recovery](../RECOVERY.md).

## 2. Choose access and run setup

The Linux setup wizard offers three choices for where you will open Blank Box:

| Choice | Who can connect directly | Address to open |
| --- | --- | --- |
| **1: On this computer** | A browser on the Linux computer running Blank Box. | `http://127.0.0.1:25265` on that computer. |
| **2: On my trusted home network** | This computer and other devices on your trusted home network. | `http://SERVER-IP:25265` on another device. |
| **3: Home network plus blankbox.local** | The same devices as option 2, with an optional friendly name. | `http://blankbox.local:25265`, or the same server-IP address as option 2. |

Choose 1 if you will use this computer directly. Choose 2 to use a phone, tablet or another computer at home. Choose 3 if you also want to try the friendly name. Option 3 does not provide a different kind of network access.

None of these choices automatically enables Internet access from outside your home or disables outgoing Internet connections. A private proxy or VPN you configured separately keeps its own access settings; option 1 limits the direct listener, not that separate route. See [Networking](NETWORKING.md) if you already use one.

The next prompt asks for the web port. Press Enter for `25265` on a fresh installation. Use the port you chose in every address below. When updating, keep your existing port and access choice unless you intend to change them; the guided wizard asks for these again.

For option 3, install the discovery packages before running the wizard. Options 1 and 2 do not need these local-name packages:

```sh
sudo apt update
sudo apt install python3 avahi-daemon avahi-utils iproute2
```

Then run the wizard from the extracted package folder:

```sh
sudo ./setup-linux.sh
```

Choose **Install or update**, your access choice from the table, and the web port.

The wizard is the recommended path. For scripting or advanced administration, the lower-level installer remains available:

```sh
sudo ./install-linux.sh                 # this computer only
sudo ./install-linux.sh --lan-access    # trusted LAN
sudo ./install-linux.sh --enable-local-name
```

The friendly name is optional. If another device already owns `blankbox.local`, use a different name with `sudo ./enable-blankbox-local.sh --name myblankbox.local --port 25265`, using your chosen port.

## 3. Open Blank Box

On the Linux computer running Blank Box, open `http://127.0.0.1:25265` for any of the three choices.

For option 2 or 3, find that Linux computer's local IP address in its network settings or your router's device list. Replace `SERVER-IP` with that address: for example, if it is `192.168.1.50`, open `http://192.168.1.50:25265` on your phone or other home-network device. Use the server's address, not the phone's address. Keep the server running and connect the other device to the same trusted network.

For option 3, you can also try `http://blankbox.local:25265`. If the name fails but the server-IP address works, continue using the IP address; [Networking](NETWORKING.md) explains local discovery. `127.0.0.1` on your phone refers to the phone itself.

The installer prints the recovery-key path. Use this key to claim the first owner profile and keep it for password recovery. Read it on the server with:

```sh
sudo cat /var/lib/blankbox/access-key.txt
```

Treat the recovery key like a password. Use your username and password for normal sign-in. Keep this key for account recovery.

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

You can use the new empty library before adding a source. When you are ready, mount the media and backup drives on the Linux computer and make sure the folders already exist. Open the existing configuration in a terminal with `sudo nano /etc/blankbox/config.json` (or your preferred editor). Change only the source and backup fields you need; retain the installed `data`, `host` and `port` values. In nano, press Ctrl+O, Enter, then Ctrl+X to save and exit.

The following is an example for option 1 on port `25265`; it is not a replacement for your existing configuration. Options 2 and 3 use `"host": "0.0.0.0"`. Replace the example folders with your real mounted folders and omit any source you do not use. Set `backupEveryHours` to `24` only if you want daily interval backups while Core runs; retain `null` for manual backups.

```json
{
  "data": "/var/lib/blankbox",
  "sources": ["/mnt/media", "/mnt/photos"],
  "backup": "/mnt/blankbox-backup",
  "host": "127.0.0.1",
  "port": 25265,
  "backupEveryHours": 24
}
```

Validate and restart. Replace `25265` in the health-check command with your installed port if it differs:

```sh
sudo -u blankbox python3 /opt/blankbox/current/doctor.py --config /etc/blankbox/config.json
sudo systemctl restart blankbox
curl http://127.0.0.1:25265/health/ready
```

## Audio-CD import (experimental)

The guided `setup-linux.sh` installer includes audio-CD import by default and gives the dedicated `blankbox` service user access to the optical-drive group when available. It does not install a CD-ripping program or require an online service or subscription. The scriptable installer grants access unless `--no-audio-cd` is passed. If you deliberately opted out, rerun Blank Box setup and accept optical-drive access.

The service account must be allowed to read the optical drive. Do not grant broader disk access or make the device world-writable. Choose a preferred drive in **Settings → Optical drive**, or select one per import under **Import Media → Disc Import**. Identify the inserted audio CD, confirm the track list, and start the lossless import. Placeholder album and track names work; edit them in Blank Box later. Keep the disc inserted until the job completes. The built-in reader produces uncompressed WAV. If you already installed both `cdparanoia` and `flac`, the existing FLAC path remains available. Matching reads are a consistency check, not independent disc-accuracy certification. Automatic metadata and artwork are not required or included.

Data/photo discs can be mounted read-only and added as normal source folders for reviewed file import. Protected commercial DVD/Blu-ray copying and Live Disc playback are not part of audio-CD import.

## Upgrade and rollback

Download and extract the new package into a separate folder. Create a recovery point and verify the package with your installed trusted verifier, then open a terminal in the new package folder:

```sh
python3 /opt/blankbox/current/release_files.py . --trusted-key /opt/blankbox/current/release-trust.json
sudo ./install-linux.sh
```

This keeps your existing account, library, port, access mode, sources and backup configuration. The installer snapshots the catalog and paired assets, activates the new release and waits for readiness. Open your usual address, sign in normally and refresh the browser. Keep the previous release and the printed recovery snapshot. If you want to change the listener as well, use `sudo ./setup-linux.sh` and select your intended access mode and port.

Updating from beta.8 or beta.9 migrates schema 20 to 22. Returning to that older application requires its paired pre-update catalog and assets; preserve later edits before a deliberate restore. See [Updates](../UPDATES.md#rollback) for commands and recovery preparation.

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
