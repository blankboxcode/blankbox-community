import type { Preorder, PreorderDetail, PreorderPage, PreorderReceipt } from './preorders';
import type { BlankBoxCapabilities } from './capabilities';
import type { CatalogDetails, Job, Kind, LibraryState, MediaItem, OwnerProfile, TvCatalog, MusicCatalog } from './media';

export type LibraryPage = { items:MediaItem[];total:number;offset:number;limit:number;indexStatus:'building'|'ready'|'unavailable';shelfGroups:{location:string;copies:number;entries:{itemId:string;copies:number}[]}[] };
export type LibraryPageOptions = {standalonePhysical?:boolean;excludeSamples?:boolean;q?:string;view?:string;kind?:string;genre?:string;status?:string;sort?:string;favorites?:boolean;facet?:string;shelves?:boolean;collection?:string;offset?:number;limit?:number};
export type JobState = { catalogRevision?:string;browseIndexStatus?: 'building'|'ready'|'unavailable'; jobs: Job[]; collectionIndexStatus: 'building' | 'ready' | 'unavailable' };

export type AuthStatus = { hasProfile: boolean; accessKeyAvailable: boolean; oidcEnabled?:boolean; oidcName?:string };
export type CollectingTarget = { identifier?: { namespace: string; value: string }; id: string; title: string; kind: Kind; year: number | null; format: string; edition?: string; releaseId?: string | null; season?: string | null; workId?: string | null; createdAt: string; status: string; itemIds: string[] };
export type CompletionMember = { position: number; title: string; kind: Kind; year: number | null; format: string; workId: string | null; ignored: boolean; outcome: 'owned' | 'library' | 'wanted' | 'missing' | 'ignored' | 'review'; ownershipStatus: string; itemIds: string[]; matchBasis: string; intentMatchAmbiguous?: boolean };
export type CompletionSet = { id: string; name: string; kind: 'custom' | 'reference'; mediaKind: Kind; source: string; sourceVersion: string; sourceLicense: string; createdAt: string; updatedAt: string; members: CompletionMember[] };
export type CollectionRecommendationMember = { key: string; title: string; kind: Kind; year: number | null; format: string; workId?: string | null; candidateIds: string[]; itemIds: string[]; status: 'library' | 'missing' | 'wanted' | 'review'; reason: string; membershipReview?: string; creators?: string[]; matchBasis: string[] };
export type CollectionRecommendation = { id: string; name: string; kind: Kind; basis: 'title-pattern' | 'studio' | 'provider-collection'; source: string; coverage: 'known-references-only' | 'household-only'; counts: { library: number; known: number; wanted: number; review: number }; members: CollectionRecommendationMember[] };
export type CollectionRecommendations = { indexStatus?: 'ready' | 'building' | 'unavailable'; recommendations: CollectionRecommendation[]; packCoverage: { id: string; kind: Kind; version: string; works: number; genreRecords: number }[]; packErrors: string[] };
export type CollectionSuggestion = { id: string; name: string; kind: Kind; basis: 'reviewed-membership' | 'saved-set' | 'creator-candidates' | 'provider-seasons' | 'known-editions'; source: string; summary?: EditionSummary; items: { title: string; kind: Kind; year: number | null; format: string; edition?: string | null; releaseId?: string | null; season?: string | null; workId?: string | null; status?: string; outcome?: string; reason: string; itemIds: string[] }[] };
export type CommerceLink = { retailerId: string; sourceRegistryId: string; name: string; version: string; capabilities: string[]; url: string; linkKind: 'search' | 'store-home'; query: string; offerStatus: 'not-checked' };
export type StoreSource = { linkKind?: 'search' | 'store-home'; id: string; name: string; mediaKinds: Kind[]; enabledKinds: Kind[] };
export type CustomStoreSource = { id: string; name: string; urlTemplate: string; mediaKinds: Kind[] };
export type MetadataCandidate = { packName?:string;packVersion?:string;lookupIds?:string[]; catalogDetails?:CatalogDetails;description?:string;genre?:string;releaseDate?:string;duration?:number;identifiers?:{namespace:string;value:string}[]; id: string; title: string; kind: Kind; level: 'work' | 'release'; work_id: string | null; year: number | null; format?: string | null; edition?: string | null; season?: string | null; identifier?: { namespace: string; value: string }; householdItemIds?: string[]; origin: string; evidence: string[]; confidence: 'identifier' | 'title-year' | 'review'; requiresReview: true; candidateRef?: string; creator?: string };
export type EditionSummary = { known: number; owned: number; digital: number; missing: number; review: number; unknown: number; coverage: 'known-references-only'; status: 'unknown' | 'review' | 'gaps' | 'all-known-owned' };
export type MetadataEdition = { wanted?: boolean; identifier?: { namespace: string; value: string }; physicalReleaseIds?: string[]; digitalSourceIds?: string[]; id: string; title: string; year: number | null; format: string | null; edition: string | null; season: string | null; origin: string; status: 'owned' | 'digital' | 'missing' | 'review' | 'unknown' };
export type MetadataEntity = { id: string; title: string; kind: Kind; level: 'work' | 'release'; work_id: string | null; year: number | null; format: string | null; edition: string | null; season: string | null; origin: string; fields: { field: string; value: unknown; source: string; source_record_id: string; source_version: string; license: string; owner_entered: number; from_pack: number }[]; identifiers: { namespace: string; value: string; source: string; source_record_id: string; source_version: string; license: string }[]; artworkRefs: { role: string; reference: string; reference_type: 'local' | 'remote'; rights: string }[] };
export type CatalogResolution = { status: 'matched' | 'ambiguous' | 'unlinked'; itemId: string | null; itemIds: string[] };
export type CatalogIdentity = { itemId: string; localWorkId: string; effective: Partial<MediaItem>; sources: { itemId: string; id?: string; type: string; label?: string; versionId?: string; providerItemId?: string; physicalReleaseId?: string; ownedCopyId?: string; packageContentId?: string }[]; references: { id: string; level: 'work' | 'release'; title: string; origin: string; relationship: string; identifiers: { namespace: string; value: string }[] }[]; fieldEvidence: { entityId: string; field: string; value: unknown; source: string; sourceRecordId: string; sourceVersion: string; ownerEntered: boolean; fromPack: boolean }[] };
export type MetadataPackInfo = { description?:string;aliasCount?:number; id: string; version: string; license: string; source: string; sourceVersion?: string; recordCount: number; releaseCount?: number; displayName?: string; distribution?: string; kind?: Kind; recordLevel?: string; databaseBytes?: number; sourceSnapshot?: string };
export type MetadataCatalogPack = Partial<MetadataPackInfo> & Pick<MetadataPackInfo, 'id' | 'version'> & { bundleBytes?: number; status: 'available' | 'update' | 'installed' | 'installed-newer' | 'conflict' | 'damaged'; error?: string };

