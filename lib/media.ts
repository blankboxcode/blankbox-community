import type { PhysicalFormat, PhysicalFormatDefaults, PhysicalSearchSource } from './physical-media';
import type { ItemActivity, LibraryCollection } from './collection-organization';

// Curated, recognizable physical-game platforms, not a ranked usage list or a
// promise that Blank Box can play games from these systems.
export const commonGamePlatforms = [
  'PlayStation 5', 'PlayStation 4', 'PlayStation 3', 'PlayStation 2', 'PlayStation',
  'PlayStation Portable (PSP)', 'PlayStation Vita',
  'Xbox Series X', 'Xbox One', 'Xbox 360', 'Xbox',
  'Nintendo Switch 2', 'Nintendo Switch', 'Nintendo 3DS', 'Nintendo DS',
  'Nintendo Wii U', 'Nintendo Wii', 'Nintendo GameCube', 'Nintendo 64',
  'Super Nintendo (SNES)', 'Nintendo Entertainment System (NES)',
  'Game Boy', 'Game Boy Color', 'Game Boy Advance',
  'Sega Genesis / Mega Drive', 'Sega Dreamcast', 'Sega Saturn', 'Sega Game Gear',
  'PC (Windows)', 'Atari 2600',
] as const;

export type CatalogDetails = { collections?:string[]; directors?:string[];writers?:string[];cast?:string[];studios?:string[];languages?:string[];countries?:string[];creators?:string[];authors?:string[];publishers?:string[];contentRating?:string;releaseType?:string;firstPublished?:string;firstReleased?:string;seasonCount?:number;episodeCount?:number;pageCount?:number;trackCount?:number;discCount?:number;ratings?:{source:string;value:number;scale:number;count?:number}[] };

