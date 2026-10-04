# Docker image delivery

We build the image from the published, signed Linux/Docker installation package. The application and starter packs stay identical to that release. The image uses Linux/amd64, a non-root account, a read-only application filesystem and a private persistent library. ARM support requires separate testing.

## Build and publish

1. Run **Actions → Build Docker image → Run workflow** on `main`. It verifies the approved ZIP and publisher signature, compares the image's runtime files, tests startup, and saves the tested image as an artifact. It does not publish.
2. Review the successful run summary and record its **build run ID** and **image archive SHA-256**. The `blankbox-docker-image` artifact contains the saved image and its build record.
3. Run **Actions → Publish reviewed Docker image → Run workflow** on the same revision. Paste those two values. This loads and publishes the saved image; it does not rebuild or replace an existing version tag.
4. Open the repository's **Packages → blankbox-community → Package settings**, find **Change visibility**, and select **Public**. Public images can be pulled without a GitHub account.
5. Save the published image digest and `blankbox-docker-publication` artifact. Verify an anonymous pull and readiness before announcing the image or activating installation links.

The publishing job uses GitHub's temporary repository token. We do not upload a publisher signing key or require a personal token. Only that job has `packages: write`. Both workflows are manual; ordinary source pushes do not publish images.

The approved input is recorded in `current-release.json`. For future application updates, review the new signed installation package, update this record, and repeat the build/review/publish steps. Keep old version tags. Each saved build must be published from the same source revision; source changes between these steps require a fresh build.

## Installation bundle

The pull-based Compose file is generated from `compose.yaml.in` with the accepted registry digest. It has no build step. The signed setup bundle includes the image descriptor, verification tools, update helper, settings example and instructions. We finalize it only after the public digest and anonymous pull are verified. This source template is not a released installation bundle; keep using the installation ZIP until the image download is announced.

Existing installations keep their Compose project, UID/GID, mounts, port and local settings when moving to the image bundle. The registry update helper pulls before stopping, makes a paired catalog/assets snapshot, checks readiness, and restores the previous image and snapshot if activation fails. Moving the library or changing its user is a separate operation.
