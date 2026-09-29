# Import a large drive

We designed this path to build catalog links from a drive you already have. The drive's original files remain where they are unless you separately confirm a managed or personal-file copy.

Add the mounted drive or folder to Blank Box's `sources` configuration and make it readable by the Core account. Open **Import → Files on a drive or folder**, select that source, and choose **Index source**. Indexing records paths, sizes, dates and filename/folder clues. It does not copy, hash, rename or delete the files. Keep the drive mounted until indexing finishes.

Before a large catalog change, export the catalog or run a verified catalog backup to separate storage. Linked originals remain on their existing drive and are not included in the catalog backup. See [Recovery](../RECOVERY.md).

After the inventory says **complete**, choose **Match all files (preview)**. The preview shows:

- Files that can attach to one existing Media Item, including titles previously brought in from a connected Plex or Jellyfin catalog.
- Files that can form new Media Items, and how many new titles those files represent.
- Unique matching references found in installed offline metapacks for new titles with a usable year.
- Files already linked, and files that still need review.

The matching is best effort. Common names, conflicting years, weak filenames, alternate editions and multiple possible household items stay for review. Some movies and other files will need manual matching after import. A pack record helps identify a title; it does not prove ownership, an exact physical edition or that the file is playable.

Read the counts and warning, tick the confirmation, then choose **Link files**. This adds catalog source links in place. It never copies, moves, renames, deletes or overwrites the original media. Progress appears in the import screen; a large batch may take several minutes. Keep Blank Box and the drive available until it finishes. If a file changes or disappears, Blank Box skips it and reports the error. Completed links remain recorded after a restart; run a fresh preview to continue.

Choose **Needs review** to see unlinked or changed files. Open **Review & link** for each remaining file, correct its title/type/year, then select the existing Media Item or create a separate one. Do not merge an ambiguous title on name alone. Reindex after changing files or reconnecting a replaced drive.

For personal files on that source drive, choose **Back up all indexed personal files** in the same Import section. Review the file count and total bytes before confirming; the job copies and verifies indexed photos, home videos and personal files on your separate backup drive. Originals remain in place. You can still select up to 100 eligible files for a manual batch. This is separate from the Storage & Backup catalog and managed-media backup, which protects collections and owner edits. Linked movies, music and books remain on their source drive. A library recovery point preserves their records but does not copy their bytes; use an external drive backup if you need those originals recoverable.

Core and metapacks have separate optional update paths. An installed pack can help identify new files offline, but no update or hosted metadata service is needed to use the library.
