'use client';

import { useEffect, useRef, useState } from 'react';
import { blankBoxClient } from '@/lib/blank-box-client';
import { isFileSource, isPlayableSource, sourceEpisodeNumber, sourceSeason, type MediaItem, type MediaSource, type TvCatalog } from '@/lib/media';
import { ItemActivityPanel } from '@/components/item-activity';
import { fileTitle } from '@/components/media-file-sections';

function SeasonDetails({ item, season, files, owned, activityEnabled, onActivityChange, onPlaySource }: { item:MediaItem; season:TvCatalog['seasons'][number]; files:MediaSource[]; owned:boolean; activityEnabled:boolean; onActivityChange:()=>void; onPlaySource:(source:MediaSource)=>void }) {
  const [open,setOpen]=useState(false);
  const episodes=new Map(season.episodes.map(episode=>[episode.number,episode]));
  const byEpisode=new Map<number,MediaSource[]>();
  for(const file of files){const number=sourceEpisodeNumber(file);if(!number)continue;const rows=byEpisode.get(number)||[];rows.push(file);byEpisode.set(number,rows);if(!episodes.has(number))episodes.set(number,{number,title:fileTitle(item,file),description:'',airDate:null,providerItemId:`local-${season.number}-${number}`});}
  const ordered=[...episodes.values()].sort((a,b)=>a.number-b.number);
  return <details onToggle={event=>setOpen(event.currentTarget.open)}><summary><strong>{season.title}</strong><small>{ordered.length?`${ordered.length} episodes`:files.length?`${files.length} files`:'Episode list unavailable'}{owned?' · Physical season recorded':''}</small></summary>{open&&<div>{activityEnabled&&season.number>=0&&<ItemActivityPanel item={item} season={season.number} onChange={onActivityChange}/>} {ordered.length?ordered.map(episode=><article key={episode.number}><span className="tv-episode-number">{season.number<0?`Episode ${episode.number}`:season.number===0?'Special':`S${String(season.number).padStart(2,'0')}E${String(episode.number).padStart(2,'0')}`}</span><div><strong>{episode.title}</strong>{episode.airDate&&<small> · {episode.airDate}</small>}{episode.description&&<p>{episode.description}</p>}{(byEpisode.get(episode.number)||[]).map(file=><div key={file.id||file.path} className="tv-episode-file"><small title={file.path}>{fileTitle(item,file)} · {file.type==='digital'?'Linked file':'Managed file'}{file.available===false?' · Unavailable':''}</small>{isPlayableSource(file)&&<button className="subtle-button" type="button" onClick={()=>onPlaySource(file)}>Play file</button>}</div>)}</div></article>):<p className="muted small">Only the season is recorded. No episode titles or ownership are inferred.</p>}{files.filter(file=>!sourceEpisodeNumber(file)).map(file=><p key={file.id||file.path} className="muted small" title={file.path}>Unnumbered file: {fileTitle(item,file)}</p>)}</div>}</details>;
}

