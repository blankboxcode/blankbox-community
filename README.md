<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="public/brand/blankbox-logo-light.png">
    <source media="(prefers-color-scheme: light)" srcset="public/brand/blankbox-logo-dark.png">
    <img src="public/brand/blankbox-logo-dark.png" alt="Blank Box" width="550" height="240">
  </picture>
</p>

<p align="center"><strong>Own it. Preserve it. Bring it home.</strong></p>

<p align="center">
  <a href="#download">Download</a> ·
  <a href="#install-from-a-zip">ZIP installation</a> ·
  <a href="#quick-start-with-docker">Docker quick start</a> ·
  <a href="https://github.com/blankboxcode/blankbox-community/wiki">Wiki</a> ·
  <a href="https://github.com/blankboxcode/blankbox-community/issues/new/choose">Feedback &amp; help</a>
</p>

# Your collection, in one private library

We built Blank Box Community to bring physical collections, files on your own drives and optional Plex/Jellyfin catalogs together. Keep track of what you own, where it lives and how you can enjoy it, with a catalog that runs on your computer and works offline.

- **Organize physical media:** record copies, editions and locations; build collections and track what you intend to buy.
- **Connect your files:** index mounted drives and link files in place without copying or renaming originals.
- **Look up titles offline:** four included optional signed metapacks help with reference facts and organization. They contain no media or cover art.
- **Enjoy compatible media:** play browser-compatible files, read supported EPUB/CBZ documents, or open connected Plex/Jellyfin sources in their own service.
- **Keep your library yours:** save corrections and artwork, export your catalog and create checked recovery points for records and managed copies.

No Blank Box online account, subscription or connected media server is required. Browser codec and format limits apply; transcoding and protected video-disc copying are not included.

## Download

The current installation prerelease is **0.1.0-beta.8**.

