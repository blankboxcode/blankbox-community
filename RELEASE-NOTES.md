# Blank Box Community 0.1.0-beta.10

## Docker image delivery

Our public prebuilt image is now available for Linux Intel/AMD. The small [Docker setup ZIP](https://raw.githubusercontent.com/blankboxcode/blankbox-community/main/downloads/blankbox-docker-0.1.0-beta.10-1.zip) verifies and pulls the image. The [Docker guide](guides/DOCKER.md) covers a Compose URL for new libraries and managers, existing-library updates, custom UID/GID and bind folders. Updates keep the existing project, user and storage and make a paired recovery snapshot. The application and catalog schema are the same as the installation ZIP below.

## Collection and library update

We added clearer item views, physical entry preferences, collector details and optional identity-provider sign-in:

- One physical-item screen for details, matching and confirmation, with saved format defaults by media type and a preferred title-search source.
- The search-default and search buttons in physical intake have clear spacing and wrap on smaller screens.
- Item details open in a popup over your library, with selectable editions, front/back artwork, visible playback and service searches, centered editors, and square, uncropped Music covers.
- Separate packaging and release-label fields, with suggested and custom values.
- Multiple saved artwork images for titles and physical editions, including front/back images and a chosen main cover.
- Digital platform purchase, redemption and code-inclusion records, with optional links and a library badge.
- Editable service names and links, custom services, and a Movies Anywhere shortcut.
- Optional OIDC sign-in linked explicitly to your existing account; local password and recovery remain available.
- UID/GID 1000:1000 for new Docker installations. Updates retain an existing installation’s numeric user, including 10001-owned data.

Linux/Docker installations on beta.8 or beta.9 upgrade from catalog schema 20 to 22, preserving existing covers, accounts and collection records. Native Linux updates keep the configured port, sources and backup destination. Docker updates keep the existing project, storage and numeric user. Follow [Updates](UPDATES.md) rather than the fresh-install commands for an existing library.

Keep the paired pre-update recovery point and prior software. An older application cannot open the upgraded catalog; use the retained pre-update snapshot for a deliberate rollback and preserve later edits separately.

The separate Windows download remains the experimental beta.8 package with schema 20; it does not include these changes. Check OIDC sign-in and recovery with your actual provider before relying on it.
