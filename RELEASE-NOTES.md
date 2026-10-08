# Blank Box Community 1.0.0

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