export function TvSeriesOrganizer({ item, activityEnabled, onActivityChange, onPlaySource }: { item: MediaItem; activityEnabled:boolean; onActivityChange:()=>void; onPlaySource:(source:MediaSource)=>void }) {
  const providers = item.sources.filter(source => (source.type === 'jellyfin' || source.type === 'plex') && source.id && source.providerItemId);
  const localFiles=item.sources.filter(isFileSource);
  const preferred = providers.find(source => source.id === item.metadataPreference) || (item.metadataPreference==='blankbox'&&localFiles.length?undefined:providers[0]);
  const [sourceId, setSourceId] = useState(preferred?.id || '');
  const [catalogs, setCatalogs] = useState<Record<string, TvCatalog>>(() => Object.fromEntries(providers.filter(source => source.id && source.tvCatalog).map(source => [source.id!, source.tvCatalog!])));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [seriesActivityOpen,setSeriesActivityOpen]=useState(false);
  const autoLoaded = useRef(new Set<string>());
  const source = providers.find(row => row.id === sourceId);
  const catalog = sourceId ? catalogs[sourceId] : undefined;
  const physicalSeasons = new Set(item.sources.filter(row => row.type === 'physical').map(row => row.season).filter(Boolean));
  const versionSeasons = new Set((item.versions || []).map(row => row.season).filter(Boolean));
  const localSeasons=new Set(localFiles.map(sourceSeason).filter(Boolean));
  const unassignedFiles=localFiles.filter(file=>!/^\d{1,3}$/.test(sourceSeason(file))&&sourceSeason(file)!=='specials');
  const knownSeasons = [...new Set([...physicalSeasons, ...versionSeasons, ...localSeasons])].sort((left, right) => Number(left) - Number(right));
  const seasons=new Map((catalog?.seasons||[]).map(season=>[season.number,season]));
  for(const value of knownSeasons){const number=value==='specials'?0:/^\d{1,3}$/.test(value!)?Number(value):undefined;if(number!==undefined&&!seasons.has(number))seasons.set(number,{number,title:number===0?'Specials':`Season ${number}`,episodes:[]});}
  // A reference count establishes listed seasons, never physical ownership.
  for(let number=1;number<=Math.min(item.catalogDetails?.seasonCount||0,100);number++){if(!seasons.has(number))seasons.set(number,{number,title:`Season ${number}`,episodes:[]});}

  const refresh = async (id: string) => {
    if (!id) return;
    setBusy(true); setError('');
    try {
      const result = await blankBoxClient.action('tv-catalog-refresh', { id: item.id, sourceId: id });
      if (result.tvCatalog) setCatalogs(current => ({ ...current, [id]: result.tvCatalog! }));
    } catch (cause) { setError((cause as Error).message); }
    finally { setBusy(false); }
  };
  useEffect(() => {
    if (!sourceId || catalogs[sourceId] || autoLoaded.current.has(sourceId)) return;
    const loaded = autoLoaded.current;
    loaded.add(sourceId);
    let active = true;
    void blankBoxClient.action('tv-catalog-refresh', { id: item.id, sourceId }).then(result => {
      if (active && result.tvCatalog) setCatalogs(current => ({ ...current, [sourceId]: result.tvCatalog! }));
    }).catch(cause => { if (active) setError((cause as Error).message); });
    return () => { active = false; loaded.delete(sourceId); };
  }, [catalogs, item.id, sourceId]);

  return <section className="tv-series-organizer">
    <div className="item-detail-section-heading"><div><h3>Seasons and episodes</h3><p>Local files and the selected episode catalog appear together. Physical seasons stay separate.</p></div></div>
    {knownSeasons.length > 0 && <p className="tv-known-seasons">Your recorded seasons: {knownSeasons.map(value => value === 'complete-series' ? 'Complete series' : value === 'specials' ? 'Specials' : `Season ${value}`).join(' · ')}</p>}
    {providers.length > 0 && <div className="tv-catalog-controls"><label className="field"><span>Episode catalog</span><select value={sourceId} onChange={event => { setSourceId(event.target.value); setError(''); }}><option value="">Blank Box local files</option>{providers.map(row => <option key={row.id} value={row.id}>{row.label}</option>)}</select></label>{sourceId&&<button className="subtle-button" type="button" disabled={busy} onClick={() => void refresh(sourceId)}>{busy ? 'Loading episodes…' : 'Refresh episodes'}</button>}</div>}
    {error && <p className="muted small" role="status">{error}{catalog ? ' Showing saved episode details.' : ''}</p>}
    {!providers.length&&!localFiles.length && <p className="muted small">Season counts come from your selected metadata. Connect Jellyfin or Plex for episode titles; seasons listed here do not establish ownership.</p>}
    {source&&catalog&&<p className="muted small">{catalog.seasons.length} seasons · {catalog.episodeCount} listed episodes · {source.label}{catalog.updatedAt?` · Updated ${new Date(catalog.updatedAt).toLocaleDateString()}`:''}</p>}
    <div className="tv-season-list">{[...seasons.values()].sort((a,b)=>a.number-b.number).map(season=><SeasonDetails key={season.number} item={item} season={season} files={localFiles.filter(file=>sourceSeason(file)==='specials'?season.number===0:Number(sourceSeason(file))===season.number)} owned={physicalSeasons.has('complete-series')||physicalSeasons.has(season.number===0?'specials':String(season.number))} activityEnabled={activityEnabled} onActivityChange={onActivityChange} onPlaySource={onPlaySource}/>)}</div>
    {unassignedFiles.length>0&&<div className="tv-season-list"><SeasonDetails key="unassigned" item={item} season={{number:-1,title:'Other TV files',episodes:[]}} files={unassignedFiles} owned={false} activityEnabled={false} onActivityChange={onActivityChange} onPlaySource={onPlaySource}/></div>}
    {!seasons.size&&!unassignedFiles.length&&<p className="muted small">No seasons are known yet. Add season details in Edit details or refresh the connected episode catalog.</p>}
    {activityEnabled&&<details className="tv-series-activity" onToggle={event=>setSeriesActivityOpen(event.currentTarget.open)}><summary>Whole Series & Activity History</summary>{seriesActivityOpen&&<ItemActivityPanel item={item} onChange={onActivityChange}/>}</details>}
  </section>;
}
