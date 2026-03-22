import React, { useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { Store } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { registerSellerAccount } from '../services/api';

export default function BecomeSeller() {
  const { user, isAuthenticated, loading, refreshUserProfile } = useAuth();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const isSellerActive = Boolean(user?.isSellerActive);

  useEffect(() => {
    const submit = async () => {
      if (loading || !isAuthenticated || isSellerActive || message || error) {
        return;
      }

      try {
        setSubmitting(true);
        const response = await registerSellerAccount();
        await refreshUserProfile();
        setMessage(response?.message || 'Seller registration submitted successfully.');
      } catch (submitError) {
        setError(submitError?.data?.error || submitError?.message || 'Unable to start seller registration.');
      } finally {
        setSubmitting(false);
      }
    };

    submit();
  }, [error, isAuthenticated, isSellerActive, loading, message, refreshUserProfile]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-[#2c77d1] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/signup?role=seller" replace />;
  }

  if (isSellerActive) {
    return <Navigate to="/seller" replace />;
  }

  return (
    <div className="min-h-screen bg-[#020617] text-white flex items-center justify-center px-4">
      <div className="w-full max-w-lg rounded-2xl border border-[#2c77d1]/20 bg-[#0f172a] p-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-[#2c77d1]/20 flex items-center justify-center">
            <Store className="w-5 h-5 text-[#2c77d1]" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Become a Seller</h1>
            <p className="text-sm text-gray-400">Seller access requires admin approval.</p>
          </div>
        </div>

        {submitting && (
          <div className="rounded-lg border border-blue-400/20 bg-blue-500/10 px-4 py-3 text-sm text-blue-200">
            Submitting your seller registration...
          </div>
        )}

        {!submitting && message && (
          <div className="rounded-lg border border-green-400/20 bg-green-500/10 px-4 py-3 text-sm text-green-200">
            {message}
          </div>
        )}

        {!submitting && error && (
          <div className="rounded-lg border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {error}
          </div>
        )}

        <div className="mt-6 space-y-3 text-sm text-gray-300">
          <p>Your seller profile will stay pending until an admin approves it.</p>
          <p>After approval, conversations for your products will remain between a buyer and the product seller.</p>
        </div>

        <div className="mt-8 flex gap-3">
          <Link to="/" className="btn-secondary flex-1 justify-center">
            Back Home
          </Link>
          <Link to="/profile" className="btn-primary flex-1 justify-center">
            Open Profile
          </Link>
        </div>
      </div>
    </div>
  );
}
