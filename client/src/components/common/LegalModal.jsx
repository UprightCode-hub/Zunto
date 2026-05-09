import React, { useEffect, useState } from 'react';
import { X } from 'lucide-react';

const LEGAL_COPY = {
  terms: {
    title: 'Terms of Service',
    summary: 'Marketplace rules for buying, selling, checkout, and direct seller transactions on Zunto.',
    sections: [
      {
        heading: 'Marketplace Use',
        body: 'By using Zunto, you agree to comply with marketplace rules, local laws, and platform safety standards. Listings, messages, payments, and reviews must be accurate, lawful, and respectful.',
      },
      {
        heading: 'Managed Commerce',
        body: 'Sellers using managed commerce must fulfill orders according to Zunto policy, including payment settlement, shipping, delivery updates, cancellations, and refund obligations.',
      },
      {
        heading: 'Direct Seller Transactions',
        body: 'Direct sellers and buyers are responsible for their own transaction terms, delivery arrangements, payment agreements, and after-sale support outside Zunto managed checkout.',
      },
    ],
  },
  privacy: {
    title: 'Privacy Policy',
    summary: 'How Zunto handles account, order, marketplace, and communication data.',
    sections: [
      {
        heading: 'Data We Use',
        body: 'Zunto collects account, order, product, browsing, and communication data to provide marketplace functionality, customer support, fraud protection, and product recommendations.',
      },
      {
        heading: 'Payments',
        body: 'Payment-related data for managed-commerce orders is processed through authorized payment providers. Zunto does not ask buyers to enter card details directly on checkout pages.',
      },
      {
        heading: 'Sharing',
        body: 'We do not sell personal data. We only share required information for order fulfillment, payment processing, safety enforcement, legal compliance, and platform operations.',
      },
    ],
  },
};

export function LegalModal({ type, onClose }) {
  const content = LEGAL_COPY[type] || LEGAL_COPY.terms;

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 px-4 py-6 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby={`${type}-modal-title`}>
      <button type="button" className="absolute inset-0 cursor-default" onClick={onClose} aria-label="Close legal modal" />
      <div className="relative max-h-[86vh] w-full max-w-2xl overflow-hidden rounded-2xl border border-[#2c77d1]/30 bg-[#071124] text-white shadow-2xl shadow-black/40">
        <div className="flex items-start justify-between gap-4 border-b border-[#2c77d1]/20 px-5 py-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#7db4ff]">Zunto Legal</p>
            <h2 id={`${type}-modal-title`} className="mt-1 text-2xl font-bold">{content.title}</h2>
            <p className="mt-1 text-sm text-gray-400">{content.summary}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="btn-icon-utility h-10 w-10 shrink-0 border-[#2c77d1]/30"
            aria-label={`Close ${content.title}`}
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="max-h-[62vh] overflow-y-auto px-5 py-5">
          <div className="space-y-4">
            {content.sections.map((section) => (
              <section key={section.heading} className="rounded-xl border border-[#2c77d1]/15 bg-[#0b1220] p-4">
                <h3 className="text-base font-semibold text-white">{section.heading}</h3>
                <p className="mt-2 text-sm leading-6 text-gray-300">{section.body}</p>
              </section>
            ))}
          </div>
        </div>
        <div className="border-t border-[#2c77d1]/20 px-5 py-4">
          <button type="button" onClick={onClose} className="btn-primary w-full sm:w-auto">
            Back to form
          </button>
        </div>
      </div>
    </div>
  );
}

export function LegalLink({ type, className = '', children }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={className}
      >
        {children || LEGAL_COPY[type]?.title}
      </button>
      {open && <LegalModal type={type} onClose={() => setOpen(false)} />}
    </>
  );
}
