# Start with Blank Box

We put this guide in every Community package so you can choose the right download, start a library and protect it before depending on it.

## Choose the right download

| Your computer | Extract this ZIP | Next step |
| --- | --- | --- |
| Linux computer with systemd | `blankbox-community-VERSION.zip` | Open the extracted folder and follow [Linux](guides/LINUX.md). |
| Linux computer running Docker | The same `blankbox-community-VERSION.zip` | Follow [Docker](guides/DOCKER.md). |
| Windows 10/11 x64 | `blankbox-community-VERSION-windows-x64.zip` | Follow [Windows](guides/WINDOWS.md). The Python runtime is included. |

`blankbox-source-VERSION.zip` is for people who want to build the browser client from source. It is not the guided installer or the package to use for a first restore drill. Replace `VERSION` with the release number on the ZIP you received, and keep all files from that one package together.

The Linux/Docker ZIP contains the Linux service and Docker setup tools. The Windows ZIP contains the Windows setup tools and its own Python runtime. Both retain the same Core and in-app reference guides, so you can read help for a different computer without mixing installers.

Extract the chosen installation package into a new folder. Open that folder: you should see `RELEASE.json`, `restore.py` and the platform setup file. Check the publisher signature using an already trusted copy of `release_files.py` or compare the signing-key fingerprint through the publisher's independently verified release announcement before first installation. A checksum detects changed bytes; it does not identify the publisher.

For a **fresh empty library**, run the setup path below. For a **restore test of an existing library on a new Linux computer**, do not run the setup wizard first. Follow [Recovery](RECOVERY.md) with the extracted Community ZIP and the complete backup folder: `restore.py` creates a new data folder, then `server.py` runs the restored library. A normal setup wizard creates its own separate installation and data folder.

- Linux: `sudo ./setup-linux.sh`. Requires Python 3.10+ and systemd. See `guides/LINUX.md`.
- Docker on Linux: configure `.env` and a separate `compose.override.yaml`, then `docker compose up --detach --build --wait --wait-timeout 240`. See `guides/DOCKER.md`.
- Windows x64: extract the Windows package and open `setup-windows.cmd`. Its private Python runtime is included. See `guides/WINDOWS.md`. Windows remains experimental pending real-machine acceptance.
- Direct Python: `python3 server.py --data /path/to/new-data --port 25265`.

Open `http://127.0.0.1:25265`. Read the recovery key on the server to create your local owner profile. Keep the key privately for password recovery. Use your username and password for normal sign-in. No online account is required.

Follow [Your first library](FIRST-STEPS.md) for a short walkthrough from adding one item through restoring a backup. Expect several minutes for the initial reference-database setup on slower storage. If setup fails, keep the extracted package and use the diagnostic command in your platform guide; do not delete an existing data directory to retry.

Add physical items manually, import a reviewed title list, or configure source folders for read-only indexing. A pack match is a reference, not an owned copy. Four optional starter metapacks support offline lookup and collection organization. They install once for a new household; existing choices and removals are retained. See `METAPACKS.md`.

Folder discovery is off initially. When enabled, it offers stable files for review. Managed copying requires an explicit selection and confirmation. Your originals remain in place. Use `RECOVERY.md` to protect the catalog and any managed copies before relying on this installation.

Storage & Backup makes a compact verified catalog and managed-media backup. Settings → System & About can create a complete recovery point paired with installed offline packs and prepare a verified restore in a new location. Import can back up all indexed photos, home videos and personal files on a configured source, or up to 100 selected files per manual batch. Linked source-drive movies, music and books are not copied by a library recovery point. Use an external drive backup if you need those original bytes recoverable.

Use loopback or a trusted private network. HTTPS through your own private reverse proxy is useful for browser camera access. Playback, cameras, removable drives and network shares need acceptance on the devices you intend to use.
