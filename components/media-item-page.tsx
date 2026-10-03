'use client';
/* eslint-disable @next/next/no-img-element -- Private artwork uses authenticated Core URLs. */

import {ArrowUpRight,Check,Disc3,Globe2,Heart,Images,Info,MapPin,Pencil,Plus,RefreshCw,Ticket,Trash2} from 'lucide-react';
import {useRef,useState} from 'react';
import {MediaActionIcon} from '@/components/media-action-icon';
import {MediaKindIcon,mediaKindLabels} from '@/components/media-kind-icon';
import {MediaCatalogDetails} from '@/components/media-catalog-details';
import {ItemActivityPanel} from '@/components/item-activity';
import {TvSeriesOrganizer} from '@/components/tv-series-organizer';
import {FindAnotherCopy} from '@/components/find-another-copy';
import {KnownEditions} from '@/components/known-editions';
import {CatalogIdentitySummary} from '@/components/catalog-identity-summary';
import {ExternalDiscPlayback} from '@/components/external-disc-playback';
import {StreamingSearchLinks} from '@/components/where-to-find';
import {fileTitle} from '@/components/media-file-sections';
import {formatsByKind} from '@/lib/collecting-formats';
import {safeServiceUrl} from '@/lib/streaming-services';
import {editionArtwork,itemEditions,itemPlaybackGroups,type ItemEdition} from '@/lib/item-presentation';
import type {CatalogEditFocus} from '@/lib/catalog-edit';
import {digitalFileFormat,isConnectedPlaybackSource,isPlayableSource,mediaLength,mediaTrackCount,preferredPlaybackSource,sourceActionLabel,type MediaItem,type MediaSource,type ServiceLink,type StreamingService} from '@/lib/media';

type Props={item:MediaItem;opticalDrive?:string;streamingServices:StreamingService[];serviceLinks?:ServiceLink[];retailEnabled:boolean;metadataEnabled:boolean;busy:boolean;playable:boolean;playLabel:string;refreshable:boolean;onBack:()=>void;onPlay:()=>void;onPlaySource:(source:MediaSource)=>void;onRemoveSource:(source:MediaSource)=>void;onRefresh:()=>void;onFavorite:()=>void;onEdit:(focus:CatalogEditFocus)=>void;onAddPhysical?:()=>void;onActivityChange:()=>void;onRemove:()=>Promise<boolean>};

function ItemArtwork({item,edition,onEdit}:{item:MediaItem;edition?:ItemEdition;onEdit:()=>void}) {
  const gallery=editionArtwork(item,edition?.releaseId||'');
  const [selectedId,setSelectedId]=useState(gallery[0]?.id||'cover');
  const selected=gallery.find(image=>image.id===selectedId)||(selectedId!=='cover'?gallery[0]:undefined);
  const url=selected?.url||item.poster;
  const label=selected?.label||`${item.title} title cover`;
  const images=[...gallery,...(item.poster&&!gallery.some(image=>image.url===item.poster)?[{id:'cover',url:item.poster,label:'Title cover',role:'cover'}]:[])];
  return <aside className={`item-page-artwork kind-${item.kind}`} aria-label="Item artwork">
    {url?<a className="item-page-cover" href={url} target="_blank" rel="noopener noreferrer" aria-label={`View full artwork: ${label}`}><img src={url} alt={label}/><span><Images size={15}/>View full image<ArrowUpRight size={13}/></span></a>:<div className="item-page-cover item-page-cover-empty"><MediaKindIcon kind={item.kind} size={64}/><span>No artwork yet</span></div>}
    {images.length>1&&<div className="item-page-thumbnails" role="group" aria-label="Choose artwork">{images.map(image=><button data-tv type="button" key={image.id} aria-label={`Show ${image.label}`} aria-pressed={image.id===selectedId} onClick={()=>setSelectedId(image.id)} title={image.label}><img src={image.url} alt="" loading="lazy"/><span>{image.role[0].toUpperCase()+image.role.slice(1)}</span></button>)}</div>}
    {selected&&<p className="item-page-art-caption">{selected.label}</p>}
    {!item.sample&&<button data-tv className="subtle-button item-page-art-edit" type="button" onClick={onEdit}><Images size={16}/>Edit artwork</button>}
  </aside>;
}

