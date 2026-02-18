import React from 'react';
import { Link } from 'react-router-dom';
import { Facebook, Twitter, Instagram, Youtube, Mail, MapPin, Phone } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="bg-gray-900 dark:bg-black border-t border-gray-200 dark:border-gray-800 py-12 px-4 sm:px-6 lg:px-8 mt-12 transition-colors">
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-8 mb-8">
          {/* Brand */}
          <div>
            <div className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-4">
              ZUNTO
            </div>
            <p className="text-gray-400 mb-4">
              Your one-stop shop for amazing products at unbeatable prices.
            </p>
            <div className="flex gap-4">
              <a href="https://facebook.com" target="_blank" rel="noreferrer" aria-label="Facebook" className="text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 transition">
                <Facebook className="w-5 h-5" />
              </a>
              <a href="https://x.com" target="_blank" rel="noreferrer" aria-label="X" className="text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 transition">
                <Twitter className="w-5 h-5" />
              </a>
              <a href="https://instagram.com" target="_blank" rel="noreferrer" aria-label="Instagram" className="text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 transition">
                <Instagram className="w-5 h-5" />
              </a>
              <a href="https://youtube.com" target="_blank" rel="noreferrer" aria-label="YouTube" className="text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 transition">
                <Youtube className="w-5 h-5" />
              </a>
            </div>
          </div>

          {/* Shop */}
          <div>
            <h4 className="font-semibold text-white mb-4">Shop</h4>
            <div className="flex flex-col gap-2 text-gray-400">
              <Link to="/shop" className="hover:text-blue-400 transition">
                All Products
              </Link>
              <Link to="/shop?new=true" className="hover:text-blue-400 transition">
                New Arrivals
              </Link>
              <Link to="/shop?sale=true" className="hover:text-blue-400 transition">
                On Sale
              </Link>
              <Link to="/admin" className="hover:text-blue-400 transition">
                Admin Portal
              </Link>
            </div>
          </div>

          {/* Support */}
          <div>
            <h4 className="font-semibold text-white mb-4">Support</h4>
            <div className="flex flex-col gap-2 text-gray-400">
              <Link to="/chat" className="hover:text-blue-400 transition">
                Contact Us
              </Link>
              <Link to="/faqs" className="hover:text-blue-400 transition">
                FAQs
              </Link>
              <Link to="/shipping-addresses" className="hover:text-blue-400 transition">
                Shipping Info
              </Link>
              <Link to="/refunds" className="hover:text-blue-400 transition">
                Returns
              </Link>
            </div>
          </div>

          {/* Company */}
          <div>
            <h4 className="font-semibold text-white mb-4">Company</h4>
            <div className="flex flex-col gap-2 text-gray-400">
              <Link to="/profile" className="hover:text-blue-400 transition">
                My Profile
              </Link>
              <Link to="/orders" className="hover:text-blue-400 transition">
                Order History
              </Link>
              <Link to="/notifications" className="hover:text-blue-400 transition">
                Notifications
              </Link>
              <Link to="/seller" className="hover:text-blue-400 transition">
                Become a Seller
              </Link>
            </div>
          </div>

          {/* Contact */}
          <div>
            <h4 className="font-semibold text-white mb-4">Contact</h4>
            <div className="flex flex-col gap-3 text-gray-400">
              <div className="flex items-center gap-2">
                <Phone className="w-4 h-4" />
                <span>+1 (555) 123-4567</span>
              </div>
              <a href="mailto:support@zunto.com" className="flex items-center gap-2 hover:text-blue-400 transition">
                <Mail className="w-4 h-4" />
                <span>support@zunto.com</span>
              </a>
              <div className="flex items-start gap-2">
                <MapPin className="w-4 h-4 mt-1" />
                <span>123 Business St, City, State 12345</span>
              </div>
            </div>
          </div>
        </div>

        <hr className="border-gray-700 dark:border-gray-800 my-8" />

        <div className="flex justify-between items-center flex-wrap gap-4">
          <p className="text-gray-400 text-sm">
            &copy; 2024 Zunto. All rights reserved.
          </p>
          <div className="flex gap-6 text-gray-400 text-sm">
            <Link to="/privacy" className="hover:text-blue-400 transition">Privacy Policy</Link>
            <Link to="/terms" className="hover:text-blue-400 transition">Terms of Service</Link>
            <Link to="/faqs" className="hover:text-blue-400 transition">Help Center</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
