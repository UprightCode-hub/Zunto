import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { User, Package, MapPin, Heart, Settings, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { getOrders } from '../services/api';

export default function Profile() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState(searchParams.get('tab') || 'profile');
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (activeTab === 'orders') {
      fetchOrders();
    }
  }, [activeTab]);

  const fetchOrders = async () => {
    try {
      setLoading(true);
      const data = await getOrders();
      setOrders(data.results || data);
    } catch (error) {
      console.error('Error fetching orders:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    if (window.confirm('Are you sure you want to logout?')) {
      logout();
      navigate('/');
    }
  };

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'orders', label: 'Orders', icon: Package },
    { id: 'addresses', label: 'Addresses', icon: MapPin },
    { id: 'wishlist', label: 'Wishlist', icon: Heart },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  if (!user) {
    navigate('/login');
    return null;
  }

  return (
    <div className="min-h-screen pt-20 pb-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 className="text-4xl font-bold mb-8">My Account</h1>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Sidebar */}
          <div className="lg:col-span-1">
            <div className="bg-[#050d1b] border border-[#2c77d1]/20 rounded-2xl p-6">
              {/* User Info */}
              <div className="text-center mb-6 pb-6 border-b border-[#2c77d1]/20">
                <div className="w-20 h-20 bg-gradient-to-r from-[#2c77d1] to-[#9426f4] rounded-full flex items-center justify-center mx-auto mb-3">
                  <span className="text-3xl font-bold">
                    {user.first_name?.[0]}{user.last_name?.[0]}
                  </span>
                </div>
                <h3 className="font-semibold text-lg">
                  {user.first_name} {user.last_name}
                </h3>
                <p className="text-sm text-gray-400">{user.email}</p>
              </div>

              {/* Navigation */}
              <nav className="space-y-2">
                {tabs.map((tab) => {
                  const Icon = tab.icon;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition ${
                        activeTab === tab.id
                          ? 'bg-gradient-to-r from-[#2c77d1] to-[#9426f4]'
                          : 'hover:bg-[#2c77d1]/10'
                      }`}
                    >
                      <Icon className="w-5 h-5" />
                      <span>{tab.label}</span>
                    </button>
                  );
                })}
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-red-500/10 text-red-400 transition"
                >
                  <LogOut className="w-5 h-5" />
                  <span>Logout</span>
                </button>
              </nav>
            </div>
          </div>

          {/* Content */}
          <div className="lg:col-span-3">
            <div className="bg-[#050d1b] border border-[#2c77d1]/20 rounded-2xl p-6">
              {/* Profile Tab */}
              {activeTab === 'profile' && (
                <div>
                  <h2 className="text-2xl font-bold mb-6">Profile Information</h2>
                  <form className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium mb-2">First Name</label>
                        <input
                          type="text"
                          defaultValue={user.first_name}
                          className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-3 focus:outline-none focus:border-[#2c77d1]"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-2">Last Name</label>
                        <input
                          type="text"
                          defaultValue={user.last_name}
                          className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-3 focus:outline-none focus:border-[#2c77d1]"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-2">Email</label>
                        <input
                          type="email"
                          defaultValue={user.email}
                          className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-3 focus:outline-none focus:border-[#2c77d1]"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-2">Phone</label>
                        <input
                          type="tel"
                          defaultValue={user.phone}
                          className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-3 focus:outline-none focus:border-[#2c77d1]"
                        />
                      </div>
                    </div>
                    <button
                      type="submit"
                      className="bg-gradient-to-r from-[#2c77d1] to-[#9426f4] px-8 py-3 rounded-full font-semibold hover:opacity-90 transition"
                    >
                      Save Changes
                    </button>
                  </form>
                </div>
              )}

              {/* Orders Tab */}
              {activeTab === 'orders' && (
                <div>
                  <h2 className="text-2xl font-bold mb-6">Order History</h2>
                  {loading ? (
                    <div className="flex justify-center py-12">
                      <div className="w-12 h-12 border-4 border-[#2c77d1] border-t-transparent rounded-full animate-spin"></div>
                    </div>
                  ) : orders.length === 0 ? (
                    <div className="text-center py-12 text-gray-400">
                      <Package className="w-16 h-16 mx-auto mb-4 opacity-50" />
                      <p>No orders yet</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {orders.map((order) => (
                        <div
                          key={order.id}
                          className="border border-[#2c77d1]/20 rounded-lg p-6 hover:border-[#2c77d1] transition"
                        >
                          <div className="flex justify-between items-start mb-4">
                            <div>
                              <p className="font-semibold text-lg">Order #{order.id}</p>
                              <p className="text-sm text-gray-400">
                                {new Date(order.created_at).toLocaleDateString()}
                              </p>
                            </div>
                            <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
                              order.status === 'delivered' ? 'bg-green-500/20 text-green-400' :
                              order.status === 'shipped' ? 'bg-blue-500/20 text-blue-400' :
                              order.status === 'processing' ? 'bg-yellow-500/20 text-yellow-400' :
                              'bg-gray-500/20 text-gray-400'
                            }`}>
                              {order.status}
                            </span>
                          </div>
                          <div className="flex justify-between items-center">
                            <p className="text-gray-300">
                              {order.items_count || order.items?.length || 0} items
                            </p>
                            <p className="text-xl font-bold text-[#2c77d1]">
                              ${order.total}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Addresses Tab */}
              {activeTab === 'addresses' && (
                <div>
                  <h2 className="text-2xl font-bold mb-6">Saved Addresses</h2>
                  <div className="text-center py-12 text-gray-400">
                    <MapPin className="w-16 h-16 mx-auto mb-4 opacity-50" />
                    <p>No saved addresses</p>
                    <button className="mt-4 bg-gradient-to-r from-[#2c77d1] to-[#9426f4] px-6 py-2 rounded-full font-semibold hover:opacity-90 transition">
                      Add Address
                    </button>
                  </div>
                </div>
              )}

              {/* Wishlist Tab */}
              {activeTab === 'wishlist' && (
                <div>
                  <h2 className="text-2xl font-bold mb-6">My Wishlist</h2>
                  <div className="text-center py-12 text-gray-400">
                    <Heart className="w-16 h-16 mx-auto mb-4 opacity-50" />
                    <p>Your wishlist is empty</p>
                  </div>
                </div>
              )}

              {/* Settings Tab */}
              {activeTab === 'settings' && (
                <div>
                  <h2 className="text-2xl font-bold mb-6">Account Settings</h2>
                  <div className="space-y-6">
                    <div>
                      <h3 className="font-semibold mb-4">Change Password</h3>
                      <form className="space-y-4">
                        <div>
                          <label className="block text-sm font-medium mb-2">Current Password</label>
                          <input
                            type="password"
                            className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-3 focus:outline-none focus:border-[#2c77d1]"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium mb-2">New Password</label>
                          <input
                            type="password"
                            className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-3 focus:outline-none focus:border-[#2c77d1]"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium mb-2">Confirm New Password</label>
                          <input
                            type="password"
                            className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg px-4 py-3 focus:outline-none focus:border-[#2c77d1]"
                          />
                        </div>
                        <button
                          type="submit"
                          className="bg-gradient-to-r from-[#2c77d1] to-[#9426f4] px-8 py-3 rounded-full font-semibold hover:opacity-90 transition"
                        >
                          Update Password
                        </button>
                      </form>
                    </div>

                    <div className="border-t border-[#2c77d1]/20 pt-6">
                      <h3 className="font-semibold mb-4 text-red-400">Danger Zone</h3>
                      <button className="border-2 border-red-500 text-red-400 px-6 py-2 rounded-full font-semibold hover:bg-red-500/10 transition">
                        Delete Account
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}