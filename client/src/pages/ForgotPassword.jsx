import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Mail, Send } from 'lucide-react';
import { requestPasswordReset } from '../services/api';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setMessage('');

    try {
      setLoading(true);
      const response = await requestPasswordReset(email.trim());
      setMessage(response?.message || 'Reset code sent. Check your email.');
    } catch (apiError) {
      setError(apiError?.data?.error || apiError?.data?.detail || 'Failed to request password reset.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#020617] text-white flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-[#0f172a] border border-gray-800 rounded-2xl p-8">
        <h1 className="text-2xl font-bold mb-2">Forgot Password</h1>
        <p className="text-gray-400 mb-6">Enter your account email to receive a reset code.</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/40 rounded-lg px-3 py-2">{error}</p>}
          {message && <p className="text-sm text-green-400 bg-green-500/10 border border-green-500/40 rounded-lg px-3 py-2">{message}</p>}

          <label className="block text-sm text-gray-300">Email</label>
          <div className="relative">
            <Mail className="w-4 h-4 absolute left-3 top-3.5 text-gray-500" />
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-[#020617] border border-gray-700 rounded-lg pl-10 pr-3 py-2.5"
              placeholder="you@example.com"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#2c77d1] hover:bg-[#256bbd] disabled:opacity-70 rounded-lg py-3 font-semibold inline-flex items-center justify-center gap-2"
          >
            <Send className="w-4 h-4" />
            {loading ? 'Sending...' : 'Send Reset Code'}
          </button>
        </form>

        <div className="mt-4 text-sm text-gray-400 flex items-center justify-between">
          <Link to="/login" className="hover:text-white">Back to login</Link>
          <Link to="/reset-password" className="text-[#2c77d1] hover:text-[#5aa5ff]">Already have a code?</Link>
        </div>
      </div>
    </div>
  );
}