function Playback({item,onPlaySource,onRemoveSource,onEditFiles,busy}:{item:MediaItem;onPlaySource:(source:MediaSource)=>void;onRemoveSource:(source:MediaSource)=>void;onEditFiles:(sourceId?:string)=>void;busy:boolean}) {
  const groups=itemPlaybackGroups(item);
  const connected=item.sources.filter(source=>isConnectedPlaybackSource(source)||source.type==='demo');
  const preferred=preferredPlaybackSource(item);
  const [expanded,setExpanded]=useState<string|null>(null);
  if(!groups.length&&!connected.length)return <p className="item-page-muted">No playable files or connected apps added yet.</p>;
  return <div className="item-page-playback-list">
    {groups.map(group=>{
      const first=group.sources.find(isPlayableSource);
      const single=group.sources.length===1;
      const label=single?fileTitle(item,group.sources[0]):group.label;
      const action=first?sourceActionLabel(item,first):'';
      return <div className="item-page-playback-group" key={group.key}>
        <div className="item-page-playback-row"><MediaActionIcon item={item} source={first||group.sources[0]} size={21}/><div><strong>{label}</strong><small>{single?digitalFileFormat(group.sources[0]):`${group.sources.length} ${item.kind==='music'?'tracks':item.kind==='tv'?'files / episodes':'files'}`} · {group.sources.every(source=>source.type==='local')?'Managed files':group.sources.every(source=>source.type==='digital')?'Linked files':'Managed & linked files'}{!first?' · Unavailable':''}</small></div>{first&&<button data-tv className="subtle-button" type="button" disabled={busy} onClick={()=>onPlaySource(first)}><MediaActionIcon item={item} source={first} size={15}/>{single?action:item.kind==='music'?'Play album':item.kind==='tv'?'Play first episode':'Open first file'}</button>}{!item.sample&&<button data-tv className="item-page-icon-button" type="button" disabled={busy} aria-label={`Edit ${label} files`} title="Edit files" onClick={()=>onEditFiles(group.sources[0]?.id)}><Pencil size={16}/></button>}</div>
        {!single&&<><button data-tv type="button" className="text-button item-page-file-toggle" aria-expanded={expanded===group.key} aria-controls={`item-files-${group.key}`} onClick={()=>setExpanded(expanded===group.key?null:group.key)}>{expanded===group.key?'Hide':item.kind==='music'?'Show tracks':item.kind==='tv'?'Show episode files':'Show files'}{expanded===group.key?' files':''} ({group.sources.length})</button>{expanded===group.key&&<ol id={`item-files-${group.key}`} className="item-page-file-list">{group.sources.map((source,index)=><li key={source.id||`${source.path}-${index}`}><span>{fileTitle(item,source)}{source.available===false&&<small>Unavailable</small>}</span>{isPlayableSource(source)&&<button data-tv className="text-button" type="button" disabled={busy} onClick={()=>onPlaySource(source)}><MediaActionIcon item={item} source={source} size={15}/>{sourceActionLabel(item,source)}</button>}{source.id&&<button className="item-page-icon-button" type="button" disabled={busy} aria-label={`Remove ${fileTitle(item,source)} source`} title="Remove source" onClick={()=>onRemoveSource(source)}><Trash2 size={15}/></button>}</li>)}</ol>}</>}
        {single&&!item.sample&&group.sources[0].id&&<button className="text-button item-page-source-remove" type="button" disabled={busy} onClick={()=>onRemoveSource(group.sources[0])}>{group.sources[0].type==='local'?'Remove managed copy':'Remove file link'}</button>}
      </div>;
    })}
    {connected.map((source,index)=><div className="item-page-playback-row" key={source.id||`${source.type}-${index}`}><MediaActionIcon item={item} source={source} size={21}/><div><strong>{source.label}</strong><small>{source.available===false?'Unavailable':source===preferred?'Main playback choice':isPlayableSource(source)?'Connected app':'Playback link unavailable'}</small></div>{isPlayableSource(source)&&<button data-tv className="subtle-button" type="button" disabled={busy} onClick={()=>onPlaySource(source)}>{sourceActionLabel(item,source)}<ArrowUpRight size={14}/></button>}{!item.sample&&source.id&&<button className="item-page-icon-button" type="button" disabled={busy} aria-label={`Remove ${source.label} source`} title="Remove source" onClick={()=>onRemoveSource(source)}><Trash2 size={15}/></button>}</div>)}
  </div>;
}

