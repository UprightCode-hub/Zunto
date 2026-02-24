import React, { useEffect, useMemo, useRef, useState } from 'react';
import { MessageCircle, Search, Send } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import {
  getChatMessages,
  getChatRooms,
  getChatWebSocketUrl,
  getConversationWsToken,
  sendMarketplaceChatMessage,
} from '../../services/api';

const getConversationTitle = (conversation) => (
  conversation?.product?.title || conversation?.product?.name || 'Conversation'
);

const getPersonLabel = (person) => (
  person?.full_name
  || [person?.first_name, person?.last_name].filter(Boolean).join(' ').trim()
  || person?.email
  || person?.username
  || 'Unknown'
);

const getOtherParticipantLabel = (conversation, user) => {
  const sellerId = conversation?.seller?.id;
  const buyerId = conversation?.buyer?.id;
  if (String(user?.id) === String(sellerId)) {
    return getPersonLabel(conversation?.buyer);
  }
  if (String(user?.id) === String(buyerId)) {
    return getPersonLabel(conversation?.seller);
  }
  return getPersonLabel(conversation?.seller);
};

const MESSAGE_WINDOW_SIZE = 250;

export default function MarketplaceInbox({
  initialConversationId = null,
  containerClassName = 'h-[calc(100vh-140px)]',
  headerTitle = 'Conversations',
  emptyListLabel = 'No conversations yet',
}) {
  const { user } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sendingMessage, setSendingMessage] = useState(false);
  const [newMessage, setNewMessage] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [connectionStatus, setConnectionStatus] = useState('offline');
  const [showConversationListMobile, setShowConversationListMobile] = useState(true);
  const messagesEndRef = useRef(null);
  const wsRef = useRef(null);

  useEffect(() => {
    const loadConversations = async () => {
      try {
        setLoading(true);
        const data = await getChatRooms();
        const nextConversations = Array.isArray(data) ? data : data.results || [];
        setConversations(nextConversations);

        if (nextConversations.length === 0) {
          return;
        }

        const matched = initialConversationId
          ? nextConversations.find((item) => String(item.id) === String(initialConversationId))
          : null;

        setSelectedConversation(matched || nextConversations[0]);
      } catch (error) {
        console.error('Error fetching conversations:', error);
      } finally {
        setLoading(false);
      }
    };

    loadConversations();
  }, [initialConversationId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (!selectedConversation) {
      setMessages([]);
      setConnectionStatus('offline');
      return undefined;
    }

    let active = true;

    const teardown = () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };

    const openConversation = async () => {
      try {
        setConnectionStatus('connecting');
        const data = await getChatMessages(selectedConversation.id);
        if (!active) {
          return;
        }
        const initialMessages = Array.isArray(data?.messages)
          ? data.messages
          : Array.isArray(data)
            ? data
            : data?.results || [];
        setMessages(initialMessages);

        const wsTokenResponse = await getConversationWsToken(selectedConversation.id);
        if (!active) {
          return;
        }
        const wsUrl = getChatWebSocketUrl(selectedConversation.id, wsTokenResponse.ws_token);
        const socket = new WebSocket(wsUrl);
        wsRef.current = socket;

        socket.onopen = () => {
          if (active) {
            setConnectionStatus('online');
          }
        };

        socket.onmessage = (event) => {
          if (!active) {
            return;
          }
          try {
            const payload = JSON.parse(event.data);
            if (payload.type === 'chat_message' && payload.message?.id) {
              setMessages((prev) => {
                if (prev.some((item) => item.id === payload.message.id)) {
                  return prev;
                }
                return [...prev, payload.message];
              });
            }
            if (payload.type === 'message_deleted' && payload.message_id) {
              setMessages((prev) => prev.filter((item) => item.id !== payload.message_id));
            }
          } catch (error) {
            console.error('WebSocket payload parse error:', error);
          }
        };

        socket.onerror = (error) => {
          if (active) {
            console.error('WebSocket error:', error);
          }
        };

        socket.onclose = () => {
          if (active) {
            setConnectionStatus('offline');
          }
        };
      } catch (error) {
        if (active) {
          console.error('Error connecting to conversation:', error);
          setConnectionStatus('offline');
        }
      }
    };

    openConversation();

    return () => {
      active = false;
      teardown();
    };
  }, [selectedConversation]);

  const handleSendMessage = async (event) => {
    event.preventDefault();
    if (!newMessage.trim() || !selectedConversation || sendingMessage) {
      return;
    }

    try {
      setSendingMessage(true);
      const response = await sendMarketplaceChatMessage(selectedConversation.id, newMessage.trim());
      setNewMessage('');
      if (response?.message?.id) {
        setMessages((prev) => {
          if (prev.some((item) => item.id === response.message.id)) {
            return prev;
          }
          return [...prev, response.message];
        });
      }
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setSendingMessage(false);
    }
  };

  const filteredConversations = useMemo(
    () => conversations.filter((conversation) => (
      getConversationTitle(conversation).toLowerCase().includes(searchQuery.toLowerCase())
      || getOtherParticipantLabel(conversation, user).toLowerCase().includes(searchQuery.toLowerCase())
    )),
    [conversations, searchQuery, user],
  );

  const visibleMessages = useMemo(() => messages.slice(-MESSAGE_WINDOW_SIZE), [messages]);

  return (
    <div className={containerClassName}>
      <div className="h-full rounded-2xl border border-[#2c77d1]/20 bg-[#0b1222] overflow-hidden grid grid-cols-1 lg:grid-cols-[340px_1fr]">
        <aside className={`${showConversationListMobile ? 'block' : 'hidden'} lg:block border-r border-[#2c77d1]/20`}>
          <div className="p-4 border-b border-[#2c77d1]/20 sticky top-0 bg-[#0b1222] z-10">
            <h2 className="text-white font-semibold text-lg">{headerTitle}</h2>
            <div className="mt-3 relative">
              <Search className="w-4 h-4 absolute left-3 top-3 text-gray-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search conversations"
                className="w-full rounded-full bg-[#111b32] border border-[#2c77d1]/20 py-2 pl-9 pr-3 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-[#2c77d1]"
              />
            </div>
          </div>

          <div className="h-[calc(100%-90px)] overflow-y-auto">
            {loading ? (
              <div className="p-4 text-sm text-gray-400">Loading conversations...</div>
            ) : filteredConversations.length === 0 ? (
              <div className="p-6 text-center text-sm text-gray-400">
                <MessageCircle className="w-8 h-8 mx-auto mb-2 opacity-60" />
                {emptyListLabel}
              </div>
            ) : (
              filteredConversations.map((conversation) => (
                <button
                  key={conversation.id}
                  onClick={() => {
                    setSelectedConversation(conversation);
                    setShowConversationListMobile(false);
                  }}
                  className={`w-full text-left px-4 py-3 border-b border-[#2c77d1]/10 hover:bg-[#111b32] transition ${selectedConversation?.id === conversation.id ? 'bg-[#14203d]' : ''}`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-semibold text-white truncate">{getConversationTitle(conversation)}</p>
                    <span className="text-[11px] text-gray-500">{new Date(conversation.updated_at || conversation.created_at).toLocaleDateString()}</span>
                  </div>
                  <p className="text-xs text-gray-400 truncate mt-1">{getOtherParticipantLabel(conversation, user)}</p>
                </button>
              ))
            )}
          </div>
        </aside>

        <section className={`${showConversationListMobile ? 'hidden' : 'flex'} lg:flex flex-col`}>
          {selectedConversation ? (
            <>
              <header className="px-4 py-3 border-b border-[#2c77d1]/20 flex items-center justify-between sticky top-0 bg-[#0b1222] z-10">
                <div>
                  <h3 className="text-white font-semibold">{getConversationTitle(selectedConversation)}</h3>
                  <p className="text-xs text-gray-400">
                    {String(selectedConversation?.seller?.id) === String(user?.id)
                      ? `Buyer: ${getPersonLabel(selectedConversation?.buyer)}`
                      : `Seller: ${getPersonLabel(selectedConversation?.seller)}`}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${connectionStatus === 'online' ? 'bg-green-500/20 text-green-300' : connectionStatus === 'connecting' ? 'bg-yellow-500/20 text-yellow-300' : 'bg-gray-500/20 text-gray-300'}`}>
                    {connectionStatus}
                  </span>
                  <button
                    type="button"
                    onClick={() => setShowConversationListMobile(true)}
                    className="lg:hidden text-xs text-blue-300"
                  >
                    Back
                  </button>
                </div>
              </header>

              <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3 bg-[#08101f]">
                {visibleMessages.length === 0 ? (
                  <div className="h-full min-h-[220px] flex items-center justify-center text-sm text-gray-500">No messages yet.</div>
                ) : visibleMessages.map((message) => (
                  <div key={message.id} className={`flex ${message.sender?.id === user?.id ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[82%] rounded-2xl px-4 py-2 ${message.sender?.id === user?.id ? 'bg-gradient-to-r from-[#2c77d1] to-[#9426f4] text-white rounded-br-md' : 'bg-[#1b2846] text-gray-100 rounded-bl-md'}`}>
                      <p className="text-sm whitespace-pre-wrap break-words">{message.content || message.message}</p>
                      <p className="text-[11px] mt-1 opacity-75 text-right">
                        {new Date(message.created_at || message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>

              <form onSubmit={handleSendMessage} className="sticky bottom-0 border-t border-[#2c77d1]/20 p-3 bg-[#0b1222] flex items-center gap-2">
                <input
                  type="text"
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  placeholder="Type a message"
                  disabled={sendingMessage}
                  className="flex-1 rounded-full bg-[#111b32] border border-[#2c77d1]/20 px-4 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-[#2c77d1] disabled:opacity-60"
                />
                <button
                  type="submit"
                  disabled={!newMessage.trim() || sendingMessage}
                  className="inline-flex items-center justify-center rounded-full px-4 py-2 bg-gradient-to-r from-[#2c77d1] to-[#9426f4] text-white font-semibold disabled:opacity-50"
                >
                  <Send className="w-4 h-4" />
                </button>
              </form>
            </>
          ) : (
            <div className="h-full flex items-center justify-center text-gray-400 text-sm">Select a conversation.</div>
          )}
        </section>
      </div>
    </div>
  );
}
