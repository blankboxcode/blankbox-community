'use client';
/* eslint-disable @next/next/no-img-element -- Artwork can come from private local services that Next image optimization cannot access. */

import { BookOpen, Check, Disc3, Film, FolderOpen, Gamepad2, HardDrive, Heart, Images, Music2, Pencil, RefreshCw, Search, Server, ShieldCheck, Trash2, X } from 'lucide-react';
import { useRef, useState } from 'react';
import { MediaActionIcon } from '@/components/media-action-icon';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { FindAnotherCopy } from '@/components/find-another-copy';
import { MediaCatalogDetails } from '@/components/media-catalog-details';
import { KnownEditions } from '@/components/known-editions';
import { CatalogIdentitySummary } from '@/components/catalog-identity-summary';
import { StreamingSearchLinks } from '@/components/where-to-find';
import { VersionsAndEditions } from '@/components/versions-and-editions';
import { ItemActivityPanel } from '@/components/item-activity';
import { ExternalDiscPlayback } from '@/components/external-disc-playback';
import { MediaFileSections } from '@/components/media-file-sections';
import { TvSeriesOrganizer } from '@/components/tv-series-organizer';
import { formatsByKind } from '@/lib/collecting-formats';
import { mediaFileGroups, mediaLength, mediaTrackCount, kindNames, preferredPlaybackSource, sourceSummaryCount, type MediaItem, type MediaSource, type StreamingService } from '@/lib/media';

type Props={onActivityChange:()=>void;item:MediaItem;opticalDrive?:string;streamingServices:StreamingService[];retailEnabled:boolean;metadataEnabled:boolean;busy:boolean;playable:boolean;playLabel:string;refreshable:boolean;onClose:()=>void;onPlay:()=>void;onPlaySource:(source:MediaSource)=>void;onRemoveSource:(source:MediaSource)=>void;onRefresh:()=>void;onFavorite:()=>void;onEdit:()=>void;onRemove:()=>Promise<boolean>};
type DetailView='overview'|'sources'|'find';

function ItemArtwork({item}:{item:MediaItem}){
 const Icon=item.kind==='movie'||item.kind==='tv'?Film:item.kind==='music'?Music2:item.kind==='book'||item.kind==='comic'?BookOpen:item.kind==='game'?Gamepad2:item.kind==='photo'||item.kind==='home-video'?Images:FolderOpen;
 return item.poster?<img className="item-detail-art" src={item.poster} alt=""/>:<div className={`item-detail-art item-detail-art-empty kind-${item.kind}`}><Icon size={46} strokeWidth={1.3}/><span>{kindNames[item.kind].replace(/s$/,'')}</span></div>;
}

