import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { MessageCircle, Search, Send } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import {
  getChatMessages,
  getChatRooms,
  getChatWebSocketUrl,
  getConversationWsToken,
  sendMarketplaceChatMessage,
} from '../../services/api';
import { buildClientWsEnvelope, dispatchInboxWsEvent, parseAndNormalizeWsEvent } from './wsProtocol';

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



const getConversationPreview = (conversation) => (
  conversation?.last_message?.content
  || conversation?.last_message?.message
  || conversation?.last_message_preview
  || ''
);

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
  const processedEventIdsRef = useRef(new Set());
  const typingStopTimerRef = useRef(null);
  const isTypingActiveRef = useRef(false);
  const [typingMap, setTypingMap] = useState(new Map());
  const [presenceMap, setPresenceMap] = useState(new Map());
  const [readMap, setReadMap] = useState(new Map());


  const clearTypingForConversation = (conversationId) => {
    setTypingMap((prev) => {
      const next = new Map(prev);
      next.delete(String(conversationId));
      return next;
    });
  };

  const upsertTyping = (conversationId, actorId) => {
    const expiresAt = Date.now() + 3000;
    setTypingMap((prev) => {
      const next = new Map(prev);
      next.set(String(conversationId), {
        actor_id: String(actorId),
        expiresAt,
      });
      return next;
    });
  };


  const setParticipantPresence = (conversationId, actorId, status) => {
    if (!conversationId || !actorId) return;
    setPresenceMap((prev) => {
      const next = new Map(prev);
      const convPresence = new Map(next.get(String(conversationId)) || []);
      convPresence.set(String(actorId), status);
      next.set(String(conversationId), convPresence);
      return next;
    });
  };

  const applyPresenceSnapshot = (conversationId, participants) => {
    if (!conversationId || !Array.isArray(participants)) return;
    setPresenceMap((prev) => {
      const next = new Map(prev);
      const convPresence = new Map();
      participants.forEach((participant) => {
        if (!participant?.actor_id) return;
        convPresence.set(String(participant.actor_id), participant.status === 'online' ? 'online' : 'offline');
      });
      next.set(String(conversationId), convPresence);
      return next;
    });
  };

  const getOtherParticipantOnline = (conversation) => {
    const convPresence = presenceMap.get(String(conversation?.id));
    if (!convPresence) return false;
    const otherActorId = String(conversation?.seller?.id) === String(user?.id)
      ? String(conversation?.buyer?.id || '')
      : String(conversation?.seller?.id || '');
    return convPresence.get(otherActorId) === 'online';
  };


  const applyReadSnapshot = (conversationId, watermarks) => {
    if (!conversationId || !Array.isArray(watermarks)) return;
    setReadMap((prev) => {
      const next = new Map(prev);
      const convReads = new Map();
      watermarks.forEach((item) => {
        if (!item?.actor_id || !item?.last_read_message_id) return;
        convReads.set(String(item.actor_id), String(item.last_read_message_id));
      });
      next.set(String(conversationId), convReads);
      return next;
    });
  };

  const updateReadWatermark = (conversationId, actorId, lastReadMessageId) => {
    if (!conversationId || !actorId || !lastReadMessageId) return;
    setReadMap((prev) => {
      const next = new Map(prev);
      const convReads = new Map(next.get(String(conversationId)) || []);
      convReads.set(String(actorId), String(lastReadMessageId));
      next.set(String(conversationId), convReads);
      return next;
    });
  };

  const getOtherParticipantReadMessageId = (conversation) => {
    const convReads = readMap.get(String(conversation?.id));
    if (!convReads) return null;
    const otherActorId = String(conversation?.seller?.id) === String(user?.id)
      ? String(conversation?.buyer?.id || '')
      : String(conversation?.seller?.id || '');
    return convReads.get(otherActorId) || null;
  };

  const emitReadUpdate = useCallback((socket, conversationId, lastReadMessageId) => {
    if (!socket || socket.readyState !== WebSocket.OPEN || !conversationId || !lastReadMessageId) {
      return;
    }
    socket.send(JSON.stringify(buildClientWsEnvelope({
      type: 'chat.read.updated',
      conversationId,
      actorId: user?.id,
      payload: {
        last_read_message_id: String(lastReadMessageId),
      },
      idempotencyKey: `read-${conversationId}-${lastReadMessageId}`,
    })));
  }, [user?.id]);

  const emitTypingEvent = useCallback((socket, type, conversationIdOverride = null) => {
    const conversationId = conversationIdOverride || selectedConversation?.id;
    if (!socket || socket.readyState !== WebSocket.OPEN || !conversationId) {
      return;
    }
    socket.send(JSON.stringify(buildClientWsEnvelope({
      type,
      conversationId,
      actorId: user?.id,
      payload: {},
    })));
  }, [selectedConversation?.id, user?.id]);

  const scheduleTypingStop = useCallback((socket, conversationIdOverride = null) => {
    if (typingStopTimerRef.current) {
      window.clearTimeout(typingStopTimerRef.current);
    }
    typingStopTimerRef.current = window.setTimeout(() => {
      if (!isTypingActiveRef.current) {
        return;
      }
      emitTypingEvent(socket, 'chat.typing.stop', conversationIdOverride);
      isTypingActiveRef.current = false;
    }, 3000);
  }, [emitTypingEvent]);

  const stopTypingNow = useCallback((socket, conversationIdOverride = null) => {
    if (typingStopTimerRef.current) {
      window.clearTimeout(typingStopTimerRef.current);
      typingStopTimerRef.current = null;
    }
    if (isTypingActiveRef.current) {
      emitTypingEvent(socket, 'chat.typing.stop', conversationIdOverride);
      isTypingActiveRef.current = false;
    }
  }, [emitTypingEvent]);

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
    const interval = window.setInterval(() => {
      const now = Date.now();
      setTypingMap((prev) => {
        const next = new Map(prev);
        let changed = false;
        next.forEach((value, key) => {
          if (!value || value.expiresAt <= now) {
            next.delete(key);
            changed = true;
          }
        });
        return changed ? next : prev;
      });
    }, 500);

    return () => {
      window.clearInterval(interval);
      if (typingStopTimerRef.current) {
        window.clearTimeout(typingStopTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!selectedConversation) {
      setMessages([]);
      setConnectionStatus('offline');
      return undefined;
    }

    let active = true;

    const teardown = () => {
      stopTypingNow(wsRef.current, selectedConversation?.id);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      clearTypingForConversation(selectedConversation?.id);
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
        lastSeenSeqRef.current.set(String(selectedConversation.id), 0);
        reorderBufferRef.current.set(String(selectedConversation.id), new Map());

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

          const parsed = parseAndNormalizeWsEvent(event.data);
          if (!parsed.ok) {
            console.warn('Dropped malformed/unsupported WS event:', parsed.reason);
            return;
          }

          const wsEvent = parsed.event;
          if (processedEventIdsRef.current.has(wsEvent.event_id)) {
            return;
          }
          processedEventIdsRef.current.add(wsEvent.event_id);

          if (processedEventIdsRef.current.size > 1000) {
            const values = Array.from(processedEventIdsRef.current.values());
            processedEventIdsRef.current = new Set(values.slice(-750));
          }

          if (String(wsEvent.conversation_id) !== String(selectedConversation.id)) {
            return;
          }

          dispatchInboxWsEvent({
            event: wsEvent,
            handlers: {
              'chat.message.created': (typedEvent) => {
                const nextMessage = typedEvent?.payload?.message;
                clearTypingForConversation(typedEvent.conversation_id);
                if (!nextMessage?.id) return;
                setMessages((prev) => {
                  if (prev.some((item) => item.id === nextMessage.id)) {
                    return prev;
                  }
                  return [...prev, nextMessage];
                });
              },
              'chat.message.deleted': (typedEvent) => {
                const messageId = typedEvent?.payload?.message_id;
                if (!messageId) return;
                setMessages((prev) => prev.filter((item) => String(item.id) !== String(messageId)));
              },
              'chat.message.ack': () => {},
              'chat.history.synced': (typedEvent) => {
                const history = typedEvent?.payload?.messages;
                if (!Array.isArray(history)) return;
                setMessages(history);
              },
              'chat.error': (typedEvent) => {
                console.warn('Chat protocol error:', typedEvent?.payload?.reason || typedEvent?.payload?.message);
              },
              'chat.warning': () => {},
              'chat.typing.start': (typedEvent) => {
                const actorId = typedEvent?.payload?.actor_id || typedEvent?.actor_id;
                if (!actorId || String(actorId) === String(user?.id)) return;
                upsertTyping(typedEvent.conversation_id, actorId);
              },
              'chat.typing.stop': (typedEvent) => {
                clearTypingForConversation(typedEvent.conversation_id);
              },
              'chat.presence.online': (typedEvent) => {
                const actorId = typedEvent?.payload?.actor_id;
                setParticipantPresence(typedEvent.conversation_id, actorId, 'online');
              },
              'chat.presence.offline': (typedEvent) => {
                const actorId = typedEvent?.payload?.actor_id;
                setParticipantPresence(typedEvent.conversation_id, actorId, 'offline');
              },
              'chat.presence.snapshot': (typedEvent) => {
                applyPresenceSnapshot(typedEvent.conversation_id, typedEvent?.payload?.participants);
              },
              'chat.read.updated': (typedEvent) => {
                const actorId = typedEvent?.payload?.actor_id;
                const lastReadMessageId = typedEvent?.payload?.last_read_message_id;
                updateReadWatermark(typedEvent.conversation_id, actorId, lastReadMessageId);
              },
              'chat.read.snapshot': (typedEvent) => {
                applyReadSnapshot(typedEvent.conversation_id, typedEvent?.payload?.watermarks);
              },
              'chat.ping': () => {
                socket.send(JSON.stringify(buildClientWsEnvelope({
                  type: 'chat.pong',
                  conversationId: selectedConversation.id,
                  actorId: user?.id,
                  payload: { timestamp: Date.now() },
                })));
              },
              'chat.pong': () => {},
              'chat.message.updated': () => {},
            },
            onUnhandled: (_unknownEvent, reason) => {
              console.warn('Unhandled ws event dropped:', reason);
            },
          });
        };

        socket.onerror = (error) => {
          if (active) {
            console.error('WebSocket error:', error);
          }
        };

        socket.onclose = () => {
          stopTypingNow(socket);
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
  }, [selectedConversation, stopTypingNow, user?.id]);

  const handleSendMessage = async (event) => {
    event.preventDefault();
    if (!newMessage.trim() || !selectedConversation || sendingMessage) {
      return;
    }

    try {
      stopTypingNow(wsRef.current, selectedConversation?.id);
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

  const activeTyping = typingMap.get(String(selectedConversation?.id || ''));
  const isConversationTyping = Boolean(activeTyping && activeTyping.expiresAt > Date.now() && String(activeTyping.actor_id) !== String(user?.id));


  useEffect(() => {
    if (!selectedConversation?.id || visibleMessages.length === 0) {
      return;
    }

    const socket = wsRef.current;
    const latestMessage = visibleMessages[visibleMessages.length - 1];
    if (!latestMessage?.id) {
      return;
    }

    emitReadUpdate(socket, selectedConversation.id, latestMessage.id);
    updateReadWatermark(selectedConversation.id, user?.id, latestMessage.id);
  }, [emitReadUpdate, visibleMessages, selectedConversation?.id, user?.id]);

  const handleComposerChange = (value) => {
    setNewMessage(value);
    const socket = wsRef.current;

    if (!value.trim()) {
      stopTypingNow(socket);
      return;
    }

    if (!isTypingActiveRef.current) {
      emitTypingEvent(socket, 'chat.typing.start');
      isTypingActiveRef.current = true;
    }
    scheduleTypingStop(socket, selectedConversation?.id);
  };

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
                  <p className="text-xs text-gray-400 truncate mt-1">{typingMap.get(String(conversation.id))?.expiresAt > Date.now() && String(typingMap.get(String(conversation.id))?.actor_id) !== String(user?.id) ? 'Typing…' : `${getOtherParticipantOnline(conversation) ? '● ' : ''}${getConversationPreview(conversation) || getOtherParticipantLabel(conversation, user)}`}</p>
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
                    {getOtherParticipantOnline(selectedConversation) ? ' · online' : ''}
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
                ) : visibleMessages.map((message, index) => {
                  const isOwn = message.sender?.id === user?.id;
                  const isLastOwn = isOwn && index === visibleMessages.length - 1;
                  const seenMessageId = getOtherParticipantReadMessageId(selectedConversation);
                  const isSeen = isLastOwn && seenMessageId && String(seenMessageId) === String(message.id);
                  return (
                    <div key={message.id} className={`flex ${isOwn ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[82%] rounded-2xl px-4 py-2 ${isOwn ? 'bg-gradient-to-r from-[#2c77d1] to-[#9426f4] text-white rounded-br-md' : 'bg-[#1b2846] text-gray-100 rounded-bl-md'}`}>
                        <p className="text-sm whitespace-pre-wrap break-words">{message.content || message.message}</p>
                        <p className="text-[11px] mt-1 opacity-75 text-right">
                          {new Date(message.created_at || message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          {isSeen ? ' · Seen' : ''}
                        </p>
                      </div>
                    </div>
                  );
                })}
                <div ref={messagesEndRef} />
              </div>

              {isConversationTyping ? (
                <div className="px-4 py-2 text-xs text-gray-400 border-t border-[#2c77d1]/10">Typing…</div>
              ) : null}

              <form onSubmit={handleSendMessage} className="sticky bottom-0 border-t border-[#2c77d1]/20 p-3 bg-[#0b1222] flex items-center gap-2">
                <input
                  type="text"
                  value={newMessage}
                  onChange={(e) => handleComposerChange(e.target.value)}
                  onBlur={() => stopTypingNow(wsRef.current)}
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
