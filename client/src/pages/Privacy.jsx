import React from 'react';

export default function Privacy() {
  return (
    <div className="min-h-screen pt-20 pb-12">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 className="text-4xl font-bold mb-4">Privacy Policy</h1>
        <div className="bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl p-6 space-y-4 text-gray-300">
          <p>
            Zunto collects account, order, and communication data to provide marketplace functionality and fraud protection.
          </p>
          <p>
            Payment-related data for managed-commerce orders is processed through authorized payment providers.
          </p>
          <p>
            We do not sell personal data and only share required information for order fulfillment and legal compliance.
          </p>
        </div>
      </div>
    </div>
  );
}
