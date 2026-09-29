'use client';

import { ArrowDown, ArrowUp, Check } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { featuredMediaKeys, featuredMediaLabels, homeRowOptions, normalizeHomeHeroOrder, type HomeRow } from '@/lib/home-preferences';
import type { Settings } from '@/lib/media';

export function HomeCustomization({ settings, busy, onChange, onSave }: {
  settings: Settings;
  busy: boolean;
  onChange: (settings: Settings) => void;
  onSave: () => void;
}) {
  const rows = settings.homeRows || ['recently-added', 'recently-released'];
  const heroOrder = normalizeHomeHeroOrder(settings.homeHeroOrder);
  const move = <T extends string,>(items: T[], item: T, direction: -1 | 1): T[] => {
    const index = items.indexOf(item), target = index + direction;
    if (index < 0 || target < 0 || target >= items.length) return items;
    const result = [...items];
    [result[index], result[target]] = [result[target], result[index]];
    return result;
  };
  const controls = (label: string, index: number, length: number, onMove: (direction: -1 | 1) => void) => <span className="home-order-controls">
    <button type="button" aria-label={`Move ${label} up`} title={`Move ${label} up`} disabled={index <= 0} onClick={() => onMove(-1)}><ArrowUp size={15} /></button>
    <button type="button" aria-label={`Move ${label} down`} title={`Move ${label} down`} disabled={index >= length - 1} onClick={() => onMove(1)}><ArrowDown size={15} /></button>
  </span>;

  return <section className="panel home-customization-panel">
    <h2>Home layout</h2>
    <p className="muted small">Choose what appears in your featured cover and library rows. Categories with no matching media stay out of view.</p>
    <div className="home-settings-group"><h3>Featured covers</h3>
      <label className="field"><span>Rotate covers by</span><Select value={settings.homeHeroSort || 'added'} onValueChange={value => onChange({ ...settings, homeHeroSort: value as Settings['homeHeroSort'] })}><SelectTrigger aria-label="Featured cover order"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="added">Recently added</SelectItem><SelectItem value="released">Newest release</SelectItem><SelectItem value="az">Title A–Z</SelectItem><SelectItem value="random">Shuffle</SelectItem></SelectContent></Select></label>
      <p className="muted small">Choose media types for the featured rotation. Order sets the first category; cover order sorts titles within each type. Photos use one picture chosen on refresh. Turn all types off to hide the cover.</p>
      {heroOrder.map((id, index) => { const key = featuredMediaKeys[id]; return <div className="home-setting-item" key={id}><span><strong>{featuredMediaLabels[id]}</strong></span><div className="home-setting-actions"><Switch checked={settings[key]} aria-label={`Feature ${featuredMediaLabels[id]} on Home`} onCheckedChange={checked => onChange({ ...settings, [key]: checked })} />{controls(featuredMediaLabels[id], index, heroOrder.length, direction => onChange({ ...settings, homeHeroOrder: move(heroOrder, id, direction) }))}</div></div>; })}
    </div>
    <div className="home-settings-group"><h3>Library rows</h3>
      {homeRowOptions.map(({ id, label, description }) => { const index = rows.indexOf(id); return <div className="home-setting-item" key={id}><span><strong>{label}</strong><small>{description}</small></span><div className="home-setting-actions"><Switch checked={index >= 0} aria-label={`Show ${label} on Home`} onCheckedChange={checked => onChange({ ...settings, homeRows: checked ? [...rows, id] : rows.filter(row => row !== id) })} />{index >= 0 && controls(label, index, rows.length, direction => onChange({ ...settings, homeRows: move(rows as HomeRow[], id, direction) }))}</div></div>; })}
    </div>
    <button className="primary-button" disabled={busy} onClick={onSave}>Save Home layout <Check size={17} /></button>
  </section>;
}
