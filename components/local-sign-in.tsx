'use client';

import { useEffect, useState } from 'react';
import { ChevronRight, KeyRound, LockKeyhole, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';
import { BrandLogo } from '@/components/brand-logo';
import { blankBoxClient, type AuthStatus } from '@/lib/blank-box-client';

type Props = {
  open: boolean;
  busy: boolean;
  onBusyChange: (busy: boolean) => void;
  onAuthenticated: () => Promise<void>;
};

export function LocalSignIn({ open, busy, onBusyChange, onAuthenticated }: Props) {
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [recovery, setRecovery] = useState(false);
  const [accessKey, setAccessKey] = useState('');
  const [username, setUsername] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [remember, setRemember] = useState(true);

  useEffect(() => {
    if (!open) return;
    void blankBoxClient.authStatus().then(setStatus).catch((error) => toast.error((error as Error).message));
  }, [open]);

  const submit = async () => {
    onBusyChange(true);
    try {
      if ((recovery || !status?.hasProfile) && password !== confirmPassword) throw new Error('The passwords do not match.');
      if (!status?.hasProfile) {
        await blankBoxClient.claimProfile(accessKey, username, displayName, password, remember);
      } else if (recovery) {
        await blankBoxClient.recoverProfile(accessKey, username, password, remember);
      } else {
        await blankBoxClient.loginWithPassword(username, password, remember);
      }
      setAccessKey('');
      setPassword('');
      setConfirmPassword('');
      await onAuthenticated();
    } catch (error) {
      toast.error((error as Error).message);
    } finally {
      onBusyChange(false);
    }
  };

  const creating = status && !status.hasProfile;
  if (!open) return null;
  return <main className="auth-screen">
      <div className="auth-glow" aria-hidden="true"/>
      <section className="auth-stage">
        <BrandLogo className="auth-brand" />
        <span className={`auth-profile-mark ${creating ? 'first-owner' : ''}`}>{creating ? <KeyRound size={29}/> : <LockKeyhole size={29}/>}</span>
        <div className="auth-copy">
          <span className="eyebrow">{creating ? 'FIRST BOOT' : recovery ? 'OWNER RECOVERY' : 'YOUR BLANK BOX'}</span>
          <h1>{creating ? 'Make this Blank Box yours.' : recovery ? 'Reset the owner password.' : 'Welcome home.'}</h1>
          <p>{creating ? 'Create the first owner profile for this private library. The recovery key is only needed for this claim and future password recovery.' : recovery ? 'Use the admin recovery key to set a new password. Existing signed-in devices will be signed out.' : 'Open your private library with the owner profile for this device.'}</p>
        </div>
        {!status ? <div className="auth-checking"><span className="auth-pulse"/><p>Checking this Blank Box…</p></div> : <form className="auth-form" onSubmit={(event) => { event.preventDefault(); void submit(); }}>
          {creating && <label className="field"><span>Display name</span><input required maxLength={60} autoComplete="name" value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label>}
          <label className="field"><span>{recovery ? 'Owner username' : 'Username'}</span><input required minLength={3} maxLength={32} autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} /></label>
          {(creating || recovery) && <label className="field"><span>Admin recovery key</span><input required type="password" autoComplete="off" value={accessKey} onChange={(event) => setAccessKey(event.target.value)} /></label>}
          <label className="field"><span>{recovery ? 'New password' : 'Password'}</span><input required type="password" minLength={10} maxLength={256} autoComplete={creating || recovery ? 'new-password' : 'current-password'} value={password} onChange={(event) => setPassword(event.target.value)} /></label>
          {(creating || recovery) && <label className="field"><span>Confirm password</span><input required type="password" minLength={10} maxLength={256} autoComplete="new-password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} /></label>}
          <label className="remember-sign-in"><input type="checkbox" checked={remember} onChange={(event) => setRemember(event.target.checked)}/><span><strong>Keep me signed in on this device</strong><small>Remember this browser for up to 90 days.</small></span></label>
          <button className="primary-button auth-primary" disabled={busy || (creating || recovery) && password !== confirmPassword}>{creating ? 'Create owner profile' : recovery ? 'Reset password' : 'Open my library'}<ChevronRight size={17} /></button>
          {!creating && <button className="text-button" type="button" onClick={() => { setRecovery((value) => !value); setPassword(''); setConfirmPassword(''); }}>{recovery ? 'Use my password instead' : 'Forgot password? Use recovery key'}</button>}
        </form>}
        <small className="auth-local-note"><ShieldCheck size={13}/>Credentials and sessions stay on this Blank Box</small>
      </section>
    </main>;
}
