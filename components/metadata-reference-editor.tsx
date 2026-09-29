'use client';

import { useState } from 'react';
import { blankBoxClient, type MetadataEntity } from '@/lib/blank-box-client';

export function MetadataReferenceEditor({ entityId, onChanged }: { entityId: string; onChanged: (entity: MetadataEntity) => void }) {
  const [entity, setEntity] = useState<MetadataEntity | null>(null);
  const [title, setTitle] = useState('');
  const [year, setYear] = useState('');
  const [artist, setArtist] = useState('');
  const [author, setAuthor] = useState('');
  const [publisher, setPublisher] = useState('');
  const [platform, setPlatform] = useState('');
  const [namespace, setNamespace] = useState('');
  const [identifierValue, setIdentifierValue] = useState('');
  const [replacement, setReplacement] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const refresh = (next: MetadataEntity, changed: boolean) => {
    setEntity(next);
    setTitle(next.title);
    setYear(next.year === null ? '' : String(next.year));
    setArtist(String(next.fields.find(field => field.field === 'artist' && field.owner_entered)?.value ?? next.fields.find(field => field.field === 'artist')?.value ?? ''));
    for (const [field, setter] of [['author', setAuthor], ['publisher', setPublisher], ['platform', setPlatform]] as const) {
      setter(String(next.fields.find(row => row.field === field && row.owner_entered)?.value ?? next.fields.find(row => row.field === field)?.value ?? ''));
    }
    if (changed) onChanged(next);
  };
  const run = async (task: () => Promise<MetadataEntity>, changed = true) => {
    setBusy(true); setError('');
    try { refresh(await task(), changed); }
    catch (cause) { setError((cause as Error).message); }
    finally { setBusy(false); }
  };
  if (!entity) return <div><button type="button" className="text-button" disabled={busy} onClick={() => void run(() => blankBoxClient.metadataGet(entityId), false)}>Edit selected local reference</button>{error && <p role="alert" className="error-text">{error}</p>}</div>;
  return <div className="metadata-reference-editor">
    <p className="muted small">{entity.level === 'release' ? 'Release' : 'Work'} reference · {entity.origin}. Owner edits remain local and keep the source evidence below.</p>
    <label className="field"><span>Reference title</span><input maxLength={250} value={title} onChange={event => setTitle(event.target.value)}/></label>
    <button type="button" className="subtle-button" disabled={busy || !title.trim() || title.trim() === entity.title} onClick={() => void run(() => blankBoxClient.metadataEdit(entityId, 'title', title.trim()))}>Save title</button>
    <label className="field"><span>Reference year</span><input type="number" min="1800" max="2200" value={year} onChange={event => setYear(event.target.value)}/></label>
    <button type="button" className="subtle-button" disabled={busy || (year ? !Number.isInteger(Number(year)) || Number(year) < 1800 || Number(year) > 2200 : false) || (year ? Number(year) : null) === entity.year} onClick={() => void run(() => blankBoxClient.metadataEdit(entityId, 'year', year ? Number(year) : null))}>Save year</button>
    {entity.kind === 'music' && <><label className="field"><span>Artist</span><input maxLength={250} value={artist} onChange={event => setArtist(event.target.value)}/></label><button type="button" className="subtle-button" disabled={busy} onClick={() => void run(() => blankBoxClient.metadataEdit(entityId, 'artist', artist.trim()))}>Save artist</button></>}
    {entity.kind === 'book' && <><label className="field"><span>Author</span><input maxLength={250} value={author} onChange={event => setAuthor(event.target.value)}/></label><button type="button" className="subtle-button" disabled={busy} onClick={() => void run(() => blankBoxClient.metadataEdit(entityId, 'author', author.trim()))}>Save author</button></>}
    {(entity.kind === 'book' || entity.kind === 'game') && <><label className="field"><span>Publisher</span><input maxLength={250} value={publisher} onChange={event => setPublisher(event.target.value)}/></label><button type="button" className="subtle-button" disabled={busy} onClick={() => void run(() => blankBoxClient.metadataEdit(entityId, 'publisher', publisher.trim()))}>Save publisher</button></>}
    {entity.kind === 'game' && entity.level === 'release' && <><label className="field"><span>Platform</span><input maxLength={120} value={platform} onChange={event => setPlatform(event.target.value)}/></label><button type="button" className="subtle-button" disabled={busy} onClick={() => void run(() => blankBoxClient.metadataEdit(entityId, 'platform', platform.trim()))}>Save platform</button></>}
    <div className="metadata-identifier-editor"><strong>Identifiers</strong><p className="muted small">Blank Box references, physical identifiers and your source mappings. Attached sources have their own IDs and resolve to this household item.</p>
      {entity.identifiers.map(identifier => {
        const key = `${identifier.namespace}:${identifier.value}:${identifier.source}:${identifier.source_record_id}`;
        return <div key={key} className="metadata-identifier-row"><span>{identifier.namespace}: {identifier.value} <small>({identifier.source})</small></span>{identifier.source === 'owner' && <><input aria-label={`New value for ${identifier.namespace}`} maxLength={512} value={replacement[key] ?? identifier.value} onChange={event => setReplacement(current => ({ ...current, [key]: event.target.value }))}/><button type="button" className="text-button" disabled={busy || !replacement[key]?.trim() || replacement[key] === identifier.value} onClick={() => void run(() => blankBoxClient.metadataIdentifier(entityId, 'update', identifier.namespace, identifier.value, replacement[key].trim()))}>Update</button><button type="button" className="text-button" disabled={busy} onClick={() => void run(() => blankBoxClient.metadataIdentifier(entityId, 'remove', identifier.namespace, identifier.value))}>Remove</button></>}</div>;
      })}
      <label className="field"><span>Identifier namespace</span><input maxLength={64} value={namespace} onChange={event => setNamespace(event.target.value)} placeholder="isbn or upc-ean"/></label>
      <label className="field"><span>Identifier value</span><input maxLength={512} value={identifierValue} onChange={event => setIdentifierValue(event.target.value)}/></label>
      <button type="button" className="subtle-button" disabled={busy || !namespace.trim() || !identifierValue.trim()} onClick={() => void run(() => blankBoxClient.metadataIdentifier(entityId, 'add', namespace.trim(), identifierValue.trim()))}>Add identifier</button>
    </div>
    <details><summary>Field provenance</summary><div className="muted small">{entity.fields.map((field, index) => <p key={`${field.field}:${field.source}:${index}`}>{field.field}: {typeof field.value==='object'?JSON.stringify(field.value):String(field.value)} · {field.source} · {field.license}</p>)}</div></details>
    {error && <p role="alert" className="error-text">{error}</p>}
  </div>;
}
