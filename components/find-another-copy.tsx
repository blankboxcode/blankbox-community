'use client';

import { ArrowUpRight, Search, ShoppingBag } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { blankBoxClient, type CommerceLink } from '@/lib/blank-box-client';
import { formatsByKind } from '@/lib/collecting-formats';
import type { MediaItem } from '@/lib/media';
import { StoreSearchSources } from '@/components/store-search-sources';

export function FindAnotherCopy({ item, initialFormat = 'Any' }: { item: MediaItem; initialFormat?: string }) {
  const formats = formatsByKind[item.kind];
  const [format, setFormat] = useState(formats?.includes(initialFormat) ? initialFormat : 'Any');
  const [links, setLinks] = useState<CommerceLink[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const request = useRef(0);

  useEffect(() => () => { request.current++; }, []);
  if (!formats || item.sample) return null;

  const search = async () => {
    const current = ++request.current;
    setBusy(true);
    setError('');
    setLinks(null);
    try {
      const result = await blankBoxClient.action('commerce-links', {
        title: item.title, kind: item.kind, year: item.year ?? null, format,
      });
      if (request.current === current) setLinks(result.storeLinks || []);
    } catch (cause) {
      if (request.current === current) setError((cause as Error).message);
    } finally {
      if (request.current === current) setBusy(false);
    }
  };

  return <section className="find-another-copy">
    <div className="where-heading"><span><strong>Store searches</strong><small>Search this title in a format you choose</small></span><ShoppingBag size={18}/></div>
    <div className="find-another-body">
      <div className="find-another-controls">
        <label htmlFor="find-another-format">Format
          <select id="find-another-format" value={format} onChange={event => { request.current++; setFormat(event.target.value); setLinks(null); setError(''); setBusy(false); }}>
            {formats.map(value => <option key={value} value={value}>{value === 'Any' ? 'Any format' : value}</option>)}
          </select>
        </label>
        <button className="subtle-button" type="button" disabled={busy} onClick={() => void search()}><Search size={16}/>{busy ? 'Finding stores…' : 'Show store searches'}</button>
      </div>
      {error && <p className="find-another-error" role="alert">{error}</p>}
      {links && <><div className="find-another-links">{links.length ? links.map(link => <a key={link.retailerId} href={link.url} target="_blank" rel="noopener noreferrer">{link.linkKind === 'store-home' ? `Open ${link.name}` : `Search ${link.name}`}<ArrowUpRight size={14}/></a>) : <span>No store links are configured for this media type.</span>}</div><p className="find-another-note">These are retailer searches, not checked offers. Confirm the listing’s format, edition, price, and availability on the store site.</p></>}
      <StoreSearchSources kind={item.kind} onSaved={() => setLinks(null)}/>
    </div>
  </section>;
}
