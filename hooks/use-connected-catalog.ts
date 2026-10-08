'use client';

import {useCallback, useEffect, useRef, useState} from 'react';
import {blankBoxClient} from '@/lib/blank-box-client';
import type {MediaItem, MediaSource, MusicCatalog, TvCatalog} from '@/lib/media';

export function useConnectedCatalog(item:MediaItem, source?:MediaSource) {
  const [catalogs,setCatalogs]=useState<Record<string,{tvCatalog?:TvCatalog;musicCatalog?:MusicCatalog}>>({});
  const [status,setStatus]=useState({id:'',busy:false,error:''});
  const generation=useRef(0);
  const id=source?.id||'';
  const supported=!!id&&['jellyfin','plex'].includes(source!.type)&&['tv','music'].includes(item.kind);
  const saved=catalogs[id]||source;
  const available=item.kind==='tv'?saved?.tvCatalog:saved?.musicCatalog;
  const refresh=useCallback(async()=>{
    if(!supported)return;
    const current=++generation.current;
    setStatus({id,busy:true,error:''});
    try {
      const result=await blankBoxClient.action(item.kind==='tv'?'tv-catalog-refresh':'music-catalog-refresh',{id:item.id,sourceId:id});
      if(current===generation.current){setCatalogs(previous=>({...previous,[id]:{tvCatalog:result.tvCatalog,musicCatalog:result.musicCatalog}}));setStatus({id,busy:false,error:''});}
    } catch(cause) {if(current===generation.current)setStatus({id,busy:false,error:(cause as Error).message});}
  },[id,item.id,item.kind,supported]);
  const cancel=useCallback(()=>{generation.current++;},[]);
  useEffect(()=>{
    let active=true;
    void Promise.resolve().then(()=>{
      if(!active)return;
      setStatus({id,busy:false,error:''});
      if(supported&&!available)void refresh();
    });
    return ()=>{active=false;cancel();};
  },[id,supported,refresh,available,cancel]);
  return {source:source?{...source,...catalogs[id]}:undefined,refresh,supported,busy:status.id===id&&status.busy,error:status.id===id?status.error:''};
}
