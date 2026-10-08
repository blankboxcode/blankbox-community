'use client';

import {ArrowUpRight, Pencil, Trash2} from 'lucide-react';
import {useState} from 'react';
import {MediaActionIcon} from '@/components/media-action-icon';
import {TvSeriesOrganizer} from '@/components/tv-series-organizer';
import {MusicTrackList} from '@/components/music-track-list';
import {fileTitle} from '@/components/media-file-sections';
import {itemPlaybackGroups} from '@/lib/item-presentation';
import {digitalFileFormat, isConnectedPlaybackSource, isFileSource, isPlayableSource, sourceActionLabel, type MediaItem, type MediaSource} from '@/lib/media';

type Props={item:MediaItem;source?:MediaSource;busy:boolean;catalogBusy:boolean;catalogError:string;activityEnabled:boolean;onActivityChange:()=>void;onSelectSource:(source:MediaSource)=>void;onPlaySource:(source:MediaSource)=>void;onRemoveSource:(source:MediaSource)=>void;onEditFiles:(sourceId?:string)=>void};

export function ItemPlayback({item,source,busy,catalogBusy,catalogError,activityEnabled,onActivityChange,onSelectSource,onPlaySource,onRemoveSource,onEditFiles}:Props) {
  const groups=itemPlaybackGroups(item);
  const connected=item.sources.filter(row=>isConnectedPlaybackSource(row)||row.type==='demo');
  const [choices,setChoices]=useState<Record<string,string>>({});
  const [filesOpen,setFilesOpen]=useState(false);
  const [offset,setOffset]=useState(0);
  const group=groups.find(row=>row.sources.some(file=>file.id===source?.id))||groups.find(row=>row.key===choices.files)||groups[0];
  const files=group?.sources||[];
  const first=files.find(isPlayableSource)||files[0];
  const localSelected=!!source&&isFileSource(source);
  const unit=item.kind==='music'?'tracks':item.kind==='tv'?'episode files':'files';
  const browseUnit=item.kind==='music'?'tracks':'seasons and episodes';
  const choose=(row:MediaSource)=>{onSelectSource(row);setOffset(0);};
  const play=(row:MediaSource)=>{choose(row);onPlaySource(row);};
  return <div className="item-playback-browser">
    {!connected.length&&!groups.length&&<p className="item-page-muted">No playable files or connected apps added yet.</p>}
    {first&&<div className={`item-page-playback-row ${localSelected?'current':''}`}>
      <MediaActionIcon item={item} source={first} size={22}/><div><strong>Local</strong><small>{files.length} {unit} · {group.label}</small>
        {groups.length>1&&<label className="item-playback-change">Change source <select aria-label="Change local source" value={group.key} onChange={event=>{const next=groups.find(row=>row.key===event.target.value)!;setChoices(previous=>({...previous,files:next.key}));choose(next.sources.find(isPlayableSource)||next.sources[0]);setFilesOpen(false);}}>{groups.map(row=><option key={row.key} value={row.key}>{row.label} · {row.sources.length} {unit}</option>)}</select></label>}
        <button data-tv className="text-button" type="button" aria-expanded={filesOpen&&localSelected} onClick={()=>{choose(first);setFilesOpen(!localSelected||!filesOpen);}}>Browse {unit}</button>
      </div>{isPlayableSource(first)&&<button data-tv type="button" className="subtle-button" disabled={busy} onClick={()=>play(first)}>{item.kind==='music'?'Play album':sourceActionLabel(item,first)}</button>}
    </div>}
    {[...new Set(connected.map(row=>row.type))].map(type=>{
      const rows=connected.filter(row=>row.type===type);
      const current=rows.find(row=>row.id===source?.id)||rows.find(row=>row.id===choices[type])||rows[0];
      return <div className={`item-page-playback-row ${current.id===source?.id?'current':''}`} key={type}>
        <MediaActionIcon item={item} source={current} size={22}/><div><strong>{type==='demo'?'Sample':type[0].toUpperCase()+type.slice(1)}</strong><small>Connected app{current.quality?` · ${current.quality}`:''}</small>
          {rows.length>1&&<label className="item-playback-change">Change source <select aria-label={`Change ${type} source`} value={current.id} onChange={event=>{const next=rows.find(row=>row.id===event.target.value)!;setChoices(previous=>({...previous,[type]:next.id!}));choose(next);}}>{rows.map((row,index)=><option key={row.id||index} value={row.id}>{[row.label,row.quality,item.versions?.find(version=>version.id===row.versionId)?.label,`Source ${index+1}`].filter(Boolean).join(' · ')}</option>)}</select></label>}
          {['tv','music'].includes(item.kind)&&['jellyfin','plex'].includes(type)&&<button data-tv type="button" className="text-button" onClick={()=>choose(current)}>Browse {browseUnit}</button>}
        </div>{isPlayableSource(current)&&<button data-tv className="subtle-button" type="button" disabled={busy} onClick={()=>play(current)}>{sourceActionLabel(item,current)}<ArrowUpRight size={14}/></button>}
      </div>;
    })}
    {localSelected&&filesOpen&&<div id="item-playback-files"><ol className="item-page-file-list" start={offset+1}>{files.slice(offset,offset+20).map((row,index)=><li key={row.id||`${row.path}-${index}`}><span>{fileTitle(item,row)}<small>{digitalFileFormat(row)}{row.available===false?' · Unavailable':''}</small></span>{isPlayableSource(row)&&<button data-tv className="text-button" type="button" disabled={busy} onClick={()=>play(row)}><MediaActionIcon item={item} source={row} size={15}/>{sourceActionLabel(item,row)}</button>}{!item.sample&&row.id&&<button className="item-page-icon-button" type="button" disabled={busy} aria-label={`Remove ${fileTitle(item,row)} source`} onClick={()=>onRemoveSource(row)}><Trash2 size={15}/></button>}</li>)}</ol>{files.length>20&&<div className="collection-paging"><button type="button" disabled={!offset} onClick={()=>setOffset(Math.max(0,offset-20))}>Previous files</button><span>{offset+1}–{Math.min(offset+20,files.length)} of {files.length}</span><button type="button" disabled={offset+20>=files.length} onClick={()=>setOffset(offset+20)}>Next files</button></div>}{!item.sample&&<button data-tv type="button" className="text-button" disabled={busy} onClick={()=>onEditFiles(first?.id)}><Pencil size={14}/>Edit these files</button>}</div>}
    {catalogBusy&&<p className="muted small" role="status">Loading {item.kind==='music'?'tracks':'episodes'}…</p>}
    {catalogError&&<p className="muted small" role="status">{catalogError} {source?.musicCatalog||source?.tvCatalog?'Showing saved details. ':''}Use Refresh below to try again.</p>}
    {item.kind==='tv'&&<TvSeriesOrganizer key={localSelected?group?.key:source?.id} item={{...item,sources:[...item.sources.filter(row=>row.type==='physical'),...(localSelected?files:source?[source]:[])]}} activityEnabled={activityEnabled} onActivityChange={onActivityChange} onPlaySource={onPlaySource}/>}
    {item.kind==='music'&&source&&!localSelected&&<MusicTrackList key={source.id} item={item} source={source} busy={busy||catalogBusy} onPlaySource={onPlaySource}/>}
  </div>;
}

export function ItemSourceManagement({item,busy,onRemoveSource}:{item:MediaItem;busy:boolean;onRemoveSource:(source:MediaSource)=>void}) {
  const sources=item.sources.filter(isConnectedPlaybackSource);
  if(!sources.length||item.sample)return null;
  return <details className="item-page-management item-playback-management"><summary>Manage connected sources</summary><div><p>{item.kind==='music'?'Open the album in its connected app for playback options.':item.kind==='tv'?'Open the series in its connected app for episode and quality options.':'Choose available playback qualities in the connected app.'}</p>{sources.map((source,index)=><div key={source.id||index}><span>{source.label}{source.quality?` · ${source.quality}`:''}</span>{source.id&&<button type="button" className="text-button" disabled={busy} onClick={()=>onRemoveSource(source)}><Trash2 size={14}/>Remove {source.label} link</button>}</div>)}</div></details>;
}
