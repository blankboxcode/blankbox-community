'use client';
/* eslint-disable @next/next/no-img-element -- Artwork can come from private local services that Next image optimization cannot access. */

import { ArrowUpRight, Check, Disc3, Globe2, Heart, Images, Info, MapPin, Pencil, RefreshCw, Search, ShieldCheck, Ticket, Trash2, X } from 'lucide-react';
import { useRef, useState } from 'react';
import { MediaActionIcon } from '@/components/media-action-icon';
import { MediaKindIcon, mediaKindLabels } from '@/components/media-kind-icon';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { FindAnotherCopy } from '@/components/find-another-copy';
import { MediaCatalogDetails } from '@/components/media-catalog-details';
import { KnownEditions } from '@/components/known-editions';
import { CatalogIdentitySummary } from '@/components/catalog-identity-summary';
import { safeServiceUrl } from '@/lib/streaming-services';
import { StreamingSearchLinks } from '@/components/where-to-find';
import { VersionsAndEditions } from '@/components/versions-and-editions';
import { ItemActivityPanel } from '@/components/item-activity';
import { ExternalDiscPlayback } from '@/components/external-disc-playback';
import { TvSeriesOrganizer } from '@/components/tv-series-organizer';
import { formatsByKind } from '@/lib/collecting-formats';
import { mediaLength, mediaTrackCount, preferredPlaybackSource, type MediaItem, type MediaSource, type StreamingService, type ServiceLink } from '@/lib/media';

type Props={serviceLinks?:ServiceLink[];onActivityChange:()=>void;item:MediaItem;opticalDrive?:string;streamingServices:StreamingService[];retailEnabled:boolean;metadataEnabled:boolean;busy:boolean;playable:boolean;playLabel:string;refreshable:boolean;onClose:()=>void;onPlay:()=>void;onPlaySource:(source:MediaSource)=>void;onRemoveSource:(source:MediaSource)=>void;onRefresh:()=>void;onFavorite:()=>void;onEdit:()=>void;onRemove:()=>Promise<boolean>};

function ItemArtwork({item}:{item:MediaItem}) {
 const [selectedId,setSelectedId]=useState('cover');
 const gallery=item.artworkGallery||[];
 const selected=gallery.find(image=>image.id===selectedId)||(!item.poster?gallery.find(image=>image.primary)||gallery[0]:undefined);
 const url=selected?.url||item.poster;
 const label=selected?.label||`${item.title} cover`;
 const edition=selected?.releaseId?item.sources.find(source=>source.physicalReleaseId===selected.releaseId):undefined;
 const thumbnails=[...(item.poster?[{id:'cover',url:item.poster,label:'Main cover'}]:[]),...gallery.filter(image=>image.url!==item.poster)];
 return <aside className={`item-artwork-panel kind-${item.kind}`} aria-label="Item artwork">
  {url?<a className="item-artwork-main" href={url} target="_blank" rel="noopener noreferrer" aria-label={`View full artwork: ${label}`}><img src={url} alt={label}/><span><Images size={15}/>View full artwork<ArrowUpRight size={14}/></span></a>:<div className="item-artwork-placeholder"><MediaKindIcon kind={item.kind} size={64} strokeWidth={1.2}/><span>{mediaKindLabels[item.kind]}</span></div>}
  {thumbnails.length>1&&<div className="item-artwork-thumbnails" role="group" aria-label="Choose artwork">{thumbnails.map(image=><button type="button" key={image.id} className={(selected?.id||selectedId)===image.id?'selected':''} aria-label={`Show ${image.label}`} title={image.label} aria-pressed={(selected?.id||selectedId)===image.id} onClick={()=>setSelectedId(image.id)}><img src={image.url} alt="" loading="lazy"/></button>)}</div>}
  {selected&&<div className="item-artwork-caption" aria-live="polite"><strong>{selected.label}</strong><span>{selected.role}{selected.primary?' · Main cover':''}</span>{edition&&<small>{[edition.edition,edition.packaging,edition.releaseLabel].filter(Boolean).join(' · ')||edition.label}</small>}</div>}
  {!url&&!item.sample&&<p className="item-artwork-note">Add a cover or edition artwork in Edit details.</p>}
 </aside>;
}

