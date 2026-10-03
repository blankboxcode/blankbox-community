'use client';

import { Info, Plus, RefreshCw, X } from 'lucide-react';
import { mediaLength, mediaTrackCount, type CatalogDetails, type Kind, type MediaItem } from '@/lib/media';

const listLabels = {directors:'Directors',writers:'Writers',cast:'Cast',studios:'Studios',languages:'Languages',countries:'Countries',creators:'Creators',authors:'Authors',publishers:'Publishers',collections:'Collection labels'} as const;
const textLabels = {contentRating:'Content rating',releaseType:'Release type',firstPublished:'First published',firstReleased:'First released'} as const;
const countLabels = {seasonCount:'Seasons',episodeCount:'Episodes',pageCount:'Pages',trackCount:'Tracks',discCount:'Discs'} as const;

export function MediaCatalogDetails({item,onRefresh,busy=false,showEmpty=false}:{item:MediaItem;onRefresh?:()=>void;busy?:boolean;showEmpty?:boolean}) {
 const details=item.catalogDetails||{};
 const rows:[string,string][]=[];
 if(item.year)rows.push(['Year',String(item.year)]);
 if(item.genre)rows.push(['Genre',item.genre]);
 if(item.artist)rows.push(['Artist',item.artist]);
 const length=mediaLength(item);if(length)rows.push([item.kind==='music'?'Length':item.kind==='book'||item.kind==='comic'?'Audio Length':'Runtime',length.replace(/ (length|listed runtime|audio length|runtime)$/,'')]);
 if(item.releaseDate)rows.push(['Release date',item.releaseDate]);
 for(const [key,label] of Object.entries(textLabels)){
  const value=details[key as keyof typeof textLabels];if(value)rows.push([label,value]);
 }
 for(const [key,label] of Object.entries(countLabels)){
  const value=key==='trackCount'?mediaTrackCount(item):details[key as keyof typeof countLabels];if(value)rows.push([label,String(value)]);
 }
 for(const [key,label] of Object.entries(listLabels)){
  const values=details[key as keyof typeof listLabels];if(values?.length)rows.push([label,values.join(' · ')]);
 }
 if(!rows.length&&!details.ratings?.length&&!onRefresh&&!showEmpty)return null;
 return <section className="media-catalog-details" aria-label="About this title"><div className="media-catalog-heading"><h3><Info size={18} aria-hidden="true"/>About this title</h3>{onRefresh&&<button className="text-button" type="button" disabled={busy} onClick={onRefresh}><RefreshCw size={14}/>{busy?'Refreshing…':'Refresh Details'}</button>}</div><dl>{rows.map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}{details.ratings?.map((rating,index)=><div key={`${rating.source}-${index}`}><dt>{rating.source}</dt><dd>{rating.value} / {rating.scale}{rating.count!==undefined?` · ${rating.count.toLocaleString()} ratings`:''}</dd></div>)}</dl>{!rows.length&&!details.ratings?.length&&<p className="muted small">{onRefresh?'Refresh connected details or use Choose details source to find a match.':'Add credits and catalog facts in Edit title details.'}</p>}</section>;
}

export function CatalogDetailsEditor({kind,value,onChange}:{kind:Kind;value:CatalogDetails;onChange:(value:CatalogDetails)=>void}) {
 const update=(key:keyof CatalogDetails,next:unknown)=>{
  const updated={...value};if(next===undefined)delete updated[key];else Object.assign(updated,{[key]:next});onChange(updated);
 };
 const lists:(keyof typeof listLabels)[]=kind==='movie'?['directors','writers','cast','studios','languages','countries']:kind==='tv'?['creators','directors','writers','cast','studios','languages','countries']:kind==='book'||kind==='comic'?['authors','publishers','creators','languages']:['creators','publishers','languages'];
 const texts:(keyof typeof textLabels)[]=kind==='music'?['releaseType','firstReleased']:kind==='book'||kind==='comic'?['firstPublished']:['contentRating'];
 lists.push('collections');
 const counts:(keyof typeof countLabels)[]=kind==='tv'?['seasonCount','episodeCount']:kind==='book'||kind==='comic'?['pageCount']:kind==='music'?['trackCount','discCount']:[];
 // Changing type must not hide an existing field from the owner.
 for(const key of Object.keys(listLabels) as (keyof typeof listLabels)[])if(value[key]?.length&&!lists.includes(key))lists.push(key);
 for(const key of Object.keys(textLabels) as (keyof typeof textLabels)[])if(value[key]&&!texts.includes(key))texts.push(key);
 for(const key of Object.keys(countLabels) as (keyof typeof countLabels)[])if(value[key]&&!counts.includes(key))counts.push(key);
 const ratings=value.ratings||[];
 const changeRating=(index:number,key:keyof NonNullable<CatalogDetails['ratings']>[number],next:string|number|undefined)=>update('ratings',ratings.map((row,i)=>{if(i!==index)return row;const updated={...row};if(next===undefined)delete updated[key];else Object.assign(updated,{[key]:next});return updated;}));
 return <section className="catalog-shared-details" aria-label="Credits and catalog facts"><h3>{kind==='book'||kind==='comic'?'Publication & Details':kind==='music'?'Album & Track Details':'Credits & Details'}</h3>
  <div className="form-grid">{texts.map(key=><label className="field" key={key}><span>{textLabels[key]} <small>optional</small></span><input maxLength={120} value={value[key]||''} onChange={event=>update(key,event.target.value.trim()?event.target.value:undefined)}/></label>)}{counts.map(key=><label className="field" key={key}><span>{countLabels[key]} <small>optional</small></span><input type="number" min={1} max={100000} step={1} value={value[key]||''} onChange={event=>update(key,event.target.value?Number(event.target.value):undefined)}/></label>)}</div>
  {lists.map(key=><label className="field" key={key}><span>{listLabels[key]} <small>one per line</small></span><textarea rows={2} maxLength={25100} value={(value[key]||[]).join('\n')} onChange={event=>{const entries=event.target.value.split('\n');update(key,entries.some(entry=>entry.trim())?entries:undefined);}}/></label>)}
  <div className="catalog-ratings"><div className="catalog-ratings-heading"><h4>Ratings</h4><button className="text-button" type="button" disabled={ratings.length>=10} onClick={()=>update('ratings',[...ratings,{source:'Owner rating',value:0,scale:10}])}><Plus size={15}/>Add Rating</button></div>{ratings.map((rating,index)=><fieldset className="catalog-rating-row" key={index}><legend>Rating {index+1}</legend><label className="field"><span>Rating Source</span><input maxLength={120} value={rating.source} onChange={event=>changeRating(index,'source',event.target.value)}/></label><div className="form-grid"><label className="field"><span>Score</span><input type="number" min={0} max={rating.scale} step="any" value={rating.value} onChange={event=>changeRating(index,'value',Number(event.target.value))}/></label><label className="field"><span>Out Of</span><input type="number" min={0.01} max={1000} step="any" value={rating.scale} onChange={event=>changeRating(index,'scale',Number(event.target.value))}/></label><label className="field"><span>Rating Count <small>optional</small></span><input type="number" min={0} max={1000000000} value={rating.count??''} onChange={event=>changeRating(index,'count',event.target.value?Number(event.target.value):undefined)}/></label></div><button className="text-button" type="button" onClick={()=>update('ratings',ratings.length===1?undefined:ratings.filter((_,i)=>i!==index))}><X size={15}/>Remove Rating</button></fieldset>)}</div>
 </section>;
}
