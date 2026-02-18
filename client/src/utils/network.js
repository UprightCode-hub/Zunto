const LOCALHOST_HOSTS = new Set(['localhost', '127.0.0.1', '::1']);

const canUseBrowserLocation = () => typeof window !== 'undefined' && Boolean(window.location?.hostname);

export const normalizeApiBaseUrl = (rawApiBaseUrl = '') => {
  const trimmedBaseUrl = rawApiBaseUrl.trim().replace(/\/+$/, '');
  if (!trimmedBaseUrl || !canUseBrowserLocation()) {
    return trimmedBaseUrl;
  }

  try {
    const configuredUrl = new URL(trimmedBaseUrl);
    if (!LOCALHOST_HOSTS.has(configuredUrl.hostname)) {
      return trimmedBaseUrl;
    }

    const frontendHost = window.location.hostname;

    if (LOCALHOST_HOSTS.has(frontendHost)) {
      return trimmedBaseUrl;
    }

    return '';
  } catch {
    return trimmedBaseUrl;
  }
};

export const buildWebSocketBaseUrl = (apiBaseUrl) => {
  const browserWsBase = canUseBrowserLocation()
    ? window.location.origin.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:')
    : 'ws://localhost:8000';

  return (apiBaseUrl || browserWsBase)
    .replace(/^http:/, 'ws:')
    .replace(/^https:/, 'wss:');
};
