'use client';

import { useState } from 'react';
import { toast } from 'sonner';
import { blankBoxClient, type MetadataEdition } from '@/lib/blank-box-client';
import { formatsByKind } from '@/lib/collecting-formats';
import type { MediaItem } from '@/lib/media';

export function EditionReferenceActions({ item, edition, disabled, onChanged }: {
  item: MediaItem; edition: MetadataEdition; disabled: boolean; onChanged: () => Promise<void>;
}) {
  const [choosing, setChoosing] = useState(false);
  const [copyId, setCopyId] = useState('');
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const physicalFormats = formatsByKind[item.kind] || [];
  const canBuy = edition.format && physicalFormats.includes(edition.format);
  const copies = item.sources.filter(source => source.type === 'physical' && source.physicalReleaseId && (
    source.label.toLowerCase() === edition.format?.toLowerCase() || item.kind === 'book' &&
    [source.label, edition.format].includes('Book') && ['Book', 'Hardcover', 'Paperback'].includes(source.label)
  ));
  const act = async (action: string, data: Record<string, unknown>) => {
    if (busy || disabled) return;
    setBusy(true);
    try { await blankBoxClient.action(action, data); await onChanged(); return true; }
    catch (cause) { toast.error((cause as Error).message); return false; }
    finally { setBusy(false); }
  };
  const match = async (physicalReleaseId: string, unlink = false) => {
    if (!window.confirm(`${unlink ? 'Remove' : 'Confirm'} this owned copy’s match to ${[edition.format, edition.edition].filter(Boolean).join(' · ')}? Check its ISBN/barcode and edition. This changes the reference match and keeps the owned copy.`)) return;
    if (await act(unlink ? 'metadata-unlink' : 'metadata-confirm', {
      targetType: 'physical_release', targetId: physicalReleaseId, entityId: edition.id, confirm: true,
    })) setChoosing(false);
  };
  if (edition.origin === 'household-copy' || edition.origin === 'household-file') return null;
  return <>
    {canBuy && edition.status !== 'owned' && <button className="text-button" disabled={disabled || busy || saved || edition.wanted} onClick={() => void act('collecting-add', { releaseId: edition.id }).then(ok => {
      if (ok) { setSaved(true); toast.success('Edition added to Wishlist'); }
    })}>{saved || edition.wanted ? 'Intention saved' : 'Wishlist this edition'}</button>}
    {!!copies.length && edition.status !== 'owned' && <button className="text-button" disabled={disabled || busy} onClick={() => {
      setChoosing(!choosing); setCopyId(copies[0].physicalReleaseId!);
    }}>Match owned copy</button>}
    {edition.physicalReleaseIds?.map(id => <button className="text-button" key={id} disabled={disabled || busy} onClick={() => void match(id, true)}>Remove copy match</button>)}
    {choosing && <div className="known-edition-file-link">
      <label className="field"><span>Owned copy matching this edition</span><select value={copyId} onChange={event => setCopyId(event.target.value)}>
        {copies.map(source => <option key={source.id} value={source.physicalReleaseId}>{[source.label, source.edition, source.barcode, source.location, source.ownedCopyId?.slice(-6)].filter(Boolean).join(' · ')}</option>)}
      </select></label>
      <p className="muted small">Confirm only the exact release. A title or format match alone may refer to another edition.</p>
      <button className="subtle-button" disabled={disabled || busy || !copyId} onClick={() => void match(copyId)}>Confirm copy match</button>
    </div>}
  </>;
}
