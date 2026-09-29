'use client';
/* eslint-disable @next/next/no-img-element -- Local/user media URLs need direct browser rendering and are not compatible with Next image optimization. */
import { useCallback, useDeferredValue, useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import { Home, Library, Layers3, Film, Tv, Music2, Images, BookOpen, Gamepad2, Disc3, Camera, List, Package, FolderOpen, HardDrive, ShieldCheck, Plus, Search, Play, ArrowLeft, ArrowUpRight, ArrowDownToLine, ChevronDown, ChevronRight, Check, Heart, Globe2, Settings2, Upload, FolderInput, X, Menu, PanelLeft, Info, Loader2, RefreshCw, LockKeyhole, CheckCircle2, Server, Cloud } from 'lucide-react';
import { Sidebar, SidebarContent, SidebarFooter, SidebarHeader, SidebarProvider, SidebarTrigger, useSidebar } from '@/components/ui/sidebar';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Checkbox } from '@/components/ui/checkbox';
import { Switch } from '@/components/ui/switch';
import { Toaster } from '@/components/ui/sonner';
import { toast } from 'sonner';
import { MediaActionIcon } from '@/components/media-action-icon';
import { LocalMediaPlayer } from '@/components/local-media-player';
import { MediaRightsChoice } from '@/components/media-rights';
import { MEDIA_RIGHTS_TERMS_VERSION } from '@/lib/media';
import { OnboardingWizard } from '@/components/onboarding-wizard';
import { MediaDetailDialog } from '@/components/media-detail-dialog';
import { CatalogEditorDialog, type MediaEdit } from '@/components/catalog-editor-dialog';
import { MetadataMatchDialog } from '@/components/metadata-match-dialog';
import { ReconciliationPanel, type ReviewPolicy } from '@/components/reconciliation-panel';
import { BrandLogo } from '@/components/brand-logo';
import { PhysicalBrowseControls } from '@/components/physical-browse-controls';
import { navigationLabels } from '@/lib/navigation';
import { AddPhysicalDialog } from '@/components/add-physical-dialog';
import { MetadataCandidateReview } from '@/components/metadata-candidate-review';
import { LocalSignIn } from '@/components/local-sign-in';
import { StartupScreen } from '@/components/startup-screen';
import { PhysicalOrganizationSettings } from '@/components/physical-organization-settings';
import { SidebarCustomization } from '@/components/sidebar-customization';
import { LibraryOverview } from '@/components/library-overview';
import { HomeCustomization } from '@/components/home-customization';
import { DocumentReader } from '@/components/document-reader';
import { DiscImport } from '@/components/disc-import';
import { MetadataPackManager } from '@/components/metadata-pack-manager';
import { OpticalDriveSettings } from '@/components/optical-drive-settings';
import { MusicPlayer } from '@/components/music-player';
import { SourceInventory } from '@/components/source-inventory';
import { CatalogListImport } from '@/components/catalog-list-import';
import { CollectionBrowser } from '@/components/collection-browser';
import { activityLabel, itemGenres, type ActivityStatus } from '@/lib/collection-organization';
import { barcodeEquivalent } from '@/lib/barcodes';
import { prepareCover } from '@/lib/artwork';
import { CameraPhysicalIntake, type CameraEntry } from '@/components/camera-physical-intake';
import { CollectionPlanner } from '@/components/collection-planner';
import { defaultHomeRows, featuredCoverPool, featuredMediaKeys, homeRowOptions, type HomeHeroMode, type HomeRow } from '@/lib/home-preferences';
import { normalizeSidebarOrder } from '@/lib/sidebar-preferences';
import { useIsMobile } from '@/hooks/use-mobile';
import { blankBoxClient, BlankBoxClientError, type MetadataCandidate, type ScanFile, type LibraryPage } from '@/lib/blank-box-client';
import { bytes, defaults, detectKind, hasDigitalOrConnectedSource, isAudiobookSource, isConnectedPlaybackSource, kindNames, mediaAddedAt, mediaReleaseAt, preferredPlaybackSource, readerFormat, sourceActionLabel, summarizeCollection, type Kind, type LibraryState, type MediaItem, type MediaSource, type ReaderFormat, type Settings, type StreamingService } from '@/lib/media';
import { defaultKindForFormat, emptyPhysicalDraft, physicalDraftForFormat, physicalDraftForKind, physicalFormatLabel, physicalFormats, physicalKindOptions, type PhysicalDraft, type PhysicalFormat } from '@/lib/physical-media';
import { BLANKBOX_CHANNEL, BLANKBOX_PACKAGE_NAME, BLANKBOX_VERSION } from '@/lib/version';
import './blank-box.css';
type View = 'home' | 'collections' | 'library' | 'physical' | 'collecting' | 'movie' | 'tv' | 'music' | 'photo' | 'book' | 'comic' | 'game' | 'import' | 'services' | 'storage' | 'settings';
type SettingsTab = 'general' | 'collection' | 'connections' | 'devices' | 'metadata' | 'activity';
const settingsTabs: {
    id: SettingsTab;
    label: string;
    icon: typeof Home;
}[] = [{ id: 'general', label: 'General', icon: Home }, { id: 'collection', label: 'Collection', icon: Library }, { id: 'connections', label: 'Connections', icon: Server }, { id: 'devices', label: 'Devices', icon: Disc3 }, { id: 'metadata', label: 'Metadata', icon: Search }, { id: 'activity', label: 'System & About', icon: Info }];
type HeroMode = HomeHeroMode;
type ImportPolicy = 'review' | 'keep' | 'incoming' | 'new-version' | 'separate';
declare const __BLANKBOX_COMMUNITY_BUILD__: boolean;
const icons = { movie: Film, tv: Tv, music: Music2, photo: Images, 'home-video': Film, book: BookOpen, comic: BookOpen, game: Gamepad2, file: FolderOpen };
const navItems: {
    id: View;
    label: string;
    icon: typeof Home;
}[] = [{ id: 'home', label: navigationLabels.home, icon: Home }, { id: 'library', label: navigationLabels.library, icon: Library }, { id: 'collections', label: navigationLabels.collections, icon: Layers3 }, { id: 'movie', label: navigationLabels.movie, icon: Film }, { id: 'tv', label: navigationLabels.tv, icon: Tv }, { id: 'music', label: navigationLabels.music, icon: Music2 }, { id: 'photo', label: navigationLabels.photo, icon: Images }, { id: 'book', label: navigationLabels.book, icon: BookOpen }, { id: 'comic', label: navigationLabels.comic, icon: BookOpen }, { id: 'game', label: navigationLabels.game, icon: Gamepad2 }, { id: 'physical', label: navigationLabels.physical, icon: Disc3 }];
const allServices: {
    id: StreamingService;
    name: string;
    mark: string;
    color: string;
    url: string;
}[] = [{ id: 'netflix', name: 'Netflix', mark: 'N', color: '#ed2439', url: 'https://www.netflix.com/' }, { id: 'prime-video', name: 'Prime Video', mark: 'prime', color: '#59b8ed', url: 'https://www.primevideo.com/' }, { id: 'disney-plus', name: 'Disney+', mark: 'Disney+', color: '#91acee', url: 'https://www.disneyplus.com/' }, { id: 'youtube', name: 'YouTube', mark: '▶', color: '#ff4444', url: 'https://www.youtube.com/' }, { id: 'spotify', name: 'Spotify', mark: 'Spotify', color: '#6dd799', url: 'https://open.spotify.com/' }, { id: 'apple-tv', name: 'Apple TV', mark: 'tv', color: '#ededed', url: 'https://tv.apple.com/' }];
const homeServices: {
    name: string;
    description: string;
    key: keyof Settings;
    icon: typeof Film;
}[] = [{ name: 'Jellyfin', description: 'Your video and music library', key: 'jellyfinUrl', icon: Film }, { name: 'Plex', description: 'Your connected media server', key: 'plexUrl', icon: Server }, { name: 'Immich', description: 'Your photos and phone backups', key: 'immichUrl', icon: Images }];
const emptyState: LibraryState = { mode: 'box', items: [], physicalInventory: { titles: 0, packages: 0, copies: 0, includedTitles: 0, formats: [] }, hiddenItems: 0, hiddenRecords: [], reviews: [], reviewCount: 0, settings: defaults, sources: [], jobs: [], storage: null, backup: { configured: false }, version: BLANKBOX_VERSION };
function safeUrl(s?: string) { try {
    const u = /^\/api\/playback\/plex\/[^/]+\/[^/]+$/.test(s || '') && typeof window !== 'undefined' ? new URL(s!, window.location.origin) : new URL(s || '');
    return ['https:', 'http:'].includes(u.protocol) && !u.username && !u.password ? u.href : '';
}
catch {
    return '';
} }
function collectionLabel(item: MediaItem) {
    if (item.sample)
        return 'Open movie';
    const preferred = preferredPlaybackSource(item);
    if (preferred?.type === 'digital')
        return 'Linked file on your drive';
    if (preferred?.type === 'local')
        return 'Digital file ready';
    if (isConnectedPlaybackSource(preferred))
        return `Connected to ${preferred.label}`;
    if (item.sources.some(source => source.type === 'catalog'))
        return 'Digital file cataloged';
    const physicalCopies = item.sources.filter(source => source.type === 'physical');
    if (physicalCopies.length)
        return physicalCopies.length === 1 ? physicalCopies[0].label : `${physicalCopies.length} physical copies`;
    return 'In your library';
}
function physicalBadge(item: MediaItem) {
    const formats = [...new Set(item.sources.filter(source => source.type === 'physical').map(source => source.label.trim()).filter(Boolean))].map(format => format === 'Game' ? physicalFormatLabel('Game') : format);
    const Icon = item.kind === 'game' ? Gamepad2 : item.kind === 'book' || item.kind === 'comic' ? BookOpen : item.kind === 'music' ? Music2 : item.kind === 'photo' || item.kind === 'home-video' ? Images : item.kind === 'movie' || item.kind === 'tv' ? Film : Disc3;
    return formats.length ? { Icon, label: formats.length === 1 ? formats[0] : `${formats[0]} +${formats.length - 1}`, title: formats.join(', ') } : null;
}
function physicalFacet(source: MediaSource, kind: Kind) {
    if (kind === 'game') {
        const platform = source.platform?.trim() || 'Platform not set';
        return { id: `platform:${platform}`, label: platform };
    }
    const format = source.label.trim() || 'Other';
    return { id: `format:${format}`, label: format === 'Game' ? 'Games' : format };
}
function preference(key: string, fallback: string) { if (typeof window === 'undefined')
    return fallback; try {
    return window.localStorage.getItem(key) ?? fallback;
}
catch {
    return fallback;
} }
function savePreference(key: string, value: string) { try {
    window.localStorage.setItem(key, value);
}
catch { /* Private browsing can disable local storage; UI state still works. */ } }
function stableCoverOrder(id: string) { let value = 2166136261; for (let index = 0; index < id.length; index++)
    value = Math.imul(value ^ id.charCodeAt(index), 16777619); return value >>> 0; }
