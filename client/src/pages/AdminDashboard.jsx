import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { BarChart3, Users, Package, ShoppingCart, TrendingUp, RefreshCw } from 'lucide-react';
import {
  getDashboardAnalytics,
  getDashboardCustomers,
  getDashboardOrders,
  getDashboardProducts,
  getDashboardSales,
} from '../services/api';

const TABS = ['overview', 'customers', 'products', 'orders'];
const PAGE_SIZE = 25;

const normalizePaginated = (data) => {
  if (Array.isArray(data)) {
    return { count: data.length, next: null, previous: null, results: data };
  }

  if (data && Array.isArray(data.results)) {
    return {
      count: Number(data.count ?? data.results.length),
      next: data.next ?? null,
      previous: data.previous ?? null,
      results: data.results,
    };
  }

  return { count: 0, next: null, previous: null, results: [] };
};

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('overview');
  const [loadingOverview, setLoadingOverview] = useState(true);
  const [loadingTab, setLoadingTab] = useState(false);
  const [error, setError] = useState('');
  const [analytics, setAnalytics] = useState({});
  const [sales, setSales] = useState({});
  const [tabData, setTabData] = useState({
    customers: { page: 1, ...normalizePaginated(null) },
    products: { page: 1, ...normalizePaginated(null) },
    orders: { page: 1, ...normalizePaginated(null) },
  });

  const loadOverview = useCallback(async () => {
    try {
      setLoadingOverview(true);
      setError('');
      const [analyticsData, salesData] = await Promise.all([
        getDashboardAnalytics(),
        getDashboardSales(),
      ]);

      setAnalytics(analyticsData || {});
      setSales(salesData || {});
    } catch (apiError) {
      setError(apiError?.data?.detail || apiError?.data?.error || 'Failed to load dashboard data.');
    } finally {
      setLoadingOverview(false);
    }
  }, []);

  const loadTab = useCallback(async (tab, page = 1) => {
    if (!['customers', 'products', 'orders'].includes(tab)) {
      return;
    }

    const loaders = {
      customers: getDashboardCustomers,
      products: getDashboardProducts,
      orders: getDashboardOrders,
    };

    try {
      setLoadingTab(true);
      setError('');
      const data = await loaders[tab]({ page, pageSize: PAGE_SIZE });
      const normalized = normalizePaginated(data);

      setTabData((prev) => ({
        ...prev,
        [tab]: {
          ...normalized,
          page,
        },
      }));
    } catch (apiError) {
      setError(apiError?.data?.detail || apiError?.data?.error || `Failed to load ${tab}.`);
    } finally {
      setLoadingTab(false);
    }
  }, []);

  const refreshCurrentView = async () => {
    await loadOverview();
    if (activeTab !== 'overview') {
      const currentPage = tabData[activeTab]?.page || 1;
      await loadTab(activeTab, currentPage);
    }
  };

  useEffect(() => {
    loadOverview();
  }, [loadOverview]);

  useEffect(() => {
    if (activeTab === 'overview') {
      return;
    }

    if ((tabData[activeTab]?.results || []).length === 0) {
      loadTab(activeTab, 1);
    }
  }, [activeTab, loadTab, tabData]);

  const statCards = useMemo(
    () => [
      { label: 'Total Users', value: analytics.total_users ?? tabData.customers.count ?? 0, icon: Users },
      { label: 'Total Products', value: analytics.total_products ?? tabData.products.count ?? 0, icon: Package },
      { label: 'Total Orders', value: analytics.total_orders ?? tabData.orders.count ?? 0, icon: ShoppingCart },
      {
        label: 'Revenue',
        value: `₦${Number(sales.total_revenue || analytics.total_revenue || 0).toLocaleString()}`,
        icon: TrendingUp,
      },
    ],
    [analytics, sales.total_revenue, tabData.customers.count, tabData.orders.count, tabData.products.count],
  );

  const currentTabState = tabData[activeTab];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8 flex flex-wrap justify-between gap-4 items-center">
          <div>
            <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">Admin Dashboard</h1>
            <p className="text-gray-600 dark:text-gray-400">Operational analytics and moderation center</p>
          </div>
          <button onClick={refreshCurrentView} disabled={loadingOverview || loadingTab} className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-60">
            <RefreshCw className={`w-4 h-4 ${loadingOverview || loadingTab ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>

        {error && <p className="mb-4 text-red-400">{error}</p>}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {statCards.map((stat) => {
            const Icon = stat.icon;
            return (
              <div key={stat.label} className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
                <div className="flex justify-between items-start mb-4">
                  <Icon className="w-8 h-8 text-blue-600 dark:text-blue-400" />
                </div>
                <p className="text-gray-600 dark:text-gray-400 text-sm mb-1">{stat.label}</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stat.value}</p>
              </div>
            );
          })}
        </div>

        <div className="mb-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex gap-4">
            {TABS.map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-3 font-semibold transition-colors ${activeTab === tab ? 'border-b-2 border-blue-600 text-blue-600 dark:text-blue-400' : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'}`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {activeTab === 'overview' && (
          <div className="grid lg:grid-cols-2 gap-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
              <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-white flex items-center gap-2">
                <BarChart3 className="w-5 h-5" /> Sales Overview
              </h2>
              <p className="text-gray-600 dark:text-gray-400">Paid Orders: <span className="font-semibold text-gray-900 dark:text-white">{sales.paid_orders ?? '-'}</span></p>
              <p className="text-gray-600 dark:text-gray-400">Pending Orders: <span className="font-semibold text-gray-900 dark:text-white">{sales.pending_orders ?? '-'}</span></p>
              <p className="text-gray-600 dark:text-gray-400">Conversion Rate: <span className="font-semibold text-gray-900 dark:text-white">{sales.conversion_rate ?? '-'}%</span></p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
              <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-white">System Health</h2>
              <p className="text-gray-600 dark:text-gray-400">Known customers: {tabData.customers.count}</p>
              <p className="text-gray-600 dark:text-gray-400">Known products: {tabData.products.count}</p>
              <p className="text-gray-600 dark:text-gray-400">Known orders: {tabData.orders.count}</p>
            </div>
          </div>
        )}

        {activeTab === 'customers' && (
          <ListTable
            title="Customers"
            rows={currentTabState?.results || []}
            columns={['name', 'email', 'role']}
            loading={loadingTab}
            page={currentTabState?.page || 1}
            totalCount={currentTabState?.count || 0}
            hasPrevious={Boolean(currentTabState?.previous)}
            hasNext={Boolean(currentTabState?.next)}
            onChangePage={(nextPage) => loadTab('customers', nextPage)}
          />
        )}
        {activeTab === 'products' && (
          <ListTable
            title="Products"
            rows={currentTabState?.results || []}
            columns={['name', 'seller', 'price', 'status']}
            loading={loadingTab}
            page={currentTabState?.page || 1}
            totalCount={currentTabState?.count || 0}
            hasPrevious={Boolean(currentTabState?.previous)}
            hasNext={Boolean(currentTabState?.next)}
            onChangePage={(nextPage) => loadTab('products', nextPage)}
          />
        )}
        {activeTab === 'orders' && (
          <ListTable
            title="Orders"
            rows={currentTabState?.results || []}
            columns={['order_number', 'customer', 'total_amount', 'status']}
            loading={loadingTab}
            page={currentTabState?.page || 1}
            totalCount={currentTabState?.count || 0}
            hasPrevious={Boolean(currentTabState?.previous)}
            hasNext={Boolean(currentTabState?.next)}
            onChangePage={(nextPage) => loadTab('orders', nextPage)}
          />
        )}
      </div>
    </div>
  );
}

