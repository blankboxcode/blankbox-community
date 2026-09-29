# Blank Box 0.1.0-beta.8

We prepared this beta for public review after the owner tested beta.7 on a Linux installation. Beta.8 keeps catalog schema 20, metapack reader 5 and the same Core library behavior. We changed the package guides and notices; we did not change the household catalog format or original source files.

- We rewrote the public guides and release text in Blank Box's owner voice. The Linux, Docker and Windows instructions identify the correct ZIP, setup path, updates, rollback and restore test steps.
- We separated license notices for components included in each package from descriptions of separately installed services. The Linux/Docker notice covers that package's dependencies; the Windows notice also identifies the included isolated CPython runtime. The public source ZIP includes its own third-party notice and a working link to it.
- We corrected the collection guide's metapack versions and coverage. This release contains one current signed copy each of Movies v4, Books v7, Music v5 and TV Shows v4; the CD proof pack is absent.

From beta.7, we keep the platform-specific setup packages: the Linux/Docker ZIP carries Linux and Docker tools, and the Windows x64 ZIP carries Windows tools and its isolated Python runtime. Both share the same Core and optional starter packs. After a portable restore, reconnect Plex/Jellyfin with a reachable address and key, then use **Settings → System & About → Restore saved provider covers** to review and fill missing covers. We preserve uploaded covers and other title details; portable backups exclude provider keys.

Beta.6's library improvements remain available. We reset Select items mode when leaving a section or page; improved EPUB page turns within long chapters; grouped audiobook files under one book title with separate listening progress; and added reviewed bulk attach actions for unlinked songs, episodes and simple split library records. We keep each selected file's source identity and require confirmation of the destination title.

For an existing Linux installation, create and verify a separate-drive recovery point before running the new package's `install-linux.sh` without new configuration flags. Our installer retains the current configuration and creates a paired pre-update catalog and pack snapshot. See [Updates](UPDATES.md) for rollback and [Recovery](RECOVERY.md) for restore review. Linked source-drive originals stay on their drives and are outside a library recovery point; protect those bytes separately if needed.

We still label Windows experimental pending real Windows and NTFS acceptance. [Platform status](PLATFORMS.md) states what has been checked for each target.
