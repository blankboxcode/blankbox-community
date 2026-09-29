'use client';

import { useEffect, useState } from 'react';
import { blankBoxClient, type CatalogIdentity } from '@/lib/blank-box-client';
import type { MediaItem } from '@/lib/media';

export function CatalogIdentitySummary({ item }: { item: MediaItem }) {
  const [identity, setIdentity] = useState<CatalogIdentity | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    void blankBoxClient.catalogIdentity(item.id).then(result => {
      if (active) { setIdentity(result); setError(''); }
    }).catch(cause => { if (active) setError((cause as Error).message); });
    return () => { active = false; };
  }, [item.id]);

  if (error) return <p role="alert" className="error-text">{error}</p>;
  if (!identity) return null;

  const references = identity.references.filter(row => row.relationship !== 'local-work');
  const evidence = identity.fieldEvidence.filter(row => row.source !== 'legacy:household');
  return <details className="item-detail-identity">
    <summary>Identity & metadata evidence</summary>
    <p>Library item ID: <code>{identity.itemId}</code>. Attached copies, files, and connected sources resolve to this item.</p>
    <p>{identity.sources.length} attached {identity.sources.length === 1 ? 'source' : 'sources'} · {references.length} saved metadata {references.length === 1 ? 'link' : 'links'} · {evidence.length} recorded metadata {evidence.length === 1 ? 'fact' : 'facts'}</p>
    {references.length > 0 && <ul>{references.map(row => <li key={`${row.id}:${row.relationship}`}><strong>{row.title}</strong> · {row.origin} · {row.level}{row.identifiers.length > 0 ? ` · ${row.identifiers.map(identifier => `${identifier.namespace}: ${identifier.value}`).join(', ')}` : ''}</li>)}</ul>}
    {evidence.length > 0 && <details><summary>Review recorded facts</summary><ul>{evidence.map((row, index) => <li key={`${row.entityId}:${row.field}:${row.source}:${row.sourceRecordId}:${index}`}><strong>{row.field}</strong>: {String(row.value).slice(0, 240)} <small>({row.source})</small></li>)}</ul></details>}
  </details>;
}
