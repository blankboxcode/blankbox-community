import type { ServiceLink, Settings, StreamingService } from './media';

export const streamingDefaults: ServiceLink[] = [
  { id: 'netflix', name: 'Netflix', mark: 'N', color: '#ed2439', url: 'https://www.netflix.com/', searchUrl: 'https://www.netflix.com/search?q={query}' },
  { id: 'prime-video', name: 'Prime Video', mark: 'prime', color: '#59b8ed', url: 'https://www.primevideo.com/', searchUrl: 'https://www.amazon.com/s?i=instant-video&k={query}' },
  { id: 'disney-plus', name: 'Disney+', mark: 'Disney+', color: '#91acee', url: 'https://www.disneyplus.com/', searchUrl: 'https://www.disneyplus.com/search?q={query}' },
  { id: 'youtube', name: 'YouTube', mark: '▶', color: '#ff4444', url: 'https://www.youtube.com/', searchUrl: 'https://www.youtube.com/results?search_query={query}' },
  { id: 'spotify', name: 'Spotify', mark: 'Spotify', color: '#6dd799', url: 'https://open.spotify.com/', searchUrl: 'https://open.spotify.com/search/{query}' },
  { id: 'apple-tv', name: 'Apple TV', mark: 'tv', color: '#ededed', url: 'https://tv.apple.com/', searchUrl: 'https://tv.apple.com/search?term={query}' },
  { id: 'movies-anywhere', name: 'Movies Anywhere', mark: 'MA', color: '#aab2ff', url: 'https://moviesanywhere.com/home' },
];

export function safeServiceUrl(value: string) {
  try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : ''; }
  catch { return ''; }
}

export function configuredServices(settings: Pick<Settings, 'streamingServices' | 'streamingServiceOverrides' | 'customStreamingServices'>, includeAll = false): ServiceLink[] {
  const overrides = settings.streamingServiceOverrides || [];
  const builtin = streamingDefaults.filter(service => includeAll || settings.streamingServices.includes(service.id as StreamingService)).map(service => {
    const override = overrides.find(row => row.id === service.id);
    return override ? { ...service, ...override, searchUrl: override.url===service.url?service.searchUrl:undefined } : service;
  });
  return [...builtin, ...(settings.customStreamingServices || []).filter(row => row.enabled !== false)].filter(row => safeServiceUrl(row.url));
}

export function serviceDestination(service: ServiceLink, title: string) {
  return safeServiceUrl(service.searchUrl ? service.searchUrl.replace('{query}', encodeURIComponent(title)) : service.url);
}

export function newRecordId() { return Array.from(crypto.getRandomValues(new Uint8Array(16)),byte=>byte.toString(16).padStart(2,'0')).join(''); }
