import type { MediaItem, Settings } from './media';

export const homeRowOptions = [
  { id: 'recently-added', label: 'Recently added', description: 'New arrivals from your sources and Physical Media.' },
  { id: 'recently-released', label: 'Recently released', description: 'Newer releases in digital and connected libraries.' },
  { id: 'movies', label: 'Movies', description: 'A quick row for your films.' },
  { id: 'tv', label: 'TV Shows', description: 'Series in your collection.' },
  { id: 'music', label: 'Music', description: 'Albums and songs.' },
  { id: 'photos', label: 'Photos & Memories', description: 'Your pictures and home videos.' },
  { id: 'books', label: 'Books', description: 'Your reading collection.' },
  { id: 'comics', label: 'Comics', description: 'Issues and collections.' },
  { id: 'games', label: 'Games', description: 'Games across your platforms.' },
] as const;

export type HomeRow = (typeof homeRowOptions)[number]['id'];
export const defaultHomeRows: HomeRow[] = ['recently-added', 'recently-released'];
export const homeHeroModes = ['watch', 'music', 'book', 'photos', 'comics', 'games'] as const;
export type HomeHeroMode = (typeof homeHeroModes)[number];
export function normalizeHomeHeroOrder(value: readonly string[] | undefined): HomeHeroMode[] {
  const saved = Array.isArray(value) ? value.filter((id): id is HomeHeroMode => homeHeroModes.includes(id as HomeHeroMode)) : [];
  return [...new Set([...saved, ...homeHeroModes])];
}
export const homeHeroSorts = ['added', 'released', 'az', 'random'] as const;
export type HomeHeroSort = (typeof homeHeroSorts)[number];

export const featuredMediaKeys = { watch: 'heroWatch', music: 'heroMusic', book: 'heroBooks', photos: 'heroPhotos', comics: 'heroComics', games: 'heroGames' } as const;
export const featuredMediaLabels: Record<HomeHeroMode, string> = { watch: 'Movies & TV', music: 'Music', book: 'Books', photos: 'Photos & videos', comics: 'Comics', games: 'Games' };
const featuredKinds = { watch: ['movie', 'tv'], music: ['music'], book: ['book'], photos: ['photo', 'home-video'], comics: ['comic'], games: ['game'] } as const;
export function featuredCoverPool(items: MediaItem[], settings: Settings, compare: (a: MediaItem, b: MediaItem) => number, photoId?: string): MediaItem[] {
  const groups = normalizeHomeHeroOrder(settings.homeHeroOrder)
    .filter(mode => settings[featuredMediaKeys[mode]] ?? mode === 'watch')
    .map(mode => items.filter(item => (featuredKinds[mode] as readonly string[]).includes(item.kind) && (item.kind !== 'photo' || item.id === photoId)).sort(compare));
  // Take one cover from each chosen category per round, so a large movie
  // catalog cannot keep books or music out of the featured rotation.
  const result: MediaItem[] = [];
  for (let index = 0; groups.some(group => index < group.length); index++) {
    for (const group of groups) if (group[index]) result.push(group[index]);
  }
  return result;
}
