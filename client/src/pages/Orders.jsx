import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { getMyOrders, cancelOrder, getOrderDetail } from '../services/api';
import { Package, Truck, Check, X, ChevronDown, ChevronUp } from 'lucide-react';

const STATUS_COLORS = {
  pending: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  processing: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  shipped: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  delivered: 'bg-green-500/10 text-green-400 border-green-500/20',
  cancelled: 'bg-red-500/10 text-red-400 border-red-500/20',
  refunded: 'bg-gray-500/10 text-gray-400 border-gray-500/20',
};

const STATUS_ICONS = {
  pending: <Package className="w-5 h-5" />,
  processing: <Truck className="w-5 h-5" />,
  shipped: <Truck className="w-5 h-5" />,
  delivered: <Check className="w-5 h-5" />,
  cancelled: <X className="w-5 h-5" />,
};

export default function Orders() {
  const { user } = useAuth();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedOrder, setExpandedOrder] = useState(null);
  const [filterStatus, setFilterStatus] = useState('');
  const [sortBy, setSortBy] = useState('newest');

  useEffect(() => {
    fetchOrders();
  }, []);

  const fetchOrders = async () => {
    try {
      setLoading(true);
      const data = await getMyOrders();
      setOrders(Array.isArray(data) ? data : data.results || []);
    } catch (err) {
      console.error('Error fetching orders:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCancelOrder = async (orderNumber) => {
    if (!window.confirm('Are you sure you want to cancel this order?')) return;
    
    try {
      await cancelOrder(orderNumber);
      fetchOrders();
      alert('Order cancelled successfully!');
    } catch (err) {
      alert('Failed to cancel order');
      console.error(err);
    }
  };

  const filteredOrders = filterStatus 
    ? orders.filter(o => o.status === filterStatus)
    : orders;

  const sortedOrders = [...filteredOrders].sort((a, b) => {
    if (sortBy === 'newest') {
      return new Date(b.created_at) - new Date(a.created_at);
    } else if (sortBy === 'oldest') {
      return new Date(a.created_at) - new Date(b.created_at);
    } else if (sortBy === 'highest') {
      return b.total_amount - a.total_amount;
    } else {
      return a.total_amount - b.total_amount;
    }
  });

  return (
    <div className="min-h-screen pt-20 pb-12">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">My Orders</h1>
          <p className="text-gray-400">Track and manage your purchases</p>
        </div>

        {/* Filters & Sorting */}
        <div className="flex flex-col sm:flex-row gap-4 mb-8">
          <div>
            <label className="block text-sm font-medium mb-2">Filter by Status</label>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-4 py-2 bg-[#2a2a2a] border border-[#2c77d1]/20 rounded-lg focus:outline-none focus:border-[#2c77d1] text-white"
            >
              <option value="">All Orders</option>
              <option value="pending">Pending</option>
              <option value="processing">Processing</option>
              <option value="shipped">Shipped</option>
              <option value="delivered">Delivered</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Sort by</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-4 py-2 bg-[#2a2a2a] border border-[#2c77d1]/20 rounded-lg focus:outline-none focus:border-[#2c77d1] text-white"
            >
              <option value="newest">Newest First</option>
              <option value="oldest">Oldest First</option>
              <option value="highest">Highest Price</option>
              <option value="lowest">Lowest Price</option>
            </select>
          </div>
        </div>

        {/* Orders List */}
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="w-8 h-8 border-2 border-[#2c77d1] border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : sortedOrders.length === 0 ? (
          <div className="text-center py-12 bg-[#1a1a1a] rounded-2xl border border-[#2c77d1]/20">
            <Package className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400 text-lg">No orders found</p>
            <p className="text-gray-500 text-sm mt-2">Your orders will appear here</p>
          </div>
        ) : (
          <div className="space-y-4">
            {sortedOrders.map(order => (
              <div
                key={order.id}
                className="bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl overflow-hidden hover:border-[#2c77d1]/40 transition"
              >
                {/* Order Header */}
                <button
                  onClick={() => setExpandedOrder(expandedOrder === order.id ? null : order.id)}
                  className="w-full p-6 flex items-center justify-between hover:bg-[#2a2a2a]/50 transition"
                >
                  <div className="flex-1 text-left">
                    <div className="flex items-center gap-4 mb-2">
                      <h3 className="text-lg font-semibold">Order #{order.order_number}</h3>
                      <span className={`flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium border ${STATUS_COLORS[order.status] || STATUS_COLORS.pending}`}>
                        {STATUS_ICONS[order.status]}
                        {order.status.charAt(0).toUpperCase() + order.status.slice(1)}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-6 text-sm text-gray-400">
                      <span>{new Date(order.created_at).toLocaleDateString()}</span>
                      <span>${order.total_amount.toFixed(2)}</span>
                      <span>{order.items?.length || 0} item(s)</span>
                    </div>
                  </div>
                  {expandedOrder === order.id ? (
                    <ChevronUp className="w-5 h-5 text-gray-400" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-gray-400" />
                  )}
                </button>

                {/* Order Details (Expanded) */}
                {expandedOrder === order.id && (
                  <div className="border-t border-[#2c77d1]/20 p-6 bg-[#2a2a2a]/30">
                    <div className="grid md:grid-cols-2 gap-8 mb-6">
                      {/* Items */}
                      <div>
                        <h4 className="font-semibold mb-4">Order Items</h4>
                        <div className="space-y-3">
                          {order.items?.map(item => (
                            <div key={item.id} className="flex justify-between text-sm">
                              <span className="text-gray-300">{item.product?.name || 'Product'} × {item.quantity}</span>
                              <span className="font-semibold">${(item.price * item.quantity).toFixed(2)}</span>
                            </div>
                          )) || <p className="text-gray-400">No items</p>}
                        </div>
                      </div>

                      {/* Order Summary */}
                      <div>
                        <h4 className="font-semibold mb-4">Order Summary</h4>
                        <div className="space-y-2 text-sm mb-4">
                          <div className="flex justify-between text-gray-300">
                            <span>Subtotal</span>
                            <span>${order.subtotal?.toFixed(2) || order.total_amount.toFixed(2)}</span>
                          </div>
                          {order.shipping_cost > 0 && (
                            <div className="flex justify-between text-gray-300">
                              <span>Shipping</span>
                              <span>${order.shipping_cost.toFixed(2)}</span>
                            </div>
                          )}
                          {order.tax > 0 && (
                            <div className="flex justify-between text-gray-300">
                              <span>Tax</span>
                              <span>${order.tax.toFixed(2)}</span>
                            </div>
                          )}
                          <div className="pt-2 border-t border-[#2c77d1]/20 flex justify-between font-semibold">
                            <span>Total</span>
                            <span className="text-[#2c77d1]">${order.total_amount.toFixed(2)}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Shipping Address */}
                    {order.shipping_address && (
                      <div className="mb-6 pb-6 border-b border-[#2c77d1]/20">
                        <h4 className="font-semibold mb-3">Shipping Address</h4>
                        <p className="text-gray-300 text-sm">
                          {order.shipping_address.street_address && `${order.shipping_address.street_address}, `}
                          {order.shipping_address.city && `${order.shipping_address.city}, `}
                          {order.shipping_address.state && `${order.shipping_address.state} `}
                          {order.shipping_address.zip_code && order.shipping_address.zip_code}
                        </p>
                      </div>
                    )}

                    {/* Action Buttons */}
                    <div className="flex gap-3">
                      {!['cancelled', 'delivered', 'refunded'].includes(order.status) && (
                        <button
                          onClick={() => handleCancelOrder(order.order_number)}
                          className="px-6 py-2 bg-red-500/10 text-red-400 border border-red-500/20 rounded-lg hover:bg-red-500/20 transition font-medium"
                        >
                          Cancel Order
                        </button>
                      )}
                      <button className="px-6 py-2 bg-[#2c77d1]/10 text-[#2c77d1] border border-[#2c77d1]/20 rounded-lg hover:bg-[#2c77d1]/20 transition font-medium">
                        Download Invoice
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
