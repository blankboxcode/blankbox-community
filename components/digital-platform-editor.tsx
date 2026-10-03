'use client';
import { newRecordId } from '@/lib/streaming-services';
import { Plus, Trash2 } from 'lucide-react';
import type { DigitalPlatform, MediaItem } from '@/lib/media';

export const digitalStatusNames={purchased:'Purchased',redeemed:'Redeemed','code-included':'Code included'};

export function DigitalPlatformEditor({item,rows,onChange}:{item:MediaItem;rows:DigitalPlatform[];onChange:(rows:DigitalPlatform[])=>void}) {
  const update=(id:string,changes:Partial<DigitalPlatform>)=>onChange(rows.map(row=>row.id===id?{...row,...changes}:row));
  return <section className="catalog-physical-edits"><h3>Digital platform copies and codes</h3><p>Record your purchases and redemptions. These are your notes; Blank Box does not check retailer accounts or redeem codes.</p>
    {rows.map(row=><fieldset className="digital-platform-record" key={row.id}><div className="form-grid"><label className="field"><span>Platform</span><input list="digital-platform-options" maxLength={120} value={row.platform} onChange={event=>update(row.id,{platform:event.target.value})}/></label><label className="field"><span>Status</span><select value={row.status} onChange={event=>update(row.id,{status:event.target.value as DigitalPlatform['status']})}>{Object.entries(digitalStatusNames).map(([id,name])=><option key={id} value={id}>{name}</option>)}</select></label></div><label className="field"><span>Link <small>optional</small></span><input type="url" value={row.url} maxLength={2000} placeholder="https://" onChange={event=>update(row.id,{url:event.target.value})}/></label><label className="field"><span>Included with physical copy <small>optional</small></span><select value={row.physicalSourceId} onChange={event=>update(row.id,{physicalSourceId:event.target.value})}><option value="">Separate digital purchase / unspecified</option>{item.sources.filter(source=>source.type==='physical'&&source.id).map(source=><option key={source.id} value={source.id}>{[source.label,source.edition,source.packaging,source.releaseLabel,source.location].filter(Boolean).join(' · ')}</option>)}</select></label><label className="field"><span>Notes <small>optional; do not enter redemption codes</small></span><textarea maxLength={1000} rows={2} value={row.notes} onChange={event=>update(row.id,{notes:event.target.value})}/></label><button className="text-button" type="button" onClick={()=>onChange(rows.filter(entry=>entry.id!==row.id))}><Trash2 size={15}/>Remove record</button></fieldset>)}
    <datalist id="digital-platform-options"><option value="Movies Anywhere"/><option value="Apple TV / iTunes"/><option value="Amazon Prime Video"/><option value="Fandango at Home"/><option value="Google TV / YouTube"/></datalist>
    <button type="button" className="subtle-button" disabled={rows.length>=30} onClick={()=>onChange([...rows,{id:newRecordId(),platform:'',status:'purchased',url:'',notes:'',physicalSourceId:''}])}><Plus size={15}/>Add digital platform</button>
  </section>;
}
