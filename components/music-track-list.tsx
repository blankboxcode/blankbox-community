'use client';

import {useState} from 'react';
import type {MediaItem,MediaSource} from '@/lib/media';

export function MusicTrackList({item,source,busy,onPlaySource}:{item:MediaItem;source:MediaSource;busy:boolean;onPlaySource:(source:MediaSource)=>void}) {
  const catalog=source.musicCatalog;
  const discs=[...new Set(catalog?.tracks.map(row=>row.disc)||[])].sort((a,b)=>a-b);
  const [disc,setDisc]=useState(discs[0]||1);
  const [offset,setOffset]=useState(0);
  const selected=discs.includes(disc)?disc:discs[0];
  const tracks=catalog?.tracks.filter(row=>row.disc===selected)||[];
  return <section className="item-album-tracks"><div className="item-detail-section-heading"><div><h3>Album tracks</h3><p>{source.label}{catalog?` · ${catalog.trackCount} tracks`:''}</p></div></div>
    {discs.length>1&&<div className="item-catalog-navigation" aria-label="Album discs">{discs.map(value=><button data-tv className="text-button" type="button" key={value} aria-pressed={value===selected} onClick={()=>{setDisc(value);setOffset(0);}}>Disc {value}</button>)}</div>}
    {!!tracks.length&&<ol className="item-page-file-list" start={offset+1}>{tracks.slice(offset,offset+25).map(track=><li key={track.providerItemId}><span><small>{discs.length>1?`Disc ${track.disc} · `:''}{track.number?`Track ${track.number}`:'Track'}</small>{track.title}{track.duration&&<small>{Math.floor(track.duration/60)}:{String(track.duration%60).padStart(2,'0')}</small>}</span><button data-tv type="button" className="text-button" disabled={busy||source.available===false} onClick={()=>onPlaySource({...source,url:`/api/playback/source/${encodeURIComponent(item.id)}/${encodeURIComponent(source.id!)}/${encodeURIComponent(track.providerItemId)}`})}>Open track</button></li>)}</ol>}
    {tracks.length>25&&<div className="collection-paging"><button type="button" disabled={!offset} onClick={()=>setOffset(Math.max(0,offset-25))}>Previous tracks</button><span>{offset+1}–{Math.min(offset+25,tracks.length)} of {tracks.length}</span><button type="button" disabled={offset+25>=tracks.length} onClick={()=>setOffset(offset+25)}>Next tracks</button></div>}
    {!tracks.length&&!busy&&<p className="muted small">No track details are available from this source yet.</p>}
  </section>;
}
