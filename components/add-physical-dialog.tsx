'use client';

import { CollectorEditionFields } from '@/components/collector-edition-fields';
import { useState, type ReactNode } from 'react';
import { Check, Plus, Settings2, X } from 'lucide-react';
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectSeparator, SelectTrigger, SelectValue } from '@/components/ui/select';
import { PhysicalFormatPicker } from '@/components/physical-format-picker';
import { GamePlatformPicker } from '@/components/physical-organization-settings';
import { kindNames } from '@/lib/media';
import {
  physicalDetailFields,
  physicalDraftForFormat,
  physicalDraftForMediaKind,
  physicalPreferenceKinds,
  physicalFormats,
  physicalKindOptions,
  physicalFormatLabel,
  type PhysicalDraft,
  type PhysicalFormat,
  type PhysicalFormatDefaults,
} from '@/lib/physical-media';

type Props = {
  open: boolean;
  busy: boolean;
  draft: PhysicalDraft;
  formats: PhysicalFormat[];
  locations: string[];
  gamePlatforms: string[];
  defaults: PhysicalFormatDefaults;
  children: ReactNode;
  onOpenChange: (open: boolean) => void;
  onChange: (draft: PhysicalDraft) => void;
  onSaveLocation: (location: string) => Promise<boolean>;
  onSaveFormats: (formats: PhysicalFormat[]) => Promise<boolean>;
  onSavePlatforms: (platforms: string[]) => Promise<boolean>;
  onSaveDefault: (kind: PhysicalDraft['kind'], format: PhysicalFormat) => Promise<boolean>;
  onContinue: () => void;
};

const updateField = (draft: PhysicalDraft, field: keyof PhysicalDraft, value: string): PhysicalDraft => ({
  ...draft,
  [field]: value,
});

