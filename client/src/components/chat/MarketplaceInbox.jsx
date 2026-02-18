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
  conversation?.product?.title || conversation?.product?.name || 'Chat'
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
  const isSeller = String(user?.id) === String(sellerId);

  if (isSeller) {
    return getPersonLabel(conversation?.buyer);
  }

  if (String(user?.id) === String(buyerId)) {
    return getPersonLabel(conversation?.seller);
  }

  return getPersonLabel(conversation?.seller);
};

export default function MarketplaceInbox({
  initialConversationId = null,
  containerClassName = 'h-[calc(100vh-100px)]',
  headerTitle = 'Messages',
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
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
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
          ? nextConversations.find((conversation) => String(conversation.id) === String(initialConversationId))
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
      setConnectionStatus('disconnected');
      return undefined;
    }

    let isMounted = true;

    const closeSocket = () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };

    const loadMessages = async () => {
      const data = await getChatMessages(selectedConversation.id);
      if (!isMounted) {
        return;
      }

      const nextMessages = Array.isArray(data?.messages)
        ? data.messages
        : Array.isArray(data)
          ? data
          : data?.results || [];

      setMessages(nextMessages);
    };

    const connectSocket = async () => {
      try {
        setConnectionStatus('connecting');
        await loadMessages();

        const wsTokenResponse = await getConversationWsToken(selectedConversation.id);
        const wsUrl = getChatWebSocketUrl(selectedConversation.id, wsTokenResponse.ws_token);
        const socket = new WebSocket(wsUrl);

        wsRef.current = socket;

        socket.onopen = () => {
          if (isMounted) {
            setConnectionStatus('connected');
          }
        };

        socket.onmessage = (event) => {
          if (!isMounted) {
            return;
          }

          try {
            const payload = JSON.parse(event.data);

            if (payload.type === 'chat_message' && payload.message?.id) {
              setMessages((prev) => {
                if (prev.some((message) => message.id === payload.message.id)) {
                  return prev;
                }
                return [...prev, payload.message];
              });
            }

            if (payload.type === 'message_deleted' && payload.message_id) {
              setMessages((prev) => prev.filter((message) => message.id !== payload.message_id));
            }
          } catch (parseError) {
            console.error('WebSocket payload parse error:', parseError);
          }
        };

        socket.onerror = (error) => {
          if (isMounted) {
            console.error('WebSocket error:', error);
          }
        };

        socket.onclose = () => {
          if (isMounted) {
            setConnectionStatus('disconnected');
          }
        };
      } catch (error) {
        if (isMounted) {
          console.error('Error connecting to conversation:', error);
          setConnectionStatus('disconnected');
        }
      }
    };

    connectSocket();

    return () => {
      isMounted = false;
      closeSocket();
    };
  }, [selectedConversation]);

  const handleSendMessage = async (event) => {
    event.preventDefault();
    if (!newMessage.trim() || !selectedConversation) {
      return;
    }

    try {
      setSendingMessage(true);
      const response = await sendMarketplaceChatMessage(selectedConversation.id, newMessage.trim());
      setNewMessage('');

      if (response?.message?.id) {
        setMessages((prev) => {
          if (prev.some((message) => message.id === response.message.id)) {
            return prev;
          }
          return [...prev, response.message];
        });
      }
    } catch (error) {
      console.error('Error sending message:', error);
      alert('Failed to send message');
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

  return (
    <div className={`${containerClassName}`}>
      <div className="h-full flex flex-col lg:flex-row gap-4">
        <div className="lg:w-80 flex flex-col bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl overflow-hidden">
          <div className="p-6 border-b border-[#2c77d1]/20">
            <h1 className="text-2xl font-bold mb-4">{headerTitle}</h1>
            <div className="relative">
              <Search className="w-5 h-5 absolute left-3 top-3 text-gray-500" />
              <input
                type="text"
                placeholder="Search conversations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-[#2a2a2a] border border-[#2c77d1]/20 rounded-lg focus:outline-none focus:border-[#2c77d1] text-white text-sm"
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center h-32">
                <div className="w-6 h-6 border-2 border-[#2c77d1] border-t-transparent rounded-full animate-spin" />
              </div>
            ) : filteredConversations.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-32 text-gray-400">
                <MessageCircle className="w-8 h-8 mb-2" />
                <p className="text-sm">{emptyListLabel}</p>
              </div>
            ) : (
              filteredConversations.map((conversation) => (
                <button
                  key={conversation.id}
                  onClick={() => setSelectedConversation(conversation)}
                  className={`w-full p-4 border-b border-[#2c77d1]/10 text-left hover:bg-[#2c77d1]/10 transition ${
                    selectedConversation?.id === conversation.id
                      ? 'bg-[#2c77d1]/20 border-l-2 border-l-[#2c77d1]'
                      : ''
                  }`}
                >
                  <h3 className="font-semibold text-white truncate">{getConversationTitle(conversation)}</h3>
                  <p className="text-xs text-gray-400 truncate mt-1">
                    {getOtherParticipantLabel(conversation, user)}
                  </p>
                </button>
              ))
            )}
          </div>
        </div>

        <div className="flex-1 flex flex-col bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl overflow-hidden">
          {selectedConversation ? (
            <>
              <div className="p-6 border-b border-[#2c77d1]/20 flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-white">
                    {getConversationTitle(selectedConversation)}
                  </h2>
                  <p className="text-sm text-gray-400 mt-1">
                    {String(selectedConversation?.seller?.id) === String(user?.id)
                      ? `Buyer: ${getPersonLabel(selectedConversation?.buyer)}`
                      : `Seller: ${getPersonLabel(selectedConversation?.seller)}`}
                  </p>
                </div>
                <span
                  className={`text-xs font-medium px-3 py-1 rounded-full ${
                    connectionStatus === 'connected'
                      ? 'bg-green-500/20 text-green-400'
                      : connectionStatus === 'connecting'
                        ? 'bg-yellow-500/20 text-yellow-400'
                        : 'bg-gray-500/20 text-gray-300'
                  }`}
                >
                  {connectionStatus}
                </span>
              </div>

              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {messages.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-gray-500">
                    <p>No messages yet. Start the conversation!</p>
                  </div>
                ) : (
                  messages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex ${
                        message.sender?.id === user?.id ? 'justify-end' : 'justify-start'
                      }`}
                    >
                      <div
                        className={`max-w-xs px-4 py-3 rounded-2xl ${
                          message.sender?.id === user?.id
                            ? 'bg-gradient-to-r from-[#2c77d1] to-[#9426f4] text-white'
                            : 'bg-[#2a2a2a] text-gray-200'
                        }`}
                      >
                        <p className="break-words">{message.content || message.message}</p>
                        <p
                          className={`text-xs mt-1 opacity-70 ${
                            message.sender?.id === user?.id ? 'text-white' : 'text-gray-400'
                          }`}
                        >
                          {new Date(message.created_at || message.timestamp).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </p>
                      </div>
                    </div>
                  ))
                )}
                <div ref={messagesEndRef} />
              </div>

              <form
                onSubmit={handleSendMessage}
                className="p-6 border-t border-[#2c77d1]/20 flex gap-3"
              >
                <input
                  type="text"
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  placeholder="Type a message..."
                  disabled={sendingMessage}
                  className="flex-1 px-4 py-3 bg-[#2a2a2a] border border-[#2c77d1]/20 rounded-lg focus:outline-none focus:border-[#2c77d1] text-white placeholder-gray-500 disabled:opacity-50"
                />
                <button
                  type="submit"
                  disabled={!newMessage.trim() || sendingMessage}
                  className="px-4 py-3 bg-gradient-to-r from-[#2c77d1] to-[#9426f4] rounded-lg hover:opacity-90 transition disabled:opacity-50 flex items-center gap-2 font-semibold"
                >
                  <Send className="w-5 h-5" />
                </button>
              </form>
            </>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500">
              <div className="text-center">
                <MessageCircle className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p>Select a conversation to start messaging</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
