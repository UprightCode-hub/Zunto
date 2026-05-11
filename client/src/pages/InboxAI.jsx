import React, { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeft, Bot, ChevronRight, Clock3, MessageSquare, Package, Plus, RotateCcw, Send, Sparkles } from 'lucide-react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getAssistantSession, getAssistantSessions, sendAssistantMessage } from '../services/api';
import AssistantReply from '../components/assistant/AssistantReply';
import ProductSuggestionRail from '../components/assistant/ProductSuggestionRail';
import ProductImage from '../components/products/ProductImage';
import { getProductImage } from '../utils/product';

const MESSAGE_WINDOW_SIZE = 200;
const NEW_HOMEPAGE_SESSION_KEY = 'new-homepage-reco-session';

const modeLabel = (mode) => {
  if (mode === 'homepage_reco') return 'Homepage AI';
  if (mode === 'customer_service') return 'Customer Service';
  return 'Inbox AI';
};

const modeBadgeClass = (mode, active = false) => {
  if (mode === 'customer_service') {
    return active
      ? 'bg-emerald-400/15 text-emerald-100 border-emerald-300/25'
      : 'bg-emerald-400/10 text-emerald-200 border-emerald-300/15';
  }
  if (mode === 'homepage_reco') {
    return active
      ? 'bg-purple-400/15 text-purple-100 border-purple-300/25'
      : 'bg-purple-400/10 text-purple-200 border-purple-300/15';
  }
  return active
    ? 'bg-blue-400/15 text-blue-100 border-blue-300/25'
    : 'bg-blue-400/10 text-blue-200 border-blue-300/15';
};

const createDraftSession = (assistantMode = 'homepage_reco', title = 'New Conversation') => ({
  client_session_key: assistantMode === 'homepage_reco' ? NEW_HOMEPAGE_SESSION_KEY : `new-${assistantMode}-session`,
  session_id: null,
  assistant_mode: assistantMode,
  conversation_title: title,
  last_activity: new Date().toISOString(),
  isDraft: true,
});

const stripReplyYesFlow = (text) => {
  const value = String(text || '');
  return value
    .split(/\n+/)
    .filter((line) => {
      const normalized = line.toLowerCase();
      return !(
        /\b(?:reply|respond|type|say)\s+(?:with\s+)?["']?yes["']?\b/.test(normalized)
        || /\bnew\s+recommendation\s+thread\b/.test(normalized)
        || /\bshall i\b.*\b(?:show|search|continue|resume|pick up)\b/.test(normalized)
      );
    })
    .join('\n')
    .trim();
};

const titleForSession = (session) => (
  session?.conversation_title
  || session?.formatted_summary
  || 'AI Conversation'
);

const formatThreadTime = (value) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const now = new Date();
  const sameDay = date.toDateString() === now.toDateString();
  if (sameDay) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
  return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
};

const formatMessageTime = (value) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

const normalizeHistoryMessages = (messages = [], sessionId = 'history') => (
  (Array.isArray(messages) ? messages : [])
    .map((entry, index) => {
      const role = String(entry?.sender || entry?.role || '').toLowerCase();
      const sender = role === 'assistant' || role === 'ai' || role === 'bot' ? 'assistant' : 'user';
      const text = stripReplyYesFlow(entry?.text ?? entry?.content ?? entry?.message ?? '');
      if (!text) return null;
      return {
        id: entry?.id || `${sessionId}-${index}`,
        sender,
        text,
        status: 'completed',
        timestamp: entry?.timestamp || entry?.created_at || entry?.createdAt || null,
        metadata: entry?.metadata || {},
      };
    })
    .filter(Boolean)
);

const ChatTypingDots = memo(function ChatTypingDots() {
  return (
    <span className="flex h-5 items-center gap-1" aria-label="AI is typing">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-blue-200 [animation-delay:0ms]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-blue-200 [animation-delay:150ms]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-blue-200 [animation-delay:300ms]" />
    </span>
  );
});

