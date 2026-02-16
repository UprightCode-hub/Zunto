export const getProductTitle = (product) => product?.title || product?.name || 'Product';

export const getProductImage = (product) => {
  if (!product) {
    return '/placeholder.svg';
  }

  if (typeof product.primary_image === 'string' && product.primary_image.trim()) {
    return product.primary_image;
  }

  if (typeof product.image === 'string' && product.image.trim()) {
    return product.image;
  }

  if (Array.isArray(product.images) && product.images.length > 0) {
    const firstImage = product.images[0];
    if (typeof firstImage === 'string') {
      return firstImage;
    }

    if (typeof firstImage?.image === 'string' && firstImage.image.trim()) {
      return firstImage.image;
    }
  }

  return '/placeholder.svg';
};
