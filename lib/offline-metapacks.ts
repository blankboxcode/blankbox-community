import type { MetadataCandidate } from './blank-box-client';

const names: Record<string, string> = {
  'movie-work-candidates': 'Movies', 'tv-work-candidates': 'TV Shows',
  'book-work-candidates': 'Books', 'music-work-candidates': 'Music',
  'comic-work-candidates': 'Comics', 'game-work-candidates': 'Games',
  'music-proof': 'Audio CD matching sample',
};
export function offlinePackName(id: string, fallback?: string) { return names[id] || fallback || id; }
export function metadataMatchCreator(candidate: MetadataCandidate) {
  return candidate.catalogDetails?.directors?.join(' · ') || candidate.creator || candidate.catalogDetails?.authors?.join(' · ') || candidate.catalogDetails?.creators?.join(' · ') || '';
}
export function metadataMatchLabel(candidate: MetadataCandidate) {
  const creator = metadataMatchCreator(candidate);
  const type = candidate.kind === 'music' ? candidate.catalogDetails?.releaseType : '';
  return `${candidate.title}${candidate.year ? ` (${candidate.year})` : ''}${creator ? ` - ${creator}` : ''}${type ? ` · ${type}` : ''}`;
}

const normalized = (value: string) => value.normalize('NFKD').toLocaleLowerCase().replace(/\p{M}/gu, '').replace(/[^\p{L}\p{N}]/gu, '');
const creatorKey = (candidate: MetadataCandidate) => normalized(metadataMatchCreator(candidate));
const richness = (candidate: MetadataCandidate) => Number(!!candidate.description) * 1000 + Object.keys(candidate.catalogDetails || {}).length * 10 + Number(!!metadataMatchCreator(candidate));

/** Presentation groups retain every option; they never establish identity. */
export function metadataMatchGroups(candidates: MetadataCandidate[]) {
  const buckets = new Map<string, MetadataCandidate[]>();
  for (const candidate of candidates) {
    const origin = candidate.origin.startsWith('pack:') ? candidate.origin : candidate.id;
    const release = candidate.level === 'release' ? JSON.stringify([candidate.format, candidate.edition, candidate.season, candidate.identifier?.namespace, candidate.identifier?.value]) : '';
    const type = candidate.kind === 'music' ? candidate.catalogDetails?.releaseType || '' : '';
    const key = JSON.stringify([origin, candidate.kind, candidate.level, normalized(candidate.title), candidate.year, release, type]);
    const bucket = buckets.get(key) || []; bucket.push(candidate); buckets.set(key, bucket);
  }
  const groups: MetadataCandidate[][] = [];
  for (const bucket of buckets.values()) {
    const creators = new Set(bucket.map(creatorKey).filter(Boolean));
    if (creators.size <= 1) groups.push(bucket.sort((a, b) => richness(b) - richness(a)));
    else {
      const separate = new Map<string, MetadataCandidate[]>();
      for (const candidate of bucket) { const key = creatorKey(candidate) || candidate.id; const group = separate.get(key) || []; group.push(candidate); separate.set(key, group); }
      groups.push(...[...separate.values()].map(group => group.sort((a, b) => richness(b) - richness(a))));
    }
  }
  return groups;
}
