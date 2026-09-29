import { BookOpen, FolderOpen, Images, Play, type LucideProps } from 'lucide-react';
import { readerFormat, type MediaItem, type MediaSource } from '@/lib/media';

export function MediaActionIcon({ item, source, ...props }: LucideProps & { item: MediaItem; source?: MediaSource }) {
  const Icon = item.kind === 'book' || item.kind === 'comic' || (source && readerFormat(source)) ? BookOpen
    : item.kind === 'photo' ? Images
    : item.kind === 'file' || item.kind === 'game' ? FolderOpen
    : Play;
  return <Icon {...props}/>;
}
