import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Heart } from 'lucide-react';
import { getFavorites, toggleFavorite } from '../services/api';

export default function Favorites() {
  const [favorites, setFavorites] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadFavorites = async () => {
    try {
      setLoading(true);
      const data = await getFavorites();
      setFavorites(Array.isArray(data) ? data : data.results || []);
    } catch (error) {
      console.error('Error loading favorites:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFavorites();
  }, []);

  const handleRemove = async (slug) => {
    try {
      await toggleFavorite(slug);
      setFavorites((prev) => prev.filter((item) => item.product?.slug !== slug && item.slug !== slug));
    } catch (error) {
      console.error('Failed to remove favorite:', error);
    }
  };

  return (
    <div className="min-h-screen pt-20 pb-12">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 className="text-4xl font-bold mb-2">My Favorites</h1>
        <p className="text-gray-400 mb-8">Products you bookmarked for later.</p>

        {loading ? (
          <div className="py-12 text-center text-gray-400">Loading favorites...</div>
        ) : favorites.length === 0 ? (
          <div className="py-12 text-center bg-[#1a1a1a] rounded-2xl border border-[#2c77d1]/20">
            <Heart className="w-10 h-10 mx-auto mb-3 text-gray-500" />
            <p className="text-gray-300">No favorites yet.</p>
            <Link to="/shop" className="inline-block mt-4 text-[#2c77d1] hover:text-[#5aa5ff]">Browse products</Link>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {favorites.map((entry) => {
              const product = entry.product || entry;
              return (
                <div key={entry.id || product.id || product.slug} className="bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl p-5">
                  <h3 className="font-semibold text-lg mb-1">{product.title || product.name}</h3>
                  <p className="text-[#2c77d1] font-bold mb-4">₦{product.price}</p>
                  <div className="flex gap-3">
                    <Link to={`/product/${product.slug}`} className="px-4 py-2 rounded-lg bg-[#2c77d1]/20 text-[#2c77d1] hover:bg-[#2c77d1]/30">View</Link>
                    <button onClick={() => handleRemove(product.slug)} className="px-4 py-2 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20">
                      Remove
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
