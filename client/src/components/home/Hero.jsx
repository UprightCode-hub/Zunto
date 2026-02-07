import React from 'react';
import { Link } from 'react-router-dom';
import { Zap, ChevronRight } from 'lucide-react';

export default function Hero({ 
  badge = 'Limited Time Offer',
  title = 'Discover Amazing Products',
  subtitle = 'Shop the latest trends with up to 50% off on selected items',
  primaryButtonText = 'Shop Now',
  primaryButtonLink = '/shop',
  secondaryButtonText = 'View Deals',
  secondaryButtonLink = '/shop?sale=true',
}) {
  return (
    <section className="pt-24 pb-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#2c77d1] via-[#9426f4] to-[#050d1b] p-12 md:p-16">
          <div className="relative z-10 max-w-2xl">
            <div className="inline-flex items-center gap-2 bg-white/10 backdrop-blur-sm px-4 py-2 rounded-full mb-6">
              <Zap className="w-4 h-4 text-yellow-300" />
              <span className="text-sm">{badge}</span>
            </div>
            <h1 className="text-4xl md:text-6xl font-bold mb-6">
              {title}
            </h1>
            <p className="text-xl text-gray-200 mb-8">
              {subtitle}
            </p>
            <div className="flex flex-wrap gap-4">
              <Link 
                to={primaryButtonLink}
                className="bg-white text-[#050d1b] px-8 py-3 rounded-full font-semibold hover:bg-gray-100 transition flex items-center gap-2"
              >
                {primaryButtonText} <ChevronRight className="w-5 h-5" />
              </Link>
              {secondaryButtonText && (
                <Link 
                  to={secondaryButtonLink}
                  className="border-2 border-white px-8 py-3 rounded-full font-semibold hover:bg-white/10 transition"
                >
                  {secondaryButtonText}
                </Link>
              )}
            </div>
          </div>
          <div className="absolute -right-10 -bottom-10 w-72 h-72 bg-[#9426f4] rounded-full blur-3xl opacity-30"></div>
          <div className="absolute -top-10 right-20 w-96 h-96 bg-[#2c77d1] rounded-full blur-3xl opacity-20"></div>
        </div>
      </div>
    </section>
  );
}