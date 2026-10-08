# Play your media in Blank Box

We play supported user-provided files locally. Use media you own or have permission to use. The household acknowledgement records intended use; it does not verify ownership or change anyone’s rights.

## Connect a local file

1. Make its folder or drive readable by the computer running Core and include it in Core’s configured source directories.
2. Open **Import → Files or drive → Index existing files**. Review the file and its title before linking it. Choose the existing household title where appropriate, so physical copies and playback providers remain on one item.
3. Open the item and choose **Play in Blank Box**. The playback area shows file actions and separate **Open Plex/Jellyfin** buttons. For albums or episode groups, expand **Show tracks / Show episode files** to pick an individual file.

Indexing and playback leave originals in place. Blank Box-managed copies and digitized audio-CD tracks can also play locally. A synced Plex/Jellyfin entry by itself does not grant Core access to its original file: that folder must be configured and its local file reviewed and linked.

## What can play?

Blank Box streams the original file with authenticated byte-range requests. Your browser must support its container and codecs; an MP4 extension alone does not guarantee compatibility. The player attempts direct play and reports failure visibly. **Download for an external player** saves the source to your device for a compatible app. Blank Box does not currently transcode, invoke FFmpeg, or create HLS streams.

Music plays with track navigation, including local WAV/FLAC audio-CD imports where the browser supports them. The CD must first be digitized; the player does not stream an inserted CD drive directly. Photos display in the browser where supported. PDF uses the browser reader; managed or reviewed indexed EPUB and CBZ use Blank Box’s bounded read-only reader. Protected books, CBR, MOBI, games, and other unsupported files need an appropriate external app.

An unavailable or changed indexed file is rejected. Reconnect its drive or index and review it again. Blank Box never silently substitutes a different file. Browser format failures retain other playback choices. A source marked unavailable falls back to other usable sources. If a connected server goes offline before Blank Box knows, use the explicit local-file action in item details.

## Digital details and physical copies

**Edit title details** edits shared title credits once. **Edit files** and **Your editions → Edit this copy** open focused editors for file labels, format/edition and relevant platform/volume/issue/release identifiers. Optional edition-specific credits inherit current title details when empty; retained differing credits stay attached to that release. Format, MIME hint, size, and source location remain observed file facts. These do not establish codec support or physical-format ownership. Condition and shelf location belong to physical copies. Known editions can explicitly link a digital file to a reviewed release; the link does not add a physical copy.

## Connect Jellyfin or Plex

Connect an existing service in **Settings → Connections**. See the [connection-key guide](CONNECTION-KEYS.md) for credentials. The main action follows a selected Plex/Jellyfin details source when it is usable. Blank Box details use reachable local files first; unavailable or removed choices fall back to other usable sources. Explicit source buttons remain available.

**Open Plex** uses the saved server connection to open that exact title in Plex Web. Sign in to Plex separately if asked. The Plex server address must be reachable from your device; Blank Box does not proxy its player or media. Existing synced titles do not need a full resync for this link correction. If the server cannot be reached, check **Settings → Connections**; local files can still play.

## Match and fill title details

Open **Choose details source → Find a match**, choose **Search Blank Box Database** for installed offline packs or **Connected libraries** for synced Jellyfin/Plex records, and review the result. Applying the match immediately fills available title facts in the editor. A pack may only contain title/year/artist; descriptions or covers appear only when the selected source supplies them. Copy condition, physical location, edition and linked file details remain separate.

**Choose details source → Use these details** explicitly reapplies that source's available facts. Later manual corrections are protected during ordinary refresh. Save only real corrections; an unchanged Save does not turn every field into a manual override.

## Video discs and external apps

DVD/Blu-ray entries are catalog records. In **Information → Play your disc in an external app**, follow the guidance to open the disc drive on the computer containing it and use an authorized compatible player. The configured Core drive path can be copied. A Linux device path such as `/dev/sr0` is not a mounted folder. A phone’s browser cannot open the server’s file manager or installed player. Blank Box does not implement protected-disc playback, decryption, ripping, or a disc-byte proxy.

## Privacy and access

LAN playback is device ↔ Core only, with household authentication. Stream URLs resolve catalog item/source IDs; they are not public bearer links and cannot request arbitrary filesystem paths. Existing session expiry governs access. Playback adds no separate history table; the existing resume-progress setting remains. No new remote-access service or cloud media upload is involved.


## Choosing sources and versions

Open a title and use **Watch**, **Listen**, or **Read & listen**. Each connected app and **Local** has one playback row. **Change source** chooses another attached version or file quality without adding physical ownership. Opening or browsing a source also updates the main playback button. **Your editions** retains the separate edition/box-set chooser with copy locations and shared package details.

TV seasons and episodes follow the playback source above. Choose a season, then expand its episode list. Connected music albums load songs from the selected Jellyfin or Plex album, with disc navigation when supplied. Connected tracks and episodes appear in pages of 25; local files use pages of 20. **Open track** or **Open episode** opens that entry in its connected app. These lists describe provider availability, not physical ownership or additional library titles.

Refresh episodes/tracks beside the information and activity controls. A failed refresh keeps saved details available and offers retry. **Manage connected sources** and connected-app guidance sit at the bottom beside **Manage this item**. Available playback qualities and supported codecs still depend on the connected app or local browser.

When importing a possible match, **Keep current details** retains the title's current metadata source and manual edits. Choosing incoming details explicitly changes the metadata source. A connected source being added does not by itself replace the selected details source. Reviews remain available in Import Media until resolved.

Library totals count saved titles, TV series and music albums. Seasons, episodes, tracks, editions and copies have separate counts. A title attached to several connected apps is counted once. Separately saved entries count separately.

Clear connected duplicates can consolidate on update and sync while retaining separate cuts and sources. Conflicts and uncertain matches remain separate. See [Connected-library matching](CONNECTED-LIBRARIES.md).
