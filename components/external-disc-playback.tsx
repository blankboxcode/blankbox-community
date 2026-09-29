'use client';
import { useState } from 'react';
import { FolderOpen } from 'lucide-react';
import type { MediaItem } from '@/lib/media';

export function ExternalDiscPlayback({item,drive}:{item:MediaItem;drive?:string}){
 const [copied,setCopied]=useState(false),[copyError,setCopyError]=useState(false);
 if(!item.sources.some(source=>source.type==='physical'&&['DVD','Blu-ray','4K UHD Blu-ray'].includes(source.label)))return null;
 return <details className="external-disc-playback"><summary><FolderOpen size={16}/>Play your disc in an external app</summary><p>Insert the matching disc into the computer you want to use. Open its disc drive in File Explorer (Windows), Finder (Mac), or Files (Linux), then use a compatible player you are authorized to use.</p>{drive&&<p>Blank Box’s configured drive: <code>{drive}</code> <button className="text-button" onClick={()=>void navigator.clipboard.writeText(drive).then(()=>{setCopied(true);setCopyError(false);}).catch(()=>setCopyError(true))}>{copied?'Drive path copied':'Copy drive path'}</button>{copyError&&<small role="alert">Select the displayed path to copy it manually.</small>}</p>}<p className="muted small">Your browser cannot open the file manager or player on the Blank Box server. A device path such as /dev/sr0 is not a folder. DVD and Blu-ray records are catalog entries; Blank Box does not play, decrypt, or copy protected video discs.</p></details>;
}
