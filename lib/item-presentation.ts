import {mediaFileGroups,playbackFileVariant,mediaVersions,sourcesForVersion,type GalleryArtwork,type MediaItem,type MediaSource} from './media';

export type ItemEdition = {id:string;label:string;subtitle:string;releaseId:string;versionId:string;sources:MediaSource[];physical:boolean;connected?:boolean};

export function itemCardCounts(item:MediaItem):{sources:number;editions:number}|null {
  if(item.cardCounts)return item.cardCounts;
  // An older compact projection cannot reveal all editions. Wait for its
  // rebuild rather than deriving a misleading total from representative rows.
  if(item.browseSummary)return null;
  const sources=new Set(item.sources.flatMap(source=>source.type==='local'||source.type==='digital'?['local']:isCardPlaybackSource(source)?[source.type]:[]));
  return {sources:sources.size,editions:Math.max(1,itemEditions(item).length)};
}

function isCardPlaybackSource(source:MediaSource){return ['jellyfin','plex','emby','demo'].includes(source.type);}

export function itemEditions(item:MediaItem):ItemEdition[] {
  const editions:ItemEdition[]=[];
  for(const version of mediaVersions(item)) {
    const sources=sourcesForVersion(item,version.id);
    const releases=new Map<string,MediaSource[]>();
    for(const source of sources.filter(row=>row.type==='physical')) {
      const id=source.physicalReleaseId||JSON.stringify([version.id,source.label,source.edition||'']);
      releases.set(id,[...(releases.get(id)||[]),source]);
    }
    for(const [id,copies] of releases) {
      const source=copies[0];
      const label=source.packageTitle||[source.label,source.edition].filter(Boolean).join(' · ');
      editions.push({id:`physical:${id}`,label,subtitle:[source.packaging,source.releaseLabel].filter(Boolean).join(' · ')||`${copies.length} ${copies.length===1?'copy':'copies'}`,releaseId:source.physicalReleaseId||'',versionId:version.id,sources:copies,physical:true});
    }
    const files=sources.filter(row=>row.type==='local'||row.type==='digital');
    if(files.length) editions.push({id:`files:${version.id}`,label:version.label==='Standard or unknown edition'?'Digital files':version.label,subtitle:`${files.length} ${files.length===1?'file':'files'}`,releaseId:'',versionId:version.id,sources:files,physical:false});
  }
  const connected=new Map<string,ItemEdition>();
  for(const source of item.sources.filter(row=>['jellyfin','plex','emby','demo'].includes(row.type))) {
    const version=mediaVersions(item).find(row=>row.id===source.versionId)||mediaVersions(item)[0];
    const explicit=source.edition?.trim();
    const fileEdition=editions.find(row=>!row.physical&&!row.connected&&row.versionId===version.id);
    if(fileEdition&&(!explicit||editionKey(explicit)===editionKey(version.label)||fileEdition.sources.some(row=>editionKey(row.edition||'')===editionKey(explicit))))continue;
    const physicalVersion=item.sources.some(row=>row.type==='physical'&&row.versionId===version.id);
    const label=explicit||(!physicalVersion&&!/^(?:standard(?: or unknown edition)?|unknown(?: edition)?)$/i.test(version.label)&&!/^\d{3,4}p$|^(?:4k|uhd|hd)$/i.test(version.label)?version.label:'Standard');
    const key=editionKey(label);
    const saved=connected.get(key);
    if(saved)saved.sources.push(source);
    else connected.set(key,{id:`connected:${key}`,label,subtitle:'Connected digital edition',releaseId:'',versionId:version.id,sources:[source],physical:false,connected:true});
  }
  editions.push(...connected.values());
  return editions;
}

function editionKey(value:string){return value.normalize('NFKD').toLocaleLowerCase().replace(/[^\p{L}\p{N}]/gu,'');}

export function editionArtwork(item:MediaItem,releaseId:string):GalleryArtwork[] {
  const gallery=item.artworkGallery||[];
  const scoped=gallery.filter(image=>(image.releaseId||'')===releaseId);
  return [...(scoped.length?scoped:gallery.filter(image=>!image.releaseId))].sort((a,b)=>Number(b.role==='front')-Number(a.role==='front')||Number(b.primary)-Number(a.primary));
}

export function itemPlaybackGroups(item:MediaItem) {
  return mediaFileGroups(item).map(group=>({...group,label:[group.label, ['tv','music','movie'].includes(item.kind)?playbackFileVariant(item,group.sources[0])||'':'', ['tv','music'].includes(item.kind)?item.versions?.find(version=>version.id===group.sources[0].versionId)?.label?.replace(/^Standard or unknown edition$/, '')||'':''].filter(Boolean).join(' · '),sources:[...group.sources].sort((a,b)=>(a.trackNumber||a.episodeNumber||0)-(b.trackNumber||b.episodeNumber||0)||(a.path||a.label).localeCompare(b.path||b.label,undefined,{numeric:true}))}));
}

export function musicPlaybackTracks(item:MediaItem,startSourceId?:string) {
  const groups=itemPlaybackGroups(item);
  const group=groups.find(row=>row.sources.some(source=>source.id===startSourceId))||groups[0];
  return (group?.sources||[]).filter(source=>source.url&&source.available!==false);
}
