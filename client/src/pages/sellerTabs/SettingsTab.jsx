import React from 'react';

export default function SettingsTab({
  storeSettings,
  setStoreSettings,
  handleStoreSettingsSave,
  savingSettings,
}) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-950 dark:text-white">Settings</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">Manage seller profile, business, and payout readiness.</p>
      </div>

      <form onSubmit={handleStoreSettingsSave} className="space-y-5 rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-950">
        <label className="flex items-center justify-between gap-4 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <span>
            <span className="block font-semibold text-gray-900 dark:text-white">Seller commerce mode</span>
            <span className="block text-sm text-gray-500 dark:text-gray-400">Enable seller-focused controls across buyer and profile experiences.</span>
          </span>
          <input
            type="checkbox"
            checked={storeSettings.seller_commerce_mode}
            onChange={(event) => setStoreSettings((current) => ({ ...current, seller_commerce_mode: event.target.checked }))}
            className="w-5 h-5"
          />
        </label>

        <div>
          <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">Store bio</label>
          <textarea
            rows="4"
            value={storeSettings.bio}
            onChange={(event) => setStoreSettings((current) => ({ ...current, bio: event.target.value }))}
            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            placeholder="Tell buyers about your store, quality, and response times."
          />
        </div>

        <button
          type="submit"
          disabled={savingSettings}
          className="bg-green-600 hover:bg-green-700 disabled:opacity-70 text-white font-semibold px-6 py-2 rounded-lg transition-colors"
        >
          {savingSettings ? 'Saving...' : 'Save Seller Settings'}
        </button>
      </form>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-950">
          <h3 className="text-lg font-bold text-gray-950 dark:text-white">Business Information</h3>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <input className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900" placeholder="Registered business name" />
            <input className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900" placeholder="Business phone" />
            <input className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900" placeholder="Business address" />
            <input className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900" placeholder="Primary category" />
          </div>
        </section>

        <section className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-950">
          <h3 className="text-lg font-bold text-gray-950 dark:text-white">Payout Details</h3>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Bank settlement fields are ready for onboarding once managed payouts are enabled.</p>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <input className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900" placeholder="Bank name" disabled />
            <input className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900" placeholder="Account number" disabled />
          </div>
        </section>
      </div>
    </div>
  );
}
