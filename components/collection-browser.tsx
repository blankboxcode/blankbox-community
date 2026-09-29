'use client';
/* eslint-disable @next/next/no-img-element -- Private library artwork. */

import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { ArrowDown, ArrowLeft, ArrowUp, Check, Layers3, Leaf, Pencil, Plus, Trash2 } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { CollectionRecommendationsPanel } from '@/components/collection-recommendations';
import { useLibraryPage } from '@/hooks/use-library-page';
import { blankBoxClient } from '@/lib/blank-box-client';
import { collectionTypeNames, emptyCollectionRules, itemGenres, orderedCollectionItems, type ActivityStatus, type LibraryCollection } from '@/lib/collection-organization';
import { kindNames, type Kind, type LibraryState, type MediaItem } from '@/lib/media';

type Draft = Pick<LibraryCollection, 'name' | 'kind' | 'rules' | 'startDay' | 'endDay' | 'memberIds'> & { id?: string };
const fresh = (kind: Draft['kind'] = 'manual'): Draft => ({ name: '', kind, rules: { ...emptyCollectionRules }, startDay: '', endDay: '', memberIds: [] });

function CollectionEditor({ draft: initial, items, state, onClose, onSaved }: { draft: Draft; items: MediaItem[]; state:LibraryState; onClose: () => void; onSaved: () => Promise<void> }) {
  const [draft, setDraft] = useState(initial);
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(0);
  const [selectedPage, setSelectedPage] = useState(0);
  const [genre, setGenre] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const explicit = draft.kind === 'manual' || draft.kind === 'series';
  const selectedPageIndex = Math.min(selectedPage, Math.max(0, Math.ceil(draft.memberIds.length / 20) - 1));
  const remote=useLibraryPage(!!state.pagedLibrary,{q:query,sort:'az',offset:page*30,limit:30,excludeSamples:true},state.items);
  const [selectedItems,setSelectedItems]=useState<MediaItem[]>([]);
  const selectedKey=JSON.stringify(draft.memberIds.slice(selectedPageIndex*20,selectedPageIndex*20+20));
  useEffect(()=>{if(!state.pagedLibrary)return;let active=true;void blankBoxClient.selection(JSON.parse(selectedKey) as string[]).then(value=>{if(active)setSelectedItems(value);}).catch(cause=>{if(active)setError((cause as Error).message);});return()=>{active=false;};},[state.pagedLibrary,selectedKey]);
  const available = items.filter(item => !item.sample);

  const lookup = new Map([...available,...selectedItems,...(remote.page?.items||[])].map(item => [item.id, item]));
  const localResults = available.filter(item => `${item.title} ${item.year || ''} ${itemGenres(item).join(' ')}`.toLocaleLowerCase().includes(query.toLocaleLowerCase())).sort((a, b) => a.title.localeCompare(b.title));
  const results=state.pagedLibrary?(remote.page?.items||[]):localResults;
  const resultTotal=state.pagedLibrary?(remote.page?.total||0):localResults.length;
  const visibleResults=state.pagedLibrary?results:results.slice(page*30,page*30+30);
  const genreChoices = state.facets?.genres || [...new Set(available.flatMap(itemGenres))].sort((a, b) => a.localeCompare(b));
  const formatChoices = state.physicalInventory.formats.map(row=>row.label).length?state.physicalInventory.formats.map(row=>row.label):[...new Set(available.flatMap(item => item.sources.filter(source => source.type === 'physical').map(source => source.label)))].sort();
  const dirty = JSON.stringify(draft) !== JSON.stringify(initial);
  const close = () => { if (!busy && (!dirty || window.confirm('Discard unsaved collection changes?'))) onClose(); };
  const rule = <K extends keyof Draft['rules']>(key: K, value: Draft['rules'][K]) => setDraft(current => ({ ...current, rules: { ...current.rules, [key]: value } }));
  const toggle = (id: string) => setDraft(current => ({ ...current, memberIds: current.memberIds.includes(id) ? current.memberIds.filter(value => value !== id) : [...current.memberIds, id] }));
  const move = (index: number, direction: number) => setDraft(current => { const members = [...current.memberIds]; [members[index], members[index + direction]] = [members[index + direction], members[index]]; return { ...current, memberIds: members }; });
  async function save() { setBusy(true); setError(''); try { await blankBoxClient.action('collection-save', { ...draft, memberIds: explicit ? draft.memberIds : [] }); await onSaved(); onClose(); } catch (cause) { setError((cause as Error).message); } finally { setBusy(false); } }
  return <Dialog open onOpenChange={open => !open && close()}><DialogContent className="form-dialog collection-editor-dialog"><DialogHeader><DialogTitle>{draft.id ? 'Edit collection' : 'Create collection'}</DialogTitle><DialogDescription>Group existing titles without moving files or changing ownership.</DialogDescription></DialogHeader>
    <div className="form-grid"><label className="field"><span>Name</span><input maxLength={120} value={draft.name} onChange={event => setDraft({ ...draft, name: event.target.value })} placeholder="Alien films, Halloween nights…"/></label><label className="field"><span>Collection type</span><select value={draft.kind} onChange={event => { const kind = event.target.value as Draft['kind']; setDraft({ ...draft, kind, startDay: kind === 'seasonal' ? draft.startDay : '', endDay: kind === 'seasonal' ? draft.endDay : '' }); }}>{Object.entries(collectionTypeNames).map(([value, name]) => <option key={value} value={value}>{name}</option>)}</select></label></div>
    {explicit ? <>
      <p className="muted small">{draft.kind === 'series' ? 'Choose the titles in this series and put them in order. You can edit the order and membership. Plan missing titles to review your linked reference set.' : 'Choose any titles to keep together.'}</p>
      <label className="field"><span>Find titles</span><input value={query} onChange={event => { setQuery(event.target.value); setPage(0); }} placeholder="Title, year, or genre"/></label>
      <div className="collection-member-picker">{visibleResults.map(item => <label key={item.id}><input type="checkbox" checked={draft.memberIds.includes(item.id)} onChange={() => toggle(item.id)}/><span>{item.title}<small>{kindNames[item.kind]}{item.year ? ` · ${item.year}` : ''}</small></span></label>)}</div>
      {resultTotal > 30 && <div className="collection-paging"><button type="button" disabled={!page} onClick={() => setPage(page - 1)}>Previous</button><span>Page {page + 1} of {Math.ceil(resultTotal / 30)}</span><button type="button" disabled={(page + 1) * 30 >= resultTotal} onClick={() => setPage(page + 1)}>Next</button></div>}
      <details className="collection-selected" open={draft.kind === 'series' || undefined}><summary>{draft.memberIds.length} selected {draft.kind === 'series' ? '· edit series order' : 'titles'}</summary>{draft.memberIds.slice(selectedPageIndex * 20, selectedPageIndex * 20 + 20).map((id, offset) => { const index = selectedPageIndex * 20 + offset; return <div key={id}><span>{index + 1}. {lookup.get(id)?.title || 'Unavailable title'}</span><button type="button" disabled={!index} aria-label={`Move ${lookup.get(id)?.title} earlier`} onClick={() => move(index, -1)}><ArrowUp size={16}/></button><button type="button" disabled={index === draft.memberIds.length - 1} aria-label={`Move ${lookup.get(id)?.title} later`} onClick={() => move(index, 1)}><ArrowDown size={16}/></button><button type="button" aria-label={`Remove ${lookup.get(id)?.title} from collection`} onClick={() => toggle(id)}><Trash2 size={16}/></button></div>; })}{draft.memberIds.length > 20 && <div className="collection-paging"><button type="button" disabled={!selectedPageIndex} onClick={() => setSelectedPage(selectedPageIndex - 1)}>Previous</button><button type="button" disabled={(selectedPageIndex + 1) * 20 >= draft.memberIds.length} onClick={() => setSelectedPage(selectedPageIndex + 1)}>Next</button></div>}</details>
    </> : <>
      <p className="muted small">Updates automatically as titles change. Different rules must all match; choices within a rule match any selected value.</p>
      <fieldset className="collection-rule-options"><legend>Media types · any when empty</legend>{Object.entries(kindNames).map(([kind, name]) => <label key={kind}><input type="checkbox" checked={draft.rules.kinds.includes(kind as Kind)} onChange={() => rule('kinds', draft.rules.kinds.includes(kind as Kind) ? draft.rules.kinds.filter(value => value !== kind) : [...draft.rules.kinds, kind as Kind])}/>{name}</label>)}</fieldset>
      <label className="field"><span>Genres · any when empty</span><div className="collection-label-input"><input list="collection-genre-options" maxLength={80} value={genre} onChange={event => setGenre(event.target.value)} placeholder="Select or enter a genre"/><button className="subtle-button" type="button" disabled={!genre.trim()} onClick={() => { rule('genres', [...new Set([...draft.rules.genres, genre.trim()])]); setGenre(''); }}>Add</button></div><datalist id="collection-genre-options">{genreChoices.map(value => <option key={value} value={value}/>)}</datalist></label>
      <div className="collection-rule-chips">{draft.rules.genres.map(value => <button type="button" key={value} onClick={() => rule('genres', draft.rules.genres.filter(label => label !== value))}>{value} ×</button>)}</div>
      <details><summary>Format, status & year rules</summary><fieldset className="collection-rule-options"><legend>Owned physical formats · any when empty</legend>{formatChoices.map(value => <label key={value}><input type="checkbox" checked={draft.rules.formats.includes(value)} onChange={() => rule('formats', draft.rules.formats.includes(value) ? draft.rules.formats.filter(label => label !== value) : [...draft.rules.formats, value])}/>{value}</label>)}</fieldset><div className="form-grid"><label className="field"><span>Local status</span><select value={draft.rules.status} onChange={event => rule('status', event.target.value as ActivityStatus | '')}><option value="">Any status</option><option value="not-started">Not started / Unwatched</option><option value="in-progress">In progress</option><option value="completed">Completed / Watched</option></select></label><label className="field"><span>From year</span><input type="number" min={1800} max={2200} value={draft.rules.yearFrom ?? ''} onChange={event => rule('yearFrom', event.target.value ? Number(event.target.value) : null)}/></label><label className="field"><span>Through year</span><input type="number" min={1800} max={2200} value={draft.rules.yearTo ?? ''} onChange={event => rule('yearTo', event.target.value ? Number(event.target.value) : null)}/></label></div></details>
      {draft.kind === 'seasonal' && <><div className="form-grid"><label className="field"><span>Starts each year (optional)</span><input type="date" value={draft.startDay ? `2000-${draft.startDay}` : ''} onChange={event => setDraft({ ...draft, startDay: event.target.value.slice(5) })}/></label><label className="field"><span>Ends each year (optional)</span><input type="date" value={draft.endDay ? `2000-${draft.endDay}` : ''} onChange={event => setDraft({ ...draft, endDay: event.target.value.slice(5) })}/></label></div><p className="muted small">Dates repeat annually, including across New Year. Off-season collections stay available. The year in the picker is ignored.</p></>}
    </>}
    {(error||remote.error) && <p role="alert" className="error-text">{error||remote.error}</p>}<button type="button" className="primary-button" disabled={busy || !draft.name.trim()} onClick={() => void save()}><Check size={17}/>{busy ? 'Saving…' : 'Save collection'}</button>
  </DialogContent></Dialog>;
}

