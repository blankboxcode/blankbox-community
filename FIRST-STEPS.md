# Your first library

We suggest starting with one item you can check easily. Add it, review its details, then try the other parts of your collection. [Wishlist and Preorders](guides/COLLECTOR-DETAILS.md#wishlist-and-preorders) can keep track of purchases along the way.

The package includes four optional reference databases; allow a few minutes for them to install on first startup. They contain reference titles, not a sample household library. You can organize your collection without internet access or connected services.

## 1. Create your owner profile

Open the address printed by your installer. On a new installation, use the recovery key stored on that computer to create your local username and password. Keep the recovery key privately, separate from the computer. An existing installation keeps its owner profile and library; sign in normally.

## 2. Choose what to organize

Complete the setup screens. Choose physical media, files, or an existing Plex/Jellyfin server. These choices describe your setup; choosing a server does not connect it. Finish its credentials and first sync in Service connections. File sources must be mounted and configured on the server before indexing. See the platform installation guide if no source is listed.

Start with one real item you can check easily:

- **Physical:** open **Add physical item**, enter the title, format and location, and search or add your entered details on that same screen. Blank Box Database searches installed reference packs; My Library finds titles you already saved. Set starting formats and title search in **Settings → Collection → Physical Media preferences**. You can also scan a barcode and review its copy details here. A title match alone does not establish the exact edition. See [Physical items and defaults](guides/COLLECTIONS.md#add-physical-items-and-choose-your-defaults).
- **Files:** index a configured source. For a large drive, use **Match all files (preview)**, inspect the counts and matching warning, then confirm the bulk links. Use **Needs review** to resolve the remaining files. Copying into managed storage is a separate, explicit action; indexing and linking leave originals where they are. See [Large library import](guides/LARGE-LIBRARY.md).
- **Plex/Jellyfin:** connect your server and sync its catalog. Check the source attached to one title. Connected access does not mean you own a physical copy.

When the title is already in your library, check whether the new source or copy belongs on it. Keep ambiguous titles or conflicting editions separate until you can confirm them. Sources and copies keep their own details when they belong to the same title.

## 3. Check the details and a collection

Open an item and confirm its title, year, editions and copy count. Use **Edit title details** for shared information or select an edition and choose **Edit this copy** for its fields. **Edit artwork** is beside the cover; **Choose details source** selects the saved information you prefer. Check playback using the file or connected-app buttons. Your edits and confirmed facts stay in your library. Save a collection, add the item, and reopen it. Reference suggestions do not add owned copies.

Library cards show connected-source and edition counts beneath the title. Wishlist and Preorders are separate planning pages in My Library and Physical Media. Use Wishlist for intended purchases and Preorders for paid orders awaiting delivery. [Purchasing guide](guides/COLLECTOR-DETAILS.md#wishlist-and-preorders).

## 4. Protect your work

Export the complete SQLite catalog to a new file and copy it to separate storage. Configure a separate writable backup destination in your platform configuration, then run a backup from Storage & Backup. A catalog export includes metadata and saved owner artwork, but not media files. The library backup covers saved records and managed copies, not linked source-drive originals. Copies of eligible personal files require a separate, confirmed Import action; follow [Recovery](RECOVERY.md).

Restore once into a **new empty directory**, start it on a different port, and compare your item ID, correction, copy count, artwork and collection. Use the restored installation only for this check; keep your main catalog authoritative. Restore commands and credentials handling are in the recovery guide.

## 5. Check the devices you will use

Restart Blank Box, sign in again and reopen the same item. Try your intended browser, phone, playback formats and storage. Camera scanning needs a browser permission and a secure context, such as localhost or HTTPS. Removing a source or a reference pack must leave your reviewed catalog record intact.

Core and metapacks have separate optional update paths. Neither an update nor a hosted metadata service is required to use your library. See [Updates](UPDATES.md) and [Metapacks](METAPACKS.md).

Collection lists can be UTF-8 CSV, TSV or text files up to 100 MB and 100,000 rows. Import Media shows a short file preview and prepares rows in the background for review. See [collection lists](guides/COLLECTIONS.md#import-a-large-collection-list).
