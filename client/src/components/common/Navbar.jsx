import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ShoppingCart, Search, Menu, X, User, Settings, LogOut, Headset, Package, Store, Inbox } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useCart } from '../../context/CartContext';
import ThemeToggle from './ThemeToggle';

export default function Navbar() {
  const navigate = useNavigate();
  const { user, logout, isAuthenticated } = useAuth();
  const { cartCount } = useCart();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const closeMenus = () => {
    setMobileMenuOpen(false);
    setProfileMenuOpen(false);
  };

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/shop?search=${encodeURIComponent(searchQuery.trim())}`);
      setSearchQuery('');
      setMobileMenuOpen(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    closeMenus();
    navigate('/');
  };

  return (
    <nav className="fixed top-0 w-full bg-white dark:bg-[#050d1b] border-b border-gray-200 dark:border-[#2c77d1]/20 z-50 shadow-sm dark:shadow-lg transition-colors duration-300">
      <div className="hidden lg:block border-b border-gray-200 dark:border-[#2c77d1]/20 bg-gray-50/70 dark:bg-[#020617]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-10 flex items-center justify-between text-xs text-gray-600 dark:text-gray-300">
          <div className="flex items-center gap-4">
            <span>Deliver to: NG</span>
            <span>Currency: NGN</span>
          </div>
          <div className="flex items-center gap-4">
            <Link to="/orders" className="hover:text-blue-600 dark:hover:text-[#2c77d1] transition">Orders</Link>
            <Link to="/faqs" className="hover:text-blue-600 dark:hover:text-[#2c77d1] transition">Help Center</Link>
            {!user && (
              <Link to="/signup" className="hover:text-blue-600 dark:hover:text-[#2c77d1] transition">Create account</Link>
            )}
            {user && user.role !== 'seller' && (
              <Link to="/seller" className="hover:text-blue-600 dark:hover:text-[#2c77d1] transition">Become a seller</Link>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-2 sm:gap-3">
            <Link
              to="/"
              className="text-xl sm:text-2xl font-bold bg-gradient-to-r from-blue-600 dark:from-[#2c77d1] to-purple-600 dark:to-[#9426f4] bg-clip-text text-transparent hover:opacity-80 transition"
              onClick={closeMenus}
            >
              ZUNTO
            </Link>
            <span className="hidden sm:inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300">
              GIGI AI
            </span>
          </div>

          <div className="hidden md:flex items-center gap-6">
            <Link to="/" className="text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-[#2c77d1] font-medium transition">Home</Link>
            <Link to="/shop" className="text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-[#2c77d1] font-medium transition">Products</Link>
            <Link to="/shop?mode=ai" className="text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-[#2c77d1] font-medium transition">AI Mode</Link>
            {user?.role === 'admin' && <Link to="/admin" className="text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-[#2c77d1] font-medium transition">Admin</Link>}
            {user?.role === 'seller' && <Link to="/seller" className="text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-[#2c77d1] font-medium transition">Seller</Link>}
          </div>

          <div className="hidden md:flex items-center gap-3">
            <form onSubmit={handleSearch} className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search products..."
                className="bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-full pl-10 pr-4 py-2 w-64 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:border-blue-600 dark:focus:border-[#2c77d1] transition"
              />
              <Search className="absolute left-3 top-2.5 w-5 h-5 text-gray-400" />
            </form>

            <ThemeToggle />

            <Link to="/cart" className="relative p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition" aria-label="Cart">
              <ShoppingCart className="w-6 h-6 text-gray-700 dark:text-gray-300" />
              {cartCount > 0 && (
                <span className="absolute -top-1 -right-1 bg-gradient-to-r from-blue-600 to-purple-600 text-white text-xs w-5 h-5 rounded-full flex items-center justify-center font-semibold">
                  {cartCount}
                </span>
              )}
            </Link>

            {isAuthenticated && (
              <Link to="/chat?mode=customer-service" className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition" aria-label="Customer Service">
                <Headset className="w-6 h-6 text-gray-700 dark:text-gray-300" />
              </Link>
            )}

            <Link to="/chat" className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition" aria-label="Inbox">
              <Inbox className="w-6 h-6 text-gray-700 dark:text-gray-300" />
            </Link>

            {isAuthenticated ? (
              <div className="relative">
                <button onClick={() => setProfileMenuOpen(!profileMenuOpen)} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition" aria-label="Account">
                  <User className="w-6 h-6 text-gray-700 dark:text-gray-300" />
                </button>
                {profileMenuOpen && (
                  <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-gray-800 rounded-lg shadow-lg dark:shadow-xl border border-gray-200 dark:border-gray-700 py-2 z-50">
                    <Link to="/profile" onClick={closeMenus} className="block px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition"><User className="w-4 h-4 inline mr-2" /> Profile</Link>
                    <Link to="/orders" onClick={closeMenus} className="block px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition"><Package className="w-4 h-4 inline mr-2" /> Orders</Link>
                    <Link to="/faqs" onClick={closeMenus} className="block px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition"><Headset className="w-4 h-4 inline mr-2" /> Help Center</Link>
                    {user?.role !== 'seller' && <Link to="/seller" onClick={closeMenus} className="block px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition"><Store className="w-4 h-4 inline mr-2" /> Become a Seller</Link>}
                    {user?.role === 'seller' && <Link to="/seller" onClick={closeMenus} className="block px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition"><Settings className="w-4 h-4 inline mr-2" /> Seller Dashboard</Link>}
                    <button onClick={handleLogout} className="w-full text-left px-4 py-2 text-red-600 dark:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition"><LogOut className="w-4 h-4 inline mr-2" /> Logout</button>
                  </div>
                )}
              </div>
            ) : (
              <Link to="/login" className="px-4 py-2 rounded-full bg-gradient-to-r from-[#2c77d1] to-[#9426f4] text-white text-sm font-semibold hover:opacity-90 transition">Sign in</Link>
            )}
          </div>

          <div className="md:hidden flex items-center gap-2">
            <ThemeToggle />
            <button className="p-2" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
              {mobileMenuOpen ? <X className="w-6 h-6 text-gray-700 dark:text-gray-300" /> : <Menu className="w-6 h-6 text-gray-700 dark:text-gray-300" />}
            </button>
          </div>
        </div>
      </div>

      {mobileMenuOpen && (
        <div className="md:hidden bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 transition-colors">
          <div className="px-4 py-4 space-y-4">
            <form onSubmit={handleSearch} className="relative">
              <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="Search products..." className="w-full bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-full pl-10 pr-4 py-2 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:border-blue-600 dark:focus:border-[#2c77d1] transition" />
              <Search className="absolute left-3 top-2.5 w-5 h-5 text-gray-400" />
            </form>

            <div className="flex flex-col gap-2">
              <Link to="/" className="py-2 text-gray-700 dark:text-gray-300 font-medium" onClick={closeMenus}>Home</Link>
              <Link to="/shop" className="py-2 text-gray-700 dark:text-gray-300 font-medium" onClick={closeMenus}>Products</Link>
              <Link to="/shop?mode=ai" className="py-2 text-gray-700 dark:text-gray-300 font-medium" onClick={closeMenus}>AI Mode</Link>
              <Link to="/orders" className="py-2 text-gray-700 dark:text-gray-300 font-medium" onClick={closeMenus}>Orders</Link>
              <Link to="/chat" className="py-2 text-gray-700 dark:text-gray-300 font-medium" onClick={closeMenus}>Inbox</Link>
              {isAuthenticated && <Link to="/chat?mode=customer-service" className="py-2 text-gray-700 dark:text-gray-300 font-medium" onClick={closeMenus}>Customer Service</Link>}
              <Link to="/faqs" className="py-2 text-gray-700 dark:text-gray-300 font-medium" onClick={closeMenus}>Help Center</Link>
              {user?.role !== 'seller' && <Link to="/seller" className="py-2 text-gray-700 dark:text-gray-300 font-medium" onClick={closeMenus}>Become a Seller</Link>}
              {user?.role === 'seller' && <Link to="/seller" className="py-2 text-gray-700 dark:text-gray-300 font-medium" onClick={closeMenus}>Seller Dashboard</Link>}

              {isAuthenticated ? (
                <>
                  <Link to="/profile" className="py-2 text-gray-700 dark:text-gray-300 font-medium" onClick={closeMenus}>Profile</Link>
                  <button onClick={handleLogout} className="w-full text-left py-2 text-red-600 dark:text-red-400 font-medium">Logout</button>
                </>
              ) : (
                <Link to="/login" className="py-2 text-gray-700 dark:text-gray-300 font-medium" onClick={closeMenus}>Login</Link>
              )}

              <Link to="/cart" className="py-2 text-gray-700 dark:text-gray-300 font-medium flex items-center justify-between" onClick={closeMenus}>
                Cart
                {cartCount > 0 && <span className="bg-gradient-to-r from-blue-600 to-purple-600 text-white text-xs w-6 h-6 rounded-full flex items-center justify-center font-semibold">{cartCount}</span>}
              </Link>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}
