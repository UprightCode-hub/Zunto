import React from 'react';
import { Link } from 'react-router-dom';
import { Plus, Minus, Trash2 } from 'lucide-react';

export default function CartItem({ item, busy, onUpdateQuantity, onRemove }) {
  const productSlug = item?.product?.slug || item?.product_id;

  return (
    <div className="bg-[#050d1b] border border-[#2c77d1]/20 rounded-2xl p-6 flex flex-col sm:flex-row gap-6">
      <Link
        to={productSlug ? `/product/${productSlug}` : '/shop'}
        className="w-full sm:w-32 h-40 sm:h-32 bg-gradient-to-br from-[#2c77d1]/20 to-[#9426f4]/20 rounded-lg overflow-hidden shrink-0"
      >
        <img
          src={item.product_image || '/placeholder.png'}
          alt={item.product_name}
          className="w-full h-full object-cover"
        />
      </Link>

      <div className="flex-1">
        <div className="flex justify-between items-start gap-2 mb-2">
          <Link
            to={productSlug ? `/product/${productSlug}` : '/shop'}
            className="text-lg sm:text-xl font-semibold hover:text-[#2c77d1] transition"
          >
            {item.product_name}
          </Link>
          <button
            onClick={() => onRemove(item.id)}
            disabled={busy}
            className="text-red-400 hover:text-red-300 transition p-2 disabled:opacity-50"
            aria-label={`Remove ${item.product_name}`}
          >
            <Trash2 className="w-5 h-5" />
          </button>
        </div>

        <p className="text-gray-400 text-sm mb-4 line-clamp-2">
          {item.product_description || 'No description available.'}
        </p>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center border border-[#2c77d1]/30 rounded-lg w-max">
            <button
              onClick={() => onUpdateQuantity(item.id, item.quantity - 1)}
              disabled={busy || item.quantity <= 1}
              className="p-2 hover:bg-[#2c77d1]/10 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              <Minus className="w-4 h-4" />
            </button>
            <span className="px-4 font-semibold">{item.quantity}</span>
            <button
              onClick={() => onUpdateQuantity(item.id, item.quantity + 1)}
              disabled={busy}
              className="p-2 hover:bg-[#2c77d1]/10 disabled:opacity-50 transition"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>

          <div className="text-right">
            <div className="text-2xl font-bold text-[#2c77d1]">${item.total_price.toFixed(2)}</div>
            <div className="text-sm text-gray-400">${item.unit_price.toFixed(2)} each</div>
          </div>
        </div>
      </div>
    </div>
  );
}
