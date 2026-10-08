'use client';

import { useState } from 'react';
import { isFileSource, isPlayableSource, sourceEpisodeNumber, sourceSeason, type MediaItem, type MediaSource, type TvCatalog } from '@/lib/media';
import { ItemActivityPanel } from '@/components/item-activity';
import { fileTitle } from '@/components/media-file-sections';

function SeasonDetails({ item, season, files, owned, activityEnabled, onActivityChange, onPlaySource }: { item:MediaItem; season:TvCatalog['seasons'][number]; files:MediaSource[]; owned:boolean; activityEnabled:boolean; onActivityChange:()=>void; onPlaySource:(source:MediaSource)=>void }) {
  const [open,setOpen]=useState(false);
  const [offset,setOffset]=useState(0);
  const provider=item.sources.find(source=>(source.type==='jellyfin'||source.type==='plex')&&source.tvCatalog);
  const episodes=new Map(season.episodes.map(episode=>[episode.number,episode]));
  const byEpisode=new Map<number,MediaSource[]>();
  for(const file of files){const number=sourceEpisodeNumber(file);if(!number)continue;const rows=byEpisode.get(number)||[];rows.push(file);byEpisode.set(number,rows);if(!episodes.has(number))episodes.set(number,{number,title:fileTitle(item,file),description:'',airDate:null,providerItemId:`local-${season.number}-${number}`});}
  const ordered=[...episodes.values()].sort((a,b)=>a.number-b.number);
  return <details onToggle={event=>setOpen(event.currentTarget.open)}><summary><strong>{season.title}</strong><small>{ordered.length?`${ordered.length} episodes`:files.length?`${files.length} files`:'Episode list unavailable'}{owned?' · Physical season recorded':''}</small></summary>{open&&<div>{activityEnabled&&season.number>=0&&<ItemActivityPanel item={item} season={season.number} onChange={onActivityChange}/>} {ordered.length?ordered.slice(offset,offset+25).map(episode=><article key={episode.number}><span className="tv-episode-number">{season.number<0?`Episode ${episode.number}`:season.number===0?'Special':`S${String(season.number).padStart(2,'0')}E${String(episode.number).padStart(2,'0')}`}</span><div><strong>{episode.title}</strong>{episode.airDate&&<small> · {episode.airDate}</small>}{episode.description&&<p>{episode.description}</p>}{provider&&<button data-tv className="text-button" type="button" onClick={()=>onPlaySource({...provider,url:`/api/playback/source/${encodeURIComponent(item.id)}/${encodeURIComponent(provider.id!)}/${encodeURIComponent(episode.providerItemId)}`})}>Open episode</button>}{(byEpisode.get(episode.number)||[]).map(file=><div key={file.id||file.path} className="tv-episode-file"><small title={file.path}>{fileTitle(item,file)} · {file.type==='digital'?'Linked file':'Managed file'}{file.available===false?' · Unavailable':''}</small>{isPlayableSource(file)&&<button className="subtle-button" type="button" onClick={()=>onPlaySource(file)}>Play file</button>}</div>)}</div></article>):<p className="muted small">Only the season is recorded. No episode titles or ownership are inferred.</p>}{ordered.length>25&&<div className="collection-paging"><button type="button" disabled={!offset} onClick={()=>setOffset(Math.max(0,offset-25))}>Previous episodes</button><span>{offset+1}–{Math.min(offset+25,ordered.length)} of {ordered.length}</span><button type="button" disabled={offset+25>=ordered.length} onClick={()=>setOffset(offset+25)}>Next episodes</button></div>}{files.filter(file=>!sourceEpisodeNumber(file)).slice(0,25).map(file=><p key={file.id||file.path} className="muted small" title={file.path}>Unnumbered file: {fileTitle(item,file)}</p>)}</div>}</details>;
}

