import React, { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Bot, MessageSquare, RotateCcw, Send } from 'lucide-react';
import { getAssistantSessions, sendAssistantMessage } from '../services/api';

const modeLabel = (mode) => (mode === 'homepage_reco' ? 'Homepage AI' : 'Inbox AI');
const MESSAGE_WINDOW_SIZE = 200;

// ---------------------------------------------------------------------------
// Lightweight markdown renderer — no external dependency
// Handles: **bold**, *italic*, `code`, bullet lists, numbered lists, ---
// ---------------------------------------------------------------------------

function inlineMarkdown(text) {
  const parts = [];
  const regex = /(\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`)/g;
  let last = 0;
  let m;

  while ((m = regex.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index));

    if (m[2] !== undefined) {
      parts.push(
        <strong key={m.index} className="font-semibold text-white">
          {m[2]}
        </strong>
      );
    } else if (m[3] !== undefined) {
      parts.push(<em key={m.index} className="italic">{m[3]}</em>);
    } else if (m[4] !== undefined) {
      parts.push(
        <code key={m.index} className="px-1 py-0.5 rounded bg-white/10 font-mono text-xs">
          {m[4]}
        </code>
      );
    }
    last = m.index + m[0].length;
  }

  if (last < text.length) parts.push(text.slice(last));
  return parts.length ? parts : text;
}

function renderMarkdown(text) {
  if (!text) return null;

  const lines = text.split('\n');
  const output = [];
  let listBuffer = [];
  let listType = null;

  const flushList = () => {
    if (!listBuffer.length) return;
    const Tag = listType === 'ol' ? 'ol' : 'ul';
    output.push(
      <Tag
        key={`list-${output.length}`}
        className={listType === 'ol' ? 'list-decimal list-inside space-y-0.5 my-1 pl-1' : 'list-disc list-inside space-y-0.5 my-1 pl-1'}
      >
        {listBuffer.map((item, i) => (
          <li key={i} className="text-sm leading-relaxed">
            {inlineMarkdown(item)}
          </li>
        ))}
      </Tag>
    );
    listBuffer = [];
    listType = null;
  };

  lines.forEach((line, idx) => {
    const ulMatch = line.match(/^[-•*]\s+(.+)/);
    const olMatch = line.match(/^\d+[.)]\s+(.+)/);
    const hrMatch = /^---+$/.test(line.trim());
    const blank = line.trim() === '';

    if (ulMatch) {
      if (listType === 'ol') flushList();
      listType = 'ul';
      listBuffer.push(ulMatch[1]);
      return;
    }
    if (olMatch) {
      if (listType === 'ul') flushList();
      listType = 'ol';
      listBuffer.push(olMatch[1]);
      return;
    }

    flushList();

    if (hrMatch) {
      output.push(<hr key={idx} className="border-white/10 my-2" />);
      return;
    }
    if (blank) {
      if (output.length) output.push(<div key={`sp-${idx}`} className="h-1" />);
      return;
    }

    output.push(
      <p key={idx} className="text-sm leading-relaxed">
        {inlineMarkdown(line)}
      </p>
    );
  });

  flushList();
  return output;
}

// ---------------------------------------------------------------------------
// MessageRow
// ---------------------------------------------------------------------------

const MessageRow = memo(function MessageRow({ message, onRetry }) {
  const isUser = message.sender === 'user';
  const isPending = message.status === 'pending';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${
          isUser
            ? 'bg-gradient-to-r from-[#2c77d1] to-[#9426f4] text-white'
            : 'bg-[#1c2742] text-gray-100'
        }`}
      >
        {isPending ? (
          // Animated typing dots instead of raw "Working on your request..."
          <span className="flex items-center gap-1 h-5">
            <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:0ms]" />
            <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:150ms]" />
            <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:300ms]" />
          </span>
        ) : isUser ? (
          <p>{message.text}</p>
        ) : (
          // Assistant messages — render markdown
          <div className="space-y-0.5">{renderMarkdown(message.text)}</div>
        )}

        {!isUser && message.status === 'failed' && (
          <div className="mt-2 flex items-center gap-2">
            <span className="text-[11px] text-red-300">Failed</span>
            <button
              type="button"
              onClick={() => onRetry(message)}
              className="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] bg-red-400/20 text-red-200 hover:bg-red-400/30"
            >
              <RotateCcw className="w-3 h-3" /> Retry
            </button>
          </div>
        )}

        {!isUser && message.status === 'aborted' && (
          <div className="mt-2 flex items-center gap-2">
            <span className="text-[11px] text-yellow-200">Aborted</span>
            <button
              type="button"
              onClick={() => onRetry(message)}
              className="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] bg-yellow-400/20 text-yellow-100 hover:bg-yellow-400/30"
            >
              <RotateCcw className="w-3 h-3" /> Retry
            </button>
          </div>
        )}
      </div>
    </div>
  );
});

