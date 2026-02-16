import React, { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { verifyOrderPaymentStatus } from '../services/api';

export default function PaymentVerification() {
  const { orderNumber } = useParams();
  const [searchParams] = useSearchParams();
  const [state, setState] = useState({ loading: true, ok: false, message: '', details: null });

  useEffect(() => {
    const verify = async () => {
      try {
        const reference = searchParams.get('reference');
        const data = await verifyOrderPaymentStatus(orderNumber, reference);
        setState({
          loading: false,
          ok: true,
          message: data?.message || 'Payment verified successfully.',
          details: data?.order || null,
        });
      } catch (apiError) {
        setState({
          loading: false,
          ok: false,
          message: apiError?.data?.error || apiError?.data?.detail || 'Payment verification failed.',
          details: null,
        });
      }
    };

    verify();
  }, [orderNumber, searchParams]);

  return (
    <div className="min-h-screen bg-[#020617] text-white flex items-center justify-center px-4">
      <div className="w-full max-w-xl bg-[#0f172a] border border-gray-800 rounded-2xl p-8">
        <h1 className="text-2xl font-bold mb-2">Payment Verification</h1>
        <p className="text-gray-400 mb-6">Order #{orderNumber}</p>

        {state.loading ? (
          <div className="py-8 text-center text-gray-400">Verifying payment...</div>
        ) : (
          <div className={`rounded-lg border p-4 ${state.ok ? 'bg-green-500/10 border-green-500/40 text-green-300' : 'bg-red-500/10 border-red-500/40 text-red-300'}`}>
            <p className="font-semibold">{state.message}</p>
            {state.details && (
              <div className="text-sm mt-3 space-y-1">
                <p>Status: {state.details.status}</p>
                <p>Payment: {state.details.payment_status}</p>
                <p>Amount: ₦{state.details.amount_paid}</p>
              </div>
            )}
          </div>
        )}

        <div className="mt-6 flex flex-wrap gap-3">
          <Link to={`/orders/${orderNumber}`} className="px-4 py-2 rounded-lg bg-[#2c77d1]/20 text-[#2c77d1] border border-[#2c77d1]/30">View Order</Link>
          <Link to="/orders" className="px-4 py-2 rounded-lg bg-gray-700/30 text-gray-300 border border-gray-700">Back to Orders</Link>
        </div>
      </div>
    </div>
  );
}
