'use client';

import { ArrowDown, ArrowUp, Check } from 'lucide-react';
import { Switch } from '@/components/ui/switch';
import { navigationLabels } from '@/lib/navigation';
import { normalizeSidebarOrder, type SidebarDestination } from '@/lib/sidebar-preferences';
import type { Settings } from '@/lib/media';

const labels = navigationLabels;
const fixedLibrary = ['library', 'collections', 'physical'];
type Shortcut = Settings['sidebarShortcuts'][number];

export function SidebarCustomization({ settings, busy, onChange, onSave }: {
  settings: Settings;
  busy: boolean;
  onChange: (settings: Settings) => void;
  onSave: () => void;
}) {
  const selected = settings.sidebarShortcuts || [];
  const order = normalizeSidebarOrder(settings.sidebarOrder);
  const visible = order.filter(id => fixedLibrary.includes(id) || selected.includes(id as Shortcut));
  const move = (id: SidebarDestination, direction: -1 | 1) => {
    const index = visible.indexOf(id), other = visible[index + direction];
    if (!other) return;
    const next = [...order], left = next.indexOf(id), right = next.indexOf(other);
    [next[left], next[right]] = [next[right], next[left]];
    onChange({ ...settings, sidebarOrder: next });
  };
  return <section className="panel sidebar-customization-panel">
    <h2>Sidebar layout</h2>
    <p className="muted small">Order your library links and choose media and planning shortcuts. Home stays first; Settings, Import, Storage & Backup, and Services stay in the tools section.</p>
    <div className="home-settings-group sidebar-order-list"><h3>Library links</h3>{visible.map((id, index) => <div className="home-setting-item" key={id}>
      <span><strong>{labels[id]}</strong></span>
      <div className="home-setting-actions">{!fixedLibrary.includes(id) && <Switch checked aria-label={`Show ${labels[id]} in sidebar`} onCheckedChange={() => onChange({ ...settings, sidebarShortcuts: selected.filter(value => value !== id) })} />}
      <span className="home-order-controls"><button type="button" aria-label={`Move ${labels[id]} up in sidebar`} disabled={busy || index === 0} onClick={() => move(id, -1)}><ArrowUp size={15}/></button><button type="button" aria-label={`Move ${labels[id]} down in sidebar`} disabled={busy || index === visible.length - 1} onClick={() => move(id, 1)}><ArrowDown size={15}/></button></span></div>
    </div>)}</div>
    {order.some(id => !visible.includes(id)) && <div className="home-settings-group"><h3>More shortcuts</h3>{order.filter(id => !visible.includes(id)).map(id => <div className="setting-row" key={id}><span><strong>{labels[id]}</strong></span><Switch checked={false} aria-label={`Show ${labels[id]} in sidebar`} onCheckedChange={() => onChange({ ...settings, sidebarShortcuts: [...selected, id as Shortcut] })}/></div>)}</div>}
    <button className="primary-button" disabled={busy} onClick={onSave}>Save sidebar layout<Check size={17}/></button>
  </section>;
}