export function TvSeriesOrganizer({ item, activityEnabled, onActivityChange, onPlaySource }: { item: MediaItem; activityEnabled:boolean; onActivityChange:()=>void; onPlaySource:(source:MediaSource)=>void }) {
  const providers = item.sources.filter(source => (source.type === 'jellyfin' || source.type === 'plex') && source.id && source.providerItemId);
  const localFiles=item.sources.filter(isFileSource);
  const source=providers[0];
  const sourceId=source?.id||'';
  const catalog=source?.tvCatalog;
  const [seriesActivityOpen,setSeriesActivityOpen]=useState(false);
  const [seasonNumber,setSeasonNumber]=useState('');
  const physicalSeasons = new Set(item.sources.filter(row => row.type === 'physical').map(row => row.season).filter(Boolean));
  const versionSeasons = new Set((item.versions || []).map(row => row.season).filter(Boolean));
  const localSeasons=new Set(localFiles.map(sourceSeason).filter(Boolean));
  const unassignedFiles=localFiles.filter(file=>!/^\d{1,3}$/.test(sourceSeason(file))&&sourceSeason(file)!=='specials');
  const knownSeasons = [...new Set([...physicalSeasons, ...versionSeasons, ...localSeasons])].sort((left, right) => Number(left) - Number(right));
  const seasons=new Map((catalog?.seasons||[]).map(season=>[season.number,season]));
  for(const value of knownSeasons){const number=value==='specials'?0:/^\d{1,3}$/.test(value!)?Number(value):undefined;if(number!==undefined&&!seasons.has(number))seasons.set(number,{number,title:number===0?'Specials':`Season ${number}`,episodes:[]});}
  // A reference count establishes listed seasons, never physical ownership.
  for(let number=1;number<=Math.min(item.catalogDetails?.seasonCount||0,100);number++){if(!seasons.has(number))seasons.set(number,{number,title:`Season ${number}`,episodes:[]});}

  return <section className="tv-series-organizer">
    <div className="item-detail-section-heading"><div><h3>Seasons and episodes</h3><p>Follows the playback source above. Physical season records stay separate.</p></div></div>
    {knownSeasons.length > 0 && <p className="tv-known-seasons">Your recorded seasons: {knownSeasons.map(value => value === 'complete-series' ? 'Complete series' : value === 'specials' ? 'Specials' : `Season ${value}`).join(' · ')}</p>}
    {!providers.length&&!localFiles.length && <p className="muted small">Season counts come from your selected metadata. Connect Jellyfin or Plex for episode titles; seasons listed here do not establish ownership.</p>}
    {source&&catalog&&<p className="muted small">{catalog.seasons.length} seasons · {catalog.episodeCount} listed episodes · {source.label}{catalog.updatedAt?` · Updated ${new Date(catalog.updatedAt).toLocaleDateString()}`:''}</p>}
    {!!seasons.size&&<div className="item-catalog-navigation" aria-label="Browse seasons">{[...seasons.values()].sort((a,b)=>a.number-b.number).map(season=><button data-tv type="button" className="text-button" aria-pressed={season.number===(seasons.has(Number(seasonNumber))&&seasonNumber!==''?Number(seasonNumber):[...seasons.keys()].sort((a,b)=>a-b)[0])} key={season.number} onClick={()=>setSeasonNumber(String(season.number))}>{season.title}</button>)}</div>}
    <div className="tv-season-list">{[...seasons.values()].sort((a,b)=>a.number-b.number).filter(season=>season.number===(seasons.has(Number(seasonNumber))&&seasonNumber!==''?Number(seasonNumber):[...seasons.keys()].sort((a,b)=>a-b)[0])).map(season=><SeasonDetails key={`${sourceId}-${season.number}`} item={item} season={season} files={localFiles.filter(file=>sourceSeason(file)==='specials'?season.number===0:Number(sourceSeason(file))===season.number)} owned={physicalSeasons.has('complete-series')||physicalSeasons.has(season.number===0?'specials':String(season.number))} activityEnabled={activityEnabled} onActivityChange={onActivityChange} onPlaySource={onPlaySource}/>)}</div>
    {unassignedFiles.length>0&&<div className="tv-season-list"><SeasonDetails key="unassigned" item={item} season={{number:-1,title:'Other TV files',episodes:[]}} files={unassignedFiles} owned={false} activityEnabled={false} onActivityChange={onActivityChange} onPlaySource={onPlaySource}/></div>}
    {!seasons.size&&!unassignedFiles.length&&<p className="muted small">No seasons are known yet. Add season details in Edit details or refresh the connected episode catalog.</p>}
    {activityEnabled&&<details className="tv-series-activity" onToggle={event=>setSeriesActivityOpen(event.currentTarget.open)}><summary>Whole Series & Activity History</summary>{seriesActivityOpen&&<ItemActivityPanel item={item} onChange={onActivityChange}/>}</details>}
  </section>;
}
