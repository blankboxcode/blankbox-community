# Run Blank Box with Portainer

Our public image runs on Linux Intel/AMD Docker hosts. We have checked deployment through Portainer Community Edition 2.45.1's Web editor, including readiness and preservation of an existing library. There is no local application build or GitHub registry sign-in requirement.

## Start a new library

1. In Portainer, select the Docker environment that will run Blank Box. Choose **Stacks → Add stack**, name it `blankbox`, and select **Web editor**.
2. Open our [Compose file](https://raw.githubusercontent.com/blankboxcode/blankbox-community/main/deploy/docker-image/compose.yaml) and paste its complete contents into the editor once.
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

Blank Box containers created outside Portainer can appear with limited stack control. Creating the stack through Portainer gives it the saved definition it needs to manage it. Other managers, Swarm, additional architectures and individual device features need their own checks.

## Keep updates and the stack definition together

Keep a verified [Docker setup ZIP](https://raw.githubusercontent.com/blankboxcode/blankbox-community/main/downloads/blankbox-docker-0.1.0-beta.10-1.zip) for signature verification and checked updates. An image-update button alone does not create a paired catalog/assets snapshot or restore a failed update.

The [checked updater](DOCKER-MIGRATION.md) must use the same project, user and complete resolved mount/network settings as the running stack. If you run it outside Portainer, it recreates the container through the CLI. Before another Portainer redeployment, synchronize its saved image digest, retained IDs and settings with the accepted `.env`; otherwise its older definition can undo your update. Use [Updates](../UPDATES.md) for verification, compatibility and rollback.

A native Linux installation needs a stopped full-library copy and review of its saved paths before moving into Docker. Do not point this fresh-install stack at native data without that migration.
