'use client';
import { useId } from 'react';

export function CollectorEditionFields({packaging,releaseLabel,onChange}:{packaging:string;releaseLabel:string;onChange:(key:'packaging'|'releaseLabel',value:string)=>void}) {
  const id=useId();
  return <div className="form-grid"><label className="field"><span>Packaging <small>optional</small></span><input maxLength={120} list={`blankbox-packaging-${id}`} value={packaging} onChange={event=>onChange('packaging',event.target.value)} placeholder="Steelbook, Amaray…"/></label><label className="field"><span>Release label <small>optional</small></span><input maxLength={120} list={`blankbox-release-label-${id}`} value={releaseLabel} onChange={event=>onChange('releaseLabel',event.target.value)} placeholder="Manta Lab, WeET…"/></label><datalist id={`blankbox-packaging-${id}`}>{['Steelbook','Mediabook','Digibook','Amaray','Slipcover','Slipbox','Box set','Other'].map(name=><option key={name} value={name}/>)}</datalist><datalist id={`blankbox-release-label-${id}`}>{['Manta Lab','WeET','BluFans','KimchiDVD','Nova Media','Plain Archive'].map(name=><option key={name} value={name}/>)}</datalist></div>;
}
