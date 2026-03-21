import React from 'react';

const ORDER_ITEM_STATUS_OPTIONS = ['shipped', 'cancelled'];

export default function OrdersTab({
  orders,
  ordersLoading,
  onOpenOrder,
  selectedOrder,
  orderDetailLoading,
  onUpdateOrderItemStatus,
  updatingItemId,
}) {
  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white">Seller Orders</h2>
        </div>
        {ordersLoading ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400">Loading orders...</div>
        ) : orders.length === 0 ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400">No seller orders yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-200">Order</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-200">Buyer</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-200">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-200">Date</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-200">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {orders.map((order) => (
                  <tr
                    key={order.order_number}
                    className="hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
                    onClick={() => onOpenOrder(order.order_number)}
                  >
                    <td className="px-4 py-3 text-sm text-blue-600 dark:text-blue-400">{order.order_number}</td>
                    <td className="px-4 py-3 text-sm text-gray-800 dark:text-gray-100">{order.customer_name || 'N/A'}</td>
                    <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-200 capitalize">{order.status}</td>
                    <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-200">{new Date(order.created_at).toLocaleDateString()}</td>
                    <td className="px-4 py-3 text-sm font-semibold text-gray-900 dark:text-white">{Number(order.total_amount || 0).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white">Order Detail</h2>
          {selectedOrder?.order_number && (
            <span className="text-sm text-gray-500 dark:text-gray-400">{selectedOrder.order_number}</span>
          )}
        </div>
        {orderDetailLoading ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400">Loading order detail...</div>
        ) : !selectedOrder ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400">Select an order to view details.</div>
        ) : (
          <div className="p-6 space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <p className="text-gray-600 dark:text-gray-400">Buyer: <span className="text-gray-900 dark:text-white">{selectedOrder.customer_name || 'N/A'}</span></p>
              <p className="text-gray-600 dark:text-gray-400">Status: <span className="text-gray-900 dark:text-white capitalize">{selectedOrder.status}</span></p>
              <p className="text-gray-600 dark:text-gray-400">Payment: <span className="text-gray-900 dark:text-white capitalize">{selectedOrder.payment_status}</span></p>
              <p className="text-gray-600 dark:text-gray-400">Total: <span className="text-gray-900 dark:text-white">{Number(selectedOrder.total_amount || 0).toLocaleString()}</span></p>
            </div>

            <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700 dark:text-gray-200">Item</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700 dark:text-gray-200">Qty</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700 dark:text-gray-200">Status</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700 dark:text-gray-200">Update</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {(selectedOrder.items || []).map((item) => (
                    <tr key={item.id}>
                      <td className="px-3 py-2 text-sm text-gray-900 dark:text-white">{item.product_name}</td>
                      <td className="px-3 py-2 text-sm text-gray-700 dark:text-gray-200">{item.quantity}</td>
                      <td className="px-3 py-2 text-sm text-gray-700 dark:text-gray-200 capitalize">{item.status}</td>
                      <td className="px-3 py-2 text-sm">
                        <select
                          value={item.status}
                          onChange={(event) => onUpdateOrderItemStatus(item.id, event.target.value)}
                          disabled={updatingItemId === String(item.id)}
                          className="border border-gray-300 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
                        >
                          <option value={item.status}>{item.status}</option>
                          {ORDER_ITEM_STATUS_OPTIONS.filter((statusOption) => statusOption !== item.status).map((statusOption) => (
                            <option key={statusOption} value={statusOption}>{statusOption}</option>
                          ))}
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
