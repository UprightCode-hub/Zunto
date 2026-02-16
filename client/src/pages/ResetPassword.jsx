import React, { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { confirmPasswordReset } from '../services/api';

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const [formData, setFormData] = useState({
    email: searchParams.get('email') || '',
    code: '',
    new_password: '',
    new_password_confirm: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const handleChange = (event) => {
    setFormData((prev) => ({ ...prev, [event.target.name]: event.target.value }));
    setError('');
    setMessage('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setMessage('');

    try {
      setLoading(true);
      const response = await confirmPasswordReset({
        ...formData,
        email: formData.email.trim(),
        code: formData.code.trim(),
      });
      setMessage(response?.message || 'Password reset successful. You can now log in.');
    } catch (apiError) {
      setError(apiError?.data?.error || apiError?.data?.detail || 'Password reset failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#020617] text-white flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-[#0f172a] border border-gray-800 rounded-2xl p-8">
        <h1 className="text-2xl font-bold mb-2">Reset Password</h1>
        <p className="text-gray-400 mb-6">Enter your email, reset code, and new password.</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/40 rounded-lg px-3 py-2">{error}</p>}
          {message && <p className="text-sm text-green-400 bg-green-500/10 border border-green-500/40 rounded-lg px-3 py-2">{message}</p>}

          <input name="email" type="email" required value={formData.email} onChange={handleChange} placeholder="Email" className="w-full bg-[#020617] border border-gray-700 rounded-lg px-3 py-2.5" />
          <input name="code" required maxLength={6} value={formData.code} onChange={handleChange} placeholder="6-digit code" className="w-full bg-[#020617] border border-gray-700 rounded-lg px-3 py-2.5 tracking-[0.2em]" />
          <input name="new_password" type="password" required minLength={8} value={formData.new_password} onChange={handleChange} placeholder="New password" className="w-full bg-[#020617] border border-gray-700 rounded-lg px-3 py-2.5" />
          <input name="new_password_confirm" type="password" required minLength={8} value={formData.new_password_confirm} onChange={handleChange} placeholder="Confirm new password" className="w-full bg-[#020617] border border-gray-700 rounded-lg px-3 py-2.5" />

          <button type="submit" disabled={loading} className="w-full bg-[#2c77d1] hover:bg-[#256bbd] disabled:opacity-70 rounded-lg py-3 font-semibold">
            {loading ? 'Resetting...' : 'Reset Password'}
          </button>
        </form>

        <div className="mt-4 text-sm">
          <Link to="/login" className="text-gray-400 hover:text-white">Back to login</Link>
        </div>
      </div>
    </div>
  );
}
