'use client';

import { useState } from 'react';
import { RefreshCw } from 'lucide-react';
import type { MediaItem } from '@/lib/media';

export function MetadataSourceChoice({expanded=false,item,busy,onChoose,onRefresh}: {
  expanded?: boolean;
  item: MediaItem;
  busy: boolean;
  onChoose: (sourceId: string) => Promise<void>;
  onRefresh: () => void;
}) {
  const sources=item.sources.filter(source=>['jellyfin','plex'].includes(source.type)&&source.id);
  const [pending,setPending]=useState<string|null>(null);
  if(!sources.length&&!expanded)return null;
  const preferred=item.metadataPreference;
  const local=item.blankboxMetadataSnapshot||item;
  const choose=async(sourceId:string)=>{
    setPending(sourceId);
    try{await onChoose(sourceId);}finally{setPending(null);}
  };
  const choices=<>
    <p className="muted small">Use these details fills the available fields from that source, replacing edits to those fields. Refresh keeps later manual edits. The main playback button follows your selected Plex or Jellyfin source when usable; Blank Box details use local playback first. Other source buttons remain available. Your physical copies, files, and connected services stay unchanged.</p>
    <div className="metadata-source-options">
      <article><div><strong>Blank Box details</strong><small>{local.title||item.title}{local.year?` (${local.year})`:''} · Use the saved local details and your edits</small><small>{local.poster?.startsWith('/api/artwork/')?'Private Blank Box cover saved':'No private cover saved; a connected cover may still appear'}</small></div><button type="button" className="subtle-button" disabled={busy||!!pending||preferred==='blankbox'} onClick={()=>void choose('blankbox')}>{preferred==='blankbox'?'Selected':'Use these details'}</button></article>
      {sources.map(source=>{const snapshot=source.metadataSnapshot;const selected=preferred===source.id;const canReapply=item.metadataOverrides?.some(field=>snapshot&&(field.startsWith('catalogDetails.')?snapshot.catalogDetails?.[field.slice(15) as keyof NonNullable<typeof snapshot.catalogDetails>]!=null:snapshot[field as keyof typeof snapshot]!=null));return <article key={source.id}><div><strong>{source.label}</strong><small>{snapshot?`${snapshot.title||item.title}${snapshot.year?` (${snapshot.year})`:''}${snapshot.artist?` · ${snapshot.artist}`:''}`:'Refresh to load this source’s details'}</small>{snapshot?.description&&<small>{snapshot.description.slice(0,160)}{snapshot.description.length>160?'…':''}</small>}</div><button type="button" className="subtle-button" disabled={busy||!!pending||!snapshot||selected&&!canReapply} onClick={()=>source.id&&void choose(source.id)}>{selected&&!canReapply?'Selected':selected?'Apply details again':'Use these details'}</button></article>;})}
    </div>
    {!!sources.length&&<button type="button" className="text-button" disabled={busy||!!pending} onClick={onRefresh}><RefreshCw size={16}/>Refresh connected sources</button>}
    {!!item.metadataOverrides?.length&&<details><summary>Fields protected during refresh</summary><p className="muted small">{item.metadataOverrides.join(', ')}</p></details>}
  </>;
  return expanded?<section className="metadata-source-choice metadata-source-expanded">{choices}</section>:<details className="metadata-source-choice"><summary>Choose where this title gets its details</summary>{choices}</details>;
}
