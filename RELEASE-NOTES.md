# Blank Box Community 1.0.1

## Preorders and Wishlist

Track purchased titles awaiting delivery separately from your owned library. Save title, edition, label, vendor, quantity, price, dates, tracking and notes. Receive a whole order or a partial delivery as physical copies or digital purchase records, with a prefilled new-item form or reviewed library/offline match. Received and cancelled history stays searchable. Select several orders to review their deliveries one at a time; removing an order keeps copies already received.

Wishlist holds titles you plan to buy. Convert an entry to a preorder or add an already purchased copy directly to your library. My Library and Physical Media offer both planning pages, a Preorders button sits beside Add media, and optional sidebar shortcuts start off. [Purchasing guide](guides/COLLECTOR-DETAILS.md#wishlist-and-preorders)

## Clearer playback and editions

Watch and Listen show one row for each connected app and Local. Change source chooses that app's version or quality and updates the main playback button. Seasons, episodes, albums, discs and songs follow the selected source in compact paged lists. Track actions stay horizontal; refresh and source management sit beside the item controls.

Library cards show title above year/type, source count and edition count. Plex/Jellyfin copies of the same standard cut count as one edition; named cuts and physical releases stay distinct. A saved title has at least one standard edition. Episodes, tracks and qualities do not inflate library title counts. Reselecting My Library clears its search.

## Connected-library matching

Clear existing Plex/Jellyfin duplicates consolidate during the first startup after updating and after later syncs. Matching uses supplied film/series identifiers or compatible title/year evidence; albums require the same normalized title, edition and artist, with known years equal or one apart. Different cuts remain attached to their work. A combined-film supercut stays separate from its component films.

Conflicting identities, incompatible manual edits or progress, ambiguous matches, pending reviews and saved separate-title choices remain separate. Retained details, provider preference, sources, files, copies, artwork and activity stay with the joined title; old item IDs resolve to it. Older provider records missing identifiers gain supplied evidence during an ordinary sync. Manual-only titles are outside this automatic cleanup. [Matching rules](guides/CONNECTED-LIBRARIES.md)

Keep current details now retains the selected details provider, manual corrections and provenance when adding another connected source. Match review closes while confirmation runs in the background, shows progress and keeps unresolved reviews available. Settings saves work when adding another provider and preserve concurrently saved settings.

## Faster browsing and Settings fixes

Library pages use cached compact cards and bounded reads, retain the grid while refreshing, and recover from stale or failed requests. Cards need no separate detail request to count sources or editions. Docker reference indexing uses the data disk for SQLite scratch instead of the small temporary mount.

Streaming and digital service links and OIDC settings each appear once. Join our [Discord community](https://discord.com/invite/fD8k4sn9sk) from beside the version on every Settings tab.

## Updating and recovery

Version 1.0.1 uses API 1, catalog schema 23 and metapack reader 5. Updating a schema 22 library adds preorder and delivery tables. Clear provider consolidation can reduce the number of duplicate title records while retaining their sources and copies. Initial reference/card indexes and consolidation run in the background; allow them to finish before importing or syncing again.

Create a complete recovery point before updating. Keep version 1.0.0 and its paired pre-update catalog/assets snapshot: it cannot open schema 23, and changing the application alone does not undo consolidation. Preserve later work before restoring an earlier state. Complete catalog exports and recovery include preorders and delivery history. [Updates](UPDATES.md) · [Recovery](RECOVERY.md)

Linux and Docker remain the stable targets; the public image is Linux/amd64. Windows remains the separate older experimental download. Multi-user libraries, ARM images, transcoding, automatic online artwork and carrier polling are not included.

## Version 1.0.0

Our first stable Linux/Docker release brings large collection imports and searchable physical box sets to Blank Box.

## Collection imports

- Import UTF-8 CSV, TSV or text lists up to 100 MB and 100,000 rows.
- Choose a file, check its columns and prepare rows in the background with progress. A short preview keeps large files manageable.
- Import blu-ray.com collection exports with recognized disc formats, film years, studio, runtime, purchase price and comments. Site release IDs stay separate from barcodes; disc dates stay separate from film dates.
- Review exact title/release matches and repeated rows. Loose title suggestions are optional, and different TV seasons stay separate.
- Fill missing details from installed offline database packs after reviewing a match. Existing entered details stay intact.
- Review 25 rows per page. Save the displayed rows with their selected database details, or turn database review off to add up to 200 ready rows at once.
- Resume a completed review after closing the screen or restarting. Uploading and preparing rows do not add titles or change media files.

## Physical box sets

One owned package can contain several movies or TV seasons. Included titles remain searchable and retain their own details and playback sources. Open its package card to manage contents, location, packaging and release label. A three-film set is one package, one owned copy and three titles; separately owned editions stay separate.

## Your existing library

Version 1.0.0 keeps API 1, catalog schema 22 and metapack reader 5. Current Linux/Docker libraries update without a schema migration. Older schema 20 Linux/Docker libraries migrate to schema 22. Accounts, artwork, saved connections, copies, pack choices and source paths are retained.

Use [Updates](UPDATES.md) for an existing library. Keep the previous application/image and a paired recovery point. Linked media remains on its source drive; a catalog backup cannot recreate missing originals.

Docker uses our prebuilt Linux/amd64 image, with no local build required. Native Linux uses the installation ZIP. New Docker libraries default to UID/GID 1000:1000; updates retain the existing user and storage. Windows remains a separate older experimental download and does not include these changes.

The existing item popup, edition artwork, square Music covers, physical entry defaults, digital-platform records, editable service links and optional OIDC remain available. Multi-user accounts and automatic online artwork lookup are not included. Offline database coverage varies by installed pack.