export function MediaDetailDialog({item,onActivityChange,opticalDrive,streamingServices,retailEnabled,metadataEnabled,busy,playable,playLabel,refreshable,onClose,onPlay,onPlaySource,onRemoveSource,onRefresh,onFavorite,onEdit,onRemove}:Props){
 const[view,setView]=useState<DetailView>('overview');
 const[findFormat,setFindFormat]=useState('Any');
 const[descriptionOpen,setDescriptionOpen]=useState(false);
 const[overviewExpanded,setOverviewExpanded]=useState(false);
 const overviewPanel=useRef<HTMLDivElement>(null);
 const physical=item.sources.filter(source=>source.type==='physical');
 const local=item.sources.filter(source=>source.type==='local');
 const linked=item.sources.filter(source=>source.type==='digital'||source.type==='catalog');
 const linkedFiles=linked.filter(source=>source.type==='digital');
 const linkedGroups=mediaFileGroups({...item,sources:linkedFiles});
 const fileUnit=item.kind==='tv'?'episodes':item.kind==='music'?'tracks':item.kind==='book'?'book files':'files';
 const connected=item.sources.filter(source=>['jellyfin','plex','emby'].includes(source.type));
 const preferred=preferredPlaybackSource(item);
 const reading=item.kind==='book'||item.kind==='comic';
 const opening=item.kind==='file'||item.kind==='game';
 const noSource=reading?'No reading source on this item':opening?'No file available to open':item.kind==='photo'?'No photo available to view':'No playable source on this item';
 const formatCopies=new Map<string,Set<string>>();
 physical.forEach((source,index)=>{const copies=formatCopies.get(source.label)||new Set<string>();copies.add(source.ownedCopyId||source.id||String(index));formatCopies.set(source.label,copies);});
 const formats=[...formatCopies].map(([format,copies])=>[format,copies.size] as const);
 const ownedCopyCount=new Set(physical.map((source,index)=>source.ownedCopyId||source.id||String(index))).size;
 const applicableStreamingServices=item.kind==='movie'||item.kind==='tv'?streamingServices.filter(service=>service!=='spotify'):item.kind==='music'?streamingServices.filter(service=>service==='spotify'||service==='youtube'):[];
 const hasStoreSearch=retailEnabled&&!!formatsByKind[item.kind];
 const canFind=!item.sample&&(hasStoreSearch||applicableStreamingServices.length>0);
 const description=item.description||'';
 const connectedOnly=item.sources.length>0&&item.sources.every(source=>['jellyfin','plex'].includes(source.type));
 const remove=async()=>{
  const managed=local.length>0,mixed=item.sources.length>1;
  const message=managed?'Remove this item and its Blank Box-managed copy? The original source file will not be changed. Verified backups may still retain a copy.':connectedOnly?'Hide this item from Blank Box? It will stay hidden after future provider syncs and can be restored from Settings. The connected service and its files will not be changed.':mixed?'Remove this entire catalog item and all of its Blank Box source links? Connected services, original files, and physical media will not be changed.':'Remove this catalog record from Blank Box? The connected service or physical media will not be changed.';
  if(window.confirm(message)&&await onRemove())onClose();
 };
 const showFind=(format='Any')=>{setFindFormat(format);setView('find');};
 return <Dialog open onOpenChange={open=>!open&&onClose()}><DialogContent className={`detail-dialog item-detail-dialog ${view!=='overview'||overviewExpanded?'item-detail-dialog-expanded':''}`} showCloseButton={false}>
  <div className="item-detail-hero">
   <ItemArtwork item={item}/>
   <div className="item-detail-intro"><span className="item-detail-kind">{kindNames[item.kind]}{item.sample?' · Sample':''}</span><DialogHeader><DialogTitle>{item.title}</DialogTitle><DialogDescription>{[item.artist,item.catalogDetails?.contentRating,mediaTrackCount(item)?`${mediaTrackCount(item)} tracks`:null,item.year,item.genre,mediaLength(item)||null].filter(Boolean).join(' · ')}</DialogDescription></DialogHeader>
    {description&&<p id="item-description" tabIndex={descriptionOpen?0:undefined} aria-label="Item description" className={`item-detail-description ${!descriptionOpen?'clamped':''}`}>{description}</p>}
    {description.length>175&&<button className="item-detail-read-more" type="button" aria-expanded={descriptionOpen} aria-controls="item-description" onClick={()=>setDescriptionOpen(!descriptionOpen)}>{descriptionOpen?'Show less':'Read description'}</button>}
    <div className="item-detail-actions">{playable?<button className="primary-button" type="button" onClick={onPlay}><MediaActionIcon item={item} source={preferred} size={16}/>{playLabel}</button>:canFind&&<button className="primary-button" type="button" onClick={()=>showFind()}><Search size={16}/>Search for More</button>}{!item.sample&&<button className="subtle-button" type="button" onClick={onEdit}><Pencil size={16}/>Edit details</button>}<button className={`item-detail-favorite ${item.favorite?'selected':''}`} type="button" aria-label={item.favorite?'Remove from favorites':'Add to favorites'} aria-pressed={!!item.favorite} title={item.favorite?'Remove from favorites':'Add to favorites'} onClick={onFavorite}><Heart size={19} fill={item.favorite?'currentColor':'none'}/></button></div>
   </div>
  </div>
  <div className={`item-detail-nav ${canFind?'has-find':''}`} aria-label="Item sections"><button type="button" className={view==='overview'?'active':''} aria-pressed={view==='overview'} onClick={()=>{setView('overview');setOverviewExpanded(false);overviewPanel.current?.scrollTo({top:0});}}>Overview</button><button type="button" className={view==='sources'?'active':''} aria-pressed={view==='sources'} onClick={()=>setView('sources')}>Sources <span>{sourceSummaryCount(item)}</span></button>{canFind&&<button type="button" className={view==='find'?'active':''} aria-pressed={view==='find'} onClick={()=>showFind()}>Find more</button>}<button type="button" className="item-detail-close" aria-label="Close item details" title="Close" onClick={onClose}><X size={19}/></button></div>
  {view==='overview'&&<div ref={overviewPanel} className="item-detail-panel" onScroll={event=>{if(event.currentTarget.scrollTop>12)setOverviewExpanded(true);}} onWheel={event=>{if(event.deltaY>12)setOverviewExpanded(true);}}><div className="item-detail-section-heading"><div><h3>{item.sample?'About this sample':'What you have'}</h3><p>{item.sample?'A preview of how media appears in your library.':'Physical ownership, local files, and connected catalogs stay distinct.'}</p></div>{item.backup==='verified'&&local.length>0&&<span className="item-detail-protection" title={item.backupVerifiedAt?`Checked ${new Date(item.backupVerifiedAt).toLocaleString()}`:'Verified backup recorded'}><ShieldCheck size={15}/>Managed-file backup verified</span>}</div>
   {!item.sample&&<div className="item-detail-ownership">
    <div className="item-detail-ownership-card physical"><div className="item-detail-card-heading"><span><Disc3 size={20}/></span><div><strong>Physical Media</strong><small>{ownedCopyCount?`${ownedCopyCount} owned ${ownedCopyCount===1?'copy':'copies'}`:'No physical copy recorded'}</small></div></div>{formats.length?<div className="item-detail-format-list">{formats.map(([format,count])=><span key={format}><Check size={13}/>{format}{count>1?` ×${count}`:''}</span>)}</div>:<p className="item-detail-empty-note">Add a copy when you have it on your shelf.</p>}{physical.length>0&&<small className="item-detail-location">{[...new Set(physical.map(source=>source.location).filter(Boolean))].slice(0,2).join(' · ')||'Location not recorded'}</small>}</div>
    <div className="item-detail-ownership-card access"><div className="item-detail-card-heading"><span>{preferred?<MediaActionIcon item={item} source={preferred} size={19}/>:<HardDrive size={19}/>}</span><div><strong>{preferred?'Ready to use':'Digital access'}</strong><small>{preferred?`Preferred: ${preferred.type==='local'?'Blank Box file':preferred.type==='digital'?'Linked file':preferred.label}`:noSource}</small></div></div><div className="item-detail-access-tags">{local.length>0&&<span><HardDrive size={13}/>{local.length} managed {item.discImport?'tracks':fileUnit}</span>}{linkedFiles.length>0&&<span><FolderOpen size={13}/>{linkedFiles.length} linked {fileUnit} in {linkedGroups.length} {linkedGroups.length===1?'group':'groups'}</span>}{linked.some(source=>source.type==='catalog')&&<span><FolderOpen size={13}/>{linked.filter(source=>source.type==='catalog').length} catalog references</span>}{connected.map(source=><span key={source.id||source.label}><Server size={13}/>{source.label}</span>)}{!local.length&&!linked.length&&!connected.length&&<span>No digital source linked</span>}</div>{item.backup!=='verified'&&local.length>0&&<small className="item-detail-backup-note">Managed-file backup has not been verified for this item.</small>}{linkedFiles.length>0&&<small className="item-detail-backup-note">Linked files stay on their source drives; library recovery points keep their records, not their bytes.</small>}</div>
   </div>}
   {item.sample&&<p className="item-detail-empty-note">Sample media is here to demonstrate the library. It does not count as an owned copy.</p>}
   {!item.sample&&item.kind!=='tv'&&<MediaFileSections item={item}/>}
   {!item.sample&&metadataEnabled&&item.kind!=='tv'&&<ItemActivityPanel key={item.id} item={item} onChange={onActivityChange}/>}
   <MediaCatalogDetails item={item} busy={busy} onRefresh={refreshable?onRefresh:undefined}/>
   {!item.sample&&item.kind==='tv'&&<TvSeriesOrganizer key={item.id} item={item} activityEnabled={metadataEnabled} onActivityChange={onActivityChange} onPlaySource={onPlaySource}/>}
   <button type="button" className="item-detail-section-link" onClick={()=>setView('sources')}>See every edition and source <span>→</span></button>
  </div>}
  {view==='sources'&&<div className="item-detail-panel item-detail-sources"><div className="item-detail-section-heading"><div><h3>Copies & sources</h3><p>Each edition and its physical, local, or connected sources.</p></div>{refreshable&&<button className="subtle-button" type="button" disabled={busy} onClick={onRefresh}><RefreshCw size={15}/>Refresh connections</button>}</div><ExternalDiscPlayback item={item} drive={opticalDrive}/><VersionsAndEditions item={item} onPlaySource={onPlaySource} onRemoveSource={onRemoveSource}/>{!item.sample&&metadataEnabled&&<KnownEditions item={item} onFind={showFind}/>}{!item.sample&&metadataEnabled&&<CatalogIdentitySummary item={item}/>}{!item.sample&&<StreamingSearchLinks item={item} streamingServices={applicableStreamingServices}/>}{!item.sample&&<section className="item-detail-manage"><div><strong>{connectedOnly?'Hide this item':'Remove this item'}</strong><p>{connectedOnly?'Keep it out of Blank Box after future service syncs. The connected service and its files stay unchanged.':'Remove its Blank Box catalog record and links. Review the confirmation before proceeding.'}</p></div><button className="danger-button" type="button" disabled={busy} onClick={()=>void remove()}><Trash2 size={16}/>{connectedOnly?'Hide from Blank Box':item.sources.length>1?'Remove entire item':'Remove from Blank Box'}</button></section>}</div>}
  {view==='find'&&canFind&&<div className="item-detail-panel item-detail-find"><div className="item-detail-section-heading"><div><h3>{hasStoreSearch?'Find another edition':'Search your services'}</h3><p>{hasStoreSearch?'Search by format, then confirm the exact listing at the store.':'Open a service search to check its current catalog.'}</p></div></div>{hasStoreSearch&&<FindAnotherCopy key={`${item.id}:${findFormat}`} item={item} initialFormat={findFormat}/>}<StreamingSearchLinks item={item} streamingServices={applicableStreamingServices}/></div>}
  {item.credit&&<p className="credit">{item.credit} <a href="/credits" target="_blank" rel="noopener noreferrer">Artwork credits & licenses</a></p>}
 </DialogContent></Dialog>;
}
