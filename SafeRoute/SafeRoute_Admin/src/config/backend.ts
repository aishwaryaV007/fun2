const DEFAULT_BACKEND_PORT = '8000';

function trimTrailingSlash(url: string): string {
  return url.replace(/\/+$/, '');
}

function resolveBrowserHostname(): string {
  if (typeof window === 'undefined' || !window.location.hostname) {
    return '127.0.0.1';
  }

  return window.location.hostname;
}

function resolveHttpBaseUrl(): string {
  const envUrl = import.meta.env.VITE_BACKEND_HTTP_URL?.trim();
  if (envUrl) {
    return trimTrailingSlash(envUrl);
  }

  const protocol =
    typeof window !== 'undefined' && window.location.protocol === 'https:'
      ? 'https:'
      : 'http:';

  return `${protocol}//${resolveBrowserHostname()}:${DEFAULT_BACKEND_PORT}`;
}

function resolveWsBaseUrl(httpBaseUrl: string): string {
  const envUrl = import.meta.env.VITE_BACKEND_WS_URL?.trim();
  if (envUrl) {
    return trimTrailingSlash(envUrl);
  }

  return httpBaseUrl.replace(/^http/i, 'ws');
}

export const BACKEND_HTTP_BASE_URL = resolveHttpBaseUrl();
export const BACKEND_WS_BASE_URL = resolveWsBaseUrl(BACKEND_HTTP_BASE_URL);

export const SOS_STREAM_WS_URL = `${BACKEND_WS_BASE_URL}/sos/stream`;
export const SOS_ALERTS_API_URL = `${BACKEND_HTTP_BASE_URL}/sos/alerts`;
export const SOS_RESOLVE_API_BASE_URL = `${BACKEND_HTTP_BASE_URL}/sos`;
export const ACTIVE_USERS_COUNT_API_URL = `${BACKEND_HTTP_BASE_URL}/users/count`;
export const HEATMAP_API_URL = `${BACKEND_HTTP_BASE_URL}/routes/heatmap`;
export const DANGER_ZONES_API_URL = `${BACKEND_HTTP_BASE_URL}/danger-zones`;

export const GOOGLE_MAPS_API_KEY =
  import.meta.env.VITE_GOOGLE_MAPS_API_KEY?.trim() ||
  'AIzaSyDRrY1Bt14-YTPB31s2WO71lq77XK6ix_g';