const MessageRow = memo(function MessageRow({ message, onRetry }) {
  const isUser = message.sender === 'user';
  const isPending = message.status === 'pending';
  const suggestedProducts = message.metadata?.suggested_products || [];

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`${isUser ? 'items-end' : 'items-start'} flex max-w-[92%] flex-col gap-1 sm:max-w-[78%]`}>
        <div
          className={`rounded-[18px] px-4 py-3 text-sm shadow-lg shadow-black/10 ${
            isUser
              ? 'rounded-br-md bg-gradient-to-r from-[#2c77d1] to-[#9426f4] text-white'
              : 'rounded-bl-md border border-white/10 bg-[#101a31] text-gray-100'
          }`}
        >
          {isPending ? (
            <ChatTypingDots />
          ) : isUser ? (
            <p className="whitespace-pre-wrap break-words leading-relaxed">{message.text}</p>
          ) : (
            <div className="space-y-2">
              <AssistantReply text={message.text} tone="dark" />
              <ProductSuggestionRail products={suggestedProducts} tone="dark" />
            </div>
          )}

          {!isUser && message.status === 'failed' && (
            <div className="mt-2 flex items-center gap-2">
              <span className="text-[11px] text-red-300">Failed</span>
              <button
                type="button"
                onClick={() => onRetry(message)}
                className="inline-flex items-center gap-1 rounded-md bg-red-400/20 px-2 py-0.5 text-[11px] text-red-200 hover:bg-red-400/30"
              >
                <RotateCcw className="h-3 w-3" /> Retry
              </button>
            </div>
          )}

          {!isUser && message.status === 'aborted' && (
            <div className="mt-2 flex items-center gap-2">
              <span className="text-[11px] text-yellow-200">Aborted</span>
              <button
                type="button"
                onClick={() => onRetry(message)}
                className="inline-flex items-center gap-1 rounded-md bg-yellow-400/20 px-2 py-0.5 text-[11px] text-yellow-100 hover:bg-yellow-400/30"
              >
                <RotateCcw className="h-3 w-3" /> Retry
              </button>
            </div>
          )}
        </div>
        {message.timestamp && (
          <span className="px-1 text-[11px] text-slate-500">
            {formatMessageTime(message.timestamp)}
          </span>
        )}
      </div>
    </div>
  );
});

const LoginGateBubble = memo(function LoginGateBubble({ onGoogleSuccess, onManualSignup }) {
  return (
    <div className="mx-4 mb-3 rounded-lg border border-blue-300/20 bg-[#101a31] p-4 shadow-md">
      <p className="text-sm font-semibold text-white">
        Create your free account to unlock personalized product results.
      </p>
      <button
        type="button"
        onClick={onGoogleSuccess}
        className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-white/15 bg-white/5 px-4 py-2 text-sm font-medium text-gray-100 hover:bg-white/10"
      >
        Continue with Google
      </button>
      <button
        type="button"
        onClick={onManualSignup}
        className="mt-2 inline-flex w-full items-center justify-center rounded-lg bg-gradient-to-r from-[#2c77d1] to-[#9426f4] px-4 py-2 text-sm font-semibold text-white hover:opacity-90"
      >
        Sign up manually
      </button>
    </div>
  );
});

