# Organize your collection and scan physical media

We include these controls in this beta. See [Platform status](../PLATFORMS.md) for device and platform limitations.

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

Open an item, choose **Edit details**, and use **Custom genres** to add household labels such as Holiday, Halloween, or Comfort films. These labels remain separate from provider genres and survive a provider metadata refresh.

Collections and the library genre filter use both ordinary genres and your custom genres. Custom genres are owner-entered local metadata; they are not contributions to a downloadable reference pack.

## Watch, read, listen, and play status

The item's **Overview** has local status controls and **History**. Set Not started, In progress, or Completed; the wording follows the media type. History shows the time recorded and lets you undo an event without deleting the history.

TV season status appears inside each expanded season, with Whole Series & Activity History kept separately. History can also record a specific episode such as `S1E1`. Recording a season or episode does not mark the entire series watched. An optional edition identifies what you used; activity still belongs to the household library item.

This first version is manual and stored on your Blank Box. Playback resume positions and Plex/Jellyfin refreshes do not automatically change it. External watch-service synchronization is not implemented. The full catalog export includes collections, custom genres, and activity history; media-byte backup is separate.

## Scan barcodes

1. Open **Import → Scan physical items**. Use HTTPS or localhost and allow camera access.
2. Choose **Scan barcode**, center the whole barcode, and hold steady. Avoid glare and move back until all bars are sharp. You can choose another camera when the browser exposes several.
3. When a code is detected, the camera stops. Review the captured frame, highlighted region, and printed number. Correct a misread or choose **Scan again**.
4. Check **This matches the code printed on my item**, then **Confirm barcode**.
5. Choose an exact household/reference candidate, or enter your own title. Select **Review physical copy**, check format, edition, location, and other details, then confirm the copy.

Nothing becomes owned merely because a barcode was scanned or a reference was found. Cancelling copy intake keeps the scan queued. A completed intake removes that scan from the queue; another copy can then be scanned and reviewed. The queue is temporary browser-session state, not a saved import batch.

**Scan several** resumes the camera after each code confirmation. The queue holds up to 50 observations. You can also choose barcode photos or covers (up to 30 selected images, each under 12 MB), or enter a printed code manually. Barcode-free covers require your title; visual cover recognition is not implemented.

Barcode decoding uses bundled ZXing on your device. Exact lookup searches saved references and installed Blank Box packs on your Core, without retailer or online metadata calls. UPC/EAN leading-zero equivalents and ISBN-10/ISBN-13 equivalents are supported. Comic barcode supplements stay distinct from the base code. A valid check digit verifies the number's structure, not ownership or a particular edition.

Coverage depends on the installed reference data. Work-only packs cannot identify a release by UPC/ISBN. An unknown code remains usable with manual details; a work match does not prove the exact physical edition. Once you confirm a reference, its saved identity/evidence survives removing the pack.

Camera captures and cover observations stay in this browser session. Camera startup, focus, and decoding depend on the device/browser and printed label; the photo and manual-code paths remain available when live scanning struggles.

## Sources and finding more

Known formats/editions are in the item’s **Sources** tab. **Find more → Choose store searches** offers 25 built-in choices across media types plus household custom links. Nine sources are initially enabled where applicable; saved choices stay exact after updates. Some sources open the store/search page for you to search there. Links do not report live prices or availability. A physical/list-only item without playback has **Search for More** as its primary action.
