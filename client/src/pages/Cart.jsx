import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ShoppingBag, ArrowRight, RefreshCw } from 'lucide-react';
import { useCart } from '../context/CartContext';
import CartItem from '../components/cart/CartItem';
import CartSummary from '../components/cart/CartSummary';

export default function Cart() {
  const navigate = useNavigate();
  const {
    cart,
    loading,
    error,
    fetchCart,
    updateQuantity,
    removeItem,
    clearCart,
    cartTotal,
    cartCount,
  } = useCart();

  const [busy, setBusy] = useState(false);

  const handleUpdateQuantity = async (itemId, quantity) => {
    if (quantity < 1) return;
    try {
      setBusy(true);
      await updateQuantity(itemId, quantity);
    } finally {
      setBusy(false);
    }
  };

  const handleRemoveItem = async (itemId) => {
    const confirmed = window.confirm('Are you sure you want to remove this item?');
    if (!confirmed) return;

    try {
      setBusy(true);
      await removeItem(itemId);
    } finally {
      setBusy(false);
    }
  };

  const handleClearCart = async () => {
    const confirmed = window.confirm('Clear your entire cart?');
    if (!confirmed) return;

    try {
      setBusy(true);
      await clearCart();
    } finally {
      setBusy(false);
    }
  };

  const handleCheckout = () => {
    navigate('/checkout');
  };

  if (loading && cart.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center pt-20">
        <div className="w-16 h-16 border-4 border-[#2c77d1] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (cart.length === 0) {
    return (
      <div className="min-h-screen pt-20 pb-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center py-20">
            <ShoppingBag className="w-24 h-24 mx-auto text-gray-600 mb-6" />
            <h2 className="text-3xl font-bold mb-4">Your cart is empty</h2>
            <p className="text-gray-400 mb-8">Add some products to get started.</p>
            <Link
              to="/shop"
              className="inline-flex items-center gap-2 bg-gradient-to-r from-[#2c77d1] to-[#9426f4] px-8 py-3 rounded-full font-semibold hover:opacity-90 transition"
            >
              Start Shopping <ArrowRight className="w-5 h-5" />
            </Link>
          </div>

        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-20 pb-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between gap-4 mb-8">
          <h1 className="text-4xl font-bold">Shopping Cart</h1>
          <button
            onClick={fetchCart}
            disabled={loading || busy}
            className="inline-flex items-center gap-2 border border-[#2c77d1]/30 rounded-lg px-4 py-2 hover:bg-[#2c77d1]/10 transition disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {error && (
          <div className="mb-6 rounded-lg border border-red-400/30 bg-red-500/10 text-red-200 px-4 py-3">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-4">
            {cart.map((item) => (
              <CartItem
                key={item.id}
                item={item}
                busy={busy}
                onUpdateQuantity={handleUpdateQuantity}
                onRemove={handleRemoveItem}
              />
            ))}
          </div>

          <div className="lg:col-span-1">
            <CartSummary
              cartCount={cartCount}
              cartTotal={cartTotal}
              busy={busy}
              onCheckout={handleCheckout}
              onClearCart={handleClearCart}
            />
          </div>
        </div>

      </div>
    </div>
  );
}
