export const getProductTitle = (product) => product?.title || product?.name || 'Product';

const PRODUCT_IMAGE_FALLBACK_SVG = `
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1200" viewBox="0 0 1200 1200" fill="none">
  <rect width="1200" height="1200" fill="#0F172A"/>
  <rect x="170" y="170" width="860" height="860" rx="48" fill="#111827" stroke="#334155" stroke-width="8"/>
  <path d="M310 790L510 540L685 705L770 610L890 790H310Z" fill="#1E293B"/>
  <circle cx="465" cy="420" r="66" fill="#334155"/>
  <path d="M246 246H954V954H246V246Z" stroke="#2C77D1" stroke-width="10" opacity="0.28"/>
  <path d="M320 910H880" stroke="#9426F4" stroke-width="16" stroke-linecap="round" opacity="0.48"/>
</svg>
`.trim();

export const PRODUCT_IMAGE_FALLBACK = `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(PRODUCT_IMAGE_FALLBACK_SVG)}`;

export const isNoImagePlaceholder = (value) => (
  typeof value === 'string'
  && /placehold\.co/i.test(value)
  && /text=No\+?Image|text=No%20Image/i.test(value)
);

export const isBundledPlaceholder = (value) => (
  typeof value === 'string'
  && /(^|\/)placeholder\.(svg|png)(?:[?#].*)?$/i.test(value.trim())
);

export const isUsableImage = (value) => (
  typeof value === 'string'
  && value.trim()
  && !isNoImagePlaceholder(value)
  && !isBundledPlaceholder(value)
  && value.trim() !== PRODUCT_IMAGE_FALLBACK
);

export const getProductImage = (product, fallback = PRODUCT_IMAGE_FALLBACK) => {
  if (!product) {
    return fallback;
  }

  if (isUsableImage(product.primary_image)) {
    return product.primary_image.trim();
  }

  if (isUsableImage(product.image_url_locked)) {
    return product.image_url_locked.trim();
  }

  if (isUsableImage(product.image_url)) {
    return product.image_url.trim();
  }

  if (isUsableImage(product.image)) {
    return product.image.trim();
  }

  if (isUsableImage(product.thumbnail)) {
    return product.thumbnail.trim();
  }

  if (Array.isArray(product.images) && product.images.length > 0) {
    const firstImage = product.images[0];
    if (isUsableImage(firstImage)) {
      return firstImage.trim();
    }

    if (isUsableImage(firstImage?.image)) {
      return firstImage.image.trim();
    }
  }

  return fallback;
};
