# Connected libraries and matching

Connect an existing Plex or Jellyfin server under **Settings → Connections**, then sync its catalog. Use a server address reachable by Blank Box and credentials from your own server. [Connection keys](CONNECTION-KEYS.md) explains setup. Connected entries supply metadata and playback links; they do not copy media or add physical ownership.

## Clear matches on update and sync

Version 1.0.1 checks saved connected entries once after startup, then repeats clear reconciliation after provider syncs. Startup uses saved evidence without contacting a provider. You can browse while its tracked job runs; wait for it to finish before another import or sync.

- Movies and TV series can join on matching supplied IMDb/TMDB work identifiers, even when their displayed titles differ. Known years must agree or differ by no more than one.
- Without a shared identifier, matching normalized title, type and known year can qualify when supplied identities do not conflict.
- Albums require matching normalized title, edition wording and known artist, with known years equal or one apart. Different named album editions remain separate.
- Recognized movie cut labels and provider edition fields belong to editions. Multiple copies of the same work join while retaining distinct cuts. A separately named combined-film supercut stays separate from its component films.

Conflicting identifiers, incompatible manual corrections or playback progress, ambiguous identity bridges, pending reviews and a saved **Keep separate** decision prevent an automatic join. Very large or capacity-limited groups remain separate. Purely manual or local-file-only titles are outside this saved-provider cleanup. Similar words alone do not qualify.

A joined title keeps the retained details source and corrections, with source, file, owned-copy, artwork, favorite and activity records carried across. Retired item IDs resolve to the retained title. Missing identifiers in older saved Plex entries can become available on an ordinary refresh; the startup pass cannot invent missing facts.

## Review uncertain matches

Import Media retains uncertain proposals for your review. Inspect the title, year and sources, then choose incoming details, **Keep current details**, or a separate title. Keeping current details preserves its current provider and manual corrections while adding the new source. Confirmation continues as a background job; unresolved or failed choices remain available for retry.

A title match does not prove a physical release. Match new shelf copies and preorder deliveries deliberately using **Search My Library** or installed offline references. Reference facts do not create ownership.

## Playback and library counts

Each connected app and Local has one row in Watch or Listen. **Change source** chooses its attached version or quality and updates the main playback action. Seasons, episodes, discs and songs follow that selection. [Playback](PLAYBACK.md) explains file and connected-app limits.

Cards count connected providers plus Local when files exist. Several files or qualities on one provider do not add providers. Edition counts group matching connected cuts, distinguish physical and file releases, and show at least one standard edition for a saved title. Title totals count films, series and albums, rather than every episode, song or source.

## Recovery

Create a complete recovery point before updating or deliberately reorganizing records. Automatic reconciliation can reduce duplicate title counts. Returning to the exact earlier arrangement requires the matching pre-update catalog/assets snapshot as well as compatible code; it is not a general undo button. Export and preserve later work before restoring an earlier state. [Updates](../UPDATES.md#rollback) · [Recovery](../RECOVERY.md)
