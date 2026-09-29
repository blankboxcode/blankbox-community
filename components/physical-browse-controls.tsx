'use client';

import { Grid2X2, Heart, Library, MapPin, Plus, Settings2 } from 'lucide-react';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { kindNames, type Kind } from '@/lib/media';
import type { ActivityStatus } from '@/lib/collection-organization';
import { navigationLabels } from '@/lib/navigation';

const categories: Kind[] = ['movie', 'tv', 'music', 'book', 'comic', 'game', 'photo', 'home-video', 'file'];
type Props = {
  category: string;
  onCategory: (value: string) => void;
  format: string;
  formats: { id: string; label: string; count: number }[];
  onFormat: (value: string) => void;
  genre: string;
  genres: string[];
  onGenre: (value: string) => void;
  status: ActivityStatus | '';
  onStatus: (value: ActivityStatus | '') => void;
  sort: string;
  onSort: (value: string) => void;
  favorites: boolean;
  onFavorites: () => void;
  view: 'grid' | 'shelves';
  onView: (value: 'grid' | 'shelves') => void;
  local: boolean;
  onLocations: () => void;
  onCollections: () => void;
  onIntendToBuy?: () => void;
};

export function PhysicalBrowseControls({ category, onCategory, format, formats, onFormat, genre, genres, onGenre, status, onStatus, sort, onSort, favorites, onFavorites, view, onView, local, onLocations, onCollections, onIntendToBuy }: Props) {
  return <section className="physical-controls" aria-label="Browse Physical Media">
    <Tabs value={category} onValueChange={onCategory} className="physical-category-tabs">
      <TabsList className="filter-tabs" aria-label="Physical Media category">
        <TabsTrigger value="all">All Media</TabsTrigger>
        {categories.map(kind => <TabsTrigger key={kind} value={kind}>{kindNames[kind]}</TabsTrigger>)}
      </TabsList>
    </Tabs>
    <div className={`physical-filter-fields ${local ? '' : 'physical-filter-fields-preview'}`}>
      <label><span>{category === 'game' ? 'Console / Platform' : category === 'all' ? 'Format / Platform' : 'Format'}</span>
        <select aria-label="Physical format or platform" value={format} onChange={event => onFormat(event.target.value)}>
          <option value="all">{category === 'game' ? 'All Platforms' : 'All Formats'}</option>
          {formats.map(option => <option key={option.id} value={option.id}>{option.label} ({option.count})</option>)}
        </select>
      </label>
      {local && <>
        <label><span>Genre</span><select value={genre} onChange={event => onGenre(event.target.value)}><option value="">All Genres</option>{genres.map(value => <option key={value} value={value}>{value}</option>)}</select></label>
        <label><span>Local Status</span><select value={status} onChange={event => onStatus(event.target.value as ActivityStatus | '')}><option value="">Any Status</option><option value="not-started">Not Started</option><option value="in-progress">In Progress</option><option value="completed">Completed</option></select></label>
      </>}
      <label><span>Sort By</span><select value={sort} onChange={event => onSort(event.target.value)}><option value="recent">Recently Added</option><option value="az">Title A–Z</option><option value="year">Newest Release</option><option value="edition">Edition A–Z</option></select></label>
    </div>
    <div className="physical-control-footer">
      <div className="physical-display-controls">
        <div className="physical-layout-switch" role="group" aria-label="Physical Media view">
          <button type="button" className={view === 'grid' ? 'active' : ''} onClick={() => onView('grid')} aria-pressed={view === 'grid'}><Grid2X2 size={16}/>Grid</button>
          <button type="button" className={view === 'shelves' ? 'active' : ''} onClick={() => onView('shelves')} aria-pressed={view === 'shelves'}><MapPin size={16}/>By Location</button>
        </div>
        <button type="button" className={`physical-favorites ${favorites ? 'active' : ''}`} aria-label="Show favorites" aria-pressed={favorites} onClick={onFavorites}><Heart size={16} fill={favorites ? 'currentColor' : 'none'}/>Favorites</button>
      </div>
      <div className="physical-browse-actions" role="group" aria-label="Physical Media tools">
        <button type="button" className="text-button" onClick={onLocations}><Settings2 size={16}/>Locations</button>
        {local && <button type="button" className="text-button" onClick={onCollections}><Library size={16}/>{navigationLabels.collections}</button>}
        {onIntendToBuy && <button type="button" className="text-button" onClick={onIntendToBuy}><Plus size={16}/>{navigationLabels.collecting}</button>}
      </div>
    </div>
  </section>;
}
