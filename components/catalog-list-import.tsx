'use client';

import { useEffect, useState } from 'react';
import { bytes, kindNames, type Kind } from '@/lib/media';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { MetadataCandidateReview } from '@/components/metadata-candidate-review';

type Mapping = Record<string, string>;
type ImportRow = { rowNumber: number; raw: Record<string,string>; proposed: null | { title: string; kind: Kind; year?: number; format?: string; issue?: string; edition?: string; physical: boolean }; status: string; error: string; candidates: { id: string; title: string; year?: number; matchReason?: string }[] };
type ImportPage = { batch: null | { id: string; sourceName: string; total: number; mode: 'titles'|'physical'|'source' }; rows: ImportRow[]; total: number; counts: Record<string, number> };
type Inspection = { headers: string[]; mapping: Mapping; total: number; sample: { rowNumber: number; values: Record<string, string> }[] };
const fields: [string, string][] = [['title','Title'],['kind','Media type'],['year','Year'],['format','Physical format'],['edition','Edition / variant'],['issue','Issue number'],['platform','Game platform'],['location','Physical location'],['condition','Condition'],['barcode','Barcode / ISBN'],['quantity','Quantity'],['creator','Creator / author'],['publisher','Publisher'],['volume','Volume'],['certificate','COA'],['signed','Signed'],['grade','Grading'],['listedPrice','Listed price (historical)'],['sourceType','Source type']];
const formats = ['DVD','Blu-ray','4K UHD Blu-ray','VHS','CD','Vinyl','Cassette','Book','Comic','Magazine','Game','Other'];

async function api<T>(url: string, body?: Record<string, unknown>): Promise<T> {
  const response = await fetch(url, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : { cache: 'no-store' });
  const value = await response.json() as T & { error?: string };
  if (!response.ok) throw new Error(value.error || 'The import could not be completed.');
  return value;
}