export type Kind = 'movie' | 'tv' | 'music' | 'photo' | 'home-video' | 'book' | 'comic' | 'game' | 'file';
export type MediaVersion = { id: string; label: string; year?: number; duration?: number; notes?: string; season?: string };
export type TvCatalog = { provider: 'jellyfin' | 'plex'; updatedAt?: string; episodeCount: number; seasons: { number: number; title: string; episodes: { number: number; title: string; description: string; airDate: string | null; providerItemId: string }[] }[] };
export type DigitalPlatform = {id:string;platform:string;status:'purchased'|'redeemed'|'code-included';url:string;notes:string;physicalSourceId:string};
export type ServiceLink = {id:string;name:string;url:string;enabled?:boolean;mark?:string;color?:string;searchUrl?:string};
export type GalleryArtwork = {id:string;releaseId:string|null;label:string;role:string;url:string;primary:boolean};
export type MediaSource = { packaging?:string; releaseLabel?:string; id?: string; itemId?: string; versionId?: string; sourceId?: string; type: 'demo' | 'local' | 'physical' | 'catalog' | 'jellyfin' | 'plex' | 'emby' | 'digital'; label: string; path?: string; url?: string; location?: string; providerItemId?: string; metadataIdentifiers?:{namespace:string;value:string}[]; metadataSnapshot?: {catalogDetails?:CatalogDetails;title?:string;kind?:Kind;year?:number;description?:string;poster?:string;genre?:string;artist?:string;releaseDate?:string;duration?:number}; tvCatalog?: TvCatalog; available?:boolean; addedAt?: string; storedPath?: string; sha256?: string; bytes?: number; mime?: string; physicalReleaseId?: string; ownedCopyId?: string; packageContentId?: string; edition?: string; quality?: string; season?: string; episodeNumber?: number; episodeEnd?: number; audioBook?: boolean; playbackProgress?: number; barcode?: string; condition?: string; platform?: string; creator?: string; publisher?: string; volume?: string; issue?: string; region?: string; catalogNumber?: string; certificate?: string; signed?: string; grade?: string; listedPrice?: string; trackNumber?: number; trackTitle?: string; discId?: string; tocFingerprint?: string; artist?: string; extraction?: string; encodingVerified?: boolean };
export type MediaItem = { digitalPlatforms?:DigitalPlatform[]; artworkGallery?:GalleryArtwork[]; browseSummary?: boolean; collectionGenres?: string[]; collectionGenreBasis?: string; catalogDetails?:CatalogDetails; customGenres?: string[]; activity?: ItemActivity; id: string; title: string; kind: Kind; year?: number; releaseDate?: string; description?: string; poster?: string; backdrop?: string; duration?: number; genre?: string; versions?: MediaVersion[]; sources: MediaSource[]; bytes?: number; sha256?: string; mime?: string; progress?: number; favorite?: boolean; addedAt: string; sample?: boolean; backup?: 'none' | 'verified'; backupVerifiedAt?: string; credit?: string; metadataMatch?: { type: 'library'; itemId: string; matchedAt: string }; metadataOverrides?: string[]; metadataProvenance?: Record<string,{source:string;updatedAt:string;sourceId?:string}>; metadataPreference?: string; blankboxMetadataSnapshot?: Partial<Pick<MediaItem,'title'|'kind'|'year'|'releaseDate'|'description'|'poster'|'backdrop'|'genre'|'duration'|'artist'|'catalogDetails'>>; artist?: string; trackCount?: number; discImport?: { tocFingerprint: string; format: 'FLAC' | 'WAV'; extraction: string; encodingVerified: boolean; discAccuracyVerified: boolean; importedAt: string } };
export type SetupMode = '' | 'managed' | 'advanced';
export type SetupStep = 'welcome' | 'media' | 'connect' | 'protection' | 'access' | 'finish';
export type MediaProvider = 'blankbox' | 'jellyfin' | 'plex' | 'emby';
export type RemoteProvider = 'local' | 'blankbox-connect' | 'tailscale' | 'wireguard' | 'custom';
export type MediaInput = 'dvd' | 'cd' | 'usb' | 'hard-drive' | 'digital-files' | 'addon' | 'jellyfin' | 'plex' | 'emby';
export type StreamingService = 'netflix' | 'prime-video' | 'disney-plus' | 'youtube' | 'spotify' | 'apple-tv' | 'movies-anywhere';
export const MEDIA_RIGHTS_TERMS_VERSION = '1';
export type MediaRightsAttestation = { accepted: true; acceptedAt?: string; termsVersion: string };
export type Settings = { streamingServiceOverrides:ServiceLink[]; customStreamingServices:ServiceLink[]; mediaRightsAttestation: MediaRightsAttestation | null; helpTipsEnabled: boolean; name: string; jellyfinUrl: string; plexUrl: string; immichUrl: string; remoteUrl: string; opticalDrive: string; setupDone: boolean; setupVersion: number; setupMode: SetupMode; setupStep: SetupStep; mediaProvider: MediaProvider; mediaInputs: MediaInput[]; physicalFormats: PhysicalFormat[]; physicalDefaultFormats: PhysicalFormatDefaults; physicalTitleSearchSource: PhysicalSearchSource; physicalLocations: string[]; gamePlatforms: string[]; gamePlatformCatalogVersion: number; sidebarShortcuts: ('movie'|'tv'|'music'|'photo'|'book'|'comic'|'game')[]; sidebarShortcutVersion: number; sidebarOrder: import('./sidebar-preferences').SidebarDestination[]; streamingServices: StreamingService[]; remoteProvider: RemoteProvider; autoImport: boolean; autoProviderRefresh: boolean; autoFolderCopy: boolean; autoSourceIndex: boolean; autoImportMinutes: number; heroWatch: boolean; heroMusic: boolean; heroBooks: boolean; heroPhotos: boolean; heroComics: boolean; heroGames: boolean; homeRows: import('./home-preferences').HomeRow[]; homeHeroOrder: import('./home-preferences').HomeHeroMode[]; homeHeroSort: import('./home-preferences').HomeHeroSort };
export type Source = { id: string; name: string; path?: string; available?: boolean };
export type InventoryBulkPreview = { id:string; batchId:string; expiresAt:number; retryUnmatched?:boolean; counts:{ inventoryFiles:number; alreadyLinked:number; matchExisting:number; newTitles:number; newTitleFiles:number; packReferences:number; needsReview:number; linkFiles:number; linkBytes:number }; reviewSamples:{path:string;title:string;kind:Kind;reason:string}[] };
export type Job = { id: string; type: string; status: string; done: number; total: number; copied?: number; duplicates?: number; errors?: string[]; message?: string; createdAt?: string; finishedAt?: string; sourceId?:string; preview?:InventoryBulkPreview; matchedExisting?:number; newTitles?:number; linked?:number; skipped?:number };
export type ReconciliationReview={id:string;source:string;createdAt?:string;incoming:MediaItem;candidates:MediaItem[]};
export type PhysicalInventorySummary={titles:number;packages:number;copies:number;includedTitles:number;formats:{label:string;count:number}[];discs?:number};
export type OwnerProfile = { id: string; username: string; displayName: string; role: 'owner' };
export type HiddenRecord = { id: string; title: string; kind: string; source: string; hiddenAt?: string | null };
export type LibraryFacets = { genres:string[];physicalFacets:{id:string;label:string;kind:Kind;count:number}[];locations:{location:string;copies:number}[] };
export type LibraryState = { catalogRevision?:string;pagedLibrary?:boolean;browseIndexStatus?:'building'|'ready'|'unavailable';summary?:CollectionSummary;kindCounts?:Partial<Record<Kind,number>>;facets?:LibraryFacets;collectionCount?:number; collections?: LibraryCollection[]; mode: 'box'; collectionPlanningAvailable?:boolean; items: MediaItem[]; physicalInventory:PhysicalInventorySummary; hiddenItems: number; hiddenRecords: HiddenRecord[]; reviews:ReconciliationReview[]; reviewCount:number; settings: Settings; sources: Source[]; jobs: Job[]; storage: { total: number; free: number; used: number } | null; backup: { configured: boolean; lastVerified?: string; sameDevice?: boolean; path?: string; verifiedItems?: number; everyHours?: number }; version: string; profile?: OwnerProfile };
export const defaults: Settings = { streamingServiceOverrides:[], customStreamingServices:[], mediaRightsAttestation: null, helpTipsEnabled: true, name: 'My Blank Box', jellyfinUrl: '', plexUrl: '', immichUrl: '', remoteUrl: '', opticalDrive: '', setupDone: false, setupVersion: 1, setupMode: '', setupStep: 'welcome', mediaProvider: 'blankbox', mediaInputs: [], physicalFormats: ['DVD', 'Blu-ray', '4K UHD Blu-ray', 'Game', 'CD', 'Vinyl', 'Book', 'Comic'], physicalDefaultFormats: {}, physicalTitleSearchSource: 'packs', physicalLocations: [], gamePlatforms: [...commonGamePlatforms], gamePlatformCatalogVersion: 1, sidebarShortcuts: [], sidebarShortcutVersion: 1, sidebarOrder: ['library', 'collections', 'physical', 'movie', 'tv', 'music', 'photo', 'book', 'comic', 'game'], streamingServices: [], remoteProvider: 'local', autoImport: false, autoProviderRefresh: false, autoFolderCopy: false, autoSourceIndex: false, autoImportMinutes: 30, heroWatch: true, heroMusic: true, heroBooks: true, heroPhotos: false, heroComics: false, heroGames: false, homeRows: ['recently-added', 'recently-released'], homeHeroOrder: ['watch', 'music', 'book', 'photos', 'comics', 'games'], homeHeroSort: 'added' };
export const kindNames: Record<Kind,string> = { movie:'Movies',tv:'TV Shows',music:'Music',photo:'Photos','home-video':'Home Videos',book:'Books',comic:'Comics',game:'Games',file:'Files' };
export function digitalFileFormat(source:MediaSource){const extension=(source.path||'').split(/[?#]/)[0].split('.').pop();return extension&&extension!==source.path?extension.toUpperCase():source.mime||'Unknown file format';}
export function bytes(n=0) { if(!n)return '0 B'; const e=Math.min(Math.floor(Math.log(n)/Math.log(1024)),4); return `${(n/1024**e).toFixed(e>1?1:0)} ${['B','KB','MB','GB','TB'][e]}`; }
export function duration(n=0) { return `${Math.floor(n/60)}:${String(Math.floor(n%60)).padStart(2,'0')}`; }
// Stored duration is always seconds; book length is independently a page count.
export function mediaLength(item: MediaItem) {
 const seconds=item.duration;
 if(!seconds||!Number.isFinite(seconds)||seconds<=0)return '';
 if(item.kind==='music')return `${duration(seconds)} length`;
 const minutes=Math.floor(seconds/60),remainder=Math.floor(seconds%60);
 const value=minutes>=60?`${Math.floor(minutes/60)}h${minutes%60?` ${minutes%60}m`:''}`:minutes?`${minutes}m${remainder?` ${remainder}s`:''}`:`${remainder}s`;
 return item.kind==='tv'?`${value} listed runtime`:item.kind==='book'||item.kind==='comic'?`${value} audio length`:`${value} runtime`;
}
export function mediaTrackCount(item: MediaItem) { return item.catalogDetails?.trackCount ?? item.trackCount; }
export function mediaVersions(item:MediaItem):MediaVersion[]{return item.versions?.length?item.versions:[{id:'standard',label:'Standard or unknown edition',year:item.year,duration:item.duration}];}
export function sourcesForVersion(item:MediaItem,versionId:string){const fallback=mediaVersions(item)[0]?.id;return item.sources.filter(source=>(source.versionId||fallback)===versionId);}
export function sourceQuality(source:MediaSource){
 const value=[source.quality,source.edition,source.path].filter(Boolean).join(' ');
 if(/(?:2160p?|\b4k\b|uhd)/i.test(value))return '4K / UHD';
 if(/(?:1080p?|720p?|\bhd\b)/i.test(value))return 'HD';
 return '';
}
export function sourceSeason(source:MediaSource){
 if(source.season&&source.season!=='complete-series')return source.season;
 const path=source.path||'';
 const episode=path.match(/\bS(\d{1,3})[ ._-]*E\d{1,3}\b/i);
 if(episode)return episode[1];
 const folder=path.match(/(?:^|[\\/])season[ ._-]*(\d{1,3})(?:[\\/]|$)/i);
 return folder?folder[1]:source.season||'';
}
export function sourceEpisodeNumber(source:MediaSource){
 if(source.episodeNumber)return source.episodeNumber;
 const match=(source.path||'').match(/\bS\d{1,3}[ ._-]*E(\d{1,3})\b/i);
 return match?Number(match[1]):0;
}
export function sourceTrackNumber(source:MediaSource){
 if(source.trackNumber)return source.trackNumber;
 const name=(source.path||'').split(/[\\/]/).pop()||'';
 const match=name.match(/^(\d{1,3})[ ._-]+/);
 return match?Number(match[1]):0;
}
export function isFileSource(source:MediaSource){return source.type==='local'||source.type==='digital';}
export function isAudiobookSource(source:MediaSource){
 if(!isFileSource(source))return false;
 return !!source.audioBook||source.mime?.startsWith('audio/')===true||/\.(?:m4b|m4a|mp3|aac|flac|ogg|opus|wav)$/i.test((source.path||'').split(/[?#]/)[0]);
}
export function sourceGroupLabel(item:MediaItem,source:MediaSource){
 const quality=sourceQuality(source);
 if(item.kind==='tv'){
  const season=sourceSeason(source);
  if(season==='0'||season==='specials')return 'Specials';
  if(season==='complete-series')return 'Complete series files';
  if(/^\d{1,3}$/.test(season))return `Season ${Number(season)}`;
  return sourceEpisodeNumber(source)?'Unassigned episodes':'Other TV files';
 }
 if(item.kind==='music')return 'Album tracks';
 if(item.kind==='book'&&isAudiobookSource(source))return 'Audiobook';
 if(item.kind==='movie'&&quality)return `${quality} files`;
 return source.label||'Files';
}
export function sourceGroupKey(item:MediaItem,source:MediaSource){
 if(item.kind==='tv')return `tv:${sourceSeason(source)||'unknown'}`;
 if(item.kind==='music')return 'music:tracks';
 if(item.kind==='book'&&isAudiobookSource(source))return `${source.versionId||'standard'}:audiobook`;
 return `${source.versionId||'standard'}:${sourceGroupLabel(item,source)}`;
}
export function mediaFileGroups(item:MediaItem){
 const groups=new Map<string,{key:string;label:string;sources:MediaSource[]}>();
 for(const source of item.sources){
  if(!isFileSource(source))continue;
  const key=sourceGroupKey(item,source);
  let group=groups.get(key);
  if(!group){group={key,label:sourceGroupLabel(item,source),sources:[]};groups.set(key,group);}
  group.sources.push(source);
 }
 return [...groups.values()];
}
export function sourceSummaryCount(item:MediaItem){
 const physicalAndDemo=item.sources.filter(source=>source.type==='physical'||source.type==='demo').length;
 const connected=new Set(item.sources.filter(source=>source.type==='plex'||source.type==='jellyfin'||source.type==='emby').map(source=>source.type)).size;
 const files=item.sources.some(isFileSource)?item.kind==='tv'||item.kind==='music'?1:mediaFileGroups(item).length:0;
 return physicalAndDemo+connected+files;
}
const playbackPriority:Partial<Record<MediaSource['type'],number>>={local:0,digital:1,jellyfin:2,plex:3,emby:4,demo:5};
function isSupportedPlaybackUrl(value?:string){if(!value)return false;if(value.startsWith('/')&&!value.startsWith('//'))return true;try{const url=new URL(value);return ['https:','http:'].includes(url.protocol)&&!url.username&&!url.password;}catch{return false;}}
export function isPlayableSource(source:MediaSource){return source.available!==false&&playbackPriority[source.type]!==undefined&&isSupportedPlaybackUrl(source.url);}
export function isConnectedPlaybackSource(source?:MediaSource){return !!source&&['jellyfin','plex','emby'].includes(source.type);}
export function preferredPlaybackSource(item:MediaItem){
 const playable=item.sources.filter(isPlayableSource);
 // Details preference is an attached source ID, or 'blankbox' for local facts.
 // A missing/offline details source must never block another usable source.
 const chosen=item.metadataPreference&&item.metadataPreference!=='blankbox'?playable.find(source=>source.id===item.metadataPreference&&isConnectedPlaybackSource(source)):undefined;
 return chosen||playable.sort((left,right)=>(playbackPriority[left.type]??99)-(playbackPriority[right.type]??99))[0];
}
export function sharedReleaseCredits(item:Pick<MediaItem,'kind'|'artist'|'catalogDetails'>){
 const details=item.catalogDetails||{};
 const creators=item.kind==='music'?[item.artist].filter(Boolean):item.kind==='book'||item.kind==='comic'?details.authors?.length?details.authors:details.creators:item.kind==='movie'||item.kind==='tv'?details.directors?.length?details.directors:details.creators:details.creators;
 const publishers=item.kind==='movie'||item.kind==='tv'?details.studios:details.publishers;
 return {creator:(creators||[]).join(' · '),publisher:(publishers||[]).join(' · ')};
}
export type ReaderFormat = 'pdf' | 'epub' | 'cbz';
export function readerFormat(source:MediaSource):ReaderFormat|null{
 if(source.type!=='local'&&source.type!=='digital')return null;
 const name=(source.path||source.url||'').split(/[?#]/)[0].toLowerCase();
 if(source.mime==='application/pdf'||name.endsWith('.pdf'))return 'pdf';
 if(!source.id||!source.url?.startsWith('/media/'))return null;
 if(source.mime==='application/epub+zip'||name.endsWith('.epub'))return 'epub';
 if(source.mime==='application/vnd.comicbook+zip'||name.endsWith('.cbz'))return 'cbz';
 return null;
}
// Action wording follows the medium; provider selection and capability checks
// remain in the existing reader/player flow.
export function sourceActionLabel(item:MediaItem,source?:MediaSource,preview=false){
 if(item.kind==='photo')return 'View photo';
 if(!preview&&isConnectedPlaybackSource(source))return `Open ${source?.label}`;
 if(source&&readerFormat(source))return 'Read';
 if(item.kind==='book'&&source&&isAudiobookSource(source))return 'Listen';
 if(item.kind==='book')return 'Open book';
 if(item.kind==='comic')return 'Open comic';
 if(item.kind==='file'||item.kind==='game')return 'Open file';
 if(preview||source?.type==='local'||source?.type==='digital')return 'Play in Blank Box';
 if(source?.type==='demo')return 'Open sample';
 return 'No playable source';
}
export function preferredSourceLabel(kind:Kind){
 return kind==='book'||kind==='comic'?'Preferred reading source':kind==='file'||kind==='photo'||kind==='game'?'Preferred source':'Preferred playback';
}
function validTimestamp(value?:string){if(!value)return '';const parsed=Date.parse(value);return Number.isFinite(parsed)?new Date(parsed).toISOString():'';}
export function mediaAddedAt(item:MediaItem){
 const sourceDates=item.sources.map(source=>validTimestamp(source.addedAt)).filter(Boolean).sort();
 return sourceDates.at(-1)||validTimestamp(item.addedAt);
}
export function mediaReleaseAt(item:MediaItem){return validTimestamp(item.releaseDate)||(item.year?`${item.year}-01-01T00:00:00.000Z`:'');}
export function hasDigitalOrConnectedSource(item:MediaItem){return item.sources.some(source=>['local','jellyfin','plex','emby','digital'].includes(source.type));}
export type CollectionSummary={titles:number;physicalCopies:number;digitalOrConnectedSources:number;physicalFormats:{label:string;count:number}[]};
export function summarizeCollection(items:MediaItem[]):CollectionSummary{
 const formatCounts=new Map<string,number>();
 let physicalCopies=0,digitalOrConnectedSources=0;
 for(const item of items){
  if(hasDigitalOrConnectedSource(item))digitalOrConnectedSources++;
  for(const source of item.sources){
  if(source.type==='physical'){
   physicalCopies++;
   const label=source.label.trim()||'Physical';
   formatCounts.set(label,(formatCounts.get(label)||0)+1);
  }
  }
 }
 return {titles:items.length,physicalCopies,digitalOrConnectedSources,physicalFormats:[...formatCounts].map(([label,count])=>({label,count})).sort((left,right)=>left.label.localeCompare(right.label))};
}
export function summarizePhysicalInventory(items:MediaItem[]):PhysicalInventorySummary{
 const physicalItems=items.filter(item=>item.sources.some(source=>source.type==='physical'));
 const collection=summarizeCollection(items);
 return {titles:physicalItems.length,packages:collection.physicalCopies,copies:collection.physicalCopies,includedTitles:collection.physicalCopies,formats:collection.physicalFormats};
}
export function detectKind(name:string):Kind { const ext=name.split('.').pop()?.toLowerCase()??''; if(/^(jpg|jpeg|png|webp|heic|heif|avif|tif|tiff|gif)$/.test(ext))return 'photo'; if(/^(mp3|flac|wav|ogg|m4a|aac|opus)$/.test(ext))return 'music'; if(/^(cbz|cbr)$/.test(ext))return 'comic'; if(/^(pdf|epub|mobi|azw|azw3|m4b)$/.test(ext))return 'book'; if(/^(mp4|mkv|avi|mov|webm|m4v|mpg|mpeg|vob)$/.test(ext))return /s\d{1,2}e\d{1,3}/i.test(name)?'tv':/^(IMG|VID|DSC|MOV)[_\d-]/i.test(name.split('/').pop()??'')?'home-video':'movie'; return 'file'; }
