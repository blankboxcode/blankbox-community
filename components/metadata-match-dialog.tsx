'use client';
/* eslint-disable @next/next/no-img-element -- Private service artwork cannot use Next image optimization. */

import { useState } from 'react';
import { ArrowLeft, ArrowUpRight, Check, Database, HardDrive, Loader2, Search, Server } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import type { MediaItem, StreamingService } from '@/lib/media';
import { MetadataCandidateReview } from '@/components/metadata-candidate-review';

const streaming:{id:StreamingService;name:string;search:(query:string)=>string}[]=[
 {id:'netflix',name:'Netflix',search:q=>'https://www.netflix.com/search?q='+encodeURIComponent(q)},
 {id:'prime-video',name:'Prime Video',search:q=>'https://www.amazon.com/s?i=instant-video&k='+encodeURIComponent(q)},
 {id:'disney-plus',name:'Disney+',search:q=>'https://www.disneyplus.com/search?q='+encodeURIComponent(q)},
 {id:'youtube',name:'YouTube',search:q=>'https://www.youtube.com/results?search_query='+encodeURIComponent(q)},
 {id:'spotify',name:'Spotify',search:q=>'https://open.spotify.com/search/'+encodeURIComponent(q)},
 {id:'apple-tv',name:'Apple TV',search:q=>'https://tv.apple.com/search?term='+encodeURIComponent(q)},
];
type Source='packs'|'household'|'connected'|'streaming';
type Props={open:boolean;target?:MediaItem|null;initialQuery:string;streamingServices:StreamingService[];busy:boolean;onOpenChange:(open:boolean)=>void;onBackToChoices?:()=>void;onSearch:(query:string,source:'household'|'connected')=>Promise<MediaItem[]>;onApply:(match:MediaItem)=>Promise<boolean>;onOpenItem:(item:MediaItem)=>void;onReferenceConfirm?:(entityId:string)=>Promise<void>};

