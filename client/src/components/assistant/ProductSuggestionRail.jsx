import React from 'react';
import { Link } from 'react-router-dom';
import { BadgeCheck, MapPin } from 'lucide-react';
import { getProductImage } from '../../utils/product';
import ProductImage from '../products/ProductImage';

const formatPrice = (value) => {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return value ? `\u20A6${value}` : 'Price on listing';
  }
  return `\u20A6${numeric.toLocaleString('en-NG', { maximumFractionDigits: 0 })}`;
};

const humanize = (value) => String(value || '')
  .replace(/_/g, ' ')
  .trim()
  .replace(/\b\w/g, (char) => char.toUpperCase());

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
    ? 'border-white/10 bg-[#101a31]'
    : 'border-gray-200 bg-gray-50 dark:border-white/10 dark:bg-[#101a31]';
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

      <div className="grid gap-3 md:grid-cols-2">
        {items.map((product) => (
          <article
            key={product.id || product.slug || product.title}
            className={`grid min-h-[132px] grid-cols-[92px_minmax(0,1fr)] gap-3 rounded-lg border p-3 ${itemClass}`}
          >
            <div className="h-24 w-[92px] overflow-hidden rounded-md bg-gray-200 dark:bg-[#17233f]">
              <ProductImage
                src={getProductImage(product)}
                alt={product.title || 'Suggested product'}
                className="h-full w-full object-cover"
              />
            </div>

            <div className="min-w-0 self-center">
              <p className="min-w-0 break-words text-sm font-semibold leading-snug">
                {product.title || product.name || 'Product'}
              </p>

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

              <Link
                to={product.product_url || (product.slug ? `/product/${product.slug}` : '/products')}
                className="mt-3 inline-flex min-h-9 items-center justify-center rounded-md bg-gradient-to-r from-[#2c77d1] to-[#9426f4] px-3 py-1.5 text-xs font-semibold text-white transition hover:opacity-90"
              >
                View Product
              </Link>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
