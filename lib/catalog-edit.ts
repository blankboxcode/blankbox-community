import type { CatalogDetails, DigitalPlatform, Kind, MediaItem } from './media';

export type PhysicalSourceEdit = {packaging:string;releaseLabel:string;sourceId:string;format:string;edition:string;season:string;barcode:string;condition:string;creator:string;publisher:string;platform:string;volume:string;issue:string;region:string;catalogNumber:string;location:string};
export type DigitalSourceEdit = {sourceId:string;label:string;edition:string;creator:string;publisher:string;platform:string;volume:string;issue:string;region:string;catalogNumber:string;barcode:string};
export type MediaEdit = {digitalPlatforms:DigitalPlatform[];catalogDetails:CatalogDetails;releaseDate:string;duration:string;customGenres:string[];title:string;kind:Kind;year:string;genre:string;description:string;artist:string;trackTitles:{sourceId:string;title:string}[];digitalSources:DigitalSourceEdit[];physicalSources:PhysicalSourceEdit[];tvSeasons:{versionId:string;season:string;label:string}[]};
export type CatalogEditFocus = {section:'all'|'title'|'artwork'|'metadata'|'physical'|'digital'|'files';sourceId?:string;releaseId?:string};

export function catalogEditPayload(item:MediaItem, edit:MediaEdit, focus:CatalogEditFocus):Record<string,unknown> {
  const payload:Record<string,unknown> = {id:item.id};
  if(focus.section==='all'||focus.section==='title') Object.assign(payload, {
    title:edit.title.trim(),kind:edit.kind,catalogDetails:edit.catalogDetails,
    releaseDate:edit.releaseDate||null,duration:edit.duration?Number(edit.duration)*60:null,
    year:edit.year?Number(edit.year):null,genre:edit.genre.trim(),customGenres:edit.customGenres,
    description:edit.description.trim(),...(edit.kind==='music'?{artist:edit.artist.trim()}:{}),
  });
  // Core validates complete ID sets. Keep sibling rows unchanged rather than
  // sending an incomplete list or adding unrelated fields to a focused save.
  if(focus.section==='all'||focus.section==='physical') payload.physicalSources=edit.physicalSources;
  if(focus.section==='all'||focus.section==='files') {
    payload.digitalSources=edit.digitalSources;
    if(edit.kind==='tv') payload.tvSeasons=edit.tvSeasons.map(({versionId,season})=>({versionId,season}));
    if(edit.kind==='music'&&item.discImport) payload.trackTitles=edit.trackTitles;
  }
  if(focus.section==='all'||focus.section==='digital') payload.digitalPlatforms=edit.digitalPlatforms;
  return payload;
}
