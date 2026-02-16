import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CreditCard, Truck, MapPin, Lock } from 'lucide-react';
import { useCart } from '../context/CartContext';
import { checkout } from '../services/api';

export default function Checkout() {
  const navigate = useNavigate();
  const { cart, cartTotal, cartCount } = useCart();
  const [loading, setLoading] = useState(false);
  
  const [formData, setFormData] = useState({
    // Shipping Info
    firstName: '',
    lastName: '',
    email: '',
    phone: '',
    address: '',
    city: '',
    state: '',
    zipCode: '',
    country: '',
    
    // Payment Info
    cardNumber: '',
    cardName: '',
    expiryDate: '',
    cvv: '',
    
    // Order Notes
    notes: '',
  });

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      setLoading(true);
      
      const payload = {
        shipping_address: formData.address,
        shipping_city: formData.city,
        shipping_state: formData.state,
        shipping_country: formData.country || 'Nigeria',
        shipping_phone: formData.phone,
        shipping_email: formData.email,
        payment_method: 'cash_on_delivery',
        notes: formData.notes,
        save_address: false,
      };

      await checkout(payload);
      
      alert('Order placed successfully!');
      navigate('/profile?tab=orders');
    } catch {
      alert('Failed to place order. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (cart.length === 0) {
    navigate('/cart');
    return null;
  }

  return (
    <div className="min-h-screen pt-20 pb-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 className="text-4xl font-bold mb-8">Checkout</h1>

        <form onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Checkout Form */}
            <div className="lg:col-span-2 space-y-8">
              {/* Shipping Information */}
              <div className="bg-[#050d1b] border border-[#2c77d1]/20 rounded-2xl p-6">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 bg-gradient-to-r from-[#2c77d1] to-[#9426f4] rounded-full flex items-center justify-center">
                    <Truck className="w-5 h-5" />
                  </div>
                  <h2 className="text-2xl font-bold">Shipping Information</h2>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">First Name *</label>
                    <input
                      type="text"
                      name="firstName"
                      value={formData.firstName}
                      onChange={handleChange}
                      required
                      className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-3 focus:outline-none focus:border-[#2c77d1]"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Last Name *</label>
                    <input
                      type="text"
                      name="lastName"
                      value={formData.lastName}
                      onChange={handleChange}
                      required
                      className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-3 focus:outline-none focus:border-[#2c77d1]"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Email *</label>
                    <input
                      type="email"
                      name="email"
                      value={formData.email}
                      onChange={handleChange}
                      required
                      className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-3 focus:outline-none focus:border-[#2c77d1]"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Phone *</label>
                    <input
                      type="tel"
                      name="phone"
                      value={formData.phone}
                      onChange={handleChange}
                      required
                      className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-3 focus:outline-none focus:border-[#2c77d1]"
                    />
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium mb-2">Address *</label>
                    <input
                      type="text"
                      name="address"
                      value={formData.address}
                      onChange={handleChange}
                      required
                      className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-3 focus:outline-none focus:border-[#2c77d1]"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">City *</label>
                    <input
                      type="text"
                      name="city"
                      value={formData.city}
                      onChange={handleChange}
                      required
                      className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-3 focus:outline-none focus:border-[#2c77d1]"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">State *</label>
                    <input
                      type="text"
                      name="state"
                      value={formData.state}
                      onChange={handleChange}
                      required
                      className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-3 focus:outline-none focus:border-[#2c77d1]"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">ZIP Code *</label>
                    <input
                      type="text"
                      name="zipCode"
                      value={formData.zipCode}
                      onChange={handleChange}
                      required
                      className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-3 focus:outline-none focus:border-[#2c77d1]"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Country *</label>
                    <input
                      type="text"
                      name="country"
                      value={formData.country}
                      onChange={handleChange}
                      required
                      className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-3 focus:outline-none focus:border-[#2c77d1]"
                    />
                  </div>
                </div>
              </div>

              {/* Payment Information */}
              <div className="bg-[#050d1b] border border-[#2c77d1]/20 rounded-2xl p-6">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 bg-gradient-to-r from-[#2c77d1] to-[#9426f4] rounded-full flex items-center justify-center">
                    <CreditCard className="w-5 h-5" />
                  </div>
                  <h2 className="text-2xl font-bold">Payment Information</h2>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Card Number *</label>
                    <input
                      type="text"
                      name="cardNumber"
                      value={formData.cardNumber}
                      onChange={handleChange}
                      placeholder="1234 5678 9012 3456"
                      required
                      maxLength="19"
                      className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-3 focus:outline-none focus:border-[#2c77d1]"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Cardholder Name *</label>
                    <input
                      type="text"
                      name="cardName"
                      value={formData.cardName}
                      onChange={handleChange}
                      required
                      className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-3 focus:outline-none focus:border-[#2c77d1]"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-2">Expiry Date *</label>
                      <input
                        type="text"
                        name="expiryDate"
                        value={formData.expiryDate}
                        onChange={handleChange}
                        placeholder="MM/YY"
                        required
                        maxLength="5"
                        className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-3 focus:outline-none focus:border-[#2c77d1]"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-2">CVV *</label>
                      <input
                        type="text"
                        name="cvv"
                        value={formData.cvv}
                        onChange={handleChange}
                        placeholder="123"
                        required
                        maxLength="4"
                        className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-3 focus:outline-none focus:border-[#2c77d1]"
                      />
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 mt-4 text-sm text-gray-400">
                  <Lock className="w-4 h-4" />
                  <span>Your payment information is secure and encrypted</span>
                </div>
              </div>

              {/* Order Notes */}
              <div className="bg-[#050d1b] border border-[#2c77d1]/20 rounded-2xl p-6">
                <h3 className="font-semibold mb-4">Order Notes (Optional)</h3>
                <textarea
                  name="notes"
                  value={formData.notes}
                  onChange={handleChange}
                  rows="4"
                  placeholder="Any special instructions for your order..."
                  className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-3 focus:outline-none focus:border-[#2c77d1] resize-none"
                />
              </div>
            </div>

            {/* Order Summary */}
            <div className="lg:col-span-1">
              <div className="bg-[#050d1b] border border-[#2c77d1]/20 rounded-2xl p-6 sticky top-24">
                <h2 className="text-2xl font-bold mb-6">Order Summary</h2>

                <div className="space-y-4 mb-6">
                  {cart.map((item) => (
                    <div key={item.id} className="flex gap-3">
                      <div className="w-16 h-16 bg-gradient-to-br from-[#2c77d1]/20 to-[#9426f4]/20 rounded-lg overflow-hidden shrink-0">
                        <img
                          src={item.product?.primary_image || '/placeholder.png'}
                          alt={item.product?.title || 'Product'}
                          className="w-full h-full object-cover"
                        />
                      </div>
                      <div className="flex-1">
                        <p className="font-medium text-sm">{item.product?.title}</p>
                        <p className="text-xs text-gray-400">Qty: {item.quantity}</p>
                        <p className="text-sm text-[#2c77d1] font-semibold">
                          ${(Number(item.price_at_addition) * item.quantity).toFixed(2)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="space-y-3 border-t border-[#2c77d1]/20 pt-4">
                  <div className="flex justify-between text-gray-300">
                    <span>Subtotal ({cartCount} items)</span>
                    <span>${cartTotal.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-gray-300">
                    <span>Shipping</span>
                    <span className="text-green-400">Free</span>
                  </div>
                  <div className="flex justify-between text-gray-300">
                    <span>Tax (10%)</span>
                    <span>${(cartTotal * 0.1).toFixed(2)}</span>
                  </div>
                  <div className="border-t border-[#2c77d1]/20 pt-3">
                    <div className="flex justify-between text-xl font-bold">
                      <span>Total</span>
                      <span className="text-[#2c77d1]">
                        ${(cartTotal * 1.1).toFixed(2)}
                      </span>
                    </div>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-gradient-to-r from-[#2c77d1] to-[#9426f4] py-4 rounded-full font-semibold text-lg mt-6 hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? 'Processing...' : 'Place Order'}
                </button>
              </div>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