function ListTable({ title, rows, columns, loading, page, totalCount, hasPrevious, hasNext, onChangePage }) {
  const start = totalCount === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const end = Math.min(page * PAGE_SIZE, totalCount);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">{title}</h2>
      </div>
      {loading ? (
        <div className="p-6 text-gray-500">Loading...</div>
      ) : rows.length === 0 ? (
        <div className="p-6 text-gray-500">No data available.</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                {columns.map((col) => (
                  <th key={col} className="px-6 py-3 text-left text-sm font-semibold text-gray-900 dark:text-white">
                    {col.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {rows.map((row, idx) => (
                <tr key={row.id || row.order_number || idx} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  {columns.map((col) => (
                    <td key={col} className="px-6 py-4 text-sm text-gray-700 dark:text-gray-300">{String(row[col] ?? '-')}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex items-center justify-between px-6 py-3 border-t border-gray-200 dark:border-gray-700 text-sm text-gray-600 dark:text-gray-300">
            <span>
              Showing {start}-{end} of {totalCount}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => onChangePage(page - 1)}
                disabled={!hasPrevious}
                className="px-3 py-1 rounded border border-gray-300 dark:border-gray-600 disabled:opacity-50"
              >
                Prev
              </button>
              <span>Page {page}</span>
              <button
                onClick={() => onChangePage(page + 1)}
                disabled={!hasNext}
                className="px-3 py-1 rounded border border-gray-300 dark:border-gray-600 disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
