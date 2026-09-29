'use client';

import { useEffect, useState } from 'react';
import { Check, History, Undo2 } from 'lucide-react';
import { blankBoxClient } from '@/lib/blank-box-client';
import { activityLabel, type ActivityEvent, type ActivityStatus, type ItemActivity } from '@/lib/collection-organization';
import type { MediaItem } from '@/lib/media';

export function ItemActivityPanel({ item, onChange, season }: { item: MediaItem; onChange: () => void; season?: number }) {
  const scopeKey=season===undefined?undefined:`S${season}`;
  const [activity, setActivity] = useState<ItemActivity>(season===undefined?item.activity || { status: 'not-started' }:{status:'not-started'});
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [history, setHistory] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [episode, setEpisode] = useState('');
  const [status, setStatus] = useState<ActivityStatus>('completed');
  const [versionId, setVersionId] = useState('');
  async function request(action: string, data: Record<string, unknown> = {}) {
    setBusy(true); setError('');
    try {
      const result = await blankBoxClient.action(action, { id: item.id, ...(scopeKey?{scopeKey}:{}), ...data }) as unknown as { activity: ItemActivity; scopeActivity?:ItemActivity; events: ActivityEvent[] };
      setActivity(result.scopeActivity||result.activity); setEvents(result.events);
      if (action !== 'activity-history') onChange();
    } catch (cause) { setError((cause as Error).message); }
    finally { setBusy(false); }
  }
  useEffect(() => { let active = true; blankBoxClient.action('activity-history', { id: item.id, ...(scopeKey?{scopeKey}:{}) }).then(result => { if (active) { const value = result as unknown as { activity: ItemActivity; scopeActivity?:ItemActivity; events: ActivityEvent[] }; setActivity(value.scopeActivity||value.activity); setEvents(value.events); } }).catch(() => { if (active) setError('Activity could not be loaded. Try opening history again.'); }); return () => { active = false; }; }, [item.id, scopeKey]);
  const record = (value: ActivityStatus, episodeKey = '') => request('activity-set', { status: value, episodeKey: scopeKey||episodeKey, eventId: Array.from(crypto.getRandomValues(new Uint32Array(4))).join('-'), ...(versionId ? { versionId } : {}) });
  return <section className="item-activity" aria-label={season===undefined?'Local activity':`Season ${season} watch status`}>
    <div className="item-activity-heading"><strong>{season===undefined?activityLabel(item.kind, activity.status):'Watch Status'}</strong><button type="button" className="text-button" onClick={() => { setHistory(!history); if (!history) void request('activity-history'); }}><History size={15}/>History</button></div>
    <div className="activity-status-buttons" role="group" aria-label="Set local activity status">{(['not-started', 'in-progress', 'completed'] as const).map(value => <button type="button" key={value} disabled={busy} className={activity.status === value ? 'selected' : ''} aria-pressed={activity.status === value} onClick={() => void record(value)}>{activity.status === value && <Check size={14}/>} {activityLabel(item.kind, value)}</button>)}</div>
    {item.kind === 'tv' && season===undefined && <p className="muted small">Series status is manual. Recording an episode does not mark the whole series watched.</p>}
    {history && <div className="activity-history">
      <p className="muted small">Saved on this Blank Box. Provider sync and playback resume positions do not overwrite your status. The latest 50 events are shown.</p>
      {season===undefined&&<details><summary>Record an edition{item.kind === 'tv' ? ' or episode' : ''}</summary><div className="form-grid"><label className="field"><span>Edition (optional)</span><select value={versionId} onChange={event => setVersionId(event.target.value)}><option value="">Whole item</option>{item.versions?.map(version => <option key={version.id} value={version.id}>{version.label}</option>)}</select></label>{item.kind === 'tv' && <label className="field"><span>Episode (optional)</span><input placeholder="S1E1" maxLength={10} value={episode} onChange={event => setEpisode(event.target.value.toUpperCase())}/></label>}<label className="field"><span>Status</span><select value={status} onChange={event => setStatus(event.target.value as ActivityStatus)}>{(['not-started', 'in-progress', 'completed'] as const).map(value => <option key={value} value={value}>{activityLabel(item.kind, value)}</option>)}</select></label></div><button className="subtle-button" type="button" disabled={busy || !!episode && !/^S\d{1,3}E\d{1,4}$/.test(episode)} onClick={() => void record(status, episode)}>Record activity</button></details>}
      {events.length ? events.map(event => <div className={`activity-event ${event.undoneAt ? 'undone' : ''}`} key={event.id}><span><strong>{activityLabel(item.kind, event.status)}{event.episodeKey && ` · ${event.episodeKey}`}</strong><small>{new Date(event.createdAt).toLocaleString()}{event.versionId && ` · ${item.versions?.find(version => version.id === event.versionId)?.label || 'Recorded edition'}`}{event.undoneAt && ' · Undone'}</small></span>{!event.undoneAt && <button className="text-button" type="button" disabled={busy} onClick={() => void request('activity-undo', { eventId: event.id })}><Undo2 size={14}/>Undo</button>}</div>) : <p className="muted small">No activity recorded yet.</p>}
    </div>}
    {error && <p className="error-text" role="alert">{error}</p>}
  </section>;
}
