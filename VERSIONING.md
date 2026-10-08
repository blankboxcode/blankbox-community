# Versions and compatibility

This stable Linux/Docker package is **1.0.1**, with catalog schema **23**. We version application packages, catalog schemas and optional metapacks independently. See [Platform status](PLATFORMS.md) for supported installation paths. The separate experimental Windows download remains **0.1.0-beta.8**, with schema **20**.

Core version, catalog schema and metapack version are separate:

| Component | This package | Update rule |
| --- | --- | --- |
| Core | 1.0.1 | Install an authenticated complete package; retain prior code and its recovery snapshot. |
| Household catalog | Schema 23 | Existing Linux/Docker catalogs migrate to 23. Version 1.0.0 cannot open schema 23; returning to older code requires its paired pre-update snapshot. |
| Metapack reader | 5 | Imported public packs require a trusted publisher signature and supported format. |
| Included metapacks | Movies 4, Books 7, Music 5, TV Shows 4 | Versioned independently; existing selections and removals are retained. |

RELEASE.json records the compatibility fields for each package. Package manifests authenticate the exact runtime files. Do not combine files from different releases or edit an installed release; configuration and household data live separately.

Core updates do not force a metapack update. Pack updates do not replace the household catalog or its Media Item IDs. Old installed packs remain usable while compatible with the reader. Failed imports leave the active pack intact. Confirmed facts, owner edits and source/copy identities remain in the catalog when a pack is removed.

There is no mandatory online update check. Download through the publisher's verified release location or transfer packages offline; verify their signatures before installation. Follow UPDATES.md for Core and METAPACKS.md for reference databases. A checksum alone is not publisher authentication.