export function AddPhysicalDialog({ open, busy, draft, formats, locations, gamePlatforms, defaults, children, onOpenChange, onChange, onSaveLocation, onSaveFormats, onSavePlatforms, onSaveDefault, onContinue }: Props) {
  const [editingFormats, setEditingFormats] = useState(false);
  const [formatDraft, setFormatDraft] = useState<PhysicalFormat[]>(formats);
  const [editingPlatforms, setEditingPlatforms] = useState(false);
  const [platformDraft, setPlatformDraft] = useState<string[]>(gamePlatforms);
  const kindOptions = [...new Set([...physicalPreferenceKinds, ...physicalKindOptions(draft.format)])].filter(kind => formats.some(format => physicalKindOptions(format).includes(kind)));
  const formatKinds = physicalKindOptions(draft.format);
  const displayKind = formatKinds.includes(draft.kind) ? draft.kind : formatKinds[0];
  const details = physicalDetailFields({ ...draft, kind: displayKind });
  const needsPlatform = draft.format === 'Game' || draft.kind === 'game';
  const savedLocation = !!draft.location.trim() && locations.some((location) => location.toLocaleLowerCase() === draft.location.trim().toLocaleLowerCase());
  const customPlatformSelected = draft.platform === '__custom__' || !!draft.platform && !gamePlatforms.includes(draft.platform);
  const platformField = <label className="field">
    <span>Console or platform <small>required</small></span>
    <Select value={customPlatformSelected ? '__custom__' : draft.platform} onValueChange={(value) => { if (value === '__quick_edit_platforms__') { setPlatformDraft(gamePlatforms); setEditingPlatforms(true); return; } onChange(updateField(draft, 'platform', value)); }}>
      <SelectTrigger aria-label="Console or platform"><SelectValue placeholder="Choose a platform" /></SelectTrigger>
      <SelectContent>{gamePlatforms.map((platform) => <SelectItem key={platform} value={platform}>{platform}</SelectItem>)}<SelectSeparator/><SelectItem value="__custom__">Custom platform…</SelectItem><SelectItem value="__quick_edit_platforms__"><Settings2 size={14}/>Quick edit viewable platforms</SelectItem></SelectContent>
    </Select>
    {customPlatformSelected && <input required maxLength={120} value={draft.platform === '__custom__' ? '' : draft.platform} onChange={(event) => onChange(updateField(draft, 'platform', event.target.value || '__custom__'))} placeholder="Enter a console or device" aria-label="Custom platform name" />}
  </label>;

  const changeFormat = (value: string) => {
    if (value === '__quick_edit__') {
      setFormatDraft(formats);
      setEditingFormats(true);
      return;
    }
    const format = value as PhysicalFormat;
    onChange(physicalDraftForFormat(draft, format));
  };

  const saveFormats = async () => {
    if (!formatDraft.length || !await onSaveFormats(formatDraft)) return;
    if (!formatDraft.includes(draft.format)) onChange(physicalDraftForFormat(draft, formatDraft[0]));
    setEditingFormats(false);
  };
  const savePlatforms = async () => {
    if (!await onSavePlatforms(platformDraft)) return;
    if (draft.platform && draft.platform !== '__custom__' && !platformDraft.includes(draft.platform)) onChange(updateField(draft, 'platform', ''));
    setEditingPlatforms(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="form-dialog physical-dialog physical-intake-unified" showCloseButton={false}>
        <DialogHeader className="intake-dialog-header">
          <DialogTitle>Add a physical item</DialogTitle>
          <DialogDescription>Enter your copy’s details, find a title if you want, then add it here. Nothing is saved until you confirm.</DialogDescription>
          <DialogClose className="intake-dialog-close" disabled={busy} aria-label="Close Add Physical Item"><X size={20}/></DialogClose>
        </DialogHeader>
        <div className="physical-intake-layout"><form id="physical-item-details" onSubmit={(event) => { event.preventDefault(); if (!busy) onContinue(); }}>
          <fieldset disabled={busy} className="physical-intake-form">
          <label className="field">
            <span>Title</span>
            <input aria-label="Physical item title" required maxLength={250} value={draft.title} onChange={(event) => onChange(updateField(draft, 'title', event.target.value))} placeholder="What are you adding?" />
          </label>
          <div className="form-grid">
            <label className="field">
              <span>Format</span>
              <Select value={draft.format} onValueChange={changeFormat}>
                <SelectTrigger aria-label="Format"><SelectValue /></SelectTrigger>
                <SelectContent>{(formats.length ? formats : physicalFormats).map((format) => <SelectItem key={format} value={format}>{physicalFormatLabel(format)}</SelectItem>)}<SelectSeparator/><SelectItem value="__quick_edit__"><Settings2 size={14}/>Quick edit viewable formats</SelectItem></SelectContent>
              </Select>
            </label>
            {kindOptions.length > 1 ? <label className="field">
              <span>Media type</span>
              <Select key={draft.format} value={displayKind} onValueChange={(value) => onChange(physicalDraftForMediaKind(draft, value as PhysicalDraft['kind'], formats, defaults))}>
                <SelectTrigger aria-label="Media type"><SelectValue /></SelectTrigger>
                <SelectContent>{kindOptions.map((kind) => <SelectItem key={kind} value={kind}>{kindNames[kind]}</SelectItem>)}</SelectContent>
              </Select>
            </label> : <div className="field">
              <span>Media type</span>
              <div className="physical-fixed-kind">{kindNames[displayKind]}</div>
            </div>}
          </div>
          <button type="button" className="text-button physical-default-save" disabled={busy || defaults[displayKind] === draft.format} onClick={() => void onSaveDefault(displayKind, draft.format)}>{defaults[displayKind] === draft.format ? `Default format for ${kindNames[displayKind]}` : `Save ${physicalFormatLabel(draft.format)} as my ${kindNames[displayKind]} default`}</button>
          <label className="field physical-location-field">
            <span>Physical location <small>optional</small></span>
            <input list="blank-box-intake-location-options" maxLength={250} value={draft.location} onChange={(event) => onChange(updateField(draft, 'location', event.target.value))} placeholder="Living room, shelf 2" />
            {!!draft.location.trim() && <button type="button" className="physical-save-value" disabled={busy || savedLocation} onClick={() => void onSaveLocation(draft.location.trim())}>{savedLocation?<><Check size={14}/>Saved location</>:<><Plus size={14}/>Save this location</>}</button>}
          </label>
          {needsPlatform && platformField}
          {editingFormats && <section className="physical-quick-formats">
            <div><strong>Formats shown in this menu</strong><small>Choose what your household uses. You can still manage the full list in Settings.</small></div>
            <PhysicalFormatPicker compact value={formatDraft} onChange={setFormatDraft}/>
            <div className="physical-inline-actions"><button type="button" className="text-button" onClick={() => setEditingFormats(false)}>Cancel</button><button type="button" className="subtle-button" disabled={busy || !formatDraft.length} onClick={() => void saveFormats()}><Check size={15}/>Save formats</button></div>
          </section>}
          {editingPlatforms && <section className="physical-quick-formats physical-quick-platforms">
            <div><strong>Platforms shown in this menu</strong><small>Choose the consoles and devices your household uses. Existing game records stay in your collection.</small></div>
            <GamePlatformPicker value={platformDraft} onChange={setPlatformDraft}/>
            <div className="physical-inline-actions"><button type="button" className="text-button" onClick={() => setEditingPlatforms(false)}>Cancel</button><button type="button" className="subtle-button" disabled={busy} onClick={() => void savePlatforms()}><Check size={15}/>Save platforms</button></div>
          </section>}
          <div className="form-grid">
            <label className="field">
              <span>Year <small>optional</small></span>
              <input type="number" min="1800" max="2200" value={draft.year} onChange={(event) => onChange(updateField(draft, 'year', event.target.value))} placeholder="1999" />
            </label>
            <label className="field">
              <span>Edition <small>optional</small></span>
              <input maxLength={120} value={draft.edition} onChange={(event) => onChange(updateField(draft, 'edition', event.target.value))} placeholder="Collector’s edition" />
            </label>
          </div>
          <CollectorEditionFields packaging={draft.packaging} releaseLabel={draft.releaseLabel} onChange={(key,value)=>onChange(updateField(draft,key,value))}/>
          {displayKind === 'tv' && <label className="field"><span>TV season <small>optional</small></span><select value={draft.season} onChange={(event) => onChange(updateField(draft, 'season', event.target.value))}><option value="">Unknown season</option><option value="complete-series">Complete series</option><option value="specials">Specials</option>{Array.from({length: 99}, (_, index) => <option key={index + 1} value={String(index + 1)}>Season {index + 1}</option>)}</select></label>}
            <label className="field">
              <span>Barcode <small>optional</small></span>
              <input maxLength={80} inputMode="numeric" value={draft.barcode} onChange={(event) => onChange(updateField(draft, 'barcode', event.target.value))} placeholder="UPC or ISBN" />
            </label>
          <details className="physical-optional-details"><summary>More copy details</summary><div className="physical-intake-fields">
          <div className="form-grid">
            <label className="field">
              <span>Condition <small>optional</small></span>
              <input maxLength={120} value={draft.condition} onChange={(event) => onChange(updateField(draft, 'condition', event.target.value))} placeholder="Like new" />
            </label>
          </div>
          {(details.creatorLabel || details.publisherLabel) && <div className="form-grid physical-specific-fields" key={`${draft.format}-${draft.kind}-credits`}>
            <label className="field">
              <span>{details.creatorLabel} <small>optional</small></span>
              <input maxLength={250} value={draft.creator} onChange={(event) => onChange(updateField(draft, 'creator', event.target.value))} />
            </label>
            <label className="field">
              <span>{details.publisherLabel} <small>optional</small></span>
              <input maxLength={250} value={draft.publisher} onChange={(event) => onChange(updateField(draft, 'publisher', event.target.value))} />
            </label>
          </div>}
          {(details.volume || details.issue) && <div className="form-grid physical-specific-fields" key={`${draft.format}-${draft.kind}-print`}>
            {details.volume && <label className="field"><span>Volume <small>optional</small></span><input maxLength={80} value={draft.volume} onChange={(event) => onChange(updateField(draft, 'volume', event.target.value))} /></label>}
            {details.issue && <label className="field"><span>Issue <small>optional</small></span><input maxLength={80} value={draft.issue} onChange={(event) => onChange(updateField(draft, 'issue', event.target.value))} /></label>}
          </div>}
          <div className="form-grid">
            <label className="field"><span>Region <small>optional</small></span><input maxLength={80} value={draft.region} onChange={(event) => onChange(updateField(draft, 'region', event.target.value))} placeholder="Region A, NTSC, PAL" /></label>
            <label className="field"><span>Catalog number <small>optional</small></span><input maxLength={120} value={draft.catalogNumber} onChange={(event) => onChange(updateField(draft, 'catalogNumber', event.target.value))} /></label>
          </div>
          <label className="field"><span>Genre <small>optional</small></span><input maxLength={500} value={draft.genre} onChange={(event) => onChange(updateField(draft, 'genre', event.target.value))}/></label>
          <label className="field"><span>Description <small>optional</small></span><textarea rows={4} maxLength={5000} value={draft.description} onChange={(event) => onChange(updateField(draft, 'description', event.target.value))}/></label>
          </div></details>
          <p className="muted small">Set starting formats and title search in Settings → Collection → Physical Media preferences.</p>
          <datalist id="blank-box-intake-location-options">{locations.map((location) => <option key={location} value={location}/>)}</datalist>
          </fieldset>
        </form><section className="physical-intake-matches" aria-label="Title matching and confirmation">{children}</section></div>
      </DialogContent>
    </Dialog>
  );
}
