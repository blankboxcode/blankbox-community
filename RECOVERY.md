# Protect and recover your library

We treat your household catalog as the authority for titles, edits, provenance, identities, physical copies, artwork, intentions, activity and saved collections. Reference databases and connected servers add evidence. Missing storage or an unavailable provider does not authorize deleting the catalog.

## Portable backup

Use Storage & Backup with a separate writable destination. A verified backup copies managed media and creates a SQLite snapshot with a manifest. Source folders remain read-only. Linked files stay on their original drives, and their catalog records survive a disconnected drive. A library recovery point does not recreate those original bytes. Copying eligible personal files to the backup drive requires a separate, confirmed Import action. RAID and a folder on the same disk are not independent protection.

A catalog export contains metadata and saved owner artwork, not media bytes. Credentials and sessions are excluded. Copy it to separate storage. CSV is a partial interchange format; use the complete SQLite catalog export for recovery.

### Scheduling and disk use

`backupEveryHours: null` means automatic scheduling is off; it does not prevent a manual backup or restore. Set it to `24` only if you want a daily interval while Core is running. The interval restarts when Core restarts; it is not a fixed wall-clock appointment. The configured `backup` destination must be available and writable. Run and verify the first backup manually instead of waiting a day. Blank Box creates a `blank-box-backup` folder inside that destination when it saves a backup; for example, a destination of `/mnt/backups/blankbox` uses `/mnt/backups/blankbox/blank-box-backup`.

Unchanged managed files are reused in the backup after checksum verification; each run creates a new catalog snapshot. If original source-drive bytes need recovery, protect them with an external backup process. Portable snapshots omit downloadable reference databases; confirmed household facts remain in the catalog. Offline upgrade snapshots include the installed pack set for paired recovery and can therefore be much larger.

**Settings → System & About → Complete recovery points → Create recovery point** manually creates an explicit portable catalog and managed-media snapshot paired with the exact installed offline pack assets on the backup drive, even when `backupEveryHours` is `null`. Wait for that job to finish successfully before trying a full restore. The regular scheduled backup stays smaller and does not duplicate packs each time. The installer still makes its own local paired maintenance snapshot before an update. Keep each complete point's snapshot folder, its `catalog.sqlite3.assets` directory, and the shared `blank-box-backup/media` files together. The complete point excludes linked source-drive originals and account/provider credentials.

For source-drive photos, home videos and personal files, use **Import → Files on a drive or folder** after a complete index. **Back up all indexed personal files** shows the exact count and total size for confirmation, then verifies copies on the configured backup drive. You can still select 1-100 eligible files per manual batch. Movie, music, book and other linked originals are not copied by this workflow; use an external drive backup if you need their bytes recoverable. Collections, ownership and saved artwork are catalog records and are covered by the catalog snapshot.

Backup retention is manual. Check free space and the last successful backup regularly. Keep at least one verified restore point on separate storage and retain the catalog/asset pair needed for rollback. Do not remove active pack files, restore scratch files, or snapshot assets just because they look old. Test restoration before deliberately pruning old backups.

## Restore to a new location

### From the running Blank Box screen

On the machine that already runs Blank Box, open **Settings → System & About → Complete recovery points**, choose **Find recovery points**, then **Prepare full restore** for a current point. The screen finds points under the configured backup destination; you do not need to type the `blank-box-backup` path. Blank Box checks the catalog, shared managed media and paired pack hashes and writes a new copy under `DATA/restore-review/POINT-ID`. The running library stays in place. You do not need to extract or install another package for this preparation step. To finish the drill, start or inspect the review copy independently using the same Core version and a different port.

### On a separate Linux test computer

For a restore trial, **do not run `setup-linux.sh` first**. The extracted Community ZIP contains the restore tool and the runnable Core. The restore tool creates a new library data folder; starting Core is a second command. A permanent service install can be planned after the restored library has been checked.

Use the `blankbox-community-VERSION.zip` matching the recovery catalog's Core version; the source ZIP is not needed. Extract the Community ZIP and the backup ZIP into separate folders under one parent folder. Keep the **whole** `blank-box-backup` folder from the backup drive: the snapshot uses the shared `media/` folder and its own `catalog.sqlite3.assets/` folder. It is not inside the Community ZIP. For example, the folders might look like this (your backup ZIP's extracted folder name can differ):

```text
blankbox/
  blankbox-community-1.0.0/
    restore.py
    server.py
  backup-extracted/
    blank-box-backup/
      media/
      snapshots/
        POINT-ID/
          full-recovery.json
          manifest.json
          catalog.sqlite3
          catalog.sqlite3.assets/
```

If your backup ZIP extracted `blank-box-backup` directly inside `blankbox`, omit `backup-extracted/` from the example path. Keep the inner folder named exactly `blank-box-backup`; the restore tool uses that name to locate its shared media.

In your file manager, open the outer `blankbox` folder and choose **Open in Terminal**. Check where the two important files landed:

```sh
find . -name restore.py -o -name full-recovery.json
```

Choose the `full-recovery.json` for the complete point you want. Its **containing folder** is the snapshot path for the next command; do not pass the JSON file itself. If there is no `full-recovery.json`, check that the backup ZIP includes a complete point and was made after that point finished. If `blank-box-backup/media/` or the point's `catalog.sqlite3.assets/` is missing, get the complete backup tree before continuing.

