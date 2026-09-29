'use client';

import { ChevronDown, GitMerge, Layers3, ListChecks, ShieldCheck } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useState } from 'react';
import { kindNames, type ReconciliationReview } from '@/lib/media';

export type ReviewPolicy='keep'|'incoming'|'new-version'|'separate';
type Props={reviews:ReconciliationReview[];reviewCount:number;busy:boolean;onResolve:(reviewId:string,policy:ReviewPolicy,targetId?:string)=>void;onResolveAll:(policy:Exclude<ReviewPolicy,'separate'>)=>void};

function detailSummary(item:ReconciliationReview['incoming']){
 const details=[item.year,item.genre,item.poster?'artwork':undefined,item.description?`${item.description.length} character description`:undefined].filter(Boolean);
 return details.length?details.join(' · '):'Title and media type only';
}

function MetadataDetails({item}:{item:ReconciliationReview['incoming']}){
 const editions=item.versions?.map(version=>version.label).filter(Boolean).join(' · ')||'Standard or unknown edition';
 const sources=item.sources.map(source=>[source.label,source.location||source.path].filter(Boolean).join(' · ')).join(' · ')||'No source location recorded';
 return <dl className="metadata-fields">
  <div><dt>Title</dt><dd>{item.title}</dd></div>
  <div><dt>Media type</dt><dd>{kindNames[item.kind]}</dd></div>
  <div><dt>Year</dt><dd>{item.year||'Not provided'}</dd></div>
  <div><dt>Genre</dt><dd>{item.genre||'Not provided'}</dd></div>
  <div><dt>Edition</dt><dd>{editions}</dd></div>
  <div><dt>Where it comes from</dt><dd>{sources}</dd></div>
  <div className="metadata-description"><dt>Description</dt><dd>{item.description||'No description provided'}</dd></div>
 </dl>;
}

export function ReconciliationPanel({reviews,reviewCount,busy,onResolve,onResolveAll}:Props){
 const[selected,setSelected]=useState<Record<string,string>>({});
 const[expanded,setExpanded]=useState(false);
 if(!reviewCount)return null;
 const visibleReviews=expanded?reviews:reviews.slice(0,2);
 const hiddenReviews=Math.max(0,reviewCount-visibleReviews.length);
 return <section className="panel reconciliation-panel">
  <div className="reconciliation-heading"><span className="source-icon peach"><GitMerge/></span><div><span className="eyebrow">MATCH REVIEW</span><h2>Consolidate {reviewCount} possible {reviewCount===1?'match':'matches'}.</h2><p>Nothing in this list is merged until you choose. Original files and connected libraries remain unchanged.</p></div></div>
  {reviewCount>25&&<div className="review-warning"><ListChecks/><span><strong>This is a large review list.</strong><small>Choose one safe rule for all proposed matches, or review the first {reviews.length} individually.</small></span></div>}
  <div className="bulk-review-actions"><button className="subtle-button" disabled={busy} onClick={()=>onResolveAll('keep')}><ShieldCheck/>Keep Blank Box details for all</button><button className="subtle-button" disabled={busy} onClick={()=>onResolveAll('incoming')}><GitMerge/>Use incoming details for all</button><button className="subtle-button" disabled={busy} onClick={()=>onResolveAll('new-version')}><Layers3/>Make new editions</button></div>
  <div className="review-list">{visibleReviews.map(review=>{const targetId=selected[review.id]||review.candidates[0]?.id;const target=review.candidates.find(candidate=>candidate.id===targetId)||review.candidates[0],sourceLabel=review.source||review.incoming.sources[0]?.label||'Connected source';return <article className="review-card" key={review.id}>
   <header><span><strong>{review.incoming.title}</strong><small><b>Importing from {sourceLabel}</b> · {kindNames[review.incoming.kind]}</small></span><em>{review.candidates.length} possible {review.candidates.length===1?'match':'matches'}</em></header>
   {review.candidates.length>1&&<label className="field"><span>Match with</span><Select value={targetId} onValueChange={value=>setSelected(current=>({...current,[review.id]:value}))}><SelectTrigger><SelectValue/></SelectTrigger><SelectContent>{review.candidates.map(candidate=><SelectItem value={candidate.id} key={candidate.id}>{candidate.title}{candidate.year?` (${candidate.year})`:''}</SelectItem>)}</SelectContent></Select></label>}
   {target&&<><div className="metadata-comparison"><div><span>BLANK BOX LIBRARY</span><strong>{target.title}{target.year?` (${target.year})`:''}</strong><small>{detailSummary(target)}</small></div><div><span>{sourceLabel.toUpperCase()}</span><strong>{review.incoming.title}{review.incoming.year?` (${review.incoming.year})`:''}</strong><small>{detailSummary(review.incoming)}</small></div></div><details className="metadata-details"><summary>Compare detailed metadata <ChevronDown size={15}/></summary><div className="metadata-detail-grid"><section><span>BLANK BOX LIBRARY</span><MetadataDetails item={target}/></section><section><span>{sourceLabel.toUpperCase()}</span><MetadataDetails item={review.incoming}/></section></div></details></>}
   <div className="review-actions"><button disabled={busy||!targetId} onClick={()=>onResolve(review.id,'keep',targetId)}>Merge, keep Blank Box<br/><small>Same edition</small></button><button disabled={busy||!targetId} onClick={()=>onResolve(review.id,'incoming',targetId)}>Merge, use {sourceLabel}<br/><small>Same edition</small></button><button disabled={busy||!targetId} onClick={()=>onResolve(review.id,'new-version',targetId)}>New edition<br/><small>Keep under this title</small></button><button disabled={busy} onClick={()=>onResolve(review.id,'separate')}>Different title<br/><small>Do not consolidate</small></button></div>
  </article>;})}</div>
  {!expanded&&hiddenReviews>0&&<button type="button" className="review-more" onClick={()=>setExpanded(true)}>Show {hiddenReviews} more {hiddenReviews===1?'match':'matches'} <ChevronDown size={15}/></button>}
  {expanded&&reviewCount>reviews.length&&<p className="muted small">Showing {reviews.length} of {reviewCount}. Resolve these to load the next group.</p>}
 </section>;
}
