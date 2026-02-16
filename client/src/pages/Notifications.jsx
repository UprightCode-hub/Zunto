import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { getNotifications, markNotificationAsRead } from '../services/api';
import { Bell, CheckCircle2, AlertCircle, Info, Trash2 } from 'lucide-react';

const NOTIFICATION_TYPES = {
  order: { icon: '📦', label: 'Order', color: 'bg-blue-500/10 text-blue-400 border-blue-500/20' },
  message: { icon: '💬', label: 'Message', color: 'bg-purple-500/10 text-purple-400 border-purple-500/20' },
  review: { icon: '⭐', label: 'Review', color: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20' },
  product: { icon: '🛍️', label: 'Product', color: 'bg-green-500/10 text-green-400 border-green-500/20' },
  system: { icon: 'ℹ️', label: 'System', color: 'bg-gray-500/10 text-gray-400 border-gray-500/20' },
};

export default function Notifications() {
  useAuth();
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // all, unread, read
  const pollInterval = useRef(null);

  const fetchNotifications = async () => {
    try {
      const data = await getNotifications();
      setNotifications(Array.isArray(data) ? data : data.results || []);
      setLoading(false);
    } catch (err) {
      console.error('Error fetching notifications:', err);
      setLoading(false);
    }
  };


  useEffect(() => {
    const startupTimer = setTimeout(fetchNotifications, 0);

    // Poll for new notifications every 5 seconds
    pollInterval.current = setInterval(fetchNotifications, 5000);

    return () => {
      clearTimeout(startupTimer);
      if (pollInterval.current) clearInterval(pollInterval.current);
    };
  }, []);

  const handleMarkAsRead = async (notificationId, e) => {
    e.stopPropagation();
    try {
      await markNotificationAsRead(notificationId);
      setNotifications(notifications.map(n => 
        n.id === notificationId ? { ...n, is_read: true } : n
      ));
    } catch (err) {
      console.error('Error marking notification as read:', err);
    }
  };

  const handleDeleteNotification = (notificationId, e) => {
    e.stopPropagation();
    setNotifications(notifications.filter(n => n.id !== notificationId));
  };

  const filteredNotifications = notifications.filter(n => {
    if (filter === 'unread') return !n.is_read;
    if (filter === 'read') return n.is_read;
    return true;
  });

  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <div className="min-h-screen pt-20 pb-12">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <h1 className="text-4xl font-bold">Notifications</h1>
            {unreadCount > 0 && (
              <span className="px-3 py-1 bg-red-500 text-white rounded-full text-sm font-semibold">
                {unreadCount} New
              </span>
            )}
          </div>
          <p className="text-gray-400">Stay updated with your activities</p>
        </div>

        {/* Filter Tabs */}
        <div className="flex gap-3 mb-8 border-b border-[#2c77d1]/20">
          {[
            { value: 'all', label: `All (${notifications.length})` },
            { value: 'unread', label: `Unread (${unreadCount})` },
            { value: 'read', label: `Read (${notifications.filter(n => n.is_read).length})` },
          ].map(tab => (
            <button
              key={tab.value}
              onClick={() => setFilter(tab.value)}
              className={`pb-4 px-4 font-semibold transition ${
                filter === tab.value
                  ? 'border-b-2 border-[#2c77d1] text-[#2c77d1]'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Notifications List */}
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="w-8 h-8 border-2 border-[#2c77d1] border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : filteredNotifications.length === 0 ? (
          <div className="text-center py-12 bg-[#1a1a1a] rounded-2xl border border-[#2c77d1]/20">
            <Bell className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400 text-lg">
              {filter === 'unread' ? 'No unread notifications' : 'No notifications'}
            </p>
            <p className="text-gray-500 text-sm mt-2">You're all caught up!</p>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredNotifications.map(notification => {
              const notifType = NOTIFICATION_TYPES[notification.type] || NOTIFICATION_TYPES.system;
              
              return (
                <div
                  key={notification.id}
                  className={`p-5 rounded-xl border transition cursor-pointer hover:border-[#2c77d1]/60 ${
                    notification.is_read
                      ? 'bg-[#1a1a1a] border-[#2c77d1]/10'
                      : 'bg-[#2c77d1]/5 border-[#2c77d1]/30 shadow-lg shadow-[#2c77d1]/5'
                  }`}
                >
                  <div className="flex items-start gap-4">
                    {/* Icon */}
                    <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${notifType.color} border`}>
                      {notifType.icon}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-4 mb-1">
                        <div>
                          <h3 className={`font-semibold ${notification.is_read ? 'text-gray-300' : 'text-white'}`}>
                            {notification.title || 'Notification'}
                          </h3>
                          {notification.type_display && (
                            <span className="inline-block mt-1 px-2 py-0.5 text-xs font-medium bg-[#2c77d1]/10 text-[#2c77d1] rounded">
                              {notification.type_display}
                            </span>
                          )}
                        </div>
                        {!notification.is_read && (
                          <div className="flex-shrink-0">
                            <CheckCircle2 className="w-5 h-5 text-[#2c77d1] opacity-60" />
                          </div>
                        )}
                      </div>
                      
                      <p className="text-gray-400 text-sm mt-2 line-clamp-2">
                        {notification.message || notification.description}
                      </p>

                      <p className="text-xs text-gray-500 mt-3">
                        {new Date(notification.created_at || notification.timestamp).toLocaleString([], {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </p>
                    </div>

                    {/* Actions */}
                    <div className="flex-shrink-0 flex gap-2">
                      {!notification.is_read && (
                        <button
                          onClick={(e) => handleMarkAsRead(notification.id, e)}
                          className="p-2 hover:bg-[#2c77d1]/20 rounded-lg transition"
                          title="Mark as read"
                        >
                          <CheckCircle2 className="w-5 h-5 text-[#2c77d1]" />
                        </button>
                      )}
                      <button
                        onClick={(e) => handleDeleteNotification(notification.id, e)}
                        className="p-2 hover:bg-red-500/20 rounded-lg transition"
                        title="Delete"
                      >
                        <Trash2 className="w-5 h-5 text-red-500" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
