import React, { useEffect, useState } from 'react';
import {
  ShieldCheck,
  Sparkles,
  Store,
  Truck,
  BadgePercent,
  MessageCircle,
} from 'lucide-react';

// Add your own local slideshow images in: client/public/marketplace-showcase/
// Expected names (kept out of git by default):
// - slide-1.jpg
// - slide-2.jpg
// - slide-3.jpg
const heroSlides = [
  {
    src: '/marketplace-showcase/slide-1.jpg',
    title: 'Discover trusted sellers',
    text: 'Verified stores, clear ratings, and straightforward delivery options.',
  },
  {
    src: '/marketplace-showcase/slide-2.jpg',
    title: 'Shop faster and safer',
    text: 'Smart search, secure checkout, and transparent order tracking.',
  },
  {
    src: '/marketplace-showcase/slide-3.jpg',
    title: 'Built for marketplace growth',
    text: 'Buyers find deals quickly while sellers reach more customers.',
  },
];

const categories = ['Fashion', 'Electronics', 'Home', 'Beauty', 'Food', 'Services'];

export default function AuthMarketplaceShowcase() {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setActive((prev) => (prev + 1) % heroSlides.length);
    }, 4200);

    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="relative z-10 px-10 py-12 w-full max-w-2xl text-white">
      <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-white/20 bg-white/10 text-xs tracking-wide uppercase text-blue-100 mb-5">
        <Sparkles className="w-3.5 h-3.5" />
        Zunto Marketplace
      </div>

      <h2 className="text-4xl xl:text-5xl font-bold leading-tight mb-4">
        Buy, sell, and scale in one modern marketplace.
      </h2>
      <p className="text-base xl:text-lg text-blue-100/90 mb-7 max-w-xl">
        A cleaner and more professional experience for shoppers and sellers, from discovery to checkout.
      </p>

      <div className="relative rounded-3xl border border-white/15 overflow-hidden p-5 shadow-2xl shadow-black/40">
        <div className="absolute inset-0 bg-gradient-to-br from-[#132349] to-[#090f20]" />

        {heroSlides.map((slide, index) => (
          <div
            key={slide.src}
            className={`absolute inset-0 bg-cover bg-center transition-opacity duration-1000 ${
              index === active ? 'opacity-70' : 'opacity-0'
            }`}
            style={{ backgroundImage: `url(${slide.src})` }}
          />
        ))}

        <div className="absolute inset-0 bg-gradient-to-t from-[#030711]/85 via-[#081027]/65 to-[#0d1735]/65" />

        <div className="relative z-10 grid grid-cols-2 sm:grid-cols-3 gap-2 mb-5">
          {categories.map((item) => (
            <span
              key={item}
              className="text-xs sm:text-sm px-3 py-2 rounded-xl bg-white/10 border border-white/15 text-blue-100/90 backdrop-blur-sm"
            >
              {item}
            </span>
          ))}
        </div>

        <div className="relative z-10 rounded-2xl border border-white/10 bg-black/30 backdrop-blur-[2px] p-4">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#2c77d1]/20 flex items-center justify-center border border-[#2c77d1]/30 shrink-0">
              <Store className="w-5 h-5 text-[#79b1ff]" />
            </div>
            <div>
              <h3 className="text-lg font-semibold mb-1">{heroSlides[active].title}</h3>
              <p className="text-sm text-blue-100/85">{heroSlides[active].text}</p>
            </div>
          </div>

          <div className="mt-4 flex items-center gap-2">
            {heroSlides.map((_, index) => (
              <button
                key={index}
                type="button"
                className={`h-2 rounded-full transition-all ${
                  index === active ? 'w-7 bg-[#2c77d1]' : 'w-2 bg-white/30 hover:bg-white/50'
                }`}
                aria-label={`Show highlight ${index + 1}`}
                onClick={() => setActive(index)}
              />
            ))}
          </div>
        </div>

        <div className="relative z-10 mt-5 grid grid-cols-3 gap-2 text-[11px] sm:text-xs text-blue-100/85">
          <div className="rounded-lg bg-white/10 border border-white/15 p-2.5 flex items-center gap-2 backdrop-blur-sm">
            <ShieldCheck className="w-4 h-4 text-emerald-300" /> Secure payments
          </div>
          <div className="rounded-lg bg-white/10 border border-white/15 p-2.5 flex items-center gap-2 backdrop-blur-sm">
            <Truck className="w-4 h-4 text-sky-300" /> Fast delivery
          </div>
          <div className="rounded-lg bg-white/10 border border-white/15 p-2.5 flex items-center gap-2 backdrop-blur-sm">
            <BadgePercent className="w-4 h-4 text-violet-300" /> Daily deals
          </div>
        </div>
      </div>

      <div className="mt-5 flex items-center gap-2 text-sm text-blue-100/80">
        <MessageCircle className="w-4 h-4 text-[#79b1ff]" />
        Smooth onboarding for both buyers and sellers.
      </div>
    </div>
  );
}