function ProductPanel({ products }) {
  const items = Array.isArray(products) ? products.slice(0, 5) : [];

  return (
    <aside className="hidden min-h-0 rounded-lg border border-[#2c77d1]/20 bg-[#071124]/95 lg:flex lg:flex-col">
      <div className="border-b border-[#2c77d1]/20 p-4">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-purple-300" />
          <h2 className="text-sm font-semibold text-white">Product Picks</h2>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        {items.length === 0 ? (
          <div className="flex h-full min-h-48 items-center justify-center rounded-lg border border-dashed border-white/10 bg-white/[0.03] p-5 text-center">
            <div>
              <Package className="mx-auto mb-3 h-8 w-8 text-slate-500" />
              <p className="text-sm text-slate-400">Product suggestions will appear here.</p>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {items.map((product) => (
              <article
                key={product.id || product.slug || product.title}
                className="rounded-lg border border-white/10 bg-[#101a31] p-3"
              >
                <div className="flex gap-3">
                  <div className="h-16 w-16 shrink-0 overflow-hidden rounded-md bg-[#17233f]">
                    <ProductImage
                      src={getProductImage(product)}
                      alt={product.title || 'Product'}
                      className="h-full w-full object-cover"
                    />
                  </div>
                  <div className="min-w-0">
                    <p className="break-words text-sm font-semibold leading-snug text-white">
                      {product.title || product.name || 'Product'}
                    </p>
                    <p className="mt-1 text-sm font-bold text-blue-300">
                      {Number.isFinite(Number(product.price))
                        ? `\u20A6${Number(product.price).toLocaleString('en-NG', { maximumFractionDigits: 0 })}`
                        : product.price || 'Price on listing'}
                    </p>
                  </div>
                </div>
                <div className="mt-3 flex items-center justify-between gap-3">
                  <span className="min-w-0 truncate text-xs text-slate-400">
                    {product.location || product.condition || 'Zunto listing'}
                  </span>
                  <Link
                    to={product.product_url || (product.slug ? `/product/${product.slug}` : '/products')}
                    className="inline-flex min-h-8 shrink-0 items-center justify-center rounded-md bg-white/10 px-3 text-xs font-semibold text-white hover:bg-white/15"
                  >
                    View Product
                  </Link>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}

function buildSupportGreeting(user) {
  const name = user?.first_name || user?.name || user?.email?.split('@')?.[0] || 'there';
  const isSeller = user?.role === 'seller' || user?.isSellerActive || user?.is_seller;
  if (isSeller) {
    return `Hi ${name}, I'm Gigi from Zunto Seller Support. I can help with buyer disputes, order issues, payments, and account questions. What's happened?`;
  }
  return `Hi ${name}, I'm Gigi from Zunto Customer Support. I can help with order status, delivery issues, payments, refunds, and seller disputes. What's happened?`;
}

function DisputeContextPanel({ panel, collapsed, onToggle }) {
  if (!panel) return null;
  const products = Array.isArray(panel.product_names) ? panel.product_names.filter(Boolean) : [];

  return (
    <aside className={`${collapsed ? 'lg:w-14' : ''} hidden min-h-0 rounded-lg border border-[#2c77d1]/20 bg-[#071124]/95 lg:flex lg:flex-col`}>
      <button
        type="button"
        onClick={onToggle}
        className="flex items-center justify-between border-b border-[#2c77d1]/20 p-4 text-left text-white"
      >
        {!collapsed && <span className="text-sm font-semibold">Dispute Context</span>}
        <ChevronRight className={`h-4 w-4 transition ${collapsed ? '' : 'rotate-180'}`} />
      </button>
      {!collapsed && (
        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4 text-sm">
          <Field label="Order reference" value={panel.order_reference || 'Not linked'} />
          <Field label="Products" value={products.length ? products.join(', ') : 'Not recorded'} />
          <Field label="Buyer" value={`${panel.buyer?.name || 'Not listed'}${panel.buyer?.contact ? ` - ${panel.buyer.contact}` : ''}`} />
          <Field label="Seller" value={`${panel.seller?.name || 'Not listed'}${panel.seller?.contact ? ` - ${panel.seller.contact}` : ''}`} />
          <Field label="Order status" value={panel.order_status || 'Not recorded'} />
          <Field label="Payment status" value={panel.payment_status || 'Not recorded'} />
          <Field label="Amount" value={panel.amount || 'Not recorded'} />
          <Field label="Conversation" value={panel.linked_conversation_id || 'Not linked'} />
        </div>
      )}
    </aside>
  );
}

function Field({ label, value }) {
  return (
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 break-words text-slate-100">{value}</p>
    </div>
  );
}

export default function InboxAI({ embedded = false, defaultAssistantMode = null, initialTitle = 'AI Inbox' }) {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const requestedMode = defaultAssistantMode || searchParams.get('mode') || 'homepage_reco';
  const [sessions, setSessions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [loginGate, setLoginGate] = useState(null);
  const [disputePanelCollapsed, setDisputePanelCollapsed] = useState(false);

  const sessionsAbortRef = useRef(null);
  const detailAbortRef = useRef(null);
  const sendAbortRef = useRef(null);
  const mountedRef = useRef(true);
  const selectedRef = useRef(null);
  const requestSeqRef = useRef(0);
  const detailSeqRef = useRef(0);
  const messageIdRef = useRef(0);
  const inFlightRef = useRef(null);
  const messageListRef = useRef(null);
  const inputRef = useRef(null);
  const shouldStickToBottomRef = useRef(true);

  const createMessageId = () => `m-${++messageIdRef.current}`;
  const selectedSessionId = selected?.session_id;
  const selectedClientSessionKey = selected?.client_session_key;

  const updateAssistantStatus = (messageId, nextStatus, fallbackText = null) => {
    setMessages((prev) =>
      prev.map((item) => (
        item.id === messageId
          ? { ...item, status: nextStatus, text: fallbackText ?? item.text }
          : item
      ))
    );
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

  const refreshSessions = useCallback(async (signal) => {
    const data = await getAssistantSessions({
      assistantMode: requestedMode === 'customer_service' ? 'customer_service' : null,
      signal,
    });
    const next = (data?.sessions || []).filter((session) => session?.session_id);
    setSessions(next);
  }, [requestedMode]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      sessionsAbortRef.current?.abort();
      detailAbortRef.current?.abort();
      abortActiveSend('aborted');
    };
  }, [abortActiveSend]);

  useEffect(() => {
    selectedRef.current = selected;
  }, [selected]);

  useEffect(() => {
    if (!selectedSessionId && !selectedClientSessionKey) return;
    window.setTimeout(() => inputRef.current?.focus(), 0);
  }, [selectedSessionId, selectedClientSessionKey]);

  useEffect(() => {
    const list = messageListRef.current;
    if (!list) return undefined;
    const onScroll = () => {
      shouldStickToBottomRef.current =
        list.scrollHeight - list.scrollTop - list.clientHeight < 48;
    };
    onScroll();
    list.addEventListener('scroll', onScroll);
    return () => list.removeEventListener('scroll', onScroll);
  }, [selected]);

  useEffect(() => {
    if (!shouldStickToBottomRef.current) return;
    const list = messageListRef.current;
    if (list) {
      list.scrollTo({ top: list.scrollHeight, behavior: 'smooth' });
    }
  }, [messages]);

  useEffect(() => {
    const controller = new AbortController();
    sessionsAbortRef.current = controller;

    (async () => {
      try {
        setLoadingSessions(true);
        setError('');
        await refreshSessions(controller.signal);
        if (!mountedRef.current || controller.signal.aborted) return;
        if (requestedMode === 'customer_service') {
          const draft = createDraftSession('customer_service', 'New Support Case');
          setSelected(draft);
          selectedRef.current = draft;
          setMessages([{
            id: createMessageId(),
            sender: 'assistant',
            text: buildSupportGreeting(user),
            status: 'completed',
            timestamp: new Date().toISOString(),
            metadata: { assistant_mode: 'customer_service' },
          }]);
        } else {
          setSelected(null);
          setMessages([]);
        }
      } catch (err) {
        if (err?.name === 'AbortError' || !mountedRef.current) return;
        setError(err?.message || 'Unable to load AI conversations.');
      } finally {
        if (mountedRef.current && !controller.signal.aborted) {
          setLoadingSessions(false);
        }
      }
    })();

    return () => controller.abort();
  }, [refreshSessions, requestedMode, user]);

  const orderedMessages = useMemo(() => messages.slice(-MESSAGE_WINDOW_SIZE), [messages]);

  const latestSuggestedProducts = useMemo(() => {
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const products = messages[index]?.metadata?.suggested_products;
      if (Array.isArray(products) && products.length > 0) {
        return products;
      }
    }
    return [];
  }, [messages]);

  const latestDisputePanel = useMemo(() => {
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const panel = messages[index]?.metadata?.contextual_dispute_panel;
      if (panel && typeof panel === 'object') {
        return panel;
      }
    }
    return null;
  }, [messages]);

  const handleNewConversation = () => {
    detailAbortRef.current?.abort();
    abortActiveSend('aborted');
    requestSeqRef.current += 1;
    const draft = createDraftSession(
      requestedMode,
      requestedMode === 'customer_service' ? 'New Support Case' : 'New Conversation',
    );
    setSelected(draft);
    selectedRef.current = draft;
    setMessages(requestedMode === 'customer_service'
      ? [{
          id: createMessageId(),
          sender: 'assistant',
          text: buildSupportGreeting(user),
          status: 'completed',
          timestamp: new Date().toISOString(),
          metadata: { assistant_mode: 'customer_service' },
        }]
      : []);
    setInput('');
    setError('');
    setLoginGate(null);
    shouldStickToBottomRef.current = true;
  };

  const handleBackToList = () => {
    detailAbortRef.current?.abort();
    abortActiveSend('aborted');
    requestSeqRef.current += 1;
    setSelected(null);
    selectedRef.current = null;
    setMessages([]);
    setInput('');
    setLoginGate(null);
  };

  const openSession = useCallback(async (session) => {
    if (!session?.session_id) return;

    detailAbortRef.current?.abort();
    abortActiveSend('aborted');
    const controller = new AbortController();
    detailAbortRef.current = controller;
    const seq = ++detailSeqRef.current;

    setSelected({ ...session, isDraft: false });
    setMessages([]);
    setInput('');
    setLoginGate(null);
    setLoadingMessages(true);
    setError('');
    shouldStickToBottomRef.current = true;

    try {
      const data = await getAssistantSession(session.session_id, controller.signal);
      if (!mountedRef.current || controller.signal.aborted || seq !== detailSeqRef.current) return;

      const history = normalizeHistoryMessages(
        data?.messages || data?.conversation_history || [],
        session.session_id,
      );
      const hydratedSession = {
        ...session,
        conversation_title: data?.conversation_title || session.conversation_title,
        assistant_mode: data?.assistant_mode || session.assistant_mode,
        assistant_lane: data?.assistant_lane || session.assistant_lane,
        last_activity: data?.last_activity || session.last_activity,
        isDraft: false,
      };
      setSelected(hydratedSession);
      selectedRef.current = hydratedSession;
      setMessages(history);
      setSessions((prev) =>
        prev.map((item) => (
          item.session_id === hydratedSession.session_id
            ? { ...item, ...hydratedSession }
            : item
        ))
      );
    } catch (err) {
      if (err?.name === 'AbortError' || !mountedRef.current) return;
      setError(err?.message || 'Unable to load this conversation.');
    } finally {
      if (mountedRef.current && !controller.signal.aborted && seq === detailSeqRef.current) {
        setLoadingMessages(false);
      }
    }
  }, [abortActiveSend]);

  const handlePostLoginSearch = useCallback(async () => {
    if (!loginGate?.collected_slots || !loginGate?.message) return;
    const targetSession = selectedRef.current;
    if (!targetSession) return;

    try {
      setSending(true);
      const response = await sendAssistantMessage(
        loginGate.message,
        loginGate.session_id || targetSession.session_id,
        null,
        'homepage_reco',
        undefined,
        { pre_collected_slots: loginGate.collected_slots },
      );

      setMessages((prev) => [
        ...prev,
        {
          id: createMessageId(),
          sender: 'assistant',
          text: stripReplyYesFlow(response?.reply) || 'No response.',
          status: 'completed',
          timestamp: new Date().toISOString(),
          metadata: response?.metadata || {},
        },
      ]);
    } catch (err) {
      setError(err?.message || 'Unable to continue recommendation search after login.');
    } finally {
      setLoginGate(null);
      setSending(false);
    }
  }, [loginGate]);

  const upsertSessionFromResponse = (targetSession, response, userText) => {
    const responseSessionId = response?.new_session_id || response?.session_id || targetSession.session_id;
    if (!responseSessionId) return targetSession;

    const nextSession = {
      ...targetSession,
      session_id: responseSessionId,
      assistant_mode: response?.metadata?.assistant_mode || targetSession.assistant_mode || 'homepage_reco',
      assistant_lane: response?.metadata?.assistant_lane || targetSession.assistant_lane || 'inbox',
      conversation_title:
        response?.metadata?.conversation_title
        || response?.conversation_title
        || targetSession.conversation_title
        || userText,
      last_activity: new Date().toISOString(),
      isDraft: false,
    };
    delete nextSession.client_session_key;

    setSelected(nextSession);
    selectedRef.current = nextSession;
    setSessions((prev) => [
      nextSession,
      ...prev.filter((session) => session.session_id !== responseSessionId),
    ]);
    return nextSession;
  };

  const dispatchSend = async ({ text, targetSession }) => {
    abortActiveSend('aborted');

    const seq = ++requestSeqRef.current;
    const timestamp = new Date().toISOString();
    const userMsgId = createMessageId();
    const asstMsgId = createMessageId();

    setMessages((prev) => [
      ...prev,
      { id: userMsgId, sender: 'user', text, status: 'completed', timestamp, metadata: {} },
      {
        id: asstMsgId,
        sender: 'assistant',
        text: '',
        status: 'pending',
        requestText: text,
        timestamp: new Date().toISOString(),
        metadata: {},
      },
    ]);

    setInput('');
    setSending(true);
    setError('');
    setLoginGate(null);
    shouldStickToBottomRef.current = true;

    const controller = new AbortController();
    sendAbortRef.current = controller;
    inFlightRef.current = {
      placeholderId: asstMsgId,
      requestSeq: seq,
      sessionId: targetSession.session_id || targetSession.client_session_key,
    };

    try {
      const response = await sendAssistantMessage(
        text,
        targetSession.session_id || null,
        null,
        targetSession.assistant_mode || 'homepage_reco',
        controller.signal,
      );

      const stillSelected = (
        selectedRef.current?.session_id === targetSession.session_id
        || (!targetSession.session_id && selectedRef.current?.client_session_key === targetSession.client_session_key)
      );
      if (!mountedRef.current || controller.signal.aborted || seq !== requestSeqRef.current || !stillSelected) {
        return;
      }

      const nextSession = upsertSessionFromResponse(targetSession, response, text);
      setMessages((prev) =>
        prev.map((item) =>
          item.id === asstMsgId
            ? {
                ...item,
                text: stripReplyYesFlow(response?.reply) || 'No response.',
                status: 'completed',
                timestamp: new Date().toISOString(),
                metadata: response?.metadata || {},
              }
            : item
        )
      );

      if (response?.login_required === true) {
        setLoginGate({
          collected_slots: response.collected_slots,
          session_id: nextSession?.session_id || null,
          message: text,
        });
      }
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

  const onSend = async (event) => {
    event.preventDefault();
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
    <div className={`${embedded ? 'h-[76vh]' : 'min-h-[var(--app-min-height)]'} bg-[#050d1b] text-white`}>
      <div className={`${embedded ? 'h-full' : 'mx-auto flex min-h-[calc(var(--app-min-height)-4rem)] max-w-7xl flex-col px-3 py-4 sm:px-5 lg:px-8'}`}>
        <div className={`${embedded ? 'h-full p-3' : ''} min-h-0 flex-1 grid-cols-1 gap-4 lg:grid ${requestedMode === 'customer_service' && !latestDisputePanel ? 'lg:grid-cols-[300px_minmax(0,1fr)]' : 'lg:grid-cols-[300px_minmax(0,1fr)_320px]'}`}>
          <aside className={`${selected ? 'hidden lg:flex' : 'flex'} ${embedded ? 'min-h-0' : 'min-h-[calc(var(--app-min-height)-6rem)]'} flex-col rounded-lg border border-[#2c77d1]/20 bg-[#071124]/95 lg:min-h-0`}>
            <div className="sticky top-0 z-10 border-b border-[#2c77d1]/20 bg-[#071124] p-4">
              <button
                type="button"
                onClick={handleNewConversation}
                className="mb-4 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-[#2c77d1] to-[#9426f4] px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-blue-950/30 transition hover:opacity-90"
              >
                <Plus className="h-4 w-4" />
                New Conversation
              </button>
              <div className="flex items-center gap-2">
                <Bot className="h-5 w-5 text-blue-300" />
                <h1 className="text-base font-bold text-white">{initialTitle}</h1>
              </div>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto">
              {loadingSessions ? (
                <div className="p-4 text-sm text-slate-400">Loading conversations...</div>
              ) : sessions.length === 0 ? (
                <div className="p-4 text-sm text-slate-400">No conversations yet.</div>
              ) : (
                <div className="p-2">
                  {sessions.map((session) => {
                    const active = selected?.session_id === session.session_id;
                    return (
                      <button
                        key={session.session_id}
                        type="button"
                        onClick={() => openSession(session)}
                        className={`mb-1 w-full rounded-lg border px-3 py-3 text-left transition ${
                          active
                            ? 'border-[#2c77d1]/40 bg-[#14203d]'
                            : 'border-transparent hover:border-[#2c77d1]/20 hover:bg-[#0d1830]'
                        }`}
                      >
                        <p className="line-clamp-2 break-words text-sm font-semibold leading-snug text-white">
                          {titleForSession(session)}
                        </p>
                        <div className="mt-2 flex items-center justify-between gap-2">
                          <span className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-semibold ${modeBadgeClass(session.assistant_mode, active)}`}>
                            {modeLabel(session.assistant_mode)}
                          </span>
                          <span className="inline-flex shrink-0 items-center gap-1 text-[11px] text-slate-500">
                            <Clock3 className="h-3 w-3" />
                            {formatThreadTime(session.last_activity)}
                          </span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </aside>

          <section className={`${selected ? 'flex' : 'hidden lg:flex'} ${embedded ? 'min-h-0' : 'min-h-[calc(var(--app-min-height)-6rem)]'} flex-col overflow-hidden rounded-lg border border-[#2c77d1]/20 bg-[#071124]/95 lg:min-h-0`}>
            {selected ? (
              <>
                <header className="flex min-h-16 items-center gap-3 border-b border-[#2c77d1]/20 bg-[#08152b] px-4">
                  <button
                    type="button"
                    onClick={handleBackToList}
                    className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-white/10 text-slate-200 hover:bg-white/10 lg:hidden"
                    aria-label="Back to conversations"
                  >
                    <ArrowLeft className="h-4 w-4" />
                  </button>
                  <div className="min-w-0 flex-1">
                    <h2 className="truncate text-sm font-semibold text-white sm:text-base">
                      {titleForSession(selected)}
                    </h2>
                    <span className={`mt-1 inline-flex rounded-full border px-2 py-0.5 text-[11px] font-semibold ${modeBadgeClass(selected.assistant_mode, true)}`}>
                      {modeLabel(selected.assistant_mode)}
                    </span>
                  </div>
                </header>

                <div ref={messageListRef} className="min-h-0 flex-1 overflow-y-auto bg-[radial-gradient(circle_at_top_left,rgba(44,119,209,0.13),transparent_34%),#071124] p-4">
                  {loadingMessages ? (
                    <div className="flex h-full min-h-64 items-center justify-center text-sm text-slate-400">
                      Loading conversation...
                    </div>
                  ) : orderedMessages.length === 0 ? (
                    <div className="flex h-full min-h-64 items-center justify-center text-center">
                      <div>
                        <MessageSquare className="mx-auto mb-3 h-10 w-10 text-blue-300/70" />
                        <p className="text-sm font-medium text-slate-200">Start a new conversation.</p>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {orderedMessages.map((msg) => (
                        <MessageRow key={msg.id} message={msg} onRetry={onRetry} />
                      ))}
                    </div>
                  )}
                </div>

                {loginGate && (
                  <LoginGateBubble
                    onGoogleSuccess={handlePostLoginSearch}
                    onManualSignup={() => navigate('/signup')}
                  />
                )}

                <form
                  onSubmit={onSend}
                  className="safe-bottom-pad border-t border-[#2c77d1]/20 bg-[#08152b] p-3 sm:p-4"
                >
                  <div className="flex items-end gap-2 rounded-full border border-[#2c77d1]/25 bg-[#101a31] p-1.5 shadow-lg shadow-black/20 focus-within:border-[#2c77d1]/70">
                    <input
                      ref={inputRef}
                      type="text"
                      value={input}
                      onChange={(event) => setInput(event.target.value)}
                      placeholder="Message Gigi AI..."
                      className="min-h-10 flex-1 bg-transparent px-3 text-sm text-white placeholder-slate-500 outline-none"
                    />
                    <button
                      type="submit"
                      disabled={!input.trim() || sending || loadingMessages}
                      className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-r from-[#2c77d1] to-[#9426f4] text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
                      aria-label="Send message"
                    >
                      <Send className="h-4 w-4" />
                    </button>
                  </div>
                </form>
              </>
            ) : (
              <div className="flex h-full min-h-96 items-center justify-center text-center text-slate-400">
                <div>
                  <MessageSquare className="mx-auto mb-3 h-10 w-10 text-blue-300/70" />
                  <p className="text-sm">Select a conversation or start a new one.</p>
                </div>
              </div>
            )}

            {error && (
              <div className="border-t border-red-400/20 bg-red-500/10 px-4 py-2 text-sm text-red-300">
                {error}
              </div>
            )}
          </section>

          {requestedMode === 'customer_service' ? (
            <DisputeContextPanel
              panel={latestDisputePanel}
              collapsed={disputePanelCollapsed}
              onToggle={() => setDisputePanelCollapsed((value) => !value)}
            />
          ) : (
            <ProductPanel products={latestSuggestedProducts} />
          )}
        </div>
      </div>
    </div>
  );
}
