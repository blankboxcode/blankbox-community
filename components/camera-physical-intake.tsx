'use client';
/* eslint-disable @next/next/no-img-element -- Cover previews use private browser and local artwork URLs. */

import { useEffect, useRef, useState } from 'react';
import { Camera, CheckCircle2, ScanLine, Trash2, X } from 'lucide-react';
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { blankBoxClient, type MetadataCandidate } from '@/lib/blank-box-client';
import { barcodeBounds, barcodeEquivalent, cleanBarcode, validBarcode, type BarcodeBounds } from '@/lib/barcodes';
import type { MediaItem } from '@/lib/media';

type Scan = { id: string; code: string; image?: string; file?: File; title: string };
type Capture = { code: string; frame?: string; file?: File; bounds?: BarcodeBounds; format?: string };
export type CameraEntry = { scanId:string; code: string; title: string; match?: MediaItem; candidate?: MetadataCandidate; artwork?: File };
const timeNow = () => Date.now();
const observationId = () => `${Date.now()}-${Math.random().toString(36).slice(2)}`;

function ScanReview({ scan, items, localMetadata, onUse, onRemove }: { scan: Scan; items: MediaItem[]; localMetadata: boolean; onUse: (entry: CameraEntry) => void; onRemove: () => void }) {
  const [candidates, setCandidates] = useState<MetadataCandidate[]>([]);
  const [householdIds, setHouseholdIds] = useState<string[]>([]);
  const [chosen, setChosen] = useState('');
  const [title, setTitle] = useState(scan.title);
  const [loading, setLoading] = useState(localMetadata && !!scan.code);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  const [useArtwork,setUseArtwork]=useState(false);
  const [remoteHousehold,setRemoteHousehold]=useState<MediaItem[]>([]);
  const household = [...new Map([...remoteHousehold,...items].map(item=>[item.id,item])).values()].filter(item => householdIds.includes(item.id) || scan.code && item.sources.some(source => source.type === 'physical' && source.barcode && barcodeEquivalent(source.barcode, scan.code)));
  const selectedHousehold = household.find(item => chosen === `item:${item.id}`);
  const visibleCandidates = candidates.filter(value => !(household.length && ['household-copy', 'legacy-household'].includes(value.origin)));
  const candidate = visibleCandidates.find(value => value.id === chosen);
  const resultTitle = title.trim() || selectedHousehold?.title || candidate?.title || '';
  useEffect(() => {
    if (!localMetadata || !scan.code) return;
    let active = true;
    blankBoxClient.action('barcode-lookup', { barcode: scan.code }).then(async raw => {
      if (!active) return;
      const result = raw as unknown as { householdItemIds: string[]; candidates: MetadataCandidate[]; warnings: string[] };
      setHouseholdIds(result.householdItemIds);const records=await blankBoxClient.selection(result.householdItemIds.slice(0,30));if(!active)return;setRemoteHousehold(records); setCandidates(result.candidates); setError(result.warnings.join(' '));
    }).catch(cause => { if (active) setError((cause as Error).message); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [scan.code, localMetadata, revision]);
  return <div className="camera-scan-row">{scan.image && <img src={scan.image} alt="Captured cover for review"/>}<div><strong>{scan.code || 'Cover photo'}</strong><small>{loading ? 'Checking household and downloaded Blank Box packs…' : household.length || visibleCandidates.length ? `${household.length} household ${household.length === 1 ? 'title' : 'titles'} · ${visibleCandidates.length} metadata matches. Choose a match or enter your own title.` : 'No exact barcode match in your library or installed packs. Enter the title; nothing has been added.'}</small>
    {!!(household.length || visibleCandidates.length) && <label className="field"><span>Choose a barcode match</span><select value={chosen} onChange={event => { setChosen(event.target.value); setTitle(''); }}><option value="">Enter my own details</option>{household.map(item => <option key={item.id} value={`item:${item.id}`}>My Library: {item.title}{item.year ? ` (${item.year})` : ''}</option>)}{visibleCandidates.map(value => <option key={value.id} value={value.id}>{value.origin.startsWith('pack:') ? 'Downloaded pack' : 'Saved reference'}: {value.title} · {value.level}{value.year ? ` (${value.year})` : ''}{value.format ? ` · ${value.format}` : ''}{value.edition ? ` · ${value.edition}` : ''}</option>)}</select></label>}
    <input aria-label={`Title for ${scan.code || 'cover'}`} maxLength={250} value={title} onChange={event => { setTitle(event.target.value); setChosen(''); }} placeholder={candidate?.title || selectedHousehold?.title || 'Enter title to continue'}/>
    {candidate && <small>{candidate.level === 'release' ? 'Identifier-backed release candidate. Check format and edition in the next step.' : 'Work match; it does not identify the exact edition.'}</small>}
    {scan.file&&<label className="camera-cover-use"><input type="checkbox" checked={useArtwork} onChange={event=>setUseArtwork(event.target.checked)}/>Use this photo as the Blank Box cover after the physical item is saved</label>}
    {error && <p className="error-text" role="alert">{error} <button className="text-button" type="button" onClick={() => { setLoading(true); setError(''); setRevision(value => value + 1); }}>Retry lookup</button></p>}
  </div><div className="camera-scan-row-actions"><button className="subtle-button" type="button" onClick={() => onUse({ scanId:scan.id, code: scan.code, title: resultTitle, match: selectedHousehold, candidate, artwork:useArtwork?scan.file:undefined })} disabled={!resultTitle || loading}>Review physical item</button><button className="text-button camera-remove-scan" type="button" onClick={onRemove} aria-label={`Remove ${scan.code || 'cover photo'} from queue`}><Trash2 size={16}/></button></div></div>;
}

export function CameraPhysicalIntake({ open, items, localMetadata = false, completedScanId, onOpenChange, onUse }: { open: boolean; items: MediaItem[]; localMetadata?: boolean; completedScanId?: string; onOpenChange: (open: boolean) => void; onUse: (entry: CameraEntry) => void }) {
  const video = useRef<HTMLVideoElement>(null);
  const [cameraOn, setCameraOn] = useState(false);
  const [cameraError, setCameraError] = useState('');
  const [scans, setScans] = useState<Scan[]>([]);
  const [manualCode, setManualCode] = useState('');
  const [pending, setPending] = useState<Capture | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [batch, setBatch] = useState(false);
  const [message, setMessage] = useState('');
  const [cameraId, setCameraId] = useState('');
  const [devices, setDevices] = useState<{ id: string; label: string }[]>([]);
  const [page, setPage] = useState(0);
  const queuePage = Math.min(page, Math.max(0, Math.ceil(scans.length / 10) - 1));
  const captures = useRef(new Set<string>());
  const imageUrls = useRef(new Set<string>());
  const photoFiles = useRef<File[]>([]);
  const photoProcessing = useRef(false);
  const pendingRef = useRef(false);
  const suppressedUntil = useRef(0);
  const mounted = useRef(true);
  const capacity = useRef(0);
  const scansRef = useRef<Scan[]>([]);
  const batchRef = useRef(false);
  const activeOpen = useRef(open);
  useEffect(() => { activeOpen.current = open; }, [open]);
  useEffect(() => { batchRef.current = batch; }, [batch]);
  useEffect(() => { capacity.current = scans.length; scansRef.current = scans; }, [scans]);
  useEffect(() => { mounted.current = true; const urls = imageUrls.current; return () => { mounted.current = false; urls.forEach(url => URL.revokeObjectURL(url)); }; }, []);
  const start = () => {
    if (!navigator.mediaDevices?.getUserMedia) { setCameraError('Camera scanning needs HTTPS (or localhost) and camera permission. Use the private secure address, choose a photo, or enter the printed code.'); return; }
    setCameraError(''); setMessage(''); setCameraOn(true);
  };
  const capture = (value: Capture) => { if (capacity.current >= 50) { setMessage('Review or remove queued scans before adding more (50 maximum).'); return; } pendingRef.current = true; setPending(value); setConfirmed(false); setCameraOn(false); };
  const releasePendingImage = () => { if (pending?.frame?.startsWith('blob:')) { URL.revokeObjectURL(pending.frame); imageUrls.current.delete(pending.frame); } };
  const retake = () => { releasePendingImage(); setPending(null); pendingRef.current = false; suppressedUntil.current = timeNow() + 1400; start(); };
  const confirmCode = () => {
    if (!pending || !confirmed) return;
    const code = cleanBarcode(pending.code);
    const duplicate=scans.some(scan => barcodeEquivalent(scan.code, code));
    if (duplicate) setMessage(`${code} is already queued. Review it before scanning another copy.`);
    else { setScans(previous => [{ id: observationId(), code, title: '', ...(pending.file?{image:pending.frame,file:pending.file}:{}) }, ...previous]); setPage(0); setMessage(`Barcode ${code} confirmed. Review the physical copy below.`); }
    captures.current.add(code);
    if(!pending.file||duplicate)releasePendingImage();
    setPending(null); pendingRef.current = false; setManualCode('');
    suppressedUntil.current = timeNow() + 1400;
    if(photoFiles.current.length)void coverFiles(null);
    else if (batchRef.current) { setCameraError(''); setCameraOn(true); }
  };

  useEffect(() => {
    if (!open || !cameraOn) return;
    let active = true;
    let stop: (() => void) | undefined;
    if (!video.current || !navigator.mediaDevices?.getUserMedia) return;
    void Promise.all([import('@zxing/browser'), import('@zxing/library')]).then(async ([{ BrowserMultiFormatReader }, { BarcodeFormat, DecodeHintType, ResultMetadataType }]) => {
      if (!active || !video.current) return;
      const node = video.current;
      const hints = new Map();
      hints.set(DecodeHintType.POSSIBLE_FORMATS, [BarcodeFormat.EAN_13, BarcodeFormat.EAN_8, BarcodeFormat.UPC_A, BarcodeFormat.UPC_E, BarcodeFormat.CODE_128, BarcodeFormat.CODE_39, BarcodeFormat.ITF]);
      hints.set(DecodeHintType.TRY_HARDER, true);
      const reader = new BrowserMultiFormatReader(hints, { delayBetweenScanAttempts: 180, delayBetweenScanSuccess: 800 });
      const controls = await reader.decodeFromConstraints({ video: { ...(cameraId ? { deviceId: { exact: cameraId } } : { facingMode: { ideal: 'environment' } }), width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false }, node, result => {
        if (!active || !result || pendingRef.current || timeNow() < suppressedUntil.current) return;
        const extension = result.getResultMetadata()?.get(ResultMetadataType.UPC_EAN_EXTENSION);
        const code = result.getText() + (typeof extension === 'string' ? extension : '');
        if (captures.current.has(code)) return;
        const points = result.getResultPoints().map(point => ({ x: point.getX(), y: point.getY() }));
        const bounds = barcodeBounds(points, node.videoWidth, node.videoHeight);
        const canvas = document.createElement('canvas'); canvas.width = Math.min(node.videoWidth, 720); canvas.height = Math.round(canvas.width * node.videoHeight / node.videoWidth);
        const context = canvas.getContext('2d'); context?.drawImage(node, 0, 0, canvas.width, canvas.height);
        capture({ code, bounds, frame: context ? canvas.toDataURL('image/jpeg', 0.75) : undefined, format: BarcodeFormat[result.getBarcodeFormat()] });
      });
      const track=(node.srcObject as MediaStream|null)?.getVideoTracks()[0];
      const focus=(track?.getCapabilities() as MediaTrackCapabilities & {focusMode?:string[]})?.focusMode;
      if(focus?.includes('continuous'))void track?.applyConstraints({advanced:[{focusMode:'continuous'} as MediaTrackConstraintSet]}).catch(()=>{/* Camera defaults remain usable. */});
      if (!active) controls.stop(); else { stop = () => controls.stop(); setCameraError(''); try { const cameras = await navigator.mediaDevices.enumerateDevices(); if (active) setDevices(cameras.filter(device => device.kind === 'videoinput').map((device, index) => ({ id: device.deviceId, label: device.label || `Camera ${index + 1}` }))); } catch { /* Camera choice is optional. */ } }
    }).catch(cause => { if (active) { setCameraError((cause as Error).name === 'NotAllowedError' ? 'Camera permission was denied. Enable it in your browser, or choose a barcode photo or enter its number.' : 'This camera could not start. Try another camera, take a still photo, or enter the number manually.'); setCameraOn(false); } });
    return () => { active = false; stop?.(); };
  }, [open, cameraOn, cameraId]);

  async function coverFiles(files: FileList | null) {
    if(files)photoFiles.current.push(...Array.from(files).slice(0, Math.max(0, 30 - photoFiles.current.length)));
    if(pendingRef.current || photoProcessing.current)return;
    photoProcessing.current = true;
    setCameraOn(false);
    try {
    while(photoFiles.current.length){
      const file=photoFiles.current.shift()!;
      if (!mounted.current || !activeOpen.current) break;
      if (!file.type.startsWith('image/') || file.size > 12 * 1024 * 1024 || capacity.current >= 50) { setMessage('Use images under 12 MB and review the queue before adding more.'); continue; }
      const image = URL.createObjectURL(file); imageUrls.current.add(image);
      try {
        const [{ BrowserMultiFormatReader }, { ResultMetadataType,BarcodeFormat,DecodeHintType }] = await Promise.all([import('@zxing/browser'), import('@zxing/library')]);
        const hints=new Map();hints.set(DecodeHintType.TRY_HARDER,true);hints.set(DecodeHintType.POSSIBLE_FORMATS,[BarcodeFormat.EAN_13,BarcodeFormat.EAN_8,BarcodeFormat.UPC_A,BarcodeFormat.UPC_E,BarcodeFormat.CODE_128,BarcodeFormat.CODE_39,BarcodeFormat.ITF]);
        const result = await new BrowserMultiFormatReader(hints).decodeFromImageUrl(image);
        if (!mounted.current || !activeOpen.current) { URL.revokeObjectURL(image); imageUrls.current.delete(image); break; }
        const extension = result.getResultMetadata()?.get(ResultMetadataType.UPC_EAN_EXTENSION);
        const code = result.getText() + (typeof extension === 'string' ? extension : '');
        if (code) {
          const bitmap = new Image(); bitmap.src = image; await bitmap.decode();
          capture({ code, frame: image, file, bounds: barcodeBounds(result.getResultPoints().map(point => ({ x: point.getX(), y: point.getY() })), bitmap.naturalWidth, bitmap.naturalHeight) });
          setMessage(photoFiles.current.length?`Confirm this barcode. ${photoFiles.current.length} photos remain for review.`:'Confirm the barcode to continue.'); break;
        }
      } catch { /* A barcode-free cover remains a manual title observation. */ }
      if (mounted.current && activeOpen.current) { capacity.current++; setScans(previous => [{ id: observationId(), code: '', image, file, title: '' }, ...previous]); setPage(0); }
    }
    } finally { photoProcessing.current = false; }
  }
  const removeScan = (scan: Scan) => { captures.current.delete(scan.code); setScans(previous => previous.filter(row => row.id !== scan.id)); if (scan.image) { URL.revokeObjectURL(scan.image); imageUrls.current.delete(scan.image); } };
  // Consume only a successfully committed copy, preserving scans if intake is abandoned.
  useEffect(()=>{if(!completedScanId)return;
    const scan=scansRef.current.find(row=>row.id===completedScanId);
    if(scan){captures.current.delete(scan.code);if(scan.image){URL.revokeObjectURL(scan.image);imageUrls.current.delete(scan.image);}}
    // eslint-disable-next-line react-hooks/set-state-in-effect -- Synchronize committed intake with this browser observation queue.
    setScans(previous=>previous.filter(row=>row.id!==completedScanId));
  },[completedScanId]);
  const close = () => { setCameraOn(false);releasePendingImage();setPending(null);photoFiles.current=[]; pendingRef.current = false; onOpenChange(false); };
  return <>
    <Dialog open={open} onOpenChange={value => value ? onOpenChange(true) : close()}><DialogContent className="form-dialog camera-intake-dialog" showCloseButton={false}><DialogHeader className="intake-dialog-header"><DialogTitle>Scan physical media</DialogTitle><DialogDescription>Confirm the barcode, choose a local match, then review the physical item.</DialogDescription><DialogClose className="intake-dialog-close" onClick={close} aria-label="Close camera intake"><X size={20}/></DialogClose></DialogHeader>
      <div className="camera-intake-body"><div className="camera-intake-actions"><button className="subtle-button" type="button" onClick={() => cameraOn ? setCameraOn(false) : start()}><ScanLine size={16}/>{cameraOn ? 'Stop camera' : 'Scan barcode'}</button><label className="subtle-button camera-cover-button"><Camera size={16}/>Barcode photo or cover<input type="file" accept="image/*" capture="environment" multiple onChange={event => { void coverFiles(event.target.files); event.target.value = ''; }}/></label></div>
        <div className="camera-controls"><label><input type="checkbox" checked={batch} onChange={event => setBatch(event.target.checked)}/>Scan several · resume after each confirmation</label>{devices.length > 1 && <label>Camera <select value={cameraId} onChange={event => setCameraId(event.target.value)}><option value="">Automatic rear camera</option>{devices.map(device => <option key={device.id} value={device.id}>{device.label}</option>)}</select></label>}</div>
        {cameraOn && <div className="barcode-camera-viewport"><video ref={video} autoPlay playsInline muted aria-label="Barcode camera view"/><div className="barcode-aim-guide" aria-hidden="true"/><span>Center the whole barcode · hold steady</span></div>}
        {cameraError && <p className="error-text" role="alert">{cameraError}</p>}{message && <p className="scan-confirmed-message" role="status"><CheckCircle2 size={17}/>{message}</p>}
        <p className="muted small camera-intake-hint">Use even light, avoid glare, and move back until every bar is sharp. The camera stops when a code is detected. Barcode decoding happens on this device.</p>
        <form className="camera-manual-code" onSubmit={event => { event.preventDefault(); capture({ code: manualCode }); }}><label className="field"><span>Or enter the printed UPC, EAN, ISBN, or custom code</span><input value={manualCode} maxLength={80} onChange={event => setManualCode(event.target.value)} inputMode="text" placeholder="Number under the bars"/></label><button className="subtle-button" type="submit" disabled={!manualCode.trim()}>Check code</button></form>
        <div className="camera-scan-queue"><h3>Ready for review <span>{scans.length}</span></h3>{!scans.length && <p className="muted small">Nothing joins your collection until you finish physical item review.</p>}{scans.slice(queuePage * 10, queuePage * 10 + 10).map(scan => <ScanReview key={scan.id} scan={scan} items={items} localMetadata={localMetadata && open} onUse={entry => { setCameraOn(false); onUse(entry); }} onRemove={() => removeScan(scan)}/>)}</div>
        {scans.length > 10 && <div className="collection-paging"><button disabled={!queuePage} onClick={() => setPage(queuePage - 1)}>Previous</button><span>Page {queuePage + 1} of {Math.ceil(scans.length / 10)}</span><button disabled={(queuePage + 1) * 10 >= scans.length} onClick={() => setPage(queuePage + 1)}>Next</button></div>}
        <p className="muted small">Lookup searches saved references and downloaded Blank Box packs, without retailer calls. Pack barcode coverage varies; work-only packs cannot identify exact releases. A cover photo is saved only if you select that option and finish adding the item. Cover recognition is not available.</p>
      </div></DialogContent></Dialog>
    <Dialog open={open && !!pending} onOpenChange={value => { if (!value) { releasePendingImage(); setPending(null); photoFiles.current = []; pendingRef.current = false; } }}><DialogContent className="form-dialog barcode-confirm-dialog"><DialogHeader><DialogTitle><CheckCircle2 size={22}/>Barcode detected</DialogTitle><DialogDescription>Check the highlighted barcode and its printed number before continuing.</DialogDescription></DialogHeader>{pending?.frame && <div className="barcode-captured-frame"><img src={pending.frame} alt="Local camera capture showing the detected barcode"/>{pending.bounds && <span className="barcode-highlight" style={{ left: `${pending.bounds.left}%`, top: `${pending.bounds.top}%`, width: `${pending.bounds.width}%`, height: `${pending.bounds.height}%` }}/>}</div>}<label className="field"><span>Detected code{pending?.format ? ` · ${pending.format.replaceAll('_', ' ')}` : ''}</span><input autoFocus value={pending?.code || ''} maxLength={80} onChange={event => { setPending(current => current ? { ...current, code: event.target.value } : null); setConfirmed(false); }}/></label>{pending && !validBarcode(pending.code) && <p className="muted small">This is not a verified UPC/EAN/ISBN check digit. It may be a custom label or a misread. Verify the printed characters.</p>}<label className="barcode-confirm-check"><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)}/>This matches the code printed on my item.</label><div className="barcode-confirm-actions"><button className="subtle-button" type="button" onClick={retake}>Scan again</button><button className="primary-button" type="button" disabled={!confirmed || !pending?.code.trim() || !/^[A-Z0-9]+$/i.test(cleanBarcode(pending?.code || ''))} onClick={confirmCode}>Confirm barcode</button></div></DialogContent></Dialog>
  </>;
}
