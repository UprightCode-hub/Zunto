import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Filter, Grid, List, X } from 'lucide-react';
import { getCategories, getProducts, getSearchSuggestions, logDemandGap, translateSearchQuery } from '../../services/api';
import useProductFilters from '../../hooks/useProductFilters';
import ProductCard from './ProductCard';

const ORDERING_OPTIONS = [
  { value: '', label: 'Default (Newest)' },
  { value: '-created_at', label: 'Newest' },
  { value: 'created_at', label: 'Oldest' },
  { value: 'price', label: 'Price: Low to High' },
  { value: '-price', label: 'Price: High to Low' },
  { value: '-views_count', label: 'Most Viewed' },
  { value: '-favorites_count', label: 'Most Favorited' },
];

const AI_FILTER_KEYS = [
  'search',
  'category',
  'condition',
  'min_price',
  'max_price',
  'is_negotiable',
  'verified_product',
  'verified_seller',
  'ordering',
];

const AI_TRIGGER_KEYWORDS = [
  'under',
  'below',
  'above',
  'more than',
  'less than',
  'used',
  'new',
  'negotiable',
  'verified',
  'in ',
];

const shouldTranslateWithAI = (query) => {
  const trimmed = (query || '').trim().toLowerCase();
  if (!trimmed) return false;

  if (trimmed.split(/\s+/).length >= 3) return true;
  if (/(\d|\bk\b|000)/i.test(trimmed)) return true;
  return AI_TRIGGER_KEYWORDS.some((keyword) => trimmed.includes(keyword));
};

