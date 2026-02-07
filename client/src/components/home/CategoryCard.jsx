import React from 'react';
import { Link } from 'react-router-dom';

export default function CategoryCard({ category }) {
  return (
    <Link
      to={`/shop?category=${category.id}`}
      className="bg-gradient-to-br from-[#2c77d1]/10 to-[#9426f4]/10 border border-[#2c77d1]/20 rounded-2xl p-6 hover:border-[#2c77d1] transition cursor-pointer group"
    >
      <div className="text-5xl mb-3 group-hover:scale-110 transition">
        {category.icon || '📦'}
      </div>
      <h3 className="font-semibold text-lg mb-1">{category.name}</h3>
      <p className="text-gray-400 text-sm">
        {category.product_count || 0} products
      </p>
    </Link>
  );
}