import React, { useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { CheckCircle2, Store } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { getCategories, submitSellerApplication } from '../services/api';

const INITIAL_FORM = {
  businessName: '',
  businessType: 'individual',
  category: '',
  city: '',
  state: '',
  description: '',
  phone: '',
};

const SUCCESS_MESSAGE = 'Your application has been submitted and is under review. You will be notified by email once approved.';

export default function BecomeSeller() {
  const { user, isAuthenticated, loading, refreshUserProfile } = useAuth();
  const [formData, setFormData] = useState(INITIAL_FORM);
  const [categories, setCategories] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const isSellerActive = Boolean(user?.isSellerActive);
  const isApplicationPending = user?.sellerApplicationStatus === 'pending' || Boolean(user?.isSellerPending) || submitted;

  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const data = await getCategories();
        const normalized = data?.results || data || [];
        setCategories(normalized);
        if (normalized.length) {
          setFormData((current) => current.category ? current : { ...current, category: String(normalized[0].id) });
        }
      } catch {
        setError('Unable to load product categories.');
      }
    };

    if (isAuthenticated && !isSellerActive && !isApplicationPending) {
      fetchCategories();
    }
  }, [isApplicationPending, isAuthenticated, isSellerActive]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setFormData((current) => ({ ...current, [name]: value }));
    setError('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');

    try {
      setSubmitting(true);
      await submitSellerApplication({
        business_name: formData.businessName.trim(),
        business_type: formData.businessType,
        category: formData.category,
        location: `${formData.city.trim()}, ${formData.state.trim()}`,
        description: formData.description.trim(),
        phone: formData.phone.trim(),
      });
      setSubmitted(true);
      setMessage(SUCCESS_MESSAGE);
      await refreshUserProfile();
    } catch (submitError) {
      setError(submitError?.data?.error || submitError?.message || 'Unable to submit seller application.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-[#2c77d1] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (isSellerActive) {
    return <Navigate to="/seller/dashboard" replace />;
  }

  return (
    <div className="min-h-screen bg-[#020617] text-white flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-2xl rounded-2xl border border-[#2c77d1]/20 bg-[#0f172a] p-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-[#2c77d1]/20 flex items-center justify-center">
            <Store className="w-5 h-5 text-[#2c77d1]" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Become a Seller</h1>
            <p className="text-sm text-gray-400">Tell us what you plan to sell. Admin approval is required.</p>
          </div>
        </div>

        {(message || isApplicationPending) && (
          <div className="mb-6 rounded-lg border border-green-400/20 bg-green-500/10 px-4 py-3 text-sm text-green-200 flex gap-2">
            <CheckCircle2 className="w-5 h-5 shrink-0" />
            <span>{message || SUCCESS_MESSAGE}</span>
          </div>
        )}

        {error && (
          <div className="mb-6 rounded-lg border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-semibold text-gray-200 mb-2">Business Name</label>
            <input
              type="text"
              name="businessName"
              value={formData.businessName}
              onChange={handleChange}
              disabled={isApplicationPending}
              required
              className="w-full bg-[#020617] border border-gray-700 rounded-lg px-3 py-2.5 text-white focus:outline-none focus:border-[#2c77d1] disabled:opacity-60"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold text-gray-200 mb-2">Business Type</label>
              <select
                name="businessType"
                value={formData.businessType}
                onChange={handleChange}
                disabled={isApplicationPending}
                className="w-full bg-[#020617] border border-gray-700 rounded-lg px-3 py-2.5 text-white focus:outline-none focus:border-[#2c77d1] disabled:opacity-60"
              >
                <option value="individual">Individual</option>
                <option value="small_business">Small Business</option>
                <option value="enterprise">Enterprise</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-200 mb-2">Product Category</label>
              <select
                name="category"
                value={formData.category}
                onChange={handleChange}
                disabled={isApplicationPending}
                required
                className="w-full bg-[#020617] border border-gray-700 rounded-lg px-3 py-2.5 text-white focus:outline-none focus:border-[#2c77d1] disabled:opacity-60"
              >
                <option value="">Select category</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>{category.name}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold text-gray-200 mb-2">City</label>
              <input
                type="text"
                name="city"
                value={formData.city}
                onChange={handleChange}
                disabled={isApplicationPending}
                required
                className="w-full bg-[#020617] border border-gray-700 rounded-lg px-3 py-2.5 text-white focus:outline-none focus:border-[#2c77d1] disabled:opacity-60"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-200 mb-2">State</label>
              <input
                type="text"
                name="state"
                value={formData.state}
                onChange={handleChange}
                disabled={isApplicationPending}
                required
                className="w-full bg-[#020617] border border-gray-700 rounded-lg px-3 py-2.5 text-white focus:outline-none focus:border-[#2c77d1] disabled:opacity-60"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-200 mb-2">Business Phone Number</label>
            <input
              type="tel"
              name="phone"
              value={formData.phone}
              onChange={handleChange}
              disabled={isApplicationPending}
              required
              className="w-full bg-[#020617] border border-gray-700 rounded-lg px-3 py-2.5 text-white focus:outline-none focus:border-[#2c77d1] disabled:opacity-60"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-200 mb-2">What do you plan to sell?</label>
            <textarea
              name="description"
              value={formData.description}
              onChange={handleChange}
              disabled={isApplicationPending}
              required
              rows="4"
              className="w-full bg-[#020617] border border-gray-700 rounded-lg px-3 py-2.5 text-white focus:outline-none focus:border-[#2c77d1] disabled:opacity-60"
            />
          </div>

          <div className="flex flex-col sm:flex-row gap-3 pt-2">
            <button
              type="submit"
              disabled={submitting || isApplicationPending}
              className="btn-primary flex-1 justify-center py-3 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isApplicationPending ? 'Application Pending' : submitting ? 'Submitting...' : 'Submit Application'}
            </button>
            <Link to="/" className="btn-secondary flex-1 justify-center">
              Back Home
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
