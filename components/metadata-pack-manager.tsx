'use client';

import { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { offlinePackName } from '@/lib/offline-metapacks';
import { blankBoxClient, type ApiResult, type MetadataCatalogPack, type MetadataPackInfo } from '@/lib/blank-box-client';

const choices = [
  { id: 'music-work-candidates', label: 'Music', note: 'Album titles, artists and release types. Audio CD editions use separate identifiers.' },
  { id: 'book-work-candidates', label: 'Books', note: 'Book titles and authors, with available ISBN editions.' },
  { id: 'game-work-candidates', label: 'Games', note: 'Awaiting reviewed game sources; future packs can include UPC/EAN release clues.' },
  { id: 'movie-work-candidates', label: 'Movies', note: 'Movie titles, descriptions, genres, release dates, ratings and credits.' },
  { id: 'tv-work-candidates', label: 'TV Shows', note: 'TV series, creators, genres and available season and episode counts.' },
  { id: 'comic-work-candidates', label: 'Comics', note: 'In preparation while issue and variant identities are sorted.' },
] as const;

const packName = (pack: MetadataPackInfo) => offlinePackName(pack.id,pack.displayName);
const packSize = (bytes?: number) => bytes ? bytes < 1048576 ? `${Math.ceil(bytes / 1024)} KB` : `${(bytes / 1048576).toFixed(1)} MB` : '';
const installable = (pack?: MetadataCatalogPack) => pack?.status === 'available' || pack?.status === 'update';

export function MetadataPackManager() {
  const [info, setInfo] = useState<ApiResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [manualFile, setManualFile] = useState<File | null>(null);
  const picker = useRef<HTMLInputElement>(null);
  const refresh = async () => setInfo(await blankBoxClient.action('metadata-pack-list'));
  useEffect(() => { void blankBoxClient.action('metadata-pack-list').then(setInfo).catch(error => toast.error((error as Error).message)); }, []);

  const catalog = new Map((info?.catalogPacks || []).map(pack => [pack.id, pack]));
  const ready = choices.map(choice => catalog.get(choice.id)).filter((pack): pack is MetadataCatalogPack => installable(pack));
  const updates = ready.filter(pack => pack.status === 'update');
  const chosen = selected.filter(id => installable(catalog.get(id)));
  const installed = [...(info?.packs || [])].sort((a, b) => packName(a).localeCompare(packName(b)));

  const install = async (ids: string[]) => {
    if (!ids.length) return;
    setBusy(true);
    const failures: string[] = [];
    let completed = 0;
    try {
      for (const packId of ids) {
        try { await blankBoxClient.action('metadata-pack-install-catalog', { packId }); completed += 1; }
        catch (error) { failures.push(`${packId}: ${(error as Error).message}`); }
      }
      await refresh();
      setSelected([]);
      if (completed) toast.success(`${completed} metadata ${completed === 1 ? 'pack' : 'packs'} installed or updated.`);
      if (failures.length) toast.error(`${failures.length} ${failures.length === 1 ? 'pack' : 'packs'} could not be installed: ${failures.join(' · ')}`);
    } catch (error) { toast.error((error as Error).message); }
    finally { setBusy(false); }
  };

  const remove = async (packId: string) => {
    setBusy(true);
    try {
      await blankBoxClient.action('metadata-pack-remove', { packId });
      await refresh();
      toast.success('Pack removed. Confirmed library metadata remains saved.');
    } catch (error) { toast.error((error as Error).message); }
    finally { setBusy(false); }
  };

  const installProof = async () => {
    setBusy(true);
    try {
      await blankBoxClient.action('metadata-pack-install-bundled', { packId: 'music-proof' });
      await refresh();
      toast.success('Audio CD matching sample installed.');
    } catch (error) { toast.error((error as Error).message); }
    finally { setBusy(false); }
  };

  const upload = async () => {
    if (!manualFile) return;
    setBusy(true);
    try {
      if (!manualFile.name.endsWith('.bbpack')) throw new Error('Choose a .bbpack file.');
      const manifest = await blankBoxClient.uploadMetadataPack(manualFile);
      await refresh();
      toast.success(`${packName(manifest)} installed for offline search.`);
      setManualFile(null);
      if (picker.current) picker.current.value = '';
    } catch (error) { toast.error((error as Error).message); }
    finally { setBusy(false); }
  };

  return <section id="metadata-pack-settings" className="panel" aria-label="Offline Metapacks">
    <h2>Offline Metapacks</h2>
    <p className="muted small">Install title data once, then search locally. You review a match before it joins your collection; confirmed details remain in your catalog if a pack is removed.</p>
    <div className="metadata-pack-choices">
      {choices.map(choice => {
        const pack = catalog.get(choice.id);
        const canInstall = installable(pack);
        const status = !pack ? 'Not available yet' : pack.status === 'available' ? 'Ready to install' : pack.status === 'update' ? 'Update available' : pack.status === 'installed' ? 'Installed' : pack.status === 'installed-newer' ? 'Newer version installed' : pack.status === 'conflict' ? 'Version conflict' : 'Pack unavailable';
        return <div className="metadata-pack-choice" key={choice.id}>
          <label className="metadata-pack-choice-main">
            <input type="checkbox" aria-label={`Select ${choice.label}`} checked={selected.includes(choice.id)} disabled={busy || !canInstall} onChange={event => setSelected(current => event.target.checked ? [...current, choice.id] : current.filter(id => id !== choice.id))}/>
            <span><strong>{choice.label}</strong><small>{pack ? `${pack.recordCount?.toLocaleString()} titles${pack.releaseCount ? ` · ${pack.releaseCount.toLocaleString()} editions` : ''} · v${pack.version} · ${packSize(pack.bundleBytes)}` : 'Awaiting source data'}</small><small>{pack?.description || choice.note}</small><small>{status}{pack?.error ? ` · ${pack.error}` : ''}</small></span>
          </label>
          <button type="button" className="subtle-button" disabled={busy || !canInstall} onClick={() => void install([choice.id])}>{pack?.status === 'update' ? 'Update' : 'Install'}</button>
        </div>;
      })}
    </div>
    {info?.catalogError && <p role="alert" className="error-text">Staged pack list unavailable: {info.catalogError}</p>}
    <div className="settings-actions">
      <button type="button" className="text-button" disabled={busy || !ready.length} onClick={() => setSelected(ready.map(pack => pack.id))}>Select all</button>
      <button type="button" className="subtle-button" disabled={busy || !chosen.length} onClick={() => void install(chosen)}>Install selected</button>
      <button type="button" className="subtle-button" disabled={busy || !ready.length} onClick={() => void install(ready.map(pack => pack.id))}>Install all</button>
      <button type="button" className="subtle-button" disabled={busy || !updates.length} onClick={() => void install(updates.map(pack => pack.id))}>Update installed</button>
    </div>
    <div className="settings-actions">
      <input ref={picker} type="file" accept=".bbpack" aria-label="Choose a metadata pack file" disabled={busy} onChange={event => setManualFile(event.target.files?.[0] || null)}/>
      <button type="button" className="subtle-button" disabled={busy || !manualFile} onClick={() => void upload()}>Upload pack file</button>
    </div>
    <p className="muted small">Packs work offline and can be updated or removed independently. Confirmed metadata stays in your library.</p>
    {installed.length > 0 && <details className="metadata-installed-packs"><summary>Installed Offline Metapacks ({installed.length})</summary><div className="hidden-items-list">{installed.map(pack => <div className="hidden-item-row" key={pack.id}><span><strong>{packName(pack)} · v{pack.version}</strong><small>{pack.recordCount.toLocaleString()} titles{pack.releaseCount ? ` · ${pack.releaseCount.toLocaleString()} editions` : ''}{pack.databaseBytes ? ` · ${packSize(pack.databaseBytes)} installed` : ''}</small>{pack.description&&<small>{pack.description}</small>}<details><summary>Data sources & usage</summary><small>Source: {pack.source}</small><small>Usage classification: {pack.license}</small>{pack.sourceVersion&&<small>Snapshot: {pack.sourceVersion.replace(/; edition-snapshot-sha256=[0-9a-f]{64}/g, '')}</small>}</details></span><button type="button" className="text-button" disabled={busy} onClick={() => void remove(pack.id)}>Remove</button></div>)}</div></details>}
    {info?.bundledProofAvailable && !installed.some(pack => pack.id === 'music-proof') && <button type="button" className="text-button" disabled={busy} onClick={() => void installProof()}>Install Audio CD matching sample</button>}
    {!!info?.packErrors?.length && <div role="alert" className="error-text">{info.packErrors.map(packId => <p key={packId}>Damaged installed pack skipped: {packId}. <button type="button" className="text-button" disabled={busy} onClick={() => void remove(packId)}>Remove damaged pack</button></p>)}</div>}
  </section>;
}
