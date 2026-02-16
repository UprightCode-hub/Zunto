import React, { useEffect, useState } from 'react';
import {
  createShippingAddress,
  deleteShippingAddress,
  getShippingAddresses,
  setDefaultAddress,
} from '../services/api';

const INITIAL_FORM = {
  label: '',
  full_name: '',
  phone: '',
  address: '',
  city: '',
  state: '',
  country: 'Nigeria',
  postal_code: '',
};

export default function ShippingAddresses() {
  const [addresses, setAddresses] = useState([]);
  const [form, setForm] = useState(INITIAL_FORM);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const loadAddresses = async () => {
    try {
      setLoading(true);
      const data = await getShippingAddresses();
      setAddresses(Array.isArray(data) ? data : data.results || []);
    } catch (error) {
      console.error('Error loading addresses:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAddresses();
  }, []);

  const handleCreate = async (event) => {
    event.preventDefault();
    try {
      setSaving(true);
      await createShippingAddress(form);
      setForm(INITIAL_FORM);
      await loadAddresses();
    } catch (error) {
      console.error('Failed to save address:', error);
      alert(error?.data?.error || error?.data?.detail || 'Failed to save address');
    } finally {
      setSaving(false);
    }
  };

  const handleSetDefault = async (id) => {
    try {
      await setDefaultAddress(id);
      await loadAddresses();
    } catch (error) {
      console.error('Failed to set default:', error);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this address?')) return;
    try {
      await deleteShippingAddress(id);
      await loadAddresses();
    } catch (error) {
      console.error('Failed to delete address:', error);
    }
  };

  return (
    <div className="min-h-screen pt-20 pb-12">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 grid lg:grid-cols-2 gap-8">
        <section>
          <h1 className="text-3xl font-bold mb-2">Shipping Address Book</h1>
          <p className="text-gray-400 mb-6">Used for managed seller checkout and delivery.</p>

          {loading ? (
            <p className="text-gray-400">Loading addresses...</p>
          ) : addresses.length === 0 ? (
            <p className="text-gray-400">No saved addresses yet.</p>
          ) : (
            <div className="space-y-3">
              {addresses.map((address) => (
                <div key={address.id} className="bg-[#1a1a1a] rounded-xl border border-[#2c77d1]/20 p-4">
                  <div className="flex justify-between gap-3">
                    <div>
                      <p className="font-semibold">{address.label} {address.is_default && <span className="text-xs text-[#2c77d1]">(Default)</span>}</p>
                      <p className="text-sm text-gray-400">{address.full_name} • {address.phone}</p>
                      <p className="text-sm mt-2 text-gray-300">{address.address}, {address.city}, {address.state}</p>
                    </div>
                    <div className="flex flex-col gap-2">
                      {!address.is_default && (
                        <button onClick={() => handleSetDefault(address.id)} className="text-xs px-3 py-1 rounded bg-[#2c77d1]/20 text-[#2c77d1]">Set default</button>
                      )}
                      <button onClick={() => handleDelete(address.id)} className="text-xs px-3 py-1 rounded bg-red-500/10 text-red-400">Delete</button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="bg-[#1a1a1a] rounded-2xl border border-[#2c77d1]/20 p-6 h-fit">
          <h2 className="text-xl font-semibold mb-4">Add New Address</h2>
          <form onSubmit={handleCreate} className="space-y-3">
            {Object.keys(INITIAL_FORM).map((key) => (
              <input
                key={key}
                required={key !== 'postal_code'}
                value={form[key]}
                onChange={(e) => setForm((prev) => ({ ...prev, [key]: e.target.value }))}
                placeholder={key.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                className="w-full bg-[#020617] border border-gray-700 rounded-lg px-3 py-2.5"
              />
            ))}
            <button type="submit" disabled={saving} className="w-full bg-[#2c77d1] hover:bg-[#256bbd] rounded-lg py-3 font-semibold disabled:opacity-70">
              {saving ? 'Saving...' : 'Save Address'}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
