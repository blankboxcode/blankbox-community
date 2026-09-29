'use client';

import { useEffect, useState } from 'react';
import { Disc3, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { useLibraryPage } from '@/hooks/use-library-page';
import { blankBoxClient, type ApiResult } from '@/lib/blank-box-client';
import type { Job, MediaItem } from '@/lib/media';
import { MetadataCandidateReview } from '@/components/metadata-candidate-review';

export function DiscImport({ items, pagedLibrary, jobs, blocked, preferredDrive, onStarted, onCataloged, onCatalogPhysical, onScanPhysical, onManagePacks }: { items: MediaItem[]; pagedLibrary?:boolean; jobs: Job[]; blocked: boolean; preferredDrive: string; onStarted: () => Promise<unknown>; onCataloged: (item: MediaItem) => void; onCatalogPhysical: () => void; onScanPhysical: () => void; onManagePacks: () => void }) {
  const [status, setStatus] = useState<ApiResult | null>(null);
  const [packInfo, setPackInfo] = useState<ApiResult | null>(null);
  const [probe, setProbe] = useState<ApiResult | null>(null);
  const [device, setDevice] = useState('');
  const [title, setTitle] = useState('');
  const [artist, setArtist] = useState('');
  const [location, setLocation] = useState('');
  const [trackTitles, setTrackTitles] = useState<string[]>([]);
  const [itemId, setItemId] = useState('');
  const [albumQuery,setAlbumQuery]=useState('');
  const [albumPage,setAlbumPage]=useState(0);
  const [identifiedAlbum,setIdentifiedAlbum]=useState<MediaItem|null>(null);
  const albumResults=useLibraryPage(!!pagedLibrary&&!!probe,{kind:'music',q:albumQuery,sort:'az',offset:albumPage*30,limit:30});
  const [metadataEntityId, setMetadataEntityId] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [choice, setChoice] = useState<'catalog' | 'digitize' | null>(null);
  const [matchNote, setMatchNote] = useState('');
  const [showMatches, setShowMatches] = useState(false);
  const [showAllTracks, setShowAllTracks] = useState(false);
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    setBusy(true);
    try {
      const next = await blankBoxClient.action('disc-status');
      setStatus(next);
      if (!next.devices?.includes(device)) setDevice(next.devices?.includes(preferredDrive) ? preferredDrive : next.devices?.[0] || '');
      setProbe(null);
      setMetadataEntityId('');
      setConfirmed(false);
      setChoice(null);
      setMatchNote('');
      setShowMatches(false);
      setShowAllTracks(false);
    } catch (error) { toast.error((error as Error).message); }
    try { setPackInfo(await blankBoxClient.action('metadata-pack-list')); }
    catch { setPackInfo(null); }
    finally { setBusy(false); }
  };
  useEffect(() => {
    let active = true;
    void blankBoxClient.action('disc-status').then(next => {
      if (active) { setStatus(next); setDevice(next.devices?.includes(preferredDrive) ? preferredDrive : next.devices?.[0] || ''); }
    }).catch(error => { if (active) toast.error((error as Error).message); });
    void blankBoxClient.action('metadata-pack-list').then(packs => {
      if (active) setPackInfo(packs);
    }).catch(() => { if (active) setPackInfo(null); });
    return () => { active = false; };
  }, [preferredDrive]);
  const identify = async () => {
    setBusy(true);
    try {
      const found = await blankBoxClient.action('disc-probe', { device });
      if (found.tocFingerprint !== probe?.tocFingerprint) {
        setTitle('Untitled audio CD'); setArtist('Unknown artist'); setItemId(''); setMetadataEntityId(''); setConfirmed(false);
        setChoice(null);
        setShowMatches(false); setShowAllTracks(false);
      }
      setProbe(found);
      setTrackTitles(Array.from({ length: found.trackCount || 0 }, (_, index) => `Track ${String(index + 1).padStart(2, '0')}`));
      const discMatches=await blankBoxClient.action('disc-household',{discId:found.discId||'',tocFingerprint:found.tocFingerprint});
      const cataloged = discMatches.items?.length===1?discMatches.items[0]:!discMatches.items?.length?items.find(item => item.kind === 'music' && item.sources.some(source => source.type === 'physical' && source.discId === found.discId && !!found.discId)):undefined;
      setIdentifiedAlbum(cataloged||null);
      if((discMatches.items?.length||0)>1)setMatchNote('Several cataloged albums match this disc. Review and choose the album below.');
      if (cataloged) {
        setItemId(cataloged.id); setTitle(cataloged.title); setArtist(cataloged.artist || 'Unknown artist');
        setMatchNote('Already in your collection. This import can use the same album.');
      } else if (found.discId) {
        try {
          const candidates = await blankBoxClient.metadataSearch({ kind: 'music', namespace: 'musicbrainz-discid', value: found.discId });
          const releases = candidates.filter(candidate => candidate.level === 'release' && candidate.evidence.includes('exact identifier'));
          const oneTitle = releases.length > 0 && releases.every(candidate => candidate.title.trim().toLocaleLowerCase() === releases[0].title.trim().toLocaleLowerCase());
          if (oneTitle) {
            setTitle(releases[0].title);
            const local = releases.find(candidate => !candidate.id.startsWith('pack:'));
            if (local) {
              try {
                const entity = await blankBoxClient.metadataGet(local.id);
                const artistField = entity.fields.find(field => field.field === 'artist' && typeof field.value === 'string' && field.value.trim());
                if (artistField) setArtist(String(artistField.value));
              } catch { /* The Disc ID and suggested title remain useful without optional fields. */ }
            }
            setMatchNote(releases.length > 1 ? 'Offline records agree on this album title. Review the exact release before confirming a match.' : 'An offline release matches this Disc ID. Verify its details before confirming it.');
          } else setMatchNote(releases.length ? 'Several releases share this Disc ID. Review the album details before choosing one.' : 'No offline Disc ID match. Enter the album details yourself.');
        } catch {
          setMatchNote('Offline matching is unavailable. You can still enter album details yourself.');
        }
      } else setMatchNote('No standard Disc ID was available. Enter album details yourself.');
    } catch (error) { setProbe(null); setMatchNote(''); toast.error((error as Error).message); }
    finally { setBusy(false); }
  };
  const importDisc = async () => {
    if (!probe?.tocFingerprint || !confirmed) return;
    setBusy(true);
    try {
      await blankBoxClient.action('disc-import', { device, tocFingerprint: probe.tocFingerprint, title, artist, location, trackTitles, confirmRights: true, ...(itemId ? { itemId } : {}), ...(metadataEntityId ? { metadataEntityId } : {}) });
      await onStarted();
      toast.success('Audio CD import started. Keep the disc inserted until it finishes.');
      setProbe(null);
    } catch (error) { toast.error((error as Error).message); }
    finally { setBusy(false); }
  };
  const catalogDisc = async () => {
    if (!probe?.tocFingerprint || !title.trim() || !artist.trim()) return;
    setBusy(true);
    try {
      const result = await blankBoxClient.action('disc-catalog', { device, tocFingerprint: probe.tocFingerprint, title, artist, location, ...(itemId ? { itemId } : {}), ...(metadataEntityId ? { metadataEntityId } : {}) });
      if (result.item?.id) setItemId(result.item.id);
      await onStarted();
      toast.success(result.alreadyLinked ? 'This CD is already in your Physical Media.' : 'CD cataloged. No tracks were copied.');
      if (result.item) { setProbe(null); setChoice(null); onCataloged(result.item as MediaItem); }
    } catch (error) { toast.error((error as Error).message); }
    finally { setBusy(false); }
  };
  const musicItems = pagedLibrary?[...new Map([...(identifiedAlbum?[identifiedAlbum]:[]),...(albumResults.page?.items||[])].map(item=>[item.id,item])).values()]:items.filter(item => item.kind === 'music');
  const latestDiscJob = jobs.find(job => job.type === 'disc-import');
  const flacAvailable = status?.platform === 'linux' && status.tools?.cdparanoia && status.tools?.flac;
  return <section id="disc-import" className="panel disc-import" aria-label="Audio CD import">
    <div className="disc-import-heading"><span className="outlined-icon"><Disc3 size={23}/></span><div><h2>Import an audio CD</h2><p>Read the disc, then choose to catalog it or save its tracks.</p></div><button className="text-button" onClick={() => void refresh()} disabled={busy} aria-label="Refresh optical drives"><RefreshCw size={16}/>Refresh drives</button></div>
    <div className="disc-start">
      <div className="disc-step-heading"><span>1</span><div><h3>Identify the disc</h3><p>Select the drive with your audio CD.</p></div></div>
      {!status ? <p className="muted small">Checking optical drives…</p> : status.devices?.length ? <div className="disc-import-controls"><label className="field"><span>Optical drive</span><select value={device} onChange={event => { setDevice(event.target.value); setProbe(null); setMetadataEntityId(''); setMatchNote(''); setShowMatches(false); }}>{status.devices.map(path => <option key={path} value={path}>{status.driveDetails?.find(detail => detail.device === path)?.label || path}</option>)}</select></label><button className="primary-button" disabled={busy || blocked || !status.ready} onClick={() => void identify()}>Identify disc</button></div> : <p className="muted small">{status.message || 'No readable audio CD drive found.'}</p>}
      {status && !status.ready && !!status.devices?.length && <p className="muted small">{status.message || 'Insert an audio CD, then refresh the drive.'}</p>}
      <div className="disc-catalog-alternatives"><span>No readable disc?</span><button type="button" className="text-button" onClick={onCatalogPhysical}>Add the physical CD manually</button><button type="button" className="text-button" onClick={onScanPhysical}>Scan barcode or cover</button></div>
    </div>
    {latestDiscJob && <div className="disc-job-status" role={latestDiscJob.status === 'failed' ? 'alert' : 'status'}><strong>Latest digitization: {latestDiscJob.status}</strong><small>{latestDiscJob.createdAt ? new Date(latestDiscJob.createdAt).toLocaleString() : 'Start time unavailable'} · {latestDiscJob.done} of {latestDiscJob.total} tracks</small>{latestDiscJob.message && <p>{latestDiscJob.message}</p>}{latestDiscJob.errors?.length ? <p className="error-text">{latestDiscJob.errors[0]}</p> : null}</div>}
    {probe && <div className="disc-import-review">
      <div className="disc-step-heading"><span>2</span><div><h3>Choose what to add</h3><p>{probe.trackCount} audio {probe.trackCount === 1 ? 'track' : 'tracks'} detected{probe.discId ? ' · Disc ID available' : ''}</p></div></div>
      {matchNote && <p className="disc-match-note" role="status">{matchNote}</p>}
      <div className="disc-choice" role="group" aria-label="Choose what to do with this audio CD"><button type="button" className={choice==='catalog'?'selected':''} aria-pressed={choice==='catalog'} onClick={()=>setChoice('catalog')}><strong>Catalog physical CD</strong><small>Record the album and its location. No audio tracks copied.</small></button><button type="button" className={choice==='digitize'?'selected':''} aria-pressed={choice==='digitize'} onClick={()=>setChoice('digitize')}><strong>Digitize CD</strong><small>Save lossless {flacAvailable ? 'FLAC' : 'WAV'} tracks and link the physical copy.</small></button></div>
      {choice && <div className="disc-review-body">
        <div className="disc-step-heading"><span>3</span><div><h3>Review album details</h3><p>Use an existing album or enter a new one.</p></div></div>
        {pagedLibrary&&<label className="field"><span>Find an existing album</span><input value={albumQuery} onChange={event=>{setAlbumQuery(event.target.value);setAlbumPage(0);}} placeholder="Search all cataloged albums"/></label>}<label className="field"><span>Album in your library</span><select value={itemId} onChange={event => { const id = event.target.value; setItemId(id); setMetadataEntityId(''); const item = musicItems.find(candidate => candidate.id === id); if (item) {setIdentifiedAlbum(item); setTitle(item.title); setArtist(item.artist || 'Unknown artist'); } }}><option value="">Create a new album</option>{musicItems.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>
        {pagedLibrary&&(albumResults.page?.total||0)>30&&<div className="collection-paging"><button disabled={!albumPage} onClick={()=>setAlbumPage(value=>value-1)}>Previous albums</button><span>Page {albumPage+1}</span><button disabled={(albumPage+1)*30>=(albumResults.page?.total||0)} onClick={()=>setAlbumPage(value=>value+1)}>Next albums</button></div>}
        {albumResults.error&&<p role="alert" className="error-text">{albumResults.error}</p>}
        <div className="disc-import-fields"><label className="field"><span>Album title</span><input value={title} onChange={event => { setTitle(event.target.value); setMetadataEntityId(''); }} maxLength={250}/></label><label className="field"><span>Artist</span><input value={artist} onChange={event => setArtist(event.target.value)} maxLength={250}/></label><label className="field"><span>Physical location <small>optional</small></span><input value={location} onChange={event => setLocation(event.target.value)} maxLength={250} placeholder="Living room shelf"/></label></div>
        <div className="disc-reference"><div><strong>Offline album match <small>optional</small></strong><p>Confirm a reference only when its title and release evidence fit your disc.</p></div><div className="disc-reference-actions"><button type="button" className="subtle-button" onClick={()=>setShowMatches(true)} disabled={busy || blocked}>{showMatches?'Review matches below':'Find an offline match'}</button><button type="button" className="text-button" onClick={onManagePacks}>Manage packs</button></div>{showMatches && <MetadataCandidateReview key={`${probe.tocFingerprint}:${title}`} title={title} kind="music" identifier={probe.discId ? { namespace: 'musicbrainz-discid', value: probe.discId } : undefined} selectedId={metadataEntityId} onSelect={setMetadataEntityId} targetLevel="any" releaseRequiresIdentifier disabled={busy || blocked}/>}</div>
        {choice==='digitize' && <div className="disc-track-editor"><div><strong>Track names</strong><p>Placeholders are ready; edit any names you know before digitizing.</p></div><div className="disc-track-fields">{trackTitles.slice(0,showAllTracks?trackTitles.length:4).map((name, index) => <label className="field" key={index}><span>Track {index + 1}</span><input value={name} onChange={event => setTrackTitles(current => current.map((value, at) => at === index ? event.target.value : value))} maxLength={250}/></label>)}</div>{trackTitles.length>4 && <button type="button" className="text-button" onClick={()=>setShowAllTracks(value=>!value)}>{showAllTracks?'Show first four tracks':`Show all ${trackTitles.length} tracks`}</button>}</div>}
        <div className="disc-confirm"><div className="disc-step-heading"><span>4</span><div><h3>Confirm</h3><p>{choice==='catalog'?'Save this physical CD without copying tracks.':'Keep the disc inserted while Blank Box saves its tracks.'}</p></div></div>{choice==='catalog' ? <button className="primary-button" disabled={busy || blocked || !title.trim() || !artist.trim()} onClick={() => void catalogDisc()}>Add physical CD</button> : <><label className="disc-rights"><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)}/>I am authorized to make a personal local copy of this disc.</label><button className="primary-button" disabled={busy || blocked || !confirmed || !title.trim() || !artist.trim() || trackTitles.some(name => !name.trim())} onClick={() => void importDisc()}>Digitize to lossless {flacAvailable ? 'FLAC' : 'WAV'}</button><p className="muted small">{flacAvailable ? 'Optional host tools provide FLAC.' : 'WAV uses more storage.'} Review the finished tracks before relying on this copy.</p></>}</div>
      </div>}
    </div>}
    {!!packInfo?.packErrors?.length && <p role="alert" className="disc-pack-error">A local metadata pack was skipped: {packInfo.packErrors.join(', ')}</p>}
  </section>;
}
