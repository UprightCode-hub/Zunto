import React, { useEffect, useRef, useState } from 'react';
import { Navigate, useSearchParams } from 'react-router-dom';
import { FileText, Headset, Send } from 'lucide-react';
import MarketplaceInbox from '../components/chat/MarketplaceInbox';
import { sendCustomerServiceMessage } from '../services/api';

function CustomerServiceChat() {
  const [messages, setMessages] = useState([
    {
      sender: 'bot',
      text: 'Customer Service AI is for disputes and complaint handling only. Share your dispute details.',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [sessionId, setSessionId] = useState(localStorage.getItem('customer_service_session_id') || null);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const onSubmit = async (event) => {
    event.preventDefault();
    const value = input.trim();
    if (!value || loading) {
      return;
    }

    setError('');
    setMessages((prev) => [...prev, { sender: 'user', text: value }]);
    setInput('');

    try {
      setLoading(true);
      const response = await sendCustomerServiceMessage(value, sessionId);
      if (response?.session_id) {
        setSessionId(response.session_id);
        localStorage.setItem('customer_service_session_id', response.session_id);
      }
      setMessages((prev) => [
        ...prev,
        {
          sender: 'bot',
          text: response?.reply || 'No response returned.',
          metadata: response?.metadata || {},
        },
      ]);
    } catch (err) {
      setError(err?.message || 'Unable to contact Customer Service AI.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[var(--app-min-height)] pb-8 bg-[#050d1b] flex flex-col">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 flex-1 min-h-0 flex flex-col">
        <div className="rounded-2xl border border-purple-500/20 bg-[#0b1222] flex-1 min-h-[65vh] flex flex-col">
          <div className="p-4 border-b border-purple-500/20 flex items-center gap-2 text-white font-semibold">
            <Headset className="w-5 h-5 text-purple-300" /> Customer Service AI
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-3 bg-[#08101f]">
            {messages.map((msg, index) => (
              <div key={`${msg.sender}-${index}`} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[82%] rounded-lg px-4 py-2 text-sm ${msg.sender === 'user' ? 'bg-gradient-to-r from-[#2c77d1] to-[#9426f4] text-white' : 'bg-[#1b2846] text-gray-100'}`}>
                  <p className="whitespace-pre-line leading-relaxed">{msg.text}</p>
                  {Array.isArray(msg.metadata?.knowledge_refs) && msg.metadata.knowledge_refs.length > 0 && (
                    <div className="mt-3 border-t border-white/10 pt-2">
                      <p className="mb-1 inline-flex items-center gap-1 text-xs font-semibold text-purple-200">
                        <FileText className="h-3 w-3" />
                        Relevant guidance
                      </p>
                      <div className="space-y-1">
                        {msg.metadata.knowledge_refs.slice(0, 3).map((ref) => (
                          <p key={ref.id || ref.question} className="text-xs leading-snug text-gray-300">
                            {ref.question}
                          </p>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="flex h-9 items-center gap-1 rounded-lg bg-[#1b2846] px-4">
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-purple-200 [animation-delay:0ms]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-purple-200 [animation-delay:150ms]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-purple-200 [animation-delay:300ms]" />
                </div>
              </div>
            )}
            {error && <p className="text-sm text-red-300">{error}</p>}
            <div ref={endRef} />
          </div>

          <form onSubmit={onSubmit} className="border-t border-purple-500/20 p-3 safe-bottom-pad bg-[#0b1222] flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Describe your dispute issue"
              className="flex-1 rounded-full bg-[#111b32] border border-purple-500/20 px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-purple-400"
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="btn-primary"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default function Chat() {
  const [searchParams] = useSearchParams();
  const mode = (searchParams.get('mode') || '').toLowerCase();
  const conversationId = searchParams.get('conversation');

  if (mode === 'customer-service') {
    return <CustomerServiceChat />;
  }

  if (conversationId) {
    return (
      <div className="min-h-screen pb-8 bg-[#050d1b]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex-1 min-h-0 flex flex-col">
          <div className="mb-4">
            <h1 className="text-2xl font-bold text-white">Conversation</h1>
            <p className="text-sm text-gray-400">Buyer and seller messages for this product.</p>
          </div>
          <MarketplaceInbox
            initialConversationId={conversationId}
            containerClassName="flex-1 min-h-[65vh]"
            headerTitle="Conversation"
          />
        </div>
      </div>
    );
  }

  return <Navigate to="/inbox" replace />;
}
