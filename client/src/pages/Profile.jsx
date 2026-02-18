import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { User, Package, MapPin, Heart, Settings, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { changePassword, getMyOrders, updateUserProfile } from '../services/api';

const INITIAL_PASSWORDS = {
  old_password: '',
  new_password: '',
  new_password_confirm: '',
};

export default function Profile() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState(searchParams.get('tab') || 'profile');
  const [orders, setOrders] = useState([]);
  const [loadingOrders, setLoadingOrders] = useState(false);
  const [profileSaving, setProfileSaving] = useState(false);
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [feedback, setFeedback] = useState({ type: '', message: '' });
  const [profileForm, setProfileForm] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    bio: '',
    address: '',
    city: '',
    state: '',
    country: '',
  });
  const [passwordForm, setPasswordForm] = useState(INITIAL_PASSWORDS);

  useEffect(() => {
    if (!user) {
      navigate('/login', { replace: true });
      return;
    }

    setProfileForm((current) => ({
      ...current,
      first_name: user.first_name || '',
      last_name: user.last_name || '',
      phone: user.phone || '',
      bio: user.bio || '',
      address: user.address || '',
      city: user.city || '',
      state: user.state || '',
      country: user.country || '',
    }));
  }, [user, navigate]);

  useEffect(() => {
    if (activeTab === 'orders') {
      fetchOrders();
    }
  }, [activeTab]);

  const fetchOrders = async () => {
    try {
      setLoadingOrders(true);
      const data = await getMyOrders();
      setOrders(data.results || data || []);
    } catch (error) {
      setFeedback({ type: 'error', message: error?.message || 'Error fetching orders.' });
    } finally {
      setLoadingOrders(false);
    }
  };

  const handleLogout = () => {
    if (window.confirm('Are you sure you want to logout?')) {
      logout();
      navigate('/');
    }
  };

  const handleProfileSubmit = async (event) => {
    event.preventDefault();
    setFeedback({ type: '', message: '' });

    try {
      setProfileSaving(true);
      const updated = await updateUserProfile(profileForm);
      localStorage.setItem('user', JSON.stringify(updated));
      setFeedback({ type: 'success', message: 'Profile updated successfully.' });
    } catch (error) {
      setFeedback({ type: 'error', message: error?.message || 'Unable to update profile.' });
    } finally {
      setProfileSaving(false);
    }
  };

  const handlePasswordSubmit = async (event) => {
    event.preventDefault();
    setFeedback({ type: '', message: '' });

    if (passwordForm.new_password !== passwordForm.new_password_confirm) {
      setFeedback({ type: 'error', message: 'New passwords do not match.' });
      return;
    }

    try {
      setPasswordSaving(true);
      await changePassword(passwordForm);
      setPasswordForm(INITIAL_PASSWORDS);
      setFeedback({ type: 'success', message: 'Password changed successfully.' });
    } catch (error) {
      setFeedback({ type: 'error', message: error?.message || 'Unable to change password.' });
    } finally {
      setPasswordSaving(false);
    }
  };

  const tabs = useMemo(() => ([
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'orders', label: 'Orders', icon: Package },
    { id: 'addresses', label: 'Addresses', icon: MapPin },
    { id: 'wishlist', label: 'Wishlist', icon: Heart },
    { id: 'settings', label: 'Settings', icon: Settings },
  ]), []);

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen pt-20 pb-12 bg-gray-50 dark:bg-gray-900 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 className="text-4xl font-bold mb-8 text-gray-900 dark:text-white">My Account</h1>

        {feedback.message && (
          <p className={`mb-6 rounded-lg px-4 py-3 ${feedback.type === 'error' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300' : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'}`}>
            {feedback.message}
          </p>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          <div className="lg:col-span-1">
            <div className="bg-white dark:bg-[#050d1b] border border-gray-200 dark:border-[#2c77d1]/20 rounded-2xl p-6 shadow-md dark:shadow-lg">
              <div className="text-center mb-6 pb-6 border-b border-gray-200 dark:border-[#2c77d1]/20">
                <div className="w-20 h-20 bg-gradient-to-r from-[#2c77d1] to-[#9426f4] rounded-full flex items-center justify-center mx-auto mb-3 shadow-lg">
                  <span className="text-3xl font-bold text-white">
                    {user.first_name?.[0]}{user.last_name?.[0]}
                  </span>
                </div>
                <h3 className="font-semibold text-lg text-gray-900 dark:text-white">{user.first_name} {user.last_name}</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">{user.email}</p>
                <p className="text-xs text-gray-400 dark:text-gray-500 mt-2 capitalize">{user.role || 'buyer'}</p>
              </div>

              <nav className="space-y-2">
                {tabs.map((tab) => {
                  const Icon = tab.icon;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition ${
                        activeTab === tab.id
                          ? 'bg-gradient-to-r from-[#2c77d1] to-[#9426f4] text-white shadow-lg'
                          : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-[#2c77d1]/10'
                      }`}
                    >
                      <Icon className="w-5 h-5" />
                      <span>{tab.label}</span>
                    </button>
                  );
                })}
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10 transition"
                >
                  <LogOut className="w-5 h-5" />
                  <span>Logout</span>
                </button>
              </nav>
            </div>
          </div>

          <div className="lg:col-span-3">
            <div className="bg-white dark:bg-[#050d1b] border border-gray-200 dark:border-[#2c77d1]/20 rounded-2xl p-6 shadow-md dark:shadow-lg">
              {activeTab === 'profile' && (
                <div>
                  <h2 className="text-2xl font-bold mb-6 text-gray-900 dark:text-white">Profile Information</h2>
                  <form className="space-y-6" onSubmit={handleProfileSubmit}>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">First Name</label>
                        <input
                          type="text"
                          value={profileForm.first_name}
                          onChange={(event) => setProfileForm((current) => ({ ...current, first_name: event.target.value }))}
                          className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg px-4 py-3"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">Last Name</label>
                        <input
                          type="text"
                          value={profileForm.last_name}
                          onChange={(event) => setProfileForm((current) => ({ ...current, last_name: event.target.value }))}
                          className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg px-4 py-3"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">Phone</label>
                        <input
                          type="tel"
                          value={profileForm.phone}
                          onChange={(event) => setProfileForm((current) => ({ ...current, phone: event.target.value }))}
                          className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg px-4 py-3"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">Country</label>
                        <input
                          type="text"
                          value={profileForm.country}
                          onChange={(event) => setProfileForm((current) => ({ ...current, country: event.target.value }))}
                          className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg px-4 py-3"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">City</label>
                        <input
                          type="text"
                          value={profileForm.city}
                          onChange={(event) => setProfileForm((current) => ({ ...current, city: event.target.value }))}
                          className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg px-4 py-3"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">State</label>
                        <input
                          type="text"
                          value={profileForm.state}
                          onChange={(event) => setProfileForm((current) => ({ ...current, state: event.target.value }))}
                          className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg px-4 py-3"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">Address</label>
                      <input
                        type="text"
                        value={profileForm.address}
                        onChange={(event) => setProfileForm((current) => ({ ...current, address: event.target.value }))}
                        className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg px-4 py-3"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">Bio</label>
                      <textarea
                        rows="3"
                        value={profileForm.bio}
                        onChange={(event) => setProfileForm((current) => ({ ...current, bio: event.target.value }))}
                        className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg px-4 py-3"
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={profileSaving}
                      className="bg-gradient-to-r from-[#2c77d1] to-[#9426f4] text-white px-8 py-3 rounded-lg font-semibold hover:opacity-90 disabled:opacity-70"
                    >
                      {profileSaving ? 'Saving...' : 'Save Changes'}
                    </button>
                  </form>
                </div>
              )}

              {activeTab === 'orders' && (
                <div>
                  <h2 className="text-2xl font-bold mb-6 text-gray-900 dark:text-white">Order History</h2>
                  {loadingOrders ? (
                    <div className="flex justify-center py-12">
                      <div className="w-12 h-12 border-4 border-[#2c77d1] border-t-transparent rounded-full animate-spin"></div>
                    </div>
                  ) : orders.length === 0 ? (
                    <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                      <Package className="w-16 h-16 mx-auto mb-4 opacity-50" />
                      <p className="text-lg">No orders yet</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {orders.map((order) => (
                        <div key={order.id} className="border border-gray-200 dark:border-[#2c77d1]/20 bg-gray-50 dark:bg-gray-800 rounded-lg p-6">
                          <div className="flex justify-between items-start mb-4">
                            <div>
                              <p className="font-semibold text-lg text-gray-900 dark:text-white">Order #{order.order_number || order.id}</p>
                              <p className="text-sm text-gray-500 dark:text-gray-400">{new Date(order.created_at).toLocaleDateString()}</p>
                            </div>
                            <span className="px-3 py-1 rounded-full text-sm font-semibold bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">{order.status}</span>
                          </div>
                          <div className="flex justify-between items-center">
                            <p className="text-gray-600 dark:text-gray-300">{order.items_count || order.items?.length || 0} items</p>
                            <p className="text-xl font-bold text-[#2c77d1]">${order.total}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'addresses' && (
                <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                  <MapPin className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p>Use dedicated address management for full CRUD operations.</p>
                  <Link to="/shipping-addresses" className="inline-block mt-4 bg-gradient-to-r from-[#2c77d1] to-[#9426f4] text-white px-6 py-2 rounded-full font-semibold hover:opacity-90 transition">
                    Manage Addresses
                  </Link>
                </div>
              )}

              {activeTab === 'wishlist' && (
                <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                  <Heart className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p>Wishlist moved to Favorites for consistency.</p>
                  <Link to="/favorites" className="inline-block mt-4 bg-gradient-to-r from-[#2c77d1] to-[#9426f4] text-white px-6 py-2 rounded-full font-semibold hover:opacity-90 transition">
                    Open Favorites
                  </Link>
                </div>
              )}

              {activeTab === 'settings' && (
                <div>
                  <h2 className="text-2xl font-bold mb-6 text-gray-900 dark:text-white">Account Settings</h2>
                  <div className="space-y-6">
                    <div>
                      <h3 className="font-semibold mb-4 text-gray-900 dark:text-white">Change Password</h3>
                      <form className="space-y-4" onSubmit={handlePasswordSubmit}>
                        <div>
                          <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">Current Password</label>
                          <input
                            type="password"
                            required
                            value={passwordForm.old_password}
                            onChange={(event) => setPasswordForm((current) => ({ ...current, old_password: event.target.value }))}
                            className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-4 py-3 text-gray-900 dark:text-white"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">New Password</label>
                          <input
                            type="password"
                            required
                            value={passwordForm.new_password}
                            onChange={(event) => setPasswordForm((current) => ({ ...current, new_password: event.target.value }))}
                            className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-4 py-3 text-gray-900 dark:text-white"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">Confirm New Password</label>
                          <input
                            type="password"
                            required
                            value={passwordForm.new_password_confirm}
                            onChange={(event) => setPasswordForm((current) => ({ ...current, new_password_confirm: event.target.value }))}
                            className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-4 py-3 text-gray-900 dark:text-white"
                          />
                        </div>
                        <button
                          type="submit"
                          disabled={passwordSaving}
                          className="bg-gradient-to-r from-[#2c77d1] to-[#9426f4] text-white px-8 py-3 rounded-lg font-semibold hover:opacity-90 disabled:opacity-70"
                        >
                          {passwordSaving ? 'Updating...' : 'Update Password'}
                        </button>
                      </form>
                    </div>

                    <div className="border-t border-[#2c77d1]/20 pt-6">
                      <h3 className="font-semibold mb-2 text-red-400">Danger Zone</h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">Account deletion is disabled in Phase 1 to avoid accidental data loss during testing.</p>
                      <button disabled className="border-2 border-red-500/60 text-red-400/60 px-6 py-2 rounded-full font-semibold cursor-not-allowed">
                        Delete Account (Coming in Phase 2)
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
