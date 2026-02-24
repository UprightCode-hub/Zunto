import React, { useEffect, useRef, useState } from 'react';
import { Navigate, useSearchParams } from 'react-router-dom';
import { Headset, Send } from 'lucide-react';
import { sendCustomerServiceMessage } from '../services/api';

export default function Chat() {
  const [searchParams] = useSearchParams();
  const mode = (searchParams.get('mode') || '').toLowerCase();

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

  if (mode !== 'customer-service') {
    return <Navigate to="/inbox" replace />;
  }

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
      setMessages((prev) => [...prev, { sender: 'bot', text: response?.reply || 'No response returned.' }]);
    } catch (err) {
      setError(err?.message || 'Unable to contact Customer Service AI.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen pt-20 pb-8 bg-[#050d1b]">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="rounded-2xl border border-purple-500/20 bg-[#0b1222] overflow-hidden min-h-[72vh] flex flex-col">
          <div className="p-4 border-b border-purple-500/20 flex items-center gap-2 text-white font-semibold">
            <Headset className="w-5 h-5 text-purple-300" /> Customer Service AI
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-[#08101f]">
            {messages.map((msg, index) => (
              <div key={`${msg.sender}-${index}`} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[82%] rounded-2xl px-4 py-2 text-sm ${msg.sender === 'user' ? 'bg-gradient-to-r from-[#2c77d1] to-[#9426f4] text-white' : 'bg-[#1b2846] text-gray-100'}`}>
                  {msg.text}
                </div>
              </div>
            ))}
            {loading && <p className="text-sm text-gray-400">Customer Service AI is thinking...</p>}
            {error && <p className="text-sm text-red-300">{error}</p>}
            <div ref={endRef} />
          </div>

          <form onSubmit={onSubmit} className="sticky bottom-0 border-t border-purple-500/20 p-3 bg-[#0b1222] flex gap-2">
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
              className="inline-flex items-center justify-center rounded-full px-4 py-2 bg-gradient-to-r from-[#2c77d1] to-[#9426f4] text-white font-semibold disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