export type ScanFile = {
  id: string;
  name: string;
  title?: string;
  year?: number;
  bytes: number;
  kind: Kind;
  duplicate: boolean;
  candidates?: MediaItem[];
};

export type InventoryPage = {
  batch: null | { id: string; sourceId: string; status: string; startedAt: string; finishedAt: string | null; scanned: number; totalBytes: number; errors: string[] };
  files: { relative_path: string; kind: Kind; title: string; year: number | null; bytes: number; mtime_ns: number; linked_item_id: string | null; needs_review?:number; groupKey?:string; clues?:{evidence?:string[];artist?:string;trackTitle?:string;season?:number;episode?:number;episodeEnd?:number} }[];
  total: number;
  counts: { kind: Kind; count: number }[];
  groups?: { groupKey: string; title: string; kind: Kind; count: number; unlinked: number }[];
};

export type InventoryReview = {
  record: { path: string; title: string; kind: Kind; year: number | null; bytes: number; groupKey?:string; clues?:{evidence?:string[];artist?:string;trackTitle?:string;season?:number;episode?:number;episodeEnd?:number} };
  sourceId: string;
  linkedItemId: string | null;
  candidates: (MediaItem & { matchConfidence: 'high' | 'review'; matchReason: string })[];
};

export type ApiResult = {
  preorder?: Preorder;
  receipt?: PreorderReceipt;
  alreadyReceived?: boolean;
  error?: string;
  id?: string;
  batchId?: string;
  count?: number;
  waitingForConnection?: number;
  connected?: { jellyfin: boolean; plex: boolean };
  bytes?: number;
  partial?: boolean;
  points?: {id:string;createdAt:string}[];
  items?: MediaItem[];
  item?: MediaItem;
  results?: MediaItem[];
  candidates?: MediaItem[];
  record?: InventoryReview['record'];
  linkedItemId?: string | null;
  ok?: boolean;
  removedCopy?: boolean;
  alreadyLinked?: boolean;
  originalPath?: string;
  proposedPath?: string;
  changed?: boolean;
  collision?: boolean;
  movedCopies?: number;
  movedTitles?: number;
  devices?: string[];
  driveDetails?: { device: string; label: string; readable: boolean }[];
  tools?: { cdparanoia: boolean; flac: boolean };
  ready?: boolean;
  message?: string;
  platform?: 'linux' | 'windows' | 'other';
  mediaType?: 'audio-cd';
  device?: string;
  trackCount?: number;
  tocFingerprint?: string;
  discId?: string;
  packs?: MetadataPackInfo[];
  manifest?: MetadataPackInfo;
  packErrors?: string[];
  catalogPacks?: MetadataCatalogPack[];
  catalogError?: string;
  bundledProofAvailable?: boolean;
  entity?: MetadataEntity;
  editions?: MetadataEdition[];
  editionSummary?: EditionSummary;
  workId?: string;
  identity?: CatalogIdentity;
  status?: CatalogResolution['status'];
  itemId?: string | null;
  itemIds?: string[];
  links?: { target_type: string; target_id: string; entity_id: string; relationship: string; confirmed_at: string }[];
  storeLinks?: CommerceLink[];
  storeSources?: StoreSource[];
  customStoreSources?: CustomStoreSource[];
  tvCatalog?: TvCatalog;
  musicCatalog?: MusicCatalog;
  sourceId?: string;
};

