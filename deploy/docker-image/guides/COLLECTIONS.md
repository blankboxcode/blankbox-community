# Organize your collection and scan physical media

Organize the media you own, record its copies and locations, and use installed reference data to help find titles. See [Platform status](../PLATFORMS.md) for device and platform limitations.

## Collections

Open **Collections** in the sidebar or **My Library → Browse collections**.

- **Custom collection:** choose existing titles to keep together.
- **Movie series / franchise:** choose titles and use the arrows to set their order. This groups your selected titles; it does not certify a complete franchise filmography.
- **Genre:** select genres to build a collection that updates as your library changes.
- **Smart collection:** combine media type, genre, owned physical format, local activity status, and year rules.
- **Seasonal:** use the same rules with an optional recurring start/end date. A season can cross New Year. Off-season collections stay accessible.

Different rules must all match. Multiple choices within one rule match any selected choice. An empty rule accepts any value. A DVD copy does not satisfy a 4K rule, and digital playback access does not imply an owned physical format.

Halloween and holiday starting points open an editable draft. Review the genres before saving. Collections group existing household titles without moving files, creating editions, or changing copy counts. Removing a collection removes its grouping only.

Use **Plan missing titles** for the separate Complete My Collection / Intend to Buy workflow. Missing editions require reference evidence; store inventory does not define collection completeness.

## Suggested collections and missing titles

**Collections → Suggested collections** reads your library together with installed offline packs. Shared title patterns suggest series; recorded studios suggest studio groups. Collection labels supplied by a source or entered in an item's **Collection labels** can group local titles too. Genres organize shelves, but do not establish franchise membership.

Each suggestion shows titles already in your library out of the known reference titles. Connected or local digital access counts as in-library; that does not mean an owned disc. Pack coverage is incomplete, alternate regional titles can need review, and a studio group can span several series or film types. Recommendations only appear when this household has related titles. Empty libraries have no required franchises or automatic buying intentions.

Use **Approve all (count)** to create editable collections and linked plans from every currently offered suggestion, including those under Show more. It uses the suggested names and all listed members, then shows completion status. It creates no buying intentions or owned copies. You can edit or remove each resulting collection afterward. Later suggestions require another explicit approval. Groups remain recommendations with partial reference coverage; source groups over 200 titles are kept out of automatic completion plans.

Choose **Review & save collection**, rename it and deselect titles outside your preferred scope. Saving creates an editable collection and a linked title plan. **Intend to Buy** can add a missing reference as a deliberate intention; the desired format is a preference, not evidence that that release exists. **Saved collection sets → Edit titles & order** can change the denominator, add/remove/reorder titles and choose desired formats. Ignored titles are excluded from the goal. Existing connected titles are not shown as missing titles in an accepted Any-format title plan.

When an item's genre is empty, a consistent exact-year/title reference or saved identifier can inform its collection genres without changing the saved item or confirming a metadata match. Your own genres and explicit corrections take priority. Saving a genre/rule collection retains its reviewed fallback genre clues, so the collection can remain useful after pack removal. No original files, copies or upstream provider records change.

The installation package includes optional Movies, Books, Music and TV Shows metapacks. They install on a fresh household once, stay separate from owned media, and remain removable. Restarts and upgrades do not reinstall a removed pack or replace an existing chosen version. Existing households keep their current pack selection; bundled packs remain available in Settings for deliberate installation or reinstallation. Core, manual collections and supplied source groups work with no packs. See ../METAPACKS.md for exact coverage.

Our current packs are Movies v4 (62,306 genre-tagged titles of 96,861), Books v7, Music v5 and TV Shows v4 (89,608 of 152,965). We do not include a CD proof, Game or Comic pack. Missing tags remain unknown rather than guessed from titles. See [Metapacks](../METAPACKS.md) for coverage and edition counts.

## Genres and your own categories

Open an item, choose **Edit title details**, and use **Custom genres** to add household labels such as Holiday, Halloween, or Comfort films. These labels remain separate from provider genres and survive a provider metadata refresh.

Collections and the library genre filter use both ordinary genres and your custom genres. Custom genres are owner-entered local metadata; they are not contributions to a downloadable reference pack.

## Watch, read, listen, and play status

Open the item's **Activity** section for local status controls and **History**. Set Not started, In progress, or Completed; the wording follows the media type. History shows the time recorded and lets you undo an event without deleting the history.

TV season status appears inside each expanded season, with Whole Series & Activity History kept separately. History can also record a specific episode such as `S1E1`. Recording a season or episode does not mark the entire series watched. An optional edition identifies what you used; activity still belongs to the household library item.

