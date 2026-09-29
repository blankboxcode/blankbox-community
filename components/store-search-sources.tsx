'use client';

import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { blankBoxClient, type CustomStoreSource, type StoreSource } from '@/lib/blank-box-client';
import { kindNames, type Kind } from '@/lib/media';

const kinds: Kind[] = ['movie', 'tv', 'music', 'book', 'comic', 'game'];

export function StoreSearchSources({ kind, onSaved }: { kind: Kind; onSaved?: () => void }) {
  const [open, setOpen] = useState(false);
  const [selectedKind, setSelectedKind] = useState<Kind>(kind);
  const [sources, setSources] = useState<StoreSource[]>([]);
  const [custom, setCustom] = useState<CustomStoreSource[]>([]);
  const [name, setName] = useState('');
  const [urlTemplate, setUrlTemplate] = useState('');
  const [mediaKinds, setMediaKinds] = useState<Kind[]>([kind]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    void blankBoxClient.action('commerce-sources').then(result => {
      setSources(result.storeSources || []);
      setCustom(result.customStoreSources || []);
    }).catch(error => toast.error((error as Error).message));
  }, [open]);

  const save = async (nextSources = sources, nextCustom = custom) => {
    setBusy(true);
    try {
      const result = await blankBoxClient.action('commerce-save-sources', {
        packagedSources: nextSources.map(source => ({ id: source.id, enabledKinds: source.enabledKinds })), customSources: nextCustom,
      });
      setSources(result.storeSources || nextSources);
      setCustom(result.customStoreSources || nextCustom);
      onSaved?.();
      toast.success('Store searches saved.');
      return true;
    } catch (error) { toast.error((error as Error).message); return false; }
    finally { setBusy(false); }
  };

  const addCustom = () => {
    if (!name.trim() || !urlTemplate.trim() || !mediaKinds.length) { toast.error('Enter a store name, search URL, and media type.'); return; }
    const next = [...custom, { id: `custom-${crypto.randomUUID().replaceAll('-', '')}`, name: name.trim(), urlTemplate: urlTemplate.trim(), mediaKinds }];
    void save(sources, next).then(saved => { if (saved) { setName(''); setUrlTemplate(''); setMediaKinds([kind]); } });
  };

  return <div className="store-source-settings">
    <button className="text-button" type="button" aria-expanded={open} onClick={() => setOpen(!open)}>{open ? 'Close store choices' : 'Choose store searches'}</button>
    {open && <div className="store-source-editor">
      <p className="muted small">{sources.length} stores available. Enable the stores you use for each media type. Some open the store for you to search there. Custom links stay in this household.</p>
      <label className="field"><span>Media type</span><select value={selectedKind} onChange={event => setSelectedKind(event.target.value as Kind)}>{kinds.map(value => <option key={value} value={value}>{kindNames[value]}</option>)}</select></label>
      <div className="store-source-options store-source-packaged">{sources.filter(source => source.mediaKinds.includes(selectedKind)).map(source => <label key={source.id}><input type="checkbox" checked={source.enabledKinds.includes(selectedKind)} onChange={event => setSources(current => current.map(row => row.id === source.id ? { ...row, enabledKinds: event.target.checked ? [...row.enabledKinds, selectedKind] : row.enabledKinds.filter(value => value !== selectedKind) } : row))}/><span>{source.name}{source.linkKind==='store-home'&&<small>Open store to search</small>}</span></label>)}</div>
      <button className="subtle-button" type="button" disabled={busy || !sources.length} onClick={() => void save()}>Save store choices</button>
      {custom.length > 0 && <div className="store-source-options">{custom.map(source => <div key={source.id}><strong>{source.name}</strong><small> · {source.mediaKinds.join(', ')}</small><button className="text-button" type="button" disabled={busy} onClick={() => void save(sources, custom.filter(row => row.id !== source.id))}>Remove</button></div>)}</div>}
      <div className="store-source-custom"><strong>Add your store search</strong><label className="field"><span>Store name</span><input value={name} maxLength={80} onChange={event => setName(event.target.value)}/></label><label className="field"><span>HTTPS search URL with {'{query}'}</span><input value={urlTemplate} onChange={event => setUrlTemplate(event.target.value)} placeholder="https://example.com/search?q={query}"/></label><div className="store-source-options" aria-label="Media types sold">{kinds.map(value => <label key={value}><input type="checkbox" checked={mediaKinds.includes(value)} onChange={event => setMediaKinds(current => event.target.checked ? [...current, value] : current.filter(choice => choice !== value))}/>{kindNames[value]}</label>)}</div><button className="subtle-button" type="button" disabled={busy} onClick={addCustom}>Add store</button></div>
    </div>}
  </div>;
}
