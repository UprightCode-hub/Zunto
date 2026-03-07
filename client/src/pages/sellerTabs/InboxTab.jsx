import React, { Suspense, lazy } from 'react';
import { Inbox } from 'lucide-react';

const MarketplaceInbox = lazy(() => import('../../components/chat/MarketplaceInbox'));

export default function InboxTab() {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Inbox className="w-5 h-5" />
          Seller Inbox
        </h2>
      </div>
      <div className="p-6">
        <Suspense fallback={<div className="text-sm text-gray-500 dark:text-gray-400">Loading inbox...</div>}>
          <MarketplaceInbox
            containerClassName="h-[70vh]"
            headerTitle="Seller Inbox"
            emptyListLabel="No buyer conversations yet"
          />
        </Suspense>
      </div>
    </div>
  );
}
