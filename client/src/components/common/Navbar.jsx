import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ShoppingCart, Search, Menu, X, User, Settings, LogOut } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useCart } from '../../context/CartContext';
import ThemeToggle from './ThemeToggle';

export default function Navbar() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { cartCount } = useCart();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/shop?search=${searchQuery}`);
      setSearchQuery('');
      setMobileMenuOpen(false);
    }
  };

  return (
    <nav className="fixed top-0 w-full bg-white dark:bg-[#050d1b] border-b border-gray-200 dark:border-[#2c77d1]/20 z-50 shadow-sm dark:shadow-lg transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center gap-2 sm:gap-3">
            <Link 
              to="/" 
              className="text-xl sm:text-2xl font-bold bg-gradient-to-r from-blue-600 dark:from-[#2c77d1] to-purple-600 dark:to-[#9426f4] bg-clip-text text-transparent hover:opacity-80 transition"
            >
              ZUNTO
            </Link>
            <span className="hidden sm:inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300">
              GIGI AI
            </span>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-8">
            <Link to="/" className="text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-[#2c77d1] font-medium transition">
              Home
            </Link>
            <Link to="/shop" className="text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-[#2c77d1] font-medium transition">
              Shop
            </Link>
            <Link to="/faqs" className="text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-[#2c77d1] font-medium transition">
              FAQs
            </Link>
            {user && user.role === 'admin' && (
              <Link to="/admin" className="text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-[#2c77d1] font-medium transition">
                Admin
              </Link>
            )}
            {user && user.role === 'seller' && (
              <Link to="/seller" className="text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-[#2c77d1] font-medium transition">
                Seller
              </Link>
            )}
          </div>

          {/* Desktop Search & Actions */}
          <div className="hidden md:flex items-center gap-4">
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

            {user ? (
              <div className="relative">
                <button
                  onClick={() => setProfileMenuOpen(!profileMenuOpen)}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition"
                >
                  <User className="w-6 h-6 text-gray-700 dark:text-gray-300" />
                </button>
                {profileMenuOpen && (
                  <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg dark:shadow-xl border border-gray-200 dark:border-gray-700 py-2 z-50">
                    <Link to="/profile" className="block px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition">
                      <User className="w-4 h-4 inline mr-2" /> Profile
                    </Link>
                    <Link to="/seller" className="block px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition">
                      <Settings className="w-4 h-4 inline mr-2" /> Seller Dashboard
                    </Link>
                    <button className="w-full text-left px-4 py-2 text-red-600 dark:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition">
                      <LogOut className="w-4 h-4 inline mr-2" /> Logout
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <Link 
                to="/login"
                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-[#2c77d1] font-medium transition"
              >
                Login
              </Link>
            )}

            <Link 
              to="/cart"
              className="relative p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition"
            >
              <ShoppingCart className="w-6 h-6 text-gray-700 dark:text-gray-300" />
              {cartCount > 0 && (
                <span className="absolute -top-1 -right-1 bg-gradient-to-r from-blue-600 to-purple-600 text-white text-xs w-5 h-5 rounded-full flex items-center justify-center font-semibold">
                  {cartCount}
                </span>
              )}
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <div className="md:hidden flex items-center gap-2">
            <ThemeToggle />
            <button 
              className="p-2"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? <X className="w-6 h-6 text-gray-700 dark:text-gray-300" /> : <Menu className="w-6 h-6 text-gray-700 dark:text-gray-300" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 transition-colors">
          <div className="px-4 py-4 space-y-4">
            <form onSubmit={handleSearch} className="relative">
              <input 
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search products..." 
                className="w-full bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-full pl-10 pr-4 py-2 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:border-blue-600 dark:focus:border-[#2c77d1] transition"
              />
              <Search className="absolute left-3 top-2.5 w-5 h-5 text-gray-400" />
            </form>

            <div className="flex flex-col gap-2">
              <Link 
                to="/" 
                className="py-2 text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-[#2c77d1] font-medium transition"
                onClick={() => setMobileMenuOpen(false)}
              >
                Home
              </Link>
              <Link 
                to="/shop" 
                className="py-2 text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-[#2c77d1] font-medium transition"
                onClick={() => setMobileMenuOpen(false)}
              >
                Shop
              </Link>
              <Link 
                to="/faqs" 
                className="py-2 text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-[#2c77d1] font-medium transition"
                onClick={() => setMobileMenuOpen(false)}
              >
                FAQs
              </Link>
              {user && user.role === 'admin' && (
                <Link 
                  to="/admin" 
                  className="py-2 text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-[#2c77d1] font-medium transition"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  Admin
                </Link>
              )}
              {user && user.role === 'seller' && (
                <Link 
                  to="/seller" 
                  className="py-2 text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-[#2c77d1] font-medium transition"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  Seller
                </Link>
              )}
              {user ? (
                <>
                  <Link 
                    to="/profile" 
                    className="py-2 text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-[#2c77d1] font-medium transition"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    Profile
                  </Link>
                  <button className="w-full text-left py-2 text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 font-medium transition">
                    Logout
                  </button>
                </>
              ) : (
                <Link 
                  to="/login" 
                  className="py-2 text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-[#2c77d1] font-medium transition"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  Login
                </Link>
              )}
              <Link 
                to="/cart" 
                className="py-2 text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-[#2c77d1] font-medium transition flex items-center justify-between"
                onClick={() => setMobileMenuOpen(false)}
              >
                Cart
                {cartCount > 0 && (
                  <span className="bg-gradient-to-r from-blue-600 to-purple-600 text-white text-xs w-6 h-6 rounded-full flex items-center justify-center font-semibold">
                    {cartCount}
                  </span>
                )}
              </Link>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}