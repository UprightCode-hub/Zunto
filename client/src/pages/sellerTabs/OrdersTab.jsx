import React, { useMemo, useState } from 'react';
import { CheckCircle2, PackageCheck, Search } from 'lucide-react';
import { formatNaira } from '../../utils/helpers';

const STATUS_OPTIONS = ['all', 'pending', 'processing', 'shipped', 'delivered', 'cancelled'];

const statusClass = (status = '') => {
  const normalized = String(status || '').toLowerCase();
  if (normalized === 'delivered') return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-200';
  if (normalized === 'shipped') return 'bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-200';
  if (normalized === 'cancelled') return 'bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-200';
  if (normalized === 'pending') return 'bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-200';
  return 'bg-slate-100 text-slate-700 dark:bg-slate-500/15 dark:text-slate-200';
};

const orderItemsText = (order) => {
  const items = Array.isArray(order?.items) ? order.items : [];
  if (!items.length) return `${order?.total_items || 0} item${Number(order?.total_items || 0) === 1 ? '' : 's'}`;
  return items.slice(0, 3).map((item) => `${item.quantity || 1}x ${item.product_name}`).join(', ');
};

export default function OrdersTab({
  orders,
  ordersLoading,
  onOpenOrder,
  selectedOrder,
  orderDetailLoading,
  onUpdateOrderItemStatus,
  updatingItemId,
}) {
  const [statusFilter, setStatusFilter] = useState('all');
  const [search, setSearch] = useState('');

  const filteredOrders = useMemo(() => {
    const term = search.trim().toLowerCase();
    return (orders || []).filter((order) => {
      const statusMatch = statusFilter === 'all' || String(order.status).toLowerCase() === statusFilter;
      const searchText = `${order.order_number || ''} ${order.customer_name || ''} ${orderItemsText(order)}`.toLowerCase();
      return statusMatch && (!term || searchText.includes(term));
    });
  }, [orders, search, statusFilter]);

  const updateWholeOrder = (status) => {
    (selectedOrder?.items || [])
      .filter((item) => item.status !== status)
      .forEach((item) => onUpdateOrderItemStatus(item.id, status));
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-950 dark:text-white">Incoming Orders</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">Review buyer orders and update fulfillment status.</p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search orders"
              className="h-10 rounded-lg border border-gray-200 bg-white pl-9 pr-3 text-sm text-gray-900 outline-none focus:border-emerald-500 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            className="h-10 rounded-lg border border-gray-200 bg-white px-3 text-sm text-gray-900 outline-none focus:border-emerald-500 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
          >
            {STATUS_OPTIONS.map((status) => (
              <option key={status} value={status}>{status === 'all' ? 'All statuses' : status}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(360px,0.65fr)]">
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-950">
          {ordersLoading ? (
            <div className="p-8 text-center text-gray-500 dark:text-gray-400">Loading orders...</div>
          ) : filteredOrders.length === 0 ? (
            <div className="p-8 text-center text-gray-500 dark:text-gray-400">No orders match this view.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b border-gray-200 bg-gray-50 dark:border-gray-800 dark:bg-gray-900">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Order</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Buyer</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Items</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Value</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Status</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-gray-500">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                  {filteredOrders.map((order) => (
                    <tr key={order.order_number} className="hover:bg-gray-50 dark:hover:bg-gray-900/70">
                      <td className="px-4 py-4 text-sm font-semibold text-blue-700 dark:text-blue-300">{order.order_number}</td>
                      <td className="px-4 py-4 text-sm text-gray-800 dark:text-gray-100">{order.customer_name || 'Buyer'}</td>
                      <td className="max-w-xs px-4 py-4 text-sm text-gray-600 dark:text-gray-300">{orderItemsText(order)}</td>
                      <td className="px-4 py-4 text-sm font-semibold text-gray-950 dark:text-white">{formatNaira(order.total_amount)}</td>
                      <td className="px-4 py-4 text-sm">
                        <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${statusClass(order.status)}`}>
                          {order.status}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => onOpenOrder(order.order_number)}
                            className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-900"
                          >
                            View
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <aside className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-950">
          <div className="border-b border-gray-200 px-5 py-4 dark:border-gray-800">
            <h3 className="font-bold text-gray-950 dark:text-white">Order Workspace</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">{selectedOrder?.order_number || 'Select an order to act on it.'}</p>
          </div>
          {orderDetailLoading ? (
            <div className="p-8 text-center text-gray-500 dark:text-gray-400">Loading order detail...</div>
          ) : !selectedOrder ? (
            <div className="p-8 text-center text-gray-500 dark:text-gray-400">No order selected.</div>
          ) : (
            <div className="space-y-5 p-5">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <p className="text-gray-500">Buyer<br /><span className="font-semibold text-gray-950 dark:text-white">{selectedOrder.customer_name || 'Buyer'}</span></p>
                <p className="text-gray-500">Payment<br /><span className="font-semibold capitalize text-gray-950 dark:text-white">{selectedOrder.payment_status}</span></p>
                <p className="text-gray-500">Status<br /><span className={`mt-1 inline-flex rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${statusClass(selectedOrder.status)}`}>{selectedOrder.status}</span></p>
                <p className="text-gray-500">Total<br /><span className="font-semibold text-gray-950 dark:text-white">{formatNaira(selectedOrder.total_amount)}</span></p>
              </div>

              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => updateWholeOrder('shipped')}
                  disabled={Boolean(updatingItemId)}
                  className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
                >
                  <PackageCheck className="h-4 w-4" />
                  Mark as Shipped
                </button>
                <button
                  type="button"
                  onClick={() => updateWholeOrder('delivered')}
                  disabled={Boolean(updatingItemId)}
                  className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-60"
                >
                  <CheckCircle2 className="h-4 w-4" />
                  Mark as Delivered
                </button>
              </div>

              <div className="space-y-3">
                {(selectedOrder.items || []).map((item) => (
                  <div key={item.id} className="rounded-lg border border-gray-200 p-3 dark:border-gray-800">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-gray-950 dark:text-white">{item.product_name}</p>
                        <p className="text-xs text-gray-500">Qty {item.quantity} · {formatNaira(item.total_price)}</p>
                      </div>
                      <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${statusClass(item.status)}`}>
                        {item.status}
                      </span>
                    </div>
                    <div className="mt-3 flex gap-2">
                      {['shipped', 'delivered'].map((status) => (
                        <button
                          key={status}
                          type="button"
                          onClick={() => onUpdateOrderItemStatus(item.id, status)}
                          disabled={updatingItemId === String(item.id) || item.status === status}
                          className="rounded-md border border-gray-200 px-3 py-1 text-xs font-semibold capitalize hover:bg-gray-50 disabled:opacity-50 dark:border-gray-700 dark:hover:bg-gray-900"
                        >
                          {status}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
