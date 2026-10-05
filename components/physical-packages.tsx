'use client';
/* eslint-disable @next/next/no-img-element -- Artwork comes from saved library references. */

import {useEffect,useState} from 'react';
import {Package,Plus,Trash2} from 'lucide-react';
import {blankBoxClient} from '@/lib/blank-box-client';
import type {MediaItem} from '@/lib/media';
import {Dialog,DialogContent,DialogDescription,DialogHeader,DialogTitle} from '@/components/ui/dialog';

type PackageContent={itemId:string;sourceId:string;copyId:string;title:string;kind:string;year?:number;poster?:string;season?:string;format:string};
type BoxSet={id:string;title:string;formats:string[];packaging:string;releaseLabel:string;notes:string;copies:{id:string;location:string;condition:string}[];contents:PackageContent[]};
type PackagePage={packages:BoxSet[];total:number;offset:number;limit:number};
async function change(details:Record<string,unknown>){return await blankBoxClient.action('physical-package-change',{...details,confirm:true}) as unknown as PackagePage;}
async function page(details:Record<string,unknown>={}){return await blankBoxClient.action('physical-packages',details) as unknown as PackagePage;}

export function PhysicalPackages({revision,onChanged,onOpenItem,onCount,kind='all',format='all',favorites=false,genre='',status=''}:{revision:unknown;onChanged:()=>void;onOpenItem:(id:string)=>void;onCount:(count:number)=>void;kind?:string;format?:string;favorites?:boolean;genre?:string;status?:string}) {
  const [result,setResult]=useState<PackagePage|null>(null);
  const [selected,setSelected]=useState<BoxSet|null>(null);
  const [pagination,setPagination]=useState({key:'',offset:0});
  const filterKey=JSON.stringify([kind,format,favorites,genre,status]);
  const offset=pagination.key===filterKey?pagination.offset:0;
  const setOffset=(value:number)=>setPagination({key:filterKey,offset:value});
  const [error,setError]=useState('');
  useEffect(()=>{
    let active=true;
    void page({offset,kind:kind==='all'?'':kind,format:format==='all'?'':format.replace(/^format:/,''),favorites,genre,status}).then(value=>{if(active){setResult(value);onCount(value.total);setError('');}}).catch(cause=>{if(active)setError((cause as Error).message);});
    return()=>{active=false;};
  },[revision,offset,onCount,kind,format,favorites,genre,status]);
  const visible=result?.packages||[];
  if(error)return <p className="error-text" role="alert">Box sets: {error}</p>;
  if(!result?.total)return null;
  return <section className="panel physical-box-sets"><div className="section-heading"><h2><Package size={20}/>Box sets</h2><span>{result.total} {result.total===1?'package':'packages'}</span></div><div className="box-set-grid">{visible.map(box=><button type="button" className="box-set-card" key={box.id} onClick={()=>setSelected(box)}><Package size={30}/><span><strong>{box.title}</strong><small>{box.contents.length} included titles or seasons · {box.copies.length} owned {box.copies.length===1?'copy':'copies'}</small><small>{box.formats.join(' / ')} · {box.copies[0]?.location||'Location not recorded'}</small></span></button>)}</div>{result.total>result.limit&&<div className="catalog-list-actions"><button className="subtle-button" disabled={!offset} onClick={()=>setOffset(Math.max(0,offset-result.limit))}>Previous box sets</button><span>{offset+1}-{Math.min(offset+result.limit,result.total)} of {result.total}</span><button className="subtle-button" disabled={offset+result.limit>=result.total} onClick={()=>setOffset(offset+result.limit)}>Next box sets</button></div>}{selected&&<BoxSetDialog key={selected.id} box={selected} onClose={()=>setSelected(null)} onChanged={box=>{setSelected(box);setResult(current=>current?{...current,packages:current.packages.map(row=>row.id===box.id?box:row)}:current);onChanged();}} onOpenItem={id=>{setSelected(null);onOpenItem(id);}}/>}</section>;
}

