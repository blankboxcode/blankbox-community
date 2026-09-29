'use client';

import { Loader2, RefreshCw, ShieldCheck } from 'lucide-react';
import { BrandLogo } from '@/components/brand-logo';

export function StartupScreen({ error, onRetry }: { error?: string; onRetry: () => void }) {
  return <main className="auth-screen startup-screen">
    <div className="auth-glow" aria-hidden="true"/>
    <div className="startup-lockup">
      <BrandLogo className="auth-brand"/>
      <span className="startup-mark">{error ? <ShieldCheck size={27}/> : <Loader2 className="animate-spin" size={27}/>}</span>
      {error && <h1>Blank Box needs a moment.</h1>}
      <p>{error || 'Connecting to your private library and checking its collection.'}</p>
      {error && <button className="subtle-button" onClick={onRetry}><RefreshCw size={16}/>Try again</button>}
    </div>
    <small className="auth-local-note"><ShieldCheck size={13}/>Private to this Blank Box</small>
  </main>;
}
