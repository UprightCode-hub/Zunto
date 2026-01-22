import React from 'react';
import { Link } from 'react-router-dom';
import { Plus, Minus, Trash2 } from 'lucide-react';

export default function CartItem({ item, onUpdateQuantity, onRemove }) {
  return (
    <div className="bg-[#050d1b] border border-[#2c77d1]/20 rounded-2xl p-6 flex gap-6">
      <Link 
        to={`/product/${item.product_id}`}
        className="w-32 h-32 bg-gradient-to-br from-[#2c77d1]/20 to-[#9426f4]/20 rounded-lg overflow-hidden shrink-0"
      >
        <img
          src={item.product_image || '/placeholder.png'}
          alt={item.product_name}
          className="w-full h-full object-cover"
        />
      </Link>

      <div className="flex-1">
        <div className="flex justify-between items-start mb-2">
          <Link
            to={`/product/${item.product_id}`}
            className="text-xl font-semibold hover:text-[#2c77d1] transition"
          >
            {item.product_name}
          </Link>
          <button
            onClick={() => onRemove(item.id)}
            className="text-red-400 hover:text-red-300 transition p-2"
          >
            <Trash2 className="w-5 h-5" />
          </button>
        </div>

        <p className="text-gray-400 text-sm mb-4 line-clamp-2">
          {item.product_description}
        </p>

        <div className="flex items-center justify-between">
          <div className="flex items-center border border-[#2c77d1]/30 rounded-lg">
            <button
              onClick={() => onUpdateQuantity(item.id, item.quantity - 1)}
              disabled={item.quantity <= 1}
              className="p-2 hover:bg-[#2c77d1]/10 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              <Minus className="w-4 h-4" />
            </button>
            <span className="px-4 font-semibold">{item.quantity}</span>
            <button
              onClick={() => onUpdateQuantity(item.id, item.quantity + 1)}
              className="p-2 hover:bg-[#2c77d1]/10 transition"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>

          <div className="text-right">
            <div className="text-2xl font-bold text-[#2c77d1]">
              ${(item.price * item.quantity).toFixed(2)}
            </div>
            <div className="text-sm text-gray-400">
              ${item.price} each
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}