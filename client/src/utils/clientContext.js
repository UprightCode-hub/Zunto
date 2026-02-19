const canUseBrowser = () => typeof window !== 'undefined';

const MOBILE_MAX_WIDTH = 767;
const TABLET_MAX_WIDTH = 1023;

const resolveViewportWidth = () => {
  if (!canUseBrowser()) {
    return 1280;
  }

  return window.innerWidth || document.documentElement?.clientWidth || 1280;
};

export const getClientViewport = () => {
  const width = resolveViewportWidth();

  if (width <= MOBILE_MAX_WIDTH) {
    return 'mobile';
  }

  if (width <= TABLET_MAX_WIDTH) {
    return 'tablet';
  }

  return 'desktop';
};

export const getClientPlatform = () => {
  if (!canUseBrowser()) {
    return 'server';
  }

  const ua = (navigator.userAgent || '').toLowerCase();

  if (/iphone|android.+mobile|windows phone|mobile/.test(ua)) {
    return 'phone';
  }

  if (/ipad|tablet|android/.test(ua)) {
    return 'tablet';
  }

  return 'laptop-desktop';
};

export const getClientContext = () => ({
  viewport: getClientViewport(),
  platform: getClientPlatform(),
});
