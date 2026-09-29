export const sidebarDestinations = ['library', 'collections', 'physical', 'movie', 'tv', 'music', 'photo', 'book', 'comic', 'game'] as const;
export type SidebarDestination = (typeof sidebarDestinations)[number];

export function normalizeSidebarOrder(value: readonly string[] | undefined): SidebarDestination[] {
  const saved = Array.isArray(value) ? value.filter((id): id is SidebarDestination => sidebarDestinations.includes(id as SidebarDestination)) : [];
  return [...new Set([...saved, ...sidebarDestinations])];
}
