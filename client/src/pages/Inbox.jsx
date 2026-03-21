import React from 'react';
import { Bot, Headset } from 'lucide-react';
import { Link } from 'react-router-dom';
import MarketplaceInbox from '../components/chat/MarketplaceInbox';

export default function Inbox() {
  return (
    <div className="min-h-screen pb-8 bg-[#050d1b]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex-1 min-h-0 flex flex-col">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-white">Inbox</h1>
            <p className="text-sm text-gray-400">Conversations with buyers and sellers.</p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to="/inbox/ai"
              className="btn-secondary"
            >
              <Bot className="w-4 h-4" />
              Gigi AI Workspace
            </Link>
            <Link
              to="/chat?mode=customer-service"
              className="btn-utility"
            >
              <Headset className="w-4 h-4" />
              Customer Service
            </Link>
          </div>
        </div>

        <MarketplaceInbox containerClassName="flex-1 min-h-[65vh]" headerTitle="Conversations" />
      </div>
    </div>
  );
}
