'use client';

import { useEffect, useState } from 'react';
import { FolderSearch, RefreshCw, Search, ShieldCheck } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { blankBoxClient, type InventoryPage, type InventoryReview } from '@/lib/blank-box-client';
import { MetadataCandidateReview } from '@/components/metadata-candidate-review';
import { bytes, kindNames, type Job, type Kind, type LibraryState, type MediaItem } from '@/lib/media';

const pageSize = 15;

export function SourceInventory({ sourceId, jobs, blocked, backupConfigured, backupPath, onSetupBackup, onStarted }: {
  sourceId: string;
  jobs: LibraryState['jobs'];
  blocked: boolean;
  backupConfigured: boolean;
  backupPath?: string;
  onSetupBackup: () => void;
  onStarted: () => Promise<unknown>;
}) {
  const [page, setPage] = useState<InventoryPage | null>(null);
  const [offset, setOffset] = useState(0);
  const [kind, setKind] = useState('');
  const [query, setQuery] = useState('');
  const [group, setGroup] = useState('');
  const [unlinkedOnly, setUnlinkedOnly] = useState(false);
  const [error, setError] = useState('');
  const [working, setWorking] = useState(false);
  const [selected, setSelected] = useState<InventoryPage['files'][number] | null>(null);
  const [reviewSelection,setReviewSelection]=useState<Set<string>>(new Set());
  const [reviewQueue,setReviewQueue]=useState<InventoryPage['files']>([]);
  const [attachFiles,setAttachFiles]=useState<InventoryPage['files']>([]);
  const [attachQuery,setAttachQuery]=useState('');
  const [attachResults,setAttachResults]=useState<MediaItem[]>([]);
  const [attachTarget,setAttachTarget]=useState<MediaItem|null>(null);
  const [attachBusy,setAttachBusy]=useState(false);
  const [attachError,setAttachError]=useState('');
  const [pageSort,setPageSort]=useState<'path'|'kind'|'size'>('path');
  const [title, setTitle] = useState('');
  const [selectedKind, setSelectedKind] = useState<Kind>('file');
  const [year, setYear] = useState('');
  const [review, setReview] = useState<InventoryReview | null>(null);
  const [target, setTarget] = useState('unselected');
  const [metadataEntityId, setMetadataEntityId] = useState('');
  const [reviewError, setReviewError] = useState('');
  const [reviewBusy, setReviewBusy] = useState(false);
  const [renamePreview, setRenamePreview] = useState<{originalPath:string;proposedPath:string;changed:boolean;collision:boolean}|null>(null);
  const [backupSelection, setBackupSelection] = useState<{batchId:string|null;files:Record<string,number>}>({batchId:null,files:{}});
  const [bulkJob, setBulkJob] = useState<Job | null>(null);
  const [bulkWarningAccepted, setBulkWarningAccepted] = useState(false);
  const inventoryJob = jobs.find(job => job.type === 'inventory' && ['queued', 'running'].includes(job.status));
  const jobStatus = jobs.find(job => job.type === 'inventory')?.status;
  const recentBulkJob = (bulkJob?.sourceId===sourceId?bulkJob:null) || jobs.find(job => job.sourceId === sourceId && (job.type === 'inventory-bulk-preview' || job.type === 'inventory-bulk-link'));

  useEffect(() => {
    if (!bulkJob || !['queued', 'running'].includes(bulkJob.status)) return;
    let cancelled = false;
    const timer = window.setInterval(() => {
      void blankBoxClient.jobs().then(result => {
        if (cancelled) return;
        const updated = result.jobs.find(job => job.id === bulkJob.id);
        if (updated) {
          setBulkJob(updated);
          if (!['queued', 'running'].includes(updated.status)) void onStarted();
        }
      }).catch(cause => { if (!cancelled) setError((cause as Error).message); });
    }, 3000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [bulkJob, onStarted]);

  useEffect(() => {
    if (!sourceId) return;
    let cancelled = false;
    const timer = window.setTimeout(() => {
      blankBoxClient.inventory(sourceId, { limit: pageSize, offset, kind, query, group, unlinkedOnly })
        .then(result => { if (!cancelled) { setPage(result); setError(''); } })
        .catch(cause => { if (!cancelled) setError((cause as Error).message); });
    }, query ? 250 : 0);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [sourceId, offset, kind, query, group, unlinkedOnly, jobStatus, inventoryJob?.done, recentBulkJob?.status, recentBulkJob?.done]);


  if (!sourceId) return <p className="muted small">Choose a source to inventory it without copying files.</p>;

  const start = async (resumeId?: string) => {
    setWorking(true);
    setError('');
    try {
      await blankBoxClient.action('inventory', { sourceId, ...(resumeId ? { resumeId } : {}) });
      await onStarted();
    } catch (cause) { setError((cause as Error).message); }
    finally { setWorking(false); }
  };
  const planBulk = async (retryUnmatched = false) => {
    setWorking(true);setError('');setBulkWarningAccepted(false);setBulkJob(null);
    try {
      const result = await blankBoxClient.action('inventory-bulk-preview', {sourceId, ...(retryUnmatched ? {retryUnmatched:true} : {})});
      if (result.id) setBulkJob({id:result.id,type:'inventory-bulk-preview',sourceId,status:'queued',done:0,total:0});
      await onStarted();
    } catch (cause) { setError((cause as Error).message); }
    finally { setWorking(false); }
  };
  const commitBulk = async () => {
    const preview = recentBulkJob?.preview;
    if (!preview || !bulkWarningAccepted) return;
    setWorking(true);setError('');
    try {
      const result = await blankBoxClient.action('inventory-bulk-commit', {previewId:preview.id,confirmBulk:true,warningAccepted:true,confirmedFileCount:preview.counts.linkFiles});
      if (result.id) setBulkJob({id:result.id,type:'inventory-bulk-link',sourceId,status:'queued',done:0,total:preview.counts.linkFiles});
      await onStarted();
    } catch (cause) { setError((cause as Error).message); }
    finally { setWorking(false); }
  };
  const batch = page?.batch;
  const reviewableFiles=(page?.files||[]).filter(file=>!file.linked_item_id||file.needs_review);
  const sortedPageFiles=[...(page?.files||[])].sort((a,b)=>pageSort==='size'?b.bytes-a.bytes||a.relative_path.localeCompare(b.relative_path):pageSort==='kind'?a.kind.localeCompare(b.kind)||a.relative_path.localeCompare(b.relative_path):a.relative_path.localeCompare(b.relative_path));
  const selectedReviewCount=sortedPageFiles.filter(file=>reviewSelection.has(file.relative_path)&&(!file.linked_item_id||file.needs_review)).length;
  const selectedBackupFiles = backupSelection.batchId === batch?.id ? backupSelection.files : {};
  const backupCount = Object.keys(selectedBackupFiles).length;
  const backupBytes = Object.values(selectedBackupFiles).reduce((sum, size) => sum + size, 0);
  const backUpSelected = async () => {
    if (!batch || !backupCount || !backupConfigured || blocked || working) return;
    if (!window.confirm(`Back up ${backupCount} selected personal file${backupCount === 1 ? '' : 's'} (${bytes(backupBytes)}) to ${backupPath || 'the configured backup destination'}? Originals will stay where they are. This is separate from the Blank Box catalog backup.`)) return;
    setWorking(true);setError('');
    try {
      await blankBoxClient.action('backup-indexed', { batchId: batch.id, paths: Object.keys(selectedBackupFiles), confirmedCount: backupCount, confirmedBytes: backupBytes, confirmPersonalFiles: true });
      setBackupSelection({batchId:null,files:{}});await onStarted();
    } catch (cause) { setError((cause as Error).message); }
    finally { setWorking(false); }
  };
  const backUpAll = async () => {
    if (!sourceId || !backupConfigured || blocked || working) return;
    setWorking(true);setError('');
    try {
      const preview=await blankBoxClient.action('backup-indexed-all-preview',{sourceId});
      if (!preview.batchId || !preview.count) { setError('No indexed photos, home videos, or personal files are available for backup in this source.'); return; }
      if (!window.confirm(`Back up all ${preview.count.toLocaleString()} indexed photos, home videos, and personal files in this source (${bytes(preview.bytes||0)}) to ${backupPath || 'the configured backup destination'}? ${preview.partial?'The index reported scan issues, so files it could not index are excluded. ':''}This may take a long time. Originals stay in place. Collection records and managed media use the separate library backup.`)) return;
      await blankBoxClient.action('backup-indexed-all',{sourceId,batchId:preview.batchId,confirmedCount:preview.count,confirmedBytes:preview.bytes,confirmPersonalFiles:true});
      await onStarted();
    } catch (cause) { setError((cause as Error).message); }
    finally { setWorking(false); }
  };
  const signature = `${title.trim()}|${selectedKind}|${year.trim()}`;
  const reviewedSignature = review ? `${review.record.title}|${review.record.kind}|${review.record.year ?? ''}` : '';
  const findMatches = async (path: string, wantedTitle: string, wantedKind: Kind, wantedYear: string) => {
    if (!batch) return;
    setReviewBusy(true); setReviewError(''); setTarget('unselected'); setMetadataEntityId(''); setReview(null);setRenamePreview(null);
    try {
      const result = await blankBoxClient.inventoryReview({ batchId: batch.id, path, title: wantedTitle.trim(), kind: wantedKind, year: wantedYear.trim() ? Number(wantedYear) : null });
      setReview(result);
      if(result.linkedItemId){const item=await blankBoxClient.item(result.linkedItemId);setReview({...result,candidates:[{...item,matchConfidence:'review',matchReason:'Currently linked title; confirm this changed file'} as InventoryReview['candidates'][number],...result.candidates.filter(candidate=>candidate.id!==item.id)]});setTarget(item.id);}else if (!result.candidates.length) setTarget('new');
    } catch (cause) { setReviewError((cause as Error).message); }
    finally { setReviewBusy(false); }
  };
  const openReview = (file: InventoryPage['files'][number]) => {
    setSelected(file);setTitle(file.title);setSelectedKind(file.kind);setYear(file.year ? String(file.year) : '');setRenamePreview(null);
    void findMatches(file.relative_path, file.title, file.kind, file.year ? String(file.year) : '');
  };
  const link = async () => {
    if (!selected || !batch || !review || signature !== reviewedSignature || target === 'unselected') return;
    setReviewBusy(true);setReviewError('');
    try {
      await blankBoxClient.action('inventory-link', { batchId: batch.id, path: selected.relative_path, title: title.trim(), kind: selectedKind, year: year.trim() ? Number(year) : null, ...(target === 'new' ? {} : { targetId: target }), ...(metadataEntityId ? { metadataEntityId } : {}), confirm: true });
      setPage(await blankBoxClient.inventory(sourceId, { limit: pageSize, offset, kind, query, group, unlinkedOnly }));
      setReviewSelection(current=>{const next=new Set(current);next.delete(selected.relative_path);return next;});
      if(reviewQueue.length>1){const remaining=reviewQueue.slice(1);setReviewQueue(remaining);openReview(remaining[0]);}else{setReviewQueue([]);setSelected(null);setReview(null);}
      await onStarted();
    } catch (cause) { setReviewError((cause as Error).message); }
    finally { setReviewBusy(false); }
  };
  const searchAttachTarget=async()=>{
    if(!attachQuery.trim())return;
    setAttachBusy(true);setAttachError('');setAttachTarget(null);
    try{const result=await blankBoxClient.action('match-search',{query:attachQuery.trim().slice(0,200),sourceScope:'all'});setAttachResults((result.results||[]).filter((item:MediaItem)=>item.kind===attachFiles[0]?.kind));}
    catch(cause){setAttachError((cause as Error).message);}finally{setAttachBusy(false);}
  };
  const attachSelected=async()=>{
    if(!batch||!attachTarget||attachFiles.length<2)return;
    if(!window.confirm(`Attach all ${attachFiles.length} selected ${kindNames[attachFiles[0].kind].toLowerCase()} files to “${attachTarget.title}” (${attachTarget.id})? Check the file list first. Existing title facts and its Media Item ID stay in place. Original files will not be moved, renamed, or copied.`))return;
    setAttachBusy(true);setAttachError('');
    try{
      await blankBoxClient.action('inventory-link-selected',{batchId:batch.id,paths:attachFiles.map(file=>file.relative_path),targetId:attachTarget.id,targetTitle:attachTarget.title,confirmedCount:attachFiles.length,confirm:true});
      setPage(await blankBoxClient.inventory(sourceId,{limit:pageSize,offset,kind,query,group,unlinkedOnly}));
      setReviewSelection(current=>{const next=new Set(current);attachFiles.forEach(file=>next.delete(file.relative_path));return next;});
      setAttachFiles([]);setAttachTarget(null);await onStarted();
    }catch(cause){setAttachError((cause as Error).message);}finally{setAttachBusy(false);}
  };
  const previewName = async () => {
    if(!selected||!batch)return;
    setReviewBusy(true);setReviewError('');setRenamePreview(null);
    try{
      const result=await blankBoxClient.action('rename-preview',{batchId:batch.id,path:selected.relative_path,title:title.trim(),kind:selectedKind,year:year.trim()?Number(year):null});
      if(result.originalPath&&result.proposedPath)setRenamePreview({originalPath:result.originalPath,proposedPath:result.proposedPath,changed:!!result.changed,collision:!!result.collision});
    }catch(cause){setReviewError((cause as Error).message);}finally{setReviewBusy(false);}
  };
  return <div className="source-inventory">
    <div className="section-heading"><div><h3>Index existing files</h3><p className="muted small">Find files in place, then review how each one belongs in your library. No media is copied or moved.</p></div></div>
    <div className="inline-form">
      <button className="primary-button" disabled={blocked || working} onClick={() => void start()}><FolderSearch size={16}/>{batch ? 'Index again' : 'Index source'}</button>
      {batch && ['interrupted', 'partial', 'failed'].includes(batch.status) && <button className="subtle-button" disabled={blocked || working} onClick={() => void start(batch.id)}><RefreshCw size={16}/>Resume inventory</button>}
      {inventoryJob && <span className="muted small">{inventoryJob.message || 'Inventory in progress…'}</span>}
    </div>
    {error && <p className="error-text" role="alert">{error}</p>}
    {batch && <><p className="muted small">{batch.scanned.toLocaleString()} files · {bytes(batch.totalBytes)} · {batch.status}. Indexing has not copied or changed media files.</p>
      {!!batch.errors.length && <p className="error-text">{batch.errors.length} scan issue{batch.errors.length === 1 ? '' : 's'}: {batch.errors[0]}</p>}
      {batch.status === 'complete' && <div className="inventory-groups"><strong>Import this source in bulk</strong><p className="muted small">Preview matches against your existing library, including connected catalogs, and optional installed metadata packs. Uncertain files stay for manual review.</p><div className="inline-form"><button className="primary-button" disabled={blocked || working} onClick={() => void planBulk()}>Match all files (preview)</button>{recentBulkJob && !['queued','running'].includes(recentBulkJob.status) && (recentBulkJob.type==='inventory-bulk-link'||!!recentBulkJob.preview?.counts.needsReview) ? <button className="subtle-button" disabled={blocked || working} onClick={() => void planBulk(true)}>Recheck remaining for new titles</button> : null}</div>
        {recentBulkJob?.type === 'inventory-bulk-preview' && ['queued','running'].includes(recentBulkJob.status) && <p className="muted small" role="status">{recentBulkJob.message || 'Planning matches…'} {recentBulkJob.total ? `${recentBulkJob.done.toLocaleString()} of ${recentBulkJob.total.toLocaleString()} title groups` : ''}</p>}
        {recentBulkJob?.type === 'inventory-bulk-preview' && recentBulkJob.status === 'failed' && <p className="error-text" role="alert">Bulk preview stopped: {recentBulkJob.message}</p>}
        {recentBulkJob?.type === 'inventory-bulk-preview' && recentBulkJob.status === 'expired' && <p className="muted small">This preview expired after restart. Plan the import again.</p>}
        {recentBulkJob?.type === 'inventory-bulk-preview' && recentBulkJob.status === 'complete' && recentBulkJob.preview?.batchId === batch.id && <div className="inventory-candidates"><strong>{recentBulkJob.preview.retryUnmatched ? 'Second bulk import preview' : 'Bulk import preview'}</strong><p>{recentBulkJob.preview.counts.linkFiles.toLocaleString()} files ({bytes(recentBulkJob.preview.counts.linkBytes)}) can be linked in place.</p><p className="muted small">{recentBulkJob.preview.counts.matchExisting.toLocaleString()} files match existing Media Items · {recentBulkJob.preview.counts.newTitleFiles.toLocaleString()} files create {recentBulkJob.preview.counts.newTitles.toLocaleString()} new titles · {recentBulkJob.preview.counts.packReferences.toLocaleString()} new titles have a unique matching offline reference · {recentBulkJob.preview.counts.alreadyLinked.toLocaleString()} already linked · {recentBulkJob.preview.counts.needsReview.toLocaleString()} need review.</p><p className="muted small">Matching uses names, years, folders, your existing catalog and installed offline packs. The second pass can create only clear unmatched book, audiobook, or comic titles; ambiguous matches, changed files, and possible existing records remain for review. Blank Box will not copy, move, rename, delete or overwrite source files; a link is not a backup. This preview expires after one hour; plan again if it expires.</p>{recentBulkJob.preview.reviewSamples.length > 0 && <details><summary>Examples needing review</summary><ul>{recentBulkJob.preview.reviewSamples.map(sample => <li key={sample.path}>{sample.path}: {sample.reason}</li>)}</ul></details>}<label className="inventory-backup-choice"><input type="checkbox" checked={bulkWarningAccepted} onChange={event=>setBulkWarningAccepted(event.target.checked)}/>I reviewed the counts and understand that uncertain matches will remain for review.</label><button className="primary-button" disabled={blocked || working || !bulkWarningAccepted || !recentBulkJob.preview.counts.linkFiles} onClick={() => void commitBulk()}>Link {recentBulkJob.preview.counts.linkFiles.toLocaleString()} files</button></div>}
        {recentBulkJob?.type === 'inventory-bulk-link' && <p className={recentBulkJob.status === 'failed' ? 'error-text' : 'muted small'} role="status">Bulk linking {recentBulkJob.status}: {recentBulkJob.message || 'Starting…'} {recentBulkJob.total ? `${recentBulkJob.done.toLocaleString()} of ${recentBulkJob.total.toLocaleString()} files processed.` : ''} {recentBulkJob.status === 'partial' ? 'Review skipped files below.' : ''}</p>}
      </div>}
      {!!batch.scanned && <>{!!page?.groups?.length&&<div className="inventory-groups"><strong>Related files to review</strong><p className="muted small">Grouped by folder and filename clues. Unclear files can be reviewed individually.</p><div>{page.groups.filter(row=>row.unlinked>0).slice(0,12).map(row=><button className={`subtle-button ${group===row.groupKey?'selected':''}`} key={row.groupKey} onClick={()=>{setGroup(group===row.groupKey?'':row.groupKey);setOffset(0);}}>{row.title} · {row.count} files</button>)}{group&&<button className="text-button" onClick={()=>{setGroup('');setOffset(0);}}>Show all files</button>}</div></div>}<div className="inline-form">
        <input aria-label="Search indexed titles" placeholder="Search indexed titles" value={query} maxLength={100} onChange={event => { setQuery(event.target.value); setOffset(0); }}/>
        <select aria-label="Filter indexed media" value={kind} onChange={event => { setKind(event.target.value); setOffset(0); }}><option value="">All formats</option>{page?.counts.map(row => <option key={row.kind} value={row.kind}>{kindNames[row.kind]} ({row.count})</option>)}</select>
        <label className="inventory-backup-choice"><input type="checkbox" checked={unlinkedOnly} onChange={event=>{setUnlinkedOnly(event.target.checked);setOffset(0);}}/>Needs review</label>
      </div><div className="catalog-list-actions"><button className="subtle-button" type="button" disabled={!reviewableFiles.length} onClick={()=>setReviewSelection(new Set(reviewableFiles.map(file=>file.relative_path)))}>Select page for review</button><button className="text-button" type="button" onClick={()=>setReviewSelection(new Set())}>Clear selection</button><label className="field"><span>Sort this page</span><select value={pageSort} onChange={event=>setPageSort(event.target.value as 'path'|'kind'|'size')}><option value="path">Path</option><option value="kind">Media type</option><option value="size">Largest file</option></select></label><button className="subtle-button" type="button" disabled={blocked||working||!selectedReviewCount} onClick={()=>{const queue=sortedPageFiles.filter(file=>reviewSelection.has(file.relative_path)&&(!file.linked_item_id||file.needs_review));if(queue.length){setReviewQueue(queue);openReview(queue[0]);}}}>Review {selectedReviewCount} selected</button><button className="subtle-button" type="button" disabled={blocked||working||selectedReviewCount<2} onClick={()=>{const files=sortedPageFiles.filter(file=>reviewSelection.has(file.relative_path)&&(!file.linked_item_id||file.needs_review));if(files.some(file=>file.kind!==files[0].kind)){setError("Select files of one media type to attach together.");return;}setAttachFiles(files);setAttachQuery("");setAttachResults([]);setAttachTarget(null);setAttachError("");}}>Attach selected to one title</button></div><div className="scan-list">{sortedPageFiles.map(file => <div key={file.relative_path}><input type="checkbox" aria-label={`Select ${file.relative_path} for review`} checked={reviewSelection.has(file.relative_path)} disabled={!!file.linked_item_id&&!file.needs_review||blocked||working} onChange={event=>setReviewSelection(current=>{const next=new Set(current);if(event.target.checked)next.add(file.relative_path);else next.delete(file.relative_path);return next;})}/><FolderSearch size={16}/><span>{file.relative_path}</span><small>{kindNames[file.kind]} · {bytes(file.bytes)}</small>{file.linked_item_id && !file.needs_review ? <span className="inventory-linked">In library</span> : <button className="subtle-button inventory-review-button" disabled={blocked || working} onClick={() => openReview(file)}>{file.needs_review?'Review changed file':'Review & link'}</button>}{['photo','home-video','file'].includes(file.kind)&&<label className="inventory-backup-choice"><input type="checkbox" aria-label={`Select ${file.relative_path} for backup`} checked={selectedBackupFiles[file.relative_path] !== undefined} disabled={blocked||working} onChange={event=>setBackupSelection(current=>{const next={...(current.batchId===batch?.id?current.files:{})};if(event.target.checked)next[file.relative_path]=file.bytes;else delete next[file.relative_path];return {batchId:batch?.id||null,files:next};})}/>Back up</label>}</div>)}</div>
      <div className="inventory-backup-action"><div><strong>Back up personal files</strong><p className="muted small">{backupCount ? `${backupCount} selected · ${bytes(backupBytes)}. ` : 'Select up to 100 photos, home videos, or personal files for a manual batch, or back up every eligible indexed file in this source. '}Copies go only to your configured backup destination. Originals stay in place. Collection records and managed media use the separate library backup.</p></div>{backupConfigured?<><button className="subtle-button" disabled={!backupCount||blocked||working} onClick={()=>void backUpSelected()}><ShieldCheck size={16}/>Back up selected</button><button className="subtle-button" disabled={blocked||working||!['complete','partial'].includes(batch.status)} onClick={()=>void backUpAll()}><ShieldCheck size={16}/>Back up all indexed personal files</button></>:<button className="subtle-button" onClick={onSetupBackup}>Set up backup drive</button>}</div>
      {page?.total === 0 && <p className="muted small">No indexed files match these filters.</p>}
      {(page?.total || 0) > pageSize && <div className="inline-form"><button className="subtle-button" disabled={!offset} onClick={() => setOffset(Math.max(0, offset - pageSize))}>Previous</button><span className="muted small">{offset + 1}–{Math.min(offset + pageSize, page?.total || 0)} of {page?.total}</span><button className="subtle-button" disabled={offset + pageSize >= (page?.total || 0)} onClick={() => setOffset(offset + pageSize)}>Next</button></div>}</>}
    </>}
    <Dialog open={attachFiles.length>0} onOpenChange={open=>{if(!open&&!attachBusy){setAttachFiles([]);setAttachTarget(null);setAttachResults([]);setAttachError('');}}}><DialogContent className="form-dialog inventory-review-dialog"><DialogHeader><DialogTitle>Attach selected files to one title</DialogTitle><DialogDescription>Choose the existing Media Item for all selected files. Review the full list before confirming; no original file will change.</DialogDescription></DialogHeader>
      <p className="muted small">{attachFiles.length} selected {attachFiles[0]&&kindNames[attachFiles[0].kind]} files · up to 15 from this page. Files of different media types need separate selections.</p>
      <div className="inventory-selected-paths"><ul>{attachFiles.map(file=><li key={file.relative_path}>{file.relative_path}</li>)}</ul></div>
      <form className="match-search" onSubmit={event=>{event.preventDefault();void searchAttachTarget();}}><label><Search size={17}/><input value={attachQuery} maxLength={200} onChange={event=>setAttachQuery(event.target.value)} placeholder="Search for the show, album, or title" aria-label="Search destination Media Item"/></label><button className="subtle-button" disabled={attachBusy||!attachQuery.trim()} type="submit">Search library</button></form>
      <div className="inventory-candidates">{attachResults.map(item=><label key={item.id}><input type="radio" name="inventory-attach-target" checked={attachTarget?.id===item.id} onChange={()=>setAttachTarget(item)}/><span>{item.title}{item.year?` (${item.year})`:''}<small>{kindNames[item.kind]} · Media Item {item.id}</small></span></label>)}{!attachResults.length&&<p className="muted small">Search your library for an existing title. If it is missing, create it through individual review first.</p>}</div>
      {attachError&&<p role="alert" className="error-text">{attachError}</p>}
      <button className="primary-button" disabled={attachBusy||!attachTarget||attachFiles.length<2} onClick={()=>void attachSelected()}>Attach all {attachFiles.length} to {attachTarget?.title||'chosen title'}</button>
    </DialogContent></Dialog>
    <Dialog open={!!selected} onOpenChange={open => { if (!open) { setSelected(null);setReviewQueue([]);setReview(null);setReviewError(''); } }}><DialogContent className="form-dialog inventory-review-dialog"><DialogHeader><DialogTitle>Review this file</DialogTitle><DialogDescription>Confirm what it is and whether it belongs with an existing title. Blank Box will link the file where it is; it will not copy or rename it.</DialogDescription></DialogHeader>
      {selected && <><p className="muted small inventory-file-path">{selected.relative_path} · {bytes(selected.bytes)}</p>{!!selected.clues?.evidence?.length&&<p className="muted small">Title clues: {selected.clues.evidence.join(', ')}{selected.clues.artist?` · Artist folder: ${selected.clues.artist}`:''}{selected.clues.season!==undefined?` · Season ${selected.clues.season}`:''}{selected.clues.episode!==undefined?` · Episode ${selected.clues.episode}`:''}. Confirm before linking.</p>}<div className="inventory-review-fields"><label className="field"><span>Title</span><input maxLength={250} value={title} onChange={event => setTitle(event.target.value)}/></label><label className="field"><span>Media type</span><select value={selectedKind} onChange={event => setSelectedKind(event.target.value as Kind)}>{(Object.entries(kindNames) as [Kind, string][]).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label className="field"><span>Release year, if known</span><input type="number" min={1800} max={2200} value={year} onChange={event => setYear(event.target.value)}/></label></div>
        <button className="subtle-button" disabled={reviewBusy || !title.trim()} onClick={() => void findMatches(selected.relative_path, title, selectedKind, year)}>Find library matches</button>
        {reviewError && <p role="alert" className="error-text">{reviewError}</p>}
        {review && signature === reviewedSignature && <div className="inventory-candidates"><strong>{review.candidates.length ? 'Possible matches' : 'No matching title in your library'}</strong><p className="muted small">Suggestions come from your existing Blank Box titles only. A matching name does not prove the same edition.</p>{review.candidates.map(candidate => <label key={candidate.id}><input type="radio" name="inventory-target" checked={target === candidate.id} onChange={() => setTarget(candidate.id)}/><span>{candidate.title}{candidate.year ? ` (${candidate.year})` : ''}<small>{kindNames[candidate.kind]} · {candidate.matchReason}</small></span></label>)}<label><input type="radio" name="inventory-target" checked={target === 'new'} onChange={() => setTarget('new')}/><span>Create a separate library title<small>Keep this file independent of the suggested records.</small></span></label></div>}
        {review && signature === reviewedSignature && <MetadataCandidateReview key={signature} title={title.trim()} kind={selectedKind} year={year.trim()?Number(year):null} selectedId={metadataEntityId} onSelect={setMetadataEntityId} disabled={reviewBusy}/>}
        {reviewQueue.length>0&&<div className="catalog-list-actions"><span className="muted small">{reviewQueue.length} files remain in this review selection</span><button className="text-button" type="button" disabled={reviewBusy} onClick={()=>{const remaining=reviewQueue.slice(1);setReviewQueue(remaining);if(remaining.length)openReview(remaining[0]);else{setSelected(null);setReview(null);}}}>Skip this file</button></div>}
        <button className="primary-button" disabled={reviewBusy || !review || signature !== reviewedSignature || target === 'unselected'} onClick={() => void link()}>{reviewBusy ? 'Checking…' : 'Link file to library'}</button><p className="muted small">The original file remains on its drive. A linked file is not a backup and may be unavailable when that drive is disconnected.</p>
        <div className="inventory-rename-preview"><button className="text-button" disabled={reviewBusy||!title.trim()} onClick={()=>void previewName()}>Preview a cleaner filename</button>{renamePreview&&<p className="muted small">{renamePreview.originalPath} → {renamePreview.proposedPath}. {renamePreview.collision?'That name is already in use. ':renamePreview.changed?'Suggested name only. ':'The filename already matches. '}No original file was changed.</p>}</div></>}
    </DialogContent></Dialog>
  </div>;
}
