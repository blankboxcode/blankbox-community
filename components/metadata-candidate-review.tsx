'use client';

import { useId, useState } from 'react';
import { blankBoxClient, type MetadataCandidate } from '@/lib/blank-box-client';
import type { Kind } from '@/lib/media';
import { metadataMatchGroups, metadataMatchLabel, offlinePackName } from '@/lib/offline-metapacks';
import { MetadataReferenceEditor } from '@/components/metadata-reference-editor';

type Props = {
  title: string;
  kind: Kind;
  year?: number | null;
  identifier?: { namespace: string; value: string };
  selectedId: string;
  onSelect: (id: string, candidate?: MetadataCandidate) => void;
  targetLevel?: 'work' | 'release' | 'any';
  releaseRequiresIdentifier?: boolean;
  sourceScope?: 'all' | 'packs' | 'saved';
  excludeItemId?: string;
  allowManualCreate?: boolean;
  disabled?: boolean;
  onSearchComplete?: () => void;
};

export function MetadataCandidateReview({ title, kind, year, identifier, selectedId, onSelect, targetLevel = 'work', releaseRequiresIdentifier = false, sourceScope = 'all', excludeItemId, allowManualCreate = true, disabled, onSearchComplete }: Props) {
  const groupName = useId();
  const [candidates, setCandidates] = useState<MetadataCandidate[] | null>(null);
  const [showAll, setShowAll] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const search = async () => {
    setBusy(true); setError(''); setShowAll(false); onSelect('');
    try {
      const byId = identifier?.value ? await blankBoxClient.metadataSearch({ kind, namespace: identifier.namespace, value: identifier.value, scope: sourceScope, excludeItemId }) : [];
      const byTitle = title.trim() ? await blankBoxClient.metadataSearch({ title: title.trim(), kind, year, scope: sourceScope, excludeItemId }) : [];
      setCandidates([...new Map([...byTitle, ...byId].map(candidate => [candidate.id, candidate])).values()]);
    } catch (cause) { setCandidates(null); setError((cause as Error).message); }
    finally { setBusy(false); onSearchComplete?.(); }
  };
  const createManual = async () => {
    setBusy(true); setError('');
    try {
      const created = await blankBoxClient.metadataCreate({ title: title.trim(), kind, level: 'work', year });
      onSelect(created.id);
      setCandidates(previous => [{ id: created.id, title: created.title, kind, level: 'work', work_id: null, year: created.year, origin: 'manual', evidence: ['owner-entered'], confidence: 'review', requiresReview: true }, ...(previous || [])]);
    } catch (cause) { setError((cause as Error).message); }
    finally { setBusy(false); }
  };
  const atLevel = (candidate: MetadataCandidate) => targetLevel === 'any' || candidate.level === targetLevel;
  const hasReleaseEvidence = (candidate: MetadataCandidate) => !releaseRequiresIdentifier || candidate.level !== 'release' || candidate.evidence.includes('exact identifier');
  const selectable = candidates?.filter(candidate => atLevel(candidate) && hasReleaseEvidence(candidate)) || [];
  const groups = metadataMatchGroups(selectable);
  const visible = showAll ? groups : groups.slice(0, 6).concat(groups.filter(group => group.some(candidate => candidate.id === selectedId) && !groups.slice(0, 6).includes(group)));
  const matchingPacks = new Set(selectable.filter(candidate => candidate.origin.startsWith('pack:')).map(candidate => candidate.origin.slice(5)));
  const titleOnlyReleases = candidates?.filter(candidate => atLevel(candidate) && !hasReleaseEvidence(candidate)).length || 0;
  const otherLevel = candidates?.filter(candidate => !atLevel(candidate)).length || 0;
  return <div className="metadata-candidate-review">
    <button type="button" className="subtle-button" disabled={disabled || busy || !title.trim() && !identifier?.value} onClick={() => void search()}>{busy ? 'Searching…' : sourceScope === 'packs' ? 'Search Blank Box Database' : sourceScope === 'saved' ? 'Search saved metadata' : 'Search saved metadata and Offline Metapacks'}</button>
    {candidates && <div className="inventory-candidates">
      <strong>{selectable.length ? `${groups.length} ${groups.length === 1 ? 'title match' : 'title matches'}` : sourceScope === 'packs' ? 'No match found in installed offline packs' : 'No saved metadata match found'}</strong>
      {sourceScope === 'packs' && !!matchingPacks.size && <p className="muted small">Search results from {matchingPacks.size} installed {matchingPacks.size === 1 ? 'Offline Metapack' : 'Offline Metapacks'}.</p>}
      <p className="muted small">Review the title before linking its metadata. Physical editions need edition identifiers.{releaseRequiresIdentifier ? ' Exact release identifiers are required to select an edition.' : ''}</p>
      {visible.map(group => {
        const first = group.find(candidate => candidate.id === selectedId) || group[0];
        const option = (candidate: MetadataCandidate) => <label key={candidate.id} className="metadata-candidate-option">
          <input type="radio" name={groupName} checked={selectedId === candidate.id} disabled={disabled || busy} onChange={() => onSelect(candidate.id, candidate)}/>
          <span>{metadataMatchLabel(candidate)}{candidate.level === 'release' ? ` · ${[candidate.format, candidate.edition, candidate.season === 'complete-series' ? 'Complete series' : candidate.season === 'specials' ? 'Specials' : candidate.season ? `Season ${candidate.season}` : ''].filter(Boolean).join(' · ')}` : ''}<small>{candidate.origin.startsWith('pack:') ? `${candidate.level === 'release' ? 'Matching edition' : candidate.evidence.some(value => value === 'exact title' || value === 'title and year' || value === 'exact identifier') ? 'Matching title' : 'Possible title match'} from locally installed database · Installed pack: ${offlinePackName(candidate.origin.slice(5),candidate.packName)}` : candidate.origin === 'manual' ? 'Your saved local metadata' : 'Saved library metadata'}</small>{candidate.catalogDetails?.contentRating&&<small>Rating: {candidate.catalogDetails.contentRating}</small>}{candidate.description&&<small className="metadata-candidate-synopsis">{candidate.description.slice(0,220)}{candidate.description.length>220?'…':''}</small>}{candidate.identifier&&<small>{candidate.identifier.namespace.toUpperCase()}: {candidate.identifier.value}</small>}</span>
        </label>;
        return <div className="metadata-match-result" key={group.map(candidate => candidate.id).join('|')}>
          {option(first)}
          {group.length > 1 && <details className="metadata-candidate-group">
            <summary>Other records with this title ({group.length - 1})</summary>
            <p className="muted small">These identities could not be safely consolidated. Review an alternative if the title above is not the work you mean.</p>
            {group.filter(candidate => candidate.id !== first.id).map(candidate => <div key={candidate.id}>{option(candidate)}{candidate.identifiers?.length ? <small>{candidate.identifiers.map(value => `${value.namespace}: ${value.value}`).join(' · ')}</small> : <small>Creator or identifying details are incomplete.</small>}</div>)}
          </details>}
        </div>;
      })}
      {groups.length > 6 && <button type="button" className="text-button" onClick={() => setShowAll(value => !value)}>{showAll ? 'Show fewer matches' : `Show ${groups.length - 6} more titles`}</button>}
      {titleOnlyReleases > 0 && <p className="muted small">{titleOnlyReleases} title-only release {titleOnlyReleases === 1 ? 'suggestion was' : 'suggestions were'} left out because there is no matching release identifier. You can still choose a work/title match or enter details yourself.</p>}
      {otherLevel > 0 && <p className="muted small">{otherLevel} {otherLevel === 1 ? 'record refers' : 'records refer'} to a different identity level and cannot be linked here.</p>}
      <label><input type="radio" name={groupName} checked={!selectedId} disabled={disabled || busy} onChange={() => onSelect('')}/><span>Keep metadata unconfirmed<small>You can review it later. Nothing is linked automatically.</small></span></label>
    </div>}
    {candidates && title.trim() && targetLevel !== 'release' && allowManualCreate && sourceScope !== 'packs' && <button type="button" className="text-button" disabled={disabled || busy} onClick={() => void createManual()}>Save local metadata for this title</button>}
    {selectedId.startsWith('bbm:') && <MetadataReferenceEditor key={selectedId} entityId={selectedId} onChanged={entity => setCandidates(current => current?.map(candidate => candidate.id === entity.id ? { ...candidate, title: entity.title, year: entity.year, evidence: ['owner correction'], confidence: 'review' } : candidate) || null)}/>}
    {error && <p role="alert" className="error-text">{error}</p>}
  </div>;
}