export function MediaItemPage({item,opticalDrive,streamingServices,serviceLinks,retailEnabled,metadataEnabled,busy,playable,playLabel,refreshable,onBack,onPlay,onPlaySource,onRemoveSource,onRefresh,onFavorite,onEdit,onAddPhysical,onActivityChange,onRemove}:Props) {
  const editions=itemEditions(item);
  const [editionSelection,setEditionSelection]=useState({id:editions[0]?.id||'',sourceId:editions[0]?.sources[0]?.id});
  const edition=editions.find(row=>editionSelection.sourceId&&row.sources.some(source=>source.id===editionSelection.sourceId))||editions.find(row=>row.id===editionSelection.id)||editions[0];
  const [section,setSection]=useState<'information'|'activity'|'discover'>('information');
  const [descriptionOpen,setDescriptionOpen]=useState(false);
  const [findFormat,setFindFormat]=useState('Any');
  const heading=useRef<HTMLHeadingElement>(null);
  const secondary=useRef<HTMLElement>(null);
  const preferred=preferredPlaybackSource(item);
  const physical=item.sources.filter(source=>source.type==='physical');
  const local=item.sources.filter(source=>source.type==='local');
  const linked=item.sources.filter(source=>source.type==='digital');
  const connectedOnly=item.sources.length>0&&item.sources.every(source=>['jellyfin','plex'].includes(source.type));
  const detailsSource=item.metadataPreference==='blankbox'?'Blank Box':item.sources.find(source=>source.id===item.metadataPreference)?.label||'Saved title details';
  const applicableStreamingServices=streamingServices.filter(service=>item.kind==='music'?['spotify','youtube'].includes(service):['movie','tv'].includes(item.kind)&&service!=='spotify');
  const applicableServiceLinks=serviceLinks?.filter(service=>item.kind==='music'?service.id==='spotify'||service.id==='youtube'||service.id.startsWith('custom-'):['movie','tv'].includes(item.kind)&&service.id!=='spotify');
  const hasSearch=(applicableServiceLinks?.length??applicableStreamingServices.length)>0;
  const canDiscover=!item.sample&&(retailEnabled&&!!formatsByKind[item.kind]||metadataEnabled);
  const showFind=(format='Any')=>{setFindFormat(format);setSection('discover');requestAnimationFrame(()=>secondary.current?.scrollIntoView({block:'start',behavior:'instant'}));};
  const remove=async()=>{
    const warning=local.length?'Remove this item and its Blank Box-managed copy? The original source file will not be changed. Verified backups may still retain a copy.':connectedOnly?'Hide this item from Blank Box? It stays hidden after future syncs. The connected service and its files will not be changed.':'Remove this catalog item and its source links? Original files, physical media and connected services will not be changed.';
    if(window.confirm(warning)&&await onRemove())onBack();
  };
  return <article className={`media-item-page kind-${item.kind}`} aria-labelledby="media-item-title">
    <div className="item-page-navigation"><span><MediaKindIcon kind={item.kind} size={16}/>{mediaKindLabels[item.kind]}{item.sample?' · Sample':''}</span></div>
    <div className="item-page-layout">
      <ItemArtwork key={edition?.id||'title'} item={item} edition={edition} onEdit={()=>onEdit({section:'artwork',releaseId:edition?.releaseId||''})}/>
      <div className="item-page-content">
        <header className="item-page-header"><div className="item-page-heading"><h1 id="media-item-title" tabIndex={-1} ref={heading}>{item.title}</h1><button data-tv className={`item-page-icon-button item-page-favorite ${item.favorite?'selected':''}`} type="button" aria-label={item.favorite?'Remove from favorites':'Add to favorites'} aria-pressed={!!item.favorite} disabled={busy} onClick={onFavorite}><Heart size={21} fill={item.favorite?'currentColor':'none'}/></button></div>
          <p className="item-page-meta">{[item.artist,item.year,item.catalogDetails?.contentRating,mediaLength(item),mediaTrackCount(item)?`${mediaTrackCount(item)} tracks`:null].filter(Boolean).join(' · ')||mediaKindLabels[item.kind]}</p>
        </header>
          <div className="item-page-main-actions">{playable&&<button data-tv className="primary-button" type="button" disabled={busy} onClick={onPlay}><MediaActionIcon item={item} source={preferred} size={18}/>{playLabel}</button>}{!item.sample&&<button data-tv className="subtle-button" type="button" disabled={busy} onClick={()=>onEdit({section:'title'})}><Pencil size={16}/>Edit title details</button>}</div>
          {!item.sample&&<div className="item-page-details-source"><span>Details from <strong>{detailsSource}</strong></span><button data-tv className="text-button" type="button" disabled={busy} onClick={()=>onEdit({section:'metadata'})}>Choose details source</button></div>}
          {item.description&&<div className="item-page-description"><p className={descriptionOpen?'':'clamped'}>{item.description}</p>{item.description.length>220&&<button className="text-button" type="button" aria-expanded={descriptionOpen} onClick={()=>setDescriptionOpen(!descriptionOpen)}>{descriptionOpen?'Show less':'Read more'}</button>}</div>}
        <section className="item-page-section item-page-playback" aria-label="Playback and access"><div className="item-page-section-heading"><h2><MediaActionIcon item={item} source={preferred} size={20}/>{item.kind==='book'||item.kind==='comic'?'Read & listen':item.kind==='music'?'Listen':['movie','tv','home-video'].includes(item.kind)?'Watch':'Open & access'}</h2>{refreshable&&<button data-tv className="text-button" type="button" disabled={busy} onClick={onRefresh}><RefreshCw size={14}/>{busy?'Refreshing…':'Refresh'}</button>}</div><Playback item={item} busy={busy} onPlaySource={onPlaySource} onRemoveSource={onRemoveSource} onEditFiles={sourceId=>onEdit({section:'files',sourceId})}/></section>
        {!item.sample&&<section className="item-page-section item-page-editions" aria-label="Your editions"><div className="item-page-section-heading"><h2><Disc3 size={20}/>Your editions <small>{editions.length||''}</small></h2>{onAddPhysical&&<button data-tv className="text-button" type="button" disabled={busy} onClick={onAddPhysical}><Plus size={16}/>Add physical copy</button>}</div>
          {editions.length?<><div className="item-page-edition-picker" role="group" aria-label="Choose edition">{editions.map(row=>{const cover=editionArtwork(item,row.releaseId)[0]?.url||item.poster;return <button data-tv type="button" key={row.id} aria-pressed={edition?.id===row.id} className={edition?.id===row.id?'selected':''} onClick={()=>setEditionSelection({id:row.id,sourceId:row.sources[0]?.id})}>{cover?<img src={cover} alt="" loading="lazy"/>:<MediaKindIcon kind={item.kind} size={26}/>}<span><strong>{row.label}</strong><small>{row.subtitle}</small><em>{row.physical?`${row.sources.length} physical ${row.sources.length===1?'copy':'copies'}`:'Digital files'}</em></span></button>;})}</div>
            {edition&&<div className="item-page-selected-edition" aria-label="Selected edition"><div className="item-page-selected-heading"><strong>{edition.label}</strong><span>{edition.subtitle}</span></div>{edition.physical?<div className="item-page-copy-list">{edition.sources.map((source,index)=><div key={source.id||index}><div><span><MapPin size={15}/>{source.location||'Location not recorded'}</span><small>{[source.condition,edition.sources.length>1?`Copy ${index+1}`:''].filter(Boolean).join(' · ')}</small></div>{source.id&&<button data-tv className="subtle-button" type="button" disabled={busy} onClick={()=>{setEditionSelection({id:edition.id,sourceId:source.id});onEdit({section:'physical',sourceId:source.id});}}><Pencil size={14}/>Edit this copy</button>}{source.id&&<button className="item-page-icon-button" type="button" disabled={busy} aria-label={`Remove ${source.label} copy ${index+1}`} title="Remove this copy" onClick={()=>onRemoveSource(source)}><Trash2 size={15}/></button>}</div>)}</div>:<div className="item-page-edition-file-summary"><span>{edition.sources.length} linked or managed {edition.sources.length===1?'file':'files'} · Playback options above</span><button data-tv className="text-button" type="button" disabled={busy} onClick={()=>onEdit({section:'files',sourceId:edition.sources[0]?.id})}>Edit files</button></div>}</div>}
          </>:<p className="item-page-muted">No physical editions or file editions recorded. Connected apps remain available above.</p>}
        </section>}
        {!item.sample&&['movie','tv'].includes(item.kind)&&<section className="item-page-section item-page-digital" aria-label="Digital purchases and codes"><div className="item-page-section-heading"><h2><Globe2 size={20}/>Digital purchases & codes</h2><button data-tv className="text-button" type="button" disabled={busy} onClick={()=>onEdit({section:'digital'})}><Plus size={15}/>{item.digitalPlatforms?.length?'Edit records':'Add record'}</button></div>{item.digitalPlatforms?.length?<div className="item-page-platforms">{item.digitalPlatforms.map(record=>{const url=safeServiceUrl(record.url);const copy=physical.find(source=>source.id===record.physicalSourceId);return <div key={record.id}><Globe2 size={20}/><span><strong>{record.platform}</strong><small>{record.status==='code-included'?<Ticket size={12}/>:<Check size={12}/>}{{purchased:'Purchased',redeemed:'Redeemed','code-included':'Code included'}[record.status]}{copy?` · ${[copy.label,copy.packaging].filter(Boolean).join(' · ')}`:''}</small>{record.notes&&<small>{record.notes}</small>}</span>{url&&<a data-tv className="text-button" href={url} target="_blank" rel="noopener noreferrer">Open platform<ArrowUpRight size={14}/></a>}</div>;})}</div>:<p className="item-page-muted">Record a purchase, redeemed code or code included with a physical copy.</p>} {!!item.digitalPlatforms?.length&&<p className="item-page-footnote">Saved records do not verify playback access. Included codes may still need redeeming.</p>}</section>}
        {!item.sample&&hasSearch&&<section className="item-page-section item-page-services" aria-label="Search streaming services"><StreamingSearchLinks item={item} streamingServices={applicableStreamingServices} serviceLinks={applicableServiceLinks}/></section>}
        {!item.sample&&item.kind==='tv'&&<div className="item-page-section"><TvSeriesOrganizer key={item.id} item={item} activityEnabled={metadataEnabled} onActivityChange={onActivityChange} onPlaySource={onPlaySource}/></div>}
        <section className="item-page-secondary" ref={secondary} aria-label="More item information"><div className="item-page-tabs" role="tablist" aria-label="Item information">{(['information',...(!item.sample&&metadataEnabled?['activity']:[]),...(canDiscover?['discover']:[])] as typeof section[]).map(tab=><button data-tv role="tab" type="button" id={`item-tab-${tab}`} aria-selected={section===tab} aria-controls={`item-panel-${tab}`} tabIndex={section===tab?0:-1} key={tab} onClick={()=>setSection(tab)} onKeyDown={event=>{const tabs=Array.from(event.currentTarget.parentElement!.querySelectorAll<HTMLButtonElement>('[role=tab]'));const index=tabs.indexOf(event.currentTarget);const next=event.key==='ArrowRight'?tabs[(index+1)%tabs.length]:event.key==='ArrowLeft'?tabs[(index+tabs.length-1)%tabs.length]:event.key==='Home'?tabs[0]:event.key==='End'?tabs.at(-1):null;if(next){event.preventDefault();next.click();next.focus();}}}>{tab==='information'?'Information':tab==='activity'?'Activity':'Find more'}</button>)}</div>
          <div className="item-page-tab-panel" role="tabpanel" id={`item-panel-${section}`} aria-labelledby={`item-tab-${section}`} tabIndex={0}>
            {section==='information'&&<><MediaCatalogDetails item={item} busy={busy} showEmpty onRefresh={refreshable?onRefresh:undefined}/>{edition?.physical&&<div className="item-page-edition-facts"><h3>Selected edition details</h3>{edition.sources.map((source,index)=><div key={source.id||index}>{edition.sources.length>1&&<strong>Copy {index+1} · {source.location||'Location not recorded'}</strong>}<dl>{([['Edition',source.edition],['Packaging',source.packaging],['Release label',source.releaseLabel],['Barcode',source.barcode],['Region',source.region],['Platform',source.platform],['Catalog number',source.catalogNumber],['Credits',source.creator],['Publisher',source.publisher],['Volume',source.volume],['Issue',source.issue],['Grade',source.grade],['Signed',source.signed],['Certificate',source.certificate],['Recorded price',source.listedPrice]] as [string,string|undefined][]).filter(([,value])=>value).map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl></div>)}</div>}<ExternalDiscPlayback item={item} drive={opticalDrive}/>{!item.sample&&metadataEnabled&&<CatalogIdentitySummary item={item}/>} {!!local.length&&<p className="item-page-footnote"><Info size={14}/>{item.backup==='verified'?'Managed-file backup verified.':'Managed-file backup has not been verified for this item.'}</p>}{!!linked.length&&<p className="item-page-footnote">Linked files stay on their drives. Recovery restores their records, not missing originals.</p>}</>}
            {section==='activity'&&<ItemActivityPanel key={item.id} item={item} onChange={onActivityChange}/>}
            {section==='discover'&&<>{retailEnabled&&!!formatsByKind[item.kind]&&<FindAnotherCopy key={`${item.id}:${findFormat}`} item={item} initialFormat={findFormat}/>} {metadataEnabled&&<KnownEditions item={item} onFind={showFind}/>}<p className="item-page-muted">Reference editions and store searches do not add copies to your collection.</p></>}
          </div>
        </section>
        {!item.sample&&<details className="item-page-management"><summary>Manage this item</summary><div><p>{connectedOnly?'Hide this title from Blank Box after future connected-service syncs.':'Remove the catalog item and review what happens to its sources.'}</p><button className="danger-button" type="button" disabled={busy} onClick={()=>void remove()}><Trash2 size={15}/>{connectedOnly?'Hide item':'Remove item'}</button></div></details>}
      </div>
    </div>
    {item.credit&&<p className="credit">{item.credit} <a href="/credits" target="_blank" rel="noopener noreferrer">Artwork credits & licenses</a></p>}
  </article>;
}
