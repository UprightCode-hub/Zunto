import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Package, RefreshCw } from 'lucide-react';
import { cancelOrder, getOrderDetail, initializeOrderPayment, reorder } from '../services/api';

const STATUS_STYLES = {
  pending: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
  paid: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  processing: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30',
  shipped: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
  delivered: 'bg-green-500/10 text-green-400 border-green-500/30',
  cancelled: 'bg-red-500/10 text-red-400 border-red-500/30',
};

export default function OrderDetail() {
  const { orderNumber } = useParams();
  const navigate = useNavigate();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState('');
  const [error, setError] = useState('');

  const loadOrder = async () => {
    try {
      setLoading(true);
      const data = await getOrderDetail(orderNumber);
      setOrder(data);
      setError('');
    } catch (apiError) {
      setError(apiError?.data?.detail || apiError?.data?.error || 'Failed to load order details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOrder();
  }, [orderNumber]);

  const handleCancel = async () => {
    if (!window.confirm('Cancel this order?')) return;
    try {
      setBusyAction('cancel');
      await cancelOrder(orderNumber);
      await loadOrder();
    } catch (apiError) {
      alert(apiError?.data?.detail || apiError?.data?.error || 'Failed to cancel order.');
    } finally {
      setBusyAction('');
    }
  };

  const handleReorder = async () => {
    try {
      setBusyAction('reorder');
      await reorder(orderNumber);
      navigate('/cart');
    } catch (apiError) {
      alert(apiError?.data?.detail || apiError?.data?.error || 'Failed to reorder items.');
    } finally {
      setBusyAction('');
    }
  };

  const handlePayNow = async () => {
    try {
      setBusyAction('pay');
      const callbackUrl = `${window.location.origin}/payment/verify/${orderNumber}/`;
      const response = await initializeOrderPayment(orderNumber, callbackUrl);
      const authUrl = response?.data?.authorization_url;
      if (authUrl) {
        window.location.href = authUrl;
        return;
      }
      alert('Payment initialized, but authorization URL was not returned.');
    } catch (apiError) {
      alert(apiError?.data?.detail || apiError?.data?.error || 'Unable to initialize payment.');
    } finally {
      setBusyAction('');
    }
  };

  if (loading) {
    return <div className="min-h-screen pt-24 text-center text-gray-400">Loading order...</div>;
  }

  if (!order) {
    return <div className="min-h-screen pt-24 text-center text-red-400">{error || 'Order not found.'}</div>;
  }

  return (
    <div className="min-h-screen pt-20 pb-12">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-6">
          <Link to="/orders" className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white">
            <ArrowLeft className="w-4 h-4" /> Back to Orders
          </Link>
        </div>

        <div className="bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl p-6 mb-6">
          <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
            <div>
              <h1 className="text-3xl font-bold">Order #{order.order_number}</h1>
              <p className="text-gray-400 text-sm mt-1">Placed on {new Date(order.created_at).toLocaleString()}</p>
            </div>
            <div className="flex gap-2 items-center">
              <span className={`px-3 py-1 rounded-full border text-sm font-semibold ${STATUS_STYLES[order.status] || STATUS_STYLES.pending}`}>
                {order.status}
              </span>
              <span className="px-3 py-1 rounded-full border text-sm font-semibold bg-[#2c77d1]/10 border-[#2c77d1]/30 text-[#2c77d1]">
                Payment: {order.payment_status}
              </span>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-6 text-sm">
            <div>
              <h3 className="font-semibold mb-2">Shipping</h3>
              <p className="text-gray-300">{order.shipping_address || 'No shipping address recorded'}</p>
              <p className="text-gray-400">{order.shipping_city} {order.shipping_state} {order.shipping_country}</p>
              <p className="text-gray-400">{order.shipping_phone || order.shipping_email}</p>
            </div>
            <div>
              <h3 className="font-semibold mb-2">Payment & Fulfillment Mode</h3>
              <p className="text-gray-300">{order.is_managed_commerce ? 'Managed by Zunto' : 'Direct seller transaction'}</p>
              <p className="text-gray-400">Method: {order.payment_method}</p>
              {order.payment_reference && <p className="text-gray-500">Ref: {order.payment_reference}</p>}
            </div>
          </div>
        </div>

        <div className="bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl p-6 mb-6">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2"><Package className="w-5 h-5" /> Items</h2>
          <div className="space-y-3">
            {(order.items || []).map((item) => (
              <div key={item.id} className="flex justify-between items-start gap-4 border-b border-[#2c77d1]/10 pb-3 last:border-b-0">
                <div>
                  <p className="font-medium">{item.product_name}</p>
                  <p className="text-sm text-gray-400">Qty: {item.quantity}</p>
                </div>
                <p className="font-semibold">₦{Number(item.total_price).toFixed(2)}</p>
              </div>
            ))}
          </div>

          <div className="mt-5 pt-4 border-t border-[#2c77d1]/20 space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-gray-400">Subtotal</span><span>₦{Number(order.subtotal || 0).toFixed(2)}</span></div>
            <div className="flex justify-between"><span className="text-gray-400">Shipping</span><span>₦{Number(order.shipping_fee || 0).toFixed(2)}</span></div>
            <div className="flex justify-between font-bold text-lg"><span>Total</span><span className="text-[#2c77d1]">₦{Number(order.total_amount || 0).toFixed(2)}</span></div>
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          {order.can_cancel && (
            <button onClick={handleCancel} disabled={busyAction === 'cancel'} className="px-5 py-2 rounded-lg bg-red-500/10 text-red-400 border border-red-500/30">
              {busyAction === 'cancel' ? 'Cancelling...' : 'Cancel Order'}
            </button>
          )}

          <button onClick={handleReorder} disabled={busyAction === 'reorder'} className="px-5 py-2 rounded-lg bg-[#2c77d1]/10 text-[#2c77d1] border border-[#2c77d1]/30 inline-flex items-center gap-2">
            <RefreshCw className="w-4 h-4" />
            {busyAction === 'reorder' ? 'Reordering...' : 'Reorder Items'}
          </button>

          {order.is_managed_commerce && order.payment_status !== 'paid' && (
            <button onClick={handlePayNow} disabled={busyAction === 'pay'} className="px-5 py-2 rounded-lg bg-green-500/10 text-green-400 border border-green-500/30">
              {busyAction === 'pay' ? 'Redirecting...' : 'Pay Now'}
            </button>
          )}

          {order.is_managed_commerce && (
            <Link to={`/payment/verify/${order.order_number}${order.payment_reference ? `?reference=${encodeURIComponent(order.payment_reference)}` : ''}`} className="px-5 py-2 rounded-lg bg-purple-500/10 text-purple-300 border border-purple-500/30">
              Check Payment Status
            </Link>
          )}
        </div>

        {error && <p className="text-sm text-red-400 mt-4">{error}</p>}
      </div>
    </div>
  );
}
