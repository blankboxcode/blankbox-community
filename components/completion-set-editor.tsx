'use client';

import { useState } from 'react';
import { ArrowDown, ArrowUp, Plus, Trash2 } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { blankBoxClient, type CompletionSet } from '@/lib/blank-box-client';
import { formatsByKind } from '@/lib/collecting-formats';

type Member = { title: string; year: number | null; format: string; workId: string | null };
export function CompletionSetEditor({ set, onClose, onSaved }: { set: CompletionSet; onClose: () => void; onSaved: () => Promise<void> }) {
  const initial = set.members.filter(m => !m.ignored).map(({ title, year, format, workId }) => ({ title, year, format, workId }));
  const [members, setMembers] = useState<Member[]>(initial);
  const [name, setName] = useState(set.name);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const dirty = name !== set.name || JSON.stringify(members) !== JSON.stringify(initial);
  const close = () => { if (!busy && (!dirty || window.confirm('Discard unsaved collection plan changes?'))) onClose(); };
  const update = (index: number, value: Partial<Member>) => setMembers(current => current.map((member, i) => i === index ? { ...member, ...value, ...('title' in value || 'year' in value ? { workId: null } : {}) } : member));
  const move = (index: number, offset: number) => setMembers(current => { const next = [...current]; [next[index], next[index + offset]] = [next[index + offset], next[index]]; return next; });
  async function save() { setBusy(true); try { await blankBoxClient.action('completion-set-save', { id: set.id, name, mediaKind: set.mediaKind, members }); await onSaved(); onClose(); } catch (cause) { setError((cause as Error).message); } finally { setBusy(false); } }
  return <Dialog open onOpenChange={value => !value && close()}><DialogContent className="form-dialog completion-set-editor"><DialogHeader><DialogTitle>Edit collection plan</DialogTitle><DialogDescription>You decide which titles count and their order. Changing a title or year removes its old reference match until reviewed again. This does not change ownership.</DialogDescription></DialogHeader><label className="field"><span>Name</span><input value={name} maxLength={120} onChange={event => setName(event.target.value)}/></label><div className="completion-set-members">{members.map((member, index) => <fieldset key={index}><legend>Title {index + 1}</legend><label className="field"><span>Title</span><input value={member.title} maxLength={250} onChange={event => update(index, { title: event.target.value })}/></label><div className="form-grid"><label className="field"><span>Year, if known</span><input type="number" min={1800} max={2200} value={member.year ?? ''} onChange={event => update(index, { year: event.target.value ? Number(event.target.value) : null })}/></label><label className="field"><span>Wanted format</span><select value={member.format} onChange={event => update(index, { format: event.target.value })}>{formatsByKind[set.mediaKind].map(format => <option key={format}>{format}</option>)}</select></label></div><div className="collecting-row-actions"><button className="text-button" type="button" disabled={!index} aria-label={`Move ${member.title} earlier`} onClick={() => move(index, -1)}><ArrowUp size={16}/></button><button className="text-button" type="button" disabled={index === members.length - 1} aria-label={`Move ${member.title} later`} onClick={() => move(index, 1)}><ArrowDown size={16}/></button><button className="text-button" type="button" aria-label={`Remove ${member.title} from plan`} onClick={() => setMembers(current => current.filter((_, i) => i !== index))}><Trash2 size={16}/></button></div></fieldset>)}</div><button className="subtle-button" disabled={members.length >= 200} onClick={() => setMembers(current => [...current, { title: '', year: null, format: 'Any', workId: null }])}><Plus size={16}/>Add another title</button>{error && <p role="alert" className="error-text">{error}</p>}<button className="primary-button" disabled={busy || !name.trim() || !members.length || members.some(m => !m.title.trim())} onClick={() => void save()}>{busy ? 'Saving…' : 'Save plan'}</button></DialogContent></Dialog>;
}
