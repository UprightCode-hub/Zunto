import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight, Zap, TrendingUp, Star, ShoppingBag } from 'lucide-react';
import { getProducts, getCategories } from '../services/api';

export default function Home() {
  const [featuredProducts, setFeaturedProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchHomeData();
  }, []);

  const fetchHomeData = async () => {
    try {
      setLoading(true);
      const [productsData, categoriesData] = await Promise.all([
        getProducts({ featured: true, limit: 8 }),
        getCategories()
      ]);
      setFeaturedProducts(productsData.results || productsData);
      setCategories(categoriesData.results || categoriesData);
    } catch (error) {
      console.error('Error fetching home data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-16 h-16 border-4 border-[#2c77d1] border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="pt-24 pb-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#2c77d1] via-[#9426f4] to-[#050d1b] p-12 md:p-16">
            <div className="relative z-10 max-w-2xl">
              <div className="inline-flex items-center gap-2 bg-white/10 backdrop-blur-sm px-4 py-2 rounded-full mb-6">
                <Zap className="w-4 h-4 text-yellow-300" />
                <span className="text-sm">Limited Time Offer</span>
              </div>
              <h1 className="text-4xl md:text-6xl font-bold mb-6">
                Discover Amazing Products
              </h1>
              <p className="text-xl text-gray-200 mb-8">
                Shop the latest trends with up to 50% off on selected items
              </p>
              <div className="flex flex-wrap gap-4">
                <Link 
                  to="/shop"
                  className="bg-white text-[#050d1b] px-8 py-3 rounded-full font-semibold hover:bg-gray-100 transition flex items-center gap-2"
                >
                  Shop Now <ChevronRight className="w-5 h-5" />
                </Link>
                <Link 
                  to="/shop?sale=true"
                  className="border-2 border-white px-8 py-3 rounded-full font-semibold hover:bg-white/10 transition"
                >
                  View Deals
                </Link>
              </div>
            </div>
            <div className="absolute -right-10 -bottom-10 w-72 h-72 bg-[#9426f4] rounded-full blur-3xl opacity-30"></div>
            <div className="absolute -top-10 right-20 w-96 h-96 bg-[#2c77d1] rounded-full blur-3xl opacity-20"></div>
          </div>
        </div>
      </section>

      {/* Categories Section */}
      <section className="py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl font-bold mb-8">Shop by Category</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {categories.slice(0, 8).map((category) => (
              <Link
                key={category.id}
                to={`/shop?category=${category.id}`}
                className="bg-gradient-to-br from-[#2c77d1]/10 to-[#9426f4]/10 border border-[#2c77d1]/20 rounded-2xl p-6 hover:border-[#2c77d1] transition cursor-pointer group"
              >
                <div className="text-5xl mb-3 group-hover:scale-110 transition">
                  {category.icon || '📦'}
                </div>
                <h3 className="font-semibold text-lg mb-1">{category.name}</h3>
                <p className="text-gray-400 text-sm">
                  {category.product_count || 0} products
                </p>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Featured Products Section */}
      <section className="py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-3xl font-bold">Featured Products</h2>
            <Link 
              to="/shop"
              className="text-[#2c77d1] hover:text-[#9426f4] flex items-center gap-2"
            >
              View All <ChevronRight className="w-5 h-5" />
            </Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {featuredProducts.map((product) => (
              <Link
                key={product.id}
                to={`/product/${product.id}`}
                className="bg-[#050d1b] border border-[#2c77d1]/20 rounded-2xl overflow-hidden hover:border-[#2c77d1] transition group"
              >
                <div className="relative bg-gradient-to-br from-[#2c77d1]/20 to-[#9426f4]/20 aspect-square">
                  <img
                    src={product.image || '/placeholder.png'}
                    alt={product.name}
                    className="w-full h-full object-cover"
                  />
                  {product.on_sale && (
                    <div className="absolute top-3 right-3 bg-[#9426f4] text-white text-xs px-3 py-1 rounded-full font-semibold">
                      Sale
                    </div>
                  )}
                </div>
                <div className="p-4">
                  <h3 className="font-semibold text-lg mb-2 group-hover:text-[#2c77d1] transition">
                    {product.name}
                  </h3>
                  <div className="flex items-center gap-2 mb-3">
                    <div className="flex items-center gap-1 text-yellow-400">
                      <Star className="w-4 h-4 fill-current" />
                      <span className="text-sm text-white">
                        {product.rating || 4.5}
                      </span>
                    </div>
                    <span className="text-gray-400 text-sm">
                      ({product.reviews_count || 0} reviews)
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-2xl font-bold text-[#2c77d1]">
                        ${product.price}
                      </span>
                      {product.old_price && (
                        <span className="text-gray-400 text-sm line-through ml-2">
                          ${product.old_price}
                        </span>
                      )}
                    </div>
                    <ShoppingBag className="w-5 h-5 text-[#9426f4] group-hover:scale-110 transition" />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Promo Banner */}
      <section className="py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="bg-gradient-to-r from-[#9426f4] to-[#2c77d1] rounded-3xl p-12 md:p-16 text-center">
            <div className="inline-flex items-center gap-2 bg-white/20 backdrop-blur-sm px-4 py-2 rounded-full mb-6">
              <TrendingUp className="w-4 h-4" />
              <span className="text-sm font-semibold">Flash Sale</span>
            </div>
            <h2 className="text-4xl md:text-5xl font-bold mb-4">
              Weekend Sale - Up to 60% Off
            </h2>
            <p className="text-xl text-gray-100 mb-8 max-w-2xl mx-auto">
              Don't miss out on incredible deals. Limited time offer on all electronics.
            </p>
            <Link
              to="/shop?sale=true"
              className="inline-flex items-center gap-2 bg-white text-[#9426f4] px-8 py-4 rounded-full font-bold text-lg hover:bg-gray-100 transition"
            >
              Shop Flash Sale <ChevronRight className="w-5 h-5" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}