import {mediaFileGroups,mediaVersions,sourcesForVersion,type GalleryArtwork,type MediaItem,type MediaSource} from './media';

export type ItemEdition = {id:string;label:string;subtitle:string;releaseId:string;versionId:string;sources:MediaSource[];physical:boolean};

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
  return editions;
}

export function editionArtwork(item:MediaItem,releaseId:string):GalleryArtwork[] {
  const gallery=item.artworkGallery||[];
  const scoped=gallery.filter(image=>(image.releaseId||'')===releaseId);
  return [...(scoped.length?scoped:gallery.filter(image=>!image.releaseId))].sort((a,b)=>Number(b.role==='front')-Number(a.role==='front')||Number(b.primary)-Number(a.primary));
}

export function itemPlaybackGroups(item:MediaItem) {
  return mediaFileGroups(item).map(group=>({...group,sources:[...group.sources].sort((a,b)=>(a.trackNumber||a.episodeNumber||0)-(b.trackNumber||b.episodeNumber||0)||(a.path||a.label).localeCompare(b.path||b.label,undefined,{numeric:true}))}));
}
