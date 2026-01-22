import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Minus, Trash2, ShoppingBag, ArrowRight } from 'lucide-react';
import { useCart } from '../context/CartContext';

export default function Cart() {
  const navigate = useNavigate();
  const { cart, loading, updateQuantity, removeItem, cartTotal, cartCount } = useCart();

  const handleUpdateQuantity = async (itemId, currentQuantity, change) => {
    const newQuantity = currentQuantity + change;
    if (newQuantity > 0) {
      await updateQuantity(itemId, newQuantity);
    }
  };

  const handleRemoveItem = async (itemId) => {
    if (window.confirm('Are you sure you want to remove this item?')) {
      await removeItem(itemId);
    }
  };

  const handleCheckout = () => {
    navigate('/checkout');
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center pt-20">
        <div className="w-16 h-16 border-4 border-[#2c77d1] border-t-transparent rounded-full animate-spin"></div>
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
            <p className="text-gray-400 mb-8">Add some products to get started!</p>
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
        <h1 className="text-4xl font-bold mb-8">Shopping Cart</h1>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Cart Items */}
          <div className="lg:col-span-2 space-y-4">
            {cart.map((item) => (
              <div
                key={item.id}
                className="bg-[#050d1b] border border-[#2c77d1]/20 rounded-2xl p-6 flex gap-6"
              >
                <div className="w-32 h-32 bg-gradient-to-br from-[#2c77d1]/20 to-[#9426f4]/20 rounded-lg overflow-hidden shrink-0">
                  <img
                    src={item.product_image || '/placeholder.png'}
                    alt={item.product_name}
                    className="w-full h-full object-cover"
                  />
                </div>

                <div className="flex-1">
                  <div className="flex justify-between items-start mb-2">
                    <Link
                      to={`/product/${item.product_id}`}
                      className="text-xl font-semibold hover:text-[#2c77d1] transition"
                    >
                      {item.product_name}
                    </Link>
                    <button
                      onClick={() => handleRemoveItem(item.id)}
                      className="text-red-400 hover:text-red-300 transition p-2"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>

                  <p className="text-gray-400 text-sm mb-4">
                    {item.product_description}
                  </p>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center border border-[#2c77d1]/30 rounded-lg">
                      <button
                        onClick={() => handleUpdateQuantity(item.id, item.quantity, -1)}
                        disabled={item.quantity <= 1}
                        className="p-2 hover:bg-[#2c77d1]/10 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <Minus className="w-4 h-4" />
                      </button>
                      <span className="px-4 font-semibold">{item.quantity}</span>
                      <button
                        onClick={() => handleUpdateQuantity(item.id, item.quantity, 1)}
                        className="p-2 hover:bg-[#2c77d1]/10"
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
            ))}
          </div>

          {/* Order Summary */}
          <div className="lg:col-span-1">
            <div className="bg-[#050d1b] border border-[#2c77d1]/20 rounded-2xl p-6 sticky top-24">
              <h2 className="text-2xl font-bold mb-6">Order Summary</h2>

              <div className="space-y-4 mb-6">
                <div className="flex justify-between text-gray-300">
                  <span>Subtotal ({cartCount} items)</span>
                  <span>${cartTotal.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-gray-300">
                  <span>Shipping</span>
                  <span className="text-green-400">Free</span>
                </div>
                <div className="flex justify-between text-gray-300">
                  <span>Tax</span>
                  <span>${(cartTotal * 0.1).toFixed(2)}</span>
                </div>
                <div className="border-t border-[#2c77d1]/20 pt-4">
                  <div className="flex justify-between text-xl font-bold">
                    <span>Total</span>
                    <span className="text-[#2c77d1]">
                      ${(cartTotal * 1.1).toFixed(2)}
                    </span>
                  </div>
                </div>
              </div>

              <button
                onClick={handleCheckout}
                className="w-full bg-gradient-to-r from-[#2c77d1] to-[#9426f4] py-4 rounded-full font-semibold text-lg flex items-center justify-center gap-2 hover:opacity-90 transition mb-4"
              >
                Proceed to Checkout <ArrowRight className="w-5 h-5" />
              </button>

              <Link
                to="/shop"
                className="block text-center text-[#2c77d1] hover:text-[#9426f4] transition"
              >
                Continue Shopping
              </Link>

              {/* Promo Code */}
              <div className="mt-6 pt-6 border-t border-[#2c77d1]/20">
                <label className="block text-sm font-medium mb-2">
                  Have a promo code?
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Enter code"
                    className="flex-1 bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-2 focus:outline-none focus:border-[#2c77d1]"
                  />
                  <button className="bg-[#2c77d1] px-6 py-2 rounded-lg font-semibold hover:bg-[#2c77d1]/90 transition">
                    Apply
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}