export function PhysicalPackageContents({item,sourceId,onChanged,onOpenItem}:{item:MediaItem;sourceId:string;onChanged:()=>void;onOpenItem?:(id:string)=>void}) {
  const source=item.sources.find(source=>source.id===sourceId);
  const [box,setBox]=useState<BoxSet|null>(null);
  const [open,setOpen]=useState(false);
  const [title,setTitle]=useState(source?.packageTitle||`${item.title} box set`);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  useEffect(()=>{
    if(source?.packageType!=='box-set'||!source.physicalReleaseId)return;
    let active=true;
    void page({releaseId:source.physicalReleaseId}).then(value=>{if(active)setBox(value.packages[0]||null);}).catch(cause=>{if(active)setError((cause as Error).message);});
    return()=>{active=false;};
  },[source?.packageType,source?.physicalReleaseId]);
  if(!source||!['movie','tv'].includes(item.kind))return null;
  const create=async()=>{
    if(!window.confirm('Make this physical copy a box set? Its title-only edition match will be cleared. The title, other copies and files will stay in your library.'))return;
    setBusy(true);setError('');
    try{const value=await change({operation:'create',itemId:item.id,sourceId,title});setBox(value.packages[0]);setOpen(true);onChanged();}catch(cause){setError((cause as Error).message);}finally{setBusy(false);}
  };
  return <div className="item-box-set">{box?<button type="button" className="subtle-button" onClick={()=>setOpen(true)}><Package size={16}/>{box.title} · {box.contents.length} included titles or seasons</button>:<details><summary>This physical copy contains more than one movie or season?</summary><label className="field"><span>Box set name</span><input value={title} maxLength={250} onChange={event=>setTitle(event.target.value)}/></label><button type="button" className="subtle-button" disabled={busy||!title.trim()} onClick={()=>void create()}><Package size={16}/>Make this a box set</button></details>}{error&&<p className="error-text" role="alert">{error}</p>}{open&&box&&<BoxSetDialog key={box.id} box={box} onClose={()=>setOpen(false)} onChanged={value=>{setBox(value);onChanged();}} onOpenItem={onOpenItem?id=>{setOpen(false);onOpenItem(id);}:undefined}/>}</div>;
}

