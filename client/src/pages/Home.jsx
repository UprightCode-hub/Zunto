import React, { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Star,
  Truck,
  Shield,
  Headphones,
  Zap,
  Megaphone,
  CheckCircle2,
  Sparkles,
  Bot,
  Mail,
  WandSparkles,
} from 'lucide-react';
import { getFeaturedProducts, getAdProducts, getCategories } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { getProductImage, getProductTitle } from '../utils/product';

const placeholderCategories = [
  { id: 'all-products', name: 'All Products' },
  { id: 'new-arrivals', name: 'New Arrivals' },
  { id: 'popular', name: 'Popular Picks' },
  { id: 'top-rated', name: 'Top Rated' },
];

const placeholderProducts = [
  { id: 'placeholder-1', slug: 'shop', name: 'Smartphone Accessories', price: 'From $15' },
  { id: 'placeholder-2', slug: 'shop', name: 'Home Essentials', price: 'From $22' },
  { id: 'placeholder-3', slug: 'shop', name: 'Fashion & Lifestyle', price: 'From $18' },
  { id: 'placeholder-4', slug: 'shop', name: 'Electronics Deals', price: 'From $49' },
];

export default function Home() {
  const [featuredProducts, setFeaturedProducts] = useState([]);
  const [adProducts, setAdProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isMobileViewport, setIsMobileViewport] = useState(false);
  const [recentlyViewedProducts, setRecentlyViewedProducts] = useState([]);
  const { user } = useAuth();

  useEffect(() => {
    const mediaQuery = window.matchMedia('(max-width: 1023px)');
    const handleViewportChange = (event) => {
      setIsMobileViewport(event.matches);
    };

    setIsMobileViewport(mediaQuery.matches);

    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleViewportChange);
      return () => mediaQuery.removeEventListener('change', handleViewportChange);
    }

    mediaQuery.addListener(handleViewportChange);
    return () => mediaQuery.removeListener(handleViewportChange);
  }, []);

  useEffect(() => {
    const fetchHomeData = async () => {
      try {
        setLoading(true);
        const [featuredData, adsData, categoriesData] = await Promise.all([
          getFeaturedProducts(),
          getAdProducts(),
          getCategories(),
        ]);

        setFeaturedProducts(featuredData.results || featuredData || []);
        setAdProducts(adsData.results || adsData || []);
        setCategories(categoriesData.results || categoriesData || []);
      } catch (error) {
        console.error('Error fetching home data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchHomeData();
  }, []);

  const features = [
    { icon: Truck, title: 'Fast Shipping', description: 'Tracked delivery across all major locations' },
    { icon: Shield, title: 'Secure Payment', description: 'Protected checkout and verified sellers' },
    { icon: Headphones, title: '24/7 Support', description: 'Dedicated support for buyers and sellers' },
    { icon: Zap, title: 'Promoted Listings', description: 'High-visibility slots for premium product ads' },
  ];

  const trustBadges = ['Verified sellers', 'Secure checkout', 'Friendly support'];
  const quickStats = [
    { label: 'Categories ready', value: categories.length || '12+' },
    { label: 'Support availability', value: '24/7' },
    { label: 'Checkout security', value: 'Protected' },
  ];

  const heroProduct = adProducts[0] || featuredProducts[0] || null;
  const hasHeroImage = Boolean(heroProduct && getProductImage(heroProduct));

  const displayedCategories = (categories.length ? categories.slice(0, 4) : placeholderCategories);
  const hasLiveCategories = categories.length > 0;

  const displayedFeatured = (featuredProducts.length ? featuredProducts.slice(0, 4) : placeholderProducts);
  const hasLiveFeatured = featuredProducts.length > 0;

  const merchandisingSections = useMemo(() => ([
    { title: 'Trending Now', subtitle: 'Popular picks people are checking this week.' },
    { title: 'New Arrivals', subtitle: 'Fresh listings recently added to the marketplace.' },
    { title: 'Best Value', subtitle: 'High-value choices across key categories.' },
  ]), []);

  const dynamicBanner = useMemo(() => {
    if (user?.role === 'seller') {
      return {
        title: 'Seller mode: boost your best listings',
        subtitle: 'GIGI AI can help buyers discover your products faster with smarter recommendations.',
      };
    }

    if (recentlyViewedProducts.length > 0) {
      return {
        title: 'Welcome back — your picks are ready',
        subtitle: 'We kept your recently viewed products so you can continue quickly.',
      };
    }

    if (hasLiveFeatured) {
      return {
        title: 'Smart picks, curated for this moment',
        subtitle: 'GIGI AI + live inventory gives faster product discovery.',
      };
    }

    return {
      title: 'Launch mode: premium marketplace experience',
      subtitle: 'The storefront stays polished while inventory is being staged.',
    };
  }, [user?.role, recentlyViewedProducts.length, hasLiveFeatured]);

  const personalizedProducts = useMemo(() => {
    if (hasLiveFeatured) {
      return displayedFeatured;
    }

    if (hasLiveCategories) {
      return placeholderProducts.map((item, index) => ({
        ...item,
        name: `${displayedCategories[index % displayedCategories.length].name} Picks`,
      }));
    }

    return placeholderProducts;
  }, [hasLiveFeatured, displayedFeatured, hasLiveCategories, displayedCategories]);

  const saveRecentlyViewed = (product) => {
    if (!product?.id) {
      return;
    }

    const compactProduct = {
      id: product.id,
      slug: product.slug || 'shop',
      title: getProductTitle(product),
      price: product.price || '0.00',
      image: getProductImage(product),
    };

    const existing = JSON.parse(localStorage.getItem('zunto_recent_products') || '[]');
    const deduped = [compactProduct, ...existing.filter((entry) => entry.id !== compactProduct.id)].slice(0, 8);
    localStorage.setItem('zunto_recent_products', JSON.stringify(deduped));
    setRecentlyViewedProducts(deduped.slice(0, 4));
  };

  useEffect(() => {
    const existing = JSON.parse(localStorage.getItem('zunto_recent_products') || '[]');
    setRecentlyViewedProducts(existing.slice(0, 4));
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-white dark:bg-gray-900 flex items-center justify-center pt-20">
        <div className="w-16 h-16 border-4 border-blue-600 dark:border-[#2c77d1] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white dark:bg-gray-900 transition-colors duration-300 pt-14 sm:pt-20 pb-20 sm:pb-0">
      <section className="relative overflow-hidden px-4 py-12 sm:py-16 lg:py-20 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-10 items-center">
            <div className="z-10">
              <h1 className="text-3xl sm:text-5xl md:text-6xl font-bold text-gray-900 dark:text-white mb-3 sm:mb-6 leading-tight">
                Shop <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">Premium</span> Products
              </h1>
              <p className="text-base sm:text-xl text-gray-600 dark:text-gray-300 mb-5 sm:mb-8">
                Discover verified listings, boosted deals, and trusted sellers across the marketplace.
              </p>

              <div className="flex flex-wrap gap-2 mb-6">
                {trustBadges.map((badge) => (
                  <span
                    key={badge}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
                  >
                    <CheckCircle2 className="w-4 h-4" /> {badge}
                  </span>
                ))}
              </div>

              <div className="grid grid-cols-3 gap-2 sm:gap-3 mb-6 sm:mb-8">
                {quickStats.map((stat) => (
                  <div key={stat.label} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-2.5 sm:p-3">
                    <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">{stat.label}</p>
                    <p className="text-sm sm:text-base font-semibold text-gray-900 dark:text-white">{stat.value}</p>
                  </div>
                ))}
              </div>

              <div className="flex gap-4 flex-wrap">
                <Link
                  to="/shop"
                  className="inline-flex items-center gap-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-bold px-5 sm:px-8 py-2.5 sm:py-4 rounded-lg transition-all transform hover:scale-105 shadow-lg text-sm sm:text-base"
                >
                  Shop Now <ArrowRight className="w-5 h-5" />
                </Link>
                {user?.role === 'seller' && (
                  <Link
                    to="/dashboard"
                    className="inline-flex items-center gap-2 bg-gray-900 dark:bg-gray-700 text-white font-bold px-5 sm:px-8 py-2.5 sm:py-4 rounded-lg hover:bg-gray-800 dark:hover:bg-gray-600 transition-all text-sm sm:text-base"
                  >
                    Dashboard
                  </Link>
                )}
                <Link
                  to="/seller"
                  className="inline-flex items-center gap-2 border-2 border-blue-600 dark:border-purple-600 text-blue-600 dark:text-purple-400 font-bold px-5 sm:px-8 py-2.5 sm:py-4 rounded-lg hover:bg-blue-50 dark:hover:bg-gray-800 transition-colors text-sm sm:text-base"
                >
                  Promote Your Products
                </Link>
              </div>
            </div>

            <div className="relative h-72 sm:h-80 md:h-full min-h-[280px]">
              <div className="absolute inset-0 bg-gradient-to-br from-blue-200 via-purple-200 to-pink-200 dark:from-blue-900 dark:via-purple-900 dark:to-pink-900 rounded-3xl opacity-20 blur-3xl" />
              <div className="relative w-full h-full bg-gray-200 dark:bg-gray-700 rounded-3xl shadow-2xl overflow-hidden">
                {hasHeroImage ? (
                  <img src={getProductImage(heroProduct)} alt="Marketplace highlight" className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full bg-gradient-to-br from-[#0f172a] via-[#1d4ed8] to-[#6d28d9] text-white p-8 flex flex-col justify-end">
                    <p className="text-sm uppercase tracking-widest text-white/80 mb-2">Marketplace Campaign</p>
                    <h3 className="text-2xl sm:text-3xl font-bold mb-2">Fresh deals are coming</h3>
                    <p className="text-white/85 max-w-sm">While we load products for launch, you can browse categories and set up your seller promotions.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="px-4 pb-10 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto rounded-2xl p-6 md:p-8 bg-gradient-to-r from-[#050d1b] via-[#1d4ed8] to-[#9426f4] text-white shadow-xl">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
            <div>
              <p className="inline-flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-white/80 mb-3">
                <Sparkles className="w-4 h-4" /> What makes Zunto different
              </p>
              <h2 className="text-xl sm:text-3xl font-bold mb-3">Meet GIGI AI, your shopping copilot</h2>
              <p className="text-sm sm:text-base text-white/90 max-w-2xl">
                GIGI AI can recommend products, guide support questions, and power smart email-style assistance inside the marketplace.
                {isMobileViewport ? ' Built for fast mobile answers.' : ' On laptop, it can support deeper shopping decisions with richer context.'}
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-1 gap-3 min-w-[220px]">
              <div className="rounded-xl bg-white/10 border border-white/20 p-3 flex items-center gap-3">
                <Bot className="w-5 h-5" />
                <span className="text-sm">Product suggestions</span>
              </div>
              <div className="rounded-xl bg-white/10 border border-white/20 p-3 flex items-center gap-3">
                <WandSparkles className="w-5 h-5" />
                <span className="text-sm">Personalized guidance</span>
              </div>
              <div className="rounded-xl bg-white/10 border border-white/20 p-3 flex items-center gap-3">
                <Mail className="w-5 h-5" />
                <span className="text-sm">Support-style responses</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="px-4 pb-8 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto rounded-2xl border border-blue-200 dark:border-blue-900/40 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-[#0b1730] dark:to-[#1b1335] p-4 sm:p-5">
          <h3 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white">{dynamicBanner.title}</h3>
          <p className="text-sm sm:text-base text-gray-600 dark:text-gray-300 mt-1">{dynamicBanner.subtitle}</p>
        </div>
      </section>

      {adProducts.length > 0 && (
        <section className="px-4 pb-10 sm:px-6 lg:px-8">
          <div className="max-w-7xl mx-auto bg-gradient-to-r from-[#0f172a] via-[#1d4ed8] to-[#6d28d9] rounded-2xl p-6 md:p-8 shadow-xl">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3 text-white">
                <Megaphone className="w-6 h-6" />
                <h2 className="text-2xl font-bold">Sponsored & Boosted Products</h2>
              </div>
              <Link to="/shop" className="text-white/90 hover:text-white font-semibold">Explore all</Link>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {adProducts.slice(0, 4).map((product) => (
                <Link key={product.id} to={`/product/${product.slug}`} onClick={() => saveRecentlyViewed(product)} className="bg-black/30 border border-white/20 rounded-xl overflow-hidden hover:border-white/40 transition">
                  <img src={getProductImage(product)} alt={getProductTitle(product)} className="h-40 w-full object-cover" />
                  <div className="p-4 text-white">
                    <h3 className="font-semibold truncate">{getProductTitle(product)}</h3>
                    <p className="text-sm text-white/80 mt-1">${product.price}</p>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      <section className="bg-gray-50 dark:bg-gray-800 py-16 px-4 sm:px-6 lg:px-8 transition-colors">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white text-center mb-10 sm:mb-12">Why Choose Zunto?</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <div key={feature.title} className="bg-white dark:bg-gray-700 p-6 sm:p-8 rounded-xl text-center shadow-md hover:shadow-lg transition-shadow">
                  <Icon className="w-10 h-10 sm:w-12 sm:h-12 text-blue-600 dark:text-purple-400 mx-auto mb-3 sm:mb-4" />
                  <h3 className="text-lg sm:text-xl font-semibold text-gray-900 dark:text-white mb-2">{feature.title}</h3>
                  <p className="text-gray-600 dark:text-gray-300">{feature.description}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {merchandisingSections.map((section) => (
        <section key={section.title} className="py-12 px-4 sm:px-6 lg:px-8">
          <div className="max-w-7xl mx-auto">
            <div className="flex items-end justify-between mb-5">
              <div>
                <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">{section.title}</h2>
                <p className="text-gray-500 dark:text-gray-400 mt-1">{section.subtitle}</p>
              </div>
              <Link to="/shop" className="text-blue-600 dark:text-blue-400 font-semibold hidden sm:inline-flex items-center gap-2">
                Explore <ArrowRight className="w-4 h-4" />
              </Link>
            </div>

            <div className="flex sm:grid sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5 overflow-x-auto sm:overflow-visible snap-x snap-mandatory pb-2 sm:pb-0">
              {displayedFeatured.map((product, index) => (
                <Link
                  key={`${section.title}-${product.id}`}
                  to={hasLiveFeatured ? `/product/${product.slug}` : '/shop'}
                  className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden shadow-sm hover:shadow-md transition min-w-[240px] sm:min-w-0 snap-start"
                >
                  <div className="h-32 sm:h-36 bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center text-white font-semibold text-sm sm:text-base">
                    {hasLiveFeatured ? getProductTitle(product) : `${section.title} ${index + 1}`}
                  </div>
                  <div className="p-4">
                    <h3 className="text-sm sm:text-base font-semibold text-gray-900 dark:text-white truncate">{hasLiveFeatured ? getProductTitle(product) : product.name}</h3>
                    <p className="text-blue-600 dark:text-blue-400 font-bold mt-1 text-sm sm:text-base">{hasLiveFeatured ? `$${product.price || '0.00'}` : product.price}</p>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>
      ))}

      <section className="py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-end justify-between mb-5">
            <div>
              <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">For You</h2>
              <p className="text-gray-500 dark:text-gray-400 mt-1">Personalized picks powered by GIGI AI signals.</p>
            </div>
            <Link to="/shop" className="text-blue-600 dark:text-blue-400 font-semibold hidden sm:inline-flex items-center gap-2">
              Explore <ArrowRight className="w-4 h-4" />
            </Link>
          </div>

          <div className="flex sm:grid sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5 overflow-x-auto sm:overflow-visible snap-x snap-mandatory pb-2 sm:pb-0">
            {personalizedProducts.map((product) => (
              <Link
                key={`personalized-${product.id}`}
                to={hasLiveFeatured ? `/product/${product.slug}` : '/shop'}
                onClick={() => saveRecentlyViewed(product)}
                className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden shadow-sm hover:shadow-md transition min-w-[240px] sm:min-w-0 snap-start"
              >
                <div className="h-32 sm:h-36 bg-gradient-to-br from-[#1d4ed8] to-[#9426f4] flex items-center justify-center text-white font-semibold text-sm sm:text-base">
                  {hasLiveFeatured ? getProductTitle(product) : product.name}
                </div>
                <div className="p-4">
                  <h3 className="text-sm sm:text-base font-semibold text-gray-900 dark:text-white truncate">{hasLiveFeatured ? getProductTitle(product) : product.name}</h3>
                  <p className="text-blue-600 dark:text-blue-400 font-bold mt-1 text-sm sm:text-base">{hasLiveFeatured ? `$${product.price || '0.00'}` : product.price}</p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-end justify-between mb-5">
            <div>
              <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">Recently Viewed</h2>
              <p className="text-gray-500 dark:text-gray-400 mt-1">Quickly jump back to products you checked earlier.</p>
            </div>
          </div>

          {recentlyViewedProducts.length === 0 ? (
            <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 p-4 sm:p-5 text-gray-600 dark:text-gray-300 text-sm sm:text-base">
              No recently viewed products yet. Browse any product to build your quick-access history.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {recentlyViewedProducts.map((product) => (
                <Link
                  key={`recent-${product.id}`}
                  to={`/product/${product.slug}`}
                  className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden shadow-sm hover:shadow-md transition"
                >
                  <div className="h-28 bg-gradient-to-br from-blue-500 to-purple-600" />
                  <div className="p-4">
                    <h3 className="text-sm sm:text-base font-semibold text-gray-900 dark:text-white truncate">{product.title}</h3>
                    <p className="text-blue-600 dark:text-blue-400 font-bold mt-1 text-sm sm:text-base">${product.price}</p>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="py-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">Shop by Category</h2>
            {!hasLiveCategories && (
              <Link to="/shop" className="text-blue-600 dark:text-blue-400 font-semibold">Browse all</Link>
            )}
          </div>

          {!hasLiveCategories && (
            <p className="text-gray-500 dark:text-gray-400 mb-6">Live categories are still being configured. You can still explore all products now.</p>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {displayedCategories.map((category) => (
              <Link
                key={category.id}
                to={hasLiveCategories ? `/shop?category=${category.id}` : '/shop'}
                className="group relative overflow-hidden rounded-xl h-48 cursor-pointer"
              >
                <div className="w-full h-full group-hover:scale-110 transition-transform duration-300 bg-gradient-to-br from-blue-500 to-blue-600" />
                <div className="absolute inset-0 bg-gradient-to-br from-blue-500 to-blue-600 opacity-40 group-hover:opacity-60 transition-opacity" />
                <div className="absolute inset-0 flex items-center justify-center px-4">
                  <h3 className="text-xl sm:text-2xl font-bold text-white text-center">{category.name}</h3>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-gray-50 dark:bg-gray-800 py-16 px-4 sm:px-6 lg:px-8 transition-colors">
        <div className="max-w-7xl mx-auto">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">Featured Products</h2>
            <Link to="/shop" className="text-blue-600 dark:text-blue-400 font-semibold hover:text-blue-700 dark:hover:text-blue-300 flex items-center gap-2">
              View All <ArrowRight className="w-4 h-4" />
            </Link>
          </div>

          {!hasLiveFeatured && (
            <p className="text-gray-500 dark:text-gray-400 mb-6">Products are being staged for launch. Here are browsing collections to get started.</p>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {displayedFeatured.map((product, index) => (
              <Link
                key={product.id}
                to={hasLiveFeatured ? `/product/${product.slug}` : '/shop'}
                onClick={() => saveRecentlyViewed(product)}
                className="bg-white dark:bg-gray-700 rounded-xl overflow-hidden shadow-md hover:shadow-xl transition-all transform hover:-translate-y-1"
              >
                <div className="relative h-48 overflow-hidden bg-gray-200 dark:bg-gray-600">
                  {hasLiveFeatured ? (
                    <img
                      src={getProductImage(product)}
                      alt={getProductTitle(product)}
                      className="w-full h-full object-cover hover:scale-110 transition-transform duration-300"
                    />
                  ) : (
                    <div className="w-full h-full bg-gradient-to-br from-blue-600 to-purple-600 opacity-90 flex items-center justify-center text-white font-semibold text-lg">
                      Collection {index + 1}
                    </div>
                  )}
                </div>
                <div className="p-6">
                  <h3 className="font-bold text-base sm:text-lg text-gray-900 dark:text-white mb-2">
                    {hasLiveFeatured ? getProductTitle(product) : product.name}
                  </h3>
                  <div className="flex justify-between items-center">
                    <span className="text-xl sm:text-2xl font-bold text-blue-600 dark:text-blue-400">
                      {hasLiveFeatured ? `$${product.price || '0.00'}` : product.price}
                    </span>
                    <div className="flex items-center gap-1">
                      <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                      <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">{hasLiveFeatured ? product.average_rating || '4.5' : 'Popular'}</span>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>


      <div className="fixed bottom-3 left-3 right-3 z-40 sm:hidden">
        <div className="rounded-2xl border border-gray-200/70 dark:border-gray-700 bg-white/95 dark:bg-gray-800/95 backdrop-blur shadow-lg px-3 py-2">
          <div className="grid grid-cols-3 gap-2 text-center text-xs font-semibold">
            <Link to="/shop" className="py-2 rounded-lg bg-blue-50 dark:bg-gray-700 text-blue-700 dark:text-blue-300">Shop</Link>
            <Link to="/faqs" className="py-2 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200">FAQs</Link>
            <button type="button" className="py-2 rounded-lg bg-purple-600 text-white">GIGI AI</button>
          </div>
        </div>
      </div>

      <section className="py-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-4">Subscribe to Marketplace Updates</h2>
          <p className="text-gray-600 dark:text-gray-300 mb-8">Get new product drops, seller promotions, and buying guides in your inbox.</p>
          <form className="flex gap-4 flex-col sm:flex-row">
            <input
              type="email"
              placeholder="Your email address"
              className="flex-1 px-6 py-3 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:border-blue-600 dark:focus:border-blue-400 transition"
            />
            <button
              type="submit"
              className="px-8 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-bold rounded-lg transition-all whitespace-nowrap shadow-lg"
            >
              Subscribe
            </button>
          </form>
        </div>
      </section>
    </div>
  );
}
