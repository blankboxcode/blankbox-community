import type { Kind } from './media';

export const physicalFormats = [
  'DVD',
  'Blu-ray',
  '4K UHD Blu-ray',
  'Game',
  'VHS',
  'Betamax',
  'LaserDisc',
  'CD',
  'Vinyl',
  'Cassette',
  '8-track',
  'MiniDisc',
  'Book',
  'Hardcover',
  'Paperback',
  'Comic',
  'Magazine',
  'Other',
] as const;

export type PhysicalFormat = (typeof physicalFormats)[number];

export const defaultPhysicalFormats: PhysicalFormat[] = [
  'DVD',
  'Blu-ray',
  '4K UHD Blu-ray',
  'Game',
  'CD',
  'Vinyl',
  'Book',
  'Comic',
];

export function physicalFormatLabel(format: PhysicalFormat): string {
  return format === 'Game' ? 'Games' : format;
}

export const physicalFormatGroups: { label: string; formats: PhysicalFormat[] }[] = [
  { label: 'Movies & shows', formats: ['DVD', 'Blu-ray', '4K UHD Blu-ray', 'VHS', 'Betamax', 'LaserDisc'] },
  { label: 'Games', formats: ['Game'] },
  { label: 'Music', formats: ['CD', 'Vinyl', 'Cassette', '8-track', 'MiniDisc'] },
  { label: 'Print', formats: ['Book', 'Hardcover', 'Paperback', 'Comic', 'Magazine'] },
  { label: 'More', formats: ['Other'] },
];

export type PhysicalDraft = {
  title: string;
  format: PhysicalFormat;
  kind: Kind;
  location: string;
  year: string;
  genre: string;
  description: string;
  edition: string;
  season: string;
  barcode: string;
  condition: string;
  creator: string;
  publisher: string;
  platform: string;
  volume: string;
  issue: string;
  region: string;
  catalogNumber: string;
};

export const emptyPhysicalDraft: PhysicalDraft = {
  title: '',
  format: 'DVD',
  kind: 'movie',
  location: '',
  year: '',
  genre: '',
  description: '',
  edition: '',
  season: '',
  barcode: '',
  condition: '',
  creator: '',
  publisher: '',
  platform: '',
  volume: '',
  issue: '',
  region: '',
  catalogNumber: '',
};

export function defaultKindForFormat(format: PhysicalFormat): Kind {
  if (['CD', 'Vinyl', 'Cassette', '8-track', 'MiniDisc'].includes(format)) return 'music';
  if (['Book', 'Hardcover', 'Paperback', 'Magazine'].includes(format)) return 'book';
  if (format === 'Comic') return 'comic';
  if (format === 'Game') return 'game';
  return 'movie';
}

export function physicalKindOptions(format: PhysicalFormat): Kind[] {
  if (['DVD', 'Blu-ray', '4K UHD Blu-ray', 'VHS', 'Betamax', 'LaserDisc'].includes(format)) return ['movie', 'tv'];
  if (format === 'Other') return ['movie', 'tv', 'music', 'book', 'comic', 'game', 'photo', 'home-video', 'file'];
  return [defaultKindForFormat(format)];
}

export function physicalDraftForFormat(draft: PhysicalDraft, format: PhysicalFormat): PhysicalDraft {
  const options = physicalKindOptions(format);
  const kind = options.includes(draft.kind) ? draft.kind : defaultKindForFormat(format);
  return physicalDraftForKind({ ...draft, format }, kind);
}

export function physicalDraftForKind(draft: PhysicalDraft, kind: Kind): PhysicalDraft {
  const detailGroup = (value: Kind) => {
    if (value === 'movie' || value === 'tv') return 'video';
    if (value === 'book' || value === 'comic') return 'print';
    return value;
  };
  const changedGroup = detailGroup(draft.kind) !== detailGroup(kind);
  const keepsCreator = ['movie', 'tv', 'music', 'book', 'comic', 'game'].includes(kind);
  const keepsVolume = kind === 'book' || kind === 'comic';
  const keepsIssue = kind === 'comic' || draft.format === 'Magazine';
  return {
    ...draft,
    kind,
    season: kind === 'tv' ? draft.season : '',
    platform: kind === 'game' && !changedGroup ? draft.platform : '',
    creator: keepsCreator && !changedGroup ? draft.creator : '',
    publisher: keepsCreator && !changedGroup ? draft.publisher : '',
    volume: keepsVolume ? draft.volume : '',
    issue: keepsIssue ? draft.issue : '',
  };
}

export function physicalDetailFields(draft: PhysicalDraft) {
  if (draft.kind === 'game') return { creatorLabel: 'Developer or creator', publisherLabel: 'Publisher', platform: true, volume: false, issue: false };
  if (draft.kind === 'music') return { creatorLabel: 'Artist', publisherLabel: 'Label', platform: false, volume: false, issue: false };
  if (draft.kind === 'comic') return { creatorLabel: 'Writer or creator', publisherLabel: 'Publisher', platform: false, volume: true, issue: true };
  if (draft.kind === 'book') return { creatorLabel: draft.format === 'Magazine' ? 'Author or editor' : 'Author', publisherLabel: 'Publisher', platform: false, volume: true, issue: draft.format === 'Magazine' };
  if (draft.kind === 'movie' || draft.kind === 'tv') return { creatorLabel: 'Director or creator', publisherLabel: 'Studio or distributor', platform: false, volume: false, issue: false };
  return { platform: false, volume: false, issue: false };
}