function BoxSetDialog({box,onClose,onChanged,onOpenItem}:{box:BoxSet;onClose:()=>void;onChanged:(box:BoxSet)=>void;onOpenItem?: (id:string)=>void}) {
  const [busy,setBusy]=useState(false),[error,setError]=useState('');
  const [query,setQuery]=useState(''),[matches,setMatches]=useState<MediaItem[]>([]);
  const [title,setTitle]=useState(''),[kind,setKind]=useState<'movie'|'tv'>('movie'),[year,setYear]=useState(''),[season,setSeason]=useState('');
  const [details,setDetails]=useState({title:box.title,location:box.copies[0]?.location||'',condition:box.copies[0]?.condition||'',packaging:box.packaging,releaseLabel:box.releaseLabel,notes:box.notes});
  const perform=async(fields:Record<string,unknown>)=>{setBusy(true);setError('');try{const value=await change({...fields,releaseId:box.id});onChanged(value.packages[0]);}catch(cause){setError((cause as Error).message);}finally{setBusy(false);}};
  const search=async()=>{setBusy(true);setError('');try{const result=await blankBoxClient.libraryPage({q:query,limit:25,excludeSamples:true});setMatches(result.items.filter(item=>['movie','tv'].includes(item.kind)));}catch(cause){setError((cause as Error).message);}finally{setBusy(false);}};
  return <Dialog open onOpenChange={value=>{if(!value&&!busy)onClose();}}><DialogContent className="form-dialog box-set-dialog"><DialogHeader><DialogTitle>{box.title}</DialogTitle><DialogDescription>One physical package. Each included title stays searchable in My Library.</DialogDescription></DialogHeader><div className="box-set-dialog-body"><p className="muted small">{box.formats.join(' / ')} · {box.copies.length} owned {box.copies.length===1?'copy':'copies'} · {box.copies[0]?.location||'Location not recorded'}</p><h3>Included titles and seasons</h3><div className="box-set-contents">{box.contents.map(content=><div key={content.sourceId}>{content.poster&&<img src={content.poster} alt="" loading="lazy"/>}<span><strong>{content.title}</strong><small>{[content.year,content.season==='complete-series'?'Complete series':content.season==='specials'?'Specials':content.season?`Season ${content.season}`:'',content.format].filter(Boolean).join(' · ')}</small></span>{onOpenItem&&<button className="text-button" disabled={busy} onClick={()=>onOpenItem(content.itemId)}>Open title</button>}<button className="item-page-icon-button" disabled={busy||box.contents.length<=1} aria-label={`Remove ${content.title} from this box set`} onClick={()=>{if(window.confirm(`Remove ${content.title} from this box set? Its other copies, title details and files will stay in your library.`))void perform({operation:'remove',sourceId:content.sourceId});}}><Trash2 size={16}/></button></div>)}</div><h3>Add an included title</h3><div className="inline-form"><input aria-label="Search library for a box set title" placeholder="Search My Library" value={query} onChange={event=>setQuery(event.target.value)}/><button className="subtle-button" disabled={busy||!query.trim()} onClick={()=>void search()}>Search</button></div>{matches.map(item=><div className="box-set-match" key={item.id}><span>{item.title}{item.year?` (${item.year})`:''}</span><button className="text-button" disabled={busy} onClick={()=>void perform({operation:'add',targetId:item.id,...(item.kind==='tv'&&season?{season}:{})})}>Include this title</button></div>)}<p className="muted small">Or enter a title that is not in your library yet.</p><div className="form-grid"><label className="field"><span>Title</span><input maxLength={250} value={title} onChange={event=>setTitle(event.target.value)}/></label><label className="field"><span>Media type</span><select value={kind} onChange={event=>{setKind(event.target.value as 'movie'|'tv');setSeason('');}}><option value="movie">Movie</option><option value="tv">TV show</option></select></label><label className="field"><span>Year <small>optional</small></span><input type="number" min={1800} max={2200} value={year} onChange={event=>setYear(event.target.value)}/></label><label className="field"><span>TV season <small>optional, also used for existing TV titles</small></span><select value={season} onChange={event=>setSeason(event.target.value)}><option value="">Not specified</option><option value="complete-series">Complete series</option><option value="specials">Specials</option>{Array.from({length:99},(_,index)=><option key={index+1} value={String(index+1)}>Season {index+1}</option>)}</select></label></div><button className="subtle-button" disabled={busy||!title.trim()} onClick={()=>void perform({operation:'add',title,kind,year:year?Number(year):null,...(kind==='tv'&&season?{season}:{})})}><Plus size={16}/>Add title to this package</button><details className="box-set-edit"><summary>Edit package details</summary><div className="form-grid">{(['title','location','condition','packaging','releaseLabel'] as const).map(field=><label className="field" key={field}><span>{{title:'Box set name',location:'Physical location',condition:'Condition',packaging:'Packaging',releaseLabel:'Release label'}[field]}</span><input maxLength={field==='title'||field==='location'?250:120} value={details[field]} onChange={event=>setDetails(current=>({...current,[field]:event.target.value}))}/></label>)}</div><label className="field"><span>Package notes</span><textarea maxLength={4000} value={details.notes} onChange={event=>setDetails(current=>({...current,notes:event.target.value}))}/></label><button className="subtle-button" disabled={busy||!details.title.trim()} onClick={()=>void perform({operation:'edit',details})}>Save package details</button></details>{error&&<p className="error-text" role="alert">{error}</p>}<button className="subtle-button" disabled={busy} onClick={onClose}>Done</button></div></DialogContent></Dialog>;
}
