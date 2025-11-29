import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Star, ShoppingBag, Heart } from 'lucide-react';
import { useCart } from '../../context/CartContext';

export default function ProductCard({ product, viewMode = 'grid' }) {
  const { addToCart } = useCart();
  const [isLoading, setIsLoading] = useState(false);
  const [isFavorite, setIsFavorite] = useState(false);

  const handleAddToCart = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    try {
      setIsLoading(true);
      await addToCart(product.id, 1);
      alert('Added to cart!');
    } catch (error) {
      alert('Failed to add to cart');
    } finally {
      setIsLoading(false);
    }
  };

  const toggleFavorite = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsFavorite(!isFavorite);
  };

  if (viewMode === 'list') {
    return (
      <Link
        to={`/product/${product.id}`}
        className="bg-[#050d1b] border border-[#2c77d1]/20 rounded-2xl overflow-hidden hover:border-[#2c77d1] transition group flex gap-4"
      >
        <div className="relative bg-gradient-to-br from-[#2c77d1]/20 to-[#9426f4]/20 w-48 h-48 shrink-0">
          <img
            src={product.image || '/placeholder.png'}
            alt={product.name}
            className="w-full h-full object-cover"
          />
          {product.on_sale && (
            <div className="absolute top-3 right-3 bg-[#9426f4] text-white text-xs px-3 py-1 rounded-full font-semibold">
              Sale
            </div>
          )}
          <button
            onClick={toggleFavorite}
            className="absolute top-3 left-3 w-8 h-8 bg-black/50 backdrop-blur-sm rounded-full flex items-center justify-center hover:bg-black/70 transition"
          >
            <Heart className={`w-4 h-4 ${isFavorite ? 'fill-red-500 text-red-500' : 'text-white'}`} />
          </button>
        </div>
        <div className="p-4 flex-1 flex flex-col justify-between">
          <div>
            <h3 className="font-semibold text-lg mb-2 group-hover:text-[#2c77d1] transition">
              {product.name}
            </h3>
            <p className="text-gray-400 text-sm mb-3 line-clamp-2">
              {product.description}
            </p>
            <div className="flex items-center gap-2 mb-3">
              <div className="flex items-center gap-1 text-yellow-400">
                <Star className="w-4 h-4 fill-current" />
                <span className="text-sm text-white">{product.rating || 4.5}</span>
              </div>
              <span className="text-gray-400 text-sm">
                ({product.reviews_count || 0} reviews)
              </span>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <span className="text-2xl font-bold text-[#2c77d1]">
                ${product.price}
              </span>
              {product.old_price && (
                <span className="text-gray-400 text-sm line-through ml-2">
                  ${product.old_price}
                </span>
              )}
            </div>
            <button
              onClick={handleAddToCart}
              disabled={isLoading || product.stock === 0}
              className="bg-gradient-to-r from-[#2c77d1] to-[#9426f4] px-4 py-2 rounded-full text-sm font-semibold hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Adding...' : 'Add to Cart'}
            </button>
          </div>
        </div>
      </Link>
    );
  }

  return (
    <Link
      to={`/product/${product.id}`}
      className="bg-[#050d1b] border border-[#2c77d1]/20 rounded-2xl overflow-hidden hover:border-[#2c77d1] transition group"
    >
      <div className="relative bg-gradient-to-br from-[#2c77d1]/20 to-[#9426f4]/20 aspect-square">
        <img
          src={product.image || '/placeholder.png'}
          alt={product.name}
          className="w-full h-full object-cover"
        />
        {product.on_sale && (
          <div className="absolute top-3 right-3 bg-[#9426f4] text-white text-xs px-3 py-1 rounded-full font-semibold">
            Sale
          </div>
        )}
        <button
          onClick={toggleFavorite}
          className="absolute top-3 left-3 w-8 h-8 bg-black/50 backdrop-blur-sm rounded-full flex items-center justify-center hover:bg-black/70 transition"
        >
          <Heart className={`w-4 h-4 ${isFavorite ? 'fill-red-500 text-red-500' : 'text-white'}`} />
        </button>
      </div>
      <div className="p-4">
        <h3 className="font-semibold text-lg mb-2 group-hover:text-[#2c77d1] transition line-clamp-1">
          {product.name}
        </h3>
        <p className="text-gray-400 text-sm mb-3 line-clamp-2">
          {product.description}
        </p>
        <div className="flex items-center gap-2 mb-3">
          <div className="flex items-center gap-1 text-yellow-400">
            <Star className="w-4 h-4 fill-current" />
            <span className="text-sm text-white">{product.rating || 4.5}</span>
          </div>
          <span className="text-gray-400 text-sm">
            ({product.reviews_count || 0})
          </span>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <span className="text-2xl font-bold text-[#2c77d1]">
              ${product.price}
            </span>
            {product.old_price && (
              <span className="text-gray-400 text-sm line-through ml-2">
                ${product.old_price}
              </span>
            )}
          </div>
          <button
            onClick={handleAddToCart}
            disabled={isLoading || product.stock === 0}
            className="p-2 bg-gradient-to-r from-[#2c77d1] to-[#9426f4] rounded-full hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ShoppingBag className="w-5 h-5" />
          </button>
        </div>
      </div>
    </Link>
  );
}