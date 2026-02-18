import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';

const SHIPPING_THRESHOLD = 100;
const SHIPPING_FEE = 8.99;
const TAX_RATE = 0.1;

export default function CartSummary({ cartCount, cartTotal, busy, onCheckout, onClearCart }) {
  const hasFreeShipping = cartTotal >= SHIPPING_THRESHOLD;
  const shipping = hasFreeShipping ? 0 : SHIPPING_FEE;
  const tax = cartTotal * TAX_RATE;
  const grandTotal = cartTotal + shipping + tax;
  const remainingForFreeShipping = Math.max(0, SHIPPING_THRESHOLD - cartTotal);

  return (
    <div className="bg-[#050d1b] border border-[#2c77d1]/20 rounded-2xl p-6 sticky top-24">
      <h2 className="text-2xl font-bold mb-6">Order Summary</h2>

      {!hasFreeShipping && cartTotal > 0 && (
        <p className="text-sm text-amber-300 bg-amber-500/10 border border-amber-400/20 rounded-lg px-3 py-2 mb-4">
          Add ${remainingForFreeShipping.toFixed(2)} more for free shipping.
        </p>
      )}

      <div className="space-y-4 mb-6">
        <div className="flex justify-between text-gray-300">
          <span>Subtotal ({cartCount} items)</span>
          <span>${cartTotal.toFixed(2)}</span>
        </div>
        <div className="flex justify-between text-gray-300">
          <span>Shipping</span>
          <span className={hasFreeShipping ? 'text-green-400' : 'text-gray-300'}>
            {hasFreeShipping ? 'Free' : `$${shipping.toFixed(2)}`}
          </span>
        </div>
        <div className="flex justify-between text-gray-300">
          <span>Tax</span>
          <span>${tax.toFixed(2)}</span>
        </div>
        <div className="border-t border-[#2c77d1]/20 pt-4">
          <div className="flex justify-between text-xl font-bold">
            <span>Total</span>
            <span className="text-[#2c77d1]">${grandTotal.toFixed(2)}</span>
          </div>
        </div>
      </div>

      <button
        onClick={onCheckout}
        disabled={busy}
        className="w-full bg-gradient-to-r from-[#2c77d1] to-[#9426f4] py-4 rounded-full font-semibold text-lg flex items-center justify-center gap-2 hover:opacity-90 transition mb-4 disabled:opacity-60"
      >
        Proceed to Checkout <ArrowRight className="w-5 h-5" />
      </button>

      <div className="space-y-3">
        <Link
          to="/shop"
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