| Your installation | Download | Instructions |
| --- | --- | --- |
| Linux with systemd | [Linux / Docker ZIP](https://github.com/blankboxcode/blankbox-community/releases/download/v0.1.0-beta.8/blankbox-community-0.1.0-beta.8.zip) | [Linux ZIP install](#linux) |
| Docker on Linux | The same [Linux / Docker ZIP](https://github.com/blankboxcode/blankbox-community/releases/download/v0.1.0-beta.8/blankbox-community-0.1.0-beta.8.zip) | [Docker quick start](#quick-start-with-docker) |
| Windows 10/11 x64 — **experimental** | [Windows x64 ZIP](https://github.com/blankboxcode/blankbox-community/releases/download/v0.1.0-beta.8/blankbox-community-0.1.0-beta.8-windows-x64.zip) | [Windows ZIP install](#windows-experimental) |

**Installation ZIPs include the prebuilt interface: you do not need Node.js, npm or a source build.** Windows includes its own Python runtime; native Linux needs Python 3.10+.

[All release files and checksums](https://github.com/blankboxcode/blankbox-community/releases/tag/v0.1.0-beta.8) · [Verify your download](https://github.com/blankboxcode/blankbox-community/blob/v0.1.0-beta.8/UPDATES.md#trust) · [Platform status](https://github.com/blankboxcode/blankbox-community/blob/v0.1.0-beta.8/PLATFORMS.md)

Verify the package before running setup. A checksum detects changed bytes; first-download publisher trust needs independent confirmation of the signing-key fingerprint. The verification guide explains the trusted verifier.

These quick starts create a **fresh library**. For an existing library, follow [Updates](https://github.com/blankboxcode/blankbox-community/blob/v0.1.0-beta.8/UPDATES.md) or [Recovery](https://github.com/blankboxcode/blankbox-community/blob/v0.1.0-beta.8/RECOVERY.md). GitHub's automatic source archives and the source ZIP are developer downloads, not the guided installation package.

## Install from a ZIP

### Linux

Requires a Debian/Ubuntu-class computer with **Python 3.10+ and systemd**.

1. Download and extract the **Linux / Docker ZIP** above.
2. Open the extracted `blankbox-community-0.1.0-beta.8` folder until you see `setup-linux.sh` and `RELEASE.json`. Choose **Open in Terminal** in your file manager.
3. Run:

   ```sh
   sudo ./setup-linux.sh
   ```

4. Choose **Install or update**, select an access mode and use port `25265` for a fresh installation unless you need another port. Blank Box then runs as a background service.

| Linux access choice | Open Blank Box here |
| --- | --- |
| **1 — This computer** | On the server computer: `http://127.0.0.1:25265`. |
| **2 — Trusted home network by IP** | On the server or another trusted home-network device: `http://SERVER-IP:25265`. |
| **3 — The same network plus blankbox.local** | The same access as option 2, plus `http://blankbox.local:25265` where discovery works. The IP address still works. |

Replace `SERVER-IP` with the server's local address from its network settings or your router's device list. Use your chosen port in every address. Option 3 needs optional Avahi discovery packages **before** running setup; see the [Linux guide](https://github.com/blankboxcode/blankbox-community/blob/v0.1.0-beta.8/guides/LINUX.md).

Read the recovery key privately on the server:

```sh
sudo cat /var/lib/blankbox/access-key.txt
```

Open your chosen address, use the key to create your local owner username/password and complete setup. Keep the key for password recovery; normal sign-in uses your username and password.

None of the three access choices automatically enables outside-home Internet access or disables outgoing Internet. A private proxy or VPN configured separately has its own settings. [Networking help](https://github.com/blankboxcode/blankbox-community/wiki/Access-on-Your-Home-Network)

### Windows (experimental)

1. Download the **Windows x64 ZIP** and choose **Extract All** in File Explorer.
2. Open the extracted folder and double-click `setup-windows.cmd`. Choose **Install or update** and follow the prompts.
3. After setup, open PowerShell and start Blank Box:

   ```powershell
   powershell.exe -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\BlankBox\start-windows.ps1"
   ```

4. Keep that window open. Open `http://127.0.0.1:25265`, using your chosen port if different. Read `%LOCALAPPDATA%\BlankBox\data\access-key.txt` privately to claim your owner profile.

The optional startup task runs **after user sign-in**, not as an always-on Windows service. Native Windows/NTFS acceptance remains open. [Full Windows guide](https://github.com/blankboxcode/blankbox-community/blob/v0.1.0-beta.8/guides/WINDOWS.md)

## Quick start with Docker

Requires a **Linux host with Docker Engine and the Docker Compose plugin**. Host Python 3.10+ is used by the package verification tools. We build the image locally from the installation ZIP; there is no published Blank Box registry image. The first build may download the pinned Python base image.

1. Download, verify and extract the **Linux / Docker ZIP** above.
2. Open a terminal in the extracted `blankbox-community-0.1.0-beta.8` folder. Check that `compose.yaml`, `Dockerfile` and `blankbox.env.example` are visible.
3. Start a fresh empty library:

   ```sh
   cp -n blankbox.env.example .env
   docker compose up --detach --build --wait --wait-timeout 240
   ```

4. Read the first-owner recovery key privately:

   ```sh
   docker compose exec -T blankbox python3 -c 'print(open("/data/access-key.txt").read().strip())'
   ```

5. Open **[http://127.0.0.1:25265](http://127.0.0.1:25265)** on the Docker host, claim your owner profile and complete setup.

To connect another device on your **trusted home network**, change these values in your local `.env`:

```dotenv
BLANKBOX_BIND_ADDRESS=0.0.0.0
BLANKBOX_PUBLISHED_PORT=25265
```

Run `docker compose up --detach --wait --wait-timeout 240` to apply the change, then open `http://SERVER-IP:25265` on the other device. Use the host's local IP and your selected port. This does not set up outside-home access, a friendly name or HTTPS.

Your library persists in the `blankbox_blankbox-data` named volume. `docker compose down` retains it; omit `--volumes` when keeping the library. Follow the [Docker guide](https://github.com/blankboxcode/blankbox-community/blob/v0.1.0-beta.8/guides/DOCKER.md) to add read-only source mounts, a writable backup mount and permissions for UID/GID `10001`. This empty-library quick start does not mount your drives or configure backups automatically.

## Build your first library

Add one physical item, index a configured folder or deliberately connect Plex/Jellyfin. Check one title and its sources before importing your whole collection. Your corrections and confirmed facts stay in the saved household catalog.

[First-library walkthrough](https://github.com/blankboxcode/blankbox-community/blob/v0.1.0-beta.8/FIRST-STEPS.md) · [Setup help](https://github.com/blankboxcode/blankbox-community/issues/new?template=02-setup-help.yml) · [Wiki](https://github.com/blankboxcode/blankbox-community/wiki)

## Protect and update your library

Use a separate backup drive and test a restore into a **new empty destination**. Library recovery protects saved records, managed copies and paired offline-pack assets. It **cannot recreate missing linked source-drive originals**; protect those bytes separately. Portable restore excludes account/provider secrets, so reconnect Plex/Jellyfin afterward.

Core and metapacks update independently and optionally. Keep earlier software and paired recovery material for rollback. [Recovery](https://github.com/blankboxcode/blankbox-community/blob/v0.1.0-beta.8/RECOVERY.md) · [Updates](https://github.com/blankboxcode/blankbox-community/blob/v0.1.0-beta.8/UPDATES.md)

## Feedback and support

We welcome [bugs, setup questions, feedback and beta test results](https://github.com/blankboxcode/blankbox-community/issues/new/choose). Include your exact version, device/OS, action, expected result and actual result. Keep household titles, paths, credentials, catalogs and backups out of public reports. Support is best effort.

[Feedback guide](FEEDBACK.md) · [Support](SUPPORT.md) · [Focused beta checks](https://github.com/blankboxcode/blankbox-community/wiki/Beta-Test-Checklist)

## License and source builds

Our original code is **source available for personal, noncommercial use** under [LICENSE](LICENSE). Redistribution and commercial use require separate permission. Third-party components retain their own licenses; see [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).

<details>
<summary>Build the browser client from source (developers)</summary>

Use Node.js 22.13+, Python 3.10+ and SQLite FTS5:

```sh
npm ci
npm run typecheck
npm run build
python3 box/server.py --data /path/to/new-blankbox-data --port 25265
```

The Core has no required third-party Python packages. To include the distributed starter packs in a source build, copy the signed `bundled-metadata` directory from the matching installation package into `box/` before first start.

</details>