export class BlankBoxClientError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'BlankBoxClientError';
    this.status = status;
  }
}

export interface BlankBoxClient {
  loadLibrary(): Promise<LibraryState>;
  libraryPage(options?:LibraryPageOptions, signal?:AbortSignal): Promise<LibraryPage>;
  item(id:string): Promise<MediaItem>;
  selection(ids:string[]):Promise<MediaItem[]>;
  collections(id?:string): Promise<{collections?:import('./collection-organization').LibraryCollection[];collection?:import('./collection-organization').LibraryCollection}>;
  jobs(): Promise<JobState>;
  capabilities(): Promise<BlankBoxCapabilities>;
  action(action: string, data?: Record<string, unknown>): Promise<ApiResult>;
  uploadMetadataPack(file: File): Promise<MetadataPackInfo>;
  uploadArtwork(itemId:string, image:Blob):Promise<MediaItem>;
  uploadGalleryArtwork(itemId:string,image:Blob,details:{releaseId:string;label:string;role:string}):Promise<MediaItem>;
  oidcStatus():Promise<{enabled:boolean;name:string;linked:boolean}>;
  startOIDC(purpose:'login'|'link',password?:string,remember?:boolean):Promise<string>;
  unlinkOIDC(password:string):Promise<void>;
  metadataSearch(query: { title?: string; kind?: Kind; year?: number | null; namespace?: string; value?: string; scope?: 'all' | 'packs' | 'saved'; excludeItemId?: string }): Promise<MetadataCandidate[]>;
  metadataCreate(record: { title: string; kind: Kind; level: 'work' | 'release'; year?: number | null; workId?: string; format?: string; edition?: string; season?: string }): Promise<MetadataEntity>;
  metadataGet(id: string): Promise<MetadataEntity>;
  catalogResolve(namespace: string, value: string): Promise<CatalogResolution>;
  catalogIdentity(itemId: string): Promise<CatalogIdentity>;
  metadataEdit(id: string, field: string, value: string | number | null): Promise<MetadataEntity>;
  metadataIdentifier(id: string, operation: 'add' | 'remove' | 'update', namespace: string, value: string, newValue?: string): Promise<MetadataEntity>;
  metadataConfirm(targetType: 'item' | 'physical_release' | 'digital_source', targetId: string, entityId: string, applyDetails?: boolean): Promise<MediaItem | undefined>;
  preorders(options?: { query?: string; status?: string; offset?: number }): Promise<PreorderPage>;
  preorder(id: string): Promise<PreorderDetail>;
  collecting(): Promise<{ targets: CollectingTarget[]; sets: CompletionSet[]; suggestions: CollectionSuggestion[] } & CollectionRecommendations>;
  scan(id: string): Promise<{ files: ScanFile[] }>;
  inventory(sourceId: string, options?: { limit?: number; offset?: number; kind?: string; query?: string; group?: string; unlinkedOnly?:boolean }): Promise<InventoryPage>;
  inventoryReview(data: { batchId: string; path: string; title: string; kind: Kind; year: number | null }): Promise<InventoryReview>;
  loginWithPassword(username: string, password: string, remember: boolean): Promise<void>;
  authStatus(): Promise<AuthStatus>;
  claimProfile(accessKey: string, username: string, displayName: string, password: string, remember: boolean): Promise<OwnerProfile>;
  recoverProfile(accessKey: string, username: string, password: string, remember: boolean): Promise<OwnerProfile>;
}

