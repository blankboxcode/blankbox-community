'use client';

import { useEffect, useMemo, useState } from 'react';
import { ArrowUpRight, Pencil, Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { blankBoxClient, type CollectingTarget, type CompletionSet, type CollectionSuggestion, type CommerceLink } from '@/lib/blank-box-client';
import { formatsByKind } from '@/lib/collecting-formats';
import type { Kind, MediaItem } from '@/lib/media';
import { CompletionSetEditor } from '@/components/completion-set-editor';
import { CollectionRecommendationsPanel } from '@/components/collection-recommendations';
import { WishlistPurchase } from '@/components/preorder-tracker';
import { StoreSearchSources } from '@/components/store-search-sources';

type Work = { title: string; kind: Kind; year: number | null; format: string; edition?: string | null; releaseId?: string | null; season?: string | null; workId?: string | null };
const kinds: Kind[] = ['movie', 'tv', 'music', 'book', 'comic', 'game'];
function key(value: string) { return value.toLocaleLowerCase().replace(/[^\p{L}\p{N}]/gu, ''); }
export function CollectionPlanner({ mode, onChange, onPreorder }: { onPreorder?: (target: CollectingTarget) => void; items: MediaItem[]; mode: 'box'; onChange: () => Promise<void> }) {
  const [purchased, setPurchased] = useState<CollectingTarget | null>(null);
  const [targets, setTargets] = useState<CollectingTarget[]>([]);
  const [sets, setSets] = useState<CompletionSet[]>([]);
  const [suggestions, setSuggestions] = useState<CollectionSuggestion[]>([]);
  const [selectedSetId, setSelectedSetId] = useState('');
  const [editingSet, setEditingSet] = useState<CompletionSet | null>(null);
  const [editingId, setEditingId] = useState('');
  const [title, setTitle] = useState('');
  const [kind, setKind] = useState<Kind>('movie');
  const [format, setFormat] = useState('4K UHD Blu-ray');
  const [year, setYear] = useState('');
  const [season, setSeason] = useState('');
  const [edition, setEdition] = useState('');
  const [busy, setBusy] = useState(false);
  const [storeFor, setStoreFor] = useState<string | null>(null);
  const [storeLinksFor, setStoreLinksFor] = useState<CommerceLink[]>([]);
  const selectedSet = sets.find(set => set.id === selectedSetId);
  const savedKeys = useMemo(() => new Set(targets.map(target => `${target.kind}:${key(target.title)}:${target.year || ''}:${target.format}:${target.season || ''}:${target.edition || ''}`)), [targets]);
  const refresh = async () => { if (mode === 'box') { const result = await blankBoxClient.collecting(); setTargets(result.targets); setSets(result.sets || []); setSuggestions(result.suggestions || []); await onChange(); } };
  useEffect(() => { if (mode === 'box') void blankBoxClient.collecting().then(result => { setTargets(result.targets); setSets(result.sets || []); setSuggestions(result.suggestions || []); }).catch(error => toast.error((error as Error).message)); }, [mode]);
  const save = async (work: Work) => {
    setBusy(true);
    try {
      await blankBoxClient.action('collecting-add', { title: work.title, kind: work.kind, year: work.year, format: work.format, edition: work.edition || '', season: work.season || null, ...(work.releaseId ? { releaseId: work.releaseId } : {}), ...(work.workId ? { workId: work.workId } : {}) });
      await refresh();
      toast.success('Added to Wishlist');
      return true;
    } catch (error) { toast.error((error as Error).message); return false; }
    finally { setBusy(false); }
  };
  const remove = async (target: CollectingTarget) => {
    if (!window.confirm(`Remove “${target.title}” (${target.format}) from Wishlist?`)) return;
    setBusy(true);
    try { await blankBoxClient.action('collecting-remove', { id: target.id, confirmId: target.id }); await refresh(); }
    catch (error) { toast.error((error as Error).message); }
    finally { setBusy(false); }
  };
  const edit = (target: CollectingTarget) => {
    setEditingId(target.id); setTitle(target.title); setKind(target.kind); setFormat(target.format); setYear(target.year ? String(target.year) : ''); setSeason(target.season || ''); setEdition(target.edition || '');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };
  const storeSearch = async (target: CollectingTarget) => {
    if (storeFor === target.id) { setStoreFor(null); return; }
    try { const result = await blankBoxClient.action('commerce-links', { title: target.title, kind: target.kind, year: target.year, format: target.format, season: target.season }); setStoreLinksFor(result.storeLinks || []); setStoreFor(target.id); }
    catch (error) { toast.error((error as Error).message); }
  };
  const removeSet = async (set: CompletionSet) => {
    if (!window.confirm(`Remove completion set “${set.name}”? Your owned items and intentions stay intact.`)) return;
    setBusy(true);
    try { await blankBoxClient.action('completion-set-remove', { id: set.id, confirmId: set.id }); await refresh(); if (selectedSetId === set.id) setSelectedSetId(''); }
    catch (error) { toast.error((error as Error).message); }
    finally { setBusy(false); }
  };
  const ignoreMember = async (set: CompletionSet, position: number, ignored: boolean) => {
    setBusy(true);
    try { await blankBoxClient.action('completion-member-ignore', { setId: set.id, position, ignored }); await refresh(); }
    catch (error) { toast.error((error as Error).message); }
    finally { setBusy(false); }
  };
  const storeLinks = (id: string) => storeFor === id && <div className="collecting-store-links"><p>Stores shown are relevant to this media type. These links open retailer searches online; Hamilton Book opens its store search page. Check each result’s format and edition. Blank Box has not checked stock, shipping, or price.</p>{storeLinksFor.map(store => <a key={store.retailerId} href={store.url} target="_blank" rel="noopener noreferrer">{store.linkKind === 'store-home' ? `Open ${store.name}` : `Search ${store.name}`}<ArrowUpRight size={15}/></a>)}</div>;
  if (mode !== 'box') return <section className="panel"><h2>Collection planning is available in self-hosted Blank Box</h2><p>Saved intentions stay in your local catalog.</p></section>;
  return <div className="collecting-page">
    {purchased && <WishlistPurchase key={purchased.id} target={purchased} onClose={() => setPurchased(null)} onSaved={() => { setPurchased(null); void refresh(); }}/>}
    <div className="page-heading"><div><h1>Wishlist</h1><p>Save titles you plan to buy. Move purchases awaiting delivery to Preorders, or add copies you already have to My Library.</p></div></div>
    <section className="panel"><div className="section-heading"><h2>Your wishlist</h2><span className="muted">{targets.length} wanted titles</span></div><StoreSearchSources kind={kind} onSaved={() => setStoreFor(null)}/>{!targets.length ? <p className="muted">Add a title below or choose a metadata suggestion.</p> : targets.map(target => <div className="collecting-row" key={target.id}><span><strong>{target.title}{target.season ? ` · ${target.season === 'specials' ? 'Specials' : target.season === 'complete-series' ? 'Complete series' : `Season ${target.season}`}` : ''}</strong><small>{[target.year, target.kind, target.format, target.edition, target.identifier ? `${target.identifier.namespace === 'isbn' ? 'ISBN' : 'UPC/EAN'} ${target.identifier.value}` : null].filter(Boolean).join(' · ')} · {target.releaseId ? 'Linked edition' : target.workId ? 'Linked work' : 'Title clue'} · {target.status}</small></span><div className="collecting-row-actions"><button className="subtle-button" disabled={busy} onClick={() => setPurchased(target)}>Bought / add to library</button>{onPreorder && <button className="subtle-button" disabled={busy} onClick={() => onPreorder(target)}>Preorder</button>}<button className="subtle-button" onClick={() => void storeSearch(target)} aria-expanded={storeFor === target.id}>Find stores online</button><button className="text-button" disabled={busy} aria-label={`Edit ${target.title}`} onClick={() => edit(target)}><Pencil size={16}/></button><button className="text-button" disabled={busy} aria-label={`Remove ${target.title}`} onClick={() => void remove(target)}><Trash2 size={16}/></button></div>{storeLinks(target.id)}</div>)}</section>
    <section className="panel"><div className="section-heading"><h2>{editingId ? 'Edit wishlist item' : 'Add a title'}</h2></div><form className="collecting-add" onSubmit={event => { event.preventDefault(); const work = { title, kind, year: year ? Number(year) : null, format, edition, season: kind === 'tv' ? season || null : null }; if (editingId) { setBusy(true); void blankBoxClient.action('collecting-update', { ...work, id: editingId }).then(async () => { await refresh(); setEditingId(''); setTitle(''); toast.success('Wishlist updated.'); }).catch(error => toast.error((error as Error).message)).finally(() => setBusy(false)); } else void save(work).then(saved => { if (saved) setTitle(''); }); }}>
      <label className="field"><span>Title</span><input value={title} required maxLength={250} onChange={event => setTitle(event.target.value)} placeholder="A movie, album, book…"/></label>
      <label className="field"><span>Media type</span><select value={kind} onChange={event => { const next = event.target.value as Kind; setKind(next); setFormat(formatsByKind[next][1] || 'Any'); setSeason(''); setEdition(''); }}>{kinds.map(value => <option key={value} value={value}>{value}</option>)}</select></label>
      <label className="field"><span>Wanted format</span><select value={format} onChange={event => setFormat(event.target.value)}>{formatsByKind[kind].map(value => <option key={value}>{value}</option>)}</select></label>
      <label className="field"><span>Wanted edition, if known</span><input value={edition} maxLength={120} onChange={event => setEdition(event.target.value)} placeholder="Printing, cut, or collector’s edition"/></label>
      <label className="field"><span>Year, if known</span><input type="number" min="1800" max="2200" value={year} onChange={event => setYear(event.target.value)}/></label>
      {kind === 'tv' && <label className="field"><span>Wanted season</span><select value={season} onChange={event => setSeason(event.target.value)}><option value="">Whole series or unknown</option><option value="complete-series">Complete series</option><option value="specials">Specials</option>{Array.from({ length: 99 }, (_, index) => <option key={index + 1} value={String(index + 1)}>Season {index + 1}</option>)}</select></label>}
      <div className="collecting-form-actions"><button className="primary-button" disabled={busy}><Plus size={17}/>{editingId ? 'Save wishlist item' : 'Add to Wishlist'}</button>{editingId && <button className="text-button" type="button" onClick={() => { setEditingId(''); setTitle(''); }}>Cancel edit</button>}</div>
    </form></section>
    <CollectionRecommendationsPanel onSaved={refresh} onIntend={member => save({ ...member, format: member.kind === kind ? format : 'Any' })}/>
    <section className="panel"><div className="section-heading"><h2>What am I missing?</h2><span className="muted">{suggestions.reduce((count, group) => count + group.items.length, 0)} suggestions</span></div><p className="muted">Blank Box groups known edition gaps, saved-set gaps, and candidate works by creators already on your shelf. Creator matches are ideas to review, not a claim that you need every title. Confirm the work and format before adding an intention.</p>
      {suggestions.length ? suggestions.map(group => <div className="collecting-suggestion-group" key={group.id}><h3>{group.name}</h3><p className="muted small">{group.basis === 'known-editions' ? 'Saved or installed release references · coverage may be incomplete' : group.basis === 'creator-candidates' ? 'Installed metadata pack · same creator; collection coverage is not established' : group.basis === 'provider-seasons' ? 'Connected catalog seasons with no matching physical season recorded' : group.basis === 'reviewed-membership' ? 'Reviewed reference membership' : 'Your saved collection set'}</p>{group.items.map((work, index) => { const saved = !work.releaseId && savedKeys.has(`${work.kind}:${key(work.title)}:${work.year || ''}:${work.format}:${work.season || ''}:${work.edition || ''}`); return <div className="collecting-row" key={`${work.releaseId || work.workId || work.title}-${work.season || ''}-${index}`}><span><strong>{work.title}{work.season ? ` · ${work.season === 'specials' ? 'Specials' : work.season === 'complete-series' ? 'Complete series' : `Season ${work.season}`}` : ''}</strong><small>{[work.year, work.format !== 'Any' ? work.format : null, work.edition].filter(Boolean).join(' · ')}{work.status === 'review' || work.outcome === 'review' ? ' · Review which edition your copy is' : work.outcome === 'wanted' ? ' · Already intended' : group.basis === 'known-editions' ? ' · No matching edition recorded' : group.basis === 'creator-candidates' ? ' · Work candidate' : group.basis === 'provider-seasons' ? ' · No matching physical season recorded' : ' · Missing from this set'}</small></span><button className="subtle-button" disabled={busy || saved || work.outcome === 'wanted'} onClick={() => void save(work)}>{saved || work.outcome === 'wanted' ? 'Saved' : 'Wishlist'}</button></div>; })}</div>) : <p className="muted small">No known edition gaps, set gaps, or creator candidates are available yet. Confirm work metadata and install packs with edition records to expand coverage. An empty result does not establish a complete collection.</p>}
    </section>
    {!!sets.length && <section className="panel"><div className="section-heading"><h2>Saved collection sets</h2><span className="muted">{sets.length}</span></div><label className="field"><span>Review a set</span><select value={selectedSetId} onChange={event => setSelectedSetId(event.target.value)}><option value="">Choose a set</option>{sets.map(set => <option value={set.id} key={set.id}>{set.name}</option>)}</select></label>{selectedSet && <><button className="subtle-button" disabled={busy} onClick={() => setEditingSet(selectedSet)}><Pencil size={15}/>Edit titles & order</button>{selectedSet.members.map(member => <div className="collecting-row" key={member.position}><span><strong>{member.title}</strong><small>{member.outcome}{member.workId ? ' · linked work' : ' · title clue'}</small></span><button className="text-button" disabled={busy} onClick={() => void ignoreMember(selectedSet, member.position, !member.ignored)}>{member.ignored ? 'Include' : 'Ignore'}</button></div>)}<button className="text-button" disabled={busy} onClick={() => void removeSet(selectedSet)}><Trash2 size={15}/>Remove set</button></>}</section>}

    {editingSet && <CompletionSetEditor set={editingSet} onClose={() => setEditingSet(null)} onSaved={refresh}/>}
  </div>;
}
