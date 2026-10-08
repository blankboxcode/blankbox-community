'use client';
/* eslint-disable @next/next/no-img-element -- Album artwork is a user-controlled local or connected media URL. */

import { useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight, Disc3, Music2 } from 'lucide-react';
import {musicPlaybackTracks} from '@/lib/item-presentation';
import type { MediaItem, MediaSource } from '@/lib/media';

function externalUrl(value?: string) {
  if (!value) return '';
  try { const url = new URL(value); return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password ? url.href : ''; }
  catch { return ''; }
}

export function MusicPlayer({ item, previewUrl, startSourceId }: { item: MediaItem; previewUrl?: string; startSourceId?: string }) {
  const tracks = useMemo(() => {
    const sorted = musicPlaybackTracks(item,startSourceId);
    return previewUrl ? [{ id: 'preview', type: 'digital', label: 'This device', url: previewUrl, trackTitle: item.title } as MediaSource, ...sorted] : sorted;
  }, [item, previewUrl, startSourceId]);
  const initial = Math.max(0, tracks.findIndex(source => source.id === startSourceId));
  const [index, setIndex] = useState(initial);
  const [failed,setFailed]=useState(false);
  const changeTrack=(next:number)=>{setFailed(false);setIndex(next);};
  const active = tracks[index];
  const connected = item.sources.filter(source => ['jellyfin', 'plex', 'emby'].includes(source.type) && externalUrl(source.url));
  const title = (source: MediaSource, at: number) => source.trackTitle || (tracks.length === 1 ? item.title : `Track ${source.trackNumber || at + 1}`);
  return <div className="music-player">
    <div className="music-player-top"><div className="music-player-art">{item.poster ? <img src={item.poster} alt=""/> : <Music2 size={48}/>}</div><div><span className="eyebrow">YOUR MUSIC</span><h2>{item.title}</h2><p>{item.artist || (item.sources.some(source => source.type === 'physical' && source.label === 'CD') ? 'Your CD collection' : 'Your library')}</p><div className="music-player-badges">{item.sources.some(source => source.type === 'physical' && source.label === 'CD') && <span><Disc3 size={14}/>Physical CD</span>}{item.discImport?.encodingVerified && <span>Lossless FLAC · Encoding verified</span>}{item.backup === 'verified' && <span>Backup verified</span>}</div></div></div>
    {item.discImport?.format === 'WAV' && <p className="muted small">Lossless WAV import from your audio CD.</p>}
    {active ? <><div className="music-now-playing"><span>NOW PLAYING</span><strong>{title(active, index)}</strong><small>{index + 1} of {tracks.length}</small></div><audio key={active.url} src={active.url} autoPlay controls onEnded={() => setIndex(current => Math.min(current + 1, tracks.length - 1))} onError={() => setFailed(true)} onLoadedMetadata={()=>setFailed(false)}/>{failed&&<div className="playback-failure" role="alert"><strong>This track could not play in this browser</strong><p>The audio codec may be unsupported or the drive unavailable. Blank Box does not transcode it.</p>{active.url&&<a className="subtle-button" href={active.url} download>Download for an external player</a>}</div>}<div className="music-player-actions"><button className="subtle-button" disabled={index === 0} onClick={() => changeTrack(index - 1)}><ChevronLeft size={16}/>Previous</button><button className="subtle-button" disabled={index >= tracks.length - 1} onClick={() => changeTrack(index + 1)}>Next<ChevronRight size={16}/></button></div><ol className="music-track-list">{tracks.map((source, at) => <li key={source.id || at}><button className={at === index ? 'active' : ''} onClick={() => changeTrack(at)}><span>{String(source.trackNumber || at + 1).padStart(2, '0')}</span><strong>{title(source, at)}</strong><small>{source.mime === 'audio/flac' ? 'FLAC' : source.mime === 'audio/wav' ? 'WAV' : source.label}</small></button></li>)}</ol></> : <p className="muted">No local track is available for in-browser playback.</p>}
    {!!connected.length && <div className="music-connected"><strong>Play from a connected source</strong>{connected.map((source, at) => <a key={source.id || at} className="text-button" href={externalUrl(source.url)} target="_blank" rel="noopener noreferrer">Open {source.label}</a>)}</div>}
    {item.discImport && <p className="muted small">{item.discImport.format === 'FLAC' ? 'CD extraction completed. FLAC encoding was checked against the extracted audio.' : 'CD extraction completed as uncompressed WAV. Each audio block was read twice for consistency.'} Disc accuracy was not independently certified.</p>}
  </div>;
}
