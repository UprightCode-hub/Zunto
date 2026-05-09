import React, { useEffect, useRef, useState } from 'react';
import { PRODUCT_IMAGE_FALLBACK, isUsableImage } from '../../utils/product';

export default function ProductImage({
  src,
  alt,
  className = '',
  timeoutMs = 15000,
  onError,
  onLoad,
  style,
  ...imageProps
}) {
  const imgRef = useRef(null);
  const loadedSrcRef = useRef('');
  const actualSrc = isUsableImage(src) ? src.trim() : '';
  const [shouldLoad, setShouldLoad] = useState(false);
  const [failed, setFailed] = useState(!actualSrc);

  useEffect(() => {
    loadedSrcRef.current = '';
    setShouldLoad(false);
    setFailed(!actualSrc);
  }, [actualSrc]);

  useEffect(() => {
    if (!actualSrc || failed) {
      return undefined;
    }

    const image = imgRef.current;
    if (!image) {
      return undefined;
    }

    if (!('IntersectionObserver' in window)) {
      setShouldLoad(true);
      return undefined;
    }

    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        setShouldLoad(true);
        observer.disconnect();
      }
    }, { threshold: 0.01 });

    observer.observe(image);
    return () => observer.disconnect();
  }, [actualSrc, failed]);

  useEffect(() => {
    if (!actualSrc || !shouldLoad || failed || timeoutMs <= 0) {
      return undefined;
    }

    const currentSrc = actualSrc;
    const timerId = window.setTimeout(() => {
      if (loadedSrcRef.current === currentSrc) {
        return;
      }

      setFailed(true);
      if (imgRef.current) {
        imgRef.current.src = PRODUCT_IMAGE_FALLBACK;
      }
    }, timeoutMs);

    return () => window.clearTimeout(timerId);
  }, [actualSrc, failed, shouldLoad, timeoutMs]);

  const handleError = (event) => {
    setFailed(true);
    event.currentTarget.removeAttribute('srcset');
    event.currentTarget.src = PRODUCT_IMAGE_FALLBACK;
    onError?.(event);
  };

  const handleLoad = (event) => {
    if (shouldLoad && actualSrc && !failed) {
      loadedSrcRef.current = actualSrc;
    }
    onLoad?.(event);
  };

  const displaySrc = actualSrc && shouldLoad && !failed
    ? actualSrc
    : PRODUCT_IMAGE_FALLBACK;
  const fallbackStyle = {
    ...style,
    backgroundColor: '#0F172A',
    backgroundImage: `url("${PRODUCT_IMAGE_FALLBACK}")`,
    backgroundPosition: 'center',
    backgroundSize: 'cover',
  };

  return (
    <img
      {...imageProps}
      ref={imgRef}
      src={displaySrc}
      alt={alt}
      className={className}
      style={fallbackStyle}
      loading="lazy"
      decoding="async"
      onError={handleError}
      onLoad={handleLoad}
    />
  );
}
