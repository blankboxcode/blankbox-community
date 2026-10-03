'use client';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { blankBoxClient } from '@/lib/blank-box-client';

export function OIDCAccountSettings() {
  const[status,setStatus]=useState<{enabled:boolean;name:string;linked:boolean}|null>(null);const[password,setPassword]=useState('');const[busy,setBusy]=useState(false);
  useEffect(()=>{void blankBoxClient.oidcStatus().then(setStatus).catch(()=>setStatus(null));},[]);
  const link=async()=>{setBusy(true);try{window.location.assign(await blankBoxClient.startOIDC('link',password));}catch(error){toast.error((error as Error).message);setBusy(false);}finally{setPassword('');}};
  const unlink=async()=>{setBusy(true);try{await blankBoxClient.unlinkOIDC(password);setStatus(current=>current?{...current,linked:false}:null);toast.success('Identity provider unlinked. Local sign-in remains available.');}catch(error){toast.error((error as Error).message);}finally{setPassword('');setBusy(false);}};
  return <section className="panel"><h2>Account sign-in and recovery</h2><p>Your local username, password and recovery key work independently of an identity provider. Password recovery signs out remembered devices and disconnects any linked OIDC identity.</p>{status?.enabled?<><p>{status.name}: {status.linked?'Linked to your account':'Not linked'}</p><label className="field"><span>Confirm local password</span><input type="password" autoComplete="current-password" value={password} onChange={event=>setPassword(event.target.value)}/></label><button className="subtle-button" type="button" disabled={busy||!password} onClick={()=>void (status.linked?unlink():link())}>{status.linked?'Unlink identity provider':'Link identity provider'}</button></>:<p className="muted">OIDC is optional. Configure an issuer, client ID and callback address on the server to enable it. See the Accounts guide.</p>}<p className="muted small">Keep a private copy of access-key.txt from your data folder. Use “Forgot password? Use recovery key” on the sign-in screen to reset your password.</p></section>;
}
