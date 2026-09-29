'use client';

import { useEffect, useState } from 'react';
import { Disc3, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { blankBoxClient, type ApiResult } from '@/lib/blank-box-client';

type Props = {
  value: string;
  busy: boolean;
  onChange: (device: string) => void;
  onSave: () => void;
  onImport: () => void;
};

export function OpticalDriveSettings({ value, busy, onChange, onSave, onImport }: Props) {
  const [status, setStatus] = useState<ApiResult | null>(null);
  const refresh = async () => {
    try { setStatus(await blankBoxClient.action('disc-status')); }
    catch (error) { toast.error((error as Error).message); }
  };
  useEffect(() => {
    let active = true;
    void blankBoxClient.action('disc-status').then(next => { if (active) setStatus(next); })
      .catch(error => { if (active) toast.error((error as Error).message); });
    return () => { active = false; };
  }, []);
  const devices = status?.devices || [];
  const missing = value && !devices.includes(value);
  return <section className="panel optical-drive-settings">
    <div className="section-heading"><h2><Disc3 size={21}/> Optical drive</h2><button className="text-button" onClick={() => void refresh()} aria-label="Refresh optical drives"><RefreshCw size={16}/>Refresh</button></div>
    <p className="muted small">Choose the drive Blank Box should use for audio CDs. Automatic uses the first connected drive. You can change drives for a single import.</p>
    <label className="field"><span>Preferred drive</span><select value={value} onChange={event => onChange(event.target.value)}><option value="">Automatic</option>{missing && <option value={value}>{value} (disconnected)</option>}{devices.map(device => <option key={device} value={device}>{status?.driveDetails?.find(detail => detail.device === device)?.label || device}</option>)}</select></label>
    {status && <p className="muted small">{devices.length ? `${devices.length} optical ${devices.length === 1 ? 'drive' : 'drives'} detected.` : status.message} {status.platform === 'linux' && status.tools?.cdparanoia && status.tools?.flac ? 'Lossless FLAC import is available on this host.' : 'Blank Box imports lossless WAV without extra CD software.'}</p>}
    <div className="settings-actions"><button className="primary-button" disabled={busy} onClick={onSave}>Save drive</button><button className="text-button" onClick={onImport}>Open Disc Import</button></div>
  </section>;
}