function physicalMetadataSignature(draft: PhysicalDraft) { return JSON.stringify([draft.title, draft.kind, draft.year, draft.barcode, draft.format, draft.edition, draft.season]); }
function physicalTitleKey(title: string) { return title.normalize('NFKD').toLocaleLowerCase().replace(/[\u0300-\u036f]/g, '').replace(/[^\p{L}\p{N}]/gu, ''); }
function matchingPhysicalVersions(item: MediaItem, draft: PhysicalDraft) { return (item.versions || []).filter(version => item.sources.some(source => source.type === 'physical' && source.versionId === version.id && source.label === draft.format && (source.edition || '').trim().toLocaleLowerCase() === draft.edition.trim().toLocaleLowerCase() && (source.season || '') === draft.season)); }
function physicalMatchSource(item: MediaItem, source: 'household' | 'connected') {
    const hasConnected = item.sources.some(entry => entry.type === 'jellyfin' || entry.type === 'plex');
    return source === 'connected' ? hasConnected : true;
}
function Navigation({ view, go, state }: {
    view: View;
    go: (v: View) => void;
    state: LibraryState;
}) {
    const { setOpenMobile } = useSidebar();
    const navigate = (v: View) => { go(v); setOpenMobile(false); };
    const physicalCount = state.physicalInventory.copies;
    const item = ({ id, label, icon: Icon }: {
        id: View;
        label: string;
        icon: typeof Home;
    }) => <button data-tv key={id} className={`nav-item ${view === id ? 'selected' : ''}`} onClick={() => navigate(id)} aria-label={label} title={label} aria-current={view === id ? 'page' : undefined}><Icon size={19}/><span>{label}</span>{id === 'physical' && physicalCount > 0 && <small>{physicalCount}</small>}{id === 'import' && state.reviewCount > 0 ? <small>{state.reviewCount}</small> : id === 'import' ? <Plus size={14} className="nav-tail"/> : null}</button>;
    const profileName = state.profile?.displayName || state.settings.name;
    const homeItem = navItems.find(({ id }) => id === 'home')!;
    const libraryItems = normalizeSidebarOrder(state.settings.sidebarOrder).map(id => navItems.find(item => item.id === id)!).filter(({ id }) => (['library', 'physical'].includes(id) || id === 'collections' || state.settings.sidebarShortcuts?.includes(id as Settings['sidebarShortcuts'][number])));
    const utilityItems = [{ id: 'settings' as View, label: navigationLabels.settings, icon: Settings2 }, { id: 'import' as View, label: navigationLabels.import, icon: FolderInput }, { id: 'storage' as View, label: navigationLabels.storage, icon: HardDrive }, { id: 'services' as View, label: navigationLabels.services, icon: Globe2 }];
    return <Sidebar collapsible="icon" className="blank-box-sidebar">
  <SidebarHeader className="brand-header"><a href="#home" onClick={event => { event.preventDefault(); navigate('home'); }} className="brand" title="Blank Box"><BrandLogo responsive/></a></SidebarHeader>
  <SidebarContent className="side-content">
   <nav aria-label="Library navigation">{item(homeItem)}{libraryItems.map(item)}</nav>
   <nav className="utility-nav" aria-label="Settings and tools">{utilityItems.map(item)}</nav>
  </SidebarContent>
  <SidebarFooter className="side-footer"><NavigationToggle /><div className="profile"><div className="avatar">{profileName.trim().charAt(0).toUpperCase() || 'B'}</div><span className="profile-copy"><strong>{profileName}</strong><small>{state.profile ? `@${state.profile.username}` : 'Personal library'}</small></span></div></SidebarFooter>
 </Sidebar>;
}
function NavigationToggle({ mobileOnly = false }: {
    mobileOnly?: boolean;
}) {
    const { open, setOpenMobile } = useSidebar();
    if (mobileOnly)
        return <button data-tv type="button" className="navigation-toggle mobile-navigation-toggle" aria-label="Open navigation" title="Open navigation" onClick={() => setOpenMobile(true)}><Menu size={21}/></button>;
    return <><button data-tv type="button" className="navigation-toggle mobile-drawer-close" aria-label="Close navigation" onClick={() => setOpenMobile(false)}><X size={18}/><span>Close navigation</span></button><SidebarTrigger data-tv className="navigation-toggle desktop-sidebar-toggle" aria-label={open ? 'Collapse navigation' : 'Expand navigation'} title={open ? 'Collapse navigation' : 'Expand navigation'}><PanelLeft size={18}/><span>{open ? 'Collapse navigation' : 'Expand navigation'}</span></SidebarTrigger></>;
}
function ImportActivity({ jobs }: {
    jobs: LibraryState['jobs'];
}) {
    const imports = jobs.slice(0, 8);
    const active = imports.filter(job => ['queued', 'running'].includes(job.status));
    const label = (type: string) => ({ inventory: 'Indexing files in place', 'inventory-bulk-preview': 'Planning bulk matches', 'inventory-bulk-link': 'Linking reviewed files', 'source-monitor': 'Monitoring configured media folder', scan: 'Discovering your media', 'auto-discovery': 'Finding personal files for review', 'auto-import': 'Automatic folder refresh', jellyfin: 'Refreshing Jellyfin catalog', plex: 'Refreshing Plex catalog', 'disc-import': 'Digitizing audio CD', backup: 'Verifying library backup', 'full-recovery': 'Creating complete recovery point', 'prepare-full-restore': 'Preparing restore review copy', 'restore-provider-covers': 'Restoring saved provider covers', 'backup-indexed': 'Backing up selected files', 'backup-indexed-all': 'Backing up indexed personal files' } as Record<string, string>)[type] || 'Adding media to Blank Box';
    const time = (value?: string) => { if (!value)
        return ''; const parsed = new Date(value); return Number.isNaN(parsed.getTime()) ? '' : parsed.toLocaleString(); };
    return <details className="section activity-disclosure" open={active.length ? true : undefined}><summary><span><strong>Recent activity</strong><small>{active.length ? `${active.length} active` : imports.length ? 'Recent jobs' : 'No activity yet'}</small></span><ChevronDown size={18}/></summary><div className="activity-disclosure-body">{imports.length ? <div className="activity-list">{imports.map(job => <div className="job-row" key={job.id}><span className="job-icon">{job.status === 'complete' ? <CheckCircle2 /> : job.status === 'failed' ? <Info /> : <Loader2 className="animate-spin"/>}</span><div><strong>{label(job.type)}</strong><p>{job.message || `${job.done} of ${job.total} files · ${job.status}`}</p><small className="job-timestamp">{job.createdAt ? `Started ${time(job.createdAt)}` : 'Start time unavailable'}{job.finishedAt ? ` · Finished ${time(job.finishedAt)}` : ''}</small>{job.errors?.length ? <p className="error-text">{job.errors.slice(0, 3).join(' · ')}</p> : null}{job.type !== 'inventory' && ['running', 'queued'].includes(job.status) && <Progress value={job.total ? job.done / job.total * 100 : 0}/>}</div><span className="quiet-badge">{job.status}</span></div>)}</div> : <div className="empty-activity"><FolderInput size={21}/><span>Jobs will appear here.</span></div>}</div></details>;
}
function AutoCopyReview({ sourceId, refreshKey, blocked, onReview }: {
    sourceId: string;
    refreshKey: string;
    blocked: boolean;
    onReview: () => Promise<void>;
}) {
    const [pending, setPending] = useState<{
        count: number;
        bytes: number;
        files: {
            path: string;
            bytes: number;
        }[];
    } | null>(null);
    useEffect(() => { if (!sourceId)
        return; let active = true; fetch(`/api/auto-copy?sourceId=${encodeURIComponent(sourceId)}`, { cache: 'no-store' }).then(response => response.ok ? response.json() : null).then(value => { if (active)
        setPending(value as {
            count: number;
            bytes: number;
            files: {
                path: string;
                bytes: number;
            }[];
        } | null); }).catch(() => { if (active)
        setPending(null); }); return () => { active = false; }; }, [sourceId, refreshKey]);
    if (!sourceId || !pending?.count)
        return null;
    return <div className="auto-copy-review"><div><strong>{pending.count} personal {pending.count === 1 ? 'file' : 'files'} ready for copy review</strong><p className="muted small">{bytes(pending.bytes)} in this source. Automatic discovery never copies files. Review up to 100 at a time and confirm the selected total before copying.</p></div><button className="subtle-button" disabled={blocked} onClick={() => void onReview()}>Review proposed copies</button></div>;
}
export default function BlankBox() {
    const [state, setState] = useState<LibraryState>(emptyState), [loaded, setLoaded] = useState(false), [error, setError] = useState(''), [locked, setLocked] = useState(false);
    const [view, setView] = useState<View>('home'), [historyCount, setHistoryCount] = useState(1), [query, setQuery] = useState(''), [filter, setFilter] = useState('all'), [sort, setSort] = useState('recent'), [favorites, setFavorites] = useState(false), [selected, setSelected] = useState<MediaItem | null>(null), [catalogEditor, setCatalogEditor] = useState<MediaItem | null>(null), [editorOrigin, setEditorOrigin] = useState<'detail' | 'intake' | null>(null), [justAddedPhysical, setJustAddedPhysical] = useState<MediaItem | null>(null), [intakeChoice, setIntakeChoice] = useState<MediaItem | null>(null), [personalDetails, setPersonalDetails] = useState<MediaItem | null>(null), [pendingPhysicalCancel, setPendingPhysicalCancel] = useState<MediaItem | null>(null), [physicalReview, setPhysicalReview] = useState<{
        draft: PhysicalDraft;
        candidates: MediaItem[];
    } | null>(null), [playing, setPlaying] = useState<MediaItem | null>(null), [busy, setBusy] = useState(false), [addDisc, setAddDisc] = useState(false), [onboarding, setOnboarding] = useState(false), [tvMode, setTvMode] = useState(false), [sidebarOpen, setSidebarOpen] = useState(true), [heroIndex, setHeroIndex] = useState(0), [photoSeed] = useState(() => Math.random()), [matchOpen, setMatchOpen] = useState(false), [matchTarget, setMatchTarget] = useState<MediaItem | null>(null), [matchSeed, setMatchSeed] = useState(0);
    const [form, setForm] = useState<Settings>(defaults), [settingsTab, setSettingsTab] = useState<SettingsTab>('general'), [disc, setDisc] = useState<PhysicalDraft>(emptyPhysicalDraft), [sourceId, setSourceId] = useState(''), [scanId, setScanId] = useState(''), [scanRows, setScanRows] = useState<ScanFile[]>([]), [scanKinds, setScanKinds] = useState<Kind[]>(['photo', 'home-video', 'file']), [scanSelected, setScanSelected] = useState<Set<string>>(new Set()), [scanPage, setScanPage] = useState(0), [jellyKey, setJellyKey] = useState(''), [plexKey, setPlexKey] = useState(''), [backupSetupOpen, setBackupSetupOpen] = useState(false), [recoveryPoints, setRecoveryPoints] = useState<{
        id: string;
        createdAt: string;
    }[]>([]), [recoveryLoading, setRecoveryLoading] = useState(false);
    const [currentCameraScanId, setCurrentCameraScanId] = useState(''), [completedCameraScanId, setCompletedCameraScanId] = useState('');
    const [cameraReference, setCameraReference] = useState<{
        candidate: MetadataCandidate;
        signature: string;
    } | null>(null);
    const [physicalMetadata, setPhysicalMetadata] = useState<{
        id: string;
        signature: string;
        candidate?: MetadataCandidate;
    } | null>(null);
    const [separatePhysicalConfirmed, setSeparatePhysicalConfirmed] = useState(false);
    const [packMatchLookup, setPackMatchLookup] = useState<{
        key: string;
        matches: MediaItem[];
        error?: string;
    } | null>(null);
    const [packMatchRevision, setPackMatchRevision] = useState(0);
    const [physicalReviewSource, setPhysicalReviewSource] = useState<'household' | 'connected' | 'packs'>('household');
    const [physicalSearchQuery, setPhysicalSearchQuery] = useState('');
    const [physicalManual, setPhysicalManual] = useState(false);
    const physicalStart = useRef<PhysicalDraft>(emptyPhysicalDraft);
    const [editorRevision, setEditorRevision] = useState(0);
    const [physicalChoice, setPhysicalChoice] = useState<{
        item: MediaItem;
        mode: 'same' | 'new' | null;
        versionId: string;
        metadataEntityId?: string;
    } | null>(null);
    const [physicalIntakeTarget, setPhysicalIntakeTarget] = useState<MediaItem | null>(null);
    const [physicalView, setPhysicalView] = useState<'grid' | 'shelves'>('grid'), [physicalFormatFilter, setPhysicalFormatFilter] = useState('all');
    const [reading, setReading] = useState<{
        item: MediaItem;
        source: MediaSource;
        url: string;
        format: ReaderFormat;
    } | null>(null);
    const [rightsOpen, setRightsOpen] = useState(false), [rightsAccepted, setRightsAccepted] = useState(false);
    const rightsOffered = useRef(false);
    useEffect(() => { if (state.settings.setupDone && !(state.settings.mediaRightsAttestation?.accepted && state.settings.mediaRightsAttestation.termsVersion === MEDIA_RIGHTS_TERMS_VERSION) && !rightsOffered.current) {
        rightsOffered.current = true;
        setRightsOpen(true);
    } }, [state.mode, state.settings.setupDone, state.settings.mediaRightsAttestation]);
    const pendingPlayback = useRef<(() => void) | null>(null);
    const [playbackAlternatives, setPlaybackAlternatives] = useState<MediaSource[]>([]);
    const [musicStartSourceId, setMusicStartSourceId] = useState<string | undefined>();
    const [importPolicy, setImportPolicy] = useState<ImportPolicy>('review');
    const [listImportOpen, setListImportOpen] = useState(false);
    const [cameraIntakeOpen, setCameraIntakeOpen] = useState(false), [cameraEntryActive, setCameraEntryActive] = useState(false);
    const visibleScanRows = useMemo(() => scanRows.filter(file => scanKinds.includes(file.kind)), [scanRows, scanKinds]);
    const [genreFilter, setGenreFilter] = useState(''), [activityFilter, setActivityFilter] = useState<ActivityStatus | ''>('');
    const selectedScanRows = useMemo(() => visibleScanRows.filter(file => scanSelected.has(file.id)), [visibleScanRows, scanSelected]);
    const isMobile = useIsMobile();
    const activeTvMode = tvMode && !isMobile;
    const [sourceReviewOpen, setSourceReviewOpen] = useState(false);
    const filesRef = useRef<HTMLInputElement>(null), searchRef = useRef<HTMLInputElement>(null), physicalReviewDialogRef = useRef<HTMLDivElement>(null), pollRef = useRef(false), scanRef = useRef(''), reviewJobWatchRef = useRef<{
        jobId: string;
        baseline: number;
    } | null>(null), normalSidebarOpenRef = useRef(true), viewRef = useRef<View>('home'), viewHistoryRef = useRef<View[]>(['home']);
    const [libraryPage, setLibraryPage] = useState({ key: '', page: 0 });
    const [librarySelectionMode, setLibrarySelectionMode] = useState(false);
    const [librarySelection, setLibrarySelection] = useState<Set<string>>(new Set());
    const [libraryAttachRows, setLibraryAttachRows] = useState<MediaItem[]>([]);
    const [libraryAttachQuery, setLibraryAttachQuery] = useState('');
    const [libraryAttachResults, setLibraryAttachResults] = useState<MediaItem[]>([]);
    const [libraryAttachTarget, setLibraryAttachTarget] = useState<MediaItem | null>(null);
    const [libraryAttachError, setLibraryAttachError] = useState('');
    const settingsDirty = JSON.stringify(form) !== JSON.stringify(state.settings);
    const confirmSettingsExit = useCallback(() => viewRef.current !== 'settings' || !settingsDirty || window.confirm('You have unsaved settings. Leave this page and discard those changes?'), [settingsDirty]);
    const changeView = useCallback((v: View, back = false) => { const prior = viewRef.current; if (v === prior)
        return true; if (!confirmSettingsExit())
        return false; if (prior === 'settings')
        setForm(state.settings); viewRef.current = v; setView(v); setLibrarySelectionMode(false); setLibrarySelection(new Set()); setQuery(''); setFilter('all'); setPhysicalFormatFilter('all'); setFavorites(false); setGenreFilter(''); setActivityFilter(''); if (back)
        viewHistoryRef.current.pop();
    else if (viewHistoryRef.current.at(-1) !== v)
        viewHistoryRef.current.push(v); setHistoryCount(viewHistoryRef.current.length); window.scrollTo({ top: 0, behavior: 'instant' }); return true; }, [confirmSettingsExit, state.settings]);
    const go = useCallback((v: View) => { if (changeView(v))
        window.location.hash = v; }, [changeView]);
    const goBack = () => { const previous = viewHistoryRef.current.at(-2); if (previous && changeView(previous, true))
        window.location.hash = previous; };
    const reload = useCallback(async () => { try {
        const data = await blankBoxClient.loadLibrary();
        setState(data);
        setLoaded(true);
        setLocked(false);
        setError('');
        return data;
    }
    catch (e) {
        if (e instanceof BlankBoxClientError && e.status === 401)
            setLocked(true);
        setError((e as Error).message);
        return null;
    } }, []);
    // Initializing from the authenticated external store is the purpose of this effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    useEffect(() => { reload().then(s => { if (s) {
        setForm(s.settings);
        if (!s.settings.setupDone)
            setOnboarding(true);
    } }); const frame = requestAnimationFrame(() => { const initial = window.location.hash.slice(1) as View; if (['home', 'library', 'collections', 'physical', 'collecting', 'movie', 'tv', 'music', 'photo', 'book', 'comic', 'game', 'import', 'services', 'storage', 'settings'].includes(initial)) {
        viewRef.current = initial;
        viewHistoryRef.current = [initial];
        setView(initial);
    } const savedTvMode = preference('blank-box-tv', '0') === '1', savedNormalSidebar = preference('blank-box-sidebar', '1') !== '0'; normalSidebarOpenRef.current = savedNormalSidebar; setTvMode(savedTvMode); setSidebarOpen(savedTvMode ? false : savedNormalSidebar); }); return () => { cancelAnimationFrame(frame); }; }, [reload]);
    useEffect(() => { const hash = () => { const next = window.location.hash.slice(1) as View; if (!['home', 'library', 'collections', 'physical', 'collecting', 'movie', 'tv', 'music', 'photo', 'book', 'comic', 'game', 'import', 'services', 'storage', 'settings'].includes(next) || next === viewRef.current)
        return; if (!changeView(next))
        window.history.replaceState(null, '', `#${viewRef.current}`); }; window.addEventListener('hashchange', hash); return () => window.removeEventListener('hashchange', hash); }, [changeView]);
    useEffect(() => { if (view !== 'settings' || !settingsDirty)
        return; const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ''; }; window.addEventListener('beforeunload', warn); return () => window.removeEventListener('beforeunload', warn); }, [view, settingsDirty]);
    useEffect(() => { const key = (e: KeyboardEvent) => { if (e.key === '/' && !/INPUT|TEXTAREA/.test((e.target as HTMLElement).tagName)) {
        e.preventDefault();
        searchRef.current?.focus();
    } if (!activeTvMode || !e.key.startsWith('Arrow') || /INPUT|TEXTAREA|SELECT/.test((e.target as HTMLElement).tagName) || document.querySelector('[role="dialog"]'))
        return; const current = document.activeElement as HTMLElement; if (!current?.matches('[data-tv]'))
        return; const a = current.getBoundingClientRect(); let best: HTMLElement | null = null; let score = Infinity; document.querySelectorAll<HTMLElement>('[data-tv]').forEach(el => { if (el === current || el.getAttribute('disabled') !== null)
        return; const b = el.getBoundingClientRect(); if (!b.width || !b.height)
        return; const dx = b.left + b.width / 2 - a.left - a.width / 2, dy = b.top + b.height / 2 - a.top - a.height / 2; const along = e.key === 'ArrowRight' ? dx : e.key === 'ArrowLeft' ? -dx : e.key === 'ArrowDown' ? dy : -dy; const across = e.key === 'ArrowRight' || e.key === 'ArrowLeft' ? Math.abs(dy) : Math.abs(dx); if (along > 5 && along + across * 3 < score) {
        best = el;
        score = along + across * 3;
    } }); if (best) {
        e.preventDefault();
        (best as HTMLElement).focus();
    } }; window.addEventListener('keydown', key); return () => window.removeEventListener('keydown', key); }, [activeTvMode]);
    useEffect(() => {
        if (!state.jobs.some(j => ['queued', 'running'].includes(j.status)) && state.browseIndexStatus !== 'building')
            return;
        let active = true;
        let timer: ReturnType<typeof setTimeout>;
        async function poll() {
            if (pollRef.current) {
                if (active)
                    timer = setTimeout(() => void poll(), 3000);
                return;
            }
            pollRef.current = true;
            try {
                const status = await blankBoxClient.jobs();
                if (!active)
                    return;
                const indexFinished = state.browseIndexStatus === 'building' && status.browseIndexStatus !== 'building';
                const finished = indexFinished || state.jobs.some(previous => ['queued', 'running'].includes(previous.status) && status.jobs.some(job => job.id === previous.id && !['queued', 'running'].includes(job.status)));
                if (finished) {
                    const snapshot = await reload();
                    if (snapshot && scanRef.current && snapshot.jobs.some(j => j.id === scanRef.current && ['complete', 'partial'].includes(j.status))) {
                        try {
                            const data = await blankBoxClient.scan(scanRef.current);
                            setScanRows(data.files);
                            setScanSelected(new Set());
                            setScanPage(0);
                            scanRef.current = '';
                        }
                        catch { /* A later refresh can retry the scan. */ }
                    }
                    const watch = reviewJobWatchRef.current, job = watch && snapshot?.jobs.find(candidate => candidate.id === watch.jobId);
                    if (watch && job && !['queued', 'running'].includes(job.status)) {
                        if ((snapshot?.reviewCount || 0) > watch.baseline)
                            setSourceReviewOpen(true);
                        reviewJobWatchRef.current = null;
                    }
                }
                else
                    setState(previous => ({ ...previous, jobs: status.jobs }));
            }
            catch { /* A transient progress error retries without fetching the whole catalog. */ }
            finally {
                pollRef.current = false;
                if (active)
                    timer = setTimeout(() => void poll(), 3000);
            }
        }
        timer = setTimeout(() => void poll(), 3000);
        return () => { active = false; clearTimeout(timer); };
    }, [state.jobs, state.browseIndexStatus, reload]);
    useEffect(() => {
        if (false || !state.pagedLibrary || state.jobs.some(job => ['queued', 'running'].includes(job.status)) || state.browseIndexStatus === 'building')
            return;
        let active = true;
        let pending = false;
        const timer = setInterval(() => { if (document.hidden || pending)
            return; pending = true; void blankBoxClient.jobs().then(async (status) => { if (!active)
            return; const prior = new Map(state.jobs.map(job => [job.id, job.status])); if (status.browseIndexStatus === 'building') {
            setState(current => ({ ...current, browseIndexStatus: 'building', jobs: status.jobs }));
            return;
        } if (status.catalogRevision !== state.catalogRevision || status.jobs.some(job => prior.get(job.id) !== job.status)) {
            await reload();
        } }).catch(() => { }).finally(() => { pending = false; }); }, 30000);
        return () => { active = false; clearInterval(timer); };
    }, [state.mode, state.pagedLibrary, state.jobs, state.browseIndexStatus, state.catalogRevision, reload]);
    const [hiddenOffset, setHiddenOffset] = useState(0);
    useEffect(() => { if (!state.pagedLibrary || view !== 'settings' || settingsTab !== 'connections')
        return; let active = true; void fetch(`/api/library/hidden?offset=${hiddenOffset}`, { cache: 'no-store' }).then(response => { if (!response.ok)
        throw new Error('Unable to read hidden items.'); return response.json(); }).then(value => { if (active)
        setState(current => ({ ...current, hiddenRecords: (value as {
                records: LibraryState['hiddenRecords'];
            }).records as LibraryState['hiddenRecords'] })); }).catch(cause => { if (active)
        toast.error((cause as Error).message); }); return () => { active = false; }; }, [state.pagedLibrary, state.hiddenItems, view, settingsTab, hiddenOffset]);
    useEffect(() => { if (!state.pagedLibrary || !(view === 'import' || sourceReviewOpen))
        return; let active = true; void fetch('/api/library/reviews', { cache: 'no-store' }).then(response => { if (!response.ok)
        throw new Error('Unable to read match reviews.'); return response.json(); }).then(value => { if (active)
        setState(current => ({ ...current, reviews: (value as {
                reviews: LibraryState['reviews'];
            }).reviews as LibraryState['reviews'] })); }).catch(cause => { if (active)
        toast.error((cause as Error).message); }); return () => { active = false; }; }, [state.pagedLibrary, state.items, view, sourceReviewOpen]);
    const act = async (action: string, data: Record<string, unknown>, message?: string) => { const reviewBaseline = state.reviewCount; setBusy(true); try {
        const v = await blankBoxClient.action(action, data), snapshot = await reload(), watchesReviews = ['jellyfin', 'plex'].includes(action) || action === 'import' && data.policy === 'review';
        if (watchesReviews && v.id) {
            const job = snapshot?.jobs.find(candidate => candidate.id === v.id);
            if (job && !['queued', 'running'].includes(job.status)) {
                if ((snapshot?.reviewCount || 0) > reviewBaseline)
                    setSourceReviewOpen(true);
            }
            else
                reviewJobWatchRef.current = { jobId: v.id, baseline: reviewBaseline };
        }
        if (message)
            toast.success(message);
        return v;
    }
    catch (e) {
        toast.error((e as Error).message);
    }
    finally {
        setBusy(false);
    } };
    const loadRecoveryPoints = async () => { setRecoveryLoading(true); try {
        const result = await blankBoxClient.action('full-recovery-points');
        setRecoveryPoints(result.points || []);
    }
    catch (e) {
        toast.error((e as Error).message);
    }
    finally {
        setRecoveryLoading(false);
    } };
    const prepareRecovery = async (id: string) => { if (!window.confirm('Verify and copy this complete recovery point into a new review directory? This can use substantial space. Your current library will keep running and will not be replaced.'))
        return; await act('prepare-full-restore', { id }, 'Restore preparation started. Watch its job below.'); };
    const restoreMissingCovers = async () => { setBusy(true); try {
        const preview = await blankBoxClient.action('missing-provider-covers');
        const count = preview.count || 0;
        if (!count) {
            toast.info(preview.waitingForConnection ? 'Saved provider covers were found, but their Plex or Jellyfin connection needs to be reconnected first.' : 'No missing covers with saved connected provider artwork were found.');
            return;
        }
        if (!window.confirm(`Use saved Plex or Jellyfin covers for ${count} ${count === 1 ? 'title' : 'titles'} without a cover? Uploaded covers, title details, and metadata source choices stay as they are.`))
            return;
        await act('restore-provider-covers', { confirm: true, expectedCount: count }, 'Cover restoration started. Watch its job below.');
    }
    catch (e) {
        toast.error((e as Error).message);
    }
    finally {
        setBusy(false);
    } };
    const persistSettings = async (next: Settings, close = false) => { setForm(next); const v = await act('settings', { settings: next }, close ? 'Setup complete' : 'Settings saved'); if (v)
        setHeroIndex(0); if (v && close)
        setOnboarding(false); return !!v; };
    const saveSettings = async (close = false) => persistSettings(form, close);
    const savePhysicalLocation = async (location: string) => { const value = location.trim(); if (!value)
        return false; if (form.physicalLocations.some(saved => saved.toLocaleLowerCase() === value.toLocaleLowerCase()))
        return true; return persistSettings({ ...form, physicalLocations: [...form.physicalLocations, value].sort((left, right) => left.localeCompare(right)) }); };
    const saveVisiblePhysicalFormats = async (physicalFormats: PhysicalFormat[]) => persistSettings({ ...form, physicalFormats });
    const saveVisibleGamePlatforms = async (gamePlatforms: string[]) => persistSettings({ ...form, gamePlatforms });
    const openEditor = (item: MediaItem, origin: 'detail' | 'intake') => { setEditorOrigin(origin); setCatalogEditor(item); };
    const backFromEditor = () => { if (!catalogEditor)
        return; if (editorOrigin === 'intake' && intakeChoice) {
        setCatalogEditor(null);
        setJustAddedPhysical(intakeChoice);
        return;
    } setCatalogEditor(null); setSelected(catalogEditor); setEditorOrigin(null); };
    const requestPhysicalCancel = (item: MediaItem, preserveEditor = false) => { const current = state.items.find(candidate => candidate.id === item.id) || item; if (!preserveEditor) {
        setCatalogEditor(null);
        setPersonalDetails(null);
        setJustAddedPhysical(null);
        setMatchOpen(false);
        setEditorOrigin(null);
    } if (current.sources.length !== 1 || current.sources[0]?.type !== 'physical') {
        setCatalogEditor(null);
        setEditorOrigin(null);
        setIntakeChoice(null);
        setSelected(current);
        toast.info('This title has other sources. Use its details to remove a specific physical copy.');
        return;
    } setPendingPhysicalCancel(current); };
    const closeEditor = () => { if (editorOrigin === 'intake' && catalogEditor) {
        requestPhysicalCancel(catalogEditor, true);
        return;
    } setCatalogEditor(null); setEditorOrigin(null); };
    const cancelPhysicalImport = async () => { if (!pendingPhysicalCancel)
        return; const item = pendingPhysicalCancel; const result = await act('delete', { id: item.id, confirmId: item.id, cancelPhysicalIntake: true, physicalSourceId: item.sources[0]?.id }, 'Physical import canceled'); if (result) {
        setPendingPhysicalCancel(null);
        setCatalogEditor(null);
        setPersonalDetails(null);
        setJustAddedPhysical(null);
        setIntakeChoice(null);
        setSelected(null);
        setMatchOpen(false);
        setMatchTarget(null);
        setEditorOrigin(null);
    } };
    const physicalPayload = (draft: PhysicalDraft) => Object.fromEntries(Object.entries({ ...draft, title: draft.title.trim(), location: draft.location.trim(), ...(draft.year ? { year: Number(draft.year) } : {}) }).filter(([, value]) => value !== ''));
    const rememberPhysicalDraft = (draft: PhysicalDraft) => setForm(current => ({ ...current, physicalLocations: draft.location.trim() && !current.physicalLocations.some(value => value.toLocaleLowerCase() === draft.location.trim().toLocaleLowerCase()) ? [...current.physicalLocations, draft.location.trim()].sort((left, right) => left.localeCompare(right)) : current.physicalLocations, gamePlatforms: draft.platform.trim() && !current.gamePlatforms.some(value => value.toLocaleLowerCase() === draft.platform.trim().toLocaleLowerCase()) ? [...current.gamePlatforms, draft.platform.trim()].sort((left, right) => left.localeCompare(right)) : current.gamePlatforms }));
    const intakeFormats = physicalFormats.filter(format => form.physicalFormats.includes(format));
    const physicalLocations = useMemo(() => [...new Set([...form.physicalLocations, ...state.items.flatMap(item => item.sources.filter(source => source.type === 'physical').map(source => source.location || '')).filter(Boolean)])].sort((left, right) => left.localeCompare(right)), [form.physicalLocations, state.items]);
    const gamePlatforms = form.gamePlatforms;
    const openPhysicalPreferences = () => { setSettingsTab('collection'); go('settings'); window.setTimeout(() => document.getElementById('physical-media-settings')?.scrollIntoView({ behavior: 'smooth' }), 0); };
    const openPhysicalFor = (formats: PhysicalFormat[]) => { if (!formats.length) {
        openPhysicalPreferences();
        toast.info('Choose the physical formats you use in Physical Media preferences.');
        return;
    } const format = formats.includes(disc.format) ? disc.format : formats[0]; const draft = { ...emptyPhysicalDraft, format, kind: defaultKindForFormat(format) }; physicalStart.current = draft; setDisc(draft); setPhysicalManual(false); setAddDisc(true); };
    const openPhysical = () => { setPhysicalIntakeTarget(null); setCameraEntryActive(false); openPhysicalFor(intakeFormats); };
    const openPhysicalForItem = (item: MediaItem) => {
        const compatible = intakeFormats.filter(format => physicalKindOptions(format).includes(item.kind));
        if (!compatible.length) {
            setCatalogEditor(null);
            setEditorOrigin(null);
            setSelected(null);
            openPhysicalPreferences();
            toast.info('Choose a physical format for this media type before adding a copy.');
            return;
        }
        const recorded = item.sources.find(source => source.type === 'physical' && compatible.includes(source.label as PhysicalFormat));
        const format = (recorded?.label as PhysicalFormat | undefined) ?? compatible[0];
        setDisc({ ...emptyPhysicalDraft, format, kind: item.kind, title: item.title, year: item.year ? String(item.year) : '', genre: item.genre || '', description: item.description || '' });
        physicalStart.current = { ...emptyPhysicalDraft, format, kind: item.kind };
        setPhysicalManual(false);
        setPhysicalIntakeTarget(item);
        setCameraEntryActive(false);
        setCatalogEditor(null);
        setEditorOrigin(null);
        setSelected(null);
        setAddDisc(true);
    };
    const cameraArtwork = useRef<File | null>(null);
    const useCameraEntry = ({ scanId, code, title, match, candidate, artwork }: CameraEntry) => {
        cameraArtwork.current = artwork || null;
        const matchedSource = match?.sources.find(source => source.type === 'physical' && !!source.barcode && barcodeEquivalent(source.barcode, code));
        const matchedFormat = matchedSource && physicalFormats.includes(matchedSource.label as PhysicalFormat) ? matchedSource.label as PhysicalFormat : undefined;
        const candidateFormat = candidate?.format && physicalFormats.includes(candidate.format as PhysicalFormat) ? candidate.format as PhysicalFormat : undefined;
        const format = matchedFormat || candidateFormat || (candidate?.kind === 'book' ? 'Book' : candidate?.kind === 'music' ? 'CD' : candidate?.kind === 'comic' ? 'Comic' : candidate?.kind === 'game' ? 'Game' : intakeFormats[0] || 'DVD');
        const draft = { ...emptyPhysicalDraft, format, kind: match?.kind || candidate?.kind || defaultKindForFormat(format), title: title || match?.title || '', year: candidate?.year ? String(candidate.year) : match?.year ? String(match.year) : '', barcode: code, edition: matchedSource?.edition || candidate?.edition || '', season: matchedSource?.season || candidate?.season || '', platform: matchedSource?.platform || '' };
        physicalStart.current = { ...emptyPhysicalDraft, format, kind: draft.kind };
        setPhysicalManual(false);
        setCurrentCameraScanId(scanId);
        setDisc(draft);
        setCameraReference(candidate ? { candidate, signature: physicalMetadataSignature(draft) } : null);
        setPhysicalIntakeTarget(null);
        setCameraEntryActive(true);
        setCameraIntakeOpen(false);
        setAddDisc(true);
    };
    const saveScannedArtwork = async (item: MediaItem) => { const file = cameraArtwork.current; cameraArtwork.current = null; if (!file)
        return item; try {
        const updated = await blankBoxClient.uploadArtwork(item.id, await prepareCover(file));
        await reload();
        toast.success('Scanned cover saved to Blank Box details.');
        return updated;
    }
    catch (error) {
        toast.error(`Physical item saved, but its cover could not be saved: ${(error as Error).message} Upload it from Edit details.`);
        return item;
    } };
    const createPhysical = async (draft: PhysicalDraft, metadataEntityId?: string) => { const v = await act('physical', { ...physicalPayload(draft), ...(metadataEntityId ? { metadataEntityId } : {}) }, 'Added to your Physical Media'); if (v?.item) {
        const added = await saveScannedArtwork(v.item as MediaItem);
        rememberPhysicalDraft(draft);
        setPhysicalMetadata(null);
        const format = intakeFormats[0] || 'DVD';
        setDisc({ ...emptyPhysicalDraft, format, kind: defaultKindForFormat(format) });
        setAddDisc(false);
        setPhysicalReview(null);
        if (cameraEntryActive) {
            setCompletedCameraScanId(currentCameraScanId);
            setCurrentCameraScanId('');
            setCameraEntryActive(false);
            go('import');
            setCameraIntakeOpen(true);
        }
        else {
            go('physical');
            setSelected(added);
        }
    } };
    const closePhysicalDraft = () => {
        if (busy)
            return;
        const entered = Object.entries(disc).some(([key, value]) => !['format', 'kind'].includes(key) && !!value.trim()) || disc.format !== physicalStart.current.format || disc.kind !== physicalStart.current.kind;
        if (entered && !window.confirm('Cancel adding this physical item and clear the entered details?'))
            return;
        setAddDisc(false);
        setPhysicalReview(null);
        setPhysicalChoice(null);
        setPhysicalMetadata(null);
        setSeparatePhysicalConfirmed(false);
        setPhysicalIntakeTarget(null);
        setPhysicalSearchQuery('');
        setPhysicalManual(false);
        setDisc(emptyPhysicalDraft);
        setCameraReference(null);
        setCurrentCameraScanId('');
        cameraArtwork.current = null;
        if (cameraEntryActive) {
            setCameraEntryActive(false);
            setCameraIntakeOpen(true);
        }
    };
    const backToPhysicalDetails = (manual = physicalManual) => { if (!physicalReview || busy)
        return; setDisc(physicalReview.draft); setPhysicalReview(null); setPhysicalChoice(null); setPhysicalManual(manual); setAddDisc(true); };
    const reviewPhysical = async () => {
        if (busy || !disc.title.trim())
            return;
        const draft = { ...disc };
        setBusy(true);
        try {
            const v = await blankBoxClient.action('physical-reference-matches', { title: draft.title.trim(), kind: draft.kind, ...(draft.year ? { year: Number(draft.year) } : {}), compatibleVideoKinds: true });
            const candidates = v.results || [];
            setPhysicalReviewSource(cameraEntryActive && cameraReference?.signature === physicalMetadataSignature(draft) ? 'packs' : 'household');
            setPhysicalSearchQuery(draft.title.slice(0, 200));
            setPhysicalChoice(physicalIntakeTarget ? { item: physicalIntakeTarget, mode: null, versionId: matchingPhysicalVersions(physicalIntakeTarget, draft)[0]?.id || '' } : null);
            setPhysicalMetadata(cameraEntryActive && cameraReference?.signature === physicalMetadataSignature(draft) ? { id: cameraReference.candidate.id, signature: cameraReference.signature, candidate: cameraReference.candidate } : null);
            setSeparatePhysicalConfirmed(false);
            setPackMatchLookup(null);
            setPackMatchRevision(value => value + 1);
            setAddDisc(false);
            setPhysicalReview({ draft, candidates });
        }
        catch (e) {
            toast.error((e as Error).message);
        }
        finally {
            setBusy(false);
        }
    };
    const changePhysicalReviewDraft = (draft: PhysicalDraft) => { if (busy)
        return; setDisc(draft); setPhysicalReview(current => current ? { ...current, draft } : null); setPhysicalMetadata(null); setPhysicalChoice(null); setSeparatePhysicalConfirmed(false); };
    const addManualPhysical = () => { if (!physicalReview || busy)
        return; if (physicalReview.candidates.length && !window.confirm(`Add “${physicalReview.draft.title}” as a separate library title? Possible matches are shown above. To add this item under an existing title, choose that title instead.`))
        return; void createPhysical(physicalReview.draft); };
    const scrollPhysicalReviewToTop = () => requestAnimationFrame(() => physicalReviewDialogRef.current?.scrollTo({ top: 0, behavior: 'smooth' }));
    const searchPhysicalLibrary = async () => { if (!physicalReview || !physicalSearchQuery.trim())
        return; setBusy(true); try {
        const v = await blankBoxClient.action('match-search', { query: physicalSearchQuery.trim().slice(0, 200), sourceScope: 'all' });
        const compatible = (v.results || []).filter(item => item.kind === physicalReview.draft.kind || ['movie', 'tv'].includes(item.kind) && ['movie', 'tv'].includes(physicalReview.draft.kind));
        setPhysicalReview(current => current ? { ...current, candidates: compatible } : null);
    }
    catch (e) {
        toast.error((e as Error).message);
    }
    finally {
        setBusy(false);
        scrollPhysicalReviewToTop();
    } };
    const attachPhysical = async () => { if (!physicalReview || !physicalChoice?.mode)
        return; const { item, mode, versionId, metadataEntityId } = physicalChoice; const newEdition = mode === 'new'; const v = await act('attach-physical', { id: item.id, ...physicalPayload(physicalReview.draft), newEdition, ...(newEdition ? {} : { versionId }), ...(metadataEntityId ? { metadataEntityId } : {}) }, newEdition ? 'New edition and physical copy added to this title' : 'Another physical copy added to this edition'); if (v?.item) {
        const added = await saveScannedArtwork(v.item as MediaItem);
        rememberPhysicalDraft(physicalReview.draft);
        setPhysicalMetadata(null);
        setPhysicalReview(null);
        setPhysicalChoice(null);
        setPhysicalIntakeTarget(null);
        setDisc(emptyPhysicalDraft);
        if (!cameraEntryActive)
            setSelected(added);
        if (cameraEntryActive) {
            setCompletedCameraScanId(currentCameraScanId);
            setCurrentCameraScanId('');
            setCameraEntryActive(false);
            go('import');
            setCameraIntakeOpen(true);
        }
        else
            go('physical');
    } };
    const movePhysicalLocation = async (fromLocation: string, toLocation: string) => { const v = await act('move-physical-location', { fromLocation, toLocation }); if (v) {
        setForm(current => ({ ...current, physicalLocations: [...new Map(current.physicalLocations.filter(value => value.toLocaleLowerCase() !== fromLocation.toLocaleLowerCase()).concat(toLocation).map(value => [value.toLocaleLowerCase(), value])).values()].sort((left, right) => left.localeCompare(right)) }));
        toast.success(`${v.movedCopies || 0} ${v.movedCopies === 1 ? 'copy' : 'copies'} moved to ${toLocation}`);
    } };
    const physicalFormatOptions = useMemo(() => {
        if (state.facets) {
            const counts = new Map<string, {
                id: string;
                label: string;
                count: number;
            }>();
            for (const row of state.facets.physicalFacets) {
                if (filter !== 'all' && row.kind !== filter)
                    continue;
                const current = counts.get(row.id);
                counts.set(row.id, { id: row.id, label: row.label, count: (current?.count || 0) + row.count });
            }
            return [...counts.values()];
        }
        const counts = new Map<string, {
            label: string;
            count: number;
        }>();
        for (const item of state.items) {
            if (filter !== 'all' && item.kind !== filter)
                continue;
            for (const source of item.sources) {
                if (source.type !== 'physical')
                    continue;
                const facet = physicalFacet(source, item.kind), entry = counts.get(facet.id);
                counts.set(facet.id, { label: facet.label, count: (entry?.count || 0) + 1 });
            }
        }
        return [...counts].map(([id, entry]) => ({ id, ...entry })).sort((a, b) => a.label.localeCompare(b.label));
    }, [state.items, state.facets, filter]);
    const searchQuery = useDeferredValue(query);
    const normalizedQuery = searchQuery.toLowerCase();
    const localFiltered = useMemo(() => state.items.filter(i => { if (genreFilter && !itemGenres(i).some(value => value.toLocaleLowerCase() === genreFilter.toLocaleLowerCase()))
        return false; if (activityFilter && (i.activity?.status || 'not-started') !== activityFilter)
        return false; if (searchQuery && !`${i.title} ${i.genre || ''} ${(i.customGenres || []).join(' ')} ${i.year || ''} ${i.description || ''} ${i.sources.map(s => `${s.label} ${s.edition || ''} ${s.volume || ''} ${s.issue || ''} ${s.region || ''} ${s.catalogNumber || ''} ${s.mime || ''} ${s.location || ''} ${s.path || ''} ${s.barcode || ''} ${s.creator || ''} ${s.publisher || ''} ${s.platform || ''}`).join(' ')}`.toLowerCase().includes(normalizedQuery))
        return false; if (favorites && !i.favorite)
        return false; if (!searchQuery && view === 'physical' && !i.sources.some(s => s.type === 'physical' && (physicalFormatFilter === 'all' || physicalFacet(s, i.kind).id === physicalFormatFilter)))
        return false; if (!searchQuery && view === 'movie' && i.kind !== 'movie')
        return false; if (!searchQuery && view === 'tv' && i.kind !== 'tv')
        return false; if (!searchQuery && view === 'music' && i.kind !== 'music')
        return false; if (!searchQuery && view === 'photo' && !['photo', 'home-video'].includes(i.kind))
        return false; if (!searchQuery && view === 'book' && i.kind !== 'book')
        return false; if (!searchQuery && view === 'comic' && i.kind !== 'comic')
        return false; if (!searchQuery && view === 'game' && i.kind !== 'game')
        return false; return filter === 'all' || i.kind === filter; }).sort((a, b) => sort === 'az' ? a.title.localeCompare(b.title) : sort === 'year' ? mediaReleaseAt(b).localeCompare(mediaReleaseAt(a)) : sort === 'edition' ? a.sources.map(s => s.edition || '').sort().join(' ').localeCompare(b.sources.map(s => s.edition || '').sort().join(' ')) || a.title.localeCompare(b.title) : mediaAddedAt(b).localeCompare(mediaAddedAt(a))), [state.items, searchQuery, normalizedQuery, view, filter, sort, favorites, physicalFormatFilter, genreFilter, activityFilter]);
    const [serverPage, setServerPage] = useState<{
        key: string;
        value: LibraryPage;
    } | null>(null);
    const [pageLoading, setPageLoading] = useState(false), [pageError, setPageError] = useState('');
    const libraryEpoch = 0;
    const libraryPageKey = JSON.stringify([view, searchQuery, filter, sort, favorites, physicalFormatFilter, genreFilter, activityFilter, physicalView]);
    const libraryPageIndex = libraryPage.key === libraryPageKey ? libraryPage.page : 0;
    const pageRequestKey = `${libraryPageKey}:${libraryPageIndex}:${libraryEpoch}`;
    const browsing = navItems.some(item => item.id === view && item.id !== 'home' && item.id !== 'collections') || !!query;
    useEffect(() => {
        if (!state.pagedLibrary || !browsing)
            return;
        const controller = new AbortController();
        const timer = setTimeout(() => {
            setPageLoading(true);
            setPageError('');
            blankBoxClient.libraryPage({ q: searchQuery, view, kind: filter === 'all' ? '' : filter, sort, favorites, facet: physicalFormatFilter, genre: genreFilter, status: activityFilter, shelves: physicalView === 'shelves', offset: libraryPageIndex * 60, limit: 60 }, controller.signal).then(value => {
                if (controller.signal.aborted)
                    return;
                if (libraryPageIndex > 0 && libraryPageIndex * 60 >= value.total) {
                    setLibraryPage({ key: libraryPageKey, page: Math.max(0, Math.ceil(value.total / 60) - 1) });
                    return;
                }
                setServerPage({ key: pageRequestKey, value });
            }).catch(cause => { if (!controller.signal.aborted)
                setPageError((cause as Error).message); }).finally(() => { if (!controller.signal.aborted)
                setPageLoading(false); });
        }, query ? 180 : 0);
        return () => { controller.abort(); clearTimeout(timer); };
    }, [state.pagedLibrary, state.items, browsing, view, searchQuery, filter, sort, favorites, physicalFormatFilter, genreFilter, activityFilter, physicalView, libraryPageIndex, libraryPageKey, pageRequestKey, query]);
    const currentServerPage = serverPage?.key === pageRequestKey ? serverPage.value : null;
    const filtered = useMemo(() => state.pagedLibrary ? (currentServerPage?.items || []) : localFiltered, [state.pagedLibrary, currentServerPage, localFiltered]);
    const physicalShelfGroups = useMemo(() => {
        if (view !== 'physical' || physicalView !== 'shelves' || searchQuery)
            return [];
        if (state.pagedLibrary) {
            const lookup = new Map(filtered.map(item => [item.id, item]));
            return (currentServerPage?.shelfGroups || []).map(group => ({ location: group.location, copies: group.copies, items: group.entries.flatMap(entry => lookup.has(entry.itemId) ? [{ item: lookup.get(entry.itemId)!, copies: entry.copies }] : []) }));
        }
        const grouped = new Map<string, Map<string, {
            item: MediaItem;
            copies: number;
        }>>();
        for (const item of filtered)
            for (const source of item.sources) {
                if (source.type !== 'physical' || physicalFormatFilter !== 'all' && physicalFacet(source, item.kind).id !== physicalFormatFilter)
                    continue;
                const location = source.location?.trim() || 'Location not set', items = grouped.get(location) || new Map<string, {
                    item: MediaItem;
                    copies: number;
                }>(), existing = items.get(item.id);
                items.set(item.id, { item, copies: (existing?.copies || 0) + 1 });
                grouped.set(location, items);
            }
        return [...grouped].sort(([a], [b]) => a.localeCompare(b)).map(([location, items]) => ({ location, items: [...items.values()], copies: [...items.values()].reduce((sum, row) => sum + row.copies, 0) }));
    }, [filtered, physicalFormatFilter, physicalView, view, searchQuery, state.pagedLibrary, currentServerPage]);
    const shelfBrowsing = view === 'physical' && !query && physicalView === 'shelves';
    const libraryEntries = state.pagedLibrary ? (currentServerPage?.total || 0) : shelfBrowsing ? physicalShelfGroups.reduce((sum, group) => sum + group.items.length, 0) : filtered.length;
    const pageItems = state.pagedLibrary ? filtered : filtered.slice(libraryPageIndex * 60, libraryPageIndex * 60 + 60);
    const selectedPageItems = pageItems.filter(item => librarySelection.has(item.id));
    const shelfPageGroups = useMemo(() => {
        if (state.pagedLibrary)
            return physicalShelfGroups;
        let offset = 0;
        const page = [];
        for (const group of physicalShelfGroups) {
            const start = Math.max(0, libraryPageIndex * 60 - offset), end = Math.min(group.items.length, (libraryPageIndex + 1) * 60 - offset);
            offset += group.items.length;
            if (end > start)
                page.push({ ...group, items: group.items.slice(start, end) });
        }
        return page;
    }, [physicalShelfGroups, libraryPageIndex, state.pagedLibrary]);
    const changeLibraryPage = (page: number) => { setLibrarySelectionMode(false); setLibrarySelection(new Set()); setLibraryPage({ key: libraryPageKey, page }); document.querySelector('.main-content')?.scrollTo({ top: 0, behavior: 'instant' }); };
    const openItem = async (item: MediaItem) => { try {
        setSelected(item.browseSummary ? await blankBoxClient.item(item.id) : item);
        setLibrarySelectionMode(false);
        setLibrarySelection(new Set());
    }
    catch (cause) {
        toast.error((cause as Error).message);
    } };
    const bulkRenameTitles = async () => {
        if (!selectedPageItems.length)
            return;
        const find = window.prompt('Find this exact text in selected Blank Box catalog titles:');
        if (!find)
            return;
        const replacement = window.prompt('Replace it with (may be empty):');
        if (replacement === null)
            return;
        const changes = selectedPageItems.map(item => ({ item, title: item.title.replaceAll(find, replacement).trim() })).filter(row => row.title !== row.item.title);
        if (!changes.length) {
            toast.info('No selected titles contain that text.');
            return;
        }
        if (changes.some(row => !row.title || row.title.length > 250)) {
            toast.error('The proposed titles must contain 1–250 characters.');
            return;
        }
        const preview = changes.slice(0, 12).map(row => `${row.item.title} → ${row.title}`).join('\n');
        if (!window.confirm(`Rename ${changes.length} Blank Box catalog titles?\n\n${preview}${changes.length > 12 ? '\n…' : ''}\n\nFiles and folders on your devices will not change.`))
            return;
        setBusy(true);
        let done = 0;
        try {
            for (const row of changes) {
                await blankBoxClient.action('update', { id: row.item.id, title: row.title });
                done++;
            }
            await reload();
            setLibrarySelection(new Set());
            toast.success(`${done} catalog titles renamed.`);
        }
        catch (cause) {
            await reload();
            toast.error(`Stopped after ${done} titles: ${(cause as Error).message}`);
        }
        finally {
            setBusy(false);
        }
    };
    const bulkConsolidate = async () => {
        if (selectedPageItems.length !== 2)
            return;
        const [first, second] = selectedPageItems;
        if (first.kind !== second.kind) {
            toast.error('Select two titles of the same media type.');
            return;
        }
        const keep = window.prompt(`Choose the stable Media Item ID to keep by typing 1 or 2:\n1. ${first.title} (${first.id})\n2. ${second.title} (${second.id})`);
        if (keep !== '1' && keep !== '2')
            return;
        const target = keep === '1' ? first : second, incoming = keep === '1' ? second : first;
        if (!window.confirm(`Consolidate “${incoming.title}” into “${target.title}”?\n\nKeep Media Item ID ${target.id}. Blank Box will keep existing title details, attach distinct sources and preserve the other ID as an alias. Originals stay on their drives.`))
            return;
        setBusy(true);
        try {
            const result = await blankBoxClient.action('consolidate-selected', { targetId: target.id, incomingId: incoming.id, targetTitle: target.title, incomingTitle: incoming.title, confirm: true });
            await reload();
            setLibrarySelection(new Set());
            if (result.item)
                setSelected(result.item);
            toast.success('Media Items consolidated.');
        }
        catch (cause) {
            toast.error((cause as Error).message);
        }
        finally {
            setBusy(false);
        }
    };
    const searchLibraryAttach = async () => {
        if (!libraryAttachQuery.trim())
            return;
        setBusy(true);
        setLibraryAttachError('');
        setLibraryAttachTarget(null);
        try {
            const result = await blankBoxClient.action('match-search', { query: libraryAttachQuery.trim().slice(0, 200), sourceScope: 'all' });
            setLibraryAttachResults((result.results || []).filter((item: MediaItem) => item.kind === libraryAttachRows[0]?.kind));
        }
        catch (cause) {
            setLibraryAttachError((cause as Error).message);
        }
        finally {
            setBusy(false);
        }
    };
    const attachLibrarySelection = async () => {
        if (!libraryAttachTarget)
            return;
        const incoming = libraryAttachRows.filter(item => item.id !== libraryAttachTarget.id);
        if (!incoming.length)
            return;
        if (!window.confirm(`Consolidate ${incoming.length} selected split title${incoming.length === 1 ? '' : 's'} into “${libraryAttachTarget.title}” (${libraryAttachTarget.id})? The destination keeps its Media Item ID and catalog details. Source IDs and original files stay in place. Records with owner edits or extra editions require individual review.`))
            return;
        setBusy(true);
        setLibraryAttachError('');
        try {
            await blankBoxClient.action('consolidate-selected-many', { targetId: libraryAttachTarget.id, targetTitle: libraryAttachTarget.title, incoming: incoming.map(item => ({ id: item.id, title: item.title })), confirmedCount: incoming.length, confirm: true });
            setLibraryAttachRows([]);
            setLibrarySelection(new Set());
            await reload();
            toast.success(`${incoming.length} split title${incoming.length === 1 ? '' : 's'} attached to ${libraryAttachTarget.title}.`);
        }
        catch (cause) {
            setLibraryAttachError((cause as Error).message);
            await reload();
        }
        finally {
            setBusy(false);
        }
    };
    const bulkRemoveRecords = async () => {
        if (!selectedPageItems.length)
            return;
        setBusy(true);
        let done = 0;
        try {
            const full = await Promise.all(selectedPageItems.map(item => blankBoxClient.item(item.id)));
            if (full.some(item => item.sources.some(source => source.type === 'local'))) {
                toast.error('Selection includes managed files. Open those items individually to review removal.');
                return;
            }
            const choice = window.prompt(`Remove ${full.length} selected Blank Box catalog records? Linked originals, source drives and connected services stay unchanged. Physical ownership records in Blank Box will be removed. Type REMOVE to confirm.`);
            if (choice?.trim() !== 'REMOVE')
                return;
            for (const item of full) {
                await blankBoxClient.action('delete', { id: item.id, confirmId: item.id });
                done++;
            }
            await reload();
            setLibrarySelection(new Set());
            toast.success(`${done} catalog records removed.`);
        }
        catch (cause) {
            await reload();
            toast.error(`Stopped after ${done} records: ${(cause as Error).message}`);
        }
        finally {
            setBusy(false);
        }
    };
    const favorite = async (item: MediaItem) => { const v = await act('update', { id: item.id, favorite: !item.favorite }); if (v) {
        if (selected?.id === item.id)
            setSelected(v.item || { ...selected, favorite: !item.favorite });
        toast.success(item.favorite ? 'Removed from favorites' : 'Added to favorites');
    } };
    const openMatch = (target: MediaItem | null, initial = query) => { setMatchTarget(target); if (initial !== query && !target)
        setQuery(initial); setMatchSeed(value => value + 1); setMatchOpen(true); };
    const searchMatches = async (value: string, sourceScope: 'household' | 'connected') => { try {
        const result = await blankBoxClient.action('match-search', { query: value, sourceScope, ...(matchTarget ? { exclude: matchTarget.id } : {}) });
        return result.results || [];
    }
    catch (e) {
        toast.error((e as Error).message);
        return [];
    } };
    const applyMatch = async (match: MediaItem) => { if (!matchTarget)
        return false; const sources = matchTarget.sources; const keepMatchId = sources.some(source => source.type === 'digital') && sources.every(source => source.type === 'digital' || source.type === 'catalog'); const result = await act('match', { id: matchTarget.id, matchId: match.id, ...(keepMatchId ? { keepMatchId: true } : {}) }, 'Titles matched'); if (result?.item) {
        setCatalogEditor(result.item);
        setEditorRevision(revision => revision + 1);
        setSelected(null);
        return true;
    } return false; };
    const saveMetadata = async (item: MediaItem, edit: MediaEdit) => { const result = await act('update', { id: item.id, title: edit.title.trim(), kind: edit.kind, catalogDetails: edit.catalogDetails, releaseDate: edit.releaseDate || null, duration: edit.duration ? Number(edit.duration) * 60 : null, year: edit.year ? Number(edit.year) : null, genre: edit.genre.trim(), customGenres: edit.customGenres, description: edit.description.trim(), physicalSources: edit.physicalSources, digitalSources: edit.digitalSources, ...(edit.kind === 'tv' ? { tvSeasons: edit.tvSeasons.map(({ versionId, season }) => ({ versionId, season })) } : {}), ...(edit.kind === 'music' ? { artist: edit.artist.trim(), ...(item.discImport ? { trackTitles: edit.trackTitles } : {}) } : {}) }, 'Details saved'); if (!result)
        return false; const updated = result.item as MediaItem; setCatalogEditor(null); setEditorOrigin(null); setIntakeChoice(null); setSelected(updated); return true; };
    const removeSelected = async () => { if (!selected)
        return false; const managed = selected.sources.some(source => source.type === 'local'), connected = selected.sources.some(source => ['jellyfin', 'plex'].includes(source.type)); const result = await act('delete', { id: selected.id, confirmId: selected.id }, managed ? 'Managed copy removed; original source unchanged' : connected ? 'Hidden from Blank Box; connected service unchanged' : 'Removed from Blank Box'); if (result) {
        return true;
    } return false; };
    const playUrl = (item: MediaItem) => preferredPlaybackSource(item)?.url || '';
    const playLabel = (item: MediaItem) => sourceActionLabel(item, preferredPlaybackSource(item));
    const openReader = (item: MediaItem, source: MediaSource, url: string) => { const format = readerFormat(source); if (!format || !url)
        return false; setSelected(null); setReading({ item, source, url, format }); return true; };
    const startPlay = (item: MediaItem) => { const source = preferredPlaybackSource(item); if (source && openReader(item, source, source.url || ''))
        return; if (isConnectedPlaybackSource(source)) {
        const link = safeUrl(source.url);
        if (link) {
            window.open(link, '_blank', 'noopener,noreferrer');
            return;
        }
    } if (source?.type === 'demo' && !/\.mp4($|\?)/.test(source.url || '')) {
        const link = safeUrl(source.url);
        if (link) {
            window.open(link, '_blank', 'noopener,noreferrer');
            return;
        }
    } if (source?.url || item.kind === 'photo' && item.poster) {
        setSelected(null);
        setMusicStartSourceId(source?.id);
        setPlaying(item.kind === 'music' ? item : source ? { ...item, mime: source.mime || item.mime, bytes: source.bytes || item.bytes, sources: [source] } : item);
    }
    else
        setSelected(item); };
    const startPlaySource = (item: MediaItem, source: MediaSource) => { if (openReader(item, source, source.url || ''))
        return; if (isConnectedPlaybackSource(source) && safeUrl(source.url)) {
        window.open(safeUrl(source.url), '_blank', 'noopener,noreferrer');
        return;
    } if ((source.type === 'local' || source.type === 'digital') && source.url) {
        setSelected(null);
        setMusicStartSourceId(source.id);
        setPlaying(item.kind === 'music' ? item : { ...item, mime: source.mime || item.mime, bytes: source.bytes || item.bytes, sources: [source] });
        return;
    } const link = safeUrl(source.url); if (link)
        window.open(link, '_blank', 'noopener,noreferrer'); };
    const prepareLocalPlayback = async (item: MediaItem, source: MediaSource | undefined, start: () => void, acknowledged = false) => {
        if (source && ['local', 'digital'].includes(source.type)) {
            if (!acknowledged && !(state.settings.mediaRightsAttestation?.accepted && state.settings.mediaRightsAttestation.termsVersion === MEDIA_RIGHTS_TERMS_VERSION)) {
                pendingPlayback.current = () => void prepareLocalPlayback(item, source, start, true);
                setRightsAccepted(false);
                setRightsOpen(true);
                return;
            }
            try {
                const response = await fetch(source.url!, { method: 'HEAD', credentials: 'same-origin' });
                if (!response.ok) {
                    toast.error(response.status === 401 ? 'Sign in again to play this file.' : response.status === 409 ? 'This file or drive is unavailable or changed. Check storage, or index and review the drive again.' : 'This local file is no longer available. Check its source in Import.');
                    return;
                }
            }
            catch {
                toast.error('Blank Box could not reach this file. Check the connection and drive.');
                return;
            }
        }
        setPlaybackAlternatives(item.sources);
        start();
    };
    const play = (item: MediaItem) => { if (item.browseSummary) {
        const source = preferredPlaybackSource(item);
        if (isConnectedPlaybackSource(source) && safeUrl(source?.url)) {
            window.open(safeUrl(source?.url), '_blank', 'noopener,noreferrer');
            return;
        }
        void blankBoxClient.item(item.id).then(full => prepareLocalPlayback(full, preferredPlaybackSource(full), () => startPlay(full))).catch(cause => toast.error((cause as Error).message));
        return;
    } void prepareLocalPlayback(item, preferredPlaybackSource(item), () => startPlay(item)); };
    const playSource = (item: MediaItem, source: MediaSource) => void prepareLocalPlayback(item, source, () => startPlaySource(item, source));
    const acceptMediaRights = async () => { const result = await act('media-rights-accept', { confirm: true, termsVersion: MEDIA_RIGHTS_TERMS_VERSION }); if (result) {
        setRightsOpen(false);
        const start = pendingPlayback.current;
        pendingPlayback.current = null;
        start?.();
    } };
    const removeSource = async (item: MediaItem, source: MediaSource) => { if (!source.id)
        return; const warning = source.type === 'local' ? `Remove this Blank Box-managed copy from ${item.title}? The original source file will not be changed.` : source.type === 'physical' ? `Take this ${source.label} copy out of your Physical Media? The physical media itself is not changed.` : ['jellyfin', 'plex'].includes(source.type) ? `Remove this ${source.label} source from ${item.title}? ${source.label} and its files will not be changed.` : `Remove this source from ${item.title}? The source itself will not be changed.`; if (!window.confirm(warning))
        return; const v = await act('remove-source', { id: item.id, sourceId: source.id, confirmSourceId: source.id }, source.type === 'local' ? 'Managed copy removed; original unchanged' : source.type === 'physical' ? 'Removed from Physical Media; physical media unchanged' : 'Source removed from this title'); if (v) {
        if (v.item)
            setSelected(v.item);
        else
            setSelected(null);
    } };
    const refreshItem = async (item: MediaItem) => { const v = await act('refresh-item', { id: item.id }, 'Connected metadata refreshed'); if (v?.item)
        setSelected(v.item); };
    const chooseEditorMetadata = async (item: MediaItem, sourceId: string) => { const v = await act('metadata-choice', { id: item.id, sourceId, confirm: true, replaceEdits: true }, sourceId === 'blankbox' ? 'Using Blank Box details' : 'Metadata source selected'); if (v?.item) {
        setCatalogEditor(v.item);
        setEditorRevision(revision => revision + 1);
    } };
    const refreshEditorMetadata = async (item: MediaItem) => { const v = await act('refresh-item', { id: item.id }, 'Connected metadata refreshed'); if (v?.item) {
        setCatalogEditor(v.item);
        setEditorRevision(revision => revision + 1);
    } };
    const uploadEditorArtwork = async (item: MediaItem, image: Blob) => { const updated = await blankBoxClient.uploadArtwork(item.id, image); setCatalogEditor(updated); setEditorRevision(revision => revision + 1); await reload(); toast.success('Local cover saved.'); };
    const removeEditorArtwork = async (item: MediaItem) => { const result = await act('artwork-remove', { id: item.id, confirm: true }, 'Local cover removed'); if (result?.item) {
        setCatalogEditor(result.item);
        setEditorRevision(revision => revision + 1);
    } };
    const resolveReview = async (reviewId: string, policy: ReviewPolicy, targetId?: string, fromDialog = false) => { const v = await act('resolve-review', { reviewId, policy, ...(targetId ? { targetId } : {}) }, policy === 'new-version' ? 'Edition added' : 'Match review saved'); if (v) {
        if (fromDialog && state.reviewCount <= 1)
            setSourceReviewOpen(false);
        else if (!fromDialog)
            go('import');
    } };
    const resolveAllReviews = async (policy: Exclude<ReviewPolicy, 'separate'>, fromDialog = false) => { if (!window.confirm(`Apply this choice to all ${state.reviewCount} proposed matches? You can still edit the consolidated items later.`))
        return; const v = await act('resolve-all-reviews', { policy }, 'Match review completed'); if (v && fromDialog)
        setSourceReviewOpen(false); };
    const fileImport = async (_files: FileList | null) => { toast.info("Use a mounted source to import files into Blank Box."); };
    const scan = async (reviewDiscovered = false) => { const v = await act(reviewDiscovered ? 'auto-copy-scan' : 'scan', { sourceId }); if (v?.id) {
        setScanId(v.id);
        scanRef.current = v.id;
        setScanKinds(['photo', 'home-video', 'file']);
        setScanRows([]);
        setScanSelected(new Set());
        setScanPage(0);
    } };
    const commit = async () => { if (!selectedScanRows.length)
        return; const total = selectedScanRows.reduce((sum, file) => sum + file.bytes, 0); if (!window.confirm(`Copy ${selectedScanRows.length} file${selectedScanRows.length === 1 ? '' : 's'} (${bytes(total)}) into Blank Box-managed storage? Originals stay in place. For movies, TV, and music you can instead use Index existing files to link without copying.`))
        return; const v = await act('import', { scanId, selectedIds: selectedScanRows.map(file => file.id), policy: importPolicy, confirmCopy: true }); if (v) {
        setScanRows([]);
        setScanSelected(new Set());
        setScanId('');
        toast.success(importPolicy === 'review' ? 'Copy started. Possible matches will appear in review.' : 'Copy and consolidation started.');
    } };
    const changeSidebar = (open: boolean) => { setSidebarOpen(open); if (!activeTvMode) {
        normalSidebarOpenRef.current = open;
        savePreference('blank-box-sidebar', open ? '1' : '0');
    } };
    const toggleTvMode = () => { if (isMobile)
        return; const next = !tvMode; setTvMode(next); setSidebarOpen(next ? false : normalSidebarOpenRef.current); savePreference('blank-box-tv', next ? '1' : '0'); };
    const card = (item: MediaItem, wide = false) => { const badge = physicalBadge(item); return <article className={`media-card ${wide ? 'wide' : ''}`} key={item.id}>{librarySelectionMode && libraryView && <label className="media-card-select"><Checkbox checked={librarySelection.has(item.id)} onCheckedChange={checked => setLibrarySelection(previous => { const next = new Set(previous); if (checked)
        next.add(item.id);
    else
        next.delete(item.id); return next; })}/><span className="sr-only">Select {item.title}</span></label>}<button data-tv onClick={() => void openItem(item)} className="art-button" aria-label={`Open ${item.title}`}><div className={`artwork kind-${item.kind}`}>{item.poster ? <img src={item.poster} alt="" loading="lazy"/> : <span className="no-art">{(() => { const Icon = icons[item.kind]; return <Icon size={38} strokeWidth={1}/>; })()}<strong>{item.title}</strong></span>}<span className="art-shade"/>{badge && <span className="art-tag" title={`Physical format: ${badge.title}`}><badge.Icon size={12}/>{badge.label}</span>}{item.favorite && <span className="art-heart"><Heart size={14} fill="currentColor"/></span>}{item.activity?.status === 'completed' && <span className="art-activity" title={activityLabel(item.kind, 'completed')}><Check size={14}/>{activityLabel(item.kind, 'completed')}</span>}<span className="card-play"><MediaActionIcon item={item} size={23}/></span>{!!item.progress && <Progress className="watch-progress" value={item.progress * 100}/>}</div></button><div className="card-meta"><button data-tv onClick={() => void openItem(item)}>{item.title}</button><span>{item.year || kindNames[item.kind]}<i>·</i>{collectionLabel(item)}</span></div></article>; };
    const memoryPhotos = useMemo(() => state.items.filter(item => item.kind === 'photo' && !item.sample && (item.poster || item.backdrop || item.sources.some(source => source.type === 'local' && source.url))), [state.items]);
    const memoryPhoto = !memoryPhotos.length ? null : memoryPhotos[Math.floor(photoSeed * memoryPhotos.length)];
    const memoryPhotoUrl = memoryPhoto?.poster || memoryPhoto?.backdrop || memoryPhoto?.sources.find(source => source.type === 'local' && source.url)?.url;
    const heroPool = useMemo(() => featuredCoverPool(state.items, state.settings, (a, b) => { switch (state.settings.homeHeroSort) {
        case 'released': return mediaReleaseAt(b).localeCompare(mediaReleaseAt(a)) || a.title.localeCompare(b.title);
        case 'az': return a.title.localeCompare(b.title);
        case 'random': return stableCoverOrder(a.id) - stableCoverOrder(b.id);
        default: return mediaAddedAt(b).localeCompare(mediaAddedAt(a)) || a.title.localeCompare(b.title);
    } }, memoryPhoto?.id), [state.items, state.settings, memoryPhoto?.id]);
    const hero = heroPool.length ? heroPool[heroIndex % heroPool.length] : null;
    const activeHeroMode: HeroMode = hero?.kind === 'music' ? 'music' : hero?.kind === 'book' ? 'book' : hero?.kind === 'comic' ? 'comics' : hero?.kind === 'game' ? 'games' : hero?.kind === 'photo' || hero?.kind === 'home-video' ? 'photos' : 'watch';
    const featuredEnabled = Object.values(featuredMediaKeys).some(key => state.settings[key]);
    const heroPlayable = !!hero && activeHeroMode !== 'games' && (!!playUrl(hero) || hero.kind === 'photo' && !!hero.poster);
    const heroActionLabel = !heroPlayable ? 'View item' : activeHeroMode === 'music' ? 'Listen now' : activeHeroMode === 'book' ? 'Read book' : activeHeroMode === 'comics' ? 'Read comic' : activeHeroMode === 'photos' ? (hero?.kind === 'home-video' ? 'Watch video' : 'View photo') : hero?.sample ? 'Watch trailer' : 'Watch now';
    useEffect(() => { if (view !== 'home' || heroPool.length < 2 || window.matchMedia('(prefers-reduced-motion: reduce)').matches)
        return; const timer = window.setInterval(() => setHeroIndex(index => (index + 1) % heroPool.length), 8000); return () => window.clearInterval(timer); }, [view, heroPool.length]);
    const customizeHome = () => { setSettingsTab('general'); go('settings'); window.setTimeout(() => document.querySelector('.home-customization-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100); };
    const activeJobs = state.jobs.filter(j => ['queued', 'running'].includes(j.status));
    const libraryView = navItems.some(item => item.id === view && item.id !== 'home' && item.id !== 'collections') || !!query;
    const collectionSummary = useMemo(() => state.summary || summarizeCollection(state.items), [state.summary, state.items]);
    const recentlyAdded = useMemo(() => [...state.items].sort((left, right) => mediaAddedAt(right).localeCompare(mediaAddedAt(left))).slice(0, 5), [state.items]);
    const recentlyReleased = useMemo(() => state.items.filter(item => item.releaseDate && hasDigitalOrConnectedSource(item)).sort((left, right) => mediaReleaseAt(right).localeCompare(mediaReleaseAt(left))).slice(0, 5), [state.items]);
    const homeRows = state.settings.homeRows || defaultHomeRows;
    const homeCategoryRows = useMemo(() => { const kinds: Partial<Record<HomeRow, Kind[]>> = { movies: ['movie'], tv: ['tv'], music: ['music'], photos: ['photo', 'home-video'], books: ['book'], comics: ['comic'], games: ['game'] }; return Object.fromEntries(Object.entries(kinds).map(([id, allowed]) => [id, state.items.filter(item => allowed?.includes(item.kind)).sort((a, b) => mediaAddedAt(b).localeCompare(mediaAddedAt(a))).slice(0, 5)])) as Partial<Record<HomeRow, MediaItem[]>>; }, [state.items]);
    const hasLibrarySource = state.sources.length > 0 || state.items.some(item => !item.sample && item.sources.length > 0) || !!state.settings.jellyfinUrl || !!state.settings.plexUrl;
    const services = state.settings.streamingServices.length ? allServices.filter(service => state.settings.streamingServices.includes(service.id)) : allServices;
    const field = (label: string, key: keyof Settings, placeholder: string) => <label className="field"><span>{label}</span><input value={String(form[key])} placeholder={placeholder} onChange={e => setForm({ ...form, [key]: e.target.value })}/></label>;
    const cancelSetup = () => { setForm(state.settings); setOnboarding(false); };
    const completeSetup = (destination: 'home' | 'import' | 'shelf' | 'settings' | 'services', settings: Settings) => { if (destination === 'shelf') {
        go('physical');
        openPhysicalFor(settings.physicalFormats);
        return;
    } go(destination); };
    const setupContent = <OnboardingWizard settings={form} mode={state.mode} sources={state.sources} backup={state.backup} busy={busy} editing={state.settings.setupDone} onPersist={persistSettings} onCancel={cancelSetup} onComplete={completeSetup}/>;
    const localMode = true;
    const collectingReady = state.collectionPlanningAvailable === true;
    const physicalBrowsing = view === 'physical' && !query;
    const visiblePhysicalCandidates = physicalReview && ['household', 'connected'].includes(physicalReviewSource) ? physicalReview.candidates.filter(item => physicalMatchSource(item, physicalReviewSource as 'household' | 'connected') && (item.kind === physicalReview.draft.kind || ['movie', 'tv'].includes(item.kind) && ['movie', 'tv'].includes(physicalReview.draft.kind))) : [];
    const selectedPackCandidate = physicalReview && physicalMetadata?.signature === physicalMetadataSignature(physicalReview.draft) ? physicalMetadata.candidate : null;
    const packMatchKey = JSON.stringify([selectedPackCandidate?.id, selectedPackCandidate?.title, selectedPackCandidate?.kind, selectedPackCandidate?.year, packMatchRevision]);
    useEffect(() => { if (!state.pagedLibrary || !selectedPackCandidate)
        return; let active = true; void blankBoxClient.action('physical-reference-matches', { title: selectedPackCandidate.title, kind: selectedPackCandidate.kind, year: selectedPackCandidate.year, referenceId: selectedPackCandidate.id }).then(result => { if (active)
        setPackMatchLookup({ key: packMatchKey, matches: result.results || [] }); }).catch(cause => { if (active)
        setPackMatchLookup({ key: packMatchKey, matches: [], error: (cause as Error).message }); }); return () => { active = false; }; }, [state.pagedLibrary, selectedPackCandidate, packMatchKey]);
    const packMatchPending = !!selectedPackCandidate && !!state.pagedLibrary && packMatchLookup?.key !== packMatchKey;
    const packMatchError = packMatchLookup?.key === packMatchKey ? packMatchLookup.error : undefined;
    const packHouseholdMatches = selectedPackCandidate ? (state.pagedLibrary ? (packMatchLookup?.key === packMatchKey ? [...packMatchLookup.matches] : []) : state.items.filter(item => item.kind === selectedPackCandidate.kind && (selectedPackCandidate.householdItemIds?.includes(item.id) || physicalTitleKey(item.title) === physicalTitleKey(selectedPackCandidate.title) && (!item.year || !selectedPackCandidate.year || item.year === selectedPackCandidate.year)))).sort((left, right) => Number(!!selectedPackCandidate.householdItemIds?.includes(right.id)) - Number(!!selectedPackCandidate.householdItemIds?.includes(left.id))).slice(0, 25) : [];
    const compatiblePhysicalVersions = physicalChoice && physicalReview ? matchingPhysicalVersions(physicalChoice.item, physicalReview.draft) : [];
    if (locked)
        return <>{<LocalSignIn open busy={busy} onBusyChange={setBusy} onAuthenticated={async () => { const s = await reload(); if (s) {
            setForm(s.settings);
            if (!s.settings.setupDone)
                setOnboarding(true);
        } }}/>}<Toaster position="bottom-right" richColors theme="dark"/></>;
    if (!loaded)
        return <><StartupScreen error={error} onRetry={() => void reload()}/><Toaster position="bottom-right" richColors theme="dark"/></>;
    return <SidebarProvider open={sidebarOpen} onOpenChange={changeSidebar} style={{ '--sidebar-width': '238px', '--sidebar-width-icon': '70px' } as CSSProperties}><div className={`blank-box-app ${activeTvMode ? 'tv-mode' : ''}`}><Navigation view={view} go={go} state={state}/><div className="main-shell"><header className="topbar" aria-label="Library toolbar"><div className="top-left"><button data-tv type="button" className="navigation-back" onClick={goBack} disabled={historyCount < 2} aria-label="Go back" title="Go back"><ArrowLeft size={18}/></button><div className="topbar-location"><span className="topbar-eyebrow">{state.settings.name}</span><strong className="topbar-title">{navigationLabels[view]}</strong></div></div><div className="top-actions"><label className="search topbar-search"><Search size={18}/><input ref={searchRef} aria-label="Search your library" placeholder="Search your library" value={query} onChange={e => setQuery(e.target.value)}/>{query ? <button type="button" aria-label="Clear search" onClick={() => setQuery('')}><X size={16}/></button> : <kbd>/</kbd>}</label><button data-tv type="button" className="add-button" aria-label="Add media" onClick={() => go('import')}><Plus size={17}/><span>Add media</span></button><NavigationToggle mobileOnly/></div></header>
 <main className="main-content">{state.browseIndexStatus === 'building' && <p className="note" role="status">Preparing library browsing in the background. Your catalog and media remain intact.</p>}{error && <div className="error-banner" role="alert"><Info size={18}/>{error}<button onClick={() => reload()}>Try again</button></div>}{!loaded && !locked && !error ? <div className="loading"><Loader2 className="animate-spin"/>Opening your library…</div> : <>
 {!query && view === 'collections' && <CollectionBrowser state={state} renderItem={card} onChange={async () => { await reload(); }} onPlan={() => go('collecting')}/>}
 {!libraryView && view === 'home' && state.browseIndexStatus !== 'building' && <><div className="page-heading home-heading"><h1>Welcome{state.profile?.username ? `, ${state.profile.username}` : ''}</h1><button data-tv className="text-button home-customize" aria-label="Customize Home" title="Customize Home" onClick={customizeHome}><Settings2 size={16}/><span>Customize Home</span></button></div>

 {featuredEnabled && (hero ? <section key={`${activeHeroMode}-${hero.id}`} className={`feature feature-kind-${activeHeroMode}`} aria-label={`Featured ${activeHeroMode === 'watch' ? 'movie or show' : activeHeroMode}`}>
  {(hero.backdrop || hero.poster || hero.kind === 'photo' && memoryPhotoUrl) && <img className="feature-image" src={hero.backdrop || hero.poster || (hero.kind === 'photo' ? memoryPhotoUrl : undefined)} alt=""/>}<div className="feature-overlay"/><div className="feature-content"><span className="feature-kicker">{(() => { const Icon = icons[hero.kind]; return <Icon size={14}/>; })()} {hero.sample ? 'FROM THE OPEN MEDIA COLLECTION' : 'FROM YOUR LIBRARY'}</span><h2>{hero.title}</h2><div className="feature-meta">{hero.year && <span>{hero.year}</span>}<span className="content-rating">{hero.sample ? 'OPEN MEDIA' : kindNames[hero.kind]}</span>{hero.genre && <span>{hero.genre}</span>}</div><p>{hero.description || `${hero.title} is in your Blank Box library.`}</p><div className="feature-actions"><button data-tv className="primary-button" onClick={() => heroPlayable ? play(hero) : void openItem(hero)}>{heroPlayable ? <Play size={17} fill="currentColor"/> : <Info size={17}/>}{heroActionLabel}</button><button data-tv className="glass-button" onClick={() => void openItem(hero)}><Info size={17}/>Details</button><button data-tv className="glass-button icon-only" aria-label={hero.favorite ? 'Remove from favorites' : 'Add to favorites'} onClick={() => favorite(hero)}><Heart size={19} fill={hero.favorite ? 'currentColor' : 'none'}/></button></div></div><div className="feature-caption"><span className="tiny-line"/>{heroPool.length > 1 ? `${heroIndex % heroPool.length + 1} of ${heroPool.length} · Rotates automatically` : hero.kind === 'photo' ? 'A photo from your media · Changes on refresh' : hero.sample ? 'Open sample media' : 'Available in your library'}</div></section> : state.items.length ? <section className="welcome-panel hero-empty"><span className="setup-symbol"><Library size={30}/></span><div><h2>No featured media yet</h2><p>Your selected media types have no titles yet. Add media or change your featured cover choices.</p><button className="subtle-button" onClick={customizeHome}>Choose featured media <Settings2 size={17}/></button></div></section> : <section className="welcome-panel"><span className="setup-symbol"><Library size={30}/></span><div><h2>Start your library</h2><p>Add your physical media, connect a folder or drive, or link your existing media server.</p><button className="primary-button" onClick={() => go('import')}>Add media <Plus size={17}/></button></div></section>)}
 {homeRows.map(row => { const option = homeRowOptions.find(item => item.id === row); if (!option)
                return null; const items = row === 'recently-added' ? (recentlyAdded) : row === 'recently-released' ? (recentlyReleased) : homeCategoryRows[row] || []; if (!items.length && !(row === 'recently-added' && !state.items.length))
                return null; return <section className="section" key={row}><div className="section-heading"><div><h2>{option.label}</h2>{row === 'recently-released' && <p className="muted small">Newer releases available from your digital files and connected libraries.</p>}</div><button data-tv className="text-button" onClick={() => go(row === 'recently-added' || row === 'recently-released' ? 'library' : row === 'movies' ? 'movie' : row === 'photos' ? 'photo' : row === 'books' ? 'book' : row === 'comics' ? 'comic' : row === 'games' ? 'game' : row)}>View {row === 'recently-added' || row === 'recently-released' ? 'library' : 'all'} <ChevronRight size={15}/></button></div><div className="poster-grid home-posters">{items.map(item => card(item))}</div>{!state.items.length && <p className="muted">Your next favorite is waiting to be added.</p>}</section>; })}
 <div className={`home-bottom ${hasLibrarySource ? 'home-bottom-single' : ''}`}><section className="memories-tile"><img src={memoryPhotoUrl || '/art/coast.jpg'} alt={memoryPhoto ? memoryPhoto.title : 'A still lake surrounded by a forest'} loading="lazy"/><div><span className="eyebrow">{memoryPhoto ? 'FROM YOUR PHOTOS' : 'THE IRREPLACEABLE COLLECTION'}</span><h2>{memoryPhoto ? 'Your memories, close at hand.' : <>The good old days,<br />always close.</>}</h2><button data-tv className="glass-button" onClick={() => go('photo')}><Images size={16}/>Photos & Memories <ChevronRight size={15}/></button></div></section>{!hasLibrarySource && <section className="bring-home"><span className="outlined-icon"><FolderInput size={23}/></span><h2>Bring your library home.</h2><p>Discs. Drives. Phones. Cameras.<br />One private place for what matters.</p><button data-tv className="text-button accent" onClick={() => go('import')}>Add your first source <Plus size={17}/></button></section>}</div>
 <section className="section service-strip"><div className="section-heading"><h2>Your services, within reach</h2><button data-tv className="text-button" onClick={() => go('services')}>View all <ChevronRight size={15}/></button></div><div className="service-row">{services.slice(0, 4).map(s => <a data-tv href={s.url} target="_blank" rel="noopener noreferrer" key={s.name}><span style={{ color: s.color }}>{s.mark}</span><ArrowUpRight size={15}/></a>)}</div></section><div className="home-footnote"><LockKeyhole size={13}/>{'Your media stays in Blank Box. Your original source files remain unchanged.'}<button onClick={() => { setSettingsTab('activity'); go('settings'); }}>About V1</button></div></>}
 {view === 'collecting' && !query && (collectingReady ? <CollectionPlanner items={state.items} mode={state.mode} onChange={async () => { await reload(); }}/> : <section className="panel"><h2>Collection planning is in the next Core update</h2><button className="subtle-button" onClick={() => go('physical')}>Return to Physical Media</button></section>)}
 {libraryView && <>
  <div className={`page-heading ${physicalBrowsing ? 'physical-page-heading' : 'library-page-heading'}`}><div><h1>{query ? `Results for “${query}”` : navigationLabels[view]}</h1>{(view !== 'library' || !!query) && <p>{view === 'physical' && !query ? `${state.physicalInventory.titles} ${state.physicalInventory.titles === 1 ? 'title' : 'titles'} · ${state.physicalInventory.packages} ${state.physicalInventory.packages === 1 ? 'physical item' : 'physical items'} · ${state.physicalInventory.copies} ${state.physicalInventory.copies === 1 ? 'copy' : 'copies'}` : `${state.pagedLibrary ? (currentServerPage?.total || 0) : filtered.length} ${(state.pagedLibrary ? (currentServerPage?.total || 0) : filtered.length) === 1 ? 'title' : 'titles'}`}{''}</p>}</div><div className="page-heading-actions">{query && <button className="primary-button" onClick={() => openMatch(null, query)}><Search size={16}/>Find title & services</button>}{physicalBrowsing ? <button className="primary-button" onClick={openPhysical}><Plus size={17}/>Add Physical Item</button> : view === 'physical' ? <>{collectingReady && <button className="subtle-button" onClick={() => go('collecting')}><Plus size={16}/>Intend to Buy</button>}<button className="text-button" onClick={openPhysicalPreferences}><Settings2 size={16}/>Manage locations</button><button className="subtle-button" onClick={openPhysical}><Plus size={17}/>Add a physical item</button></> : <button className="subtle-button" onClick={() => go('import')}><Plus size={16}/>Add media</button>}</div></div>
  {view === 'library' && !query && <LibraryOverview state={state} summary={collectionSummary} onOpen={destination => destination === 'library' ? document.querySelector('.collection-toolbar')?.scrollIntoView({ behavior: 'smooth' }) : go(destination)}/>}
  {physicalBrowsing ? <PhysicalBrowseControls category={filter} onCategory={value => { setFilter(value); setPhysicalFormatFilter('all'); }} format={physicalFormatFilter} formats={physicalFormatOptions} onFormat={setPhysicalFormatFilter} genre={genreFilter} genres={(state.facets?.genres || [...new Set(state.items.flatMap(itemGenres))].sort())} onGenre={setGenreFilter} status={activityFilter} onStatus={setActivityFilter} sort={sort} onSort={setSort} favorites={favorites} onFavorites={() => setFavorites(!favorites)} view={physicalView} onView={setPhysicalView} local={true} onLocations={openPhysicalPreferences} onCollections={() => go('collections')} onIntendToBuy={collectingReady ? () => go('collecting') : undefined}/> : <>
  <div className={`collection-toolbar ${!query && !['library', 'physical'].includes(view) ? 'category-only' : ''}`}>{(query || view === 'library' || view === 'physical') && <Tabs value={filter} onValueChange={value => { setFilter(value); setPhysicalFormatFilter('all'); }} className="category-tabs"><TabsList className="filter-tabs">{[['all', 'All media'], ...Object.entries(kindNames)].map(([id, label]) => <TabsTrigger key={id} value={id}>{label}</TabsTrigger>)}</TabsList></Tabs>}<div className="library-control-row">{<div className="library-organization-filters"><label><span>Genre</span><select value={genreFilter} onChange={event => setGenreFilter(event.target.value)}><option value="">All genres</option>{(state.facets?.genres || [...new Set(state.items.flatMap(itemGenres))].sort()).map(value => <option key={value} value={value}>{value}</option>)}</select></label><label><span>Local status</span><select value={activityFilter} onChange={event => setActivityFilter(event.target.value as ActivityStatus | '')}><option value="">Any status</option><option value="not-started">Unwatched / Not started</option><option value="in-progress">In progress</option><option value="completed">Watched / Completed</option></select></label><button className="text-button" onClick={() => go('collections')}>Browse collections →</button></div>}<div className="collection-options"><button className={`favorite-filter ${favorites ? 'on' : ''}`} onClick={() => setFavorites(!favorites)} aria-label="Show favorites" aria-pressed={favorites}><Heart size={17} fill={favorites ? 'currentColor' : 'none'}/></button><Select value={sort} onValueChange={setSort}><SelectTrigger aria-label="Sort media"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="recent">Recently added</SelectItem><SelectItem value="az">Title A–Z</SelectItem><SelectItem value="year">Newest release</SelectItem><SelectItem value="edition">Edition A–Z</SelectItem></SelectContent></Select></div></div></div>
  </>}
  {<div className="library-bulk-controls"><button className="subtle-button" type="button" onClick={() => { setLibrarySelectionMode(!librarySelectionMode); setLibrarySelection(new Set()); }}>{librarySelectionMode ? 'Done selecting' : 'Select items'}</button>{librarySelectionMode && <><button className="subtle-button" type="button" onClick={() => setLibrarySelection(new Set(pageItems.map(item => item.id)))}>Select this page</button><button className="text-button" type="button" onClick={() => setLibrarySelection(new Set())}>Clear</button><span className="muted small">{selectedPageItems.length} selected on this page · sorting is above</span><button className="subtle-button" type="button" disabled={busy || selectedPageItems.length !== 1} onClick={() => void openItem(selectedPageItems[0])}>Review</button><button className="subtle-button" type="button" disabled={busy || selectedPageItems.length !== 2} onClick={() => void bulkConsolidate()}>Consolidate two</button><button className="subtle-button" type="button" disabled={busy || !selectedPageItems.length} onClick={() => { setLibraryAttachRows([...selectedPageItems]); setLibraryAttachQuery(""); setLibraryAttachResults([]); setLibraryAttachTarget(null); setLibraryAttachError(""); }}>Attach selected to title</button><button className="subtle-button" type="button" disabled={busy || !selectedPageItems.length} onClick={() => void bulkRenameTitles()}>Rename catalog titles</button><button className="subtle-button" type="button" disabled={busy || !selectedPageItems.length} onClick={() => void bulkRemoveRecords()}>Remove records</button></>}</div>}
  {pageError && <p role="alert" className="error-text">{pageError}</p>}
  {state.pagedLibrary && (pageLoading || !currentServerPage || currentServerPage.indexStatus === 'building') ? <p role="status" className="muted">Loading library page…</p> : filtered.length ? view === 'physical' && !query && physicalView === 'shelves' ? <div className="physical-shelf-groups">{shelfPageGroups.map(group => <section className="physical-shelf-group" key={group.location}><div className="physical-shelf-heading"><h2>{group.location}</h2><span>{group.copies} {group.copies === 1 ? 'copy' : 'copies'}</span></div><div className="poster-grid library-grid">{group.items.map(row => <div className="physical-shelf-entry" key={row.item.id}>{card(row.item)}{row.copies > 1 && <small>{row.copies} copies here</small>}</div>)}</div></section>)}</div> : <div className={`poster-grid library-grid ${view === 'photo' ? 'photo-grid' : ''}`}>{pageItems.map(i => card(i))}</div> : <div className="empty-panel"><span className="outlined-icon">{view === 'physical' ? <Disc3 /> : view === 'movie' ? <Film /> : view === 'tv' ? <Tv /> : view === 'book' || view === 'comic' ? <BookOpen /> : view === 'game' ? <Gamepad2 /> : view === 'music' ? <Music2 /> : <Library />}</span><h2>{query ? 'Nothing here by that name.' : favorites ? 'Your favorites will live here.' : view === 'physical' && physicalFormatFilter !== 'all' ? 'No copies in this format.' : view === 'physical' ? 'Start your Physical Media.' : 'Let’s make this yours.'}</h2><p>{query ? 'Try a different title, year, or format.' : view === 'physical' && physicalFormatFilter !== 'all' ? 'Choose another format or add a physical item.' : view === 'physical' ? 'Add your physical media, including its format, edition, and where you keep it.' : view === 'movie' ? 'Add a movie file, connect a media server, or catalog a physical item.' : view === 'tv' ? 'Add a show or connect an existing TV library.' : view === 'book' ? 'Bring in books, PDFs, and EPUBs.' : view === 'comic' ? 'Catalog physical issues and digital comic files.' : view === 'game' ? 'Catalog games by platform, format, and edition.' : view === 'music' ? 'Add music files from your collection.' : view === 'photo' ? 'Bring your photos and home videos into one place.' : 'Add some media to start your collection.'}</p><button className="primary-button" onClick={() => query ? setQuery('') : view === 'physical' ? openPhysical() : go('import')}>{query ? 'Clear search' : 'Add to your library'}<Plus size={16}/></button></div>}
  {libraryEntries > 60 && <nav className="collection-paging library-paging" aria-label="Library pages"><button className="subtle-button" disabled={!libraryPageIndex} onClick={() => changeLibraryPage(libraryPageIndex - 1)}>Previous</button><span>Page {libraryPageIndex + 1} of {Math.ceil(libraryEntries / 60)} · {libraryEntries.toLocaleString()} {shelfBrowsing ? 'location entries' : 'titles'}</span><button className="subtle-button" disabled={(libraryPageIndex + 1) * 60 >= libraryEntries} onClick={() => changeLibraryPage(libraryPageIndex + 1)}>Next</button></nav>}
  {view === 'physical' && <div className="note"><Disc3 size={19}/><p>Physical Media keeps physical copies visible inside your unified library. Saved physical locations tell you where each item actually lives. Playback still requires a supported player or a separately authorized digital copy.</p></div>}
 </>}
 {!query && view === 'import' && <>
  <div className="page-heading"><div><h1>{navigationLabels.import}</h1><p>Choose how your media exists today. Each method shows what Blank Box will add before you confirm.</p></div><span className="quiet-badge"><LockKeyhole size={14}/>Review before changes</span></div>
  <div className="import-options import-method-grid">
   <button className="source-card" onClick={() => document.getElementById('import-files')?.scrollIntoView({ behavior: 'smooth', block: 'start' })}><span className="source-icon peach"><HardDrive size={28}/></span><h2>Files on a drive</h2><p>Index movies, shows, music, books, comics, photos, and files in place. Back up selected personal files separately.</p><span>{'Choose a drive below'}<ChevronRight size={17}/></span></button>
   <button className="source-card" onClick={openPhysical}><span className="source-icon lavender"><Package size={28}/></span><h2>Add physical item</h2><p>Add a disc, book, comic, game, or other owned copy to your Physical Media.</p><span>Add a physical item<ChevronRight size={17}/></span></button>
   <button className="source-card" onClick={() => setCameraIntakeOpen(true)}><span className="source-icon lavender"><Camera size={28}/></span><h2>Scan physical items</h2><p>Use a camera for barcodes or collect cover photos. Review each title and copy before adding it.</p><span>Open camera intake<ChevronRight size={17}/></span></button>
   <button className="source-card" onClick={() => setListImportOpen(true)}><span className="source-icon blue">{<List size={28}/>}</span><h2>{'Import a title list'}</h2><p>{'Bring movie, TV, music, book, comic, or game titles from text, CSV, or TSV. No media bytes are copied.'}</p><span>{'Open guided list import'}<ChevronRight size={17}/></span></button>
   <button className="source-card" onClick={() => { setSettingsTab('connections'); go('settings'); }}><span className="source-icon blue"><Server size={28}/></span><h2>Jellyfin or Plex</h2><p>Connect an existing media catalog. Blank Box reads its details and opens playback there.</p><span>Connect a media server<ChevronRight size={17}/></span></button>
   {<button className="source-card" onClick={() => document.getElementById('import-disc')?.scrollIntoView({ behavior: 'smooth', block: 'start' })}><span className="source-icon lavender"><Disc3 size={28}/></span><h2>Import an audio CD</h2><p>Catalog the physical album and save lossless local tracks from a supported drive.</p><span>Review CD import<ChevronRight size={17}/></span></button>}
  </div>
  {state.settings.helpTipsEnabled && <div className="import-help-tip"><p><strong>Start with the form you have.</strong> A list adds catalog titles; a folder can be indexed in place; Physical Media records physical copies. No method changes an original file without a separate review.</p><button className="text-button" onClick={() => void persistSettings({ ...state.settings, helpTipsEnabled: false })}>Turn off tips</button></div>}
  <div className="import-steps"><span className="active"><b>1</b>Choose a method</span><i /><span className={scanRows.length || state.reviewCount ? 'active' : ''}><b>2</b>Review</span><i /><span><b>3</b>Confirm</span></div><input ref={filesRef} type="file" multiple hidden onChange={e => fileImport(e.target.files)}/>
 <CameraPhysicalIntake open={cameraIntakeOpen} items={state.items} localMetadata={true} completedScanId={completedCameraScanId} onOpenChange={setCameraIntakeOpen} onUse={useCameraEntry}/>
 {<CatalogListImport open={listImportOpen} onOpenChange={setListImportOpen} onChanged={reload}/>}
 {<section className="panel" id="import-files"><div className="section-heading"><h2>Files on a drive or folder</h2><span className="muted">{state.sources.length} available</span></div>{state.sources.length ? <><div className="inline-form"><Select value={sourceId} onValueChange={setSourceId}><SelectTrigger id="source-select" aria-label="Choose source folder"><SelectValue placeholder="Choose a folder or drive"/></SelectTrigger><SelectContent>{state.sources.map(s => <SelectItem key={s.id} value={s.id} disabled={!s.available}>{s.name} {!s.available ? '(offline)' : ''}</SelectItem>)}</SelectContent></Select></div><SourceInventory key={sourceId} sourceId={sourceId} jobs={state.jobs} blocked={busy || !!activeJobs.length} backupConfigured={state.backup.configured} backupPath={state.backup.path} onSetupBackup={() => { go('storage'); setBackupSetupOpen(true); }} onStarted={reload}/><details className="optional-file-tools"><summary>Advanced: make a local managed copy for playback</summary><p className="muted small">This keeps a second file in Blank Box primary storage after selection and count/size review. It is not a backup on your backup drive. Filename cleanup is separate; originals are never renamed or moved.</p><AutoCopyReview sourceId={sourceId} refreshKey={state.jobs.map(job => `${job.id}:${job.status}`).join(',')} blocked={busy || !!activeJobs.length} onReview={() => scan(true)}/><div className="legacy-copy-scan"><h3>Choose personal files for a local managed copy</h3><p className="muted small">Copying computes checksums and creates managed files after a count/size review. It never changes the originals.</p><button className="subtle-button" disabled={busy || !sourceId || !!activeJobs.length} onClick={() => void act('auto-discovery', {}, 'Checking personal files for review')}><Search size={16}/>Find personal files</button><button className="subtle-button" disabled={busy || !sourceId || !!activeJobs.length} onClick={() => scan()}><Search size={16}/>Review all files to copy</button></div></details></> : <p className="muted">No source folders configured. Restart the companion with a source folder using the setup guide.</p>}</section>}
 {!!scanRows.length && <section className="panel"><div className="section-heading"><h2>Review files to copy</h2><span>{scanRows.length} found · {bytes(scanRows.reduce((sum, file) => sum + file.bytes, 0))}</span></div>
  <p className="muted small">Choose individual files or select a whole media type. Nothing is copied until you confirm the exact count and size. Originals are not renamed or changed.</p>
  <div className="kind-checks">{Object.entries(kindNames).filter(([key]) => scanRows.some(file => file.kind === key)).map(([key, label]) => <label key={key}><Checkbox checked={scanKinds.includes(key as Kind)} onCheckedChange={checked => { setScanKinds(checked ? [...scanKinds, key as Kind] : scanKinds.filter(value => value !== key)); setScanPage(0); }}/>{label} <small>{scanRows.filter(file => file.kind === key).length}</small></label>)}</div>
  <div className="catalog-list-actions"><button className="subtle-button" onClick={() => setScanSelected(new Set(visibleScanRows.map(file => file.id)))}>Select shown types</button><button className="text-button" onClick={() => setScanSelected(new Set())}>Clear selection</button><span className="muted small">{selectedScanRows.length} selected</span></div>
  <div className="scan-list">{visibleScanRows.slice(scanPage * 25, scanPage * 25 + 25).map(file => <label key={file.id}><Checkbox checked={scanSelected.has(file.id)} onCheckedChange={checked => setScanSelected(previous => { const next = new Set(previous); if (checked)
                    next.add(file.id);
                else
                    next.delete(file.id); return next; })}/><FolderOpen size={16}/><span>{file.name}</span><small>{file.duplicate ? 'Exact copy already imported' : file.candidates?.length ? 'Possible library match' : bytes(file.bytes)}</small></label>)}</div>
  {visibleScanRows.length > 25 && <div className="catalog-list-actions"><button className="subtle-button" disabled={scanPage === 0} onClick={() => setScanPage(Math.max(0, scanPage - 1))}>Previous</button><span className="muted small">Page {scanPage + 1}</span><button className="subtle-button" disabled={(scanPage + 1) * 25 >= visibleScanRows.length} onClick={() => setScanPage(scanPage + 1)}>Next</button></div>}
  {scanRows.some(file => file.candidates?.length) && <label className="field import-policy"><span>When a title already exists</span><Select value={importPolicy} onValueChange={value => setImportPolicy(value as ImportPolicy)}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="review">Review matches one by one</SelectItem><SelectItem value="keep">Consolidate; keep Blank Box details</SelectItem><SelectItem value="incoming">Consolidate; use incoming details</SelectItem><SelectItem value="new-version">Add as new editions</SelectItem><SelectItem value="separate">Keep as different titles</SelectItem></SelectContent></Select><small>{importPolicy === 'review' ? 'Possible matches will wait in a durable review list.' : importPolicy === 'keep' ? 'Incoming sources join the existing edition; owner edits remain protected.' : importPolicy === 'incoming' ? 'Incoming metadata replaces non-owner fields when available.' : importPolicy === 'new-version' ? 'Incoming files become additional editions beneath the matching title.' : 'No title-based consolidation will occur.'}</small></label>}
  <button className="primary-button" onClick={commit} disabled={busy || !!activeJobs.length || !selectedScanRows.length}><ArrowDownToLine size={17}/>Copy {selectedScanRows.length} selected files</button>
 </section>}
 {<div id="import-disc"><DiscImport items={state.items} pagedLibrary={state.pagedLibrary} jobs={state.jobs} blocked={busy || !!activeJobs.length} preferredDrive={state.settings.opticalDrive} onStarted={reload} onCataloged={item => { go('physical'); setSelected(item); }} onCatalogPhysical={() => { setCameraEntryActive(false); setPhysicalIntakeTarget(null); physicalStart.current = { ...emptyPhysicalDraft, format: 'CD', kind: 'music' }; setDisc(physicalStart.current); setPhysicalManual(false); setAddDisc(true); }} onScanPhysical={() => setCameraIntakeOpen(true)} onManagePacks={() => { setSettingsTab('metadata'); go('settings'); window.setTimeout(() => document.getElementById('metadata-pack-settings')?.scrollIntoView({ behavior: 'smooth' }), 0); }}/></div>}
 <ReconciliationPanel reviews={state.reviews} reviewCount={state.reviewCount} busy={busy} onResolve={(reviewId, policy, targetId) => void resolveReview(reviewId, policy, targetId)} onResolveAll={policy => void resolveAllReviews(policy)}/>
 <ImportActivity jobs={state.jobs}/><div className="note"><Info size={19}/><p>{'Indexing leaves your source media in place. Managed copying handles selected files after count and size review. Audio-CD import remains a distinct Alpha path; protected DVD and Blu-ray copying or Live Disc playback are not included.'}</p></div></>}
 {!query && view === 'services' && <><div className="page-heading"><div><h1>Services & Connections</h1><p>Your personal collection and the services you enjoy, within reach.</p></div></div><h2 className="standalone-heading">Your home services</h2><div className="home-service-grid">{homeServices.map(s => <div className="home-service" key={s.name}><span className="source-icon peach"><s.icon size={24}/></span><div><h2>{s.name}</h2><p>{s.description}</p></div>{safeUrl(state.settings[s.key] as string) ? <a className="subtle-button" href={safeUrl(state.settings[s.key] as string)} target="_blank" rel="noopener noreferrer">Open<ArrowUpRight size={16}/></a> : <button className="subtle-button" onClick={() => { setSettingsTab('connections'); go('settings'); }}>Connect<Plus size={16}/></button>}</div>)}</div><h2 className="standalone-heading">Streaming & entertainment</h2><div className="services-grid">{services.map(s => <a data-tv className="service-tile" href={s.url} target="_blank" rel="noopener noreferrer" key={s.name}><span className="service-wordmark" style={{ color: s.color }}>{s.mark}</span><div><strong>{s.name}</strong><ArrowUpRight size={18}/></div><small>Open official website</small></a>)}</div><div className="note"><ArrowUpRight size={19}/><p>Services open in their own websites. Their subscriptions, sign-ins, and device support still apply. Blank Box does not import their catalogs or viewing history.</p></div></>}
 {!query && view === 'storage' && <>
  <div className="page-heading"><div><h1>{navigationLabels.storage}</h1><p>See your storage and verify a separate copy of the media Blank Box manages.</p></div><button className="subtle-button" onClick={() => reload()}><RefreshCw size={16}/>Refresh</button></div>
  <div className="storage-overview">
   <section className="panel storage-primary"><span className="outlined-icon"><HardDrive size={25}/></span><h2>Your library storage</h2><div className="storage-number">{state.storage ? bytes(state.storage.used) : 'Not connected'}{state.storage && <small>of {bytes(state.storage.total)}</small>}</div><Progress value={state.storage ? state.storage.used / state.storage.total * 100 : 0}/><div className="storage-caption"><span>{state.storage ? `${bytes(state.storage.free)} free` : 'Connect Blank Box for live storage'}</span><span>{state.summary?.titles ?? state.items.filter(i => !i.sample).length} catalog items</span></div><p className="muted small">{state.storage ? 'Usage includes all files on the drive that holds your library. This is not a per-drive health check.' : 'Storage information is unavailable.'}</p></section>
   <section className="panel backup-primary"><span className="outlined-icon"><ShieldCheck size={25}/></span><h2>{state.backup.configured && state.backup.lastVerified ? 'A backup has been checked.' : 'Give your library a second copy.'}</h2><p>{state.backup.lastVerified ? `Last verification: ${new Date(state.backup.lastVerified).toLocaleString()}. ${state.backup.verifiedItems || 0} managed files checked.${state.backup.configured ? '' : ' Reconnect a backup destination before the next run.'}` : 'Connect a separate backup drive to protect your Blank Box catalog and managed media.'}</p><button className="primary-button" disabled={busy || !!activeJobs.length} onClick={() => state.backup.configured ? void act('backup', {}, 'Backup started') : setBackupSetupOpen(true)}>{state.backup.configured ? 'Run & verify backup' : 'How to set up backup'}<ShieldCheck size={17}/></button></section>
  </div>
  {backupSetupOpen && <section className="panel backup-setup" aria-label="Backup setup"><div className="backup-setup-heading"><h2>Set up a separate backup drive</h2><button className="text-button" onClick={() => setBackupSetupOpen(false)} aria-label="Close backup setup"><X size={16}/>Close</button></div><p>Mount a separate drive and choose an existing writable folder on it. Add that path to your installation configuration, restart Blank Box, then return here to run and verify the first backup.</p><div className="backup-platforms"><p><strong>Linux</strong><span>Set <code>backup</code> in <code>/etc/blankbox/config.json</code>.</span></p><p><strong>Docker</strong><span>Mount a host folder at <code>/backup</code> and set <code>BLANKBOX_BACKUP=/backup</code>.</span></p><p><strong>Windows or manual install</strong><span>Set <code>backup</code> in your config or use <code>--backup</code>.</span></p></div><p className="muted small">An optional <code>backupEveryHours</code> schedule runs while Blank Box is on.</p><a className="text-button" href="/downloads/START-HERE.md" target="_blank" rel="noopener noreferrer">Read backup and restore instructions <ArrowUpRight size={16}/></a></section>}
  <div className="protection-list"><div><span className="protection-icon"><HardDrive /></span><span><strong>Primary copy</strong><small>{'Files stored in Blank Box'}</small></span><span className="quiet-badge">{'Connected'}</span></div><div><span className="protection-icon"><ShieldCheck /></span><span><strong>Local backup</strong><small>{state.backup.sameDevice ? 'Backup folder is on the same filesystem; it does not protect against drive failure.' : state.backup.configured ? `Backup destination configured${state.backup.everyHours ? ` · Every ${state.backup.everyHours} hours while running` : ''}` : 'No backup destination configured'}</small></span><span className="quiet-badge">{state.backup.sameDevice ? 'Same filesystem' : state.backup.configured && state.backup.lastVerified ? 'Last run verified' : 'Needs setup or verification'}</span></div><div><span className="protection-icon"><Cloud /></span><span><strong>Off-site copy</strong><small>Keep a separate copy away from your home.</small></span><span className="quiet-badge">Not configured</span></div></div>
  {state.jobs.filter(j => j.type === 'backup').map(j => <div className="job-row" key={j.id}><ShieldCheck /><div><strong>Library backup · {j.status}</strong><p>{j.message}</p>{j.errors?.length ? <p className="error-text">{j.errors.join(' · ')}</p> : null}<Progress value={j.total ? j.done / j.total * 100 : 0}/></div></div>)}
  <div className="note"><Info size={19}/><p>Verified backup covers Blank Box’s catalog and managed media only. It does not copy unimported source folders, your whole computer, or Jellyfin, Plex, and Immich databases. Test a restore before relying on it.</p></div>
 </>}
 {!query && view === 'settings' && <>
  <div className="page-heading"><div><h1>{navigationLabels.settings}</h1><p>Choose an area to find the controls you need.</p></div><span className="quiet-badge">Blank Box {state.version || BLANKBOX_VERSION} · {BLANKBOX_CHANNEL}</span></div>
  {settingsDirty && <div className="settings-unsaved" role="status"><span><strong>Unsaved changes</strong><small>Your choices are not active until you save them.</small></span><div><button className="text-button" onClick={() => setForm(state.settings)}>Discard</button><button className="primary-button" disabled={busy || !form.name.trim()} onClick={() => void saveSettings()}>Save changes <Check size={16}/></button></div></div>}
  <nav className="settings-tabs" role="tablist" aria-label="Settings sections" onKeyDown={event => { if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key))
                return; event.preventDefault(); const tabs = settingsTabs.filter(tab => true || !['devices', 'metadata'].includes(tab.id)); const index = tabs.findIndex(tab => tab.id === settingsTab); const next = event.key === 'Home' ? tabs[0] : event.key === 'End' ? tabs[tabs.length - 1] : tabs[(index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length]; setSettingsTab(next.id); requestAnimationFrame(() => document.getElementById(`settings-tab-${next.id}`)?.focus()); }}>{settingsTabs.filter(tab => true || !['devices', 'metadata'].includes(tab.id)).map(tab => { const Icon = tab.icon; return <button key={tab.id} id={`settings-tab-${tab.id}`} type="button" role="tab" aria-selected={settingsTab === tab.id} aria-controls={`settings-panel-${tab.id}`} tabIndex={settingsTab === tab.id ? 0 : -1} className={settingsTab === tab.id ? 'active' : ''} onClick={() => setSettingsTab(tab.id)}><Icon size={17}/>{tab.label}</button>; })}</nav>
  <div id={`settings-panel-${settingsTab}`} role="tabpanel" aria-labelledby={`settings-tab-${settingsTab}`} className="settings-layout settings-tab-content">
    {settingsTab === 'general' && <section className="panel"><h2>Your household</h2>{field('Library name', 'name', 'Your household')}{!isMobile && <div className="setting-row"><span><strong>TV mode</strong><small>Enlarges the interface and adds remote-friendly focus.</small></span><Switch checked={activeTvMode} aria-label="TV mode" onCheckedChange={toggleTvMode}/></div>}<div className="setting-row"><span><strong>Helpful tips</strong><small>Short, dismissible explanations on import and physical collection screens.</small></span><Switch checked={form.helpTipsEnabled} aria-label="Show helpful tips" onCheckedChange={helpTipsEnabled => setForm({ ...form, helpTipsEnabled })}/></div><div className="settings-actions"><button className="primary-button" disabled={busy || !form.name.trim()} onClick={() => saveSettings()}>Save household <Check size={17}/></button><button className="text-button" onClick={() => { setForm(state.settings); setOnboarding(true); }}>Run setup again <ChevronRight size={16}/></button></div></section>}
    {settingsTab === 'connections' && <details className="settings-disclosure" open><summary><span><strong>Service connections</strong><small>Jellyfin, Plex, Immich, and private access</small></span><ChevronDown size={18}/></summary><div className="settings-disclosure-body"><p className="muted small">Connect catalogs you already operate. Blank Box remains the ownership layer and opens playback in the source service. <a href="/downloads/guides/PLAYBACK.md" target="_blank" rel="noopener noreferrer">New to Jellyfin or Plex? Read the playback guide.</a> <a href="/downloads/guides/CONNECTION-KEYS.md" target="_blank" rel="noopener noreferrer">How to get a Jellyfin API key or Plex token.</a></p>{field('Jellyfin address', 'jellyfinUrl', 'http://blank-box:8096')}{field('Plex server address', 'plexUrl', 'http://blank-box:32400')}{field('Immich address', 'immichUrl', 'http://blank-box:2283')}{field('Private remote address', 'remoteUrl', 'https://remote.example.com')}<button className="primary-button" disabled={busy} onClick={() => saveSettings()}>Save connections <Check size={17}/></button>{<><div className="connection-extra"><h3>Bring in your Jellyfin catalog</h3><p className="muted small">Read movie, series, and music metadata. Playback opens Jellyfin. The key stays in Blank Box.</p><label className="field"><span>Jellyfin API key</span><input type="password" autoComplete="off" value={jellyKey} onChange={e => setJellyKey(e.target.value)} placeholder="Create a key in the Jellyfin dashboard"/></label><a className="text-button connection-key-guide" href="/downloads/guides/CONNECTION-KEYS.md" target="_blank" rel="noopener noreferrer">How to create a Jellyfin API key <ArrowUpRight size={14}/></a><button className="subtle-button" disabled={busy || !form.jellyfinUrl || !jellyKey} onClick={async () => { const v = await act('jellyfin', { url: form.jellyfinUrl, key: jellyKey }, 'Jellyfin catalog added'); if (v)
                setJellyKey(''); }}>Sync Jellyfin <RefreshCw size={16}/></button></div><div className="connection-extra"><h3>Bring in your Plex catalog</h3><p className="muted small">Read movie, series, and album metadata. Playback opens Plex. The token stays in Blank Box and is excluded from portable backups.</p><label className="field"><span>Plex token</span><input type="password" autoComplete="off" value={plexKey} onChange={e => setPlexKey(e.target.value)} placeholder="Use a token from your Plex account"/></label><a className="text-button connection-key-guide" href="/downloads/guides/CONNECTION-KEYS.md" target="_blank" rel="noopener noreferrer">How to find a Plex token <ArrowUpRight size={14}/></a><button className="subtle-button" disabled={busy || !form.plexUrl || !plexKey} onClick={async () => { const v = await act('plex', { url: form.plexUrl, key: plexKey }, 'Plex catalog added'); if (v)
                setPlexKey(''); }}>Sync Plex <RefreshCw size={16}/></button></div></>}</div></details>}
    {settingsTab === 'collection' && <section className="panel"><h2>Automatic library refresh</h2><p className="muted small">Connected catalogs can refresh without copying media. Configured folders can be checked automatically for new or changed files. Files stay in place, and matches require review.</p><div className="setting-row"><span><strong>Refresh connected catalogs</strong><small>Update Jellyfin and Plex metadata without copying media files.</small></span><Switch checked={form.autoProviderRefresh} aria-label="Refresh connected catalogs automatically" onCheckedChange={v => setForm({ ...form, autoProviderRefresh: v })}/></div><div className="setting-row"><span><strong>Monitor configured media folders</strong><small>Check movies, TV, music, books, comics, photos, and files in place. New or changed files need two stable observations at least a minute apart, then appear in Import Media for review. Missing drives keep their catalog links.</small></span><Switch checked={form.autoSourceIndex} aria-label="Monitor configured media folders" onCheckedChange={v => setForm({ ...form, autoSourceIndex: v })}/></div><div className="setting-row"><span><strong>Find personal files for optional local copies</strong><small>Discover stable photos, home videos, and files for a managed playback copy on primary storage. Backup-drive copies are selected directly in Import Media.</small></span><Switch checked={form.autoFolderCopy} aria-label="Find personal files for optional local copies" onCheckedChange={v => setForm({ ...form, autoFolderCopy: v, autoImport: v })}/></div><label className="field"><span>Check every <small>minutes</small></span><input type="number" min="1" max="1440" value={form.autoImportMinutes} onChange={e => setForm({ ...form, autoImportMinutes: Number(e.target.value) })}/></label><button className="primary-button" disabled={busy || !form.name.trim() || form.autoImportMinutes < 1 || form.autoImportMinutes > 1440} onClick={() => saveSettings()}>Save refresh settings <Check size={17}/></button></section>}
    {settingsTab === 'devices' && <OpticalDriveSettings value={form.opticalDrive} busy={busy} onChange={opticalDrive => setForm(current => ({ ...current, opticalDrive }))} onSave={() => void saveSettings()} onImport={() => { go('import'); window.setTimeout(() => document.getElementById('disc-import')?.scrollIntoView({ behavior: 'smooth' }), 0); }}/>}
    {settingsTab === 'metadata' && <MetadataPackManager />}
    {settingsTab === 'general' && <SidebarCustomization settings={form} busy={busy} onChange={setForm} onSave={() => void saveSettings()}/>}
    {settingsTab === 'general' && <details className="settings-disclosure" open><summary><span><strong>Customize Home</strong><small>Featured covers, category rows, and their order</small></span><ChevronDown size={18}/></summary><HomeCustomization settings={form} busy={busy} onChange={setForm} onSave={() => void saveSettings()}/></details>}
    {settingsTab === 'activity' && <ImportActivity jobs={state.jobs}/>}
    {settingsTab === 'activity' && <details className="settings-disclosure" open><summary><span><strong>Complete recovery points</strong><small>Catalog, managed media, and installed offline packs together</small></span><ChevronDown size={18}/></summary><div className="settings-disclosure-body"><p className="muted small">Create a complete recovery point on your configured backup drive. The update installer still makes its own paired maintenance snapshot. To copy indexed photos, home videos, or personal files to the backup drive, use the separate, confirmed Import action. Linked source-drive originals remain in place.</p><div className="inline-form"><button className="subtle-button" disabled={!state.backup.configured || busy || !!activeJobs.length} onClick={() => void act('full-recovery', {}, 'Complete recovery point started')}><ShieldCheck size={16}/>Create recovery point</button><button className="subtle-button" disabled={!state.backup.configured || recoveryLoading} onClick={() => void loadRecoveryPoints()}><RefreshCw size={16}/>Find recovery points</button></div>{!state.backup.configured && <p className="muted small">Configure a separate backup destination in Storage & Backup first.</p>}{recoveryPoints.map(point => <div className="setting-row" key={point.id}><span><strong>{new Date(point.createdAt).toLocaleString()}</strong><small>Recovery point {point.id}</small></span><button className="subtle-button" disabled={busy || !!activeJobs.length} onClick={() => void prepareRecovery(point.id)}>Prepare full restore</button></div>)}{state.jobs.filter(job => ['full-recovery', 'prepare-full-restore'].includes(job.type)).map(job => <p className="muted small" key={job.id}>{job.type === 'full-recovery' ? 'Recovery point' : 'Restore preparation'} · {job.status}: {job.message}</p>)}<p className="muted small">A restore is prepared in a new empty review directory; it does not replace the running library. Review it before a deliberate offline switch. Read the <a href="/downloads/START-HERE.md" target="_blank" rel="noopener noreferrer">setup and recovery guide</a>.</p></div></details>}
    {settingsTab === 'activity' && <details className="settings-disclosure"><summary><span><strong>Restore saved provider covers</strong><small>After moving a library to another computer</small></span><ChevronDown size={18}/></summary><div className="settings-disclosure-body"><p className="muted small">Portable recovery keeps saved titles, uploaded covers, and Plex/Jellyfin addresses, but excludes their private keys. Reconnect each provider in Service connections if its address or key changed. Then use this action to fill missing covers from saved provider artwork. It leaves uploaded covers, other title details, and metadata source choices alone.</p><button className="subtle-button" disabled={busy || !!activeJobs.length} onClick={() => void restoreMissingCovers()}><RefreshCw size={16}/>Restore missing covers</button>{state.jobs.filter(job => job.type === 'restore-provider-covers').map(job => <p className="muted small" key={job.id}>Cover restoration · {job.status}: {job.message}</p>)}</div></details>}
    {settingsTab === 'activity' && <details className="settings-disclosure" open><summary><span><strong>Update Blank Box software</strong><small>Prepare a recovery point, then install a verified new package</small></span><ChevronDown size={18}/></summary><div className="settings-disclosure-body"><p className="muted small">The operating system controls software installation. First create and verify a complete recovery point on your configured backup drive. Then download the new release package and run its platform installer. The installer also keeps its paired catalog and pack snapshot for rollback.</p>{state.backup.configured ? <button className="subtle-button" type="button" disabled={busy || !!activeJobs.length} onClick={() => void act('full-recovery', {}, 'Update recovery point started')}><ShieldCheck size={16}/>Create recovery point for update</button> : <p className="muted small">Set up a separate backup destination in Storage & Backup before updating.</p>}{state.jobs.filter(job => job.type === 'full-recovery').slice(0, 1).map(job => <p key={job.id} role="status" className="muted small">Recovery point · {job.status}: {job.message}</p>)}<p className="muted small">Wait for the recovery point to finish before running the installer. Review the package version and signature; keep the prior package for rollback.</p><div className="inline-form"><a className="text-button" href="/downloads/guides/LINUX.md" target="_blank" rel="noopener noreferrer">Linux update guide <ArrowUpRight size={14}/></a><a className="text-button" href="/downloads/guides/DOCKER.md" target="_blank" rel="noopener noreferrer">Docker update guide <ArrowUpRight size={14}/></a><a className="text-button" href="/downloads/guides/WINDOWS.md" target="_blank" rel="noopener noreferrer">Windows update guide <ArrowUpRight size={14}/></a></div></div></details>}
    {settingsTab === 'activity' && <details className="settings-disclosure" open><summary><span><strong>About this installation</strong><small>{`Community software running · ${state.version || BLANKBOX_VERSION}`}</small></span><ChevronDown size={18}/></summary><div className="settings-disclosure-body"><p className="muted small">{'This self-hosted installation is running on your device.'}</p>{false}<a className="text-button" href="/downloads/START-HERE.md" target="_blank" rel="noopener noreferrer">Setup guide <ArrowUpRight size={16}/></a><details className="version-capabilities"><summary>What works in this version</summary><div className="scope-panel">{['Browse and organize media', 'Catalog physical copies and editions', 'Scan mounted folders and connect Jellyfin or Plex', 'Play supported files and check backups', 'Use an owner profile and recovery key'].map(s => <div key={s}><CheckCircle2 size={16}/>{s}</div>)}</div></details></div></details>}
    {settingsTab === 'activity' && <div className="settings-links"><a href="/downloads/README.md" target="_blank" rel="noopener noreferrer">Community guide <ArrowUpRight size={14}/></a><a href="/credits" target="_blank" rel="noopener noreferrer">Artwork and third-party notices <ArrowUpRight size={14}/></a></div>}

 {settingsTab === 'collection' && <PhysicalOrganizationSettings settings={form} items={state.items} locationsSummary={state.facets?.locations} busy={busy} onChange={setForm} onSave={() => void saveSettings()} onMove={movePhysicalLocation}/>}
 {settingsTab === 'connections' && state.hiddenItems > 0 && <details className="settings-disclosure settings-wide-disclosure hidden-items-disclosure"><summary><span><strong>{state.hiddenItems} hidden connected {state.hiddenItems === 1 ? 'item' : 'items'}</strong><small>Review or restore individual records. Jellyfin and Plex are not changed.</small></span><ChevronDown size={18}/></summary><div className="hidden-items-body"><div className="hidden-items-list">{(state.hiddenRecords || []).map(record => <div className="hidden-item-row" key={record.id}><span><strong>{record.title}</strong><small>{record.source} · {kindNames[record.kind as Kind] || record.kind}{record.hiddenAt ? ` · Hidden ${new Date(record.hiddenAt).toLocaleDateString()}` : ''}</small></span><button className="subtle-button" disabled={busy} onClick={() => void act('restore-hidden', { id: record.id }, 'Connected item restored')}>Restore</button></div>)}</div>{state.pagedLibrary && state.hiddenItems > 50 && <div className="collection-paging"><button disabled={!hiddenOffset} onClick={() => setHiddenOffset(Math.max(0, hiddenOffset - 50))}>Previous</button><span>{hiddenOffset + 1}–{Math.min(hiddenOffset + 50, state.hiddenItems)} of {state.hiddenItems}</span><button disabled={hiddenOffset + 50 >= state.hiddenItems} onClick={() => setHiddenOffset(hiddenOffset + 50)}>Next</button></div>}<button className="text-button" disabled={busy} onClick={() => { if (window.confirm(`Restore all ${state.hiddenItems} hidden connected items to your library?`))
                void act('restore-hidden', {}, 'Hidden connected items restored'); }}>Restore all hidden items</button></div></details>}
  </div>
 </>}
 {!!activeJobs.length && view !== 'import' && view !== 'storage' && <button className="job-toast" onClick={() => go(activeJobs[0].type === 'backup' ? 'storage' : 'import')}><Loader2 size={16} className="animate-spin"/><span>{activeJobs[0].message || 'Blank Box is working…'}</span><ChevronRight size={16}/></button>}
 </>}
 </main></div></div>
 <Dialog open={libraryAttachRows.length > 0} onOpenChange={open => { if (!open && !busy) {
        setLibraryAttachRows([]);
        setLibraryAttachTarget(null);
        setLibraryAttachError('');
    } }}><DialogContent className="form-dialog inventory-review-dialog"><DialogHeader><DialogTitle>Attach selected titles to one Media Item</DialogTitle><DialogDescription>Use this for stray tracks or episodes that already became separate library titles. The chosen title keeps its ID and details. Originals stay on their drives.</DialogDescription></DialogHeader><p className="muted small">{libraryAttachRows.length} selected on this page. Only simple linked file records can be consolidated here; owner edits and extra editions need individual review.</p><div className="inventory-selected-paths"><ul>{libraryAttachRows.map(item => <li key={item.id}>{item.title} · {item.id}</li>)}</ul></div><form className="match-search" onSubmit={event => { event.preventDefault(); void searchLibraryAttach(); }}><label><Search size={17}/><input value={libraryAttachQuery} maxLength={200} onChange={event => setLibraryAttachQuery(event.target.value)} placeholder="Search for the destination show or album" aria-label="Search destination title"/></label><button className="subtle-button" disabled={busy || !libraryAttachQuery.trim()} type="submit">Search library</button></form><div className="inventory-candidates">{libraryAttachResults.map(item => <label key={item.id}><input type="radio" name="library-attach-target" checked={libraryAttachTarget?.id === item.id} onChange={() => setLibraryAttachTarget(item)}/><span>{item.title}{item.year ? ` (${item.year})` : ''}<small>{kindNames[item.kind]} · Media Item {item.id}</small></span></label>)}{!libraryAttachResults.length && <p className="muted small">Search for the title that should remain in your library. It may be one of the selected titles.</p>}</div>{libraryAttachError && <p role="alert" className="error-text">{libraryAttachError}</p>}<button className="primary-button" disabled={busy || !libraryAttachTarget || libraryAttachRows.filter(item => item.id !== libraryAttachTarget.id).length === 0} onClick={() => void attachLibrarySelection()}>Attach {libraryAttachRows.filter(item => item.id !== libraryAttachTarget?.id).length} to {libraryAttachTarget?.title || 'chosen title'}</button></DialogContent></Dialog>
 <Dialog open={sourceReviewOpen} onOpenChange={setSourceReviewOpen}><DialogContent className="form-dialog reconciliation-dialog"><DialogHeader><DialogTitle>We found possible matches</DialogTitle><DialogDescription>Review them now, or leave them safely in Import Media for later.</DialogDescription></DialogHeader><ReconciliationPanel reviews={state.reviews} reviewCount={state.reviewCount} busy={busy} onResolve={(reviewId, policy, targetId) => void resolveReview(reviewId, policy, targetId, true)} onResolveAll={policy => void resolveAllReviews(policy, true)}/><button className="subtle-button decide-later" onClick={() => { setSourceReviewOpen(false); toast.info('Possible matches saved in Import Media.'); }}>Decide later</button></DialogContent></Dialog>
 {selected && <MediaDetailDialog key={selected.id} item={selected} opticalDrive={state.settings.opticalDrive} onActivityChange={() => void reload()} streamingServices={state.settings.streamingServices} retailEnabled={collectingReady} metadataEnabled={true} busy={busy} playable={!!playUrl(selected) || selected.kind === 'photo' && !!selected.poster} playLabel={playLabel(selected)} refreshable={selected.sources.some(source => ['jellyfin', 'plex'].includes(source.type))} onClose={() => setSelected(null)} onPlay={() => play(selected)} onPlaySource={source => playSource(selected, source)} onRemoveSource={source => void removeSource(selected, source)} onRefresh={() => void refreshItem(selected)} onFavorite={() => favorite(selected)} onEdit={() => { setSelected(null); openEditor(selected, 'detail'); }} onRemove={removeSelected}/>}
 {catalogEditor && <CatalogEditorDialog key={`${catalogEditor.id}-${catalogEditor.metadataMatch?.matchedAt || ''}-${editorRevision}`} item={catalogEditor} genreSuggestions={state.facets?.genres || [...new Set(state.items.flatMap(item => item.customGenres || []))]} busy={busy} onClose={closeEditor} onMatch={() => openMatch(catalogEditor, catalogEditor.title)} onAddPhysical={editorOrigin === 'detail' ? () => openPhysicalForItem(catalogEditor) : undefined} backLabel={editorOrigin === 'intake' ? 'Back to import choices' : 'Back to media details'} onBack={backFromEditor} onSave={edit => saveMetadata(catalogEditor, edit)} onChooseMetadata={sourceId => chooseEditorMetadata(catalogEditor, sourceId)} onRefreshMetadata={() => refreshEditorMetadata(catalogEditor)} onUploadArtwork={image => uploadEditorArtwork(catalogEditor, image)} onRemoveArtwork={() => removeEditorArtwork(catalogEditor)}/>}
 {matchOpen && <MetadataMatchDialog key={matchSeed} open target={matchTarget} initialQuery={matchTarget?.title || query} streamingServices={state.settings.streamingServices} busy={busy} onOpenChange={setMatchOpen} onBackToChoices={editorOrigin === 'intake' && intakeChoice ? () => { setMatchOpen(false); if (catalogEditor)
        backFromEditor();
    else
        setJustAddedPhysical(intakeChoice); } : undefined} onSearch={searchMatches} onApply={applyMatch} onOpenItem={item => void openItem(item)} onReferenceConfirm={matchTarget ? async (entityId) => { setBusy(true); try {
        const item = await blankBoxClient.metadataConfirm('item', matchTarget.id, entityId, true);
        if (item) {
            setCatalogEditor(item);
            setEditorRevision(revision => revision + 1);
            setSelected(null);
        }
        await reload();
        toast.success('Title matched and available details filled.');
    }
    finally {
        setBusy(false);
    } } : undefined}/>}
 {reading && <DocumentReader key={`${reading.item.id}:${reading.source.id}`} {...reading} onClose={() => { setReading(null); void reload(); }} onProgress={progress => { void blankBoxClient.action('update', { id: reading.item.id, progress }).catch(() => toast.error('Reading progress could not be saved.')); }}/>}
 <Dialog open={!!playing} onOpenChange={v => !v && setPlaying(null)}><DialogContent className="player-dialog">{playing && (playing.kind === 'music' ? <MusicPlayer key={`${playing.id}:${musicStartSourceId || ''}`} item={playing} startSourceId={musicStartSourceId}/> :
            <LocalMediaPlayer key={`${playing.id}:${playUrl(playing)}`} item={playing} source={preferredPlaybackSource(playing)} url={playUrl(playing)} alternatives={playbackAlternatives} onProgress={progress => { const source = preferredPlaybackSource(playing); const audiobook = playing.kind === 'book' && source?.id && isAudiobookSource(source); void blankBoxClient.action(audiobook ? 'update-source-progress' : 'update', audiobook ? { id: playing.id, sourceId: source.id, progress } : { id: playing.id, progress }).then(() => reload()).catch(() => toast.error('Playback progress could not be saved.')); }}/>)}</DialogContent></Dialog>
 <Dialog open={rightsOpen} onOpenChange={open => { setRightsOpen(open); if (!open)
        pendingPlayback.current = null; }}><DialogContent className="form-dialog"><DialogHeader><DialogTitle>Before using your media</DialogTitle><DialogDescription>This acknowledgement is saved once for your household.</DialogDescription></DialogHeader><MediaRightsChoice accepted={rightsAccepted} onChange={setRightsAccepted}/><button className="primary-button" disabled={busy || !rightsAccepted} onClick={() => void acceptMediaRights()}>Agree and continue</button><button className="text-button" onClick={() => { setRightsOpen(false); pendingPlayback.current = null; }}>Later</button></DialogContent></Dialog>
 {addDisc && <AddPhysicalDialog open busy={busy} draft={disc} manual={physicalManual} formats={!intakeFormats.includes(disc.format) ? [disc.format, ...intakeFormats] : intakeFormats} locations={physicalLocations} gamePlatforms={gamePlatforms} onOpenChange={open => { if (!open)
        closePhysicalDraft(); }} onChange={setDisc} onSaveLocation={savePhysicalLocation} onSaveFormats={saveVisiblePhysicalFormats} onSavePlatforms={saveVisibleGamePlatforms} onFindMatch={() => void reviewPhysical()} onManual={() => setPhysicalManual(true)} onContinue={() => void reviewPhysical()}/>}
 <Dialog open={!!physicalReview} onOpenChange={open => { if (!open)
        closePhysicalDraft(); }}><DialogContent ref={physicalReviewDialogRef} className="form-dialog duplicate-review-dialog">
  <DialogHeader><DialogTitle>{physicalChoice ? 'How does this item fit?' : 'Review the physical item'}</DialogTitle><DialogDescription>{physicalChoice ? 'Choose an existing edition or make a separate edition. Nothing changes until you add the item.' : 'Choose where to look for a title. This item is still a draft and is not in your collection.'}</DialogDescription></DialogHeader>
  {physicalReview && !physicalChoice && <>
   <p className="muted small">Physical item: <strong>{physicalReview.draft.title}</strong> · {physicalReview.draft.format}{physicalReview.draft.edition ? ` · ${physicalReview.draft.edition}` : ''}{physicalReview.draft.location ? ` · ${physicalReview.draft.location}` : ''}</p>
   {visiblePhysicalCandidates.length > 0 && <div className="duplicate-candidates"><div className="physical-match-heading"><strong>Possible match or duplicate in your library</strong><small>{visiblePhysicalCandidates.length} existing {visiblePhysicalCandidates.length === 1 ? 'title' : 'titles'} found. Choose one to add this copy under it.</small></div>
    {visiblePhysicalCandidates.map(item => <article key={item.id} className="duplicate-candidate"><Library size={19}/><span><strong>{item.title}</strong><small>{[item.year, kindNames[item.kind], item.sources.filter(source => source.type === 'physical').map(source => source.label).join(' · '), item.sources.filter(source => ['jellyfin', 'plex'].includes(source.type)).map(source => source.label).join(' · ')].filter(Boolean).join(' · ')}</small></span><button className="subtle-button" disabled={busy} onClick={() => { const versions = matchingPhysicalVersions(item, physicalReview.draft); setPhysicalChoice({ item, mode: versions.length ? null : 'new', versionId: versions[0]?.id || '' }); }}>Add copy to this title<ChevronRight size={16}/></button></article>)}
   </div>}
   {physicalReviewSource === 'packs' && packHouseholdMatches.length > 0 && <div className="duplicate-candidates"><div className="physical-match-heading"><strong>Possible match in your library</strong><small>Add this copy to an existing title to keep its physical copies and digital playback sources together.</small></div>
    {packHouseholdMatches.map(item => <article key={item.id} className="duplicate-candidate"><Library size={19}/><span><strong>{item.title}</strong><small>{[item.year, kindNames[item.kind], selectedPackCandidate?.householdItemIds?.includes(item.id) ? 'Already linked to this reference' : 'Possible title match', item.sources.filter(source => source.type === 'physical').length + ' physical copies', item.sources.some(source => ['jellyfin', 'plex'].includes(source.type)) ? 'Connected playback' : ''].filter(Boolean).join(' · ')}</small></span><button className="subtle-button" disabled={busy} onClick={() => { const versions = matchingPhysicalVersions(item, physicalReview.draft); setPhysicalChoice({ item, mode: versions.length ? null : 'new', versionId: versions[0]?.id || '', metadataEntityId: physicalMetadata?.id }); }}>Add copy to this title<ChevronRight size={16}/></button></article>)}
   </div>}
   {physicalReviewSource === 'packs' && <section className="physical-pack-search" aria-label="Blank Box Database matches"><div className="physical-match-heading"><strong>Blank Box Database matches</strong><small>Search installed Offline Metapacks. A title match alone does not prove an edition.</small></div><MetadataCandidateReview key={physicalMetadataSignature(physicalReview.draft)} title={physicalReview.draft.title} kind={physicalReview.draft.kind} year={physicalReview.draft.year ? Number(physicalReview.draft.year) : null} identifier={physicalReview.draft.barcode.trim() ? { namespace: physicalReview.draft.kind === 'book' ? 'isbn' : 'upc-ean', value: physicalReview.draft.barcode.trim() } : undefined} selectedId={physicalMetadata?.signature === physicalMetadataSignature(physicalReview.draft) ? physicalMetadata.id : ''} onSelect={(id, candidate) => { setPhysicalMetadata(id ? { id, signature: physicalMetadataSignature(physicalReview.draft), candidate } : null); setSeparatePhysicalConfirmed(false); setPackMatchLookup(null); setPackMatchRevision(value => value + 1); if (id)
            scrollPhysicalReviewToTop(); }} onSearchComplete={scrollPhysicalReviewToTop} sourceScope="packs" targetLevel="any" releaseRequiresIdentifier disabled={busy}/></section>}
   <section className="physical-review-search" aria-label="Find a matching title">
    <div className="physical-match-heading"><strong>Search for a title</strong><small>Choose where to look, then review a result before attaching this copy.</small></div>
    <div className="physical-review-sources" role="group" aria-label="Where to match this item">
     <button type="button" className={physicalReviewSource === 'household' ? 'selected' : ''} aria-pressed={physicalReviewSource === 'household'} onClick={() => { setPhysicalReviewSource('household'); scrollPhysicalReviewToTop(); }}><HardDrive size={17}/><span><strong>My Library</strong><small>All saved titles, including connected libraries</small></span></button>
     <button type="button" className={physicalReviewSource === 'packs' ? 'selected' : ''} aria-pressed={physicalReviewSource === 'packs'} onClick={() => { setPhysicalReviewSource('packs'); scrollPhysicalReviewToTop(); }}><Search size={17}/><span><strong>Search Blank Box Database</strong><small>Search reference titles installed on this box</small></span></button>
     <button type="button" className={physicalReviewSource === 'connected' ? 'selected' : ''} aria-pressed={physicalReviewSource === 'connected'} onClick={() => { setPhysicalReviewSource('connected'); scrollPhysicalReviewToTop(); }}><Server size={17}/><span><strong>Connected libraries</strong><small>Synced Jellyfin and Plex titles</small></span></button>
    </div>
    <button type="button" className="text-button physical-manual-choice" disabled={busy} onClick={() => backToPhysicalDetails(true)}><Disc3 size={16}/>Enter details myself</button>
    {(physicalReviewSource === 'household' || physicalReviewSource === 'connected') && <form className="match-search" onSubmit={event => { event.preventDefault(); void searchPhysicalLibrary(); }}><label><Search size={17}/><input value={physicalSearchQuery} onChange={event => setPhysicalSearchQuery(event.target.value)} placeholder="Search an existing title"/></label><button className="subtle-button" disabled={busy || !physicalSearchQuery.trim()}>Search</button></form>}
   </section>
   <div className="form-grid physical-review-details">
    <label className="field"><span>Format</span><select disabled={busy} value={physicalReview.draft.format} onChange={event => changePhysicalReviewDraft(physicalDraftForFormat(physicalReview.draft, event.target.value as PhysicalFormat))}>{[...new Set([physicalReview.draft.format, ...intakeFormats])].map(format => <option key={format} value={format}>{physicalFormatLabel(format)}</option>)}</select></label>
    <label className="field"><span>Media type</span><select disabled={busy} value={physicalReview.draft.kind} onChange={event => changePhysicalReviewDraft(physicalDraftForKind(physicalReview.draft, event.target.value as Kind))}>{physicalKindOptions(physicalReview.draft.format).map(kind => <option key={kind} value={kind}>{kindNames[kind]}</option>)}</select></label>
    <label className="field"><span>Barcode / ISBN <small>optional</small></span><input disabled={busy} maxLength={80} value={physicalReview.draft.barcode} onChange={event => changePhysicalReviewDraft({ ...physicalReview.draft, barcode: event.target.value })}/></label>
    {physicalReview.draft.kind === 'game' && <label className="field"><span>Console or platform <small>required</small></span><input disabled={busy} list="physical-review-platforms" maxLength={120} value={physicalReview.draft.platform === '__custom__' ? '' : physicalReview.draft.platform} onChange={event => changePhysicalReviewDraft({ ...physicalReview.draft, platform: event.target.value })}/><datalist id="physical-review-platforms">{gamePlatforms.map(platform => <option key={platform} value={platform}/>)}</datalist></label>}
   </div>
   {physicalReviewSource === 'packs' && <section className="physical-pack-review">
    {selectedPackCandidate && <>
     <div className="barcode-reference-summary"><CheckCircle2 size={18}/><span><strong>{selectedPackCandidate.title}</strong><small>{selectedPackCandidate.level === 'release' ? 'Matched edition' : 'Matched title'} · {[selectedPackCandidate.year, selectedPackCandidate.format, selectedPackCandidate.edition].filter(Boolean).join(' · ')}</small></span><button className="text-button" onClick={() => setPhysicalMetadata(null)}>Clear match</button></div>
     {packMatchPending && <p role="status" className="muted small">Checking your library, including connected sources…</p>}
     {packMatchError && <p role="alert" className="error-text">Could not check existing library titles: {packMatchError} <button className="text-button" disabled={busy} onClick={() => setPackMatchRevision(value => value + 1)}>Retry library check</button></p>}
     {packHouseholdMatches.length > 0 && <label className="physical-separate-confirm"><input type="checkbox" checked={separatePhysicalConfirmed} onChange={event => setSeparatePhysicalConfirmed(event.target.checked)}/><span>I checked these titles and want a separate library item.</span></label>}
     <button className="primary-button" disabled={busy || !physicalMetadata || packMatchPending || !!packMatchError || packHouseholdMatches.length > 0 && !separatePhysicalConfirmed || physicalReview.draft.kind === 'game' && (!physicalReview.draft.platform.trim() || physicalReview.draft.platform === '__custom__')} onClick={() => void createPhysical(physicalReview.draft, physicalMetadata?.id)}>{packHouseholdMatches.length ? 'Create separate title and add item' : 'Confirm title and add physical item'}</button>
    </>}
   </section>}
   {physicalManual && physicalReviewSource !== 'packs' && <button className="primary-button" disabled={busy || !physicalReview.draft.title.trim() || physicalReview.draft.kind === 'game' && (!physicalReview.draft.platform.trim() || physicalReview.draft.platform === '__custom__')} onClick={addManualPhysical}>{physicalReview.candidates.length ? 'Add as a separate library title' : 'Confirm and add physical item'}</button>}
   <button className="subtle-button physical-review-back" disabled={busy} onClick={() => backToPhysicalDetails(true)}><ArrowLeft size={16}/>Back to item details</button>
  </>}
  {physicalReview && physicalChoice && <>
   <div className="physical-merge-summary"><span><strong>Selected library title</strong><small>{physicalChoice.item.title}{physicalChoice.item.year ? ` (${physicalChoice.item.year})` : ''} · {kindNames[physicalChoice.item.kind]}</small></span><span><strong>Physical item you are adding</strong><small>{physicalReview.draft.format}{physicalReview.draft.edition ? ` · ${physicalReview.draft.edition}` : ''}{physicalReview.draft.location ? ` · ${physicalReview.draft.location}` : ''}{physicalReview.draft.barcode ? ` · barcode ${physicalReview.draft.barcode}` : ''}</small></span></div>
   <div className="physical-existing-sources"><strong>Already linked to this title</strong><p>{physicalChoice.item.sources.length ? physicalChoice.item.sources.map(source => `${source.type === 'physical' ? `${source.label} physical copy` : source.type === 'local' ? 'Blank Box file' : source.type === 'digital' ? 'Indexed file' : ['plex', 'jellyfin', 'emby'].includes(source.type) ? source.label : `${source.label} source`}${source.location ? ` at ${source.location}` : ''}`).join(' · ') : 'No sources yet'}</p></div>
   <div className="physical-edition-options" role="group" aria-label="Choose how to add this physical item"><button type="button" disabled={!compatiblePhysicalVersions.length} className={physicalChoice.mode === 'same' ? 'selected' : ''} aria-pressed={physicalChoice.mode === 'same'} onClick={() => setPhysicalChoice({ ...physicalChoice, mode: 'same', versionId: compatiblePhysicalVersions[0].id })}><strong>Another owned copy of this edition</strong><small>{compatiblePhysicalVersions.length ? 'Use the same format and edition already recorded on this title. The owned-copy count increases.' : 'No existing physical edition has this format and edition.'}</small></button><button type="button" className={physicalChoice.mode === 'new' ? 'selected' : ''} aria-pressed={physicalChoice.mode === 'new'} onClick={() => setPhysicalChoice({ ...physicalChoice, mode: 'new' })}><strong>Add a different format or edition</strong><small>Create a separate edition and a new physical copy under this library title.</small></button></div>
   {physicalChoice.mode === 'new' ? <p className="muted small">This creates {physicalReview.draft.format}{physicalReview.draft.edition ? ` · ${physicalReview.draft.edition}` : ''} on this title and adds one owned copy. Use Back to item details to change the format or edition.</p> : physicalChoice.mode === 'same' ? <label className="field"><span>Which existing edition is this copy of?</span><select value={physicalChoice.versionId} onChange={event => setPhysicalChoice({ ...physicalChoice, versionId: event.target.value })}>{compatiblePhysicalVersions.map(version => <option key={version.id} value={version.id}>{version.label}</option>)}</select><small>Only the new owned copy is added to this edition. Existing files and service links remain.</small></label> : <p className="muted small">Choose how this physical copy belongs under the selected title.</p>}
   <div className="duplicate-review-actions physical-choice-actions"><button className="subtle-button" disabled={busy} onClick={() => setPhysicalChoice(null)}><ArrowLeft size={16}/>Back to matches</button><button className="primary-button" disabled={busy || !physicalChoice.mode || physicalChoice.mode === 'same' && !physicalChoice.versionId} onClick={() => void attachPhysical()}>{physicalChoice.mode === 'new' ? 'Create edition and add copy' : physicalChoice.mode === 'same' ? 'Add another owned copy' : 'Choose how to add'}</button></div>
  </>}
 </DialogContent></Dialog>
 <Dialog open={!!justAddedPhysical} onOpenChange={open => { if (!open && justAddedPhysical)
        requestPhysicalCancel(justAddedPhysical); }}><DialogContent className="form-dialog import-match-dialog"><DialogHeader><DialogTitle>Added to your Physical Media</DialogTitle><DialogDescription>Choose how you want to finish this record.</DialogDescription></DialogHeader><div className="import-match-actions"><button className="import-choice match-choice" onClick={() => { if (justAddedPhysical) {
        setIntakeChoice(justAddedPhysical);
        setEditorOrigin('intake');
        openMatch(justAddedPhysical, justAddedPhysical.title);
        setJustAddedPhysical(null);
    } }}><Search size={20}/><span><strong>Find a matching title</strong><small>Search Offline Metapacks and connected catalogs. Review a result before applying it.</small></span><ChevronRight size={17}/></button><button className="import-choice" onClick={() => { if (justAddedPhysical) {
        setIntakeChoice(justAddedPhysical);
        setPersonalDetails(justAddedPhysical);
        setJustAddedPhysical(null);
    } }}><Disc3 size={20}/><span><strong>Enter details yourself</strong><small>Keep this physical copy local and add your own title details without choosing a match.</small></span><ChevronRight size={17}/></button></div></DialogContent></Dialog>
 <Dialog open={!!personalDetails} onOpenChange={open => { if (!open && personalDetails)
        requestPhysicalCancel(personalDetails); }}><DialogContent className="form-dialog import-match-dialog"><DialogHeader><DialogTitle>Personal or local media</DialogTitle><DialogDescription>Your copy is safely cataloged. Would you like to add details now?</DialogDescription></DialogHeader><div className="import-match-actions"><button className="import-choice match-choice" onClick={() => { if (personalDetails) {
        openEditor(personalDetails, 'intake');
        setPersonalDetails(null);
    } }}><Check size={20}/><span><strong>Add your own details</strong><small>Add a description, year, genre, or physical location. Matching remains optional.</small></span><ChevronRight size={17}/></button><button className="import-choice" onClick={() => { if (personalDetails) {
        setSelected(personalDetails);
        setPersonalDetails(null);
        setIntakeChoice(null);
    } }}><Disc3 size={20}/><span><strong>Keep it as entered</strong><small>You can edit this record later from its details screen.</small></span><ChevronRight size={17}/></button></div></DialogContent></Dialog>
 <Dialog open={!!pendingPhysicalCancel} onOpenChange={open => !open && setPendingPhysicalCancel(null)}><DialogContent className="form-dialog import-match-dialog"><DialogHeader><DialogTitle>Cancel this physical import?</DialogTitle><DialogDescription>This only affects the new Physical Media record you just created.</DialogDescription></DialogHeader><p className="muted">No disc, file, connected catalog, or existing media item will be changed.</p><div className="duplicate-review-actions cancel-import-actions"><button className="primary-button" disabled={busy} onClick={() => { if (pendingPhysicalCancel) {
        if (!catalogEditor)
            setJustAddedPhysical(pendingPhysicalCancel);
        setPendingPhysicalCancel(null);
    } }}>Keep this copy</button><button className="danger-button" disabled={busy} onClick={() => void cancelPhysicalImport()}>Cancel import</button></div></DialogContent></Dialog>
 <Dialog open={onboarding} onOpenChange={open => { if (open)
        setOnboarding(true);
    else if (state.settings.setupDone)
        cancelSetup(); }}><DialogContent className="form-dialog onboarding-dialog" showCloseButton={state.settings.setupDone}>{setupContent}</DialogContent></Dialog>
 <Toaster position="bottom-right" richColors theme="dark"/>
 </SidebarProvider>;
}
