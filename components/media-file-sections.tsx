'use client';

import { useState } from 'react';
import { isFileSource, mediaFileGroups, sourceEpisodeNumber, sourceTrackNumber, sourceQuality, type MediaItem, type MediaSource } from '@/lib/media';

function fileName(source:MediaSource){return (source.path||source.label).split(/[\\/]/).pop()||source.label;}

export function fileTitle(item:MediaItem,source:MediaSource){
 if(item.kind==='tv'&&sourceEpisodeNumber(source)){
  const number=`Episode ${sourceEpisodeNumber(source)}${source.episodeEnd?`–${source.episodeEnd}`:''}`;
  const clue=fileName(source).replace(/\.[^.]+$/,'').replace(/^.*?\bS\d{1,3}[ ._-]*E\d{1,3}(?:[ ._-]*E\d{1,3})?[ ._-]*/i,'').replace(/[._-]+/g,' ').replace(/\b(?:2160p|1080p|720p|x264|x265|hevc|web[ .-]?dl|bluray)\b.*$/i,'').trim();
  return clue&&clue!==fileName(source)?`${number} · ${clue}`:number;
 }
 if(item.kind==='music'&&sourceTrackNumber(source))return `${sourceTrackNumber(source)}. ${source.trackTitle||fileName(source).replace(/^\d{1,3}[ ._-]+/,'').replace(/\.[^.]+$/,'')}`;
 return fileName(source);
}

function FileGroup({item,label,sources}:{item:MediaItem;label:string;sources:MediaSource[]}){
 const [open,setOpen]=useState(false);
 const ordered=[...sources].sort((a,b)=>{
  const left=item.kind==='tv'?sourceEpisodeNumber(a):item.kind==='music'?sourceTrackNumber(a):0;
  const right=item.kind==='tv'?sourceEpisodeNumber(b):item.kind==='music'?sourceTrackNumber(b):0;
  return left-right||fileName(a).localeCompare(fileName(b),undefined,{numeric:true});
 });
 const unit=item.kind==='tv'?'episodes':item.kind==='music'?'tracks':'files';
 return <details className="media-file-group" onToggle={event=>setOpen(event.currentTarget.open)}><summary><span><strong>{label}</strong><small>{sources.length} {sources.length===1?unit.slice(0,-1):unit}</small></span></summary>{open&&<ol>{ordered.map((source,index)=><li key={source.id||`${source.path}-${index}`}><span title={source.path||source.label}>{fileTitle(item,source)}</span>{item.kind==='movie'&&sourceQuality(source)&&<small>{sourceQuality(source)}</small>}</li>)}</ol>}</details>;
}

export function MediaFileSections({item}:{item:MediaItem}){
 const fileCount=item.sources.filter(isFileSource).length;
 if(!fileCount||!['tv','music','book','movie'].includes(item.kind))return null;
 const groups=mediaFileGroups(item);
 return <section className="media-file-sections"><div className="item-detail-section-heading"><div><h3>{item.kind==='tv'?'Episodes on your drives':item.kind==='music'?'Album tracks':item.kind==='book'?'Book and audiobook files':'Video versions'}</h3><p>{fileCount} linked or managed {fileCount===1?'file':'files'} in {groups.length} {groups.length===1?'group':'groups'}. Originals stay on their drives.</p></div></div><div className="media-file-groups">{groups.map(group=><FileGroup key={group.key} item={item} label={group.label} sources={group.sources}/>)}</div></section>;
}
