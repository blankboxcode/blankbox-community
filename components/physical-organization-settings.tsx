'use client';

import { useMemo, useState } from 'react';
import { ArrowRight, Check, Plus, X } from 'lucide-react';
import { PhysicalFormatPicker } from '@/components/physical-format-picker';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { commonGamePlatforms, kindNames, type MediaItem, type Settings } from '@/lib/media';
import { physicalFormatLabel, physicalFormats, physicalKindOptions, physicalPreferenceKinds, type PhysicalFormat, type PhysicalSearchSource } from '@/lib/physical-media';

const standardPlatforms = new Set<string>(commonGamePlatforms);
const platformGroups = [
  { title: 'PlayStation', values: commonGamePlatforms.slice(0, 7) },
  { title: 'Xbox', values: commonGamePlatforms.slice(7, 11) },
  { title: 'Nintendo', values: commonGamePlatforms.slice(11, 24) },
  { title: 'Sega', values: commonGamePlatforms.slice(24, 28) },
  { title: 'Other', values: commonGamePlatforms.slice(28) },
];

type Props = {
  settings: Settings;
  items: MediaItem[]; locationsSummary?: {location:string;copies:number}[];
  busy: boolean;
  onChange: (settings: Settings) => void;
  onSave: () => void;
  onMove: (fromLocation: string, toLocation: string) => Promise<void>;
};

function unique(values: string[]) {
  return [...new Map(values.map((value) => value.trim()).filter(Boolean).map((value) => [value.toLocaleLowerCase(), value])).values()].sort((left, right) => left.localeCompare(right));
}

function platformChoices(selected: string[], custom: string[]) {
  const names = [...selected, ...custom.map((value) => commonGamePlatforms.find((standard) => standard.toLocaleLowerCase() === value.toLocaleLowerCase()) || value)];
  return [...new Map(names.map((value) => [value.toLocaleLowerCase(), value])).values()];
}

export function GamePlatformPicker({ value, onChange }: { value: string[]; onChange: (platforms: string[]) => void }) {
  return <div className="physical-format-picker game-platform-picker">{platformGroups.map((group) => <section key={group.title}><strong>{group.title}</strong><div>{group.values.map((platform) => {
    const selected = value.includes(platform);
    return <button type="button" key={platform} className={selected ? 'selected' : ''} aria-pressed={selected} onClick={() => onChange(selected ? value.filter((item) => item !== platform) : [...value, platform])}><span>{selected && <Check size={13}/>}</span>{platform}</button>;
  })}</div></section>)}</div>;
}

function SavedValues({ title, description, values, placeholder, onChange }:{ title:string; description:string; values:string[]; placeholder:string; onChange:(values:string[])=>void }) {
  const [draft, setDraft] = useState('');
  const add = () => {
    const value = draft.trim();
    if (!value || values.some((item) => item.toLocaleLowerCase() === value.toLocaleLowerCase())) return;
    onChange([...values, value]);
    setDraft('');
  };
  return <div className="saved-values">
    <div><strong>{title}</strong><small>{description}</small></div>
    {!!values.length && <div className="saved-value-list">{values.map((value) => <span key={value}>{value}<button type="button" aria-label={`Remove ${value}`} onClick={() => onChange(values.filter((item) => item !== value))}><X size={13}/></button></span>)}</div>}
    <div className="saved-value-add"><input maxLength={120} value={draft} placeholder={placeholder} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); add(); } }}/><button type="button" className="subtle-button" disabled={!draft.trim()} onClick={add}><Plus size={15}/>Save</button></div>
  </div>;
}

