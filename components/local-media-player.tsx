'use client';
/* eslint-disable @next/next/no-img-element -- User media is served by authenticated Core routes. */
import { useState } from 'react';
import { ArrowUpRight } from 'lucide-react';
import { DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { digitalFileFormat, isAudiobookSource, isConnectedPlaybackSource, isPlayableSource, type MediaItem, type MediaSource } from '@/lib/media';

export function LocalMediaPlayer({item,source,url,alternatives,onProgress}:{item:MediaItem;source?:MediaSource;url:string;alternatives:MediaSource[];onProgress:(progress:number)=>void}){
 const [failed,setFailed]=useState(false);
 const audiobook=item.kind==='book'&&!!source&&isAudiobookSource(source);
 const playbackMime=audiobook&&/\.m4b$/i.test(source?.path||'')?'audio/mp4':source?.mime;
 const [support]=useState(()=>typeof document!=='undefined'&&playbackMime&&(['movie','tv','home-video'].includes(item.kind)||audiobook)?document.createElement(audiobook?'audio':'video').canPlayType(playbackMime):'unknown');
 const providers=alternatives.filter(row=>isConnectedPlaybackSource(row)&&isPlayableSource(row));
 const video=['movie','tv','home-video'].includes(item.kind);
 const reading=item.kind==='book'||item.kind==='comic';
 const action=video?'Playing':audiobook?'Listening':item.kind==='photo'?'Viewing':reading?'Reading / opening':'Opening';
 return <><DialogHeader><DialogTitle>{item.title}</DialogTitle><DialogDescription>{item.sample&&video?'Open movie preview. Playback depends on the external media host.':`${action} in Blank Box${source?` · ${digitalFileFormat(source)}`:''}.${video||audiobook?' Browser support depends on the file’s container and codecs.':''}`}</DialogDescription></DialogHeader>
 {item.kind==='photo'?<img className="photo-player" src={url||item.poster} alt={item.title} onError={()=>setFailed(true)}/>:video?<video src={url} controls autoPlay playsInline onError={()=>setFailed(true)} onLoadedMetadata={event=>{setFailed(false);if(item.progress&&Number.isFinite(event.currentTarget.duration))event.currentTarget.currentTime=event.currentTarget.duration*item.progress;}} onPause={event=>{const player=event.currentTarget;if(Number.isFinite(player.duration)&&player.duration>0)onProgress(Math.min(player.currentTime/player.duration,1));}}/>:audiobook?<audio className="audiobook-player" src={url} controls preload="metadata" onError={()=>setFailed(true)} onLoadedMetadata={event=>{setFailed(false);const position=source?.playbackProgress;if(position&&Number.isFinite(event.currentTarget.duration))event.currentTarget.currentTime=event.currentTarget.duration*position;}} onPause={event=>{const player=event.currentTarget;if(Number.isFinite(player.duration)&&player.duration>0)onProgress(Math.min(player.currentTime/player.duration,1));}}/>:<div className="empty-panel"><p>Open this file in a compatible app on your device.</p></div>}
 {!failed&&support===''&&<p className="muted small">This browser does not report direct support for the file type. Playback is being attempted; use another player if it cannot open.</p>}
 {failed&&<div className="playback-failure" role="alert"><h3>{video||audiobook?'This file could not play in this browser':'This file could not be viewed in this browser'}</h3><p>{video||audiobook?'The format or codec may be unsupported, or the source may have become unavailable. Blank Box does not transcode this file. Try a compatible device, a connected player, or download the source for an external app.':'The file format may be unsupported, or the source may have become unavailable. Try opening the source file or downloading it for a compatible app.'}</p></div>}
 {!item.sample&&url&&<div className="playback-options"><a className="subtle-button" href={url} download>{video||audiobook?'Download for an external player':reading?'Download for a reader':'Download file'}</a><a className="text-button" href={url} target="_blank" rel="noopener noreferrer">Open source file<ArrowUpRight size={14}/></a></div>}
 {!!providers.length&&<div className="playback-options"><strong>{video?'Other playback options':reading?'Other reading options':'Other ways to open'}</strong>{providers.map(row=><a key={row.id||row.type} className="text-button" href={row.url} target="_blank" rel="noopener noreferrer">Open {row.type==='plex'?'Plex':row.type==='jellyfin'?'Jellyfin':row.label}<ArrowUpRight size={14}/></a>)}</div>}
 {item.sample&&<p className="credit">{item.credit}</p>}</>;
}