This first version is manual and stored on your Blank Box. Playback resume positions and Plex/Jellyfin refreshes do not automatically change it. External watch-service synchronization is not implemented. The full catalog export includes collections, custom genres, and activity history; media-byte backup is separate.

## Add physical items and choose your defaults

Open **Import → Add physical item** or **Physical Media → Add physical item**. Enter the title, format, media type and location on the same screen where you search and confirm the copy. Year, edition, packaging, release label and barcode are available there too; expand **More copy details** for condition, credits, region and catalog number.

**Search for a title** starts with **Blank Box Database**, which searches installed Offline Metapacks on your computer. Choose **My Library** for saved titles or **Connected libraries** for synced Plex/Jellyfin titles. Search uses the title you entered; you do not need to enter it again. Select a reference and confirm the physical item, or choose an existing library title and decide whether this is another copy of its edition or a different edition. A title match alone does not prove the exact physical edition.

Use **Add without a match** to save your entered details. We check your library before creating a new title. If there are possible duplicates, add the copy to a matching title or explicitly confirm a separate title. No item is saved simply by searching, choosing a default or scanning a barcode. Closing a changed draft asks before clearing it.

In **Settings → Collection → Physical Media preferences**, set a starting format for each media type and **Default title search**, then save. For example, set Movies to **4K UHD Blu-ray** and Music to **Vinyl**. These are starting choices; each copy can use a different format. **Save … as my … default** and **Use this search as my default** save the current choice directly from the add screen. Saving a format as your default also makes that format visible if it was hidden.

Hiding a preferred format makes new drafts fall back to a visible compatible format; it does not change existing copies or forget the preference. An exact scanned edition keeps its identified format, and audio-CD intake keeps CD. Your preferences survive updates and catalog export/recovery. Searching reference data requires an installed pack; manual entry and My Library remain available without packs.

## Scan barcodes

1. Open **Import → Scan physical items**. Use HTTPS or localhost and allow camera access.
2. Choose **Scan barcode**, center the whole barcode, and hold steady. Avoid glare and move back until all bars are sharp. You can choose another camera when the browser exposes several.
3. When a code is detected, the camera stops. Review the captured frame, highlighted region, and printed number. Correct a misread or choose **Scan again**.
4. Check **This matches the code printed on my item**, then **Confirm barcode**.
5. Choose an exact household/reference candidate, or enter your own title. Select **Review physical item** to open the same add screen, check format, edition, location, and other details, then confirm the copy.

Nothing becomes owned merely because a barcode was scanned or a reference was found. Cancelling copy intake keeps the scan queued. A completed intake removes that scan from the queue; another copy can then be scanned and reviewed. The queue is temporary browser-session state, not a saved import batch.

**Scan several** resumes the camera after each code confirmation. The queue holds up to 50 observations. You can also choose barcode photos or covers (up to 30 selected images, each under 12 MB), or enter a printed code manually. Barcode-free covers require your title; visual cover recognition is not implemented.

Barcode decoding uses bundled ZXing on your device. Exact lookup searches saved references and installed Blank Box packs on your Core, without retailer or online metadata calls. UPC/EAN leading-zero equivalents and ISBN-10/ISBN-13 equivalents are supported. Comic barcode supplements stay distinct from the base code. A valid check digit verifies the number's structure, not ownership or a particular edition.

Coverage depends on the installed reference data. Work-only packs cannot identify a release by UPC/ISBN. An unknown code remains usable with manual details; a work match does not prove the exact physical edition. Once you confirm a reference, its saved identity/evidence survives removing the pack.

Camera captures and cover observations stay in this browser session. Camera startup, focus, and decoding depend on the device/browser and printed label; the photo and manual-code paths remain available when live scanning struggles.

## Sources and finding more

Open a title to see its artwork, playback choices and **Your editions** in a popup over your library. Select an edition to show its artwork and copies; use **Edit this copy** for its location, condition and edition fields. **Edit title details** changes shared information, **Edit artwork** opens the selected edition’s gallery, and **Choose details source** selects saved Blank Box or connected-service information. Music covers stay square and show the full image. **Close (×)** or **Escape** returns to your library with its filters and scroll position. Editors open above the item; closing an editor returns to the same edition and artwork. Each popup scrolls within the screen.

**Find more → Choose store searches** offers 25 built-in choices across media types plus custom links. Nine sources are initially enabled where applicable; saved choices stay exact after updates. Reference editions appear here separately from your owned copies. Some links open a store page for you to search there; they do not report live prices or availability. **Search your services** stays in item details and opens the configured streaming searches.
