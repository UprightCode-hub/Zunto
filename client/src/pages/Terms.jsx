import React from 'react';

export default function Terms() {
  return (
    <div className="min-h-screen pt-20 pb-12">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 className="text-4xl font-bold mb-4">Terms of Service</h1>
        <div className="bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl p-6 space-y-4 text-gray-300">
          <p>
            By using Zunto, you agree to comply with marketplace rules, local laws, and platform safety standards.
          </p>
          <p>
            Sellers using managed-commerce must fulfill orders according to Zunto policy, including payment settlement,
            shipping, and refund obligations.
          </p>
          <p>
            Direct sellers and buyers are responsible for their own transaction terms and delivery agreements.
          </p>
        </div>
      </div>
    </div>
  );
}