async function responseJson<T>(response: Response, fallback: string): Promise<T> {
  let value: unknown;
  try {
    value = await response.json();
  } catch {
    throw new BlankBoxClientError(fallback, response.status);
  }
  if (!response.ok) {
    const message = typeof value === 'object' && value !== null && 'error' in value && typeof value.error === 'string'
      ? value.error
      : fallback;
    throw new BlankBoxClientError(message, response.status);
  }
  return value as T;
}

/** Bound read requests, including body reads, so an idle connection can retry. */
export async function readJson<T>(url:string,fallback:string,signal?:AbortSignal,timeoutMs=15000):Promise<T> {
  const controller=new AbortController();
  const abort=()=>controller.abort();
  let timedOut=false;
  if(signal?.aborted)controller.abort();
  else signal?.addEventListener('abort',abort,{once:true});
  const timer=setTimeout(()=>{timedOut=true;controller.abort();},timeoutMs);
  try{return await responseJson<T>(await fetch(url,{cache:'no-store',signal:controller.signal}),fallback);}
  catch(cause){if(timedOut)throw new Error(`${fallback} The request timed out. Please retry.`);throw cause;}
  finally{clearTimeout(timer);signal?.removeEventListener('abort',abort);}
}

export class HttpBlankBoxClient implements BlankBoxClient {
  private pendingJobs: Promise<JobState> | null = null;
  private pendingLibrary: Promise<LibraryState> | null = null;
  jobs(): Promise<JobState> {
    if (!this.pendingJobs) {
      const pending=readJson<JobState>('/api/jobs','Unable to read operation progress.').finally(() => { if(this.pendingJobs===pending)this.pendingJobs=null; });
      this.pendingJobs=pending;
    }
    return this.pendingJobs;
  }
  loadLibrary(): Promise<LibraryState> {
    if(!this.pendingLibrary){const pending=readJson<LibraryState>('/api/library/summary','Unable to open your library.')
      .catch(cause=>{if(cause instanceof BlankBoxClientError&&cause.status===404)return readJson<LibraryState>('/api/library','Unable to open your library.');throw cause;})
      .finally(()=>{if(this.pendingLibrary===pending)this.pendingLibrary=null;});
      this.pendingLibrary=pending;
    }
    return this.pendingLibrary;
  }

  async libraryPage(options:LibraryPageOptions={}, signal?:AbortSignal):Promise<LibraryPage> {
    const params=new URLSearchParams(Object.entries(options).map(([k,v])=>[k,String(v)]));
    return readJson<LibraryPage>(`/api/library/items?${params}`,'Unable to browse your library.',signal);
  }
  async selection(ids:string[]):Promise<MediaItem[]> {
    if(!ids.length)return [];
    const params=new URLSearchParams(ids.map(id=>['id',id]));
    return (await responseJson<{items:MediaItem[]}>(await fetch(`/api/library/selection?${params}`,{cache:'no-store'}),'Unable to read selected titles.')).items;
  }
  async item(id:string):Promise<MediaItem> {
    const result=await responseJson<{item:MediaItem}>(await fetch(`/api/library/item?id=${encodeURIComponent(id)}`,{cache:'no-store'}),'Unable to open this title.');return result.item;
  }
  async collections(id?:string) {
    return responseJson<{collections?:import('./collection-organization').LibraryCollection[];collection?:import('./collection-organization').LibraryCollection}>(await fetch('/api/library/collections'+(id?`?id=${encodeURIComponent(id)}`:''),{cache:'no-store'}),'Unable to open collections.');
  }

