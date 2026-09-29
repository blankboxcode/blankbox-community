# Your first library

We include four optional reference databases; allow a few minutes for them to install on first startup. They contain reference titles, not a sample household library. You can organize your collection without internet access or connected services.

## 1. Create your owner profile

Open the address printed by your installer. On a new installation, use the recovery key stored on that computer to create your local username and password. Keep the recovery key privately, separate from the computer. An existing installation keeps its owner profile and library; sign in normally.

## 2. Choose what to organize

Complete the setup screens. Choose physical media, files, or an existing Plex/Jellyfin server. These choices describe your setup; choosing a server does not connect it. Finish its credentials and first sync in Service connections. File sources must be mounted and configured on the server before indexing. See the platform installation guide if no source is listed.

Start with one real item you can check easily:

- **Physical:** open Physical Media, enter its title or scan its barcode, review the proposed title and edition, and record its format and location. A title match alone does not establish the exact edition.
- **Files:** index a configured source. For a large drive, use **Match all files (preview)**, inspect the counts and matching warning, then confirm the bulk links. Use **Needs review** to resolve the remaining files. Copying into managed storage is a separate, explicit action; indexing and linking leave originals where they are. See [Large library import](guides/LARGE-LIBRARY.md).
- **Plex/Jellyfin:** connect your server and sync its catalog. Check the source attached to one title. Connected access does not mean you own a physical copy.

When the same title already exists, review attaching the new evidence to it. Keep ambiguous titles or conflicting editions separate until you can confirm them. Each reviewed title has one stable Media Item ID; its sources, releases and copies have their own IDs.

## 3. Check the details and a collection

Open the item's details and Sources. Confirm title, year, edition and copy count. Correct one field and save it. Choose the details source you prefer; your own edits and confirmed facts remain in the household catalog. Save a collection, add the item, and reopen it. Reference suggestions are not ownership records and require review.

## 4. Protect your work

Export the complete SQLite catalog to a new file and copy it to separate storage. Configure a separate writable backup destination in your platform configuration, then run a backup from Storage & Backup. A catalog export includes metadata and saved owner artwork, but not media files. The library backup covers saved records and managed copies, not linked source-drive originals. Copies of eligible personal files require a separate, confirmed Import action; follow [Recovery](RECOVERY.md).

Restore once into a **new empty directory**, start it on a different port, and compare your item ID, correction, copy count, artwork and collection. Use the restored installation only for this check; keep your main catalog authoritative. Restore commands and credentials handling are in the recovery guide.

## 5. Check the devices you will use

Restart Blank Box, sign in again and reopen the same item. Try your intended browser, phone, playback formats and storage. Camera scanning needs a browser permission and a secure context, such as localhost or HTTPS. Removing a source or a reference pack must leave your reviewed catalog record intact.

Core and metapacks have separate optional update paths. Neither an update nor a hosted metadata service is required to use your library. See [Updates](UPDATES.md) and [Metapacks](METAPACKS.md).