function ProductFilters({
  filters,
  categories,
  onSearchChange,
  onImmediateChange,
  onReset,
  suggestions = [],
  showSuggestions = false,
  onSuggestionClick,
}) {
  return (
    <div className="space-y-4">
      <div className="relative">
        <label className="block text-sm font-medium mb-2">Search</label>
        <input
          type="text"
          value={filters.search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Search products..."
          className="w-full bg-white dark:bg-[#050d1b] border border-gray-300 dark:border-[#2c77d1]/30 rounded-lg px-4 py-2 focus:outline-none focus:border-[#2c77d1]"
        />
        {showSuggestions && suggestions.length > 0 && (
          <div className="absolute z-20 mt-1 w-full bg-white dark:bg-[#050d1b] border border-gray-200 dark:border-[#2c77d1]/30 rounded-lg shadow-lg overflow-hidden">
            {suggestions.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                onClick={() => onSuggestionClick?.(suggestion)}
                className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-[#0a1f3d]"
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Category</label>
        <select
          value={filters.category}
          onChange={(event) => onImmediateChange('category', event.target.value)}
          className="w-full bg-white dark:bg-[#050d1b] border border-gray-300 dark:border-[#2c77d1]/30 rounded-lg px-4 py-2 focus:outline-none focus:border-[#2c77d1]"
        >
          <option value="">All Categories</option>
          {categories.map((category) => (
            <option key={category.id} value={category.slug || category.id}>{category.name}</option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Condition</label>
        <select
          value={filters.condition}
          onChange={(event) => onImmediateChange('condition', event.target.value)}
          className="w-full bg-white dark:bg-[#050d1b] border border-gray-300 dark:border-[#2c77d1]/30 rounded-lg px-4 py-2 focus:outline-none focus:border-[#2c77d1]"
        >
          <option value="">All Conditions</option>
          <option value="new">New</option>
          <option value="used">Used</option>
        </select>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium mb-2">Min Price</label>
          <input
            type="number"
            value={filters.min_price}
            onChange={(event) => onImmediateChange('min_price', event.target.value)}
            placeholder="0"
            min="0"
            className="w-full bg-white dark:bg-[#050d1b] border border-gray-300 dark:border-[#2c77d1]/30 rounded-lg px-4 py-2 focus:outline-none focus:border-[#2c77d1]"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-2">Max Price</label>
          <input
            type="number"
            value={filters.max_price}
            onChange={(event) => onImmediateChange('max_price', event.target.value)}
            placeholder="500000"
            min="0"
            className="w-full bg-white dark:bg-[#050d1b] border border-gray-300 dark:border-[#2c77d1]/30 rounded-lg px-4 py-2 focus:outline-none focus:border-[#2c77d1]"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Sorting</label>
        <select
          value={filters.ordering}
          onChange={(event) => onImmediateChange('ordering', event.target.value)}
          className="w-full bg-white dark:bg-[#050d1b] border border-gray-300 dark:border-[#2c77d1]/30 rounded-lg px-4 py-2 focus:outline-none focus:border-[#2c77d1]"
        >
          {ORDERING_OPTIONS.map((option) => (
            <option key={option.value || 'default'} value={option.value}>{option.label}</option>
          ))}
        </select>
      </div>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={filters.is_negotiable === 'true'}
          onChange={(event) => onImmediateChange('is_negotiable', event.target.checked ? 'true' : '')}
          className="rounded border-gray-400"
        />
        Negotiable only
      </label>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={filters.verified_product === 'true'}
          onChange={(event) => onImmediateChange('verified_product', event.target.checked ? 'true' : '')}
          className="rounded border-gray-400"
        />
        Verified product only
      </label>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={filters.verified_seller === 'true'}
          onChange={(event) => onImmediateChange('verified_seller', event.target.checked ? 'true' : '')}
          className="rounded border-gray-400"
        />
        Verified seller only
      </label>

      <button type="button" onClick={onReset} className="w-full btn-secondary">Reset Filters</button>
    </div>
  );
}

export default function ProductGrid({
  title = 'Products',
  description,
  showFilters = true,
  showHeader = true,
  initialViewMode = 'grid',
  limit,
}) {
  const location = useLocation();
  const { parsedFilters, updateFilters, resetFilters } = useProductFilters();
  const [productsResponse, setProductsResponse] = useState({ count: 0, next: null, previous: null, results: [] });
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isDesktop, setIsDesktop] = useState(false);
  const [isMobileFilterOpen, setIsMobileFilterOpen] = useState(false);
  const [viewMode, setViewMode] = useState(initialViewMode);
  const [searchDraft, setSearchDraft] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const lastAiAppliedFiltersRef = useRef({});
  const loggedZeroResultSearchesRef = useRef(new Set());

  useEffect(() => {
    const mediaQuery = window.matchMedia('(min-width: 1024px)');
    const apply = () => setIsDesktop(mediaQuery.matches);
    apply();

    mediaQuery.addEventListener('change', apply);
    return () => mediaQuery.removeEventListener('change', apply);
  }, []);

  useEffect(() => {
    if (isDesktop) {
      setIsMobileFilterOpen(false);
    }
  }, [isDesktop]);

  const effectiveFilters = useMemo(() => {
    const merged = {};

    Object.entries(parsedFilters).forEach(([key, value]) => {
      if (value) {
        merged[key] = value;
      }
    });

    return merged;
  }, [parsedFilters]);

  const normalizedFilters = useMemo(() => ({
    search: parsedFilters.search || '',
    category: parsedFilters.category || '',
    condition: parsedFilters.condition || '',
    min_price: parsedFilters.min_price || '',
    max_price: parsedFilters.max_price || '',
    is_negotiable: parsedFilters.is_negotiable || '',
    verified_product: parsedFilters.verified_product || '',
    verified_seller: parsedFilters.verified_seller || '',
    ordering: parsedFilters.ordering || '',
    page: parsedFilters.page || '',
  }), [parsedFilters]);

  useEffect(() => {
    setSearchDraft(normalizedFilters.search);
  }, [normalizedFilters.search]);

  useEffect(() => {
    const query = searchDraft.trim();
    if (query.length < 2) {
      setSuggestions([]);
      setShowSuggestions(false);
      return undefined;
    }

    const timeoutId = window.setTimeout(async () => {
      try {
        const response = await getSearchSuggestions(query);
        const nextSuggestions = response?.suggestions || [];
        setSuggestions(nextSuggestions);
        setShowSuggestions(nextSuggestions.length > 0);
      } catch {
        setSuggestions([]);
        setShowSuggestions(false);
      }
    }, 220);

    return () => window.clearTimeout(timeoutId);
  }, [searchDraft]);

  const handleSuggestionSelect = (value) => {
    const normalizedValue = String(value || '').trim();
    if (!normalizedValue) return;

    setSearchDraft(normalizedValue);
    setShowSuggestions(false);
    updateFilters({ search: normalizedValue, page: '1' });
  };

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      const runSearchUpdate = async () => {
        const trimmedSearch = searchDraft.trim();
        const normalizedSearch = (normalizedFilters.search || '').trim();

        if (trimmedSearch === normalizedSearch) return;

        const fallbackUpdate = {
          search: trimmedSearch,
          page: '1',
        };

        if (!shouldTranslateWithAI(trimmedSearch)) {
          updateFilters(fallbackUpdate);
          return;
        }

        try {
          const response = await translateSearchQuery(trimmedSearch);
          const aiFilters = response?.filters;
          const confidence = Number(response?.confidence ?? 0);

          if (!aiFilters || Number.isNaN(confidence) || confidence < 0.5) {
            updateFilters(fallbackUpdate);
            return;
          }

          const previousAiFilters = lastAiAppliedFiltersRef.current || {};
          const mergedUpdate = {
            search: typeof aiFilters.search === 'string' ? aiFilters.search : trimmedSearch,
            page: '1',
          };

          AI_FILTER_KEYS.forEach((key) => {
            if (key === 'search') return;
            const incomingValue = aiFilters[key];
            const nextValue = incomingValue === undefined || incomingValue === null ? '' : String(incomingValue);
            const currentValue = parsedFilters[key] || '';
            const previousAiValue = previousAiFilters[key] || '';
            const isManuallySet = Boolean(currentValue) && currentValue !== previousAiValue;

            if (isManuallySet) {
              return;
            }

            mergedUpdate[key] = nextValue;
          });

          lastAiAppliedFiltersRef.current = AI_FILTER_KEYS.reduce((acc, key) => {
            if (key === 'search') return acc;
            acc[key] = mergedUpdate[key] || '';
            return acc;
          }, {});

          updateFilters(mergedUpdate);
        } catch {
          updateFilters(fallbackUpdate);
        }
      };

      runSearchUpdate();
    }, 300);

    return () => window.clearTimeout(timeoutId);
  }, [searchDraft, normalizedFilters.search, parsedFilters, updateFilters]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [productsData, categoriesData] = await Promise.all([
          getProducts(effectiveFilters),
          getCategories(),
        ]);

        const normalizedResults = productsData?.results || productsData || [];
        setProductsResponse({
          count: productsData?.count ?? normalizedResults.length,
          next: productsData?.next ?? null,
          previous: productsData?.previous ?? null,
          results: limit ? normalizedResults.slice(0, limit) : normalizedResults,
        });
        setCategories(categoriesData?.results || categoriesData || []);
      } catch (error) {
        console.error('Error loading products:', error);
        setProductsResponse({ count: 0, next: null, previous: null, results: [] });
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [location.search]);


  useEffect(() => {
    if (loading) return;
    if (!normalizedFilters.search) return;
    if (productsResponse.count !== 0) return;

    const searchKey = location.search || `search=${normalizedFilters.search}`;
    if (loggedZeroResultSearchesRef.current.has(searchKey)) {
      return;
    }
    loggedZeroResultSearchesRef.current.add(searchKey);

    void logDemandGap({
      rawQuery: normalizedFilters.search,
      filters: effectiveFilters,
      source: 'grid_search',
    }).catch((error) => {
      console.warn('Demand-gap logging failed:', error);
    });
  }, [effectiveFilters, loading, location.search, normalizedFilters.search, productsResponse.count]);

  const applyImmediateFilterChange = (key, value) => {
    updateFilters({
      [key]: value,
      page: '1',
    });
  };

  const handlePageChange = (nextPage) => {
    if (!nextPage || nextPage < 1) return;
    updateFilters({ page: String(nextPage) });
  };

  const currentPage = Number(normalizedFilters.page || '1');

  return (
    <section className="w-full">
      {showHeader && (
        <div className="flex items-center justify-between mb-6 gap-4">
          <div>
            <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">{title}</h2>
            {description && <p className="text-gray-500 dark:text-gray-400 mt-1">{description}</p>}
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{productsResponse.count} products found</p>
          </div>

          <button
            type="button"
            onClick={() => setViewMode((mode) => (mode === 'grid' ? 'list' : 'grid'))}
            className="btn-icon-utility rounded-lg"
          >
            {viewMode === 'grid' ? <List className="w-5 h-5" /> : <Grid className="w-5 h-5" />}
          </button>
        </div>
      )}

      {showFilters && !isDesktop && (
        <div className="mb-4">
          <button type="button" onClick={() => setIsMobileFilterOpen(true)} className="btn-secondary">
            <Filter className="w-5 h-5" /> Filter
          </button>
        </div>
      )}

      <div className="flex gap-8 items-start">
        {showFilters && isDesktop && (
          <aside className="w-[300px] shrink-0">
            <div className="sticky top-24 rounded-2xl border border-gray-200 dark:border-[#2c77d1]/20 bg-white dark:bg-[#050d1b] p-6">
              <h3 className="text-xl font-bold mb-5">Filters</h3>
              <ProductFilters
                filters={{ ...normalizedFilters, search: searchDraft }}
                categories={categories}
                onSearchChange={setSearchDraft}
                suggestions={suggestions}
                showSuggestions={showSuggestions}
                onSuggestionClick={handleSuggestionSelect}
                onImmediateChange={applyImmediateFilterChange}
                onReset={resetFilters}
              />
            </div>
          </aside>
        )}

        <div className="flex-1">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="w-16 h-16 border-4 border-[#2c77d1] border-t-transparent rounded-full animate-spin" />
            </div>
          ) : productsResponse.results.length === 0 ? (
            <div className="text-center py-20">
              <p className="text-xl text-gray-500 dark:text-gray-400">No products found</p>
            </div>
          ) : (
            <>
              <div className={viewMode === 'grid' ? 'grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6' : 'space-y-4'}>
                {productsResponse.results.map((product) => (
                  <ProductCard key={product.id} product={product} viewMode={viewMode} />
                ))}
              </div>

              {!limit && (
                <div className="mt-8 flex items-center justify-between gap-4">
                  <button
                    type="button"
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={!productsResponse.previous || currentPage <= 1}
                    className="btn-secondary disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Page {currentPage}</p>
                  <button
                    type="button"
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={!productsResponse.next}
                    className="btn-secondary disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {showFilters && isMobileFilterOpen && (
        <div className="fixed inset-0 z-50 bg-black/50" onClick={() => setIsMobileFilterOpen(false)}>
          <div
            className="absolute bottom-0 left-0 right-0 rounded-t-2xl bg-white dark:bg-[#050d1b] p-6 max-h-[82vh] overflow-y-auto"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-xl font-bold">Filters</h3>
              <button type="button" onClick={() => setIsMobileFilterOpen(false)}><X className="w-6 h-6" /></button>
            </div>

            <ProductFilters
              filters={{ ...normalizedFilters, search: searchDraft }}
              categories={categories}
              onSearchChange={setSearchDraft}
              suggestions={suggestions}
              showSuggestions={showSuggestions}
              onSuggestionClick={handleSuggestionSelect}
              onImmediateChange={applyImmediateFilterChange}
              onReset={resetFilters}
            />
          </div>
        </div>
      )}
    </section>
  );
}
