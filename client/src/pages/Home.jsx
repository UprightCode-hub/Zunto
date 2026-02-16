import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Star, Truck, Shield, Headphones, Zap, Megaphone } from 'lucide-react';
import { getFeaturedProducts, getAdProducts, getCategories } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { getProductImage, getProductTitle } from '../utils/product';

export default function Home() {
  const [featuredProducts, setFeaturedProducts] = useState([]);
  const [adProducts, setAdProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();

  useEffect(() => {
    const fetchHomeData = async () => {
      try {
        setLoading(true);
        const [featuredData, adsData, categoriesData] = await Promise.all([
          getFeaturedProducts(),
          getAdProducts(),
          getCategories(),
        ]);

        setFeaturedProducts(featuredData.results || featuredData);
        setAdProducts(adsData.results || adsData);
        setCategories(categoriesData.results || categoriesData);
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

  if (loading) {
    return (
      <div className="min-h-screen bg-white dark:bg-gray-900 flex items-center justify-center pt-20">
        <div className="w-16 h-16 border-4 border-blue-600 dark:border-[#2c77d1] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white dark:bg-gray-900 transition-colors duration-300 pt-20">
      <section className="relative overflow-hidden px-4 py-20 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
            <div className="z-10">
              <h1 className="text-5xl md:text-6xl font-bold text-gray-900 dark:text-white mb-6 leading-tight">
                Shop <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">Premium</span> Products
              </h1>
              <p className="text-xl text-gray-600 dark:text-gray-300 mb-8">
                Discover verified listings, boosted deals, and trusted sellers across the marketplace.
              </p>
              <div className="flex gap-4 flex-wrap">
                <Link
                  to="/shop"
                  className="inline-flex items-center gap-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-bold px-8 py-4 rounded-lg transition-all transform hover:scale-105 shadow-lg"
                >
                  Shop Now <ArrowRight className="w-5 h-5" />
                </Link>
                {user?.role === 'seller' && (
                  <Link
                    to="/dashboard"
                    className="inline-flex items-center gap-2 bg-gray-900 dark:bg-gray-700 text-white font-bold px-8 py-4 rounded-lg hover:bg-gray-800 dark:hover:bg-gray-600 transition-all"
                  >
                    Dashboard
                  </Link>
                )}
                <Link
                  to="/seller"
                  className="inline-flex items-center gap-2 border-2 border-blue-600 dark:border-purple-600 text-blue-600 dark:text-purple-400 font-bold px-8 py-4 rounded-lg hover:bg-blue-50 dark:hover:bg-gray-800 transition-colors"
                >
                  Promote Your Products
                </Link>
              </div>
            </div>
            <div className="relative h-96 md:h-full">
              <div className="absolute inset-0 bg-gradient-to-br from-blue-200 via-purple-200 to-pink-200 dark:from-blue-900 dark:via-purple-900 dark:to-pink-900 rounded-3xl opacity-20 blur-3xl" />
              <div className="relative w-full h-full bg-gray-200 dark:bg-gray-700 rounded-3xl shadow-2xl overflow-hidden">
                <img src={getProductImage(adProducts[0] || featuredProducts[0])} alt="Marketplace highlight" className="w-full h-full object-cover" />
              </div>
            </div>
          </div>
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
                <Link key={product.id} to={`/product/${product.slug}`} className="bg-black/30 border border-white/20 rounded-xl overflow-hidden hover:border-white/40 transition">
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
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white text-center mb-12">Why Choose Zunto?</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <div key={feature.title} className="bg-white dark:bg-gray-700 p-8 rounded-xl text-center shadow-md hover:shadow-lg transition-shadow">
                  <Icon className="w-12 h-12 text-blue-600 dark:text-purple-400 mx-auto mb-4" />
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">{feature.title}</h3>
                  <p className="text-gray-600 dark:text-gray-300">{feature.description}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="py-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-12">Shop by Category</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {categories.slice(0, 4).map((category) => (
              <Link
                key={category.id}
                to={`/shop?category=${category.id}`}
                className="group relative overflow-hidden rounded-xl h-48 cursor-pointer"
              >
                <div className="w-full h-full group-hover:scale-110 transition-transform duration-300 bg-gradient-to-br from-blue-500 to-blue-600" />
                <div className="absolute inset-0 bg-gradient-to-br from-blue-500 to-blue-600 opacity-40 group-hover:opacity-60 transition-opacity" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <h3 className="text-2xl font-bold text-white text-center">{category.name}</h3>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-gray-50 dark:bg-gray-800 py-16 px-4 sm:px-6 lg:px-8 transition-colors">
        <div className="max-w-7xl mx-auto">
          <div className="flex justify-between items-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white">Featured Products</h2>
            <Link to="/shop" className="text-blue-600 dark:text-blue-400 font-semibold hover:text-blue-700 dark:hover:text-blue-300 flex items-center gap-2">
              View All <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {featuredProducts.slice(0, 4).map((product) => (
              <Link
                key={product.id}
                to={`/product/${product.slug}`}
                className="bg-white dark:bg-gray-700 rounded-xl overflow-hidden shadow-md hover:shadow-xl transition-all transform hover:-translate-y-1"
              >
                <div className="relative h-48 overflow-hidden bg-gray-200 dark:bg-gray-600">
                  <img
                    src={getProductImage(product)}
                    alt={getProductTitle(product)}
                    className="w-full h-full object-cover hover:scale-110 transition-transform duration-300"
                  />
                </div>
                <div className="p-6">
                  <h3 className="font-bold text-lg text-gray-900 dark:text-white mb-2">{getProductTitle(product)}</h3>
                  <div className="flex justify-between items-center">
                    <span className="text-2xl font-bold text-blue-600 dark:text-blue-400">${product.price || '0.00'}</span>
                    <div className="flex items-center gap-1">
                      <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                      <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">{product.average_rating || '4.5'}</span>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="py-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">Subscribe to Marketplace Updates</h2>
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
