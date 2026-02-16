import React from 'react';
import { useSearchParams } from 'react-router-dom';
import MarketplaceInbox from '../components/chat/MarketplaceInbox';

export default function Chat() {
  const [searchParams] = useSearchParams();
  const conversationId = searchParams.get('conversation');

  return (
    <div className="min-h-screen pt-20 pb-12 bg-black">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <MarketplaceInbox initialConversationId={conversationId} />
      </div>
    </div>
  );
}
