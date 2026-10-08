'use client';

import { useEffect, useState } from 'react';
import { ArrowUpRight, PackageCheck, Pencil, Plus, Search, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { blankBoxClient, type CollectingTarget, type MetadataCandidate } from '@/lib/blank-box-client';
import { AddPhysicalDialog } from '@/components/add-physical-dialog';
import { emptyPhysicalDraft, type PhysicalDraft, type PhysicalFormat } from '@/lib/physical-media';
import { MetadataCandidateReview } from '@/components/metadata-candidate-review';
import { formatsByKind } from '@/lib/collecting-formats';
import { newRecordId } from '@/lib/streaming-services';
import { kindNames, type Kind, type MediaItem } from '@/lib/media';
import { emptyPreorder, preorderStatusNames, type Preorder, type PreorderDetail, type PreorderDraft, type PreorderPage } from '@/lib/preorders';

const kinds = Object.keys(formatsByKind) as Kind[];
const today = () => { const date = new Date(); return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`; };
const seasonName = (season: string | null) => season === 'complete-series' ? 'Complete series' : season === 'specials' ? 'Specials' : season ? `Season ${season}` : '';

export function PreorderTracker({ intention, onIntentionUsed, onChange, onOpenItem }: {
  intention: CollectingTarget | null; onIntentionUsed: () => void; onChange: () => Promise<void>; onOpenItem: (id: string) => void;
}) {
  const [page, setPage] = useState<PreorderPage | null>(null);
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('active');
  const [offset, setOffset] = useState(0);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editor, setEditor] = useState<Preorder | 'new' | null>(null);
  const [receiving, setReceiving] = useState<Preorder[]>([]);
  const [queueSize, setQueueSize] = useState(0);
  const [selecting, setSelecting] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [removing, setRemoving] = useState(false);
  const [detail, setDetail] = useState<PreorderDetail | null>(null);
  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      setLoading(true); setError('');
      void blankBoxClient.preorders({ query, status, offset }).then(result => { if (active) { setPage(result); setSelected(new Set()); } })
        .catch(cause => { if (active) setError((cause as Error).message); }).finally(() => { if (active) setLoading(false); });
    }, 180);
    return () => { active = false; window.clearTimeout(timer); };
  }, [query, status, offset, revision]);
  const changed = async () => {
    setOffset(0); setRevision(value => value + 1);
    try { await onChange(); } catch (cause) { toast.error((cause as Error).message); }
  };
  const openDetail = async (order: Preorder) => {
    try { setDetail(await blankBoxClient.preorder(order.id)); } catch (cause) { toast.error((cause as Error).message); }
  };
  const receiveOrders = (orders: Preorder[]) => { setReceiving(orders); setQueueSize(orders.length); };
  const nextOrder = () => setReceiving(current => current.slice(1));
  const stopReceiving = () => { if (receiving.length < 2 || window.confirm('Stop reviewing the remaining orders? Deliveries already confirmed are saved.')) setReceiving([]); };
  const remove = async (order: Preorder) => {
    const history = order.receivedQuantity ? ' Its delivery history will also be removed. Received copies and their purchase details stay in your library.' : ' This removes the saved order.';
    if (!window.confirm(`Remove preorder “${order.title}”?${history}`)) return;
    setRemoving(true);
    try { await blankBoxClient.action('preorder-remove', { id: order.id, confirmId: order.id, revision: order.revision, confirmHistory: true }); toast.success('Preorder removed'); await changed(); }
    catch (cause) { toast.error((cause as Error).message); } finally { setRemoving(false); }
  };
  const selectable = page?.preorders.filter(order => !['received', 'cancelled'].includes(order.status)) || [];
  const closeEditor = () => { setEditor(null); onIntentionUsed(); };
  return <div className="preorder-page">
    <div className="page-heading"><div><h1>Preorders</h1><p>Track purchases awaiting release or delivery. Add them to your library when they arrive.</p></div><button className="primary-button" onClick={() => setEditor('new')}><Plus size={17}/>Add preorder</button></div>
    <div className="preorder-filters">
      <label className="field"><span>Search preorders</span><input type="search" value={query} maxLength={250} onChange={event => { setQuery(event.target.value); setOffset(0); }} placeholder="Title, label, vendor, or order number"/></label>
      <label className="field"><span>Show orders</span><select value={status} onChange={event => { setStatus(event.target.value); setOffset(0); }}>
        <option value="active">Awaiting delivery{page ? ` (${page.counts.active})` : ''}</option><option value="all">All orders</option>
        {Object.entries(preorderStatusNames).map(([value, name]) => <option key={value} value={value}>{name}</option>)}
      </select></label>
    </div>
    {error && <p className="error-text" role="alert">{error} <button className="text-button" onClick={() => setRevision(value => value + 1)}>Try again</button></p>}
    {loading ? <p className="muted" role="status">Loading preorders…</p> : !error && <>
      {!!selectable.length && <div className="preorder-actions preorder-selection">{!selecting ? <button className="subtle-button" onClick={() => setSelecting(true)}>Select</button> : <><button className="subtle-button" onClick={() => setSelected(new Set(selectable.map(order => order.id)))}>Select All</button><button className="primary-button" disabled={!selected.size} onClick={() => receiveOrders(selectable.filter(order => selected.has(order.id)))}>Mark Delivered ({selected.size})</button><button className="text-button" onClick={() => { setSelected(new Set()); setSelecting(false); }}>Clear selection</button><span className="muted small">Select orders on this page, then review each delivery in turn.</span></>}</div>}
      {!page?.preorders.length && <section className="panel"><h2>{query ? 'No matching preorders' : status === 'active' ? 'Nothing awaiting delivery' : 'No orders here yet'}</h2><p className="muted">Add a purchased title above, or move one from Wishlist. Received and cancelled orders stay in your order history.</p></section>}
      {page?.preorders.map(order => <article className="panel preorder-card" key={order.id}>
        <div className="section-heading">{selecting && !['received', 'cancelled'].includes(order.status) && <input type="checkbox" aria-label={`Select ${order.title}`} checked={selected.has(order.id)} onChange={event => setSelected(current => { const next = new Set(current); if (event.target.checked) next.add(order.id); else next.delete(order.id); return next; })}/>}<h2>{order.title}{order.year ? ` (${order.year})` : ''}</h2><span className={`preorder-status status-${order.status}`}>{preorderStatusNames[order.status]}</span></div>
        <p className="muted">{[kindNames[order.kind], order.releaseType === 'digital' ? 'Digital' : order.format, order.releaseType === 'digital' ? order.digitalPlatform : '', order.edition, seasonName(order.season), order.label].filter(Boolean).join(' · ')}</p>
        <dl className="preorder-facts">
          <div><dt>Vendor</dt><dd>{order.vendor || 'Not recorded'}</dd></div><div><dt>Copies</dt><dd>{order.quantity} ordered · {order.receivedQuantity} received</dd></div>
          {order.price && <div><dt>Unit price</dt><dd>{order.currency} {order.price}</dd></div>}
          {order.dateOrdered && <div><dt>Date ordered</dt><dd>{order.dateOrdered}</dd></div>}
          {order.releaseDate && <div><dt>Expected release</dt><dd>{order.releaseDate}</dd></div>}
          {order.expectedDeliveryDate && <div><dt>Expected delivery</dt><dd>{order.expectedDeliveryDate}</dd></div>}
          {order.trackingNumber && <div><dt>Tracking number</dt><dd>{order.trackingNumber}</dd></div>}
          {order.orderNumber && <div><dt>Order number</dt><dd>{order.orderNumber}</dd></div>}
        </dl>
        {order.notes && <p className="preorder-notes">{order.notes}</p>}
        <div className="preorder-actions">
          {!['received', 'cancelled'].includes(order.status) && <button className="primary-button" onClick={() => receiveOrders([order])}><PackageCheck size={17}/>Mark Delivered</button>}
          <button className="subtle-button" onClick={() => setEditor(order)}><Pencil size={15}/>Edit order</button>
          <button className="text-button" onClick={() => void openDetail(order)}>Order history</button><button className="text-button" disabled={removing} onClick={() => void remove(order)}><Trash2 size={15}/>Remove order</button>
        </div>
      </article>)}
      {!!page?.total && <div className="collection-paging"><button disabled={!offset} onClick={() => setOffset(Math.max(0, offset - 25))}>Previous</button><span>{offset + 1}–{Math.min(offset + 25, page.total)} of {page.total}</span><button disabled={offset + 25 >= page.total} onClick={() => setOffset(offset + 25)}>Next</button></div>}
    </>}
    {(editor || intention) && <PreorderEditor key={typeof editor === 'object' && editor ? editor.id : intention?.id || 'new'} order={typeof editor === 'object' ? editor : null} intention={intention} onClose={closeEditor} onSaved={() => { closeEditor(); void changed(); }}/ >}
    {!!receiving.length && <PurchaseReceiver key={receiving[0].id} order={receiving[0]} queueProgress={queueSize > 1 ? `Order ${queueSize - receiving.length + 1} of ${queueSize}` : undefined} onSkip={receiving.length > 1 ? nextOrder : undefined} onClose={stopReceiving} onSaved={() => { nextOrder(); void changed(); }}/ >}
    {detail && <Dialog open onOpenChange={open => { if (!open) setDetail(null); }}><DialogContent className="form-dialog preorder-dialog"><DialogHeader><DialogTitle>Order history: {detail.preorder.title}</DialogTitle><DialogDescription>{detail.preorder.receivedQuantity} of {detail.preorder.quantity} copies received · {preorderStatusNames[detail.preorder.status]}</DialogDescription></DialogHeader>
      <p className="muted small">Ordered {detail.preorder.dateOrdered || 'date not recorded'}{detail.preorder.vendor ? ` from ${detail.preorder.vendor}` : ''}. Saved {new Date(detail.preorder.createdAt).toLocaleDateString()}.</p>
      {!detail.receipts.length && <p className="muted">No deliveries recorded.</p>}
      {detail.receipts.map(receipt => <section className="preorder-receipt" key={receipt.id}><h3>{receipt.quantity} {receipt.quantity === 1 ? 'copy' : 'copies'} received · {receipt.receivedAt}</h3><p className="muted small">{[receipt.releaseType === 'digital' ? 'Digital purchase' : receipt.receivedDetails?.format || receipt.orderDetails.format, receipt.releaseType === 'digital' ? receipt.receivedDetails?.platform : '', receipt.orderDetails.edition, receipt.orderDetails.label, receipt.orderDetails.vendor, receipt.orderDetails.price ? `${receipt.orderDetails.currency} ${receipt.orderDetails.price} per copy` : ''].filter(Boolean).join(' · ')}</p>{receipt.orderDetails.trackingNumber && <p className="muted small">Tracking: {receipt.orderDetails.trackingNumber}</p>}{receipt.orderDetails.notes && <p className="preorder-notes">{receipt.orderDetails.notes}</p>}{receipt.currentItemId ? <button className="text-button" onClick={() => { setDetail(null); onOpenItem(receipt.currentItemId!); }}>Open library title <ArrowUpRight size={15}/></button> : <p className="muted small">The library title has since been removed. This delivery record is retained.</p>}</section>)}
    </DialogContent></Dialog>}
  </div>;
}

function PreorderEditor({ order, intention, onClose, onSaved }: { order: Preorder | null; intention: CollectingTarget | null; onClose: () => void; onSaved: () => void }) {
  const [draft, setDraft] = useState<PreorderDraft>(() => order || { ...emptyPreorder(), ...(intention ? { title: intention.title, kind: intention.kind, year: intention.year, format: intention.format, edition: intention.edition || '', season: intention.season || null } : {}) });
  const [requestId] = useState(newRecordId);
  const [moveIntention, setMoveIntention] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [dirty, setDirty] = useState(false);
  const fixed = !!order?.receivedQuantity;
  const update = <K extends keyof PreorderDraft>(field: K, value: PreorderDraft[K]) => { setDirty(true); setDraft(current => ({ ...current, [field]: value })); };
  const close = () => { if (!busy && (!dirty || window.confirm('Discard unsaved preorder changes?'))) onClose(); };
  const save = async () => {
    setBusy(true); setError('');
    try {
      await blankBoxClient.action('preorder-save', { ...draft, ...(order ? { id: order.id, revision: order.revision } : { requestId }), ...(intention ? { intentionId: intention.id, moveIntention } : {}) });
      toast.success(order ? 'Preorder updated' : 'Preorder saved'); onSaved();
    } catch (cause) { setError((cause as Error).message); } finally { setBusy(false); }
  };
  const text = (field: keyof Pick<PreorderDraft, 'title' | 'edition' | 'label' | 'vendor' | 'platform' | 'region' | 'barcode' | 'trackingNumber' | 'orderNumber' | 'digitalPlatform' | 'digitalFormat' | 'digitalUrl'>, label: string, maximum: number, disabled = false) => <label className="field"><span>{label}</span><input value={draft[field]} maxLength={maximum} required={field === 'title'} disabled={disabled} onChange={event => update(field, event.target.value)}/></label>;
  return <Dialog open onOpenChange={open => { if (!open) close(); }}><DialogContent className="form-dialog preorder-dialog"><DialogHeader><DialogTitle>{order ? 'Edit preorder' : 'Add preorder'}</DialogTitle><DialogDescription>Record a purchase you are waiting to receive. Price is per copy.</DialogDescription></DialogHeader>
    <form onSubmit={event => { event.preventDefault(); void save(); }}>
      <fieldset disabled={busy} className="preorder-fieldset"><legend>Title and edition</legend>
        {fixed && <p className="muted small">Title, edition, and ordered quantity are fixed after the first delivery. Purchase details and notes can still be updated.</p>}
        <label className="field"><span>Release type</span><select value={draft.releaseType || 'physical'} disabled={fixed} onChange={event => update('releaseType', event.target.value as 'physical' | 'digital')}><option value="physical">Physical</option><option value="digital">Digital</option></select></label>
        <div className="preorder-form-grid">{text('title', 'Title', 250, fixed)}
          <label className="field"><span>Media type</span><select value={draft.kind} disabled={fixed} onChange={event => { const kind = event.target.value as Kind; setDirty(true); setDraft(current => ({ ...current, kind, format: formatsByKind[kind][1], season: null, platform: '' })); }}>{kinds.map(kind => <option key={kind} value={kind}>{kindNames[kind]}</option>)}</select></label>
          {draft.releaseType === 'digital' ? <>{text('digitalPlatform', 'Digital platform / store', 120, fixed)}{text('digitalFormat', 'Digital format / quality', 120, fixed)}{text('digitalUrl', 'Platform link (optional)', 2000)}</> : <label className="field"><span>Format</span><select value={draft.format} disabled={fixed} onChange={event => update('format', event.target.value)}>{formatsByKind[draft.kind].map(format => <option key={format}>{format}</option>)}</select></label>}
          {text('edition', 'Edition', 120, fixed)}
          <label className="field"><span>Title release year</span><input type="number" min={1800} max={2200} disabled={fixed} value={draft.year ?? ''} onChange={event => update('year', event.target.value ? Number(event.target.value) : null)}/></label>
          {draft.kind === 'tv' && <label className="field"><span>Season</span><select value={draft.season || ''} disabled={fixed} onChange={event => update('season', event.target.value || null)}><option value="">Unknown / not specified</option><option value="complete-series">Complete series</option><option value="specials">Specials</option>{Array.from({ length: 99 }, (_, index) => <option key={index} value={String(index + 1)}>Season {index + 1}</option>)}</select></label>}
          {text('label', 'Release label / publisher', 120)}{draft.releaseType !== 'digital' && <>{draft.kind === 'game' && text('platform', 'Console / platform', 120, fixed)}{text('region', 'Region', 80, fixed)}{text('barcode', 'Barcode / ISBN', 80, fixed)}</>}
        </div>
      </fieldset>
      <fieldset disabled={busy} className="preorder-fieldset"><legend>Purchase and delivery</legend><div className="preorder-form-grid">
        {text('vendor', 'Retailer / vendor', 250)}{text('orderNumber', 'Order number', 120)}
        <label className="field"><span>Quantity ordered</span><input type="number" min={1} max={999} required disabled={fixed} value={draft.quantity} onChange={event => update('quantity', Number(event.target.value))}/></label>
        <label className="field"><span>Unit price</span><input type="number" min={0} max={999999999.99} step="0.01" value={draft.price} onChange={event => update('price', event.target.value)}/></label>
        <label className="field"><span>Currency</span><input maxLength={3} minLength={3} pattern="[A-Za-z]{3}" required value={draft.currency} onChange={event => update('currency', event.target.value.toUpperCase())}/></label>
        {(['dateOrdered', 'releaseDate', 'expectedDeliveryDate'] as const).map((field, index) => <label className="field" key={field}><span>{['Date ordered', 'Expected release date', 'Expected delivery date'][index]}</span><input type="date" min="1800-01-01" max="2200-12-31" value={draft[field]} onChange={event => update(field, event.target.value)}/></label>)}
        {text('trackingNumber', 'Tracking number', 250)}
        {order?.status !== 'received' && <label className="field"><span>Delivery status</span><select value={draft.deliveryStatus} onChange={event => update('deliveryStatus', event.target.value as PreorderDraft['deliveryStatus'])}><option value="ordered">Ordered</option><option value="shipped">Shipped</option><option value="cancelled">Cancelled</option></select></label>}
      </div><label className="field"><span>Order notes</span><textarea rows={3} maxLength={4000} value={draft.notes} onChange={event => update('notes', event.target.value)}/></label></fieldset>
      {intention && <label className="preorder-check"><input type="checkbox" checked={moveIntention} disabled={busy} onChange={event => setMoveIntention(event.target.checked)}/><span>Remove this saved intention after the preorder is saved. Its title and edition must still match.</span></label>}
      {draft.deliveryStatus === 'cancelled' && <p className="muted small">Cancellation keeps the order and any received copies. Only the outstanding quantity is cancelled.</p>}
      {error && <p role="alert" className="error-text">{error}</p>}
      <div className="preorder-actions"><button className="primary-button" disabled={busy}>{busy ? 'Saving…' : 'Save preorder'}</button><button className="text-button" type="button" disabled={busy} onClick={close}>Cancel</button></div>
    </form>
  </DialogContent></Dialog>;
}

export function WishlistPurchase({ target, onClose, onSaved }: { target: CollectingTarget; onClose: () => void; onSaved: () => void }) {
  const order: Preorder = { ...emptyPreorder(), title: target.title, kind: target.kind, year: target.year, format: target.format, edition: target.edition || '', season: target.season || null, barcode: target.identifier?.value || '', id: target.id, revision: 0, quantity: 100, receivedQuantity: 0, status: 'ordered', createdAt: target.createdAt, updatedAt: target.createdAt };
  return <PurchaseReceiver order={order} wishlist={target} onClose={onClose} onSaved={onSaved}/>;
}

function PurchaseReceiver({ order, wishlist, queueProgress, onSkip, onClose, onSaved }: { order: Preorder; wishlist?: CollectingTarget; queueProgress?: string; onSkip?: () => void; onClose: () => void; onSaved: () => void }) {
  const remaining = order.quantity - order.receivedQuantity;
  const [quantity, setQuantity] = useState(wishlist ? 1 : Math.min(remaining, order.releaseType === 'digital' ? 30 : 100));
  const [receivedDate, setReceivedDate] = useState(today);
  const [releaseType, setReleaseType] = useState<'physical' | 'digital'>(order.releaseType || 'physical');
  const [digitalPlatform, setDigitalPlatform] = useState(order.digitalPlatform || '');
  const [digitalFormat, setDigitalFormat] = useState(order.digitalFormat || '');
  const [digitalUrl, setDigitalUrl] = useState(order.digitalUrl || '');
  const [mode, setMode] = useState<'delivery' | 'new' | 'match'>('delivery');
  const [query, setQuery] = useState(order.title);
  const [results, setResults] = useState<MediaItem[]>([]);
  const [target, setTarget] = useState<MediaItem | 'new' | null>(null);
  const [edition, setEdition] = useState('new');
  const [format, setFormat] = useState(order.format === 'Any' ? formatsByKind[order.kind][1] : order.format);
  const [platform, setPlatform] = useState(order.platform);
  const [location, setLocation] = useState('');
  const [condition, setCondition] = useState('');
  const [draft, setDraft] = useState<PhysicalDraft>({ ...emptyPhysicalDraft, title: order.title, kind: order.kind, year: order.year ? String(order.year) : '', format: (order.format === 'Any' ? formatsByKind[order.kind][1] : order.format) as PhysicalFormat, edition: order.edition, releaseLabel: order.label, season: order.season || '', barcode: order.barcode, region: order.region, platform: order.platform });
  const [searching, setSearching] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [searchError, setSearchError] = useState('');
  const [requestId] = useState(newRecordId);
  const [metadata, setMetadata] = useState<MetadataCandidate | null>(() => { const workId = wishlist?.workId || order.intentionReference?.workId; return workId ? { id: workId, title: order.title, kind: order.kind, year: order.year, level: 'work', work_id: null, origin: 'saved', evidence: ['previously confirmed wishlist work'], confidence: 'review', requiresReview: true } : null; });
  const [applyDetails, setApplyDetails] = useState(false);
  useEffect(() => {
    if (mode !== 'match') return;
    let active = true;
    const timer = window.setTimeout(() => {
      setSearching(true); setSearchError('');
      void Promise.all([blankBoxClient.libraryPage({ q: query, kind: order.kind, limit: 20 }), ...(query.trim() || metadata ? [blankBoxClient.action('physical-reference-matches', { title: metadata?.title || query.trim(), kind: order.kind, year: metadata?.year || order.year, ...(metadata ? { referenceId: metadata.id } : {}) })] : [])]).then(([page, linked]) => { if (active) setResults([...new Map([...(linked?.results || []), ...page.items].map(item => [item.id, item])).values()]); })
        .catch(cause => { if (active) { setResults([]); setSearchError((cause as Error).message); } }).finally(() => { if (active) setSearching(false); });
    }, 180);
    return () => { active = false; window.clearTimeout(timer); };
  }, [query, order.kind, order.year, metadata, mode]);
  const selectItem = async (item: MediaItem) => {
    setBusy(true);
    try { setTarget(await blankBoxClient.item(item.id)); setEdition('new'); setApplyDetails(false); setError(''); } catch (cause) { setError((cause as Error).message); } finally { setBusy(false); }
  };
  const receive = async () => {
    if (!target || busy) return;
    setBusy(true); setError('');
    try {
      const newDetails = Object.fromEntries(Object.entries(draft).filter(([key]) => key !== 'kind'));
      await blankBoxClient.action(wishlist ? 'wishlist-receive' : 'preorder-receive', { id: order.id, confirmId: order.id, revision: order.revision, requestId,
        ...(wishlist ? { expectedTarget: { title: wishlist.title, kind: wishlist.kind, year: wishlist.year, format: wishlist.format, edition: wishlist.edition || '', season: wishlist.season || null, workId: wishlist.workId || null, releaseId: wishlist.releaseId || null } } : {}),
        ...(metadata ? { metadataEntityId: metadata.id, applyMetadataDetails: target === 'new' || applyDetails } : {}), barcode: order.barcode,
        quantity, receivedDate, releaseType, digitalPlatform, digitalFormat, digitalUrl, format, platform, location, condition,
        ...(target === 'new' ? { createSeparate: true, newItemDetails: releaseType === 'physical' ? { ...newDetails, year: draft.year ? Number(draft.year) : null } : { title: draft.title, year: draft.year ? Number(draft.year) : null, description: draft.description, genre: draft.genre } } : { itemId: target.id, ...(edition === 'new' ? { newEdition: true } : { versionId: edition }) }) });
      toast.success(`${quantity} ${releaseType === 'digital' ? quantity === 1 ? 'purchase recorded' : 'purchases recorded' : quantity === 1 ? 'copy added' : 'copies added'} in your library`); onSaved();
    } catch (cause) { setError((cause as Error).message); } finally { setBusy(false); }
  };
  const physicalVersions = target && target !== 'new' ? target.versions?.filter(version => target.sources.some(source => source.type === 'physical' && source.versionId === version.id && source.packageType !== 'box-set')) || [] : [];
  const chooseNew = () => { setDraft(current => ({ ...current, format: format as PhysicalFormat, platform, location, condition })); setTarget('new'); setMode('new'); setError(''); };
  const back = () => { setMode('delivery'); setTarget(null); setError(''); };
  const metadataReview = <MetadataCandidateReview title={mode === 'new' ? draft.title : query} kind={order.kind} year={order.year} identifier={releaseType === 'physical' && order.barcode ? { namespace: order.kind === 'book' ? 'isbn' : 'upc-ean', value: order.barcode } : undefined} selectedId={metadata?.id || ''} onSelect={(_, candidate) => { setMetadata(candidate || null); if (mode === 'match') { setTarget(null); if(candidate?.id !== metadata?.id) setSearching(true); } setApplyDetails(false); }} targetLevel={releaseType === 'digital' ? 'work' : 'any'} releaseRequiresIdentifier allowManualCreate={false} disabled={busy}/>;
  const confirmation = <><p className="muted small">{quantity} {releaseType === 'digital' ? 'digital purchase records' : quantity === 1 ? 'physical copy' : 'physical copies'} · {receivedDate}. {wishlist ? 'The wishlist entry is removed after saving.' : 'Order history is retained.'}</p>{error && <p role="alert" className="error-text">{error}</p>}<div className="preorder-actions"><button className="primary-button" form={releaseType === 'physical' && mode === 'new' ? 'physical-item-details' : undefined} type="submit" disabled={busy || !target || (mode === 'match' && searching)}>{busy ? 'Saving…' : wishlist ? 'Add to library' : 'Confirm delivery'}</button><button className="text-button" type="button" disabled={busy} onClick={back}>Back to delivery</button></div></>;
  if (mode === 'new' && releaseType === 'physical') return <AddPhysicalDialog open busy={busy} title={`Add as New Copy: ${order.title}`} fixedKind hidePreferences draft={draft} formats={formatsByKind[order.kind].filter(value => value !== 'Any') as PhysicalFormat[]} locations={[]} gamePlatforms={platform ? [platform] : []} defaults={{}} onChange={value => { setDraft(value); setFormat(value.format); setLocation(value.location); setCondition(value.condition); setPlatform(value.platform); }} onContinue={() => void receive()} onOpenChange={open => { if (!open && !busy) back(); }} onSaveLocation={async () => false} onSaveFormats={async () => false} onSavePlatforms={async () => false} onSaveDefault={async () => false}><p className="muted">This creates a new library title with the preorder details filled in. To add a copy under a title you already have, go back and choose Match to Existing.</p>{metadataReview}{confirmation}</AddPhysicalDialog>;
  return <Dialog open onOpenChange={open => { if (!open && !busy) onClose(); }}><DialogContent className="form-dialog preorder-dialog"><DialogHeader><DialogTitle>{wishlist ? 'Bought / add to library: ' : 'Mark Delivered: '}{order.title}</DialogTitle><DialogDescription>{queueProgress && `${queueProgress}. `}{wishlist ? 'Record your purchase and add it to the library.' : `${remaining} ${remaining === 1 ? 'copy' : 'copies'} awaiting delivery.`} Choose how to add this delivery.</DialogDescription></DialogHeader>
    <form onSubmit={event => { event.preventDefault(); void receive(); }}>
      <fieldset disabled={busy} className="preorder-fieldset"><legend>Delivery</legend><div className="preorder-form-grid">
        <label className="field"><span>Release type</span><select disabled={!!order.receivedQuantity} value={releaseType} onChange={event => { setReleaseType(event.target.value as 'physical' | 'digital'); if(event.target.value === 'digital') setQuantity(current=>Math.min(current,30)); back(); setMetadata(current => current?.level === 'release' ? null : current); }}><option value="physical">Physical</option><option value="digital">Digital</option></select></label>
        <label className="field"><span>{wishlist ? 'Quantity to add' : 'Quantity delivered now'}</span><input required type="number" min={1} max={Math.min(remaining, releaseType === 'digital' ? 30 : 100)} value={quantity} onChange={event => setQuantity(Number(event.target.value))}/></label>
        <label className="field"><span>Date received</span><input required type="date" min="1800-01-01" max="2200-12-31" value={receivedDate} onChange={event => setReceivedDate(event.target.value)}/></label>
        {releaseType === 'physical' ? <><label className="field"><span>Received format</span><select value={format} onChange={event => setFormat(event.target.value)}>{formatsByKind[order.kind].filter(value => value !== 'Any').map(value => <option key={value}>{value}</option>)}</select></label>
        {order.kind === 'game' && <label className="field"><span>Console / platform</span><input required maxLength={120} value={platform} onChange={event => setPlatform(event.target.value)}/></label>}
        <label className="field"><span>Storage location</span><input maxLength={250} value={location} onChange={event => setLocation(event.target.value)} placeholder="Optional"/></label>
        <label className="field"><span>Condition</span><input maxLength={120} value={condition} onChange={event => setCondition(event.target.value)} placeholder="Optional"/></label></> : <><label className="field"><span>Digital platform / store</span><input required maxLength={120} value={digitalPlatform} onChange={event => setDigitalPlatform(event.target.value)} placeholder="Platform where you purchased it"/></label><label className="field"><span>Digital format / quality</span><input maxLength={120} value={digitalFormat} onChange={event => setDigitalFormat(event.target.value)} placeholder="4K, HD, EPUB, FLAC…"/></label><label className="field"><span>Platform link (optional)</span><input type="url" maxLength={2000} value={digitalUrl} onChange={event => setDigitalUrl(event.target.value)}/></label></>}
      </div>{releaseType === 'digital' && <p className="muted small">Records a purchase on the named platform. Files and playback access are not verified. Up to 30 digital records per library title.</p>}{!wishlist && remaining > 100 && <p className="muted small">Receive up to 100 physical copies at a time. The remainder stays outstanding.</p>}</fieldset>
      <div className="preorder-actions preorder-destination-actions"><button type="button" className={mode === 'new' ? 'primary-button' : 'subtle-button'} disabled={busy} onClick={chooseNew}>Add as New Copy</button><button type="button" className={mode === 'match' ? 'primary-button' : 'subtle-button'} disabled={busy} onClick={() => { if(mode !== 'match') setSearching(true); setMode('match'); setTarget(null); setError(''); }}>Match to Existing</button></div>
      {mode === 'match' && <fieldset disabled={busy} className="preorder-fieldset"><legend>Find a match</legend>
        <p className="muted small">Choose a title in My Library. Saved metadata and the installed Blank Box Database can help identify it.</p>
        {metadataReview}
        {metadata && <p className="muted small">Reviewed metadata: {metadata.title}{metadata.year ? ` (${metadata.year})` : ''}. Its reference identity will be saved with your selection.</p>}
        <label className="field"><span><Search size={14}/>Search My Library</span><input value={query} maxLength={200} onChange={event => { if(event.target.value !== query) setSearching(true); setQuery(event.target.value); }}/></label>
        {searching ? <p className="muted small" role="status">Searching library…</p> : <div className="preorder-destinations">{results.map(item => <label className="preorder-check" key={item.id}><input type="radio" name="preorder-target" checked={target !== 'new' && target?.id === item.id} onChange={() => void selectItem(item)}/><span>{item.title}{item.year ? ` (${item.year})` : ''}<small>{kindNames[item.kind]} · {item.sources.filter(source => source.type === 'physical').length} physical copies</small></span></label>)}{!results.length && !searchError && <p className="muted small">No matching title found. Try another search, or choose Add as New Copy above.</p>}</div>}
        {searchError && <p role="alert" className="error-text">{searchError}</p>}
        {target && target !== 'new' && <><p className="muted small">Destination: {target.title}{target.year ? ` (${target.year})` : ''}</p>{releaseType === 'physical' && <><label className="field"><span>Physical edition</span><select value={edition} onChange={event => setEdition(event.target.value)}><option value="new">Create a new physical edition</option>{physicalVersions.map(version => <option key={version.id} value={version.id}>{version.label}</option>)}</select></label><p className="muted small">An existing edition must match the received format, edition, season, and release details.</p></>}</>}
      </fieldset>}
      {mode === 'new' && <fieldset disabled={busy} className="preorder-fieldset"><legend>Add digital media</legend><div className="preorder-form-grid"><label className="field"><span>Title</span><input required maxLength={250} value={draft.title} onChange={event => setDraft(current => ({ ...current, title: event.target.value }))}/></label><label className="field"><span>Year</span><input type="number" min={1800} max={2200} value={draft.year} onChange={event => setDraft(current => ({ ...current, year: event.target.value }))}/></label></div><label className="field"><span>Description</span><textarea maxLength={5000} value={draft.description} onChange={event => setDraft(current => ({ ...current, description: event.target.value }))}/></label>{metadataReview}</fieldset>}
      {metadata && target && target !== 'new' && <label className="preorder-check"><input type="checkbox" checked={applyDetails} onChange={event => setApplyDetails(event.target.checked)} disabled={busy}/><span>Apply the reviewed title details to this existing library title. Leave unchecked to keep its saved facts.</span></label>}
      {mode !== 'delivery' && confirmation}
      <div className="preorder-actions"><button className="text-button" type="button" disabled={busy} onClick={onClose}>{queueProgress ? 'Stop reviewing' : 'Cancel'}</button>{onSkip && <button className="text-button" type="button" disabled={busy} onClick={onSkip}>Skip this order</button>}</div>
    </form>
  </DialogContent></Dialog>;
}
