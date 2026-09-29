'use client';
import { useEffect, useState } from 'react';
import { blankBoxClient, type LibraryPage, type LibraryPageOptions } from '@/lib/blank-box-client';

export function useLibraryPage(enabled:boolean, options:LibraryPageOptions, revision?:unknown) {
  const key=JSON.stringify(options);
  const [result,setResult]=useState<{key:string;page:LibraryPage}|null>(null);
  const [error,setError]=useState('');
  useEffect(()=>{
    if(!enabled)return;
    const controller=new AbortController();
    const timer=setTimeout(()=>{
      blankBoxClient.libraryPage(JSON.parse(key) as LibraryPageOptions,controller.signal).then(page=>{
        if(!controller.signal.aborted){setResult({key,page});setError('');}
      }).catch(cause=>{if(!controller.signal.aborted)setError((cause as Error).message);});
    },options.q?180:0);
    return()=>{controller.abort();clearTimeout(timer);};
  },[enabled,key,revision,options.q]);
  return {page:result?.key===key?result.page:null,error};
}