From that same outer folder, restore into a **new** `restored-data` folder. This example assumes the folder names shown above. Replace the quoted snapshot path with the containing folder shown by your `find` output:

```sh
python3 "./blankbox-community-1.0.0/restore.py" --full "./backup-extracted/blank-box-backup/snapshots/POINT-ID" "./restored-data"
python3 "./blankbox-community-1.0.0/server.py" --data "./restored-data" --port 25266
```

Wait for the first command to report that it restored and checked the catalog, managed files and packs. If it reports an error, stop and keep both extracted ZIP folders; do not run the second command against a partial restore. Leave the second command running and open `http://127.0.0.1:25266` in a browser **on that test computer**. Blank Box creates a new recovery key at `restored-data/access-key.txt` when Core first starts; read it privately to claim a test owner profile. Stop only this test process with Ctrl+C when done; the `restored-data` folder remains for review. Do not run the normal setup wizard against this restored data folder; the wizard creates a separate fresh installation. Existing populated restore destinations and linked destination paths are rejected. Run the commands as an account that can read the snapshot and shared managed-media backup and write the new destination; on a Linux service installation this is normally the `blankbox` account. Do not make private backups world-readable to work around a permission error.

**After the trial:** This two-command run is a foreground test, not a systemd installation. Its `restored-data` folder is the library; the extracted Community folder is the software and still contains `setup-linux.sh`, update tools and the uninstall wizard. Stop the foreground process with Ctrl+C. There is no installed service for the wizard to uninstall, and stopping Core does not erase `restored-data`. Keep the extracted folders until you have finished reviewing the restore.

To update a metapack while the test Core runs, use **Settings → Metadata** to import a newer signed `.bbpack`; the four bundled packs are already the current versions in this release, and packs have no cover art. To trial newer Core software, stop this foreground process, extract the newer Community ZIP separately, restore a recovery point into another empty test data folder, and start that copy with the newer package's `server.py`. Keep the earlier test copy and package for comparison. A permanent Linux service uses the platform install/update guide and a deliberate handoff of the reviewed data; running `setup-linux.sh` now would create a separate default data folder instead of adopting this review copy.

Portable recovery keeps saved Plex/Jellyfin addresses and metadata references, but excludes their private API keys and tokens. On another machine the saved addresses may also point to the old network location. Reconnect each provider in **Settings → Connections** with a reachable address and a new or existing key before expecting provider artwork or playback to work. Owner-uploaded covers are stored in the catalog; provider artwork is fetched through the connected service and is not stored in the metapacks. After reconnecting, open **Settings → System & About → Restore saved provider covers** and choose **Restore missing covers**. Review the count and confirm. This fills only missing covers with saved provider artwork references; it keeps uploaded art, other title details and metadata source choices. If a provider is not reconnected or had no saved cover reference, review that title individually.

Verify item IDs, copy counts, artwork, collections, managed-media hashes and installed packs. The review copy resets operational backup badges until its own destination is configured and checked; titles, ownership and collection records remain. Linked records survive with the original drive absent. For immediate access to linked files on another Linux machine, configure the source at the **same absolute folder path** used when the files were linked; a different path gets a different source ID. A replaced drive may also require reindexing and review even at the same path. Across operating systems, linked files may need explicit review and relinking. The recovery point does not recreate absent original files or restore provider credentials.

For a smaller portable snapshot without paired packs, use `python3 restore.py "/path/to/blank-box-backup/snapshots/POINT-ID" "$HOME/BlankBox-restore-test"` with a different empty destination. For a metadata-only catalog export, use `python3 restore.py --catalog-only "/path/to/export.sqlite3" "$HOME/BlankBox-catalog-test"`; no media bytes are restored. Choose one restore mode for each empty destination.

Indexed personal-file backups include files plus their separate manifests under `blank-box-backup/indexed-personal/` and `indexed-personal-manifests/`; review and recover these to a new directory separately. Do not overwrite original media.

## Offline upgrade snapshots

Stop Core first. `maintenance.py backup` creates a complete local SQLite snapshot including private authentication state and a paired `.assets` directory for pack recovery. Treat both as private, restrict access, and copy them to a separate protected disk. `maintenance.py restore` is deliberate replacement of this installation's catalog, retains a pre-restore copy and restores its paired pack set. It is not the empty-directory portable restore command. See UPDATES.md.

Interrupted copy and disc-import scratch files are retained after a crash. Review them before manually reclaiming space; filenames alone do not prove that a file is disposable.

## Uninstall

Uninstall disables/removes startup registration while retaining application files, configuration, catalog, media, and unrelated files. Reinstallation can reuse the data. Permanent deletion is a separate manual operation after a verified restore; no normal uninstall recursively erases your installation directory.

## Diagnostics

`python3 doctor.py --config /path/to/config.json` checks runtime, catalog schema/integrity, source access and browser files without migration. `/health/live` and `/health/ready` expose no catalog or credentials. Logs can contain private paths and titles: review/redact them before sharing. Never share recovery keys, tokens, the private catalog, or session files in a support request.
