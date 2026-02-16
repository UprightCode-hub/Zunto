import React, { useEffect, useState } from 'react';
import { getNotificationPreferences, updateNotificationPreferences } from '../services/api';

const FIELDS = [
  { key: 'email_order_updates', label: 'Email: Order updates' },
  { key: 'email_payment_updates', label: 'Email: Payment updates' },
  { key: 'email_shipping_updates', label: 'Email: Shipping updates' },
  { key: 'email_promotional', label: 'Email: Marketing offers' },
  { key: 'email_review_reminders', label: 'Email: Review reminders' },
  { key: 'email_cart_abandonment', label: 'Email: Cart reminders' },
  { key: 'email_seller_new_orders', label: 'Seller: New order alerts' },
  { key: 'email_seller_reviews', label: 'Seller: New review alerts' },
  { key: 'email_seller_messages', label: 'Seller: New message alerts' },
];

export default function NotificationSettings() {
  const [prefs, setPrefs] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const data = await getNotificationPreferences();
        setPrefs(data || {});
      } catch (error) {
        console.error('Failed to load notification preferences', error);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const toggle = (key) => {
    setPrefs((prev) => ({ ...prev, [key]: !prev[key] }));
    setMessage('');
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      const updated = await updateNotificationPreferences(prefs);
      setPrefs(updated || prefs);
      setMessage('Notification preferences saved.');
    } catch (error) {
      setMessage(error?.data?.error || error?.data?.detail || 'Failed to save preferences.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen pt-20 pb-12">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 className="text-3xl font-bold mb-2">Notification Preferences</h1>
        <p className="text-gray-400 mb-6">Control which updates you receive.</p>

        <div className="bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl p-6 space-y-4">
          {loading ? (
            <p className="text-gray-400">Loading preferences...</p>
          ) : (
            FIELDS.map((field) => (
              <label key={field.key} className="flex items-center justify-between py-3 border-b border-[#2c77d1]/10 last:border-b-0">
                <span className="text-gray-200">{field.label}</span>
                <input
                  type="checkbox"
                  checked={Boolean(prefs[field.key])}
                  onChange={() => toggle(field.key)}
                  className="h-5 w-5 accent-[#2c77d1]"
                />
              </label>
            ))
          )}

          <div className="pt-2">
            <button onClick={handleSave} disabled={saving || loading} className="px-5 py-2 bg-[#2c77d1] hover:bg-[#256bbd] rounded-lg font-semibold disabled:opacity-60">
              {saving ? 'Saving...' : 'Save Preferences'}
            </button>
            {message && <p className="text-sm text-gray-300 mt-3">{message}</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