  async capabilities(): Promise<BlankBoxCapabilities> {
    const response = await fetch('/api/v1/capabilities', { cache: 'no-store' });
    return responseJson<BlankBoxCapabilities>(response, 'Unable to read Blank Box capabilities.');
  }

  async action(action: string, data: Record<string, unknown> = {}): Promise<ApiResult> {
    const response = await fetch('/api/library', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, ...data }),
    });
    const result=await responseJson<ApiResult>(response, 'Please try again.');
    // Reads started before a completed write must not satisfy its refresh.
    this.pendingLibrary=null;this.pendingJobs=null;
    return result;
  }

  async uploadMetadataPack(file: File): Promise<MetadataPackInfo> {
    const response = await fetch('/api/metadata-pack/upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/vnd.blankbox.metadata-pack+zip' },
      body: file,
    });
    const result = await responseJson<ApiResult>(response, 'The metadata pack could not be installed.');
    if (!result.manifest) throw new BlankBoxClientError('The metadata pack was not installed.', 500);
    return result.manifest;
  }

  async uploadGalleryArtwork(itemId:string,image:Blob,details:{releaseId:string;label:string;role:string}):Promise<MediaItem> {
    const query=new URLSearchParams(details);const response=await fetch(`/api/artwork/gallery/upload/${encodeURIComponent(itemId)}?${query}`,{method:'POST',headers:{'Content-Type':'image/jpeg'},body:image});
    const result=await responseJson<ApiResult>(response,'The artwork could not be saved.');if(!result.item)throw new Error('The artwork could not be saved.');return result.item;
  }
  async oidcStatus():Promise<{enabled:boolean;name:string;linked:boolean}> {return responseJson(await fetch('/api/oidc/status',{cache:'no-store'}),'Unable to read identity settings.');}
  async startOIDC(purpose:'login'|'link',password?:string,remember=false):Promise<string> {const result=await responseJson<{url:string}>(await fetch('/api/oidc/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({purpose,password,remember})}),'Identity sign-in could not start.');return result.url;}
  async unlinkOIDC(password:string):Promise<void> {await responseJson(await fetch('/api/oidc/unlink',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password})}),'The identity could not be unlinked.');}

  async uploadArtwork(itemId:string,image:Blob):Promise<MediaItem> {
    const response=await fetch(`/api/artwork/upload/${encodeURIComponent(itemId)}`,{
      method:'POST',headers:{'Content-Type':'image/jpeg'},body:image,
    });
    const result=await responseJson<ApiResult>(response,'The cover could not be saved.');
    if(!result.item)throw new BlankBoxClientError('The cover could not be saved.',500);
    return result.item;
  }

  async metadataSearch(query: { title?: string; kind?: Kind; year?: number | null; namespace?: string; value?: string; scope?: 'all' | 'packs' | 'saved'; excludeItemId?: string }): Promise<MetadataCandidate[]> {
    const result = await this.action('metadata-search', query);
    return result.candidates ? result.candidates as unknown as MetadataCandidate[] : [];
  }

  async metadataCreate(record: { title: string; kind: Kind; level: 'work' | 'release'; year?: number | null; workId?: string; format?: string; edition?: string; season?: string }): Promise<MetadataEntity> {
    const result = await this.action('metadata-create', record);
    if (!result.entity) throw new BlankBoxClientError('Metadata record was not saved.', 500);
    return result.entity;
  }

  async metadataGet(id: string): Promise<MetadataEntity> {
    const result = await this.action('metadata-get', { id });
    if (!result.entity) throw new BlankBoxClientError('Metadata record was not found.', 404);
    return result.entity;
  }

  async catalogResolve(namespace: string, value: string): Promise<CatalogResolution> {
    const result = await this.action('catalog-resolve', { namespace, value });
    return { status: result.status || 'unlinked', itemId: result.itemId || null, itemIds: result.itemIds || [] };
  }

  async catalogIdentity(itemId: string): Promise<CatalogIdentity> {
    const result = await this.action('catalog-identity', { itemId });
    if (!result.identity) throw new BlankBoxClientError('Catalog identity was not found.', 404);
    return result.identity;
  }

  async metadataEdit(id: string, field: string, value: string | number | null): Promise<MetadataEntity> {
    const result = await this.action('metadata-edit', { id, field, value });
    if (!result.entity) throw new BlankBoxClientError('Metadata edit was not saved.', 500);
    return result.entity;
  }

  async metadataIdentifier(id: string, operation: 'add' | 'remove' | 'update', namespace: string, value: string, newValue?: string): Promise<MetadataEntity> {
    const result = await this.action(`metadata-identifier-${operation}`, { id, namespace, value, newValue });
    if (!result.entity) throw new BlankBoxClientError('Identifier change was not saved.', 500);
    return result.entity;
  }

  async metadataConfirm(targetType: 'item' | 'physical_release' | 'digital_source', targetId: string, entityId: string, applyDetails = false): Promise<MediaItem | undefined> {
    const result = await this.action('metadata-confirm', { targetType, targetId, entityId, confirm: true, applyDetails });
    if (applyDetails && !result.item) throw new BlankBoxClientError('The reference was not applied to the catalog item.', 500);
    return result.item;
  }

  async preorders(options: { query?: string; status?: string; offset?: number } = {}): Promise<PreorderPage> {
    const params = new URLSearchParams({ q: options.query || '', status: options.status || 'active', offset: String(options.offset || 0) });
    return responseJson<PreorderPage>(await fetch(`/api/preorders?${params}`, { cache: 'no-store' }), 'Unable to load preorders.');
  }

  async preorder(id: string): Promise<PreorderDetail> {
    return responseJson<PreorderDetail>(await fetch(`/api/preorders?id=${encodeURIComponent(id)}`, { cache: 'no-store' }), 'Unable to load order history.');
  }

  async collecting(): Promise<{ targets: CollectingTarget[]; sets: CompletionSet[]; suggestions: CollectionSuggestion[] } & CollectionRecommendations> {
    const response = await fetch('/api/collecting', { cache: 'no-store' });
    return responseJson(response, 'Unable to load your intend to buy list.');
  }

  async scan(id: string): Promise<{ files: ScanFile[] }> {
    const response = await fetch(`/api/scan?id=${encodeURIComponent(id)}`, { cache: 'no-store' });
    return responseJson<{ files: ScanFile[] }>(response, 'Unable to load the scan results.');
  }

  async inventory(sourceId: string, options: { limit?: number; offset?: number; kind?: string; query?: string; group?: string; unlinkedOnly?:boolean } = {}): Promise<InventoryPage> {
    const params = new URLSearchParams({ sourceId, limit: String(options.limit ?? 15), offset: String(options.offset ?? 0) });
    if (options.kind) params.set('kind', options.kind);
    if (options.query) params.set('q', options.query);
    if (options.group) params.set('group', options.group);
    if (options.unlinkedOnly) params.set('unlinked', '1');
    const response = await fetch(`/api/inventory?${params}`, { cache: 'no-store' });
    return responseJson<InventoryPage>(response, 'Unable to load the source inventory.');
  }

  async inventoryReview(data: { batchId: string; path: string; title: string; kind: Kind; year: number | null }): Promise<InventoryReview> {
    const response = await fetch('/api/library', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'inventory-review', ...data }),
    });
    return responseJson<InventoryReview>(response, 'Unable to review this file.');
  }

  async loginWithPassword(username: string, password: string, remember: boolean): Promise<void> {
    const response = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, remember }),
    });
    await responseJson<{ ok: true }>(response, 'That username or password did not match.');
  }

  async authStatus(): Promise<AuthStatus> {
    const response = await fetch('/api/auth/status', { cache: 'no-store' });
    return responseJson<AuthStatus>(response, 'Unable to read the sign-in status.');
  }

  async claimProfile(accessKey: string, username: string, displayName: string, password: string, remember: boolean): Promise<OwnerProfile> {
    const response = await fetch('/api/claim-profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ accessKey, username, displayName, password, remember }),
    });
    const result = await responseJson<{ ok: true; profile: OwnerProfile }>(response, 'Unable to create the owner profile.');
    return result.profile;
  }

  async recoverProfile(accessKey: string, username: string, password: string, remember: boolean): Promise<OwnerProfile> {
    const response = await fetch('/api/recover-profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ accessKey, username, password, remember }),
    });
    const result = await responseJson<{ ok: true; profile: OwnerProfile }>(response, 'Unable to recover the owner profile.');
    return result.profile;
  }
}

export const blankBoxClient: BlankBoxClient = new HttpBlankBoxClient();
