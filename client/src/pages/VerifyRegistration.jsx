import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { MailCheck, RefreshCw } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function VerifyRegistration() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { verifyRegistration, resendRegistrationCode } = useAuth();

  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const queryEmail = searchParams.get('email') || '';
    setEmail(queryEmail);
  }, [searchParams]);

  const handleVerify = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');

    if (!email.trim()) {
      setError('Email is required.');
      return;
    }

    if (code.trim().length !== 6) {
      setError('Enter the 6-digit verification code.');
      return;
    }

    setLoading(true);
    const result = await verifyRegistration(email.trim(), code.trim());
    setLoading(false);

    if (result.success) {
      navigate('/dashboard');
      return;
    }

    setError(result.error || 'Verification failed. Please try again.');
  };

  const handleResend = async () => {
    setError('');
    setMessage('');

    if (!email.trim()) {
      setError('Enter your registration email to resend the code.');
      return;
    }

    setResending(true);
    const result = await resendRegistrationCode(email.trim());
    setResending(false);

    if (result.success) {
      setMessage(result.data?.message || 'Verification code resent.');
      return;
    }

    setError(result.error || 'Failed to resend code.');
  };

  return (
    <div className="min-h-screen bg-[#020617] text-white flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-[#0f172a] border border-gray-800 rounded-2xl p-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-[#2c77d1]/20 flex items-center justify-center">
            <MailCheck className="w-5 h-5 text-[#2c77d1]" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Verify Your Email</h1>
            <p className="text-sm text-gray-400">Complete verification to activate your account.</p>
          </div>
        </div>

        <form onSubmit={handleVerify} className="space-y-4">
          {error && (
            <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/40 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          {message && (
            <div className="text-sm text-green-400 bg-green-500/10 border border-green-500/40 rounded-lg px-3 py-2">
              {message}
            </div>
          )}

          <div className="space-y-1">
            <label className="text-sm text-gray-300">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full bg-[#020617] border border-gray-700 rounded-lg px-3 py-2.5 text-white focus:outline-none focus:border-[#2c77d1]"
              required
            />
          </div>

          <div className="space-y-1">
            <label className="text-sm text-gray-300">Verification Code</label>
            <input
              type="text"
              inputMode="numeric"
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
              placeholder="123456"
              className="w-full bg-[#020617] border border-gray-700 rounded-lg px-3 py-2.5 text-white tracking-[0.3em] focus:outline-none focus:border-[#2c77d1]"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#2c77d1] hover:bg-[#256bbd] transition-colors rounded-lg py-3 font-semibold disabled:opacity-70"
          >
            {loading ? 'Verifying...' : 'Verify and Continue'}
          </button>
        </form>

        <div className="mt-4 flex items-center justify-between">
          <button
            type="button"
            onClick={handleResend}
            disabled={resending}
            className="text-sm text-[#2c77d1] hover:text-[#5aa5ff] transition-colors inline-flex items-center gap-1 disabled:opacity-60"
          >
            <RefreshCw className={`w-4 h-4 ${resending ? 'animate-spin' : ''}`} />
            {resending ? 'Resending...' : 'Resend Code'}
          </button>

          <Link to="/login" className="text-sm text-gray-400 hover:text-white transition-colors">
            Back to Login
          </Link>
        </div>
      </div>
    </div>
  );
}
