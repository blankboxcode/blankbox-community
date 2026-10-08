# Platform status

The stable Linux/Docker package is **1.0.1**, with catalog schema **23**. The separate Windows download remains **0.1.0-beta.8**, with schema **20**. The current collection import, box-set, collector, artwork, physical-entry and OIDC features are available on Linux/Docker; they are not included in the older Windows package.

Choose the full Community ZIP for native Linux, the small setup ZIP for a prebuilt Docker image on Linux/amd64, or the Windows x64 offline ZIP for Windows. Each installation ZIP carries setup and update tools for its target platform; the source ZIP is a separate download for developers. Shared in-app guides may mention other platforms.

| Target | Installation model | Status |
| --- | --- | --- |
| Linux | System Python 3.10+, SQLite FTS5, systemd for service installation | Primary native installation path. Use the Linux guide for setup and updates. |
| Docker on Linux/amd64 | Public prebuilt image, small signed setup bundle, non-root user (1000:1000 for new installations; existing IDs retained on update), persistent named volume or dedicated bind folder | Prebuilt image with setup, update and recovery tools. Portainer Web editor instructions are available. ARM images are not available. Other Docker managers can handle updates differently. Optical hardware needs compatible host access. |
| Windows 10/11 x64 | Included CPython 3.13.15, foreground process or per-user logon task | Experimental older download. Runs in the foreground or after user sign-in. Do not use it to open a schema 23 catalog. |

Windows service installation, Windows ARM packages, transcoding and protected video-disc extraction are not available. Browser playback depends on its supported codecs. Audio-CD import reads the drive without modifying it and produces WAV; existing Linux utilities can also produce FLAC. Optical-drive access depends on the host and drive, and Docker Desktop passthrough is not supported here.

Large catalogs load pages of titles and fetch full details when you open an item. Initial indexes, broad searches, uncached collection suggestions and large folder walks may take time. Folder monitoring is optional, periodically checks metadata, and queues review after two stable observations. Performance depends on library size, storage and the device running Blank Box.
