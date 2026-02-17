import React, { useEffect, useMemo, useState } from 'react';
import { ChevronDown, Search, MessageCircle } from 'lucide-react';
import { getFaqSections } from '../services/api';

export default function FAQs() {
  const [sections, setSections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [openItems, setOpenItems] = useState({});

  useEffect(() => {
    const fetchFaqs = async () => {
      try {
        setLoading(true);
        const payload = await getFaqSections();
        setSections(payload.sections || []);
      } catch {
        setError('We could not load FAQs right now. Please try again in a moment.');
      } finally {
        setLoading(false);
      }
    };

    fetchFaqs();
  }, []);

  const filteredSections = useMemo(() => {
    if (!query.trim()) {
      return sections;
    }

    const normalizedQuery = query.toLowerCase();
    return sections
      .map((section) => ({
        ...section,
        faqs: section.faqs.filter((faq) => {
          const questionText = (faq.question || '').toLowerCase();
          const answerText = (faq.answer || '').toLowerCase();
          return questionText.includes(normalizedQuery) || answerText.includes(normalizedQuery);
        }),
      }))
      .filter((section) => section.faqs.length > 0);
  }, [sections, query]);

  const totalFaqs = filteredSections.reduce((sum, section) => sum + section.faqs.length, 0);

  const toggleItem = (faqId) => {
    setOpenItems((previous) => ({
      ...previous,
      [faqId]: !previous[faqId],
    }));
  };

  return (
    <div className="min-h-screen pt-20 pb-14 bg-white dark:bg-gray-900 transition-colors">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <header className="mb-8">
          <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 dark:text-white">Frequently Asked Questions</h1>
          <p className="mt-3 text-gray-600 dark:text-gray-300">
            Find quick answers about accounts, buying, delivery, refunds, and selling on Zunto.
          </p>
        </header>

        <div className="sticky top-16 z-20 bg-white/95 dark:bg-gray-900/95 backdrop-blur pb-4">
          <label htmlFor="faq-search" className="sr-only">Search FAQs</label>
          <div className="relative">
            <Search className="w-5 h-5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              id="faq-search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search FAQ questions and answers"
              className="w-full rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 pl-10 pr-4 py-3 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">Showing {totalFaqs} FAQ items</p>
        </div>

        {loading && (
          <div className="space-y-3 mt-4">
            {[...Array(6)].map((_, index) => (
              <div key={index} className="h-16 rounded-xl bg-gray-100 dark:bg-gray-800 animate-pulse" />
            ))}
          </div>
        )}

        {!loading && error && (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-red-700 dark:bg-red-900/20 dark:border-red-800 dark:text-red-300">
            {error}
          </div>
        )}

        {!loading && !error && filteredSections.length === 0 && (
          <div className="mt-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-4 py-6 text-gray-600 dark:text-gray-300">
            No FAQs match your search yet.
          </div>
        )}

        {!loading && !error && filteredSections.length > 0 && (
          <div className="space-y-8 mt-4">
            {filteredSections.map((section) => (
              <section key={section.id}>
                <h2 className="text-xl sm:text-2xl font-semibold text-gray-900 dark:text-white mb-4">{section.title}</h2>
                <div className="space-y-3">
                  {section.faqs.map((faq) => {
                    const isOpen = !!openItems[faq.id];
                    return (
                      <article key={faq.id} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden">
                        <button
                          type="button"
                          onClick={() => toggleItem(faq.id)}
                          className="w-full flex items-center justify-between gap-4 p-4 text-left"
                        >
                          <span className="font-medium text-gray-900 dark:text-white">{faq.question}</span>
                          <ChevronDown className={`w-5 h-5 text-gray-500 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                        </button>
                        {isOpen && (
                          <div className="px-4 pb-4 text-gray-700 dark:text-gray-300 leading-relaxed border-t border-gray-100 dark:border-gray-700">
                            <p className="pt-3">{faq.answer}</p>
                          </div>
                        )}
                      </article>
                    );
                  })}
                </div>
              </section>
            ))}
          </div>
        )}

        <div className="mt-12 rounded-2xl bg-gradient-to-r from-blue-600 to-purple-600 p-5 sm:p-6 text-white flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold">Still need help?</h3>
            <p className="text-white/90 text-sm">Use the assistant chat at the bottom-right for quick support.</p>
          </div>
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-lg bg-white text-blue-700 px-4 py-2 font-semibold"
          >
            <MessageCircle className="w-4 h-4" /> Open Assistant Chat
          </button>
        </div>
      </div>
    </div>
  );
}
