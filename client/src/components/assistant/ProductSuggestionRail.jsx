import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, BadgeCheck, MapPin, Package } from 'lucide-react';

const formatPrice = (value) => {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return value ? `₦${value}` : 'Price on listing';
  }
  return `₦${numeric.toLocaleString('en-NG', { maximumFractionDigits: 0 })}`;
};

const humanize = (value) => String(value || '').replace(/_/g, ' ').trim();

export default function ProductSuggestionRail({ products = [], tone = 'light' }) {
  const items = Array.isArray(products) ? products.filter(Boolean).slice(0, 5) : [];
  if (!items.length) {
    return null;
  }

  const isDark = tone === 'dark';
  const shellClass = isDark
    ? 'border-white/10 bg-white/5 text-gray-100'
    : 'border-gray-200 bg-white text-gray-900 dark:border-white/10 dark:bg-white/5 dark:text-gray-100';
  const subtleText = isDark ? 'text-gray-400' : 'text-gray-500 dark:text-gray-400';
  const itemClass = isDark
    ? 'border-white/10 bg-[#101a31] hover:border-blue-300/50'
    : 'border-gray-200 bg-gray-50 hover:border-blue-300 dark:border-white/10 dark:bg-[#101a31] dark:hover:border-blue-300/50';
  const isAlternativeRail = items.every((product) => product.match_type === 'alternative');
  const railLabel = isAlternativeRail ? 'Alternative Products' : 'Suggested Products';
  const countLabel = isAlternativeRail ? `${items.length} alternatives` : `${items.length} shown`;

  return (
    <div className={`mt-3 rounded-lg border ${shellClass} p-3`}>
      <div className="mb-2 flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-500">
          {railLabel}
        </p>
        <span className={`text-xs ${subtleText}`}>{countLabel}</span>
      </div>

      <div className="grid gap-2 sm:grid-cols-2">
        {items.map((product) => (
          <Link
            key={product.id || product.slug || product.title}
            to={product.product_url || (product.slug ? `/product/${product.slug}` : '/products')}
            className={`group grid grid-cols-[64px_1fr] gap-3 rounded-lg border p-2 transition ${itemClass}`}
          >
            <div className="h-16 w-16 overflow-hidden rounded-md bg-gray-200 dark:bg-[#17233f]">
              {product.primary_image ? (
                <img
                  src={product.primary_image}
                  alt={product.title || 'Suggested product'}
                  className="h-full w-full object-cover"
                  loading="lazy"
                />
              ) : (
                <div className="flex h-full w-full items-center justify-center">
                  <Package className={`h-6 w-6 ${subtleText}`} />
                </div>
              )}
            </div>

            <div className="min-w-0">
              <div className="flex items-start justify-between gap-2">
                <p className="min-w-0 truncate text-sm font-semibold">
                  {product.title || 'Product'}
                </p>
                <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-blue-500 opacity-70 transition group-hover:translate-x-0.5 group-hover:opacity-100" />
              </div>

              <p className="mt-1 text-sm font-bold text-blue-500">
                {formatPrice(product.price)}
              </p>

              <div className={`mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs ${subtleText}`}>
                {product.match_type === 'alternative' && (
                  <span className="font-semibold text-amber-600 dark:text-amber-300">
                    Alternative
                  </span>
                )}
                {product.condition && <span>{humanize(product.condition)}</span>}
                {product.location && (
                  <span className="inline-flex min-w-0 items-center gap-1">
                    <MapPin className="h-3 w-3 shrink-0" />
                    <span className="truncate">{product.location}</span>
                  </span>
                )}
                {(product.is_verified || product.is_verified_product) && (
                  <span className="inline-flex items-center gap-1 text-emerald-500">
                    <BadgeCheck className="h-3 w-3" />
                    Verified
                  </span>
                )}
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
