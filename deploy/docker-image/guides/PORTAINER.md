# Run Blank Box with Portainer

Use the prebuilt image on a Linux Intel/AMD Docker host. We’ve tested these instructions with Portainer Community Edition 2.45.1’s Web editor. You can install without building the application or signing in to GitHub.

## Start a new library

1. In Portainer, select the Docker environment that will run Blank Box. Choose **Stacks → Add stack**, name it `blankbox`, and select **Web editor**.
2. Open the [Compose file](https://raw.githubusercontent.com/blankboxcode/blankbox-community/main/deploy/docker-image/compose.yaml) and paste its complete contents into the editor once.
3. Under **Environment variables**, choose how you will connect:

   | Access | Settings and address |
   | --- | --- |
   | On the Docker host | Defaults work: open `http://127.0.0.1:25265` in a browser on that host. |
   | Another trusted home-network device | Set `BLANKBOX_BIND_ADDRESS` to `0.0.0.0`; open `http://SERVER-IP:25265`. |
   | An existing private HTTPS proxy or Tailscale Serve | Keep the loopback default and forward your proxy to `http://127.0.0.1:25265` on the Docker host. Open the proxy's own HTTPS address and port. |

   Set `BLANKBOX_PUBLISHED_PORT` if you need a different host port. `127.0.0.1` on your phone or laptop refers to that device, not the Docker host.
4. Choose **Deploy the stack** and wait for the container to become healthy. Its fresh library persists in the named volume `blankbox_blankbox-data`, using non-root user `1000:1000`.
5. Open the container's **Console**, connect with `/bin/sh`, and read the recovery key privately:

   ```sh
   cat /data/access-key.txt
   ```

   Open the selected address, create your local account and finish setup. Keep the key for password recovery.

You can also load the Compose file through Portainer's Git repository option: repository `https://github.com/blankboxcode/blankbox-community`, reference `main`, Compose path `deploy/docker-image/compose.yaml`. Leave automatic Git/image redeployment disabled until you have a checked update process with recovery points.

To add media folders or a writable backup destination, follow the examples in [Docker](DOCKER.md#2-add-media-and-backup-mounts). In the Web editor, combine them under the existing `blankbox` service. Use absolute paths on the Docker host. Keep media read-only and prepare any custom data-folder ownership before selecting another UID/GID. These mounts are optional for a first look at an empty library.

## Move an existing Docker installation

First [switch to the official image](DOCKER-MIGRATION.md) and check sign-in and your library. Handing management over to Portainer is a separate step on the same Docker host:

1. Keep the accepted setup folder, previous image and complete recovery point. Record the existing project name, UID/GID, ports, networking, mounts and any secret/config files.
2. Prepare the Web editor stack with those same settings. For an existing named data volume, replace the bottom `volumes` section with an explicit reference, using its actual name:

   ```yaml
   volumes:
     blankbox-data:
       external: true
       name: YOUR_EXISTING_VOLUME_NAME
   ```

   For an existing data bind folder, keep its same absolute host path and `/data` target. Preserve media and backup mounts, and keep your old UID/GID rather than applying the fresh-install default. Portainer does not automatically import your installation's `.env` or override files: load the variables and combine the selected Compose settings in its editor.
3. From the accepted setup folder, stop and remove the old container while retaining storage:

   ```sh
   docker compose down
   ```

   Use sudo if Docker needs it. **Omit `--volumes`.** Then deploy the prepared Portainer stack using the same project name. Only one Blank Box container may run against this library.
4. Check health, your usual address, existing sign-in, items, artwork and playback. Keep the old setup and recovery material.

Blank Box containers created outside Portainer can appear with limited stack control. Creating the stack through Portainer gives it the saved definition it needs to manage it. These instructions cover Portainer on a Linux Intel/AMD Docker host. Swarm and other architectures are outside this guide.

## Keep updates and the stack definition together

For an existing Portainer-managed stack:

1. Create a complete recovery point in **Settings → System & About** on your configured separate backup drive. Wait for it and any imports or syncs to finish. Keep the current image digest and stack settings.
2. Download and verify the new [Docker setup ZIP](https://raw.githubusercontent.com/blankboxcode/blankbox-community/main/downloads/blankbox-docker-1.0.1-1.zip) with your previously trusted verifier. Its authenticated `image.json` identifies the new image digest.
3. Pull that exact image on your Docker host before updating. This checks that it is available while the current container keeps running:

   ```sh
   docker pull ghcr.io/blankboxcode/blankbox-community@sha256:NEW_VERIFIED_DIGEST
   ```

   Replace the example with the image from the verified descriptor. Use sudo if Docker requires it.
4. In **Stacks → blankbox → Editor**, replace only the service's `image:` value with that verified image. Keep your existing project, UID/GID, networking, ports, data volume or bind folder, media mounts and configuration.
5. Choose **Update the stack**. With the image already pulled, another pull is unnecessary. Wait for health, open your usual address, sign in and check items, artwork, copies and sources.

Keep the saved stack definition on that accepted digest. Image changes do not require a new library or a new data volume. For a compatible same-schema rollback, stop the new container and return the same stack to its retained previous image. A schema downgrade or restoration of an earlier catalog needs both the earlier software and its paired catalog/assets snapshot; preserve later changes before restoring. See [Updates](../UPDATES.md#rollback) and [Recovery](../RECOVERY.md).

The checked Compose updater offers automatic stopped snapshots and failed-activation recovery for CLI-managed installations. Running it against a Portainer stack outside Portainer recreates its container through the CLI. Synchronize Portainer's saved image, user and resolved settings afterward, or a later redeployment can undo that update. An image-update button alone does not create a paired snapshot or automatically recover a failed update.

A native Linux installation needs a stopped full-library copy and review of its saved paths before moving into Docker. Do not point this fresh-install stack at native data without that migration.