export function MetadataMatchDialog({open,target,initialQuery,streamingServices,busy,onOpenChange,onBackToChoices,onSearch,onApply,onOpenItem,onReferenceConfirm}:Props){
 const[query,setQuery]=useState(initialQuery),[results,setResults]=useState<MediaItem[]>([]),[searched,setSearched]=useState(false),[searching,setSearching]=useState(false);
 const[source,setSource]=useState<Source>(target&&onReferenceConfirm?'packs':'household');
 const[referenceId,setReferenceId]=useState(''),[referenceError,setReferenceError]=useState('');
 const chosen=streaming.filter(service=>streamingServices.includes(service.id));
 const attachLinkedFile=!!target&&target.sources.some(source=>source.type==='digital')&&target.sources.every(source=>source.type==='digital'||source.type==='catalog');
 const chooseSource=(next:Source)=>{setSource(next);setResults([]);setSearched(false);setReferenceId('');setReferenceError('');};
 const search=async()=>{if(!query.trim()||source==='packs'||source==='streaming')return;setSearching(true);try{setResults(await onSearch(query.trim(),source));setSearched(true);}finally{setSearching(false);}};
 const apply=async(match:MediaItem)=>{if(await onApply(match))onOpenChange(false);};
 return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent className="match-dialog">
  <DialogHeader><DialogTitle>{target?`Match ${target.title}`:'Find a title and where it lives'}</DialogTitle><DialogDescription>Choose where to look first. {attachLinkedFile?'Attaching this linked file keeps the chosen library title and its Media Item ID. Episodes and tracks stay as file evidence under that title.':'Applying a match fills its available title details. Fields it does not provide and your copy details stay in place.'}</DialogDescription></DialogHeader>
  {target&&<div className="match-return-actions"><button className="subtle-button" type="button" onClick={onBackToChoices||(()=>onOpenChange(false))}><ArrowLeft size={15}/>{onBackToChoices?'Back to import choices':'Back to item'}</button></div>}
  <div className="match-source-picker" role="group" aria-label="Choose match source">
   <button type="button" className={source==='household'?'selected':''} aria-pressed={source==='household'} onClick={()=>chooseSource('household')}><HardDrive size={17}/><span><strong>My Library</strong><small>Physical copies and files already cataloged here</small></span></button>
   {target&&onReferenceConfirm&&<button type="button" className={source==='packs'?'selected':''} aria-pressed={source==='packs'} onClick={()=>chooseSource('packs')}><Database size={17}/><span><strong>Search Blank Box Database</strong><small>Offline titles and metadata installed on this box</small></span></button>}
   <button type="button" className={source==='connected'?'selected':''} aria-pressed={source==='connected'} onClick={()=>chooseSource('connected')}><Server size={17}/><span><strong>Connected libraries</strong><small>Jellyfin or Plex titles already synced to Blank Box</small></span></button>
   <button type="button" className={source==='streaming'?'selected':''} aria-pressed={source==='streaming'} onClick={()=>chooseSource('streaming')}><ArrowUpRight size={17}/><span><strong>Streaming searches</strong><small>Open official searches; availability is not verified</small></span></button>
  </div>
  {source==='packs'&&target&&onReferenceConfirm?<section className="match-section"><div className="match-heading"><span><Database size={16}/><strong>Search Blank Box Database</strong></span></div><p className="match-empty">Search your locally installed Offline Metapacks. Physical editions need separate edition identifiers.</p><label className="match-streaming-query">Title to match<input value={query} onChange={event=>{setQuery(event.target.value);setReferenceId('');}} /></label><MetadataCandidateReview key={query} title={query||target.title} kind={target.kind} year={target.year} selectedId={referenceId} onSelect={setReferenceId} sourceScope="packs" excludeItemId={target.id} allowManualCreate={false} disabled={busy}/>{referenceId&&<button type="button" className="subtle-button" disabled={busy} onClick={()=>void onReferenceConfirm(referenceId).then(()=>onOpenChange(false)).catch(error=>setReferenceError((error as Error).message))}><Check size={15}/>Use this title & details</button>}{referenceError&&<p role="alert" className="error-text">{referenceError}</p>}</section>:null}
  {(source==='household'||source==='connected')&&<section className="match-section"><div className="match-heading"><span>{source==='connected'?<Server size={16}/>:<HardDrive size={16}/>}<strong>{source==='connected'?'Synced Jellyfin and Plex titles':'Titles in your library'}</strong></span></div><form className="match-search" onSubmit={event=>{event.preventDefault();void search();}}><label><Search size={17}/><input autoFocus value={query} onChange={event=>{setQuery(event.target.value);setSearched(false);}} placeholder="Movie, show, album, or book title"/></label><button className="primary-button" disabled={searching||!query.trim()}>{searching?<Loader2 className="animate-spin"/>:<Search/>}Search</button></form>{searched?(results.length?<div className="match-results">{results.map(result=><article key={result.id}>{result.poster&&<img src={result.poster} alt=""/>}<div><strong>{result.title}</strong><small>{[result.year,result.kind,result.sources.map(entry=>entry.label).join(' · ')].filter(Boolean).join(' · ')}</small>{result.description&&<p>{result.description}</p>}</div>{target?<button type="button" className="subtle-button" disabled={busy} onClick={()=>void apply(result)}><Check size={15}/>{attachLinkedFile?'Attach to this title':'Use this title'}</button>:<button type="button" className="subtle-button" onClick={()=>{onOpenChange(false);onOpenItem(result);}}>View item</button>}</article>)}</div>:<p className="match-empty">No matching title found in this source. You can try another source or enter details yourself.</p>):<p className="match-empty">Search this source to review possible titles before choosing one.</p>}</section>}
  {source==='streaming'&&<section className="match-section"><div className="match-heading"><span><ArrowUpRight size={16}/><strong>Search your selected services</strong></span></div><label className="match-streaming-query">Title to search<input value={query} onChange={event=>setQuery(event.target.value)} /></label>{chosen.length?<div className="streaming-searches">{chosen.map(service=><a key={service.id} href={service.search(query||initialQuery)} target="_blank" rel="noopener noreferrer">{service.name}<ArrowUpRight size={14}/></a>)}</div>:<p className="match-empty">Choose streaming shortcuts in Settings to see them here.</p>}<p className="match-disclaimer">These are online searches, not verified availability. Region, plan, rental, and purchase terms may differ.</p></section>}
 </DialogContent></Dialog>;
}
