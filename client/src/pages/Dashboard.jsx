import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { BarChart3, TrendingUp, Users, ShoppingCart, DollarSign, Package } from 'lucide-react';
import { getOrderStatistics, getSellerStatistics } from '../services/api';

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) {
      navigate('/login');
      return;
    }

    if (!user.is_verified) {
      const email = user.email ? encodeURIComponent(user.email) : '';
      navigate(`/verify-registration?email=${email}`);
      return;
    }

    if (user.role === 'buyer') {
      fetchBuyerStats();
    } else if (user.role === 'seller') {
      fetchSellerStats();
    }
  }, [user]);

  const fetchBuyerStats = async () => {
    try {
      const data = await getOrderStatistics();
      setStats(data);
    } catch (err) {
      console.error('Error fetching buyer stats:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchSellerStats = async () => {
    try {
      const data = await getSellerStatistics();
      setStats(data);
    } catch (err) {
      console.error('Error fetching seller stats:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center pt-20">
        <div className="w-16 h-16 border-4 border-[#2c77d1] border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (user?.role === 'buyer') {
    return (
      <div className="min-h-screen pt-20 pb-12">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="mb-8">
            <h1 className="text-4xl font-bold mb-2">Welcome Back, {user?.first_name}!</h1>
            <p className="text-gray-400">Here's your activity overview</p>
          </div>

          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div className="bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-400">Total Orders</h3>
                <div className="w-12 h-12 bg-[#2c77d1]/10 rounded-lg flex items-center justify-center">
                  <ShoppingCart className="w-6 h-6 text-[#2c77d1]" />
                </div>
              </div>
              <p className="text-3xl font-bold">{stats?.total_orders || 0}</p>
              <p className="text-sm text-gray-400 mt-2">Lifetime purchases</p>
            </div>

            <div className="bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-400">Total Spent</h3>
                <div className="w-12 h-12 bg-green-500/10 rounded-lg flex items-center justify-center">
                  <DollarSign className="w-6 h-6 text-green-400" />
                </div>
              </div>
              <p className="text-3xl font-bold">${(stats?.total_spent || 0).toFixed(2)}</p>
              <p className="text-sm text-gray-400 mt-2">Total expenditure</p>
            </div>

            <div className="bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-400">Completed</h3>
                <div className="w-12 h-12 bg-purple-500/10 rounded-lg flex items-center justify-center">
                  <Package className="w-6 h-6 text-purple-400" />
                </div>
              </div>
              <p className="text-3xl font-bold">{stats?.completed_orders || 0}</p>
              <p className="text-sm text-gray-400 mt-2">Delivered orders</p>
            </div>

            <div className="bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-400">Avg. Order</h3>
                <div className="w-12 h-12 bg-yellow-500/10 rounded-lg flex items-center justify-center">
                  <TrendingUp className="w-6 h-6 text-yellow-400" />
                </div>
              </div>
              <p className="text-3xl font-bold">
                ${stats?.total_orders > 0 ? (stats?.total_spent / stats?.total_orders).toFixed(2) : '0.00'}
              </p>
              <p className="text-sm text-gray-400 mt-2">Per order value</p>
            </div>
          </div>

          {/* Recent Activity */}
          <div className="bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl p-6">
            <h2 className="text-2xl font-bold mb-6">Order Status Breakdown</h2>
            <div className="space-y-4">
              {stats?.status_breakdown ? (
                Object.entries(stats.status_breakdown).map(([status, count]) => (
                  <div key={status}>
                    <div className="flex justify-between mb-2">
                      <span className="capitalize text-gray-300">{status}</span>
                      <span className="font-semibold">{count}</span>
                    </div>
                    <div className="w-full bg-[#2c77d1]/10 rounded-full h-2">
                      <div
                        className="bg-gradient-to-r from-[#2c77d1] to-[#9426f4] h-2 rounded-full"
                        style={{ width: `${(count / (stats?.total_orders || 1)) * 100}%` }}
                      ></div>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-gray-400">No order data available</p>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Seller Dashboard
  if (user?.role === 'seller') {
    return (
      <div className="min-h-screen pt-20 pb-12">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="mb-8">
            <h1 className="text-4xl font-bold mb-2">Seller Dashboard</h1>
            <p className="text-gray-400">Track your sales and performance</p>
          </div>

          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div className="bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-400">Total Sales</h3>
                <div className="w-12 h-12 bg-[#2c77d1]/10 rounded-lg flex items-center justify-center">
                  <DollarSign className="w-6 h-6 text-[#2c77d1]" />
                </div>
              </div>
              <p className="text-3xl font-bold">${(stats?.total_revenue || 0).toFixed(2)}</p>
              <p className="text-sm text-gray-400 mt-2">Total revenue</p>
            </div>

            <div className="bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-400">Total Orders</h3>
                <div className="w-12 h-12 bg-green-500/10 rounded-lg flex items-center justify-center">
                  <ShoppingCart className="w-6 h-6 text-green-400" />
                </div>
              </div>
              <p className="text-3xl font-bold">{stats?.total_orders || 0}</p>
              <p className="text-sm text-gray-400 mt-2">Completed sales</p>
            </div>

            <div className="bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-400">Active Products</h3>
                <div className="w-12 h-12 bg-purple-500/10 rounded-lg flex items-center justify-center">
                  <Package className="w-6 h-6 text-purple-400" />
                </div>
              </div>
              <p className="text-3xl font-bold">{stats?.active_products || 0}</p>
              <p className="text-sm text-gray-400 mt-2">Listings</p>
            </div>

            <div className="bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-400">Avg. Rating</h3>
                <div className="w-12 h-12 bg-yellow-500/10 rounded-lg flex items-center justify-center">
                  <TrendingUp className="w-6 h-6 text-yellow-400" />
                </div>
              </div>
              <p className="text-3xl font-bold">{(stats?.average_rating || 0).toFixed(1)} ⭐</p>
              <p className="text-sm text-gray-400 mt-2">Customer rating</p>
            </div>
          </div>

          {/* Performance Cards */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Sales Chart */}
            <div className="bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl p-6">
              <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
                <BarChart3 className="w-5 h-5" />
                Revenue Overview
              </h2>
              <div className="space-y-4">
                {stats?.monthly_revenue ? (
                  Object.entries(stats.monthly_revenue).map(([month, revenue]) => (
                    <div key={month}>
                      <div className="flex justify-between mb-2">
                        <span className="text-gray-300">{month}</span>
                        <span className="font-semibold">${revenue.toFixed(2)}</span>
                      </div>
                      <div className="w-full bg-[#2c77d1]/10 rounded-full h-3">
                        <div
                          className="bg-gradient-to-r from-green-500 to-green-400 h-3 rounded-full"
                          style={{
                            width: `${Math.min(100, (revenue / Object.values(stats.monthly_revenue || {}).reduce((a, b) => Math.max(a, b), 1)) * 100)}%`,
                          }}
                        ></div>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-gray-400">No sales data yet</p>
                )}
              </div>
            </div>

            {/* Product Performance */}
            <div className="bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl p-6">
              <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
                <Package className="w-5 h-5" />
                Top Products
              </h2>
              <div className="space-y-4">
                {stats?.top_products && stats.top_products.length > 0 ? (
                  stats.top_products.map((product, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 bg-[#2c77d1]/5 rounded-lg">
                      <div>
                        <p className="font-semibold text-sm">{product.name}</p>
                        <p className="text-xs text-gray-400">{product.sales} sales</p>
                      </div>
                      <span className="text-sm font-bold text-[#2c77d1]">${product.revenue.toFixed(2)}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-gray-400">No product data yet</p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Admin Dashboard
  return (
    <div className="min-h-screen pt-20 pb-12">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Admin Dashboard</h1>
          <p className="text-gray-400">Platform analytics and management</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-400">Total Users</h3>
              <Users className="w-6 h-6 text-[#2c77d1]" />
            </div>
            <p className="text-3xl font-bold">Coming Soon</p>
          </div>

          <div className="bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-400">Total Revenue</h3>
              <DollarSign className="w-6 h-6 text-green-400" />
            </div>
            <p className="text-3xl font-bold">Coming Soon</p>
          </div>

          <div className="bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-400">Active Sellers</h3>
              <Package className="w-6 h-6 text-purple-400" />
            </div>
            <p className="text-3xl font-bold">Coming Soon</p>
          </div>

          <div className="bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-400">Platform Growth</h3>
              <TrendingUp className="w-6 h-6 text-yellow-400" />
            </div>
            <p className="text-3xl font-bold">Coming Soon</p>
          </div>
        </div>

        <div className="bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl p-6 text-center py-12">
          <p className="text-gray-400">Admin analytics features coming soon</p>
        </div>
      </div>
    </div>
  );
}
