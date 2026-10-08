<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="public/brand/blankbox-logo-light.png">
    <source media="(prefers-color-scheme: light)" srcset="public/brand/blankbox-logo-dark.png">
    <img src="public/brand/blankbox-logo-dark.png" alt="Blank Box" width="550" height="240">
  </picture>
</p>

<p align="center"><strong>Own it. Preserve it. Bring it home.</strong></p>

<p align="center">
  <a href="#install-with-docker">Docker</a> ·
  <a href="#install-from-a-zip">ZIP installation</a> ·
  <a href="#updates">Updates</a> ·
  <a href="https://github.com/blankboxcode/blankbox-community/wiki">Wiki</a> ·
  <a href="https://github.com/blankboxcode/blankbox-community/issues/new/choose">Feedback &amp; help</a>
</p>

# Your collection, in one private library

We built Blank Box Community to bring physical collections, files on your own drives and optional Plex/Jellyfin catalogs together. See what you own, where it lives and how to enjoy it, in a library that runs on your computer and works offline.

- **Catalog your collection:** record discs, books, records and other physical media, with editions, packaging, release labels, locations and front/back artwork.
- **Import a collection list:** bring in CSV, TSV or text files up to 100 MB and 100,000 rows, including blu-ray.com exports. Review matches and optional offline details before saving.
- **Organize box sets:** keep one physical package with searchable movies or seasons inside it, alongside separately owned copies.
- **Connect your files and services:** link files on mounted drives in place, or sync an existing Plex/Jellyfin catalog. Your originals stay where they are.
- **Find details offline:** optional signed Movies, TV, Books and Music database packs help with titles and reference facts. Coverage varies; these packs contain no media or cover art.
- **Choose how to enjoy a title:** browse editions and artwork, play compatible files, read supported EPUB/CBZ documents, or open a connected service. Record digital purchases and redeemed codes separately from playback.
- **Plan your next purchase:** keep a Wishlist and track paid Preorders, receive partial deliveries and retain order history. [Purchasing guide](guides/COLLECTOR-DETAILS.md#wishlist-and-preorders).
- **Keep your library yours:** save corrections, export your catalog and create recovery points for your records and managed copies.

No Blank Box online account, subscription or connected media server is required. Browser formats and codecs determine what plays directly; Blank Box does not transcode.

## Download

**Blank Box Community 1.0.1** is the stable release for Linux and Docker. The interface is already built; no Node.js, npm or source build is needed to install it.

| How you want to run it | Download | Guide |
| --- | --- | --- |
| Docker on Linux Intel/AMD | [Small Docker setup ZIP](https://raw.githubusercontent.com/blankboxcode/blankbox-community/main/downloads/blankbox-docker-1.0.1-1.zip) | [Docker](guides/DOCKER.md) |
| Linux background service | [Linux installation ZIP](https://github.com/blankboxcode/blankbox-community/releases/download/v1.0.1/blankbox-community-1.0.1.zip) | [Linux](guides/LINUX.md) |
| Windows 10/11 x64, experimental | [Earlier Windows package](https://github.com/blankboxcode/blankbox-community/releases/download/v0.1.0-beta.8/blankbox-community-0.1.0-beta.8-windows-x64.zip) | [Windows](guides/WINDOWS.md) |

[Release files and checksums](https://github.com/blankboxcode/blankbox-community/releases/tag/v1.0.1) · [Verify a download](UPDATES.md#trust) · [Platform status](PLATFORMS.md)

Verify the package before running setup. For your first download, confirm the signing-key fingerprint through an independently trusted Blank Box channel. For updates, use your existing trusted verifier. GitHub's source archives are developer downloads.

## Install with Docker

Requires Docker Engine and the Compose plugin on a Linux Intel/AMD host, plus Python 3.10+ for verification and checked updates. We provide a public image from GitHub Container Registry; no local application build or GitHub sign-in is needed.

1. Download, verify and extract the **Docker setup ZIP**. Open a terminal in its folder.
2. Start a new library:

   ```sh
   cp -n blankbox.env.example .env
   ./setup-docker.sh
   ```

   Use `sudo ./setup-docker.sh` if your host requires sudo for Docker.

3. Read the recovery key privately:

   ```sh
   docker compose exec -T blankbox python3 -c 'print(open("/data/access-key.txt").read().strip())'
   ```

   Use `sudo docker compose` if needed. Keep this key private for password recovery.

4. Open **[http://127.0.0.1:25265](http://127.0.0.1:25265)** on the Docker host, create your local account and complete setup.

For another device on your trusted home network, set `BLANKBOX_BIND_ADDRESS=0.0.0.0` in `.env`, then run `docker compose up -d --wait`. Open `http://SERVER-IP:25265`, using your host's local IP and chosen port. Outside-home access and HTTPS require your own separate setup.

Your library stays in the persistent `blankbox_blankbox-data` volume. Keep it when updating or recreating containers. The [Docker guide](guides/DOCKER.md) covers media mounts, backups, custom UID/GID and bind folders.

**Portainer:** follow the [Portainer guide](guides/PORTAINER.md) or use repository `https://github.com/blankboxcode/blankbox-community`, branch `main`, Compose path `deploy/docker-image/compose.yaml`. The [Compose file](https://raw.githubusercontent.com/blankboxcode/blankbox-community/main/deploy/docker-image/compose.yaml) uses our prebuilt image.

## Install from a ZIP

### Linux

Requires Python 3.10+ and systemd on a Debian/Ubuntu-class computer.

1. Download, verify and extract the **Linux installation ZIP**.
2. Open a terminal in the extracted `blankbox-community-1.0.1` folder, where `setup-linux.sh` and `RELEASE.json` are visible.
3. Run:

   ```sh
   sudo ./setup-linux.sh
   ```

4. Choose **Install or update**, then choose where to open Blank Box:

   | Choice | Address |
   | --- | --- |
   | 1: This computer | `http://127.0.0.1:25265` on the computer running Blank Box. |
   | 2: Trusted home network by IP | `http://SERVER-IP:25265` on this computer or another home-network device. |
   | 3: The same network plus blankbox.local | The same IP access, plus `http://blankbox.local:25265` where discovery works. |

   Use your chosen port if different. Option 3 needs optional discovery packages; see [Linux](guides/LINUX.md).

5. Read the recovery key privately, then open your chosen address and create your local account:

   ```sh
   sudo cat /var/lib/blankbox/access-key.txt
   ```

None of these access choices automatically enables outside-home Internet access or disables outgoing Internet. A separately configured private proxy or VPN keeps its own settings.

### Windows, experimental

The earlier Windows package includes Python. Extract it, open `setup-windows.cmd` and follow its [Windows guide](guides/WINDOWS.md). It does not include the current Linux/Docker features and cannot open a schema 23 catalog.

## Make it your library

Start with a shelf, a folder or a connected catalog, then add the rest at your own pace.

- **Import Media:** import and review a collection list, index configured folders, or connect a Plex/Jellyfin catalog.
- **Physical Media:** add copies, save entry defaults and manage movie/TV box sets.
- **Item details:** choose editions, artwork, playback, streaming searches and digital-platform records in a popup over your library.
- **Wishlist and Preorders:** open them from My Library or Physical Media, or enable their optional sidebar links.
- **Collections:** organize custom groups and rules, locations, favorites and activity.
- **Settings:** manage service links, offline database packs, local account recovery and optional OIDC.

[First steps](FIRST-STEPS.md) · [Collection imports and box sets](guides/COLLECTIONS.md) · [Artwork and collector details](guides/COLLECTOR-DETAILS.md) · [Playback](guides/PLAYBACK.md) · [Accounts](guides/ACCOUNTS.md) · [Wiki](https://github.com/blankboxcode/blankbox-community/wiki)

A catalog entry does not create a playable file or prove digital ownership. Database facts depend on installed packs; artwork can be uploaded manually. Blank Box currently uses one shared household account.

## Updates

Create a complete recovery point, download and verify the new package, and keep the same library and settings.

- **Native Linux:** run `sudo ./install-linux.sh` from the new verified installation folder.
- **Docker Compose:** copy your existing `.env` and supported Compose override into the new verified Docker setup folder, then run `./upgrade-docker.sh` with sudo if Docker needs it.
- **Portainer:** follow the [stack update guide](guides/PORTAINER.md#keep-updates-and-the-stack-definition-together) so its saved definition and recovery point match the accepted image.

Open your usual address and refresh the browser. Keep the previous software and paired recovery snapshot. [Full update and rollback guide](UPDATES.md) · [Older local-image migration](guides/DOCKER-MIGRATION.md)

## Protect your library

Use separate storage and test a restore into a new empty destination. A library recovery point protects catalog records and managed copies. It **cannot recreate missing linked originals** on your source drives; back up those separately. Core and database packs update independently.

[Recovery](RECOVERY.md) · [Offline packs](METAPACKS.md)

## Feedback and support

We welcome [bugs, questions and suggestions](https://github.com/blankboxcode/blankbox-community/issues/new/choose). Include the installed version, device/OS, steps and expected result. Keep credentials, household catalogs and private paths out of public reports.

[Join us on Discord](https://discord.com/invite/fD8k4sn9sk) · [Feedback guide](FEEDBACK.md) · [Support](SUPPORT.md)

## License and source builds

Our code is source available for personal, noncommercial use under [LICENSE](LICENSE). Redistribution and commercial use require separate permission. Third-party components retain their own licenses; see [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).

<details>
<summary>Build from source</summary>

Use Node.js 22.13+, Python 3.10+ and SQLite FTS5:

```sh
npm ci
npm run typecheck
npm run build
python3 box/server.py --data /path/to/new-blankbox-data --port 25265
```

The Core has no required third-party Python packages. Starter packs can be copied from the matching installation package into `box/bundled-metadata` before first start.

</details>
