import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Facebook, Twitter, Instagram, Youtube, Mail } from 'lucide-react';

export default function Footer() {
  const [email, setEmail] = useState('');

  const handleSubscribe = (e) => {
    e.preventDefault();
    alert('Thank you for subscribing!');
    setEmail('');
  };

  return (
    <footer className="bg-[#050d1b] border-t border-[#2c77d1]/20 py-12 px-4 sm:px-6 lg:px-8 mt-12">
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 mb-8">
          {/* Brand */}
          <div>
            <div className="text-2xl font-bold bg-gradient-to-r from-[#2c77d1] to-[#9426f4] bg-clip-text text-transparent mb-4">
              ZUNTO
            </div>
            <p className="text-gray-400 mb-4">
              Your one-stop shop for amazing products at unbeatable prices.
            </p>
            <div className="flex gap-4">
              <a href="#" className="text-gray-400 hover:text-[#2c77d1] transition">
                <Facebook className="w-5 h-5" />
              </a>
              <a href="#" className="text-gray-400 hover:text-[#2c77d1] transition">
                <Twitter className="w-5 h-5" />
              </a>
              <a href="#" className="text-gray-400 hover:text-[#2c77d1] transition">
                <Instagram className="w-5 h-5" />
              </a>
              <a href="#" className="text-gray-400 hover:text-[#2c77d1] transition">
                <Youtube className="w-5 h-5" />
              </a>
            </div>
          </div>

          {/* Shop */}
          <div>
            <h4 className="font-semibold mb-4">Shop</h4>
            <div className="flex flex-col gap-2 text-gray-400">
              <Link to="/shop" className="hover:text-[#2c77d1] transition">
                All Products
              </Link>
              <Link to="/shop?new=true" className="hover:text-[#2c77d1] transition">
                New Arrivals
              </Link>
              <Link to="/shop?featured=true" className="hover:text-[#2c77d1] transition">
                Best Sellers
              </Link>
              <Link to="/shop?sale=true" className="hover:text-[#2c77d1] transition">
                Sale
              </Link>
            </div>
          </div>

          {/* Support */}
          <div>
            <h4 className="font-semibold mb-4">Support</h4>
            <div className="flex flex-col gap-2 text-gray-400">
              <Link to="/contact" className="hover:text-[#2c77d1] transition">
                Contact Us
              </Link>
              <Link to="/faq" className="hover:text-[#2c77d1] transition">
                FAQ
              </Link>
              <Link to="/shipping" className="hover:text-[#2c77d1] transition">
                Shipping Info
              </Link>
              <Link to="/returns" className="hover:text-[#2c77d1] transition">
                Returns
              </Link>
            </div>
          </div>

          {/* Newsletter */}
          <div>
            <h4 className="font-semibold mb-4">Newsletter</h4>
            <p className="text-gray-400 mb-4 text-sm">
              Subscribe to get special offers and updates
            </p>
            <form onSubmit={handleSubscribe} className="flex flex-col gap-2">
              <div className="relative">
                <input 
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Your email" 
                  required
                  className="w-full bg-[#050d1b] border border-[#2c77d1]/30 rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:border-[#2c77d1]"
                />
                <Mail className="absolute left-3 top-2.5 w-5 h-5 text-gray-400" />
              </div>
              <button 
                type="submit"
                className="bg-gradient-to-r from-[#2c77d1] to-[#9426f4] py-2 rounded-lg font-semibold hover:opacity-90 transition"
              >
                Subscribe
              </button>
            </form>
          </div>
        </div>

        <div className="border-t border-[#2c77d1]/20 pt-8">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-gray-400 text-sm">
              © {new Date().getFullYear()} ZUNTO. All rights reserved.
            </p>
            <div className="flex gap-6 text-sm text-gray-400">
              <Link to="/privacy" className="hover:text-[#2c77d1] transition">
                Privacy Policy
              </Link>
              <Link to="/terms" className="hover:text-[#2c77d1] transition">
                Terms of Service
              </Link>
              <Link to="/cookies" className="hover:text-[#2c77d1] transition">
                Cookie Policy
              </Link>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}