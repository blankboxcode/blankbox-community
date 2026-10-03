import { BookOpen, Clapperboard, File, Gamepad2, Images, LibraryBig, Music2, Tv, Video, type LucideProps } from 'lucide-react';
import type { Kind } from '@/lib/media';

export const mediaKindLabels: Record<Kind, string> = {
  movie: 'Movie', tv: 'TV series', music: 'Music', photo: 'Photos',
  'home-video': 'Home video', book: 'Book', comic: 'Comic', game: 'Game', file: 'File',
};

export function MediaKindIcon({ kind, ...props }: LucideProps & { kind: Kind }) {
  const Icon = { movie: Clapperboard, tv: Tv, music: Music2, photo: Images,
    'home-video': Video, book: BookOpen, comic: LibraryBig, game: Gamepad2, file: File }[kind];
  return <Icon aria-hidden="true" {...props}/>;
}
