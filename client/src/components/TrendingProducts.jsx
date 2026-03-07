import React, { useEffect, useState } from 'react';
import ProductCard from './products/ProductCard';
import { getTrendingProducts } from '../services/api';

export default function TrendingProducts() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    const loadTrending = async () => {
      try {
        setLoading(true);
        const response = await getTrendingProducts();
        const normalized = response?.results || response || [];
        if (isMounted) {
          setProducts(Array.isArray(normalized) ? normalized : []);
        }
      } catch (error) {
        console.error('Failed to load trending products:', error);
        if (isMounted) {
          setProducts([]);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    loadTrending();
    return () => {
      isMounted = false;
    };
  }, []);

  if (!loading && products.length === 0) {
    return null;
  }

  return (
    <section className="px-4 pb-8 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">🔥 Hot Demand</h2>
          {loading && <span className="text-sm text-gray-500 dark:text-gray-400">Loading...</span>}
        </div>

        <div className="flex gap-4 overflow-x-auto pb-2 snap-x snap-mandatory">
          {loading
            ? Array.from({ length: 4 }).map((_, idx) => (
                <div
                  key={`trend-skeleton-${idx}`}
                  className="min-w-[240px] sm:min-w-[260px] h-[340px] rounded-2xl border border-gray-200 dark:border-[#2c77d1]/20 bg-gray-100 dark:bg-[#0b1222] animate-pulse"
                />
              ))
            : products.map((product) => (
                <div key={product.id} className="min-w-[240px] sm:min-w-[260px] max-w-[260px] snap-start">
                  <ProductCard product={product} viewMode="grid" />
                </div>
              ))}
        </div>
      </div>
    </section>
  );
}
