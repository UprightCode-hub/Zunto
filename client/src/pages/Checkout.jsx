import React, { useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { CreditCard, Truck, Lock } from 'lucide-react';
import { useCart } from '../context/CartContext';
import { checkout, initializeOrderPayment } from '../services/api';
import { formatNaira } from '../utils/helpers';
import ProductImage from '../components/products/ProductImage';
import { getProductImage } from '../utils/product';

const panelClass = 'bg-[#0b1222] border border-[#2c77d1]/20 rounded-2xl p-6 shadow-sm shadow-black/20';
const fieldClass = 'w-full bg-[#111827] border border-[#2c77d1]/30 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-[#2c77d1] focus:ring-1 focus:ring-[#2c77d1] [color-scheme:dark]';
const textAreaClass = `${fieldClass} resize-none`;

export default function Checkout() {
  const navigate = useNavigate();
  const { cart, cartTotal, cartCount } = useCart();
  const [loading, setLoading] = useState(false);
  const [paymentRedirecting, setPaymentRedirecting] = useState(false);
  const [checkoutFeedback, setCheckoutFeedback] = useState(null);
  
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
    country: 'Nigeria',
    
    // Payment Info
    paymentMethod: 'paystack',
    
    // Order Notes
    notes: '',
  });
  const blockedItems = cart.filter((item) => !item.is_managed_commerce_eligible);
  const blockedSellerNames = [...new Set(blockedItems.map((item) => item.seller_name).filter(Boolean))];
  const isCheckoutBlocked = blockedSellerNames.length > 0;

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setCheckoutFeedback(null);

    if (isCheckoutBlocked) {
      setCheckoutFeedback({
        type: 'error',
        message: `Zunto checkout works only for managed sellers. Remove items from: ${blockedSellerNames.join(', ')}.`,
      });
      return;
    }

    const selectedPaymentMethod = formData.paymentMethod || 'paystack';

    try {
      setLoading(true);

      const payload = {
        shipping_address: formData.address,
        shipping_city: formData.city,
        shipping_state: formData.state,
        shipping_country: formData.country || 'Nigeria',
        shipping_phone: formData.phone,
        shipping_email: formData.email,
        shipping_postal_code: formData.zipCode,
        shipping_full_name: `${formData.firstName} ${formData.lastName}`.trim(),
        payment_method: selectedPaymentMethod,
        notes: formData.notes,
        save_address: false,
      };

      const response = await checkout(payload);
      const orderNumber = response?.order?.order_number;

      if (selectedPaymentMethod === 'paystack') {
        if (!orderNumber) {
          throw new Error('Order was created but order number is missing.');
        }

        setPaymentRedirecting(true);
        const callbackUrl = `${window.location.origin}/payment/verify/${orderNumber}/`;
        const checkoutAuthorizationUrl = response?.payment_data?.authorization_url;
        const initialized = checkoutAuthorizationUrl
          ? null
          : await initializeOrderPayment(orderNumber, callbackUrl);
        const authorizationUrl = checkoutAuthorizationUrl || initialized?.data?.authorization_url;

        if (!authorizationUrl) {
          throw new Error('Payment initialized, but authorization URL was not returned.');
        }

        window.location.href = authorizationUrl;
        return;
      }

      if (orderNumber) {
        navigate(`/orders/${orderNumber}`);
      } else {
        navigate('/orders');
      }
    } catch (error) {
      const blockedSellers = error?.data?.blocked_sellers;
      if (Array.isArray(blockedSellers) && blockedSellers.length > 0) {
        const names = blockedSellers.map((seller) => seller.seller_name).join(', ');
        setCheckoutFeedback({
          type: 'error',
          message: `This cart contains direct/unverified sellers (${names}). Zunto checkout works only for managed sellers.`,
        });
      } else {
        setCheckoutFeedback({
          type: 'error',
          message: error?.data?.error || error?.data?.detail || error?.message || 'Failed to place order. Please try again.',
        });
      }
      setPaymentRedirecting(false);
    } finally {
      setLoading(false);
    }
  };

  if (cart.length === 0) {
    return <Navigate to="/cart" replace />;
  }

  return (
    <div className="min-h-screen bg-[#050d1b] pb-12 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 className="text-4xl font-bold mb-8">Checkout</h1>

        {isCheckoutBlocked && (
          <div className="mb-6 rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-red-200">
            Zunto checkout is unavailable for items from: {blockedSellerNames.join(', ')}. Remove those items from your cart and contact the seller directly in chat.
          </div>
        )}

        {checkoutFeedback && (
          <div className={`mb-6 rounded-xl border px-4 py-3 ${
            checkoutFeedback.type === 'error'
              ? 'border-red-400/30 bg-red-500/10 text-red-200'
              : 'border-green-400/30 bg-green-500/10 text-green-200'
          }`}>
            {checkoutFeedback.message}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Checkout Form */}
            <div className="lg:col-span-2 space-y-8">
              {/* Shipping Information */}
              <div className={panelClass}>
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
                      className={fieldClass}
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
                      className={fieldClass}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Email *</label>
                    <input
                      type="text"
                      inputMode="email"
                      name="email"
                      value={formData.email}
                      onChange={handleChange}
                      required
                      className={fieldClass}
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
                      className={fieldClass}
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
                      className={fieldClass}
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
                      className={fieldClass}
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
                      className={fieldClass}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Postal Code</label>
                    <input
                      type="text"
                      name="zipCode"
                      value={formData.zipCode}
                      onChange={handleChange}
                      className={fieldClass}
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
                      className={fieldClass}
                    />
                  </div>
                </div>
              </div>

              {/* Payment Information */}
              <div className={panelClass}>
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 bg-gradient-to-r from-[#2c77d1] to-[#9426f4] rounded-full flex items-center justify-center">
                    <CreditCard className="w-5 h-5" />
                  </div>
                  <h2 className="text-2xl font-bold">Payment Information</h2>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Payment Method *</label>
                    <select
                      name="paymentMethod"
                      value={formData.paymentMethod}
                      onChange={handleChange}
                      className={fieldClass}
                    >
                      <option value="paystack">Paystack (Card/Bank Transfer)</option>
                      <option value="cash_on_delivery">Cash on Delivery</option>
                    </select>
                  </div>

                  {formData.paymentMethod === 'paystack' ? (
                    <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">
                      You will be redirected to Paystack to complete payment by card, bank transfer, or USSD.
                    </div>
                  ) : (
                    <div className="rounded-lg border border-blue-500/30 bg-blue-500/10 p-3 text-sm text-blue-100">
                      Pay the seller when your order is delivered. No card details are collected on this page.
                    </div>
                  )}
                  <div className="flex items-center gap-2 mt-4 text-sm text-gray-400">
                    <Lock className="w-4 h-4" />
                    <span>Your payment information is secure and encrypted</span>
                  </div>
                </div>
              </div>

              {/* Order Notes */}
              <div className={panelClass}>
                <h3 className="font-semibold mb-4">Order Notes (Optional)</h3>
                <textarea
                  name="notes"
                  value={formData.notes}
                  onChange={handleChange}
                  rows="4"
                  placeholder="Any special instructions for your order..."
                  className={textAreaClass}
                />
              </div>
            </div>

            {/* Order Summary */}
            <div className="lg:col-span-1">
              <div className="bg-[#0b1222] border border-[#2c77d1]/20 rounded-2xl p-6 sticky top-24 shadow-sm shadow-black/20">
                <h2 className="text-2xl font-bold mb-6">Order Summary</h2>

                <div className="space-y-4 mb-6">
                  {cart.map((item) => (
                    <div key={item.id} className="flex gap-3">
                      <div className="w-16 h-16 bg-gradient-to-br from-[#2c77d1]/20 to-[#9426f4]/20 rounded-lg overflow-hidden shrink-0">
                        <ProductImage
                          src={getProductImage(item.product, item.product_image)}
                          alt={item.product?.title || 'Product'}
                          className="w-full h-full object-cover"
                        />
                      </div>
                      <div className="flex-1">
                        <p className="font-medium text-sm">{item.product?.title}</p>
                        <p className="text-xs text-gray-400">Qty: {item.quantity}</p>
                        <p className="text-sm text-[#2c77d1] font-semibold">
                          {formatNaira(Number(item.price_at_addition) * Number(item.quantity || 0))}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="space-y-3 border-t border-[#2c77d1]/20 pt-4">
                  <div className="flex justify-between text-gray-300">
                    <span>Subtotal ({cartCount} items)</span>
                    <span>{formatNaira(cartTotal)}</span>
                  </div>
                  <div className="flex justify-between text-gray-300">
                    <span>Delivery</span>
                    <span className="text-gray-400">Confirmed at checkout</span>
                  </div>
                  <div className="flex justify-between text-gray-300">
                    <span>Tax</span>
                    <span>{formatNaira(0)}</span>
                  </div>
                  <div className="border-t border-[#2c77d1]/20 pt-3">
                    <div className="flex justify-between text-xl font-bold">
                      <span>Total</span>
                      <span className="text-[#2c77d1]">
                        {formatNaira(cartTotal)}
                      </span>
                    </div>
                  </div>
                </div>

                {(paymentRedirecting || (loading && formData.paymentMethod === 'paystack')) && (
                  <p className="mt-4 text-sm text-amber-300 border border-amber-500/30 bg-amber-500/10 rounded-lg px-3 py-2">
                    Do not refresh or close this page while payment is processing.
                  </p>
                )}

                <button
                  type="submit"
                  disabled={loading || isCheckoutBlocked}
                  className="w-full bg-gradient-to-r from-[#2c77d1] to-[#9426f4] py-4 rounded-full font-semibold text-lg mt-6 hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isCheckoutBlocked
                    ? 'Checkout Unavailable'
                    : loading
                      ? (formData.paymentMethod === 'paystack' ? 'Redirecting to Paystack...' : 'Processing...')
                      : (formData.paymentMethod === 'paystack' ? 'Continue to Paystack' : 'Place Order')}
                </button>
              </div>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
