import { useCallback, useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

const FILTER_KEYS = [
  'search',
  'category',
  'condition',
  'min_price',
  'max_price',
  'is_negotiable',
  'verified_product',
  'verified_seller',
  'ordering',
  'page',
];

const BOOLEAN_KEYS = ['is_negotiable', 'verified_product', 'verified_seller'];

const normalizeValue = (key, value) => {
  if (value === undefined || value === null) return null;

  if (BOOLEAN_KEYS.includes(key)) {
    if (typeof value === 'boolean') return value ? 'true' : 'false';
    const normalized = String(value).trim().toLowerCase();
    if (normalized === 'true' || normalized === 'false') return normalized;
    return null;
  }

  const normalized = String(value).trim();
  return normalized === '' ? null : normalized;
};

export default function useProductFilters() {
  const location = useLocation();
  const navigate = useNavigate();

  const parsedFilters = useMemo(() => {
    const params = new URLSearchParams(location.search);

    return FILTER_KEYS.reduce((acc, key) => {
      const value = params.get(key);
      acc[key] = value ?? '';
      return acc;
    }, {});
  }, [location.search]);

  const updateFilters = useCallback((newValues = {}) => {
    const params = new URLSearchParams(location.search);

    Object.entries(newValues).forEach(([key, value]) => {
      if (!FILTER_KEYS.includes(key)) return;
      const normalized = normalizeValue(key, value);
      if (normalized === null) {
        params.delete(key);
      } else {
        params.set(key, normalized);
      }
    });

    const queryString = params.toString();
    navigate(
      {
        pathname: location.pathname,
        search: queryString ? `?${queryString}` : '',
      },
      { replace: false },
    );
  }, [location.pathname, location.search, navigate]);

  const resetFilters = useCallback(() => {
    const params = new URLSearchParams(location.search);
    FILTER_KEYS.forEach((key) => params.delete(key));

    const queryString = params.toString();
    navigate(
      {
        pathname: location.pathname,
        search: queryString ? `?${queryString}` : '',
      },
      { replace: false },
    );
  }, [location.pathname, location.search, navigate]);

  return {
    parsedFilters,
    updateFilters,
    resetFilters,
  };
}

export { FILTER_KEYS };