export function CatalogListImport({ open, onOpenChange, onChanged }: { open: boolean; onOpenChange: (open: boolean) => void; onChanged: () => Promise<unknown> }) {
  const [content,setContent] = useState('');
  const [inputType,setInputType] = useState<'lines'|'csv'|'tsv'>('lines');
  const [sourceName,setSourceName] = useState('My collection list');
  const [inspection,setInspection] = useState<Inspection|null>(null);
  const [mapping,setMapping] = useState<Mapping>({ title: 'Title' });
  const [kind,setKind] = useState<Kind|'auto'>('auto');
  const [mode,setMode] = useState<'titles'|'physical'|'source'>('titles');
  const [format,setFormat] = useState('');
  const [rowChoices,setRowChoices] = useState<Record<number,{kind:string;format:string}>>({});
  const [metadataRowNumber,setMetadataRowNumber] = useState(0);
  const [metadataEntityId,setMetadataEntityId] = useState('');
  const [page,setPage] = useState<ImportPage|null>(null);
  const [offset,setOffset] = useState(0);
  const [filter,setFilter] = useState('');
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState('');
  const [phase,setPhase] = useState<1|2|3>(1);
  async function refresh(batchId?: string, nextOffset = 0, nextFilter = '') {
    const params = new URLSearchParams({ limit: '25', offset: String(nextOffset) });
    if (batchId) params.set('batchId',batchId);
    if (nextFilter) params.set('status',nextFilter);
    setPage(await api<ImportPage>(`/api/list-imports?${params}`));
    setOffset(nextOffset); setFilter(nextFilter);
  }
  useEffect(() => { let active=true;void api<ImportPage>('/api/list-imports?limit=25&offset=0').then(result=>{if(active)setPage(result);}).catch(()=>undefined);return()=>{active=false;}; }, []);
  async function inspect() {
    setBusy(true);setError('');
    try { const result=await api<Inspection>('/api/library',{ action:'list-inspect',content,inputType });setInspection(result);setMapping(result.mapping);setPhase(2); }
    catch (cause) { setError(cause instanceof Error?cause.message:'Unable to read this list.'); }
    finally { setBusy(false); }
  }
  async function stage() {
    setBusy(true);setError('');
    try {
      const result=await api<ImportPage>('/api/library',{ action:'list-stage',content,inputType,mapping,defaultKind:kind,defaultFormat:format,mode,sourceName });
      setPage(result);setOffset(0);setFilter('');setMetadataRowNumber(0);setMetadataEntityId('');setPhase(3);
    } catch (cause) { setError(cause instanceof Error?cause.message:'Unable to stage this list.'); }
    finally { setBusy(false); }
  }
  async function commit(choice: 'ready'|'new'|'attach'|'skip', row?: ImportRow, targetId?: string) {
    if (!page?.batch) return;
    const message=choice==='ready' ? 'Add up to 200 ready catalog rows? This does not copy, rename, or change source files.' :
      choice==='skip' ? `Skip row ${row?.rowNumber}?` : `Add ${row?.proposed?.title||'this row'} to your library? No source files will be copied.`;
    if (!window.confirm(message)) return;
    setBusy(true);setError('');
    try {
      await api<ImportPage>('/api/library',{ action:'list-commit',batchId:page.batch.id,choice,rowNumber:row?.rowNumber,targetId,...(row?.rowNumber===metadataRowNumber && metadataEntityId ? { metadataEntityId } : {}),confirm:true });
      await refresh(page.batch.id,offset,filter);await onChanged();
    } catch (cause) { setError(cause instanceof Error?cause.message:'Unable to add these rows.'); }
    finally { setBusy(false); }
  }
  async function classify(row: ImportRow) {
    if (!page?.batch) return;
    const selected=rowChoices[row.rowNumber];
    if (!selected?.kind || (page.batch?.mode==='physical'||page.batch?.mode==='source'&&row.raw[mapping.sourceType]?.toLowerCase()==='physical')&&!selected.format) { setError('Choose a media type and, for a physical copy, its format.'); return; }
    setBusy(true);setError('');
    try {
      await api<ImportPage>('/api/library',{ action:'list-classify',batchId:page.batch.id,rowNumber:row.rowNumber,kind:selected.kind,format:page.batch?.mode!=='titles'?selected.format:'' });
      await refresh(page.batch.id,offset,filter);
    } catch (cause) { setError(cause instanceof Error?cause.message:'Unable to set this media type.'); }
    finally { setBusy(false); }
  }
  async function openFile(file?: File) {
    if (!file) return;
    if (file.size>3*1024*1024) { setError('Choose a list smaller than 3 MB.');return; }
    const text=await file.text();
    const first=text.replace(/^\uFEFF/,'').split(/\r?\n/,1)[0];
    setInputType(first.includes('\t')?'tsv':first.includes(',')&&file.name.toLowerCase().endsWith('.csv')?'csv':'lines');
    setContent(text);setSourceName(file.name);setInspection(null);setError('');setPhase(1);
  }
  const metadataRow = page?.rows.find(row => row.rowNumber === metadataRowNumber && row.proposed);
  return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent className="form-dialog catalog-list-dialog"><DialogHeader><DialogTitle>Add titles from a list</DialogTitle><DialogDescription>Paste titles or choose a text, CSV, or TSV file. Review types and matches before adding them.</DialogDescription></DialogHeader><div className="catalog-list-import"><div className="import-steps"><span className="active"><b>1</b>Add titles</span><i/><span className={phase>=2?'active':''}><b>2</b>Check columns & types</span><i/><span className={phase===3?'active':''}><b>3</b>Review & add</span></div>
    {phase===1&&<>{page?.batch&&<button className="subtle-button" onClick={()=>setPhase(3)}>Resume review of {page.batch.sourceName}</button>}<div className="catalog-list-controls"><label className="field"><span>Choose a list file</span><input type="file" accept=".txt,.csv,.tsv,text/plain,text/csv,text/tab-separated-values" onChange={event=>void openFile(event.target.files?.[0])}/></label><label className="field"><span>File layout</span><select value={inputType} onChange={event=>{setInputType(event.target.value as typeof inputType);setInspection(null);}}><option value="lines">One title per line</option><option value="csv">CSV with headers</option><option value="tsv">TSV with headers</option></select></label></div>
    <label className="field"><span>Or paste a list</span><textarea rows={5} value={content} onChange={event=>{setContent(event.target.value);setInspection(null);}} placeholder={'Blade Runner 2049\nArrival\nOK Computer'}/></label>
    <button className="subtle-button" disabled={busy||!content.trim()} onClick={()=>void inspect()}>Continue to check titles</button></>}
    {phase===2&&inspection&&<div className="catalog-list-preview"><button className="text-button" onClick={()=>setPhase(1)}>Back to titles</button><p className="muted small">{inspection.total.toLocaleString()} nonempty rows found. The first few are shown below. Section headings in comic issue exports are skipped when you map an Issue column.</p><div className="catalog-list-controls"><label className="field"><span>List name</span><input value={sourceName} maxLength={120} onChange={event=>setSourceName(event.target.value)}/></label><label className="field"><span>What does each row represent?</span><select value={mode} onChange={event=>setMode(event.target.value as typeof mode)}><option value="titles">A title in my catalog</option><option value="physical">A physical copy I own</option>{mapping.sourceType&&<option value="source">Use each row’s Source Type</option>}</select></label><label className="field"><span>Media type if the list does not say</span><select value={kind} onChange={event=>{const selected=event.target.value as Kind|'auto';setKind(selected);if(selected==='comic')setFormat('Comic');else if(selected==='book')setFormat('Book');else if(selected==='game')setFormat('Game');}}><option value="auto">Detect clear clues; ask for unclear rows</option>{Object.entries(kindNames).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>{mode==='physical'&&<label className="field"><span>Format if the list does not say</span><select value={format} onChange={event=>setFormat(event.target.value)}><option value="">Review each missing format</option>{formats.map(value=><option key={value}>{value}</option>)}</select></label>}</div>
      {inputType!=='lines'&&<div className="catalog-mapping">{fields.map(([field,label])=><label className="field" key={field}><span>{label}</span><select value={mapping[field]||''} onChange={event=>setMapping(previous=>{const next={...previous};if(event.target.value)next[field]=event.target.value;else delete next[field];return next;})}><option value="">Not mapped</option>{inspection.headers.map(header=><option key={header} value={header}>{header}</option>)}</select></label>)}</div>}
      <div className="catalog-sample">{inspection.sample.map(row=><div key={row.rowNumber}><strong>Row {row.rowNumber}</strong> {Object.entries(row.values).filter(([,value])=>value).slice(0,5).map(([name,value])=>`${name}: ${value}`).join(' · ')}</div>)}</div><button className="primary-button" disabled={busy||!mapping.title} onClick={()=>void stage()}>Continue to review matches</button></div>}
    {phase===3&&page?.batch&&<div className="catalog-list-staged"><button className="text-button" onClick={()=>setPhase(1)}>Start another list</button><div className="section-heading"><h3>{page.batch.sourceName}</h3><span className="muted small">{page.batch.total} rows · {page.counts.ready||0} ready · {page.counts.review||0} need review · {page.counts.error||0} need a type or correction · {page.counts.committed||0} added</span></div><p className="muted small">Exact and partial title suggestions are held for review. A list entry does not make a playable file or prove a disc is present.</p><div className="catalog-list-actions"><button className="primary-button" disabled={busy||!page.counts.ready} onClick={()=>void commit('ready')}>Add up to 200 ready rows</button><select aria-label="Filter list rows" value={filter} onChange={event=>void refresh(page.batch?.id,0,event.target.value)}><option value="">All rows</option>{['ready','review','error','committed','skipped'].map(value=><option key={value} value={value}>{value}</option>)}</select></div><div className="catalog-list-rows">{page.rows.map(row=><div className="catalog-list-row" key={row.rowNumber}><div><strong>{row.proposed?.title||row.raw[mapping.title]||`Row ${row.rowNumber}`}</strong><small>{row.proposed?`${kindNames[row.proposed.kind]}${row.proposed.format?` · ${row.proposed.format}`:''}${row.proposed.edition?` · ${row.proposed.edition}`:''}`:row.error} · {row.status}</small></div>{row.status==='review'&&<div className="catalog-row-buttons">{row.candidates.map(candidate=><button key={candidate.id} className="subtle-button" disabled={busy} title={candidate.matchReason} onClick={()=>void commit('attach',row,candidate.id)}>{row.proposed?.physical?'Add physical item to':'Attach list entry to'} {candidate.title}{candidate.year?` (${candidate.year})`:''}</button>)}<button className="subtle-button" disabled={busy} onClick={()=>void commit('new',row)}>Keep separate</button><button className="text-button" disabled={busy} onClick={()=>void commit('skip',row)}>Skip</button></div>}{row.status==='error'&&<div className="catalog-row-buttons"><select aria-label={`Media type for row ${row.rowNumber}`} value={rowChoices[row.rowNumber]?.kind||''} onChange={event=>setRowChoices(previous=>({...previous,[row.rowNumber]:{kind:event.target.value,format:previous[row.rowNumber]?.format||format}}))} disabled={busy}><option value="">Choose media type…</option>{Object.entries(kindNames).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select>{page.batch?.mode!=='titles'&&<select aria-label={`Physical format for row ${row.rowNumber}`} value={rowChoices[row.rowNumber]?.format||''} onChange={event=>setRowChoices(previous=>({...previous,[row.rowNumber]:{kind:previous[row.rowNumber]?.kind||'',format:event.target.value}}))} disabled={busy}><option value="">Choose format…</option>{formats.map(value=><option key={value} value={value}>{value}</option>)}</select>}<button className="subtle-button" disabled={busy||!rowChoices[row.rowNumber]?.kind||(page.batch?.mode==='physical'||page.batch?.mode==='source'&&row.raw[mapping.sourceType]?.toLowerCase()==='physical')&&!rowChoices[row.rowNumber]?.format} onClick={()=>void classify(row)}>Check this row</button><button className="text-button" disabled={busy} onClick={()=>void commit('skip',row)}>Skip</button></div>}{row.status==='ready'&&<button className="subtle-button" disabled={busy} onClick={()=>void commit('new',row)}>Add</button>}</div>)}</div>{page.total>25&&<div className="catalog-list-actions"><button className="subtle-button" disabled={busy||offset===0} onClick={()=>void refresh(page.batch?.id,Math.max(0,offset-25),filter)}>Previous</button><span className="muted small">{offset+1}–{Math.min(offset+25,page.total)} of {page.total}</span><button className="subtle-button" disabled={busy||offset+25>=page.total} onClick={()=>void refresh(page.batch?.id,offset+25,filter)}>Next</button></div>}</div>}
    {phase===3&&page?.batch&&<div className="catalog-list-preview"><label className="field"><span>Optional local metadata review for one staged row</span><select value={metadataRowNumber||''} onChange={event=>{setMetadataRowNumber(Number(event.target.value));setMetadataEntityId('');}}><option value="">Choose a row on this page</option>{page.rows.filter(row=>row.proposed&&['ready','review'].includes(row.status)).map(row=><option key={row.rowNumber} value={row.rowNumber}>Row {row.rowNumber}: {row.proposed?.title}</option>)}</select></label>{metadataRow?.proposed&&<><MetadataCandidateReview key={`${page.batch.id}-${metadataRow.rowNumber}`} title={metadataRow.proposed.title} kind={metadataRow.proposed.kind} year={metadataRow.proposed.year} identifier={mapping.barcode&&metadataRow.raw[mapping.barcode]?{namespace:metadataRow.proposed.kind==='book'?'isbn':'upc-ean',value:metadataRow.raw[mapping.barcode]}:undefined} selectedId={metadataEntityId} onSelect={setMetadataEntityId} disabled={busy}/><p className="muted small">The selected work identity is linked only when you use this row’s existing Add or Attach action. Bulk ready-row commits leave identities unconfirmed.</p></>}</div>}
    {error&&<p className="error-text" role="alert">{error}</p>}
    <p className="muted small">This adds catalog records only. Media files copied by this list: {bytes(0)}.</p>
    <div className="catalog-list-actions"><a className="text-button" href="/api/catalog/export.csv">Spreadsheet export</a><a className="text-button" href="/api/catalog/export.sqlite3">Complete catalog export</a></div>
  </div></DialogContent></Dialog>;
}