// ---------------------------------------------------------------------------
// InboxAI
// ---------------------------------------------------------------------------

export default function InboxAI() {
  const [sessions, setSessions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  const loadAbortRef = useRef(null);
  const sendAbortRef = useRef(null);
  const mountedRef = useRef(true);
  const selectedRef = useRef(null);
  const requestSeqRef = useRef(0);
  const messageIdRef = useRef(0);
  const inFlightRef = useRef(null);
  const messageListRef = useRef(null);
  const shouldStickToBottomRef = useRef(true);

  const createMessageId = () => `m-${++messageIdRef.current}`;

  const updateAssistantStatus = (messageId, nextStatus, fallbackText = null) => {
    setMessages((prev) =>
      prev.map((item) => {
        if (item.id !== messageId) return item;
        return { ...item, status: nextStatus, text: fallbackText ?? item.text };
      })
    );
  };

  const bumpSessionToTop = (session) => {
    if (!session?.session_id) return;
    const updated = { ...session, last_activity: new Date().toISOString() };
    setSessions((prev) => [updated, ...prev.filter((s) => s.session_id !== session.session_id)]);
    setSelected((prev) => {
      if (!prev || prev.session_id !== session.session_id) return prev;
      return updated;
    });
    selectedRef.current = updated;
  };

  const abortActiveSend = useCallback((markAs = 'aborted') => {
    if (sendAbortRef.current) {
      sendAbortRef.current.abort();
      sendAbortRef.current = null;
    }
    const inFlight = inFlightRef.current;
    if (!inFlight) return;
    if (markAs === 'aborted') {
      updateAssistantStatus(inFlight.placeholderId, 'aborted', 'Message request was aborted.');
    }
    inFlightRef.current = null;
    setSending(false);
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      loadAbortRef.current?.abort();
      abortActiveSend('aborted');
    };
  }, [abortActiveSend]);

  useEffect(() => { selectedRef.current = selected; }, [selected]);

  useEffect(() => {
    const list = messageListRef.current;
    if (!list) return undefined;
    const onScroll = () => {
      shouldStickToBottomRef.current =
        list.scrollHeight - list.scrollTop - list.clientHeight < 24;
    };
    onScroll();
    list.addEventListener('scroll', onScroll);
    return () => list.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    if (!shouldStickToBottomRef.current) return;
    const list = messageListRef.current;
    if (list) list.scrollTop = list.scrollHeight;
  }, [messages]);

  // Load sessions once
  useEffect(() => {
    const controller = new AbortController();
    loadAbortRef.current = controller;

    (async () => {
      try {
        setLoading(true);
        const data = await getAssistantSessions({
          excludeCustomerService: true,
          signal: controller.signal,
        });
        if (!mountedRef.current || controller.signal.aborted) return;
        const next = (data?.sessions || []).filter(
          (s) => s.assistant_mode !== 'customer_service'
        );
        setSessions(next);
        setSelected(next[0] || null);
      } catch (err) {
        if (err?.name === 'AbortError' || !mountedRef.current) return;
        setError(err?.message || 'Unable to load AI workspace sessions.');
      } finally {
        if (mountedRef.current && !controller.signal.aborted) setLoading(false);
      }
    })();

    return () => controller.abort();
  }, []);

  const orderedMessages = useMemo(() => messages.slice(-MESSAGE_WINDOW_SIZE), [messages]);

  const dispatchSend = async ({ text, targetSession }) => {
    const seq = ++requestSeqRef.current;
    const userMsgId = createMessageId();
    const asstMsgId = createMessageId();

    setMessages((prev) => [
      ...prev,
      { id: userMsgId, sender: 'user', text, status: 'completed' },
      { id: asstMsgId, sender: 'assistant', text: '', status: 'pending', requestText: text },
    ]);

    setInput('');
    setSending(true);
    setError('');
    bumpSessionToTop(targetSession);
    abortActiveSend('aborted');

    const controller = new AbortController();
    sendAbortRef.current = controller;
    inFlightRef.current = { placeholderId: asstMsgId, requestSeq: seq, sessionId: targetSession.session_id };

    try {
      const response = await sendAssistantMessage(
        text,
        targetSession.session_id,
        null,
        targetSession.assistant_mode || 'inbox_general',
        controller.signal,
      );

      if (
        !mountedRef.current ||
        controller.signal.aborted ||
        seq !== requestSeqRef.current ||
        selectedRef.current?.session_id !== targetSession.session_id
      ) return;

      setMessages((prev) =>
        prev.map((item) =>
          item.id === asstMsgId
            ? { ...item, text: response?.reply || 'No response.', status: 'completed' }
            : item
        )
      );
    } catch (err) {
      if (!mountedRef.current || seq !== requestSeqRef.current) return;
      if (err?.name === 'AbortError') {
        updateAssistantStatus(asstMsgId, 'aborted', 'Message request was aborted.');
        return;
      }
      updateAssistantStatus(asstMsgId, 'failed', err?.message || 'Failed to send AI message.');
      setError(err?.message || 'Failed to send AI message.');
    } finally {
      if (mountedRef.current && seq === requestSeqRef.current) setSending(false);
      if (inFlightRef.current?.placeholderId === asstMsgId) inFlightRef.current = null;
      if (sendAbortRef.current === controller) sendAbortRef.current = null;
    }
  };

  const onSend = async (e) => {
    e.preventDefault();
    const text = input.trim();
    const targetSession = selectedRef.current;
    if (!text || !targetSession || sending) return;
    await dispatchSend({ text, targetSession });
  };

  const onRetry = async (message) => {
    const retryText = message.requestText?.trim();
    const targetSession = selectedRef.current;
    if (!retryText || !targetSession || sending) return;
    await dispatchSend({ text: retryText, targetSession });
  };

  return (
    <div className="min-h-[var(--app-min-height)] pb-8 bg-[#050d1b] flex flex-col">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex-1 min-h-0 flex flex-col">
        <div className="flex-1 min-h-[65vh] grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4">

          {/* Session sidebar */}
          <aside className="rounded-2xl border border-[#2c77d1]/20 bg-[#0b1222] min-h-0 flex flex-col">
            <div className="p-4 border-b border-[#2c77d1]/20">
              <h1 className="text-lg font-bold text-white flex items-center gap-2">
                <Bot className="w-5 h-5 text-blue-300" /> AI Workspace
              </h1>
              <p className="text-xs text-gray-400 mt-1">Homepage and Inbox AI threads.</p>
            </div>
            <div className="overflow-y-auto flex-1 min-h-0">
              {loading ? (
                <div className="p-4 text-gray-400 text-sm">Loading...</div>
              ) : sessions.length === 0 ? (
                <div className="p-4 text-gray-400 text-sm">No AI conversations yet.</div>
              ) : (
                sessions.map((session) => (
                  <button
                    key={session.session_id}
                    onClick={() => {
                      requestSeqRef.current += 1;
                      abortActiveSend('aborted');
                      setSelected(session);
                      setMessages([]);
                    }}
                    className={`w-full text-left px-4 py-3 border-b border-[#2c77d1]/10 hover:bg-[#111b32] transition-colors ${
                      selected?.session_id === session.session_id ? 'bg-[#14203d]' : ''
                    }`}
                  >
                    <p className="text-sm font-semibold text-white truncate">
                      {session.conversation_title || 'AI Conversation'}
                    </p>
                    <div className="mt-1 flex items-center justify-between">
                      <span className="text-[11px] px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300">
                        {modeLabel(session.assistant_mode)}
                      </span>
                      <span className="text-[11px] text-gray-500">
                        {new Date(session.last_activity).toLocaleDateString()}
                      </span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </aside>

          {/* Chat panel */}
          <section className="rounded-2xl border border-[#2c77d1]/20 bg-[#0b1222] min-h-0 flex flex-col">
            {selected ? (
              <>
                <header className="p-4 border-b border-[#2c77d1]/20">
                  <h2 className="text-white font-semibold truncate">
                    {selected.conversation_title || 'AI Conversation'}
                  </h2>
                  <p className="text-xs text-gray-400">{modeLabel(selected.assistant_mode)}</p>
                </header>

                <div ref={messageListRef} className="flex-1 min-h-0 overflow-y-auto p-4 space-y-3">
                  {orderedMessages.length === 0 && (
                    <p className="text-sm text-gray-400">Start the conversation.</p>
                  )}
                  {orderedMessages.map((msg) => (
                    <MessageRow key={msg.id} message={msg} onRetry={onRetry} />
                  ))}
                </div>

                <form
                  onSubmit={onSend}
                  className="p-4 safe-bottom-pad border-t border-[#2c77d1]/20 bg-[#0b1222] flex gap-2"
                >
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
                    className="btn-primary disabled:opacity-40 disabled:cursor-not-allowed"
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

            {error && (
              <div className="px-4 py-2 text-sm text-red-300 border-t border-red-400/20 bg-red-500/10">
                {error}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}