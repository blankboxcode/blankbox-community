import type { Kind, MediaItem } from './media';

export type ActivityStatus = 'not-started' | 'in-progress' | 'completed';
export type ItemActivity = { status: ActivityStatus; updatedAt?: string; eventId?: string };
export type ActivityEvent = { id: string; itemId: string; status: ActivityStatus; episodeKey: string; sourceId: string | null; versionId: string | null; profileId: string; origin: string; createdAt: string; undoneAt: string | null };
export type CollectionRules = { kinds: Kind[]; genres: string[]; formats: string[]; status: ActivityStatus | ''; yearFrom: number | null; yearTo: number | null };
export type LibraryCollection = { titleCount?:number;covers?:MediaItem[]; completionSetId?: string; recommendationId?: string; completionCounts?: { library: number; known: number; wanted: number; review: number }; id: string; name: string; kind: 'manual' | 'series' | 'genre' | 'seasonal' | 'smart'; rules: CollectionRules; startDay: string; endDay: string; createdAt: string; updatedAt: string; memberIds: string[]; itemIds: string[]; active: boolean };
export const emptyCollectionRules: CollectionRules = { kinds: [], genres: [], formats: [], status: '', yearFrom: null, yearTo: null };
export const collectionTypeNames = { manual: 'Custom collection', series: 'Movie series / franchise', genre: 'Genre collection', seasonal: 'Seasonal collection', smart: 'Smart collection' };
export function itemGenres(item: MediaItem) { return [...new Set([...(item.genre || '').split(/[·,;|]/).map(value => value.trim()).filter(Boolean), ...(item.customGenres || []), ...(item.collectionGenres || [])])]; }
export function activityLabel(kind: Kind, status: ActivityStatus) {
  if (status === 'not-started') return ['movie', 'tv', 'home-video'].includes(kind) ? 'Unwatched' : 'Not started';
  if (status === 'in-progress') return 'In progress';
  return ['movie', 'tv', 'home-video'].includes(kind) ? 'Watched' : kind === 'book' || kind === 'comic' ? 'Read' : kind === 'music' ? 'Listened' : kind === 'game' ? 'Played' : 'Completed';
}

export function orderedCollectionItems(collection: LibraryCollection, items: MediaItem[] | ReadonlyMap<string, MediaItem>) {
  const lookup: ReadonlyMap<string, MediaItem> = Array.isArray(items) ? new Map(items.map(item => [item.id, item])) : items;
  return collection.itemIds.flatMap(id => lookup.has(id) ? [lookup.get(id)!] : []);
}
