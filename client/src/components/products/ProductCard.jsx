import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Heart, MapPin, ShoppingBag, Star } from 'lucide-react';
import { useCart } from '../../context/CartContext';
import { useAuth } from '../../context/AuthContext';
import { toggleFavorite as toggleFavoriteAPI } from '../../services/api';
import { getProductImage, getProductTitle } from '../../utils/product';
import { formatConditionLabel, formatNaira } from '../../utils/helpers';
import ProductImage from './ProductImage';

export default function ProductCard({ product, viewMode = 'grid' }) {
  const navigate = useNavigate();
  const { addToCart } = useCart();
  const { isAuthenticated } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [isFavorite, setIsFavorite] = useState(Boolean(product?.is_favorited));
  const [feedback, setFeedback] = useState('');

  const productTitle = getProductTitle(product);
  const rating = Number(product.average_rating || product.rating || 0);
  const reviewCount = Number(product.review_count || product.reviews_count || 0);

  const flashFeedback = (message) => {
    setFeedback(message);
    window.setTimeout(() => setFeedback(''), 2200);
  };

  const handleAddToCart = async (event) => {
    event.preventDefault();
    event.stopPropagation();

    try {
      setIsLoading(true);
      await addToCart(product.id, 1);
      flashFeedback('Added to cart');
    } catch (error) {
      flashFeedback(error?.message || 'Unable to add item');
    } finally {
      setIsLoading(false);
    }
  };

  const toggleFavorite = async (event) => {
    event.preventDefault();
    event.stopPropagation();

    if (!isAuthenticated) {
      navigate('/login');
      return;
    }

    const previous = isFavorite;
    setIsFavorite(!previous);

    try {
      const response = await toggleFavoriteAPI(product.slug);
      if (typeof response?.is_favorited === 'boolean') {
        setIsFavorite(response.is_favorited);
      }
      flashFeedback(response?.is_favorited === false ? 'Removed from wishlist' : 'Saved to wishlist');
    } catch {
      setIsFavorite(previous);
      flashFeedback('Unable to update wishlist');
    }
  };

  const FavoriteButton = ({ className = '' }) => (
    <button
      type="button"
      onClick={toggleFavorite}
      className={`btn-icon-utility border-0 bg-black/50 backdrop-blur-sm hover:bg-black/70 ${className}`}
      aria-label={isFavorite ? `Remove ${productTitle} from wishlist` : `Save ${productTitle} to wishlist`}
    >
      <Heart className={`h-4 w-4 ${isFavorite ? 'fill-red-500 text-red-500' : 'text-white'}`} />
    </button>
  );

  const ProductMeta = () => (
    <>
      <div className="mb-2 flex items-center gap-2">
        <div className="flex items-center gap-1 text-yellow-400">
          <Star className="h-4 w-4 fill-current" />
          <span className="text-sm text-white">{rating > 0 ? rating.toFixed(1) : 'Unrated'}</span>
        </div>
        <span className="text-xs text-gray-400">({reviewCount} reviews)</span>
      </div>
      <p className="mb-2 text-xs text-gray-400">Condition: {formatConditionLabel(product.condition)}</p>
      {product.location_display && (
        <p className="mb-3 flex items-center gap-1 text-xs text-gray-400">
          <MapPin className="h-3.5 w-3.5" /> {product.location_display}
        </p>
      )}
    </>
  );

  if (viewMode === 'list') {
    return (
      <Link
        to={`/product/${product.slug}`}
        className="group flex gap-4 overflow-hidden rounded-2xl border border-[#2c77d1]/20 bg-[#050d1b] transition hover:border-[#2c77d1]"
      >
        <div className="relative h-48 w-48 shrink-0 bg-gradient-to-br from-[#2c77d1]/20 to-[#9426f4]/20">
          <ProductImage
            src={getProductImage(product)}
            alt={productTitle}
            className="h-full w-full object-cover"
          />
          {product.on_sale && (
            <div className="absolute right-3 top-3 rounded-full bg-[#9426f4] px-3 py-1 text-xs font-semibold text-white">
              Sale
            </div>
          )}
          <FavoriteButton className="absolute left-3 top-3 h-9 w-9" />
        </div>
        <div className="flex flex-1 flex-col justify-between p-4">
          <div>
            <h3 className="mb-2 text-lg font-semibold transition group-hover:text-[#2c77d1]">{productTitle}</h3>
            <p className="mb-3 line-clamp-2 text-sm text-gray-400">{product.description}</p>
            <ProductMeta />
          </div>
          <div>
            <div className="flex items-center justify-between gap-4">
              <div>
                <span className="text-2xl font-bold text-[#2c77d1]">{formatNaira(product.price)}</span>
                {product.old_price && (
                  <span className="ml-2 text-sm text-gray-400 line-through">{formatNaira(product.old_price)}</span>
                )}
              </div>
              <button
                type="button"
                onClick={handleAddToCart}
                disabled={isLoading || product.stock === 0}
                className="btn-primary"
              >
                <ShoppingBag className="h-4 w-4" />
                {isLoading ? 'Adding...' : 'Add to Cart'}
              </button>
            </div>
            {feedback && <p className="mt-2 text-sm text-[#7db4ff]">{feedback}</p>}
          </div>
        </div>
      </Link>
    );
  }

  return (
    <Link
      to={`/product/${product.slug}`}
      className="group flex h-full flex-col overflow-hidden rounded-2xl border border-[#2c77d1]/20 bg-[#050d1b] transition hover:border-[#2c77d1]"
    >
      <div className="relative aspect-square overflow-hidden bg-gradient-to-br from-[#2c77d1]/20 to-[#9426f4]/20">
        <ProductImage
          src={getProductImage(product)}
          alt={productTitle}
          className="h-full w-full object-cover transition duration-500 group-hover:scale-105"
        />
        {product.on_sale && (
          <div className="absolute right-3 top-3 rounded-full bg-[#9426f4] px-3 py-1 text-xs font-semibold text-white">
            Sale
          </div>
        )}
        <FavoriteButton className="absolute left-3 top-3 h-9 w-9" />
      </div>
      <div className="flex flex-1 flex-col p-4">
        <h3 className="mb-1 truncate text-lg font-semibold transition group-hover:text-[#2c77d1]">{productTitle}</h3>
        <ProductMeta />
        <div className="mt-auto flex items-center justify-between gap-3">
          <div className="min-w-0">
            <span className="block truncate text-xl font-bold text-[#2c77d1]">{formatNaira(product.price)}</span>
            {product.old_price && (
              <span className="text-xs text-gray-400 line-through">{formatNaira(product.old_price)}</span>
            )}
          </div>
          <button
            type="button"
            onClick={handleAddToCart}
            disabled={isLoading || product.stock === 0}
            className="btn-primary shrink-0 px-4"
          >
            {isLoading ? (
              <div className="h-4 w-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
            ) : (
              <>
                <ShoppingBag className="h-4 w-4 text-white" />
                Add
              </>
            )}
          </button>
        </div>
        {feedback && <p className="mt-2 text-xs text-[#7db4ff]">{feedback}</p>}
      </div>
    </Link>
  );
}
