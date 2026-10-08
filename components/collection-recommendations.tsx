'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Check, Layers3, Plus, X } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { blankBoxClient, type CollectionRecommendation, type CollectionRecommendationMember, type CollectionRecommendations } from '@/lib/blank-box-client';
import { kindNames } from '@/lib/media';

export function CollectionRecommendationsPanel({ onSaved, onIntend }: { onSaved: () => Promise<void>; onIntend?: (member: CollectionRecommendationMember) => Promise<boolean> }) {
  const [data, setData] = useState<CollectionRecommendations | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [approvalJob, setApprovalJob] = useState('');
  const [message, setMessage] = useState('');
  const [shown, setShown] = useState(6);
  const [review, setReview] = useState<CollectionRecommendation | null>(null);
  const [name, setName] = useState('');
  const [selected, setSelected] = useState<string[]>([]);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const loadedReferenceGenres = useRef(false);
  const onSavedRef = useRef(onSaved);
  useEffect(() => { onSavedRef.current = onSaved; }, [onSaved]);
  const refresh = useCallback(async () => { try { const result = await blankBoxClient.action('collection-recommendations', {}); setData(result as unknown as CollectionRecommendations); setError(''); } catch (cause) { setError((cause as Error).message); } }, []);
  useEffect(() => { let active = true; void blankBoxClient.action('collection-recommendations', {}).then(result => { if (active) setData(result as unknown as CollectionRecommendations); }).catch(cause => { if (active) setError((cause as Error).message); }); return () => { active = false; }; }, []);
  useEffect(() => {
    if (data?.indexStatus !== 'building' && !approvalJob) return;
    let active = true; let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const status = await blankBoxClient.jobs(); if (!active) return;
        if (approvalJob) {
          const job = status.jobs.find(value => value.id === approvalJob);
          if (job && !['queued', 'running'].includes(job.status)) {
            setApprovalJob(''); setBusy(false);
            await onSavedRef.current(); await refresh();
            if (job.status === 'complete') setMessage(job.message || 'Collections created.');
            else setError(job.message || 'Collections could not be created. Refresh and try again.');
            return;
          }
        } else if (status.collectionIndexStatus !== 'building') { await refresh(); return; }
      } catch (cause) { if (active) setError((cause as Error).message); }
      if (active) timer = setTimeout(() => void poll(), 3000);
    }
    timer = setTimeout(() => void poll(), 3000);
    return () => { active = false; clearTimeout(timer); };
  }, [data?.indexStatus, approvalJob, refresh]);
  useEffect(() => { if (data?.indexStatus !== 'ready' || loadedReferenceGenres.current) return; loadedReferenceGenres.current = true; void onSaved().catch(cause => setError((cause as Error).message)); }, [data?.indexStatus, onSaved]);
  const open = (group: CollectionRecommendation) => { setReview(group); setName(group.name); setSelected(group.members.map(member => member.key)); setError(''); };
  const dirty = review && (name !== review.name || selected.length !== review.members.length);
  const close = () => { if (!busy && (!dirty || window.confirm('Discard unsaved collection changes?'))) setReview(null); };
  async function save() {
    if (!review) return;
    setBusy(true);
    try { await blankBoxClient.action('collection-recommendation-save', { recommendationId: review.id, name, memberKeys: selected }); setReview(null); await onSaved(); await refresh(); }
    catch (cause) { setError((cause as Error).message); } finally { setBusy(false); }
  }
  async function hide(group: CollectionRecommendation) { setBusy(true); try { await blankBoxClient.action('collection-recommendation-dismiss', { recommendationId: group.id }); await refresh(); } catch (cause) { setError((cause as Error).message); } finally { setBusy(false); } }
  async function approveAll() {
    if (!data?.recommendations.length || busy) return;
    setBusy(true); setError(''); setMessage('');
    try {
      const result = await blankBoxClient.action('collection-recommendations-approve', { recommendationIds: data.recommendations.map(group => group.id) });
      if (!result.id) throw new Error('The collection operation did not start.');
      setApprovalJob(result.id);
    } catch (cause) { setError((cause as Error).message); setBusy(false); }
  }
  async function intend(member: CollectionRecommendationMember) { if (!onIntend) return; setBusy(true); try { if (await onIntend(member)) await refresh(); } finally { setBusy(false); } }
  return <section className="collection-recommendations panel">
    <div className="section-heading"><h2><Layers3 size={20}/>Suggested collections</h2><div className="collection-recommendation-actions">{!!data?.recommendations.length && <button className="subtle-button" disabled={busy || data.indexStatus !== 'ready'} title="Create editable collections and plans using the suggested names and all listed members. No buying intentions are added." onClick={() => void approveAll()}><Check size={15}/>{approvalJob ? 'Creating collections…' : `Approve all (${data.recommendations.length})`}</button>}<button className="text-button" disabled={busy} onClick={() => void refresh()}>Refresh suggestions</button></div></div>
    <p className="muted">Built around titles in your library. Review the members and make each collection your own. Counts cover known references, including connected titles; they do not count owned discs or certify a complete franchise.</p>
    {!data && !error && <p className="muted" role="status">Reading your library and offline metadata…</p>}
    {data?.recommendations.slice(0, shown).map(group => <article className="collection-recommendation" key={group.id}>
      <div className="section-heading"><div><h3>{group.name}</h3><p className="small">{group.counts.library} of {group.counts.known} known {group.coverage === 'household-only' ? 'household' : 'reference'} titles in your library{group.counts.wanted ? ` · ${group.counts.wanted} intended` : ''}</p></div><button className="text-button" disabled={busy} aria-label={`Hide ${group.name} suggestion`} onClick={() => void hide(group)}><X size={16}/></button></div>
      <p className="muted small">{kindNames[group.kind]} · {group.basis === 'studio' ? 'Recorded studio · may span different series and film types' : group.basis === 'title-pattern' ? 'Shared title pattern · review series membership and alternate titles' : 'Saved collection labels · full membership beyond this library is unknown'}</p>
      <details onToggle={event => { const opened = event.currentTarget.open; setExpanded(current => { const next = new Set(current); if (opened) next.add(group.id); else next.delete(group.id); return next; }); }}><summary>View titles and gaps</summary>{expanded.has(group.id) && <div className="collection-reference-members">{group.members.map(member => <div className="collecting-row" key={member.key}><span><strong>{member.title}</strong><small>{member.year || 'Year unknown'}{member.creators?.length ? ` · ${member.creators.slice(0,2).join(', ')}` : ''} · {member.status === 'library' ? 'In your library' : member.status === 'wanted' ? 'Intended to buy' : member.status === 'review' ? 'Review library match' : 'Not in your library'}{member.matchBasis.includes('title-year-candidate') ? ' · title/year clue' : ''}{member.membershipReview ? ' · Possible alternate title' : ''}</small></span>{onIntend && member.status === 'missing' && <button className="subtle-button" disabled={busy} onClick={() => void intend(member)}><Plus size={14}/>Wishlist</button>}</div>)}</div>}</details>
      <button className="subtle-button" disabled={busy} onClick={() => open(group)}>Review &amp; save collection</button>
    </article>)}
    {data?.indexStatus === 'building' && <p className="muted" role="status">Waiting for library work or organizing metadata… You can keep browsing your library.</p>}
    {data && data.indexStatus !== 'building' && !data.recommendations.length && <p className="muted">No new collection recommendations for this library yet. You can create a collection or browse genres at any time.</p>}
    {data && data.recommendations.length > shown && <button className="text-button" onClick={() => setShown(shown + 6)}>Show more suggestions</button>}
    {data && <details className="collection-pack-coverage"><summary>Metadata coverage</summary><p className="muted small">Genre tags organize shelves. They do not prove series membership. Missing tags stay unknown; your own genres take priority.</p>{data.packCoverage.map(pack => <p className="small" key={pack.id}>{kindNames[pack.kind] || pack.kind} · {pack.genreRecords.toLocaleString()} of {pack.works.toLocaleString()} records with genres{pack.genreRecords ? '' : ' · no genre tags in this pack'}</p>)}{!data.packCoverage.length && data.indexStatus !== 'building' && <p className="muted small">No metadata packs installed. Local genres and supplied source collection labels still work.</p>}{data.packErrors.map((value, index) => <p className="muted small" key={index}>{value}</p>)}</details>}
    {error && <p role="alert" className="error-text">{error}</p>}
    {message && <p role="status" className="muted small">{message}</p>}
    {review && <Dialog open onOpenChange={value => !value && close()}><DialogContent className="form-dialog collection-recommendation-dialog"><DialogHeader><DialogTitle>Review suggested collection</DialogTitle><DialogDescription>Select the titles you want to collect. Saving creates an editable collection and a linked missing-title plan; buying intentions are added only when you choose them.</DialogDescription></DialogHeader><label className="field"><span>Collection name</span><input maxLength={120} value={name} onChange={event => setName(event.target.value)}/></label><p className="muted small">{selected.length} selected references · formats and editions are separate. Same-year or alternate titles need your review.</p><div className="collection-member-picker">{review.members.map(member => <label key={member.key}><input type="checkbox" checked={selected.includes(member.key)} onChange={() => setSelected(current => current.includes(member.key) ? current.filter(value => value !== member.key) : [...current, member.key])}/><span>{member.title}<small>{member.year || 'Year unknown'}{member.creators?.length ? ` · ${member.creators.slice(0,2).join(', ')}` : ''} · {member.status === 'library' ? 'In your library' : member.status === 'wanted' ? 'Intended' : 'Reference candidate'}{member.membershipReview ? ` · ${member.membershipReview}` : ''}</small></span></label>)}</div>{error && <p role="alert" className="error-text">{error}</p>}<button className="primary-button" disabled={busy || !selected.length || !name.trim()} onClick={() => void save()}><Check size={17}/>{busy ? 'Saving…' : 'Save collection & plan'}</button></DialogContent></Dialog>}
  </section>;
}
