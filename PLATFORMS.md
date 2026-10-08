# Platform status

The stable Linux/Docker package is **1.0.1**, with catalog schema **23**. Our separate Windows download remains **0.1.0-beta.8**, with schema **20**. The current collection import, box-set, collector, artwork, physical-entry and OIDC features are available on Linux/Docker; they are not included in the older Windows package.

Choose the full Community ZIP for native Linux, the small setup ZIP for a prebuilt Docker image on Linux/amd64, or the Windows x64 offline ZIP for Windows. Each installation ZIP carries setup and update tools for its target platform; the source ZIP is a separate developer artifact. Shared in-app guides may mention other platforms.

| Target | Installation model | Status |
| --- | --- | --- |
| Linux | System Python 3.10+, SQLite FTS5, systemd for service installation | Primary native installation path. Use the Linux guide for setup and updates. |
| Docker on Linux/amd64 | Public prebuilt image, small signed setup bundle, non-root user (1000:1000 for new installations; existing IDs retained on update), persistent named volume or dedicated bind folder | Verified registry pull, setup/update and recovery path, plus Portainer CE 2.45.1 Web editor deployment. ARM, other managers and repository/automatic-update modes remain separate. Optical hardware needs compatible host access. |
| Windows 10/11 x64 | Included CPython 3.13.15, foreground process or per-user logon task | Experimental older download. Native Windows/NTFS and full-machine reboot acceptance remain incomplete. Do not use it to open a schema 23 catalog. |

We do not claim an always-on Windows service, Windows ARM, Docker Desktop optical passthrough, universal browser codecs, transcoding or protected video-disc extraction. Our native audio-CD adapters use read-only APIs and produce WAV; optional existing Linux utilities can produce FLAC. Real-drive acceptance remains device-specific.

Large catalogs use bounded server pages, compact summaries and on-demand details. Initial indexes, broad searches, uncached collection suggestions and large folder walks may take time. Folder monitoring is optional, periodically checks metadata, and queues review after two stable observations. Performance depends on library size, storage and the device running Blank Box.
