import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { formatNaira } from '../../utils/helpers';

export default function CartSummary({
  cartCount,
  cartTotal,
  busy,
  onCheckout,
  onClearCart,
  blockedSellerNames = [],
  checkoutDisabledReason = '',
}) {
  const isCheckoutBlocked = blockedSellerNames.length > 0;

  return (
    <div className="bg-[#050d1b] border border-[#2c77d1]/20 rounded-2xl p-6 sticky top-24">
      <h2 className="text-2xl font-bold mb-6">Order Summary</h2>

      {isCheckoutBlocked && (
        <p className="text-sm text-red-200 bg-red-500/10 border border-red-400/20 rounded-lg px-3 py-2 mb-4">
          {checkoutDisabledReason || `Checkout is unavailable for items from: ${blockedSellerNames.join(', ')}.`}
        </p>
      )}

      <div className="space-y-4 mb-6">
        <div className="flex justify-between text-gray-300">
          <span>Subtotal ({cartCount} items)</span>
          <span>{formatNaira(cartTotal)}</span>
        </div>
        <div className="flex justify-between text-gray-300">
          <span>Delivery</span>
          <span className="text-gray-400">Calculated at checkout</span>
        </div>
        <div className="border-t border-[#2c77d1]/20 pt-4">
          <div className="flex justify-between text-xl font-bold">
            <span>Total</span>
            <span className="text-[#2c77d1]">{formatNaira(cartTotal)}</span>
          </div>
        </div>
      </div>

      <button
        onClick={onCheckout}
        disabled={busy || isCheckoutBlocked}
        className="w-full bg-gradient-to-r from-[#2c77d1] to-[#9426f4] py-4 rounded-full font-semibold text-lg flex items-center justify-center gap-2 hover:opacity-90 transition mb-4 disabled:opacity-60"
      >
        {isCheckoutBlocked ? 'Checkout Unavailable' : 'Proceed to Checkout'} <ArrowRight className="w-5 h-5" />
      </button>

      <div className="space-y-3">
        <Link
          to="/products"
          className="block text-center text-[#2c77d1] hover:text-[#9426f4] transition"
        >
          Continue Shopping
        </Link>
        <button
          onClick={onClearCart}
          disabled={busy || cartCount === 0}
          className="w-full text-red-300 border border-red-400/30 rounded-lg py-2 hover:bg-red-500/10 transition disabled:opacity-50"
        >
          Clear cart
        </button>
      </div>
    </div>
  );
}
