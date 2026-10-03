'use client';

import { MediaRightsChoice } from '@/components/media-rights';
import { MEDIA_RIGHTS_TERMS_VERSION } from '@/lib/media';

import { useState, type ReactNode } from 'react';
import { Check, ChevronLeft, ChevronRight, CircleAlert, Disc3, HardDrive, LockKeyhole, Network, Server, Sparkles, Wrench } from 'lucide-react';
import { DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { PhysicalFormatPicker } from '@/components/physical-format-picker';
import { GamePlatformPicker } from '@/components/physical-organization-settings';
import { homeRowOptions, type HomeRow } from '@/lib/home-preferences';
import type { LibraryState, MediaInput, Settings, SetupMode, SetupStep, StreamingService } from '@/lib/media';
import { defaultPhysicalFormats, type PhysicalFormat } from '@/lib/physical-media';

const steps: SetupStep[] = ['welcome', 'media', 'connect', 'protection', 'access', 'finish'];
const labels: Record<SetupStep,string> = { welcome:'Start', media:'Media', connect:'Connect', protection:'Protection', access:'Access', finish:'Ready' };
type MediaGroup = 'physical' | 'files' | 'servers' | 'streaming';
type SetupDestination = 'home' | 'import' | 'shelf' | 'settings' | 'services';

type Props = {
  settings: Settings;
  mode: LibraryState['mode'];
  sources: LibraryState['sources'];
  backup: LibraryState['backup'];
  busy: boolean;
  editing?: boolean;
  onPersist: (settings: Settings, close?: boolean) => Promise<boolean>;
  onCancel?: () => void;
  onComplete?: (destination: SetupDestination, settings: Settings) => void;
};

function Choice({selected,disabled=false,title,description,badge,onClick,icon,className=''}:{selected:boolean;disabled?:boolean;title:string;description:string;badge:string;onClick:()=>void;icon:ReactNode;className?:string}) {
  return <button type="button" className={`setup-choice ${className} ${selected?'selected':''}`} disabled={disabled} onClick={onClick} aria-pressed={selected}>
    <span className="setup-choice-icon">{icon}</span><span><strong>{title}</strong><small>{description}</small></span><em>{badge}</em>
  </button>;
}

function MediaOption({selected,title,description,badge,planned=false,onClick,icon}:{selected:boolean;title:string;description:string;badge:string;planned?:boolean;onClick:()=>void;icon:ReactNode}) {
  return <button type="button" className={`setup-media-option ${selected?'selected':''} ${planned?'planned':''}`} onClick={onClick} aria-pressed={selected}><span className="setup-media-check">{selected?<Check size={14}/>:null}</span><span className="setup-media-icon">{icon}</span><span><strong>{title}</strong><small>{description}</small></span><em>{badge}</em></button>;
}

function MediaCategory({selected,title,description,count,onClick,icon}:{selected:boolean;title:string;description:string;count:number;onClick:()=>void;icon:ReactNode}) {
  return <button type="button" className={`setup-media-category ${selected?'selected':''}`} onClick={onClick} aria-pressed={selected}><span className="setup-category-icon">{icon}</span><span><strong>{title}</strong><small>{description}</small></span><em>{selected?`${count} selected`:'Choose'}</em><span className="setup-category-check">{selected?<Check size={14}/>:null}</span></button>;
}

export function OnboardingWizard({settings,mode,sources,backup,busy,editing=false,onPersist,onCancel,onComplete}:Props) {
  const [draft,setDraft]=useState<Settings>(settings);
  const [step,setStep]=useState<SetupStep>(editing?'welcome':settings.setupStep || 'welcome');
  const [mediaGroups,setMediaGroups]=useState<MediaGroup[]>(()=>{const groups:MediaGroup[]=[];if(settings.mediaInputs.some(input=>['dvd','cd','addon'].includes(input)))groups.push('physical');if(settings.mediaInputs.some(input=>['usb','hard-drive','digital-files'].includes(input)))groups.push('files');if(settings.mediaInputs.some(input=>['jellyfin','plex','emby'].includes(input)))groups.push('servers');if(settings.streamingServices.length)groups.push('streaming');return groups;});
  const [rightsAccepted,setRightsAccepted]=useState(settings.mediaRightsAttestation?.accepted===true&&settings.mediaRightsAttestation.termsVersion===MEDIA_RIGHTS_TERMS_VERSION);
  const canFinish=mode!=='box'||rightsAccepted;
  const index=steps.indexOf(step);
  const update=(value:Partial<Settings>)=>setDraft(current=>({...current,...value}));
  const chooseMode=(setupMode:SetupMode)=>update({setupMode,mediaProvider:setupMode==='managed'?'blankbox':draft.mediaProvider,remoteProvider:'local'});
  const toggleMedia=(input:MediaInput)=>setDraft(current=>{const mediaInputs=current.mediaInputs.includes(input)?current.mediaInputs.filter(item=>item!==input):[...current.mediaInputs,input];return {...current,mediaInputs,mediaProvider:mediaInputs.includes('jellyfin')?'jellyfin':mediaInputs.includes('plex')?'plex':'blankbox'};});
  const toggleStreaming=(service:StreamingService)=>setDraft(current=>({ ...current,streamingServices:current.streamingServices.includes(service)?current.streamingServices.filter(item=>item!==service):[...current.streamingServices,service]}));
  const physicalInputs=(formats:PhysicalFormat[]):MediaInput[]=>{
    const inputs:MediaInput[]=[];
    if(formats.some(format=>['DVD','Blu-ray','4K UHD Blu-ray','VHS','Betamax','LaserDisc'].includes(format)))inputs.push('dvd');
    if(formats.includes('CD'))inputs.push('cd');
    if(formats.some(format=>!['DVD','Blu-ray','4K UHD Blu-ray','VHS','Betamax','LaserDisc','CD'].includes(format)))inputs.push('addon');
    return inputs;
  };
  const choosePhysicalFormats=(physicalFormats:PhysicalFormat[])=>setDraft(current=>{const nonPhysical=current.mediaInputs.filter(input=>!['dvd','cd','addon'].includes(input));return {...current,physicalFormats,mediaInputs:[...nonPhysical,...physicalInputs(physicalFormats)]};});
  const toggleHomeCategory=(row:HomeRow)=>setDraft(current=>{
    const enabled=current.homeRows.includes(row);
    const shortcut=row==='movies'?'movie':row==='books'?'book':row==='comics'?'comic':row==='games'?'game':row==='photos'?'photo':row;
    const sidebarShortcuts=current.sidebarShortcuts.filter(value=>value!==shortcut);
    if(!enabled)sidebarShortcuts.push(shortcut as Settings['sidebarShortcuts'][number]);
    return {...current,homeRows:enabled?current.homeRows.filter(value=>value!==row):[...current.homeRows,row],sidebarShortcuts};
  });
  const toggleGroup=(group:MediaGroup)=>{if(!mediaGroups.includes(group)){setMediaGroups(current=>[...current,group]);if(group==='physical')setDraft(current=>{const physicalFormats=current.physicalFormats.length?current.physicalFormats:defaultPhysicalFormats;const nonPhysical=current.mediaInputs.filter(input=>!['dvd','cd','addon'].includes(input));return {...current,physicalFormats,mediaInputs:[...nonPhysical,...physicalInputs(physicalFormats)]};});return;}setMediaGroups(current=>current.filter(item=>item!==group));setDraft(current=>{const groupInputs:Record<Exclude<MediaGroup,'streaming'>,MediaInput[]>={physical:['dvd','cd','addon'],files:['usb','hard-drive','digital-files'],servers:['jellyfin','plex','emby']};const mediaInputs=group==='streaming'?current.mediaInputs:current.mediaInputs.filter(input=>!groupInputs[group].includes(input));return {...current,...(group==='physical'?{physicalFormats:[]}:{}),mediaInputs,streamingServices:group==='streaming'?[]:current.streamingServices,mediaProvider:mediaInputs.includes('jellyfin')?'jellyfin':mediaInputs.includes('plex')?'plex':'blankbox'};});};
  const move=async(next:SetupStep)=>{
    const nextSettings={...draft,setupVersion:1,setupStep:next,setupDone:false};
    setDraft(nextSettings);
    if(editing){setStep(next);return;}
    if(await onPersist(nextSettings)){setStep(next);}
  };
  const finish=async(destination:SetupDestination='home')=>{
    if(!canFinish)return;
    const complete={...draft,...(mode==='box'&&rightsAccepted?{mediaRightsAttestation:{accepted:true as const,termsVersion:MEDIA_RIGHTS_TERMS_VERSION}}:{}),setupVersion:1,setupStep:'finish' as const,setupDone:true};
    setDraft(complete);
    if(await onPersist(complete,true))onComplete?.(destination,complete);
  };
  const mediaReady=mediaGroups.includes('physical')&&draft.physicalFormats.length>0||draft.mediaInputs.some(input=>!['addon','emby','dvd','cd'].includes(input));
  const remoteReady=draft.remoteProvider!=='blankbox-connect';

  return <div className="setup-wizard">
    <div className="setup-progress" aria-label="Setup progress">{steps.map((item,n)=><span key={item} className={n<=index?'active':''}><b>{n<index?<Check size={13}/>:n+1}</b><small>{labels[item]}</small></span>)}</div>

    {step==='welcome'&&<>
      <DialogHeader><DialogTitle>Set up your Blank Box.</DialogTitle><DialogDescription>Choose how much of the setup you want Blank Box to handle. You can change individual connections later.</DialogDescription></DialogHeader>
      <label className="field"><span>Library name</span><input value={draft.name} maxLength={60} onChange={event=>update({name:event.target.value})} placeholder="The family library"/></label>
      <div className="setup-choices">
        <Choice selected={draft.setupMode==='managed'} title="Let Blank Box handle it" description="Recommended guidance, safe defaults, health checks, and managed features as they become available." badge="Recommended" icon={<Sparkles/>} onClick={()=>chooseMode('managed')}/>
        <Choice selected={draft.setupMode==='advanced'} title="Advanced setup" description="Connect your existing folders, media servers, networking, and custom household infrastructure." badge="Self-hosted" icon={<Wrench/>} onClick={()=>chooseMode('advanced')}/>
      </div>
    </>}

    {step==='media'&&<>
      <DialogHeader><DialogTitle>What belongs in your Blank Box?</DialogTitle><DialogDescription>Choose the parts of your media life you want to bring together. We’ll show individual connections only for the categories you select.</DialogDescription></DialogHeader>
      <div className="setup-media-categories"><MediaCategory selected={mediaGroups.includes('physical')} title="Physical Media" description="Choose the formats on your shelves" count={draft.physicalFormats.length} icon={<Disc3/>} onClick={()=>toggleGroup('physical')}/><MediaCategory selected={mediaGroups.includes('files')} title="Drives & files" description="USB, hard drives, NAS, and files" count={draft.mediaInputs.filter(input=>['usb','hard-drive','digital-files'].includes(input)).length} icon={<HardDrive/>} onClick={()=>toggleGroup('files')}/><MediaCategory selected={mediaGroups.includes('servers')} title="Media servers" description="Jellyfin, Plex, and Emby" count={draft.mediaInputs.filter(input=>['jellyfin','plex','emby'].includes(input)).length} icon={<Server/>} onClick={()=>toggleGroup('servers')}/><MediaCategory selected={mediaGroups.includes('streaming')} title="Streaming services" description="Official services your household uses" count={draft.streamingServices.length} icon={<Sparkles/>} onClick={()=>toggleGroup('streaming')}/></div>
      {!!mediaGroups.length&&<div className="setup-media-groups">
        {mediaGroups.includes('physical')&&<section><div><strong>Formats on your shelves</strong><small>Only selected formats appear when you add a physical copy. Change this anytime in Settings.</small></div><PhysicalFormatPicker compact value={draft.physicalFormats} onChange={choosePhysicalFormats}/></section>}
        {mediaGroups.includes('physical')&&draft.physicalFormats.includes('Game')&&<section><div><strong>Consoles and platforms you use</strong><small>These appear first when you add a game. You can enter another platform anytime.</small></div><GamePlatformPicker value={draft.gamePlatforms} onChange={gamePlatforms=>update({gamePlatforms})}/></section>}
        {mediaGroups.includes('files')&&<section><div><strong>Drives & files</strong><small>Use one or several sources. Originals remain unchanged.</small></div><div className="setup-media-options"><MediaOption selected={draft.mediaInputs.includes('usb')} title="USB storage" description="Removable drives mounted by the operating system." badge="Ready" icon={<HardDrive/>} onClick={()=>toggleMedia('usb')}/><MediaOption selected={draft.mediaInputs.includes('hard-drive')} title="Hard drive or NAS" description={`${sources.length} source folder${sources.length===1?'':'s'} currently configured.`} badge="Ready" icon={<HardDrive/>} onClick={()=>toggleMedia('hard-drive')}/><MediaOption selected={draft.mediaInputs.includes('digital-files')} title="Digital files" description="Movies, music, photos, books, and household files." badge="Ready" icon={<HardDrive/>} onClick={()=>toggleMedia('digital-files')}/></div></section>}
        {mediaGroups.includes('servers')&&<section><div><strong>Media servers</strong><small>Bring existing catalogs into the same household view.</small></div><div className="setup-media-options"><MediaOption selected={draft.mediaInputs.includes('jellyfin')} title="Jellyfin" description="Sync catalog metadata without copying the underlying media." badge="Ready" icon={<Server/>} onClick={()=>toggleMedia('jellyfin')}/><MediaOption selected={draft.mediaInputs.includes('plex')} title="Plex" description="Sync movies, shows, and albums; playback opens your Plex server." badge="Ready" icon={<Server/>} onClick={()=>toggleMedia('plex')}/><MediaOption selected={draft.mediaInputs.includes('emby')} title="Emby" description="Record this household for the planned Emby provider adapter." badge="Planned" planned icon={<Server/>} onClick={()=>toggleMedia('emby')}/></div></section>}
        {mediaGroups.includes('streaming')&&<section><div><strong>Streaming services</strong><small>Blank Box stores shortcut preferences, not service passwords.</small></div><div className="setup-media-options"><MediaOption selected={draft.streamingServices.includes('netflix')} title="Netflix" description="Open the official app or website for sign-in." badge="Shortcut" icon={<Sparkles/>} onClick={()=>toggleStreaming('netflix')}/><MediaOption selected={draft.streamingServices.includes('prime-video')} title="Prime Video" description="Open the official app or website for sign-in." badge="Shortcut" icon={<Sparkles/>} onClick={()=>toggleStreaming('prime-video')}/><MediaOption selected={draft.streamingServices.includes('disney-plus')} title="Disney+" description="Open the official app or website for sign-in." badge="Shortcut" icon={<Sparkles/>} onClick={()=>toggleStreaming('disney-plus')}/><MediaOption selected={draft.streamingServices.includes('youtube')} title="YouTube" description="Open the official app or website for sign-in." badge="Shortcut" icon={<Sparkles/>} onClick={()=>toggleStreaming('youtube')}/><MediaOption selected={draft.streamingServices.includes('spotify')} title="Spotify" description="Open the official app or website for sign-in." badge="Shortcut" icon={<Sparkles/>} onClick={()=>toggleStreaming('spotify')}/><MediaOption selected={draft.streamingServices.includes('apple-tv')} title="Apple TV" description="Open the official app or website for sign-in." badge="Shortcut" icon={<Sparkles/>} onClick={()=>toggleStreaming('apple-tv')}/><MediaOption selected={draft.streamingServices.includes('movies-anywhere')} title="Movies Anywhere" description="Open the official website. Digital ownership is recorded separately per title." badge="Shortcut" icon={<Sparkles/>} onClick={()=>toggleStreaming('movies-anywhere')}/></div></section>}
      </div>}
      <section className="setup-home-preferences"><strong>What should be easy to find?</strong><p className="muted small">Choose media categories for Home rows and sidebar shortcuts. Recently added stays on Home. You can rearrange these later in Settings.</p><div className="setup-category-picks">{homeRowOptions.filter(option=>!['recently-added','recently-released'].includes(option.id)).map(option=><button type="button" key={option.id} className={`subtle-button ${draft.homeRows.includes(option.id)?'selected':''}`} aria-pressed={draft.homeRows.includes(option.id)} onClick={()=>toggleHomeCategory(option.id)}>{draft.homeRows.includes(option.id)&&<Check size={15}/>} {option.label}</button>)}</div></section>
    </>}

    {step==='connect'&&<>
      <DialogHeader><DialogTitle>Connect what you selected.</DialogTitle><DialogDescription>Here is what happens next for each source. Blank Box keeps service credentials on this Core and never puts them in the source package.</DialogDescription></DialogHeader>
      <div className="setup-connection-list">
        {draft.mediaInputs.some(input=>['dvd','cd'].includes(input))&&<div><Disc3/><span><strong>Physical discs</strong><small>Add titles, editions, identifiers, condition, and physical locations after setup. Playback availability depends on the format and connected hardware.</small></span><em>Use Physical Media</em></div>}
        {draft.mediaInputs.includes('addon')&&<div><Wrench/><span><strong>Books, games & older formats</strong><small>Catalog these objects and their format-specific details in Physical Media. Some media require an adapter for playback or capture.</small></span><em>Use Physical Media</em></div>}
        {draft.mediaInputs.some(input=>['usb','hard-drive','digital-files'].includes(input))&&<div><HardDrive/><span><strong>Drives & files</strong><small>{sources.length?`${sources.length} mounted source folder${sources.length===1?' is':'s are'} ready. Index names in place, then review links and matches. Optional copying of personal files is a separate action.`:'No source folder is mounted yet. Follow the setup guide to add source paths, then index names in place.'}</small></span><em>{sources.length?'Ready to index':'Needs source'}</em></div>}
        {draft.mediaInputs.includes('jellyfin')&&<div className="setup-connection-form"><Server/><span><strong>Jellyfin</strong><small>Enter the server address now. After setup, add a dedicated API key and start catalog sync from Service connections. Media files are not copied.</small><label className="field"><span>Jellyfin address</span><input value={draft.jellyfinUrl} onChange={event=>update({jellyfinUrl:event.target.value})} placeholder="http://blank-box:8096"/></label></span><em>Connect after setup</em></div>}
        {draft.mediaInputs.includes('plex')&&<div className="setup-connection-form"><Server/><span><strong>Plex</strong><small>Enter the Plex Media Server address now. After setup, add a token and start catalog sync from Service connections. Media files are not copied.</small><label className="field"><span>Plex server address</span><input value={draft.plexUrl} onChange={event=>update({plexUrl:event.target.value})} placeholder="http://blank-box:32400"/></label></span><em>Connect after setup</em></div>}
        {draft.mediaInputs.includes('emby')&&<div><Server/><span><strong>Emby</strong><small>Your selection is saved, but this catalog adapter is not available yet.</small></span><em>Planned</em></div>}
        {!!draft.streamingServices.length&&<div><Sparkles/><span><strong>Streaming shortcuts</strong><small>{draft.streamingServices.length} selected service{draft.streamingServices.length===1?'':'s'} will appear in your Services view. Sign in through each official app or website; Blank Box does not store those passwords.</small></span><em>After setup</em></div>}
      </div>
      {mode==='box'&&<section className="setup-monitoring"><h3>Keep your library up to date</h3><p className="muted small">Choose automatic checks or leave them off and run them from Import Media. Checks use your configured interval after the previous batch finishes.</p><label className="setting-row"><span><strong>Monitor configured media folders</strong><small>Find new or changed movies, shows, music, books, comics, photos, and files without copying them. Stable files appear in Import Media for your match review. Unavailable drives keep their catalog links.</small></span><input type="checkbox" checked={draft.autoSourceIndex} onChange={event=>update({autoSourceIndex:event.target.checked})}/></label><label className="setting-row"><span><strong>Refresh connected catalogs</strong><small>Refresh metadata from saved Plex/Jellyfin connections. This is independent of direct folder monitoring.</small></span><input type="checkbox" checked={draft.autoProviderRefresh} onChange={event=>update({autoProviderRefresh:event.target.checked})}/></label><label className="field"><span>Check every (minutes)</span><input type="number" min={1} max={1440} value={draft.autoImportMinutes} onChange={event=>update({autoImportMinutes:Math.max(1,Math.min(1440,Number(event.target.value)||30))})}/></label><p className="muted small">New or changed files need two matching observations at least a minute apart. With folder monitoring off, choose Index source whenever you want to discover changes. Personal-file copy discovery is a separate option in Settings.</p></section>}
      <p className="setup-honesty"><CircleAlert size={17}/>Imports do not begin silently. You will review files or catalog access before starting each ingest.</p>
    </>}

    {step==='protection'&&<>
      <DialogHeader><DialogTitle>Protect what matters.</DialogTitle><DialogDescription>Blank Box distinguishes a working library from a separately verified backup.</DialogDescription></DialogHeader>
      <div className="setup-readiness">
        <div><HardDrive/><span><strong>Media sources</strong><small>{sources.length?`${sources.length} source folder${sources.length===1?' is':'s are'} configured.`:'No source folder is configured yet. Add one when starting the Core.'}</small></span><em className={sources.length?'ready':'attention'}>{sources.length?'Ready':'Needs setup'}</em></div>
        <div><LockKeyhole/><span><strong>Backup destination</strong><small>{backup.configured?backup.sameDevice?'Configured on the same filesystem; use a separate device for real protection.':'A separate backup destination is configured.':'Start the Core with a backup destination to enable checked backups.'}</small></span><em className={backup.configured&&!backup.sameDevice?'ready':'attention'}>{backup.configured&&!backup.sameDevice?'Ready':'Needs attention'}</em></div>
      </div>
      <p className="setup-honesty"><CircleAlert size={17}/>This build does not choose or format drives from the browser. Storage changes stay explicit and reversible.</p>
    </>}

    {step==='access'&&<>
      <DialogHeader><DialogTitle>Choose how you connect.</DialogTitle><DialogDescription>Local-only is the safest default. Advanced networking remains customer-controlled in this release.</DialogDescription></DialogHeader>
      <div className={`setup-choices ${draft.setupMode==='managed'?'setup-managed-access':''}`}>
        {draft.setupMode==='managed'&&<Choice className="managed-connect" selected={false} disabled title="Blank Box Connect" description="The future guided choice for simple device pairing and private access away from home. It will become selectable when the managed service is ready." badge="Coming later" icon={<Sparkles/>} onClick={()=>{}}/>}
        <Choice className={draft.setupMode==='managed'?'local-fallback':''} selected={draft.remoteProvider==='local'} title={draft.setupMode==='managed'?'Stay local':'Local only'} description="Use Blank Box on your home network with no managed remote connection." badge="Ready now" icon={<LockKeyhole/>} onClick={()=>update({remoteProvider:'local',remoteUrl:''})}/>
        {draft.setupMode==='advanced'&&<>
          <Choice selected={draft.remoteProvider==='tailscale'} title="Tailscale" description="Use your own Tailscale network for private access away from home." badge="Advanced" icon={<Network/>} onClick={()=>update({remoteProvider:'tailscale'})}/>
          <Choice selected={draft.remoteProvider==='wireguard'} title="WireGuard" description="Use networking you configure and operate yourself." badge="Advanced" icon={<Network/>} onClick={()=>update({remoteProvider:'wireguard'})}/>
          <Choice selected={draft.remoteProvider==='custom'} title="Custom address" description="Record a reviewed private access address for this household." badge="Advanced" icon={<Network/>} onClick={()=>update({remoteProvider:'custom'})}/>
        </>}
      </div>
      {draft.remoteProvider!=='local'&&<label className="field"><span>Private remote address <small>optional during setup</small></span><input value={draft.remoteUrl} onChange={event=>update({remoteUrl:event.target.value})} placeholder="https://your-private-address.example"/></label>}
    </>}

    {step==='finish'&&<>
      <DialogHeader><DialogTitle>Your foundation is ready.</DialogTitle><DialogDescription>Blank Box will show honest status for anything that still needs attention.</DialogDescription></DialogHeader>
      {mode==='box'&&<MediaRightsChoice accepted={rightsAccepted} onChange={setRightsAccepted}/>}
      <div className="setup-summary">
        <div><span>Setup</span><strong>{draft.setupMode==='managed'?'Recommended guidance':'Advanced / self-hosted'}</strong><em className="ready">Ready</em></div>
        <div><span>Media</span><strong>{draft.mediaInputs.length} input type{draft.mediaInputs.length===1?'':'s'} · {draft.streamingServices.length} streaming shortcut{draft.streamingServices.length===1?'':'s'}</strong><em className={mediaReady?'ready':'attention'}>{mediaReady?'Configured':'Needs a ready source'}</em></div>
        <div><span>Monitoring</span><strong>{draft.autoSourceIndex?'Configured folders on':'Folders checked manually'} · {draft.autoProviderRefresh?'Connected refresh on':'Connected refresh off'}</strong><em>Optional</em></div><div><span>Protection</span><strong>{backup.configured?'Backup configured':'Configure a backup next'}</strong><em className={backup.configured&&!backup.sameDevice?'ready':'attention'}>{backup.configured&&!backup.sameDevice?'Ready':'Optional'}</em></div>
        <div><span>Access</span><strong>{draft.remoteProvider==='local'?'Local only':draft.remoteProvider}</strong><em className={remoteReady?'ready':'attention'}>{remoteReady?'Ready':'Planned'}</em></div>
      </div>
      <div className="setup-next-actions"><strong>Start building your library</strong><small>Save setup and go directly to the next task.</small><div>{draft.mediaInputs.some(input=>['usb','hard-drive','digital-files'].includes(input))&&<button type="button" className="primary-button" disabled={busy||!canFinish} onClick={()=>finish('import')}><HardDrive size={16}/>Start file import</button>}{draft.mediaInputs.some(input=>['dvd','cd','addon'].includes(input))&&<button type="button" className="subtle-button" disabled={busy||!canFinish} onClick={()=>finish('shelf')}><Disc3 size={16}/>Add to Physical Media</button>}{draft.mediaInputs.some(input=>['jellyfin','plex'].includes(input))&&<button type="button" className="subtle-button" disabled={busy||!canFinish} onClick={()=>finish('settings')}><Server size={16}/>Connect media server</button>}{!!draft.streamingServices.length&&<button type="button" className="subtle-button" disabled={busy||!canFinish} onClick={()=>finish('services')}><Sparkles size={16}/>Open services</button>}</div></div>
      <label className="setup-tip-choice"><input type="checkbox" checked={draft.helpTipsEnabled} onChange={event=>update({helpTipsEnabled:event.target.checked})}/>Show short help tips while I learn Blank Box</label>
      <p className="muted small">Physical Media records physical copies and their real locations. A physical record does not mean Blank Box can play or copy the object. Follow the <a href="/downloads/FIRST-STEPS.md" target="_blank" rel="noreferrer">first-library walkthrough</a> to add an item, review a match, and check a backup.</p>
      <p className="setup-honesty"><Check size={17}/>You can revisit services, storage, and access from Settings.</p>
    </>}

    <div className="setup-actions">
      <div className="setup-actions-left">{editing&&<button type="button" className="subtle-button" disabled={busy} onClick={onCancel}>Cancel</button>}{index>0&&<button type="button" className="subtle-button" disabled={busy} onClick={()=>move(steps[index-1] as SetupStep)}><ChevronLeft size={17}/>Back</button>}</div>
      <span/>
      {step!=='finish'?<button type="button" className="primary-button" disabled={busy||!draft.name.trim()||!draft.setupMode||(step==='media'&&!mediaReady)||(step==='access'&&!remoteReady)} onClick={()=>move(steps[index+1] as SetupStep)}>Continue<ChevronRight size={17}/></button>:<button type="button" className="primary-button" disabled={busy||!canFinish} onClick={()=>finish()}>{editing?'Save changes':'Open Blank Box'}<ChevronRight size={17}/></button>}
    </div>
    <small className="setup-mode-note">{editing?'Changes are saved only when you choose Save changes.':'First-time setup progress is saved locally so you can safely resume.'}</small>
  </div>;
}
