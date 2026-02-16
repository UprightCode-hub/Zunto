import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Filter, X, Grid, List } from 'lucide-react';
import { getProducts, getCategories } from '../services/api';
import ProductCard from '../components/products/ProductCard';

export default function Shop() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterOpen, setFilterOpen] = useState(false);
  const [viewMode, setViewMode] = useState('grid');

  const [filters, setFilters] = useState({
    category: searchParams.get('category') || '',
    minPrice: searchParams.get('minPrice') || '',
    maxPrice: searchParams.get('maxPrice') || '',
    sort: searchParams.get('sort') || '-created_at',
    search: searchParams.get('search') || '',
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [productsData, categoriesData] = await Promise.all([
          getProducts(Object.fromEntries(searchParams)),
          getCategories(),
        ]);
        setProducts(productsData.results || productsData);
        setCategories(categoriesData.results || categoriesData);
      } catch (error) {
        console.error('Error fetching shop data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [searchParams]);

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const applyFilters = () => {
    const params = {};
    Object.entries(filters).forEach(([key, value]) => {
      if (value) {
        params[key] = value;
      }
    });
    setSearchParams(params);
    setFilterOpen(false);
  };

  const clearFilters = () => {
    const nextFilters = {
      category: '',
      minPrice: '',
      maxPrice: '',
      sort: '-created_at',
      search: '',
    };
    setFilters(nextFilters);
    setSearchParams({});
  };

  return (
    <div className="min-h-screen pt-20 pb-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold mb-2">Shop</h1>
            <p className="text-gray-400">{products.length} products found</p>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={() => setViewMode((mode) => (mode === 'grid' ? 'list' : 'grid'))}
              className="p-2 border border-[#2c77d1]/20 rounded-lg hover:border-[#2c77d1] transition"
            >
              {viewMode === 'grid' ? <List className="w-5 h-5" /> : <Grid className="w-5 h-5" />}
            </button>
            <button
              onClick={() => setFilterOpen((open) => !open)}
              className="lg:hidden flex items-center gap-2 bg-[#2c77d1] px-4 py-2 rounded-full hover:bg-[#2c77d1]/90 transition"
            >
              <Filter className="w-5 h-5" />
              Filters
            </button>
          </div>
        </div>

        <div className="flex gap-8">
          <aside className="hidden lg:block w-64 shrink-0">
            <div className="sticky top-24 bg-[#050d1b] border border-[#2c77d1]/20 rounded-2xl p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-bold">Filters</h3>
                <button onClick={clearFilters} className="text-sm text-[#2c77d1] hover:text-[#9426f4]">Clear All</button>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium mb-2">Search</label>
                <input
                  type="text"
                  value={filters.search}
                  onChange={(event) => handleFilterChange('search', event.target.value)}
                  placeholder="Search products..."
                  className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-2 focus:outline-none focus:border-[#2c77d1]"
                />
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium mb-2">Category</label>
                <select
                  value={filters.category}
                  onChange={(event) => handleFilterChange('category', event.target.value)}
                  className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-2 focus:outline-none focus:border-[#2c77d1]"
                >
                  <option value="">All Categories</option>
                  {categories.map((category) => (
                    <option key={category.id} value={category.id}>{category.name}</option>
                  ))}
                </select>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium mb-2">Sort By</label>
                <select
                  value={filters.sort}
                  onChange={(event) => handleFilterChange('sort', event.target.value)}
                  className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-2 focus:outline-none focus:border-[#2c77d1]"
                >
                  <option value="-created_at">Newest</option>
                  <option value="price">Price: Low to High</option>
                  <option value="-price">Price: High to Low</option>
                  <option value="-views_count">Most Viewed</option>
                </select>
              </div>

              <button
                onClick={applyFilters}
                className="w-full bg-gradient-to-r from-[#2c77d1] to-[#9426f4] py-3 rounded-full font-semibold hover:opacity-90 transition"
              >
                Apply Filters
              </button>
            </div>
          </aside>

          {filterOpen && (
            <div className="lg:hidden fixed inset-0 z-50 bg-black/50" onClick={() => setFilterOpen(false)}>
              <div className="absolute right-0 top-0 h-full w-80 bg-[#050d1b] p-6 overflow-y-auto" onClick={(event) => event.stopPropagation()}>
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-xl font-bold">Filters</h3>
                  <button onClick={() => setFilterOpen(false)}><X className="w-6 h-6" /></button>
                </div>
                <div className="space-y-6">
                  <input
                    type="text"
                    value={filters.search}
                    onChange={(event) => handleFilterChange('search', event.target.value)}
                    placeholder="Search products..."
                    className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-2 focus:outline-none focus:border-[#2c77d1]"
                  />
                  <select
                    value={filters.category}
                    onChange={(event) => handleFilterChange('category', event.target.value)}
                    className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-2 focus:outline-none focus:border-[#2c77d1]"
                  >
                    <option value="">All Categories</option>
                    {categories.map((category) => (
                      <option key={category.id} value={category.id}>{category.name}</option>
                    ))}
                  </select>
                  <button
                    onClick={applyFilters}
                    className="w-full bg-gradient-to-r from-[#2c77d1] to-[#9426f4] py-3 rounded-full font-semibold hover:opacity-90 transition"
                  >
                    Apply Filters
                  </button>
                </div>
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
                <p className="text-xl text-gray-400">No products found</p>
              </div>
            ) : (
              <div className={viewMode === 'grid' ? 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6' : 'space-y-4'}>
                {products.map((product) => (
                  <ProductCard key={product.id} product={product} viewMode={viewMode} />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
