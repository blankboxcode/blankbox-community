'use client';
import { newRecordId } from '@/lib/streaming-services';
import { Plus, Trash2 } from 'lucide-react';
import type { Settings, StreamingService } from '@/lib/media';
import { streamingDefaults } from '@/lib/streaming-services';

export function StreamingServicesEditor({value,onChange}:{value:Settings;onChange:(value:Settings)=>void}) {
  const overrides=value.streamingServiceOverrides||[];const custom=value.customStreamingServices||[];
  const editBuiltin=(id:string,key:'name'|'url',text:string)=>{
    const original=streamingDefaults.find(row=>row.id===id)!;const prior=overrides.find(row=>row.id===id)||original;
    onChange({...value,streamingServiceOverrides:[...overrides.filter(row=>row.id!==id),{id,name:prior.name,url:prior.url,[key]:text}]});
  };
  return <section className="panel service-links-editor"><h2>Streaming and digital service links</h2><p>Choose the services you use and edit their links. These shortcuts do not connect accounts or check which titles you own.</p>
    {streamingDefaults.map(original=>{const row=overrides.find(row=>row.id===original.id)||original;return <details key={row.id}><summary>{row.name||original.name}</summary><label className="toggle-row"><input type="checkbox" checked={value.streamingServices.includes(row.id as StreamingService)} onChange={event=>onChange({...value,streamingServices:event.target.checked?[...value.streamingServices,row.id as StreamingService]:value.streamingServices.filter(id=>id!==row.id)})}/>Show in title details</label><div className="form-grid"><label className="field"><span>Name</span><input maxLength={80} value={row.name} onChange={event=>editBuiltin(row.id,'name',event.target.value)}/></label><label className="field"><span>Website link</span><input type="url" maxLength={2000} value={row.url} onChange={event=>editBuiltin(row.id,'url',event.target.value)}/></label></div><button className="text-button" type="button" onClick={()=>onChange({...value,streamingServiceOverrides:overrides.filter(entry=>entry.id!==row.id)})}>Restore default name and link</button></details>;})}
    <h3>Custom services</h3>{custom.map(row=><div className="custom-service-row" key={row.id}><div className="form-grid"><label className="field"><span>Name</span><input maxLength={80} value={row.name} onChange={event=>onChange({...value,customStreamingServices:custom.map(entry=>entry.id===row.id?{...entry,name:event.target.value}:entry)})}/></label><label className="field"><span>Website link</span><input type="url" maxLength={2000} value={row.url} placeholder="https://" onChange={event=>onChange({...value,customStreamingServices:custom.map(entry=>entry.id===row.id?{...entry,url:event.target.value}:entry)})}/></label></div><label><input type="checkbox" checked={row.enabled!==false} onChange={event=>onChange({...value,customStreamingServices:custom.map(entry=>entry.id===row.id?{...entry,enabled:event.target.checked}:entry)})}/> Show service</label><button type="button" className="text-button" aria-label={`Remove ${row.name||'custom service'}`} onClick={()=>onChange({...value,customStreamingServices:custom.filter(entry=>entry.id!==row.id)})}><Trash2 size={15}/>Remove</button></div>)}
    <button type="button" className="subtle-button" disabled={custom.length>=30} onClick={()=>onChange({...value,customStreamingServices:[...custom,{id:`custom-${newRecordId()}`,name:'',url:'',enabled:true}]})}><Plus size={15}/>Add custom service</button><p className="muted small">Use Save settings to apply your changes.</p>
  </section>;
}
