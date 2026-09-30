# Platform status

We use the same Core and catalog schema 20 on every target. Our installation paths and their requirements are listed below.

Choose the Linux/Docker Community ZIP for a Linux computer or the Windows x64 offline ZIP for Windows. Each installation ZIP carries setup and update tools for its target platform; the source ZIP is a separate developer artifact. Shared in-app guides may mention other platforms.

| Target | Installation model | Evidence boundary |
| --- | --- | --- |
| Linux | System Python 3.10+, SQLite FTS5, systemd for service installation | Local Python and isolated package checks; clean-machine system service/reboot acceptance must be recorded separately. |
| Docker on Linux | Locally built image, non-root user (10001:10001 by default), persistent named volume or dedicated local bind folder, read-only source mounts | Container acceptance is recorded with the exact package; optical hardware requires separate testing. |
| Windows 10/11 x64 | Included CPython 3.13.15, foreground process or per-user logon task | Experimental. Script checks on Linux are not Windows installation, NTFS, device or reboot acceptance. |

We do not claim an always-on Windows service, Windows ARM, Docker Desktop optical passthrough, universal browser codecs, transcoding or protected video-disc extraction. Our native audio-CD adapters use read-only APIs and produce WAV; optional existing Linux utilities can produce FLAC. Real-drive acceptance remains device-specific.

Large catalogs use bounded server pages, compact summaries and on-demand details. Initial indexes, broad searches, uncached collection suggestions and large folder walks may take time. Folder monitoring is optional, periodically checks metadata, and queues review after two stable observations. Network shares and low-power devices need their own measurements. A 100,000-title fixture is not a million-title performance guarantee.
