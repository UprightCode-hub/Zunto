import React, { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Filter, X, Star, ShoppingBag, Grid, List } from 'lucide-react';
import { getProducts, getCategories } from '../services/api';

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
    sort: searchParams.get('sort') || 'name',
    search: searchParams.get('search') || '',
  });

  useEffect(() => {
    fetchData();
  }, [searchParams]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [productsData, categoriesData] = await Promise.all([
        getProducts(Object.fromEntries(searchParams)),
        getCategories()
      ]);
      setProducts(productsData.results || productsData);
      setCategories(categoriesData.results || categoriesData);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const applyFilters = () => {
    const params = {};
    Object.keys(filters).forEach(key => {
      if (filters[key]) params[key] = filters[key];
    });
    setSearchParams(params);
    setFilterOpen(false);
  };

  const clearFilters = () => {
    setFilters({
      category: '',
      minPrice: '',
      maxPrice: '',
      sort: 'name',
      search: '',
    });
    setSearchParams({});
  };

  return (
    <div className="min-h-screen pt-20 pb-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold mb-2">Shop</h1>
            <p className="text-gray-400">
              {products.length} products found
            </p>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={() => setViewMode(viewMode === 'grid' ? 'list' : 'grid')}
              className="p-2 border border-[#2c77d1]/20 rounded-lg hover:border-[#2c77d1] transition"
            >
              {viewMode === 'grid' ? <List className="w-5 h-5" /> : <Grid className="w-5 h-5" />}
            </button>
            <button
              onClick={() => setFilterOpen(!filterOpen)}
              className="lg:hidden flex items-center gap-2 bg-[#2c77d1] px-4 py-2 rounded-full hover:bg-[#2c77d1]/90 transition"
            >
              <Filter className="w-5 h-5" />
              Filters
            </button>
          </div>
        </div>

        <div className="flex gap-8">
          {/* Sidebar Filters - Desktop */}
          <aside className="hidden lg:block w-64 shrink-0">
            <div className="sticky top-24 bg-[#050d1b] border border-[#2c77d1]/20 rounded-2xl p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-bold">Filters</h3>
                <button
                  onClick={clearFilters}
                  className="text-sm text-[#2c77d1] hover:text-[#9426f4]"
                >
                  Clear All
                </button>
              </div>

              {/* Search */}
              <div className="mb-6">
                <label className="block text-sm font-medium mb-2">Search</label>
                <input
                  type="text"
                  value={filters.search}
                  onChange={(e) => handleFilterChange('search', e.target.value)}
                  placeholder="Search products..."
                  className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-2 focus:outline-none focus:border-[#2c77d1]"
                />
              </div>

              {/* Categories */}
              <div className="mb-6">
                <label className="block text-sm font-medium mb-2">Category</label>
                <select
                  value={filters.category}
                  onChange={(e) => handleFilterChange('category', e.target.value)}
                  className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-2 focus:outline-none focus:border-[#2c77d1]"
                >
                  <option value="">All Categories</option>
                  {categories.map(cat => (
                    <option key={cat.id} value={cat.id}>{cat.name}</option>
                  ))}
                </select>
              </div>

              {/* Price Range */}
              <div className="mb-6">
                <label className="block text-sm font-medium mb-2">Price Range</label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    value={filters.minPrice}
                    onChange={(e) => handleFilterChange('minPrice', e.target.value)}
                    placeholder="Min"
                    className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-2 focus:outline-none focus:border-[#2c77d1]"
                  />
                  <input
                    type="number"
                    value={filters.maxPrice}
                    onChange={(e) => handleFilterChange('maxPrice', e.target.value)}
                    placeholder="Max"
                    className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-2 focus:outline-none focus:border-[#2c77d1]"
                  />
                </div>
              </div>

              {/* Sort */}
              <div className="mb-6">
                <label className="block text-sm font-medium mb-2">Sort By</label>
                <select
                  value={filters.sort}
                  onChange={(e) => handleFilterChange('sort', e.target.value)}
                  className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-2 focus:outline-none focus:border-[#2c77d1]"
                >
                  <option value="name">Name</option>
                  <option value="price_low">Price: Low to High</option>
                  <option value="price_high">Price: High to Low</option>
                  <option value="rating">Rating</option>
                  <option value="newest">Newest</option>
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

          {/* Mobile Filter Drawer */}
          {filterOpen && (
            <div className="lg:hidden fixed inset-0 z-50 bg-black/50" onClick={() => setFilterOpen(false)}>
              <div className="absolute right-0 top-0 h-full w-80 bg-[#050d1b] p-6 overflow-y-auto" onClick={e => e.stopPropagation()}>
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-xl font-bold">Filters</h3>
                  <button onClick={() => setFilterOpen(false)}>
                    <X className="w-6 h-6" />
                  </button>
                </div>
                {/* Same filter content as desktop */}
                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium mb-2">Search</label>
                    <input
                      type="text"
                      value={filters.search}
                      onChange={(e) => handleFilterChange('search', e.target.value)}
                      placeholder="Search products..."
                      className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-2 focus:outline-none focus:border-[#2c77d1]"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Category</label>
                    <select
                      value={filters.category}
                      onChange={(e) => handleFilterChange('category', e.target.value)}
                      className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-2 focus:outline-none focus:border-[#2c77d1]"
                    >
                      <option value="">All Categories</option>
                      {categories.map(cat => (
                        <option key={cat.id} value={cat.id}>{cat.name}</option>
                      ))}
                    </select>
                  </div>
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

          {/* Products Grid/List */}
          <div className="flex-1">
            {loading ? (
              <div className="flex items-center justify-center py-20">
                <div className="w-16 h-16 border-4 border-[#2c77d1] border-t-transparent rounded-full animate-spin"></div>
              </div>
            ) : products.length === 0 ? (
              <div className="text-center py-20">
                <p className="text-xl text-gray-400">No products found</p>
              </div>
            ) : (
              <div className={viewMode === 'grid' ? 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6' : 'space-y-4'}>
                {products.map((product) => (
                  <Link
                    key={product.id}
                    to={`/product/${product.id}`}
                    className={`bg-[#050d1b] border border-[#2c77d1]/20 rounded-2xl overflow-hidden hover:border-[#2c77d1] transition group ${
                      viewMode === 'list' ? 'flex gap-4' : ''
                    }`}
                  >
                    <div className={`relative bg-gradient-to-br from-[#2c77d1]/20 to-[#9426f4]/20 ${
                      viewMode === 'grid' ? 'aspect-square' : 'w-48 h-48'
                    }`}>
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
                    </div>
                    <div className="p-4 flex-1">
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
                        <ShoppingBag className="w-5 h-5 text-[#9426f4] group-hover:scale-110 transition" />
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}