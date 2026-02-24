import React, { useEffect, useMemo, useState } from 'react';
import { Bot, MessageSquare, Send } from 'lucide-react';
import { getAssistantSessions, sendAssistantMessage } from '../services/api';

const modeLabel = (mode) => (mode === 'homepage_reco' ? 'Homepage AI' : 'Inbox AI');

export default function InboxAI() {
  const [sessions, setSessions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const data = await getAssistantSessions({ excludeCustomerService: true });
        const next = (data?.sessions || []).filter((item) => item.assistant_mode !== 'customer_service');
        setSessions(next);
        setSelected(next[0] || null);
      } catch (err) {
        setError(err?.message || 'Unable to load AI workspace sessions.');
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  const orderedMessages = useMemo(() => messages.slice(-200), [messages]);

  const onSend = async (event) => {
    event.preventDefault();
    const text = input.trim();
    if (!text || !selected || sending) {
      return;
    }

    setSending(true);
    setError('');
    setMessages((prev) => [...prev, { sender: 'user', text, id: `${Date.now()}-u` }]);
    setInput('');

    try {
      const response = await sendAssistantMessage(text, selected.session_id, null, selected.assistant_mode || 'inbox_general');
      setMessages((prev) => [...prev, { sender: 'bot', text: response?.reply || 'No response.', id: `${Date.now()}-b` }]);
    } catch (err) {
      setError(err?.message || 'Failed to send AI message.');
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="min-h-screen pt-20 pb-8 bg-[#050d1b]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-[calc(100vh-120px)]">
        <div className="h-full grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4">
          <aside className="rounded-2xl border border-[#2c77d1]/20 bg-[#0b1222] overflow-hidden">
            <div className="p-4 border-b border-[#2c77d1]/20">
              <h1 className="text-lg font-bold text-white flex items-center gap-2"><Bot className="w-5 h-5 text-blue-300" /> AI Workspace</h1>
              <p className="text-xs text-gray-400 mt-1">Homepage and Inbox AI threads.</p>
            </div>
            <div className="overflow-y-auto h-[calc(100%-74px)]">
              {loading ? (
                <div className="p-4 text-gray-400 text-sm">Loading...</div>
              ) : sessions.length === 0 ? (
                <div className="p-4 text-gray-400 text-sm">No AI conversations yet.</div>
              ) : sessions.map((session) => (
                <button
                  key={session.session_id}
                  onClick={() => {
                    setSelected(session);
                    setMessages([]);
                  }}
                  className={`w-full text-left px-4 py-3 border-b border-[#2c77d1]/10 hover:bg-[#111b32] ${selected?.session_id === session.session_id ? 'bg-[#14203d]' : ''}`}
                >
                  <p className="text-sm font-semibold text-white truncate">{session.conversation_title || 'AI Conversation'}</p>
                  <div className="mt-1 flex items-center justify-between">
                    <span className="text-[11px] px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300">{modeLabel(session.assistant_mode)}</span>
                    <span className="text-[11px] text-gray-500">{new Date(session.last_activity).toLocaleDateString()}</span>
                  </div>
                </button>
              ))}
            </div>
          </aside>

          <section className="rounded-2xl border border-[#2c77d1]/20 bg-[#0b1222] overflow-hidden flex flex-col">
            {selected ? (
              <>
                <header className="p-4 border-b border-[#2c77d1]/20">
                  <h2 className="text-white font-semibold truncate">{selected.conversation_title || 'AI Conversation'}</h2>
                  <p className="text-xs text-gray-400">{modeLabel(selected.assistant_mode)}</p>
                </header>
                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                  {orderedMessages.length === 0 && <p className="text-sm text-gray-400">Start the conversation.</p>}
                  {orderedMessages.map((msg) => (
                    <div key={msg.id} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm ${msg.sender === 'user' ? 'bg-gradient-to-r from-[#2c77d1] to-[#9426f4] text-white' : 'bg-[#1c2742] text-gray-100'}`}>
                        {msg.text}
                      </div>
                    </div>
                  ))}
                </div>
                <form onSubmit={onSend} className="sticky bottom-0 p-4 border-t border-[#2c77d1]/20 bg-[#0b1222] flex gap-2">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Message AI workspace..."
                    className="flex-1 rounded-full bg-[#111b32] border border-[#2c77d1]/20 px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-[#2c77d1]"
                  />
                  <button
                    type="submit"
                    disabled={!input.trim() || sending}
                    className="inline-flex items-center justify-center rounded-full px-4 py-2 bg-gradient-to-r from-[#2c77d1] to-[#9426f4] text-white font-semibold disabled:opacity-50"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </form>
              </>
            ) : (
              <div className="h-full flex items-center justify-center text-gray-400 text-sm">
                <div className="text-center">
                  <MessageSquare className="w-10 h-10 mx-auto mb-2 opacity-70" />
                  Select an AI conversation.
                </div>
              </div>
            )}
            {error && <div className="px-4 py-2 text-sm text-red-300 border-t border-red-400/20 bg-red-500/10">{error}</div>}
          </section>
        </div>
      </div>
    </div>
  );
}
