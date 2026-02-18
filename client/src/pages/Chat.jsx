import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Headset, Inbox, Send } from 'lucide-react';
import MarketplaceInbox from '../components/chat/MarketplaceInbox';
import { sendAssistantMessage } from '../services/api';

export default function Chat() {
  const [searchParams] = useSearchParams();
  const conversationId = searchParams.get('conversation');
  const mode = (searchParams.get('mode') || '').toLowerCase();
  const query = searchParams.get('q') || '';

  const isAssistantMode = mode === 'assistant' || mode === 'customer-service';
  const assistantLane = mode === 'customer-service' ? 'customer_service' : 'inbox';

  const [assistantMessages, setAssistantMessages] = useState([]);
  const [assistantInput, setAssistantInput] = useState(query);
  const [assistantSessionId, setAssistantSessionId] = useState(localStorage.getItem('chat_session_id') || null);
  const [assistantLoading, setAssistantLoading] = useState(false);
  const [assistantError, setAssistantError] = useState('');
  const endRef = useRef(null);

  useEffect(() => {
    if (!isAssistantMode) {
      return;
    }

    const openingMessage = mode === 'customer-service'
      ? 'You are in Customer Service mode for disputes and complaint guidance.'
      : 'Welcome to GIGI AI support. Ask for recommendations, product guidance, or help center support.';

    setAssistantMessages([{ sender: 'bot', text: openingMessage }]);
  }, [isAssistantMode, mode]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [assistantMessages, assistantLoading]);

  const modeLabel = useMemo(() => (mode === 'customer-service' ? 'Customer Service AI' : 'GIGI AI Assistant'), [mode]);

  const handleAssistantSend = async (event) => {
    event.preventDefault();
    const trimmed = assistantInput.trim();
    if (!trimmed || assistantLoading) {
      return;
    }

    setAssistantError('');
    setAssistantMessages((prev) => [...prev, { sender: 'user', text: trimmed }]);
    setAssistantInput('');

    try {
      setAssistantLoading(true);
      const response = await sendAssistantMessage(trimmed, assistantSessionId, null, assistantLane);
      if (response?.session_id) {
        setAssistantSessionId(response.session_id);
        localStorage.setItem('chat_session_id', response.session_id);
      }
      setAssistantMessages((prev) => [...prev, { sender: 'bot', text: response?.reply || 'No response returned.' }]);
    } catch (error) {
      setAssistantError(error?.message || 'Unable to contact assistant right now.');
    } finally {
      setAssistantLoading(false);
    }
  };

  if (isAssistantMode) {
    return (
      <div className="min-h-screen pt-20 pb-12 bg-black">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              <Headset className="w-6 h-6 text-blue-400" /> {modeLabel}
            </h1>
            <Link to="/chat" className="inline-flex items-center gap-2 text-sm text-blue-300 hover:text-blue-200 transition">
              <Inbox className="w-4 h-4" /> Open Inbox
            </Link>
          </div>

          <div className="rounded-xl border border-gray-700 bg-gray-900 min-h-[65vh] flex flex-col">
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {assistantMessages.map((msg, index) => (
                <div key={`${msg.sender}-${index}`} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[85%] rounded-xl px-4 py-3 text-sm ${msg.sender === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-100 border border-gray-700'}`}>
                    {msg.text}
                  </div>
                </div>
              ))}
              {assistantLoading && <p className="text-sm text-gray-400">GIGI AI is thinking...</p>}
              {assistantError && <p className="text-sm text-red-300">{assistantError}</p>}
              <div ref={endRef} />
            </div>

            <form onSubmit={handleAssistantSend} className="border-t border-gray-700 p-3 flex items-center gap-2">
              <input
                type="text"
                value={assistantInput}
                onChange={(event) => setAssistantInput(event.target.value)}
                placeholder={mode === 'customer-service' ? 'Describe your dispute issue...' : 'Ask GIGI AI anything about products...'}
                className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
              />
              <button
                type="submit"
                disabled={assistantLoading || !assistantInput.trim()}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-70"
              >
                <Send className="w-4 h-4" /> Send
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-20 pb-12 bg-black">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <MarketplaceInbox initialConversationId={conversationId} />
      </div>
    </div>
  );
}
