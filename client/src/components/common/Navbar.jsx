import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ShoppingCart, Search, Menu, X, User } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useCart } from '../../context/CartContext';

export default function Navbar() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { cartCount } = useCart();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
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
    <nav className="fixed top-0 w-full bg-[#050d1b]/95 backdrop-blur-sm border-b border-[#2c77d1]/20 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link 
            to="/" 
            className="text-2xl font-bold bg-gradient-to-r from-[#2c77d1] to-[#9426f4] bg-clip-text text-transparent"
          >
            ZUNTO
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-6">
            <Link to="/" className="hover:text-[#2c77d1] transition">
              Home
            </Link>
            <Link to="/shop" className="hover:text-[#2c77d1] transition">
              Shop
            </Link>
            <Link to="/shop?sale=true" className="hover:text-[#2c77d1] transition">
              Deals
            </Link>
          </div>

          {/* Desktop Search & Actions */}
          <div className="hidden md:flex items-center gap-4">
            <form onSubmit={handleSearch} className="relative">
              <input 
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search products..." 
                className="bg-[#050d1b] border border-[#2c77d1]/30 rounded-full pl-10 pr-4 py-2 w-64 focus:outline-none focus:border-[#2c77d1]"
              />
              <Search className="absolute left-3 top-2.5 w-5 h-5 text-gray-400" />
            </form>

            {user ? (
              <Link 
                to="/profile"
                className="p-2 hover:bg-[#2c77d1]/10 rounded-full transition"
              >
                <User className="w-6 h-6" />
              </Link>
            ) : (
              <Link 
                to="/login"
                className="px-4 py-2 hover:text-[#2c77d1] transition"
              >
                Login
              </Link>
            )}

            <Link 
              to="/cart"
              className="relative p-2 hover:bg-[#2c77d1]/10 rounded-full transition"
            >
              <ShoppingCart className="w-6 h-6" />
              {cartCount > 0 && (
                <span className="absolute -top-1 -right-1 bg-[#9426f4] text-xs w-5 h-5 rounded-full flex items-center justify-center">
                  {cartCount}
                </span>
              )}
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <button 
            className="md:hidden p-2"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-[#050d1b] border-t border-[#2c77d1]/20">
          <div className="px-4 py-4 space-y-4">
            <form onSubmit={handleSearch} className="relative">
              <input 
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search products..." 
                className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-full pl-10 pr-4 py-2 focus:outline-none focus:border-[#2c77d1]"
              />
              <Search className="absolute left-3 top-2.5 w-5 h-5 text-gray-400" />
            </form>

            <div className="flex flex-col gap-2">
              <Link 
                to="/" 
                className="py-2 hover:text-[#2c77d1]"
                onClick={() => setMobileMenuOpen(false)}
              >
                Home
              </Link>
              <Link 
                to="/shop" 
                className="py-2 hover:text-[#2c77d1]"
                onClick={() => setMobileMenuOpen(false)}
              >
                Shop
              </Link>
              <Link 
                to="/shop?sale=true" 
                className="py-2 hover:text-[#2c77d1]"
                onClick={() => setMobileMenuOpen(false)}
              >
                Deals
              </Link>
              {user ? (
                <Link 
                  to="/profile" 
                  className="py-2 hover:text-[#2c77d1]"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  Profile
                </Link>
              ) : (
                <Link 
                  to="/login" 
                  className="py-2 hover:text-[#2c77d1]"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  Login
                </Link>
              )}
              <Link 
                to="/cart" 
                className="py-2 hover:text-[#2c77d1] flex items-center gap-2"
                onClick={() => setMobileMenuOpen(false)}
              >
                Cart {cartCount > 0 && `(${cartCount})`}
              </Link>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}