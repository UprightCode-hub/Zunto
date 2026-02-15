import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { getChatRooms, getChatMessages, sendMarketplaceChatMessage } from '../services/api';
import { Send, MessageCircle, Search } from 'lucide-react';

export default function Chat() {
  const { user } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sendingMessage, setSendingMessage] = useState(false);
  const [newMessage, setNewMessage] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const messagesEndRef = useRef(null);
  const pollInterval = useRef(null);

  useEffect(() => {
    fetchConversations();
  }, []);

  const fetchConversations = async () => {
    try {
      setLoading(true);
      const data = await getChatRooms();
      setConversations(Array.isArray(data) ? data : data.results || []);
    } catch (err) {
      console.error('Error fetching conversations:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!selectedConversation) return;

    const fetchMessages = async () => {
      try {
        const data = await getChatMessages(selectedConversation.id);
        setMessages(Array.isArray(data) ? data : data.results || []);
      } catch (err) {
        console.error('Error fetching messages:', err);
      }
    };

    fetchMessages();

    // Poll for new messages every 3 seconds
    pollInterval.current = setInterval(fetchMessages, 3000);

    return () => {
      if (pollInterval.current) clearInterval(pollInterval.current);
    };
  }, [selectedConversation]);

  useEffect(() => {
    // Auto-scroll to bottom
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !selectedConversation) return;

    try {
      setSendingMessage(true);
      await sendMarketplaceChatMessage(selectedConversation.id, newMessage);
      setNewMessage('');
      
      // Fetch updated messages
      const data = await getChatMessages(selectedConversation.id);
      setMessages(Array.isArray(data) ? data : data.results || []);
    } catch (err) {
      console.error('Error sending message:', err);
      alert('Failed to send message');
    } finally {
      setSendingMessage(false);
    }
  };

  const filteredConversations = conversations.filter(conv =>
    (conv.product?.name || 'Chat').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (conv.seller?.username || conv.buyer?.username || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen pt-20 pb-12 bg-black">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-[calc(100vh-100px)]">
        <div className="h-full flex flex-col lg:flex-row gap-4">
          {/* Conversations List */}
          <div className="lg:w-80 flex flex-col bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl overflow-hidden">
            <div className="p-6 border-b border-[#2c77d1]/20">
              <h1 className="text-2xl font-bold mb-4">Messages</h1>
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
                  <div className="w-6 h-6 border-2 border-[#2c77d1] border-t-transparent rounded-full animate-spin"></div>
                </div>
              ) : filteredConversations.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-32 text-gray-400">
                  <MessageCircle className="w-8 h-8 mb-2" />
                  <p className="text-sm">No conversations yet</p>
                </div>
              ) : (
                <div>
                  {filteredConversations.map(conversation => (
                    <button
                      key={conversation.id}
                      onClick={() => setSelectedConversation(conversation)}
                      className={`w-full p-4 border-b border-[#2c77d1]/10 text-left hover:bg-[#2c77d1]/10 transition ${
                        selectedConversation?.id === conversation.id
                          ? 'bg-[#2c77d1]/20 border-l-2 border-l-[#2c77d1]'
                          : ''
                      }`}
                    >
                      <h3 className="font-semibold text-white truncate">
                        {conversation.product?.name || 'Chat'}
                      </h3>
                      <p className="text-xs text-gray-400 truncate mt-1">
                        {conversation.seller?.username && conversation.buyer?.username
                          ? `${conversation.seller.username === user?.username ? conversation.buyer.username : conversation.seller.username}`
                          : 'Loading...'}
                      </p>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Messages Area */}
          <div className="flex-1 flex flex-col bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl overflow-hidden">
            {selectedConversation ? (
              <>
                {/* Chat Header */}
                <div className="p-6 border-b border-[#2c77d1]/20">
                  <h2 className="text-xl font-semibold text-white">
                    {selectedConversation.product?.name || 'Chat'}
                  </h2>
                  <p className="text-sm text-gray-400 mt-1">
                    {selectedConversation.seller?.username === user?.username
                      ? `Buyer: ${selectedConversation.buyer?.username}`
                      : `Seller: ${selectedConversation.seller?.username}`}
                  </p>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-6 space-y-4">
                  {messages.length === 0 ? (
                    <div className="flex items-center justify-center h-full text-gray-500">
                      <p>No messages yet. Start the conversation!</p>
                    </div>
                  ) : (
                    messages.map(msg => (
                      <div
                        key={msg.id}
                        className={`flex ${
                          msg.sender?.id === user?.id ? 'justify-end' : 'justify-start'
                        }`}
                      >
                        <div
                          className={`max-w-xs px-4 py-3 rounded-2xl ${
                            msg.sender?.id === user?.id
                              ? 'bg-gradient-to-r from-[#2c77d1] to-[#9426f4] text-white'
                              : 'bg-[#2a2a2a] text-gray-200'
                          }`}
                        >
                          <p className="break-words">{msg.content || msg.message}</p>
                          <p className={`text-xs mt-1 opacity-70 ${
                            msg.sender?.id === user?.id ? 'text-white' : 'text-gray-400'
                          }`}>
                            {new Date(msg.created_at || msg.timestamp).toLocaleTimeString([], {
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

                {/* Message Input */}
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
    </div>
  );
}
