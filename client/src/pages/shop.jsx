import React from 'react';
import ProductGrid from '../components/products/ProductGrid';

export default function Shop() {
  return (
    <div className="min-h-screen pb-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <ProductGrid
          title="Products"
          description="Expanded marketplace view with full query-driven filtering."
          showFilters
          showHeader
        />
      </div>
    </div>
  );
}