export function MediaDetailDialog({serviceLinks,item,onActivityChange,opticalDrive,streamingServices,retailEnabled,metadataEnabled,busy,playable,playLabel,refreshable,onClose,onPlay,onPlaySource,onRemoveSource,onRefresh,onFavorite,onEdit,onRemove}:Props) {
 const [findFormat,setFindFormat]=useState('Any');
 const [descriptionOpen,setDescriptionOpen]=useState(false);
 const sourcesPanel=useRef<HTMLElement>(null);
 const aboutPanel=useRef<HTMLDivElement>(null);
 const findPanel=useRef<HTMLElement>(null);
 const physical=item.sources.filter(source=>source.type==='physical');
 const local=item.sources.filter(source=>source.type==='local');
 const linkedFiles=item.sources.filter(source=>source.type==='digital');
 const preferred=preferredPlaybackSource(item);
 const ownedCopyCount=new Set(physical.map((source,index)=>source.ownedCopyId||source.id||String(index))).size;
 const physicalFormats=[...new Set(physical.map(source=>source.label))];
 const locations=[...new Set(physical.map(source=>source.location).filter(Boolean))];
 const applicableStreamingServices=item.kind==='movie'||item.kind==='tv'?streamingServices.filter(service=>service!=='spotify'):item.kind==='music'?streamingServices.filter(service=>service==='spotify'||service==='youtube'):[];
 const applicableServiceLinks=serviceLinks?.filter(service=>item.kind==='movie'||item.kind==='tv'?service.id!=='spotify':item.kind==='music'?(service.id==='spotify'||service.id==='youtube'||service.id.startsWith('custom-')):false);
 const hasStoreSearch=retailEnabled&&!!formatsByKind[item.kind];
 const canFind=!item.sample&&(hasStoreSearch||(applicableServiceLinks?.length??applicableStreamingServices.length)>0);
 const description=item.description||'';
 const connectedOnly=item.sources.length>0&&item.sources.every(source=>['jellyfin','plex'].includes(source.type));
 const sourceHeading=item.kind==='book'||item.kind==='comic'?'Sources & reading':item.kind==='file'||item.kind==='game'||item.kind==='photo'?'Sources & access':'Sources & playback';
 const jumpTo=(panel:HTMLElement|null)=>{panel?.scrollIntoView({block:'start',behavior:'auto'});panel?.focus({preventScroll:true});};
 const showFind=(format='Any')=>{setFindFormat(format);jumpTo(findPanel.current);};
 const remove=async()=>{
  const managed=local.length>0,mixed=item.sources.length>1;
  const message=managed?'Remove this item and its Blank Box-managed copy? The original source file will not be changed. Verified backups may still retain a copy.':connectedOnly?'Hide this item from Blank Box? It will stay hidden after future provider syncs and can be restored from Settings. The connected service and its files will not be changed.':mixed?'Remove this entire catalog item and all of its Blank Box source links? Connected services, original files, and physical media will not be changed.':'Remove this catalog record from Blank Box? The connected service or physical media will not be changed.';
  if(window.confirm(message)&&await onRemove())onClose();
 };
 return <Dialog open onOpenChange={open=>!open&&onClose()}><DialogContent className="detail-dialog item-detail-dialog item-detail-polished" showCloseButton={false}>
  <div className="item-detail-toolbar"><span><MediaKindIcon kind={item.kind} size={17}/>{mediaKindLabels[item.kind]} details{item.sample&&<small>Sample</small>}</span><nav aria-label="Jump to item section"><button type="button" onClick={()=>jumpTo(sourcesPanel.current)}>Sources</button><button type="button" onClick={()=>jumpTo(aboutPanel.current)}>Details</button>{canFind&&<button type="button" onClick={()=>showFind()}>Find more</button>}</nav><button className="item-detail-close" type="button" aria-label="Close item details" title="Close" onClick={onClose}><X size={20}/></button></div>
  <div className="item-detail-body"><div className="item-detail-layout">
   <ItemArtwork item={item}/>
   <div className="item-detail-content">
    <header className="item-detail-intro"><span className={`item-detail-kind kind-${item.kind}`}><MediaKindIcon kind={item.kind} size={15}/>{mediaKindLabels[item.kind]}</span><DialogHeader><DialogTitle>{item.title}</DialogTitle><DialogDescription>{[item.artist,item.year,item.catalogDetails?.contentRating,mediaLength(item)||null,mediaTrackCount(item)?`${mediaTrackCount(item)} tracks`:null].filter(Boolean).join(' · ')||'Your Blank Box library'}</DialogDescription></DialogHeader>
     {item.genre&&<p className="item-detail-genre">{item.genre}</p>}
     <div className="item-detail-actions">{playable&&<button className="primary-button" type="button" onClick={onPlay}><MediaActionIcon item={item} source={preferred} size={17}/>{playLabel}</button>}{!item.sample&&<button className="subtle-button" type="button" onClick={onEdit}><Pencil size={15}/>Edit details</button>}<button className={`item-detail-favorite ${item.favorite?'selected':''}`} type="button" aria-label={item.favorite?'Remove from favorites':'Add to favorites'} aria-pressed={!!item.favorite} title={item.favorite?'Remove from favorites':'Add to favorites'} onClick={onFavorite}><Heart size={19} fill={item.favorite?'currentColor':'none'}/></button></div>
     {description&&<div className="item-detail-synopsis"><p id="item-description" className={`item-detail-description ${!descriptionOpen?'clamped':''}`}>{description}</p>{description.length>220&&<button className="item-detail-read-more" type="button" aria-expanded={descriptionOpen} aria-controls="item-description" onClick={()=>setDescriptionOpen(!descriptionOpen)}>{descriptionOpen?'Show less':'Read more'}</button>}</div>}
     {!item.sample&&ownedCopyCount>0&&<div className="item-collection-summary"><span><Disc3 size={16}/>{ownedCopyCount} physical {ownedCopyCount===1?'copy':'copies'}</span><span>{physicalFormats.join(' · ')}</span>{locations.length>0&&<span><MapPin size={14}/>{locations.slice(0,2).join(' · ')}{locations.length>2?` +${locations.length-2}`:''}</span>}</div>}
    </header>
    <section ref={sourcesPanel} tabIndex={-1} className="item-detail-sources item-detail-block" aria-label={sourceHeading}>
     <div className="item-detail-section-heading"><div><h3><MediaActionIcon item={item} source={preferred} size={19}/>{sourceHeading}</h3><p>{item.sample?'Preview sources for this sample.':'Open a file or connected app, or see the copies on your shelf.'}</p></div>{refreshable&&<button className="text-button" type="button" disabled={busy} onClick={onRefresh}><RefreshCw size={14}/>{busy?'Refreshing…':'Refresh'}</button>}</div>
     <VersionsAndEditions item={item} onPlaySource={onPlaySource} onRemoveSource={onRemoveSource}/>
     {!item.sources.length&&<div className="item-source-empty"><MediaKindIcon kind={item.kind} size={24}/><div><strong>No sources added yet</strong><p>Add a physical copy or link a file in Edit details.</p></div>{!item.sample&&<button className="subtle-button" type="button" onClick={onEdit}><Pencil size={14}/>Add a source</button>}</div>}
     {local.length>0&&<p className={`item-source-note ${item.backup==='verified'?'verified':''}`}><ShieldCheck size={14}/>{item.backup==='verified'?'Managed-file backup verified.':'Managed-file backup has not been verified for this item.'}{item.backup==='verified'&&item.backupVerifiedAt&&<span>Checked {new Date(item.backupVerifiedAt).toLocaleDateString()}.</span>}</p>}
     {linkedFiles.length>0&&<p className="item-source-note"><Info size={14}/>Linked files stay on their drives. Recovery restores their records, not missing originals.</p>}
     <ExternalDiscPlayback item={item} drive={opticalDrive}/>
    </section>
    {!item.sample&&!!item.digitalPlatforms?.length&&<section className="item-detail-block item-digital-copies" aria-label="Digital copies and codes"><div className="item-detail-section-heading"><div><h3><Globe2 size={19}/>Digital copies & codes</h3><p>Purchases and codes you recorded for this title.</p></div></div><div className="item-digital-grid">{item.digitalPlatforms.map(record=>{const url=safeServiceUrl(record.url);const copy=physical.find(source=>source.id===record.physicalSourceId);return <article className="item-digital-card" key={record.id}><span className="item-digital-icon"><Globe2 size={19}/></span><div><strong>{record.platform}</strong><span className={`item-digital-status ${record.status}`}>{record.status==='code-included'?<Ticket size={12}/>:<Check size={12}/>}{{purchased:'Purchased',redeemed:'Redeemed','code-included':'Code included'}[record.status]}</span>{copy&&<small>{[copy.label,copy.packaging,copy.releaseLabel].filter(Boolean).join(' · ')}</small>}{record.notes&&<p>{record.notes}</p>}{url&&<a href={url} target="_blank" rel="noopener noreferrer">Open platform<ArrowUpRight size={14}/></a>}</div></article>;})}</div><p className="item-source-note">A saved purchase or code does not verify playback access. Included codes may still need redeeming.</p></section>}
    {!item.sample&&item.kind==='tv'&&<TvSeriesOrganizer key={item.id} item={item} activityEnabled={metadataEnabled} onActivityChange={onActivityChange} onPlaySource={onPlaySource}/>}
    <div ref={aboutPanel} tabIndex={-1} className="item-detail-block item-about-block"><MediaCatalogDetails item={item} busy={busy} showEmpty onRefresh={refreshable?onRefresh:undefined}/>{!item.sample&&metadataEnabled&&item.kind!=='tv'&&<ItemActivityPanel key={item.id} item={item} onChange={onActivityChange}/>}</div>
    {canFind&&<section ref={findPanel} tabIndex={-1} className="item-detail-block item-detail-find" aria-label="Find more copies"><div className="item-detail-section-heading"><div><h3><Search size={19}/>Find more</h3><p>{hasStoreSearch?'Explore editions and search the services you use.':'Search the services you use for this title.'}</p></div></div>{hasStoreSearch&&<FindAnotherCopy key={`${item.id}:${findFormat}`} item={item} initialFormat={findFormat}/>}<StreamingSearchLinks item={item} streamingServices={applicableStreamingServices} serviceLinks={applicableServiceLinks}/></section>}
    {!item.sample&&metadataEnabled&&<KnownEditions item={item} onFind={showFind}/>}
    {!item.sample&&metadataEnabled&&<CatalogIdentitySummary item={item}/>}
    {!item.sample&&<section className="item-detail-manage"><div><strong>{connectedOnly?'Hide this item':'Remove this item'}</strong><p>{connectedOnly?'Keep it out of Blank Box after future service syncs.':'Review the confirmation before removing its catalog record and links.'}</p></div><button className="danger-button" type="button" disabled={busy} onClick={()=>void remove()}><Trash2 size={15}/>{connectedOnly?'Hide item':'Remove item'}</button></section>}
   </div>
  </div></div>
  {item.credit&&<p className="credit">{item.credit} <a href="/credits" target="_blank" rel="noopener noreferrer">Artwork credits & licenses</a></p>}
 </DialogContent></Dialog>;
}
