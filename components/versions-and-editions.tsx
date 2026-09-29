'use client';

import { BookOpen, ChevronDown, Disc3, Film, FolderArchive, Gamepad2, HardDrive, Headphones, Images, Music2, Server, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { MediaActionIcon } from '@/components/media-action-icon';
import { fileTitle } from '@/components/media-file-sections';
import { digitalFileFormat, sharedReleaseCredits, preferredSourceLabel, sourceActionLabel, isAudiobookSource, isPlayableSource, mediaFileGroups, mediaVersions, preferredPlaybackSource, sourceEpisodeNumber, sourceTrackNumber, sourcesForVersion, type MediaItem, type MediaSource } from '@/lib/media';
import { physicalFormatLabel } from '@/lib/physical-media';

type Props={item:MediaItem;onPlaySource:(source:MediaSource)=>void;onRemoveSource:(source:MediaSource)=>void};

function sourceDetail(source:MediaSource,item:MediaItem,versionLabel=''){
 const shared=sharedReleaseCredits(item);
 const creator=source.creator&&source.creator!==shared.creator?`Edition credits: ${source.creator}`:null;
 const publisher=source.publisher&&source.publisher!==shared.publisher?`Edition publisher: ${source.publisher}`:null;
 if(source.type==='physical')return [source.location||'Physical location not entered',source.edition&&!versionLabel.toLocaleLowerCase().includes(source.edition.toLocaleLowerCase())?source.edition:null,source.season&&!versionLabel.includes(source.season)?source.season==='complete-series'?'Complete series':source.season==='specials'?'Specials':`Season ${source.season}`:null,source.platform,source.volume&&`Volume ${source.volume}`,source.issue&&`Issue ${source.issue}`,source.condition,source.region,source.grade&&`Grade ${source.grade}`,source.signed&&`Signed: ${source.signed}`,source.certificate&&`COA: ${source.certificate}`,source.barcode&&`Barcode ${source.barcode}`,creator,publisher,source.catalogNumber&&`Catalog ${source.catalogNumber}`,source.listedPrice&&`Recorded price ${source.listedPrice}`].filter(Boolean).join(' · ');
 if(source.type==='local'||source.type==='digital')return [digitalFileFormat(source),source.edition&&!versionLabel.toLocaleLowerCase().includes(source.edition.toLocaleLowerCase())?source.edition:null,creator,publisher,source.platform,source.volume&&`Volume ${source.volume}`,source.issue&&`Issue ${source.issue}`,source.region,source.catalogNumber&&`Catalog ${source.catalogNumber}`,source.barcode&&`Release ID ${source.barcode}`,source.available===false?'File unavailable on this installation':source.trackTitle||source.path||'Blank Box storage'].filter(Boolean).join(' · ');
 if(source.type==='jellyfin'||source.type==='plex'||source.type==='emby')return 'Connected catalog · Opens in the source app';
 if(source.type==='catalog')return source.path||'Catalog reference';
 if(source.available===false)return `${source.path||source.location||'Linked file'} · Unavailable on this installation`;
 return source.path||source.location||'Available source';
}

function SourceIcon({source,item}:{source:MediaSource;item:MediaItem}){
 if(item.kind==='book'&&isAudiobookSource(source))return <Headphones/>;
 if(source.type==='physical'){
  const Icon=item.kind==='game'?Gamepad2:item.kind==='book'||item.kind==='comic'?BookOpen:item.kind==='music'?Music2:item.kind==='photo'||item.kind==='home-video'?Images:item.kind==='movie'||item.kind==='tv'?Film:Disc3;
  return <Icon/>;
 }
 if(source.type==='local')return <HardDrive/>;
 if(source.type==='jellyfin'||source.type==='plex'||source.type==='emby')return <Server/>;
 return <FolderArchive/>;
}

export function VersionsAndEditions({item,onPlaySource,onRemoveSource}:Props){
 const versions=mediaVersions(item);
 const preferred=preferredPlaybackSource(item);
 if(item.kind==='tv'){
  const files=item.sources.filter(source=>source.type==='local'||source.type==='digital');
  const connected=item.sources.filter(source=>source.type==='jellyfin'||source.type==='plex'||source.type==='emby');
  const references=item.sources.filter(source=>source.type==='catalog');
  const physical=versions.map(version=>({version,sources:sourcesForVersion(item,version.id).filter(source=>source.type==='physical')})).filter(row=>row.sources.length);
  return <section className="versions-editions"><div className="edition-list">
   {files.length>0&&<EditionCard key="local-files" item={item} label="Local files" sources={files} preferred={preferred} initiallyOpen={false} onPlaySource={onPlaySource} onRemoveSource={onRemoveSource}/>}
   {connected.length>0&&<EditionCard key="connected" item={item} label="Connected catalogs" sources={connected} preferred={preferred} initiallyOpen={false} onPlaySource={onPlaySource} onRemoveSource={onRemoveSource}/>}
   {physical.map(({version,sources})=><EditionCard key={version.id} item={item} label={version.label==='Standard or unknown edition'?sources[0]?.label||version.label:version.label} year={version.year} sources={sources} preferred={preferred} initiallyOpen={false} onPlaySource={onPlaySource} onRemoveSource={onRemoveSource}/>)}
   {references.length>0&&<EditionCard key="references" item={item} label="Metadata references" sources={references} preferred={preferred} initiallyOpen={false} onPlaySource={onPlaySource} onRemoveSource={onRemoveSource}/>}
  </div></section>;
 }
 const audioCards=item.kind==='book'?versions.map(version=>({version,sources:sourcesForVersion(item,version.id).filter(isAudiobookSource)})).filter(row=>row.sources.length):[];
 return <section className="versions-editions"><div className="edition-list">{versions.map((version,index)=>{
  const sources=sourcesForVersion(item,version.id).filter(source=>item.kind!=='book'||!isAudiobookSource(source)).sort((left,right)=>left===preferred?-1:right===preferred?1:0);
  if(!sources.length&&audioCards.length)return null;
  const physical=sources.filter(source=>source.type==='physical');
  const known=new Set(physical.map(source=>[source.label,source.edition,source.season==='complete-series'?'Complete series':source.season==='specials'?'Specials':source.season?`Season ${source.season}`:''].filter(Boolean).join(' · ')));
  const baseLabel=version.label==='Standard or unknown edition'&&physical.length===sources.length&&known.size===1?[...known][0]:version.label;
  const seasonLabel=version.season==='complete-series'?'Complete series':version.season==='specials'?'Specials':version.season?`Season ${version.season}`:'';
  const label=seasonLabel&&!baseLabel.includes(seasonLabel)?`${baseLabel} · ${seasonLabel}`:baseLabel;
  return <EditionCard key={version.id} item={item} label={label} year={version.year} sources={sources} preferred={preferred} initiallyOpen={index===0&&sources.length<=5} onPlaySource={onPlaySource} onRemoveSource={onRemoveSource}/>;
 })}{audioCards.map(({version,sources})=><EditionCard key={`${version.id}-audiobook`} item={item} label={version.label==='Standard or unknown edition'?'Audiobook':`${version.label} · Audiobook`} year={version.year} sources={sources} preferred={preferred} initiallyOpen onPlaySource={onPlaySource} onRemoveSource={onRemoveSource}/>)}</div></section>;
}

function EditionCard({item,label,year,sources,preferred,initiallyOpen,onPlaySource,onRemoveSource}:{item:MediaItem;label:string;year?:number;sources:MediaSource[];preferred?:MediaSource;initiallyOpen:boolean;onPlaySource:Props['onPlaySource'];onRemoveSource:Props['onRemoveSource']}){
 const[open,setOpen]=useState(initiallyOpen);
 const physicalRows=sources.filter(source=>source.type==='physical');
 const physical=new Set(physicalRows.map((source,index)=>source.ownedCopyId||source.id||String(index))).size;
 const tracks=item.kind==='music'?sources.filter(source=>sourceTrackNumber(source)).length:0;
 const episodes=item.kind==='tv'?sources.filter(source=>sourceEpisodeNumber(source)).length:0;
 const audiobook=item.kind==='book'?sources.filter(isAudiobookSource).length:0;
 const other=sources.length-physicalRows.length-tracks-episodes-audiobook;
 const summary=[physical?`${physical} physical ${physical===1?'copy':'copies'}`:'',tracks?`${tracks} tracks`:'',episodes?`${episodes} episodes`:'',audiobook?`${audiobook} audiobook ${audiobook===1?'file':'files'}`:'',other?`${other} other ${other===1?'source':'sources'}`:''].filter(Boolean).join(' · ')||'No sources';
 const fileGroups=mediaFileGroups({...item,sources});
 const otherSources=sources.filter(source=>source.type!=='local'&&source.type!=='digital');
 return <article className="edition-card"><button className="edition-card-toggle" type="button" aria-expanded={open} onClick={()=>setOpen(!open)}><span><strong>{label}</strong><small>{[year,summary].filter(Boolean).join(' · ')}</small></span><ChevronDown size={18} className={open?'open':''}/></button>
  {open&&<div className="edition-sources">{otherSources.map(source=><SourceRow key={source.id||`${source.type}-${source.label}`} item={item} source={source} versionLabel={label} preferred={preferred} onPlaySource={onPlaySource} onRemoveSource={onRemoveSource}/>)}{fileGroups.map(group=>group.sources.length>1?<SourceGroup key={group.key} item={item} label={group.label} sources={group.sources} versionLabel={label} preferred={preferred} onPlaySource={onPlaySource} onRemoveSource={onRemoveSource}/>:group.sources.map(source=><SourceRow key={source.id||source.path} item={item} source={source} versionLabel={label} preferred={preferred} onPlaySource={onPlaySource} onRemoveSource={onRemoveSource}/>))}</div>}
 </article>;
}

function SourceGroup({item,label,sources,versionLabel,preferred,onPlaySource,onRemoveSource}:{item:MediaItem;label:string;sources:MediaSource[];versionLabel:string;preferred?:MediaSource;onPlaySource:Props['onPlaySource'];onRemoveSource:Props['onRemoveSource']}){
 const[open,setOpen]=useState(false);
 const ordered=[...sources].sort((a,b)=>(item.kind==='tv'?sourceEpisodeNumber(a)-sourceEpisodeNumber(b):item.kind==='music'?sourceTrackNumber(a)-sourceTrackNumber(b):0)||(a.path||'').localeCompare(b.path||'',undefined,{numeric:true}));
 return <details className="edition-source-group" onToggle={event=>setOpen(event.currentTarget.open)}><summary>{label} · {sources.length} files</summary>{open&&ordered.map(source=><SourceRow key={source.id||source.path} item={item} source={source} versionLabel={versionLabel} preferred={preferred} onPlaySource={onPlaySource} onRemoveSource={onRemoveSource}/>)}</details>;
}

function SourceRow({item,source,versionLabel,preferred,onPlaySource,onRemoveSource}:{item:MediaItem;source:MediaSource;versionLabel:string;preferred?:MediaSource;onPlaySource:Props['onPlaySource'];onRemoveSource:Props['onRemoveSource']}){
 const playable=isPlayableSource(source),isPreferred=source===preferred;
 const name=source.type==='physical'&&source.label==='Game'?physicalFormatLabel('Game'):source.type==='local'||source.type==='digital'?fileTitle(item,source):source.label;
 return <div className="edition-source"><span className={`find-icon ${source.type==='physical'?'physical':playable?'ready':''}`}><SourceIcon source={source} item={item}/></span><span><strong>{name}</strong><small>{sourceDetail(source,item,versionLabel)}{isPreferred?` · ${preferredSourceLabel(item.kind)}`:''}</small></span><div className="edition-source-actions">{playable&&<button className="source-action" type="button" onClick={()=>onPlaySource(source)}><MediaActionIcon item={item} source={source}/> {sourceActionLabel(item,source)}</button>}{source.type!=='demo'&&source.id&&<button className="source-action remove" type="button" aria-label={`Remove ${name} source`} title="Remove this source" onClick={()=>onRemoveSource(source)}><Trash2/>Remove</button>}</div></div>;
}