export function PhysicalOrganizationSettings({ settings, items, locationsSummary, busy, onChange, onSave, onMove }: Props) {
  const catalogLocations = useMemo(() => unique(items.flatMap((item) => item.sources.filter((source) => source.type === 'physical').map((source) => source.location || ''))), [items]);
  const locations = unique([...settings.physicalLocations, ...(locationsSummary?.map(row=>row.location).filter(value=>value!=='Location not set')||[]), ...catalogLocations]);
  const selectedStandardPlatforms = settings.gamePlatforms.filter((platform) => standardPlatforms.has(platform));
  const customPlatforms = settings.gamePlatforms.filter((platform) => !standardPlatforms.has(platform));
  const [fromLocation, setFromLocation] = useState('');
  const [toLocation, setToLocation] = useState('');
  const matchingCopies = locationsSummary?.find(row=>row.location.toLocaleLowerCase()===fromLocation.toLocaleLowerCase())?.copies ?? items.reduce((count, item) => count + item.sources.filter((source) => source.type === 'physical' && source.location?.toLocaleLowerCase() === fromLocation.toLocaleLowerCase()).length, 0);

  const move = async () => {
    await onMove(fromLocation, toLocation.trim());
    setFromLocation('');
    setToLocation('');
  };

  return <section className="panel physical-preferences-panel" id="physical-media-settings">
    <h2>Physical Media preferences</h2>
    <p className="muted">Keep physical intake focused on the formats and organizers your household actually uses.</p>
    <div className="settings-divider"/>
    <h3>Formats shown when adding media</h3>
    <PhysicalFormatPicker value={settings.physicalFormats} onChange={(physicalFormats) => onChange({ ...settings, physicalFormats })}/>
    <h3>Defaults for new physical items</h3>
    <p className="muted small">Choose the starting format for each media type. You can change it for any copy. A hidden default falls back to a visible compatible format; existing items stay unchanged.</p>
    <div className="form-grid physical-default-formats">{physicalPreferenceKinds.map(kind => {
      const formats = physicalFormats.filter(format => settings.physicalFormats.includes(format) && physicalKindOptions(format).includes(kind));
      const selected = settings.physicalDefaultFormats?.[kind];
      return <label className="field" key={kind}><span>{kindNames[kind]}</span><select aria-label={`Default format for ${kindNames[kind]}`} disabled={busy || !formats.length} value={selected && formats.includes(selected) ? selected : ''} onChange={event => {
        const physicalDefaultFormats = { ...settings.physicalDefaultFormats };
        if (event.target.value) physicalDefaultFormats[kind] = event.target.value as PhysicalFormat;
        else delete physicalDefaultFormats[kind];
        onChange({ ...settings, physicalDefaultFormats });
      }}><option value="">{formats.length ? 'First visible compatible format' : 'Enable a compatible format above'}</option>{formats.map(format => <option key={format} value={format}>{physicalFormatLabel(format)}</option>)}</select></label>;
    })}</div>
    <label className="field"><span>Default title search</span><select aria-label="Default title search" disabled={busy} value={settings.physicalTitleSearchSource || 'packs'} onChange={event => onChange({ ...settings, physicalTitleSearchSource: event.target.value as PhysicalSearchSource })}><option value="packs">Blank Box Database</option><option value="household">My Library</option><option value="connected">Connected libraries</option></select><small>Blank Box Database searches installed Offline Metapacks. Switch sources while adding any item; this preference sets where each new draft starts.</small></label>
    <SavedValues title="Saved physical locations" description="Reuse room, shelf, cabinet, or box names while adding copies." values={settings.physicalLocations} placeholder="Living room, shelf 2" onChange={(physicalLocations) => onChange({ ...settings, physicalLocations })}/>
    <section className="game-platform-settings" aria-labelledby="game-platform-settings-title">
      <h3 id="game-platform-settings-title">Game consoles & platforms</h3>
      <p className="muted small">Choose the systems your household uses. Existing game records remain in your collection when a choice is hidden.</p>
      <GamePlatformPicker value={settings.gamePlatforms} onChange={(gamePlatforms) => onChange({ ...settings, gamePlatforms })}/>
      <SavedValues title="Custom consoles & platforms" description="Add a console or device missing from the choices above. These appear in the same game dropdown." values={customPlatforms} placeholder="Another console or device" onChange={(custom) => onChange({ ...settings, gamePlatforms: platformChoices(selectedStandardPlatforms, custom) })}/>
    </section>
    <button className="primary-button" disabled={busy} onClick={onSave}>Save Physical Media preferences<Check size={17}/></button>
    <div className="settings-divider"/>
    <h3>Move a physical location at once</h3>
    <p className="muted small">Move every physical copy at one saved location without editing titles one by one.</p>
    {locations.length ? <div className="bulk-location-move">
      <Select value={fromLocation} onValueChange={setFromLocation}><SelectTrigger aria-label="Current physical location"><SelectValue placeholder="Current location"/></SelectTrigger><SelectContent>{locations.map((location) => <SelectItem key={location} value={location}>{location}</SelectItem>)}</SelectContent></Select>
      <ArrowRight size={18}/>
      <label><span className="sr-only">New physical location</span><input list="blank-box-location-options" maxLength={250} value={toLocation} onChange={(event) => setToLocation(event.target.value)} placeholder="New location"/></label>
      <button className="subtle-button" disabled={busy || !fromLocation || !toLocation.trim() || fromLocation === toLocation.trim()} onClick={() => void move()}>Move {matchingCopies || ''} {matchingCopies === 1 ? 'copy' : 'copies'}</button>
      <datalist id="blank-box-location-options">{locations.map((location) => <option key={location} value={location}/>)}</datalist>
    </div> : <p className="muted small">Add a physical item with a saved location to enable bulk moves.</p>}
  </section>;
}
