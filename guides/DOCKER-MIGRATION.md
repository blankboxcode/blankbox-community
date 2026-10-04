# Switch to the official Docker image

Already running Blank Box from an image you built locally? You can switch to our prebuilt image on the same Linux Intel/AMD Docker host. Your library stays in its existing volume or folder. You do not need a new account or a larger Compose file.

## Five steps

1. Create a complete recovery point in **Settings → System & About → Update Blank Box software**. Keep your current container running.
2. Download the small [Docker setup ZIP](https://raw.githubusercontent.com/blankboxcode/blankbox-community/main/downloads/blankbox-docker-0.1.0-beta.10-1.zip), extract it into a new folder, and [verify it using your previously trusted package](../UPDATES.md#trust).
3. Copy your current `.env`, Compose override files and referenced secret files into that new folder. Keep the same project name, UID/GID, port, media mounts and data volume or bind folder. Relative bind paths must still point to the same existing folders. Keep access settings in `.env`; sudo can omit settings exported only in your terminal. For trusted home-network access, keep `BLANKBOX_BIND_ADDRESS=0.0.0.0` there.
4. Open a terminal in the new setup folder, where `image.json` and `upgrade-docker.sh` are visible, and run:

   ```sh
   ./upgrade-docker.sh
   ```

   If Docker needs sudo on your host, use:

   ```sh
   sudo ./upgrade-docker.sh
   ```

   You can invoke the Bash script with `sudo bash ./upgrade-docker.sh` if it does not execute directly.

5. Open your usual address, sign in, refresh the browser and check existing items, artwork and sources. Keep the previous image and paired snapshot printed by the updater.

The updater verifies and pulls the signed image digest before stopping. It checks your existing user and storage, makes a paired catalog/assets snapshot, waits for readiness, then saves the accepted image and retained user IDs. Failed activation restores the previous image and paired catalog. Existing `10001:10001` installations keep those IDs; switching to the image does not change library ownership.

The official-image updater preserves the incoming `.env` file's ownership. If an earlier update left it root-owned, restore its intended Linux-user ownership before copying it. This file owner is separate from the container's UID/GID.

Do not use `setup-docker.sh` or the fresh-install Compose URL for this transition. Do not delete the old volume. Move storage, change user IDs or [switch management to Portainer](PORTAINER.md#move-an-existing-docker-installation) after the image update works.

See [Docker](DOCKER.md) for full configuration and [Updates and rollback](../UPDATES.md) for schema compatibility and recovery. This guide is for existing Docker installations; a native Linux installation needs its own stopped-library migration.
