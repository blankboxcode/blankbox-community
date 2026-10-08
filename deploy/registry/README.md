# Blank Box Docker image

The image runs on Linux Intel/AMD computers. It contains the same application and offline databases as the installation ZIP, with a non-root user and a persistent library under `/data`.

## Install or update

Download the [Docker setup ZIP](https://raw.githubusercontent.com/blankboxcode/blankbox-community/main/downloads/blankbox-docker-1.0.1-1.zip) and follow the [Docker guide](../../guides/DOCKER.md), or use the [Portainer guide](../../guides/PORTAINER.md). The setup pulls the image from [GitHub Container Registry](https://github.com/blankboxcode/blankbox-community/pkgs/container/blankbox-community); no local build or GitHub sign-in is needed.

For a new library, the [Compose file](../docker-image/compose.yaml) is also available. Existing libraries should use the update guide and keep their project name, user IDs, mounts and settings.

The setup includes signature verification and update tools. Its image address uses a specific registry digest so container recreation starts the same release. Personal settings belong in `.env` and supported Compose overrides.

## Your library

The application filesystem is read-only; your catalog, account and managed files stay in the persistent data location. Media folders can be mounted read-only for indexing and playback.

The updater pulls the image before stopping the old container, saves the matching catalog and assets, then checks startup. If startup fails, it restores the previous image and snapshot. Keep your previous software and recovery point. Changing storage or user IDs is a separate operation.

ARM images are not available. See [Platform status](../../PLATFORMS.md) and [Recovery](../../RECOVERY.md).
