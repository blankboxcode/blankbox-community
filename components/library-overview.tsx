'use client';

import { BookOpen, ChevronRight, Disc3, Film, Gamepad2, Images, Library, Music2, Tv } from 'lucide-react';
import { type CollectionSummary, type Kind, type LibraryState } from '@/lib/media';
import { physicalFormatLabel } from '@/lib/physical-media';

export type LibraryDestination = 'collections' | 'library' | 'physical' | 'movie' | 'tv' | 'music' | 'photo' | 'book' | 'comic' | 'game';

const categories: { id: LibraryDestination; label: string; kinds: Kind[]; icon: typeof Film }[] = [
  { id: 'movie', label: 'Movies', kinds: ['movie'], icon: Film },
  { id: 'tv', label: 'TV Shows', kinds: ['tv'], icon: Tv },
  { id: 'music', label: 'Music', kinds: ['music'], icon: Music2 },
  { id: 'photo', label: 'Photos & Memories', kinds: ['photo', 'home-video'], icon: Images },
  { id: 'book', label: 'Books', kinds: ['book'], icon: BookOpen },
  { id: 'comic', label: 'Comics', kinds: ['comic'], icon: BookOpen },
  { id: 'game', label: 'Games', kinds: ['game'], icon: Gamepad2 },
  { id: 'library', label: 'All media', kinds: [], icon: Library },
];

export function LibraryOverview({ state, summary, onOpen }: {
  state: LibraryState;
  summary: CollectionSummary;
  onOpen: (destination: LibraryDestination) => void;
}) {
  const counts = state.kindCounts || state.items.reduce((result, item) => {
    result[item.kind] = (result[item.kind] || 0) + 1;
    return result;
  }, {} as Partial<Record<Kind, number>>);
  const formats = state.physicalInventory.formats;

  return <section className="library-overview" aria-label="Library overview">
    <div className="library-count-banner">
      <div className="library-count-lead"><strong>{summary.titles}</strong><span>{summary.titles === 1 ? 'title' : 'titles'} in your library</span></div>
      <div className="library-count-details">
        <span><strong>{summary.digitalOrConnectedSources}</strong>Titles with digital access</span>
        <span><strong>{state.physicalInventory.packages}</strong>Physical items</span>
        <span><strong>{state.physicalInventory.copies}</strong>Owned copies</span>
      </div>
    </div>
    {state.mode==='box'&&<button className="library-collections-link" onClick={()=>onOpen('collections')}>Browse collections <span>{state.collectionCount??state.collections?.length??0} saved · Series, genres & seasonal favorites</span><ChevronRight size={18}/></button>}
    <div className="library-destinations">
      <button data-tv className="library-shelf-hub" onClick={() => onOpen('physical')} aria-label="Open Physical Media">
        <span className="source-icon lavender"><Disc3 size={28}/></span>
        <span className="library-shelf-content"><strong>Physical Media</strong><small>Find your editions, copies, and physical locations.</small>
          {!!formats.length && <span className="library-shelf-formats">{formats.slice(0, 4).map(format => <b key={format.label}>{format.label === 'Game' ? physicalFormatLabel('Game') : format.label}</b>)}{formats.length > 4 && <b>+{formats.length - 4} more</b>}</span>}
        </span>
        <ChevronRight size={22}/>
      </button>
      <nav className="library-category-grid" aria-label="Browse by category">
        {categories.map(({ id, label, kinds, icon: Icon }) => {
          const count = id === 'library' ? summary.titles : kinds.reduce((total, kind) => total + (counts[kind] || 0), 0);
          return <button data-tv className={`library-category kind-${id}`} key={id} onClick={() => onOpen(id)} aria-label={`Open ${label}, ${count} ${count === 1 ? 'title' : 'titles'}`}>
            <Icon size={22}/><span><strong>{label}</strong><small>{count} {count === 1 ? 'title' : 'titles'}</small></span><ChevronRight size={17}/>
          </button>;
        })}
      </nav>
    </div>
  </section>;
}
