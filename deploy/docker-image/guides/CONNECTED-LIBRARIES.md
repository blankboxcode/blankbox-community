# Connected libraries and matching

A title can have copies on Plex, Jellyfin and your local drives. Matching connected entries keeps those sources together while leaving their versions and editions available.

Connect your server under **Settings → Connections**, then sync its catalog. Use an address reachable from the computer running Blank Box. See [Connection keys](CONNECTION-KEYS.md) for setup. Syncing reads your server's catalog and adds playback links; it leaves the server's files unchanged.

## Clear matches on update and sync

Version 1.0.1 checks existing connected titles after the first startup and again after a sync. The first check uses details already saved in your library. It runs in the background; wait for it to finish before starting another import or sync.

- Movies and TV series can match through the same IMDb or TMDB identifier, even if their names differ. Known release years must be the same or one year apart.
- Without a shared identifier, the title, media type and known year must match, with no conflicting identifiers.
- Albums must have the same title, edition and artist. Known years may be the same or one year apart. Different named album editions stay separate.
- Movie cut names belong to editions. Copies of the same film can share one title and keep their separate cuts. A supercut combining several films stays separate from those films.

An automatic merge is blocked by conflicting identifiers, incompatible corrections or playback progress, more than one possible match, an unfinished match review or a saved **Keep separate** choice. A group that exceeds the library's record limits also stays separate. This check applies to connected titles, not titles entered only by hand or from local files. Similar wording alone is not enough.

The merged title keeps its selected details source and corrections. Sources, files, owned copies, artwork, favorites and activity stay attached. Links to the old title open the merged title. Older Plex entries may gain missing identifiers on their next sync; the first startup check only uses what is already saved.

## Review uncertain matches

Open **Import Media** to review remaining proposals. Check the title, year and sources, then choose incoming details, **Keep current details**, or a separate title. Keeping current details adds the source while retaining the current metadata provider and your corrections.

Confirmation runs in the background. Unfinished or failed reviews remain available to retry.

For a physical copy or preorder delivery, use **Search My Library** or an installed offline database and confirm its edition. A movie title match alone cannot identify a particular disc release.

## Playback and library counts

Watch or Listen shows one row per connected app and Local. **Change source** chooses a version or quality and updates the main playback button. Seasons, episodes, discs and songs follow your choice. See [Playback](PLAYBACK.md).

Cards count each connected provider once, plus Local when files are attached. Several qualities on one provider still count as one source. Matching standard cuts across providers count as one edition; physical releases and different cuts count separately. A saved title without separate editions shows one standard edition. Films, series and albums count as titles; their episodes, tracks and sources do not add to that total.

## Recovery

Back up your library before updating. Merging duplicates can reduce your title count while keeping their sources and copies. To restore the earlier arrangement, use its matching pre-update catalog and assets with compatible software. Keep later work before restoring an earlier backup. [Updates](../UPDATES.md#rollback) · [Recovery](../RECOVERY.md)
