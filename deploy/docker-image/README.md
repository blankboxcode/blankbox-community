# Run Blank Box with a prebuilt Docker image

You need a Linux Intel/AMD host, Docker Engine with the Compose plugin, and Python 3.10 or newer for signature verification. This download contains the setup files; Docker pulls the application image. There is no local application build.

## New installation

Extract the Docker setup ZIP and open a terminal inside its folder. For your first download, confirm the publisher key fingerprint independently, then verify the included files and start:

```sh
python3 release_files.py .
cp -n blankbox.env.example .env
./setup-docker.sh
```

If you already have a trusted Blank Box package, verify this new folder with that package's `release_files.py` and `release-trust.json` before running any new scripts. See [Updates](UPDATES.md#trust). The bundle includes the public verifier and key; it does not establish first-download trust by itself.

If `docker info` reports permission denied but `sudo docker info` works, run `sudo ./setup-docker.sh` and use `sudo` for the Docker commands below. For updates use `sudo ./upgrade-docker.sh`. This grants access to the host's Docker service; Blank Box still runs in its container as a non-root user. Keep your Compose settings in `.env`, since `sudo` can omit shell variables.

Read the recovery key privately:

```sh
docker compose exec -T blankbox python3 -c 'print(open("/data/access-key.txt").read().strip())'
```

Open `http://127.0.0.1:25265` and use the key to create your account. The default named volume is `blankbox_blankbox-data`, owned by the container user `1000:1000`.

## Access from other devices

For direct access on this computer, leave `BLANKBOX_BIND_ADDRESS=127.0.0.1`. For access on your trusted home network, change it to `0.0.0.0` in `.env` and open `http://SERVER-IP:25265`. Apply changes with `docker compose up --detach --wait`. A friendly `blankbox.local` name requires separate host/network discovery setup. These choices do not automatically enable outside-home Internet access or disable outbound Internet.

## Your media folders and data location

Keep personal settings in `.env` and `compose.override.yaml`. The included `guides/DOCKER.md` explains read-only media mounts, backup mounts, custom UID/GID and host bind folders. You can use the same overrides with this image setup; its `compose.yaml` has no `build` entry.

Changing the process user does not change folder ownership. For a new custom UID, create a dedicated, correctly owned host data folder and bind it at `/data`. Keep source media read-only. An existing library is not copied or moved automatically.

## Update or switch from a locally built image

Create a separate complete library recovery point first. Keep the current container running. Extract the new Docker bundle into a new folder and verify it using your previously trusted verifier/key. Copy your existing `.env`, Compose overrides and any referenced secret files into that folder. Keep the same project name, port, UID/GID and every data/media/backup mount. Relative host paths must still point to the same existing folders.

Run from the new folder:

```sh
./upgrade-docker.sh
```

Use `sudo` if your Docker commands require it. The helper checks the existing container and storage, keeps its actual UID/GID, verifies and pulls the signed image digest before stopping, then makes a paired catalog/assets snapshot and waits for readiness. Failed activation restores the previous image and snapshot. Successful updates save the accepted digest and user settings in `.env`, so ordinary container recreation keeps them. A library using UID 10001 keeps 10001. No library ownership or location changes automatically.

After updating, sign in at your usual address and check an existing item and your sources. Keep the printed previous image tag and paired snapshot for recovery. Never start an older image against an incompatible newer catalog; see `UPDATES.md` and `RECOVERY.md`. A library recovery point cannot recreate missing linked originals.

For a previously created container managed through a Docker UI, keep its stack/project and mounts identical. The image has no build requirement, but each manager's deployment and update behavior requires its own check. Do not assume a manager's “update image” button creates a paired catalog snapshot.

## Normal operation

```sh
docker compose ps
docker compose logs --follow blankbox
docker compose down
docker compose up --detach --wait
```

Normal shutdown keeps your library. Do not use `down --volumes` or remove the data folder unless you intend to erase it and have verified recovery.
