import React from 'react';
import { Bot, Headset } from 'lucide-react';
import { Link } from 'react-router-dom';
import MarketplaceInbox from '../components/chat/MarketplaceInbox';

export default function Inbox() {
  return (
    <div className="min-h-screen pt-20 pb-8 bg-[#050d1b]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-white">Inbox</h1>
            <p className="text-sm text-gray-400">Conversations with buyers and sellers.</p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to="/inbox/ai"
              className="inline-flex items-center gap-2 rounded-full border border-[#2c77d1]/50 bg-[#0f172a] px-4 py-2 text-sm font-semibold text-blue-200 hover:border-[#2c77d1]"
            >
              <Bot className="w-4 h-4" />
              Gigi AI Workspace
            </Link>
            <Link
              to="/chat?mode=customer-service"
              className="inline-flex items-center gap-2 rounded-full border border-purple-500/50 bg-[#0f172a] px-4 py-2 text-sm font-semibold text-purple-200 hover:border-purple-400"
            >
              <Headset className="w-4 h-4" />
              Customer Service
            </Link>
          </div>
        </div>

        <MarketplaceInbox containerClassName="h-[calc(100vh-200px)]" headerTitle="Conversations" />
      </div>
    </div>
  );
}