export function CollectionBrowser({ state, renderItem, onChange, onPlan }: { state: LibraryState; renderItem: (item: MediaItem) => ReactNode; onChange: () => Promise<void>; onPlan: () => void }) {
  const [selectedId, setSelectedId] = useState('');
  const [genre, setGenre] = useState('');
  const [draft, setDraft] = useState<Draft | null>(null);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const [error, setError] = useState('');
  const [remoteCollections,setRemoteCollections]=useState<LibraryCollection[]>([]);
  useEffect(()=>{if(!state.pagedLibrary)return;let active=true;void blankBoxClient.collections().then(value=>{if(active)setRemoteCollections(value.collections||[]);}).catch(cause=>{if(active)setError((cause as Error).message);});return()=>{active=false;};},[state.pagedLibrary,state.items]);
  const collections = state.pagedLibrary?remoteCollections:state.collections || [];

  const itemLookup = useMemo(() => new Map(state.items.map(item => [item.id, item])), [state.items]);
  const selected = collections.find(collection => collection.id === selectedId);
  const genres = useMemo(() => state.facets?.genres||[...new Set(state.items.flatMap(itemGenres))].sort((a, b) => a.localeCompare(b)), [state.items,state.facets]);
  const members = useMemo(() => selected ? orderedCollectionItems(selected, itemLookup) : genre ? state.items.filter(item => itemGenres(item).some(value => value.toLocaleLowerCase() === genre.toLocaleLowerCase())) : [], [selected, itemLookup, genre, state.items]);
  const localResults = members.filter(item => `${item.title} ${item.year || ''}`.toLocaleLowerCase().includes(search.toLocaleLowerCase()));
  const remote=useLibraryPage(!!state.pagedLibrary&&!!(selectedId||genre),{collection:selectedId,genre,q:search,offset:page*60,limit:60},state.items);
  const results=state.pagedLibrary?(remote.page?.items||[]):localResults;
  const resultTotal=state.pagedLibrary?(remote.page?.total||0):results.length;
  const visibleResults=state.pagedLibrary?results:results.slice(page*60,page*60+60);
  const edit=async()=>{if(!selected)return;try{const record=state.pagedLibrary?(await blankBoxClient.collections(selected.id)).collection:selected;if(record)setDraft({...record,memberIds:record.itemIds});}catch(cause){setError((cause as Error).message);}};
  const remove = async () => { if (!selected || !window.confirm(`Remove the collection “${selected.name}”? Its titles and files remain in your library.`)) return; try { await blankBoxClient.action('collection-remove', { id: selected.id, confirm: true }); setSelectedId(''); await onChange(); } catch (cause) { setError((cause as Error).message); } };
  const open = (id: string, label = '') => { setSelectedId(id); setGenre(label); setSearch(''); setPage(0); };
  return <section className="collections-page">
    <div className="page-heading"><div><h1>{selected?.name || genre || 'Collections'}</h1><p>{selected || genre ? `${resultTotal} titles · ${selected ? collectionTypeNames[selected.kind] : 'Genre'}` : 'Series, genres, and collections you make your own.'}</p></div><div className="page-heading-actions">{selected || genre ? <><button className="subtle-button" onClick={() => open('')}><ArrowLeft size={16}/>All collections</button>{selected ? <><button className="subtle-button" onClick={() => void edit()}><Pencil size={16}/>Edit</button><button className="text-button" onClick={() => void remove()}><Trash2 size={16}/>Remove collection</button></> : <button className="subtle-button" onClick={() => setDraft({ ...fresh('genre'), name: genre, rules: { ...emptyCollectionRules, genres: [genre] } })}><Plus size={16}/>Save genre collection</button>}</> : <button className="primary-button" onClick={() => setDraft(fresh())}><Plus size={16}/>Create collection</button>}</div></div>
    {selected || genre ? <><label className="field"><span>Search this collection</span><input value={search} onChange={event => { setSearch(event.target.value); setPage(0); }}/></label>{selected && (selected.kind === 'series' || selected.completionSetId) && <div className="collection-series-note"><span>{selected.completionCounts ? `${selected.completionCounts.library} of ${selected.completionCounts.known} known reference titles in your library` : 'Your selected series titles, in your chosen order.'}</span><button className="text-button" onClick={onPlan}>Plan missing titles →</button></div>}<div className="poster-grid library-grid">{visibleResults.map(item => <div key={item.id}>{renderItem(item)}</div>)}</div>{!results.length && <p className="muted">No titles match yet. Edit the rules or add titles to your library.</p>}{resultTotal > 60 && <div className="collection-paging"><button disabled={!page} onClick={() => setPage(page - 1)}>Previous</button><span>Page {page + 1} of {Math.ceil(resultTotal / 60)}</span><button disabled={(page + 1) * 60 >= resultTotal} onClick={() => setPage(page + 1)}>Next</button></div>}</> : <>
      <div className="saved-collections-grid">{collections.map(collection => { const covers = (collection.covers||orderedCollectionItems(collection, itemLookup)).filter(item => item.poster).slice(0, 3); return <button className="saved-collection-card" key={collection.id} onClick={() => open(collection.id)}><span className="collection-cover-stack">{covers.length ? covers.map(item => <img key={item.id} src={item.poster} alt="" loading="lazy"/>) : collection.kind === 'seasonal' ? <Leaf size={32}/> : <Layers3 size={32}/>}</span><span><strong>{collection.name}</strong><small>{collection.completionCounts ? `${collection.completionCounts.library} of ${collection.completionCounts.known} known titles in library` : `${collection.titleCount??collection.itemIds.length} titles`} · {collectionTypeNames[collection.kind]}</small>{collection.kind === 'seasonal' && <small>{collection.active ? 'In season' : 'Off season'}{collection.startDay ? ` · ${collection.startDay} – ${collection.endDay}` : ''}</small>}</span></button>; })}</div>
      {!collections.length && <div className="empty-panel"><Layers3 size={36}/><h2>Keep favorite worlds together.</h2><p>Create a series in your chosen order, a personal selection, or an automatically updated genre collection.</p></div>}
      <div className="collection-presets"><h2>Seasonal starting points</h2><button className="subtle-button" onClick={() => setDraft({ ...fresh('seasonal'), name: 'Halloween nights', startDay: '10-01', endDay: '10-31', rules: { ...emptyCollectionRules, kinds: ['movie', 'tv'], genres: ['Horror'] } })}><Leaf size={17}/>Halloween nights</button><button className="subtle-button" onClick={() => setDraft({ ...fresh('seasonal'), name: 'Holiday favorites', startDay: '12-01', endDay: '01-06', rules: { ...emptyCollectionRules, kinds: ['movie', 'tv'], genres: ['Holiday', 'Christmas'] } })}>Holiday favorites</button><p className="muted small">Review the rules before saving. Add custom genres in Edit details to include your household favorites.</p></div>
      {state.mode === 'box' && <CollectionRecommendationsPanel onSaved={onChange}/>}
      <section className="collection-genre-browser"><h2>Browse by genre</h2><div className="collection-rule-chips">{genres.map(label => <button key={label} onClick={() => open('', label)}>{label}</button>)}</div>{!genres.length && <p className="muted">Add genres or custom genres in an item’s Edit details.</p>}</section>
    </>}
    {error && <p role="alert" className="error-text">{error}</p>}{draft && <CollectionEditor draft={draft} items={state.items} state={state} onClose={() => setDraft(null)} onSaved={onChange}/>}
  </section>;
}
