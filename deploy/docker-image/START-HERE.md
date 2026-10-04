# Start with Blank Box

We put this guide in every Community package so you can choose the right download, start a library and protect it before depending on it.

## Choose the right download

| Your computer | Extract this ZIP | Next step |
| --- | --- | --- |
| Linux computer with systemd | `blankbox-community-VERSION.zip` | Open the extracted folder and follow [Linux](guides/LINUX.md). |
| Linux Intel/AMD computer running Docker | Small `blankbox-docker-VERSION-1.zip` | Follow [Docker](guides/DOCKER.md); the application image is pulled. |
| Windows 10/11 x64 | `blankbox-community-VERSION-windows-x64.zip` | Follow [Windows](guides/WINDOWS.md). The Python runtime is included. |

`blankbox-source-VERSION.zip` is for people who want to build the browser client from source. It is not the guided installer or the package to use for a first restore drill. Replace `VERSION` with the release number on the ZIP you received, and keep all files from that one package together.

The current Linux/Docker ZIP is 0.1.0-beta.10 (catalog schema 22) and contains Linux service and Docker setup tools. The separate experimental Windows ZIP remains 0.1.0-beta.8 (schema 20), with its own Python runtime. Follow the guides supplied with your package; the older Windows download does not include this Linux/Docker feature update and cannot open a schema 22 catalog.

Extract into a new folder. A native installation ZIP contains `RELEASE.json`, `restore.py` and platform setup files. The small Docker bundle contains `image.json`, `compose.yaml` and `setup-docker.sh` instead; it does not contain the application source. Check the publisher signature using an already trusted copy of `release_files.py` or compare the signing-key fingerprint through the publisher's independently verified release announcement before first installation. A checksum detects changed bytes; it does not identify the publisher.

For a **fresh empty library**, run the setup path below. For a **restore test of an existing library on a new Linux computer**, do not run the setup wizard first. Follow [Recovery](RECOVERY.md) with the extracted Community ZIP and the complete backup folder: `restore.py` creates a new data folder, then `server.py` runs the restored library. A normal setup wizard creates its own separate installation and data folder.

For an **existing installation**, use [Update your installation](UPDATES.md#update-your-installation). Native Linux uses `sudo ./install-linux.sh` from the new verified package to keep your configuration. Docker uses `./upgrade-docker.sh` with your existing `.env` and overrides. Keep the same library location, project name and numeric user.

- Linux: `sudo ./setup-linux.sh`. Requires Python 3.10+ and systemd. See `guides/LINUX.md`.
- Docker on Linux/amd64: configure `.env` and any `compose.override.yaml`, then run `./setup-docker.sh` from the small setup bundle. Use sudo if Docker requires it. The full ZIP local-build option remains available. See `guides/DOCKER.md`.
- Windows x64: extract the Windows package and open `setup-windows.cmd`. Its private Python runtime is included. See `guides/WINDOWS.md`. Windows remains experimental pending real-machine acceptance.
- Direct Python from the full Community ZIP: `python3 server.py --data /path/to/new-data --port 25265`.

## Choose where to open your Linux installation

| Linux setup choice | Open Blank Box here |
| --- | --- |
| **1 — On this computer** | On the computer running Blank Box: `http://127.0.0.1:25265`. |
| **2 — Trusted home network by IP** | On that computer, or another home-network device using `http://SERVER-IP:25265`. |
| **3 — The same network plus blankbox.local** | The same access as option 2, with `http://blankbox.local:25265` as an optional friendly address. The IP address still works. |

Replace `SERVER-IP` with the server's local IP address and use the port you selected. None of these choices automatically enables access from outside your home or disables outgoing Internet access. A private proxy or VPN configured separately has its own access settings. See [Linux](guides/LINUX.md) for the numbered setup steps and [Networking](guides/NETWORKING.md) if another device cannot connect.

Open the address for your chosen access mode. Direct Python and the default Docker setup use `http://127.0.0.1:25265` on the computer running them. Read the recovery key on the server to create your local owner profile. Keep the key privately for password recovery. Use your username and password for normal sign-in. No online account is required.

Follow [Your first library](FIRST-STEPS.md) for a short walkthrough from adding one item through restoring a backup. Expect several minutes for the initial reference-database setup on slower storage. If setup fails, keep the extracted package and use the diagnostic command in your platform guide; do not delete an existing data directory to retry.

Add physical items manually, import a reviewed title list, or configure source folders for read-only indexing. A pack match is a reference, not an owned copy. Four optional starter metapacks support offline lookup and collection organization. They install once for a new household; existing choices and removals are retained. See `METAPACKS.md`.

Folder discovery is off initially. When enabled, it offers stable files for review. Managed copying requires an explicit selection and confirmation. Your originals remain in place. Use `RECOVERY.md` to protect the catalog and any managed copies before relying on this installation.

Storage & Backup makes a compact verified catalog and managed-media backup. Settings → System & About can create a complete recovery point paired with installed offline packs and prepare a verified restore in a new location. Import can back up all indexed photos, home videos and personal files on a configured source, or up to 100 selected files per manual batch. Linked source-drive movies, music and books are not copied by a library recovery point. Use an external drive backup if you need those original bytes recoverable.

Use loopback or a trusted private network. HTTPS through your own private reverse proxy is useful for browser camera access. Playback, cameras, removable drives and network shares need acceptance on the devices you intend to use.
