'use client';

import { useEffect, useState } from 'react';
import { blankBoxClient, type MetadataEdition } from '@/lib/blank-box-client';
import { formatsByKind } from '@/lib/collecting-formats';
import type { MediaItem } from '@/lib/media';
import { EditionReferenceActions } from '@/components/edition-reference-actions';

export function KnownEditions({ item, onFind }: { item: MediaItem; onFind: (format: string) => void }) {
  const [editions, setEditions] = useState<MetadataEdition[] | null>(null);
  const [workId, setWorkId] = useState('');
  const [format, setFormat] = useState('');
  const [edition, setEdition] = useState('');
  const [season, setSeason] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [editingId, setEditingId] = useState('');
  const [editFormat, setEditFormat] = useState('');
  const [editEdition, setEditEdition] = useState('');
  const [editSeason, setEditSeason] = useState('');
  const [linkingId,setLinkingId]=useState('');
  const [fileId,setFileId]=useState('');
  const files=item.sources.filter(source=>['local','digital'].includes(source.type)&&source.id);
  const linkFile=async(row:MetadataEdition,sourceId:string,unlink=false)=>{if(!sourceId||busy)return;if(!window.confirm(`${unlink?'Unlink':'Confirm'} this file’s metadata association with ${row.title} · ${row.edition||row.format||'this release'}? This does not add or remove a physical copy, or change the file.`))return;setBusy(true);setError('');try{await blankBoxClient.action(unlink?'metadata-unlink':'metadata-confirm',{targetType:'digital_source',targetId:sourceId,entityId:row.id,confirm:true});await refresh();setLinkingId('');}catch(cause){setError((cause as Error).message);}finally{setBusy(false);}};
  const choices = (formatsByKind[item.kind] || []).filter(value => value !== 'Any' && value !== 'Other');

  useEffect(() => {
    let active = true;
    void blankBoxClient.action('metadata-editions', { itemId: item.id }).then(result => {
      if (active) { setEditions(result.editions || []); setWorkId(result.workId || ''); }
    }).catch(cause => { if (active) setError((cause as Error).message); });
    return () => { active = false; };
  }, [item.id, item.sources]);

  const add = async () => {
    if (!workId || !format || busy) return;
    if (editions?.some(row => row.format?.toLocaleLowerCase() === format.toLocaleLowerCase() && (row.edition || '').toLocaleLowerCase() === edition.trim().toLocaleLowerCase() && (row.season || '') === season)) {
      setError('That format and edition is already recorded. Add a copy to its existing edition.');
      return;
    }
    setBusy(true); setError('');
    try {
      await blankBoxClient.metadataCreate({ title: item.title, kind: item.kind, level: 'release', workId, year: item.year, format, edition: edition.trim(), ...(item.kind === 'tv' && season ? { season } : {}) });
      const result = await blankBoxClient.action('metadata-editions', { itemId: item.id });
      setEditions(result.editions || []); setEdition(''); setSeason('');
    } catch (cause) { setError((cause as Error).message); }
    finally { setBusy(false); }
  };

  const refresh = async () => {
    const result = await blankBoxClient.action('metadata-editions', { itemId: item.id });
    setEditions(result.editions || []);
  };
  const saveEdit = async () => {
    if (!editingId || !editFormat || busy) return;
    if (editions?.some(row => row.id !== editingId && row.format?.toLocaleLowerCase() === editFormat.toLocaleLowerCase() && (row.edition || '').toLocaleLowerCase() === editEdition.trim().toLocaleLowerCase() && (row.season || '') === editSeason)) {
      setError('That format and edition is already recorded.'); return;
    }
    setBusy(true); setError('');
    try {
      const current = editions?.find(row => row.id === editingId);
      if (current?.format !== editFormat) await blankBoxClient.metadataEdit(editingId, 'format', editFormat);
      if ((current?.edition || '') !== editEdition.trim()) await blankBoxClient.metadataEdit(editingId, 'edition', editEdition.trim());
      if ((current?.season || '') !== editSeason) await blankBoxClient.metadataEdit(editingId, 'season', editSeason || null);
      await refresh(); setEditingId('');
    } catch (cause) { setError((cause as Error).message); }
    finally { setBusy(false); }
  };
  const remove = async (row: MetadataEdition) => {
    if (busy || !window.confirm(`Remove the known ${[row.format, row.edition].filter(Boolean).join(' · ')} reference? Physical copies remain unchanged.`)) return;
    setBusy(true); setError('');
    try { await blankBoxClient.action('metadata-release-remove', { id: row.id, confirm: true }); await refresh(); setEditingId(''); }
    catch (cause) { setError((cause as Error).message); }
    finally { setBusy(false); }
  };

  if (!choices.length || error && !workId) return null;
  const other = editions?.filter(row => row.origin !== 'household-copy') || [];
  const references = other.filter(row => row.origin !== 'household-file');
  const ownedCount = references.filter(row => row.status === 'owned').length;
  const missingCount = references.filter(row => row.status === 'missing').length;
  const reviewCount = references.filter(row => row.status === 'review' || row.status === 'unknown').length;
  return <section className="known-editions">
    <div className="item-detail-section-heading"><div><h3>Known formats and editions</h3><p>Uses saved references and installed edition packs linked to this work.</p></div></div>
    {!!references.length && <p className="muted small">{ownedCount === references.length ? `All ${ownedCount} known physical editions are matched.` : `${ownedCount} matched · ${missingCount} missing · ${reviewCount} to review`}{references.some(row => row.status === 'digital') ? ' · Digital links do not establish physical ownership.' : ''} Reference coverage may be incomplete.</p>}
    {other.length ? <div className="known-edition-list">{other.map(row => <div className="known-edition-row" key={row.id}>
      {editingId === row.id ? <div className="known-edition-edit"><div className="form-grid"><label className="field"><span>Format</span><select value={editFormat} onChange={event => setEditFormat(event.target.value)}>{[...new Set([...choices, row.format || ''].filter(Boolean))].map(value => <option key={value} value={value}>{value}</option>)}</select></label><label className="field"><span>Edition</span><input maxLength={120} value={editEdition} onChange={event => setEditEdition(event.target.value)}/></label></div>{item.kind === 'tv' && <label className="field"><span>TV season</span><select value={editSeason} onChange={event => setEditSeason(event.target.value)}><option value="">Unknown season</option><option value="complete-series">Complete series</option><option value="specials">Specials</option>{Array.from({ length: 99 }, (_, index) => <option key={index + 1} value={String(index + 1)}>Season {index + 1}</option>)}</select></label>}<button className="subtle-button" type="button" disabled={busy || !editFormat} onClick={() => void saveEdit()}>Save correction</button><button className="text-button" type="button" onClick={() => setEditingId('')}>Cancel</button></div> : <><span><strong>{[row.format, row.edition, row.season === 'complete-series' ? 'Complete series' : row.season === 'specials' ? 'Specials' : row.season ? `Season ${row.season}` : ''].filter(Boolean).join(' · ') || row.title}</strong>{row.identifier && <small>{row.identifier.namespace === 'isbn' ? 'ISBN' : 'UPC/EAN'}: {row.identifier.value}</small>}<small>{row.status === 'digital' ? 'Linked digital file' : row.status === 'owned' ? 'Matched to a physical copy' : row.status === 'missing' ? 'Not recorded in your collection' : row.status === 'review' ? 'Check which release your copy is' : 'Format needs review'} · {row.origin === 'household-file' ? 'Your file edition' : row.origin === 'manual' ? 'Your reference' : row.origin.startsWith('pack:') ? 'Installed reference pack' : 'Saved reference'}</small></span><div className="known-edition-actions"><EditionReferenceActions item={item} edition={row} disabled={busy} onChanged={refresh}/>{!!files.length&&row.origin!=='household-file'&&<><button className="text-button" disabled={busy} onClick={()=>{setLinkingId(linkingId===row.id?'':row.id);setFileId(files[0].id!);}}>Link digital file</button>{row.digitalSourceIds?.map(id=><button className="text-button" key={id} disabled={busy} onClick={()=>void linkFile(row,id,true)}>Unlink {files.find(source=>source.id===id)?.label||'file'}</button>)}{linkingId===row.id&&<div className="known-edition-file-link"><label className="field"><span>File matching this release</span><select value={fileId} onChange={event=>setFileId(event.target.value)}>{files.map(source=><option value={source.id} key={source.id}>{source.trackTitle||source.path||source.label}</option>)}</select></label><p className="muted small">Confirm only a matching release. A digital link does not record ownership of its physical format.</p><button className="subtle-button" disabled={busy||!fileId} onClick={()=>void linkFile(row,fileId)}>Confirm file match</button></div>}</>}{row.status === 'missing' && row.format && !row.edition && <button className="text-button" type="button" onClick={() => onFind(row.format!)}>Find this format</button>}{row.origin === 'manual' && <><button className="text-button" type="button" disabled={busy} onClick={() => { setEditingId(row.id); setEditFormat(row.format || ''); setEditEdition(row.edition || ''); setEditSeason(row.season || ''); setError(''); }}>Edit</button><button className="text-button" type="button" disabled={busy} onClick={() => void remove(row)}>Remove</button></>}</div></>}
    </div>)}</div> : <p className="item-detail-empty-note">No other editions are recorded for this title yet. Confirm its work reference and install a pack with edition records to expand coverage.</p>}
    {error&&<p role="alert" className="error-text">{error}</p>}
    <details className="known-edition-add"><summary>Record a known format or edition</summary>
      <p className="muted small">Use this for a format or edition you know exists. It does not add an owned copy or confirm an exact release.</p>
      <div className="form-grid"><label className="field"><span>Format</span><select value={format} onChange={event => setFormat(event.target.value)}><option value="">Choose format</option>{choices.map(value => <option key={value} value={value}>{value}</option>)}</select></label><label className="field"><span>Edition, if known</span><input maxLength={120} value={edition} onChange={event => setEdition(event.target.value)} placeholder="Collector’s edition"/></label></div>
      {item.kind === 'tv' && <label className="field"><span>TV season</span><select value={season} onChange={event => setSeason(event.target.value)}><option value="">Unknown season</option><option value="complete-series">Complete series</option><option value="specials">Specials</option>{Array.from({ length: 99 }, (_, index) => <option key={index + 1} value={String(index + 1)}>Season {index + 1}</option>)}</select></label>}
      <button className="subtle-button" type="button" disabled={!format || busy} onClick={() => void add()}>{busy ? 'Saving…' : 'Save known edition'}</button>
      {error && <p role="alert" className="error-text">{error}</p>}
    </details>
  </section>;
}
