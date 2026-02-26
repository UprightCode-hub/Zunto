import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Filter, Grid, List, X } from 'lucide-react';
import { getCategories, getProducts } from '../../services/api';
import ProductCard from './ProductCard';

const ORDERING_OPTIONS = [
  { value: '-created_at', label: 'Newest' },
  { value: 'price', label: 'Price: Low to High' },
  { value: '-price', label: 'Price: High to Low' },
  { value: '-views_count', label: 'Most Viewed' },
];

const QUERY_KEYS = ['search', 'category', 'seller', 'verified_product', 'verified_seller', 'ordering'];

export default function ProductGrid({
  title = 'Products',
  description,
  defaultParams = {},
  showFilters = true,
  showHeader = true,
  initialViewMode = 'grid',
  limit,
}) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterOpen, setFilterOpen] = useState(false);
  const [viewMode, setViewMode] = useState(initialViewMode);

  const effectiveParams = useMemo(() => {
    const params = { ...defaultParams };
    QUERY_KEYS.forEach((key) => {
      const value = searchParams.get(key);
      if (value) {
        params[key] = value;
      }
    });
    return params;
  }, [defaultParams, searchParams]);

  const [filters, setFilters] = useState({
    search: effectiveParams.search || '',
    category: effectiveParams.category || '',
    seller: effectiveParams.seller || '',
    verified_product: effectiveParams.verified_product || '',
    verified_seller: effectiveParams.verified_seller || '',
    ordering: effectiveParams.ordering || '-created_at',
  });

  useEffect(() => {
    setFilters({
      search: effectiveParams.search || '',
      category: effectiveParams.category || '',
      seller: effectiveParams.seller || '',
      verified_product: effectiveParams.verified_product || '',
      verified_seller: effectiveParams.verified_seller || '',
      ordering: effectiveParams.ordering || '-created_at',
    });
  }, [effectiveParams]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [productsData, categoriesData] = await Promise.all([
          getProducts(effectiveParams),
          getCategories(),
        ]);
        const normalized = productsData.results || productsData || [];
        setProducts(limit ? normalized.slice(0, limit) : normalized);
        setCategories(categoriesData.results || categoriesData || []);
      } catch (error) {
        console.error('Error loading products:', error);
        setProducts([]);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [effectiveParams, limit]);

  useEffect(() => {
    if (!filterOpen) {
      document.body.style.overflow = '';
      return;
    }
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [filterOpen]);

  const updateFilters = (nextFilters) => {
    const nextParams = new URLSearchParams(searchParams);

    QUERY_KEYS.forEach((key) => {
      nextParams.delete(key);
    });

    Object.entries(defaultParams).forEach(([key, value]) => {
      if (value) {
        nextParams.set(key, value);
      }
    });

    Object.entries(nextFilters).forEach(([key, value]) => {
      if (value) {
        nextParams.set(key, value);
      }
    });

    setSearchParams(nextParams);
  };

  const applyFilters = () => {
    updateFilters(filters);
    setFilterOpen(false);
  };

  const clearFilters = () => {
    const reset = {
      search: '',
      category: '',
      seller: '',
      verified_product: '',
      verified_seller: '',
      ordering: '-created_at',
    };
    setFilters(reset);
    updateFilters(reset);
  };

  const renderFilters = () => (
    <>
      <div>
        <label className="block text-sm font-medium mb-2">Search</label>
        <input
          type="text"
          value={filters.search}
          onChange={(event) => setFilters((prev) => ({ ...prev, search: event.target.value }))}
          placeholder="Search products..."
          className="w-full bg-white dark:bg-[#050d1b] border border-gray-300 dark:border-[#2c77d1]/30 rounded-lg px-4 py-2 focus:outline-none focus:border-[#2c77d1]"
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Category</label>
        <select
          value={filters.category}
          onChange={(event) => setFilters((prev) => ({ ...prev, category: event.target.value }))}
          className="w-full bg-white dark:bg-[#050d1b] border border-gray-300 dark:border-[#2c77d1]/30 rounded-lg px-4 py-2 focus:outline-none focus:border-[#2c77d1]"
        >
          <option value="">All Categories</option>
          {categories.map((category) => (
            <option key={category.id} value={category.slug || category.id}>{category.name}</option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Ordering</label>
        <select
          value={filters.ordering}
          onChange={(event) => setFilters((prev) => ({ ...prev, ordering: event.target.value }))}
          className="w-full bg-white dark:bg-[#050d1b] border border-gray-300 dark:border-[#2c77d1]/30 rounded-lg px-4 py-2 focus:outline-none focus:border-[#2c77d1]"
        >
          {ORDERING_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Verified Product</label>
        <select
          value={filters.verified_product}
          onChange={(event) => setFilters((prev) => ({ ...prev, verified_product: event.target.value }))}
          className="w-full bg-white dark:bg-[#050d1b] border border-gray-300 dark:border-[#2c77d1]/30 rounded-lg px-4 py-2 focus:outline-none focus:border-[#2c77d1]"
        >
          <option value="">All</option>
          <option value="true">Verified only</option>
          <option value="false">Unverified only</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Verified Seller</label>
        <select
          value={filters.verified_seller}
          onChange={(event) => setFilters((prev) => ({ ...prev, verified_seller: event.target.value }))}
          className="w-full bg-white dark:bg-[#050d1b] border border-gray-300 dark:border-[#2c77d1]/30 rounded-lg px-4 py-2 focus:outline-none focus:border-[#2c77d1]"
        >
          <option value="">All</option>
          <option value="true">Verified only</option>
          <option value="false">Unverified only</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Seller ID</label>
        <input
          type="text"
          value={filters.seller}
          onChange={(event) => setFilters((prev) => ({ ...prev, seller: event.target.value }))}
          placeholder="Filter by seller UUID"
          className="w-full bg-white dark:bg-[#050d1b] border border-gray-300 dark:border-[#2c77d1]/30 rounded-lg px-4 py-2 focus:outline-none focus:border-[#2c77d1]"
        />
      </div>

      <button onClick={applyFilters} className="btn-primary w-full">Apply Filters</button>
    </>
  );

  return (
    <section className="w-full">
      {showHeader && (
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">{title}</h2>
            {description && <p className="text-gray-500 dark:text-gray-400 mt-1">{description}</p>}
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{products.length} products found</p>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setViewMode((mode) => (mode === 'grid' ? 'list' : 'grid'))}
              className="btn-icon-utility rounded-lg"
            >
              {viewMode === 'grid' ? <List className="w-5 h-5" /> : <Grid className="w-5 h-5" />}
            </button>
            {showFilters && (
              <button type="button" onClick={() => setFilterOpen((open) => !open)} className="btn-secondary lg:hidden">
                <Filter className="w-5 h-5" /> Filters
              </button>
            )}
          </div>
        </div>
      )}

      <div className="flex gap-8">
        {showFilters && (
          <aside className="hidden lg:block w-72 shrink-0">
            <div className="sticky top-24 rounded-2xl border border-gray-200 dark:border-[#2c77d1]/20 bg-white dark:bg-[#050d1b] p-6 space-y-5">
              <div className="flex items-center justify-between">
                <h3 className="text-xl font-bold">Filters</h3>
                <button type="button" onClick={clearFilters} className="text-sm text-[#2c77d1] hover:text-[#9426f4]">Clear</button>
              </div>
              {renderFilters()}
            </div>
          </aside>
        )}

        {showFilters && filterOpen && (
          <div className="lg:hidden fixed inset-0 z-50 bg-black/50" onClick={() => setFilterOpen(false)}>
            <div className="absolute right-0 top-0 h-full w-80 bg-white dark:bg-[#050d1b] p-6 overflow-y-auto" onClick={(event) => event.stopPropagation()}>
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-bold">Filters</h3>
                <button type="button" onClick={() => setFilterOpen(false)}><X className="w-6 h-6" /></button>
              </div>
              <div className="space-y-5">{renderFilters()}</div>
            </div>
          </div>
        )}

        <div className="flex-1">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="w-16 h-16 border-4 border-[#2c77d1] border-t-transparent rounded-full animate-spin" />
            </div>
          ) : products.length === 0 ? (
            <div className="text-center py-20">
              <p className="text-xl text-gray-500 dark:text-gray-400">No products found</p>
            </div>
          ) : (
            <div className={viewMode === 'grid' ? 'grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6' : 'space-y-4'}>
              {products.map((product) => (
                <ProductCard key={product.id} product={product} viewMode={viewMode} />
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
