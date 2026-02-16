import React, { useEffect, useState } from 'react';
import { getMyOrders, getMyRefunds, requestRefund } from '../services/api';

export default function Refunds() {
  const [orders, setOrders] = useState([]);
  const [refunds, setRefunds] = useState([]);
  const [form, setForm] = useState({ order: '', amount: '', reason: '', description: '' });
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const [ordersData, refundsData] = await Promise.all([getMyOrders(), getMyRefunds()]);
      setOrders(Array.isArray(ordersData) ? ordersData : ordersData.results || []);
      setRefunds(Array.isArray(refundsData) ? refundsData : refundsData.results || []);
    } catch (error) {
      console.error('Failed to load refund data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSubmit = async (event) => {
    event.preventDefault();
    try {
      setSubmitting(true);
      await requestRefund({
        order: form.order,
        amount: form.amount,
        reason: form.reason,
        description: form.description,
      });
      setForm({ order: '', amount: '', reason: '', description: '' });
      await loadData();
    } catch (error) {
      alert(error?.data?.error || error?.data?.detail || 'Refund request failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen pt-20 pb-12">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 grid lg:grid-cols-2 gap-8">
        <section className="bg-[#1a1a1a] rounded-2xl border border-[#2c77d1]/20 p-6 h-fit">
          <h1 className="text-2xl font-bold mb-2">Request Refund</h1>
          <p className="text-gray-400 mb-5">Refunds are available for Zunto managed-commerce orders only.</p>

          <form onSubmit={handleSubmit} className="space-y-3">
            <select required value={form.order} onChange={(e) => setForm((prev) => ({ ...prev, order: e.target.value }))} className="w-full bg-[#020617] border border-gray-700 rounded-lg px-3 py-2.5">
              <option value="">Select order</option>
              {orders.map((order) => (
                <option key={order.id} value={order.id}>#{order.order_number} - ₦{order.total_amount}</option>
              ))}
            </select>
            <input required type="number" min="1" step="0.01" value={form.amount} onChange={(e) => setForm((prev) => ({ ...prev, amount: e.target.value }))} placeholder="Refund amount" className="w-full bg-[#020617] border border-gray-700 rounded-lg px-3 py-2.5" />
            <input required value={form.reason} onChange={(e) => setForm((prev) => ({ ...prev, reason: e.target.value }))} placeholder="Reason" className="w-full bg-[#020617] border border-gray-700 rounded-lg px-3 py-2.5" />
            <textarea value={form.description} onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))} placeholder="Description (optional)" className="w-full bg-[#020617] border border-gray-700 rounded-lg px-3 py-2.5 min-h-[100px]" />
            <button type="submit" disabled={submitting} className="w-full bg-[#2c77d1] hover:bg-[#256bbd] rounded-lg py-3 font-semibold disabled:opacity-70">
              {submitting ? 'Submitting...' : 'Submit Refund Request'}
            </button>
          </form>
        </section>

        <section>
          <h2 className="text-2xl font-bold mb-4">My Refunds</h2>
          {loading ? (
            <p className="text-gray-400">Loading...</p>
          ) : refunds.length === 0 ? (
            <p className="text-gray-400">No refund requests yet.</p>
          ) : (
            <div className="space-y-3">
              {refunds.map((refund) => (
                <div key={refund.id} className="bg-[#1a1a1a] rounded-xl border border-[#2c77d1]/20 p-4">
                  <div className="flex items-center justify-between">
                    <p className="font-semibold">Order #{refund.order_number}</p>
                    <span className="text-sm text-[#2c77d1] uppercase">{refund.status}</span>
                  </div>
                  <p className="text-gray-300 mt-2">₦{refund.amount} • {refund.reason}</p>
                  {refund.description && <p className="text-sm text-gray-400 mt-1">{refund.description}</p>}
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
