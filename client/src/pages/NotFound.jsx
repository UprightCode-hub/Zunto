import React from 'react';
import { Link } from 'react-router-dom';
import { Home, Search } from 'lucide-react';

export default function NotFound() {
  return (
    <section className="max-w-4xl mx-auto px-4 py-16 sm:py-20 text-center">
      <p className="text-sm font-semibold tracking-wide uppercase text-blue-600 dark:text-blue-400">404</p>
      <h1 className="mt-3 text-3xl sm:text-4xl font-bold text-gray-900 dark:text-white">Page not found</h1>
      <p className="mt-4 text-gray-600 dark:text-gray-300">
        We couldn&apos;t find the page you requested. Use one of the quick links below to continue shopping on Zunto.
      </p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <Link
          to="/"
          className="inline-flex items-center gap-2 px-5 py-3 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition"
        >
          <Home className="w-4 h-4" />
          Go to Home
        </Link>
        <Link
          to="/shop"
          className="inline-flex items-center gap-2 px-5 py-3 rounded-lg border border-gray-300 dark:border-gray-700 text-gray-800 dark:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
        >
          <Search className="w-4 h-4" />
          Browse Products
        </Link>
      </div>
    </section>
  );
}
