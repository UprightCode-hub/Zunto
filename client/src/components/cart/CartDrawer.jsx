import React from 'react';
import { X } from 'lucide-react';
import CartItem from './CartItem';
import CartSummary from './CartSummary';

export default function CartDrawer({
  isOpen,
  onClose,
  cart,
  cartCount,
  cartTotal,
  busy,
  onUpdateQuantity,
  onRemove,
  onCheckout,
  onClearCart,
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button className="absolute inset-0 bg-black/60" onClick={onClose} aria-label="Close cart drawer" />
      <div className="relative w-full max-w-2xl h-full bg-[#050d1b] border-l border-[#2c77d1]/20 overflow-y-auto p-4 sm:p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold">Your Cart ({cartCount})</h2>
          <button onClick={onClose} className="p-2 rounded-full hover:bg-white/10 transition" aria-label="Close drawer">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-4">
          {cart.map((item) => (
            <CartItem
              key={item.id}
              item={item}
              busy={busy}
              onUpdateQuantity={onUpdateQuantity}
              onRemove={onRemove}
            />
          ))}
        </div>

        <div className="mt-6">
          <CartSummary
            cartCount={cartCount}
            cartTotal={cartTotal}
            busy={busy}
            onCheckout={onCheckout}
            onClearCart={onClearCart}
          />
        </div>
      </div>
    </div>
  );
}
