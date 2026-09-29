# Blank Box Community

We built Blank Box to organize physical collections, local media and optional Plex/Jellyfin catalogs in one private household library. Your catalog runs on your device and works offline. You do not need a hosted account, metapack subscription or update to use it.

Start with [START-HERE.md](START-HERE.md). Linux, Docker and Windows use the same Python Core, SQLite catalog and browser client. See [PLATFORMS.md](PLATFORMS.md) for verified scope and limitations, [RECOVERY.md](RECOVERY.md) for backup and restore, and [UPDATES.md](UPDATES.md) for independent Core and metapack updates.

We make our original code source available for personal, noncommercial installation and modification under [LICENSE](LICENSE). Redistribution and commercial use require separate permission. We list included third-party components and their separate licenses in [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).

## Build from source

Use Node.js 22.13+ and Python 3.10+ with SQLite FTS5. From a newly extracted source directory:

```sh
npm ci
npm run typecheck
npm run build
python3 box/server.py --data /path/to/new-blankbox-data --port 25265
```

The runtime has no required Python packages. Node and npm are needed only to rebuild the browser client. Installation packages include its prebuilt files. Packs are optional separate data bundles. To include the distributed starter packs in a source build, copy the signed `bundled-metadata` directory from the matching installation package into `box/` before first start.

## Catalog identity

One reviewed title has one durable household Media Item ID. Local files, connected records, physical releases, owned copies, editions and confirmed reference facts keep their distinct IDs under that item. Similar names and barcode observations remain reviewable. Source loss or removing a reference pack does not erase saved catalog knowledge, owner corrections or physical ownership.

Manual cataloging and collection organization work without metadata providers. Browser playback depends on codecs; EPUB, CBZ and browser PDF reading have format limits. Plex and Jellyfin playback opens the selected service. Protected video-disc copying, transcoding, cover recognition, multiple household accounts and live retailer prices are not included.
