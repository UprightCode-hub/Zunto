// client/src/pages/Login.jsx
import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Mail, Lock, Eye, EyeOff, ArrowRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import GoogleAuthButton from '../components/auth/GoogleAuthButton';
import AuthMarketplaceShowcase from '../components/auth/AuthMarketplaceShowcase';

export default function Login() {
  const navigate = useNavigate();
  const { login, googleAuth } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    try {
      setLoading(true);
      const result = await login(formData.email, formData.password);
      
      if (result.success) {
        navigate('/');
      } else {
        setError(result.error || 'Login failed. Please try again.');
      }
    } catch { 
      setError('An unexpected error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left Side - Hero/Branding */}
      <div className="hidden lg:flex lg:w-1/2 relative bg-[#050d1b] overflow-hidden items-center justify-center">
        <div className="absolute inset-0 bg-gradient-to-br from-[#2c77d1]/20 to-[#9426f4]/20 z-0" />
        <div className="absolute -top-24 -left-24 w-96 h-96 bg-[#2c77d1]/30 rounded-full blur-3xl opacity-50" />
        <div className="absolute -bottom-24 -right-24 w-96 h-96 bg-[#9426f4]/30 rounded-full blur-3xl opacity-50" />
        
        <AuthMarketplaceShowcase />
      </div>

      {/* Right Side - Form */}
      <div className="w-full lg:w-1/2 bg-[#020617] flex items-center justify-center p-8 relative">
        <div className="max-w-md w-full">
          <div className="text-center lg:text-left mb-10">
            <h1 className="text-3xl font-bold mb-2 text-white">Sign In</h1>
            <p className="text-gray-400">
              Don't have an account?{' '}
              <Link to="/signup" className="text-[#2c77d1] hover:text-[#9426f4] transition-colors font-medium">
                Create one now
              </Link>
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="bg-red-500/10 border border-red-500/50 rounded-xl p-4 flex items-center gap-3 text-red-400 text-sm animate-fade-in">
                <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
                {error}
              </div>
            )}

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300 ml-1">Email Address</label>
              <div className="relative group">
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  required
                  placeholder="you@example.com"
                  className="w-full bg-[#0f172a] border border-gray-800 rounded-xl pl-12 pr-4 py-3.5 text-white placeholder-gray-500 focus:outline-none focus:border-[#2c77d1] focus:ring-1 focus:ring-[#2c77d1] transition-all duration-200"
                />
                <Mail className="absolute left-4 top-3.5 w-5 h-5 text-gray-500 group-focus-within:text-[#2c77d1] transition-colors" />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between items-center ml-1">
                <label className="text-sm font-medium text-gray-300">Password</label>
                <Link to="/forgot-password" className="text-xs text-[#2c77d1] hover:text-[#9426f4] transition-colors">
                  Forgot password?
                </Link>
              </div>
              <div className="relative group">
                <input
                  type={showPassword ? 'text' : 'password'}
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  required
                  placeholder="••••••••"
                  className="w-full bg-[#0f172a] border border-gray-800 rounded-xl pl-12 pr-12 py-3.5 text-white placeholder-gray-500 focus:outline-none focus:border-[#2c77d1] focus:ring-1 focus:ring-[#2c77d1] transition-all duration-200"
                />
                <Lock className="absolute left-4 top-3.5 w-5 h-5 text-gray-500 group-focus-within:text-[#2c77d1] transition-colors" />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-3.5 text-gray-500 hover:text-white transition-colors focus:outline-none"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-[#2c77d1] to-[#9426f4] hover:opacity-90 text-white font-semibold py-4 rounded-xl transition-all duration-200 transform hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2 shadow-lg shadow-[#2c77d1]/25 disabled:opacity-70 disabled:cursor-not-allowed disabled:transform-none"
            >
              {loading ? (
                <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  Sign In <ArrowRight className="w-5 h-5" />
                </>
              )}
            </button>
          </form>

          <div className="mt-6">
            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-800"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-3 bg-[#020617] text-gray-500">Or continue with</span>
              </div>
            </div>

            <GoogleAuthButton 
              mode="signin"
              onSuccess={async (data) => {
                const authResult = await googleAuth(data);
                if (authResult.success) {
                  navigate('/');
                } else {
                  setError(authResult.error || 'Google authentication failed.');
                }
              }}
              onError={(errorMsg) => {
                setError(errorMsg);
              }}
            />
          </div>

          <div className="mt-8 pt-8 border-t border-gray-800 text-center">
            <p className="text-gray-500 text-sm">
              By signing in, you agree to our{' '}
              <Link to="/terms" className="text-gray-400 hover:text-white transition-colors">Terms of Service</Link>
              {' '}and{' '}
              <Link to="/privacy" className="text-gray-400 hover:text-white transition-colors">Privacy Policy</Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
