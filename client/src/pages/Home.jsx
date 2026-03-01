import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, CheckCircle2, Sparkles } from 'lucide-react';
import { getCategories, sendHomepageRecommendationMessage } from '../services/api';
import { useAuth } from '../context/AuthContext';
import ProductGrid from '../components/products/ProductGrid';

export default function Home() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [categoriesCount, setCategoriesCount] = useState(0);
  const [heroSearchTerm, setHeroSearchTerm] = useState('');
  const [aiSearchMode, setAiSearchMode] = useState('ai');
  const [assistantReply, setAssistantReply] = useState('');
  const [assistantError, setAssistantError] = useState('');
  const [assistantLoading, setAssistantLoading] = useState(false);
  const [assistantSessionId, setAssistantSessionId] = useState(() => localStorage.getItem('homepage_assistant_session_id') || null);

  const aiCtaHref = user ? '/inbox/ai' : '/login';

  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const categoriesData = await getCategories();
        const normalized = categoriesData.results || categoriesData || [];
        setCategoriesCount(normalized.length);
      } catch (error) {
        console.error('Error fetching category count:', error);
      }
    };

    fetchCategories();
  }, []);

  const handleHeroSearchSubmit = async (event) => {
    event.preventDefault();
    const value = heroSearchTerm.trim() || 'Popular products';

    if (aiSearchMode === 'products') {
      navigate(`/products?search=${encodeURIComponent(value)}`);
      return;
    }

    setAssistantError('');

    try {
      setAssistantLoading(true);
      const response = await sendHomepageRecommendationMessage(value, assistantSessionId);
      if (response?.session_id) {
        setAssistantSessionId(response.session_id);
        localStorage.setItem('homepage_assistant_session_id', response.session_id);
      }
      setAssistantReply(response?.reply || 'No recommendation returned.');
    } catch (error) {
      const backendError = error?.data;
      const message = backendError?.error || backendError?.detail || error?.message || 'Unable to fetch AI recommendations right now.';
      setAssistantError(message);
    } finally {
      setAssistantLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white dark:bg-gray-900 transition-colors duration-300 pb-12">
      <section className="relative overflow-hidden px-4 py-12 sm:py-16 lg:py-20 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
          <div>
            <h1 className="text-3xl sm:text-5xl md:text-6xl font-bold text-gray-900 dark:text-white mb-5 leading-tight">
              Discover products with
              {' '}
              <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">clear intent</span>
            </h1>
            <p className="text-base sm:text-xl text-gray-600 dark:text-gray-300 mb-6">
              Browse marketplace inventory directly or ask AI to find the right products faster.
            </p>

            <div className="flex flex-wrap gap-2 mb-6">
              {['Verified sellers', 'Secure checkout', 'AI-assisted discovery'].map((badge) => (
                <span
                  key={badge}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
                >
                  <CheckCircle2 className="w-4 h-4" /> {badge}
                </span>
              ))}
            </div>

            <div className="grid grid-cols-3 gap-3 mb-8">
              <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3">
                <p className="text-sm text-gray-500 dark:text-gray-400">Categories</p>
                <p className="text-base font-semibold text-gray-900 dark:text-white">{categoriesCount || '12+'}</p>
              </div>
              <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3">
                <p className="text-sm text-gray-500 dark:text-gray-400">Discovery</p>
                <p className="text-base font-semibold text-gray-900 dark:text-white">Query-driven</p>
              </div>
              <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3">
                <p className="text-sm text-gray-500 dark:text-gray-400">Support</p>
                <p className="text-base font-semibold text-gray-900 dark:text-white">24/7</p>
              </div>
            </div>

            <div className="flex gap-3 flex-wrap">
              <Link to="/products" className="btn-primary btn-primary-lg">
                Start Exploring <ArrowRight className="w-5 h-5" />
              </Link>
              <Link to={aiCtaHref} className="btn-secondary">
                Shop with AI
              </Link>
            </div>
          </div>

          <div className="rounded-2xl border border-[#2c77d1]/25 dark:border-[#2c77d1]/40 bg-white dark:bg-[#0b1222] p-5 sm:p-6 shadow-sm">
            <div className="flex flex-wrap items-center gap-2 mb-4">
              <button
                type="button"
                onClick={() => setAiSearchMode('ai')}
                className={`px-4 py-2 rounded-full text-sm font-semibold transition ${
                  aiSearchMode === 'ai'
                    ? 'bg-gradient-to-r from-[#2c77d1] to-[#9426f4] text-white'
                    : 'bg-gray-100 dark:bg-[#121c34] text-gray-700 dark:text-gray-300'
                }`}
              >
                Ask AI
              </button>
              <button
                type="button"
                onClick={() => setAiSearchMode('products')}
                className={`px-4 py-2 rounded-full text-sm font-semibold transition ${
                  aiSearchMode === 'products'
                    ? 'bg-gradient-to-r from-[#2c77d1] to-[#9426f4] text-white'
                    : 'bg-gray-100 dark:bg-[#121c34] text-gray-700 dark:text-gray-300'
                }`}
              >
                Search Products
              </button>
              <span className="text-xs text-gray-500 dark:text-gray-400 sm:ml-2">
                {aiSearchMode === 'products' ? 'Updates URL query and opens filtered product view.' : 'Get recommendation responses anchored to your assistant session.'}
              </span>
            </div>

            <form onSubmit={handleHeroSearchSubmit} className="rounded-2xl border border-[#2c77d1]/30 bg-gray-50 dark:bg-[#111827] p-4 flex flex-col sm:flex-row gap-3 sm:items-center">
              <input
                type="text"
                value={heroSearchTerm}
                onChange={(event) => setHeroSearchTerm(event.target.value)}
                placeholder={aiSearchMode === 'products' ? 'Search products in marketplace' : 'Ask AI for product recommendations'}
                className="flex-1 bg-transparent text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none"
              />
              <button type="submit" disabled={aiSearchMode === 'ai' && assistantLoading} className="inline-flex items-center justify-center px-5 py-2.5 rounded-full bg-gradient-to-r from-[#2c77d1] to-[#9426f4] text-white font-semibold hover:opacity-90 transition disabled:opacity-70">
                {aiSearchMode === 'products' ? 'Search' : assistantLoading ? 'Thinking...' : 'Ask AI'}
              </button>
            </form>

            {aiSearchMode === 'ai' && (
              <div className="mt-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#0f172a] p-4 space-y-2">
                <p className="text-xs uppercase tracking-wide text-blue-600 dark:text-blue-300 font-semibold inline-flex items-center gap-1">
                  <Sparkles className="w-3 h-3" /> GIGI AI Response
                </p>
                {assistantError && <p className="text-sm text-red-500 dark:text-red-300">{assistantError}</p>}
                {!assistantError && assistantReply && <p className="text-sm text-gray-800 dark:text-gray-100 whitespace-pre-line">{assistantReply}</p>}
                {!assistantError && !assistantReply && <p className="text-sm text-gray-500 dark:text-gray-400">Ask for recommendations to get an inline response here.</p>}
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="px-4 pb-12 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <ProductGrid
            title="Discovery Feed"
            description="Homepage discovery now uses the same query-driven product renderer as the products page."
            showFilters={false}
            showHeader
            limit={9}
          />
        </div>
      </section>
    </div>
  );
}
