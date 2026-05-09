import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, BarChart3, CheckCircle2, Gavel, Package, RefreshCw, ShoppingCart, ShieldCheck, TrendingUp, UserCheck, Users } from 'lucide-react';
import {
  applyDisputeTicketDecision,
  applyBulkRefundDecision,
  getAdminDisputeTickets,
  getAssistantReportsQueue,
  getCompanyAdminOperations,
  getDashboardAnalytics,
  getDashboardCustomers,
  getDashboardOrders,
  getDashboardProducts,
  getDashboardSales,
  getProductReportModerationQueue,
  getReviewFlagModerationQueue,
  getSellerApplications,
  getSystemHealth,
  moderateProductReport,
  moderateReviewFlag,
  updateAssistantReport,
  updateDashboardProduct,
  updateDashboardUser,
  updateSellerApplication,
} from '../services/api';

const TABS = ['overview', 'operations', 'customers', 'products', 'orders'];
const PAGE_SIZE = 25;
const MODERATION_STATUSES = ['pending', 'reviewing', 'resolved', 'dismissed'];
const REPORT_REASONS = ['spam', 'fake', 'inappropriate', 'misleading', 'duplicate', 'other'];
const FLAG_REASONS = ['spam', 'offensive', 'fake', 'irrelevant', 'personal_info', 'other'];
const ASSISTANT_REPORT_STATUSES = ['pending', 'reviewing', 'resolved', 'closed'];
const ASSISTANT_REPORT_TYPES = ['dispute', 'complaint', 'feedback', 'suggestion', 'bug', 'scam', 'other'];
const DISPUTE_STATUSES = ['OPEN', 'UNDER_REVIEW', 'ESCALATED', 'UNDER_SENIOR_REVIEW', 'RESOLVED_APPROVED', 'RESOLVED_DENIED', 'CLOSED'];
const SELLER_STATUSES = ['pending', 'approved', 'rejected'];

const normalizePaginated = (data) => {
  if (Array.isArray(data)) return { count: data.length, next: null, previous: null, results: data };

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
  const [loadingOperations, setLoadingOperations] = useState(false);
  const [operationBusy, setOperationBusy] = useState(false);
  const [error, setError] = useState('');
  const [operationError, setOperationError] = useState('');
  const [operationSuccess, setOperationSuccess] = useState('');
  const [analytics, setAnalytics] = useState({});
  const [sales, setSales] = useState({});
  const [systemHealth, setSystemHealth] = useState({ status: 'unknown', alerts: [] });
  const [opsQueues, setOpsQueues] = useState({});
  const [tabData, setTabData] = useState({
    customers: { page: 1, ...normalizePaginated(null) },
    products: { page: 1, ...normalizePaginated(null) },
    orders: { page: 1, ...normalizePaginated(null) },
  });
  const [operationsData, setOperationsData] = useState({
    productReports: { page: 1, status: 'pending', reason: '', ...normalizePaginated(null) },
    reviewFlags: { page: 1, status: 'pending', reason: '', ...normalizePaginated(null) },
    assistantReports: { page: 1, status: 'pending', report_type: '', ...normalizePaginated(null) },
    disputeTickets: { page: 1, status: 'OPEN', seller_type: '', ...normalizePaginated(null) },
    sellerApplications: { page: 1, status: 'pending', ...normalizePaginated(null) },
    refundIds: '',
    refundDecision: 'approve',
    refundNotes: '',
    reportNotes: '',
    flagNotes: '',
    assistantReportNotes: '',
    disputeDecision: '',
    disputeDecisionReason: '',
  });

  const loadOverview = useCallback(async () => {
    try {
      setLoadingOverview(true);
      setError('');

      const [analyticsData, salesData, healthData, opsData] = await Promise.all([
        getDashboardAnalytics(),
        getDashboardSales(),
        getSystemHealth().catch(() => ({ status: 'unhealthy', diagnostics: { alerts: [{ kind: 'health_endpoint_unavailable' }] } })),
        getCompanyAdminOperations().catch(() => ({})),
      ]);

      setAnalytics(analyticsData || {});
      setSales(salesData || {});
      setSystemHealth({
        status: healthData?.status || 'unknown',
        alerts: healthData?.diagnostics?.alerts || [],
      });
      setOpsQueues(opsData || {});
    } catch (apiError) {
      setError(apiError?.data?.detail || apiError?.data?.error || 'Failed to load dashboard data.');
    } finally {
      setLoadingOverview(false);
    }
  }, []);

  const loadTab = useCallback(async (tab, page = 1) => {
    if (!['customers', 'products', 'orders'].includes(tab)) return;

    const loaders = {
      customers: getDashboardCustomers,
      products: getDashboardProducts,
      orders: getDashboardOrders,
    };

    try {
      setLoadingTab(true);
      setError('');
      const data = await loaders[tab]({ page, pageSize: PAGE_SIZE });
      setTabData((prev) => ({ ...prev, [tab]: { ...normalizePaginated(data), page } }));
    } catch (apiError) {
      setError(apiError?.data?.detail || apiError?.data?.error || `Failed to load ${tab}.`);
    } finally {
      setLoadingTab(false);
    }
  }, []);

  const loadOperations = useCallback(async () => {
    try {
      setLoadingOperations(true);
      setOperationError('');

      const [reports, flags, assistantReports, disputeTickets, sellerApplications] = await Promise.all([
        getProductReportModerationQueue({
          page: operationsData.productReports.page,
          pageSize: PAGE_SIZE,
          status: operationsData.productReports.status,
          reason: operationsData.productReports.reason,
        }),
        getReviewFlagModerationQueue({
          page: operationsData.reviewFlags.page,
          pageSize: PAGE_SIZE,
          status: operationsData.reviewFlags.status,
          reason: operationsData.reviewFlags.reason,
        }),
        getAssistantReportsQueue({
          page: operationsData.assistantReports.page,
          pageSize: PAGE_SIZE,
          status: operationsData.assistantReports.status,
          report_type: operationsData.assistantReports.report_type,
        }),
        getAdminDisputeTickets({
          page: operationsData.disputeTickets.page,
          pageSize: PAGE_SIZE,
          status: operationsData.disputeTickets.status,
          seller_type: operationsData.disputeTickets.seller_type,
        }),
        getSellerApplications({
          page: operationsData.sellerApplications.page,
          pageSize: PAGE_SIZE,
          status: operationsData.sellerApplications.status,
        }),
      ]);

      setOperationsData((prev) => ({
        ...prev,
        productReports: { ...prev.productReports, ...normalizePaginated(reports) },
        reviewFlags: { ...prev.reviewFlags, ...normalizePaginated(flags) },
        assistantReports: { ...prev.assistantReports, ...normalizePaginated(assistantReports) },
        disputeTickets: { ...prev.disputeTickets, ...normalizePaginated(disputeTickets) },
        sellerApplications: { ...prev.sellerApplications, ...normalizePaginated(sellerApplications) },
      }));
    } catch (apiError) {
      setOperationError(apiError?.data?.detail || apiError?.data?.error || 'Failed to load operations queues.');
    } finally {
      setLoadingOperations(false);
    }
  }, [
    operationsData.assistantReports.page,
    operationsData.assistantReports.report_type,
    operationsData.assistantReports.status,
    operationsData.disputeTickets.page,
    operationsData.disputeTickets.seller_type,
    operationsData.disputeTickets.status,
    operationsData.productReports.page,
    operationsData.productReports.reason,
    operationsData.productReports.status,
    operationsData.reviewFlags.page,
    operationsData.reviewFlags.reason,
    operationsData.reviewFlags.status,
    operationsData.sellerApplications.page,
    operationsData.sellerApplications.status,
  ]);

  useEffect(() => {
    loadOverview();
  }, [loadOverview]);

  useEffect(() => {
    if (activeTab === 'operations') {
      loadOperations();
      return;
    }

    if (activeTab === 'overview') return;

    if ((tabData[activeTab]?.results || []).length === 0) {
      loadTab(activeTab, 1);
    }
  }, [activeTab, loadOperations, loadTab, tabData]);

  const refreshCurrentView = async () => {
    setOperationSuccess('');
    await loadOverview();
    if (activeTab === 'operations') {
      await loadOperations();
      return;
    }
    if (activeTab !== 'overview') {
      await loadTab(activeTab, tabData[activeTab]?.page || 1);
    }
  };

  const runReportAction = async (reportId, status) => {
    try {
      setOperationBusy(true);
      setOperationError('');
      await moderateProductReport(reportId, { status, admin_notes: operationsData.reportNotes });
      setOperationSuccess(`Product report updated to ${status}.`);
      await Promise.all([loadOverview(), loadOperations()]);
    } catch (apiError) {
      setOperationError(apiError?.data?.detail || apiError?.data?.error || 'Failed to update product report.');
    } finally {
      setOperationBusy(false);
    }
  };

  const runFlagAction = async (flagId, status) => {
    try {
      setOperationBusy(true);
      setOperationError('');
      await moderateReviewFlag(flagId, { status, admin_notes: operationsData.flagNotes });
      setOperationSuccess(`Review flag updated to ${status}.`);
      await Promise.all([loadOverview(), loadOperations()]);
    } catch (apiError) {
      setOperationError(apiError?.data?.detail || apiError?.data?.error || 'Failed to update review flag.');
    } finally {
      setOperationBusy(false);
    }
  };

  const runAssistantReportAction = async (reportId, status) => {
    try {
      setOperationBusy(true);
      setOperationError('');
      await updateAssistantReport(reportId, { status, admin_notes: operationsData.assistantReportNotes });
      setOperationSuccess(`Assistant report updated to ${status}.`);
      await Promise.all([loadOverview(), loadOperations()]);
    } catch (apiError) {
      setOperationError(apiError?.data?.detail || apiError?.data?.error || 'Failed to update assistant report.');
    } finally {
      setOperationBusy(false);
    }
  };

  const runDisputeTicketAction = async (ticketId, status) => {
    const fallbackDecision = status === 'RESOLVED_APPROVED'
      ? 'Resolved in favor of buyer'
      : status === 'RESOLVED_DENIED'
        ? 'Resolved in favor of seller'
        : `Moved to ${status.replace(/_/g, ' ').toLowerCase()}`;

    try {
      setOperationBusy(true);
      setOperationError('');
      await applyDisputeTicketDecision(ticketId, {
        status,
        admin_decision: operationsData.disputeDecision || fallbackDecision,
        admin_decision_reason: operationsData.disputeDecisionReason,
      });
      setOperationSuccess(`Dispute ticket moved to ${status}.`);
      await Promise.all([loadOverview(), loadOperations()]);
    } catch (apiError) {
      setOperationError(apiError?.data?.detail || apiError?.data?.error || 'Failed to update dispute ticket.');
    } finally {
      setOperationBusy(false);
    }
  };

  const runSellerDecision = async (profileId, status) => {
    try {
      setOperationBusy(true);
      setOperationError('');
      await updateSellerApplication(profileId, { status, is_verified_seller: status === 'approved' });
      setOperationSuccess(`Seller application updated to ${status}.`);
      await Promise.all([loadOverview(), loadOperations(), loadTab('customers', tabData.customers.page || 1)]);
    } catch (apiError) {
      setOperationError(apiError?.data?.detail || apiError?.data?.error || 'Failed to update seller application.');
    } finally {
      setOperationBusy(false);
    }
  };

  const runUserAction = async (userId, payload) => {
    try {
      setLoadingTab(true);
      setError('');
      await updateDashboardUser(userId, payload);
      await Promise.all([loadOverview(), loadTab('customers', tabData.customers.page || 1)]);
    } catch (apiError) {
      setError(apiError?.data?.detail || apiError?.data?.error || 'Failed to update user.');
    } finally {
      setLoadingTab(false);
    }
  };

  const runProductAction = async (productId, payload) => {
    try {
      setLoadingTab(true);
      setError('');
      await updateDashboardProduct(productId, payload);
      await Promise.all([loadOverview(), loadTab('products', tabData.products.page || 1)]);
    } catch (apiError) {
      setError(apiError?.data?.detail || apiError?.data?.error || 'Failed to update product.');
    } finally {
      setLoadingTab(false);
    }
  };

  const submitBulkRefundDecision = async () => {
    const refundIds = operationsData.refundIds.split(',').map((id) => id.trim()).filter(Boolean);
    if (refundIds.length === 0) {
      setOperationError('Enter at least one refund ID.');
      return;
    }

    try {
      setOperationBusy(true);
      setOperationError('');
      const result = await applyBulkRefundDecision({
        refund_ids: refundIds,
        decision: operationsData.refundDecision,
        admin_notes: operationsData.refundNotes,
      });
      setOperationSuccess(`Bulk refund decision applied. Updated: ${result.updated_count ?? 0}, skipped: ${(result.skipped || []).length}.`);
      await loadOverview();
    } catch (apiError) {
      setOperationError(apiError?.data?.detail || apiError?.data?.error || 'Failed to apply refund decision.');
    } finally {
      setOperationBusy(false);
    }
  };

  const statCards = useMemo(() => ([
    { label: 'Total Users', value: analytics.total_users ?? tabData.customers.count ?? 0, icon: Users },
    { label: 'Total Products', value: analytics.total_products ?? tabData.products.count ?? 0, icon: Package },
    { label: 'Total Orders', value: analytics.total_orders ?? tabData.orders.count ?? 0, icon: ShoppingCart },
    {
      label: 'Revenue',
      value: `NGN ${Number(sales.total_revenue || analytics.total_revenue || 0).toLocaleString()}`,
      icon: TrendingUp,
    },
  ]), [analytics, sales.total_revenue, tabData.customers.count, tabData.orders.count, tabData.products.count]);

  const currentTabState = tabData[activeTab];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8 flex flex-wrap justify-between gap-4 items-center">
          <div>
            <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">Admin Dashboard</h1>
            <p className="text-gray-600 dark:text-gray-400">Operational analytics and moderation center</p>
          </div>
          <button
            onClick={refreshCurrentView}
            disabled={loadingOverview || loadingTab || loadingOperations || operationBusy}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-60"
          >
            <RefreshCw className={`w-4 h-4 ${loadingOverview || loadingTab || loadingOperations || operationBusy ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {error && <p className="mb-4 text-red-500">{error}</p>}

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
          <div className="flex gap-4 flex-wrap">
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
              <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-white">Company Admin Operations</h2>
              <p className="text-gray-600 dark:text-gray-400">Product reports pending/reviewing: <span className="font-semibold text-gray-900 dark:text-white">{opsQueues?.product_reports?.pending ?? 0}/{opsQueues?.product_reports?.reviewing ?? 0}</span></p>
              <p className="text-gray-600 dark:text-gray-400">Review flags pending/reviewing: <span className="font-semibold text-gray-900 dark:text-white">{opsQueues?.review_flags?.pending ?? 0}/{opsQueues?.review_flags?.reviewing ?? 0}</span></p>
              <p className="text-gray-600 dark:text-gray-400">Assistant reports pending/reviewing: <span className="font-semibold text-gray-900 dark:text-white">{opsQueues?.assistant_reports?.pending ?? 0}/{opsQueues?.assistant_reports?.reviewing ?? 0}</span></p>
              <p className="text-gray-600 dark:text-gray-400">Disputes open/review/escalated: <span className="font-semibold text-gray-900 dark:text-white">{opsQueues?.dispute_tickets?.open ?? 0}/{opsQueues?.dispute_tickets?.under_review ?? 0}/{opsQueues?.dispute_tickets?.escalated ?? 0}</span></p>
              <p className="text-gray-600 dark:text-gray-400">Seller applications pending: <span className="font-semibold text-gray-900 dark:text-white">{opsQueues?.seller_applications?.pending ?? 0}</span></p>
              <p className="text-gray-600 dark:text-gray-400">Refunds pending/processing: <span className="font-semibold text-gray-900 dark:text-white">{opsQueues?.refunds?.pending ?? 0}/{opsQueues?.refunds?.processing ?? 0}</span></p>
              <p className="text-gray-600 dark:text-gray-400">Videos pending scan/quarantined: <span className="font-semibold text-gray-900 dark:text-white">{opsQueues?.product_videos?.pending_scan ?? 0}/{opsQueues?.product_videos?.quarantined ?? 0}</span></p>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
              <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-white">System Health</h2>
              <p className="text-gray-600 dark:text-gray-400">Platform status: <span className={`font-semibold ${systemHealth.status === 'healthy' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>{systemHealth.status}</span></p>
              <p className="text-gray-600 dark:text-gray-400">Active alerts: <span className="font-semibold text-gray-900 dark:text-white">{systemHealth.alerts.length}</span></p>
            </div>
          </div>
        )}

        {activeTab === 'operations' && (
          <OperationsPanel
            data={operationsData}
            loading={loadingOperations}
            busy={operationBusy}
            error={operationError}
            success={operationSuccess}
            onChange={setOperationsData}
            onModerateReport={runReportAction}
            onModerateFlag={runFlagAction}
            onModerateAssistantReport={runAssistantReportAction}
            onDisputeTicketAction={runDisputeTicketAction}
            onSellerDecision={runSellerDecision}
            onSubmitRefundDecision={submitBulkRefundDecision}
          />
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
            renderActions={(row) => (
              <div className="flex flex-wrap gap-2">
                {!row.is_verified && <SmallActionButton onClick={() => runUserAction(row.id, { action: 'verify_email' })}>Verify</SmallActionButton>}
                {row.is_suspended || !row.is_active ? (
                  <SmallActionButton onClick={() => runUserAction(row.id, { action: 'activate' })}>Activate</SmallActionButton>
                ) : (
                  <SmallActionButton onClick={() => runUserAction(row.id, { action: 'suspend', suspension_reason: 'Suspended from admin dashboard' })}>Suspend</SmallActionButton>
                )}
                {row.role !== 'admin' && <SmallActionButton onClick={() => runUserAction(row.id, { role: 'admin', is_staff: true })}>Make Admin</SmallActionButton>}
              </div>
            )}
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
            renderActions={(row) => (
              <div className="flex flex-wrap gap-2">
                {!row.is_verified_product && <SmallActionButton onClick={() => runProductAction(row.id, { is_verified: true, is_verified_product: true })}>Verify</SmallActionButton>}
                {!row.is_featured && <SmallActionButton onClick={() => runProductAction(row.id, { is_featured: true })}>Feature</SmallActionButton>}
                {row.status !== 'suspended' && <SmallActionButton onClick={() => runProductAction(row.id, { status: 'suspended' })}>Suspend</SmallActionButton>}
                {row.status !== 'sold' && <SmallActionButton onClick={() => runProductAction(row.id, { status: 'sold' })}>Sold</SmallActionButton>}
                {row.status !== 'active' && <SmallActionButton onClick={() => runProductAction(row.id, { status: 'active' })}>Activate</SmallActionButton>}
              </div>
            )}
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

function OperationsPanel({
  data,
  loading,
  busy,
  error,
  success,
  onChange,
  onModerateReport,
  onModerateFlag,
  onModerateAssistantReport,
  onDisputeTicketAction,
  onSellerDecision,
  onSubmitRefundDecision,
}) {
  return (
    <div className="space-y-6">
      {error && <p className="text-red-500">{error}</p>}
      {success && <p className="text-green-600 dark:text-green-400">{success}</p>}

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 space-y-4">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">Bulk Refund Decision</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">Enter pending refund IDs separated by commas.</p>
        <textarea
          value={data.refundIds}
          onChange={(e) => onChange((prev) => ({ ...prev, refundIds: e.target.value }))}
          className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm"
          rows={3}
          placeholder="id-1, id-2, id-3"
        />
        <div className="grid md:grid-cols-2 gap-3">
          <select
            value={data.refundDecision}
            onChange={(e) => onChange((prev) => ({ ...prev, refundDecision: e.target.value }))}
            className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm"
          >
            <option value="approve">Approve</option>
            <option value="reject">Reject</option>
          </select>
          <input
            value={data.refundNotes}
            onChange={(e) => onChange((prev) => ({ ...prev, refundNotes: e.target.value }))}
            className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm"
            placeholder="Admin notes (optional)"
          />
        </div>
        <button onClick={onSubmitRefundDecision} disabled={busy} className="px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50">Apply Decision</button>
      </div>

      <QueueCard
        title="Seller Applications"
        icon={UserCheck}
        loading={loading}
        rows={data.sellerApplications.results || []}
        page={data.sellerApplications.page}
        totalCount={data.sellerApplications.count}
        hasPrevious={Boolean(data.sellerApplications.previous)}
        hasNext={Boolean(data.sellerApplications.next)}
        status={data.sellerApplications.status}
        reason=""
        statuses={SELLER_STATUSES}
        reasons={[]}
        notesValue={null}
        onStatusChange={(value) => onChange((prev) => ({
          ...prev,
          sellerApplications: { ...prev.sellerApplications, page: 1, status: value },
        }))}
        onReasonChange={() => {}}
        onPrevPage={() => onChange((prev) => ({
          ...prev,
          sellerApplications: { ...prev.sellerApplications, page: Math.max(1, prev.sellerApplications.page - 1) },
        }))}
        onNextPage={() => onChange((prev) => ({
          ...prev,
          sellerApplications: { ...prev.sellerApplications, page: prev.sellerApplications.page + 1 },
        }))}
        onNotesChange={() => {}}
        busy={busy}
        actionButtons={[
          { label: 'Approve', status: 'approved' },
          { label: 'Reject', status: 'rejected' },
          { label: 'Pending', status: 'pending' },
        ]}
        onAction={(row, status) => onSellerDecision(row.id, status)}
        renderTitle={(row) => row.name || row.email || row.id}
        renderMeta={(row) => `Status: ${row.status || '-'} - Mode: ${row.seller_commerce_mode || '-'} - Reviews: ${row.total_reviews ?? 0}`}
      />

      <QueueCard
        title="Assistant Reports"
        icon={AlertTriangle}
        loading={loading}
        rows={data.assistantReports.results || []}
        page={data.assistantReports.page}
        totalCount={data.assistantReports.count}
        hasPrevious={Boolean(data.assistantReports.previous)}
        hasNext={Boolean(data.assistantReports.next)}
        status={data.assistantReports.status}
        reason={data.assistantReports.report_type}
        statuses={ASSISTANT_REPORT_STATUSES}
        reasons={ASSISTANT_REPORT_TYPES}
        filterLabel="all report types"
        notesValue={data.assistantReportNotes}
        onStatusChange={(value) => onChange((prev) => ({
          ...prev,
          assistantReports: { ...prev.assistantReports, page: 1, status: value },
        }))}
        onReasonChange={(value) => onChange((prev) => ({
          ...prev,
          assistantReports: { ...prev.assistantReports, page: 1, report_type: value },
        }))}
        onPrevPage={() => onChange((prev) => ({
          ...prev,
          assistantReports: { ...prev.assistantReports, page: Math.max(1, prev.assistantReports.page - 1) },
        }))}
        onNextPage={() => onChange((prev) => ({
          ...prev,
          assistantReports: { ...prev.assistantReports, page: prev.assistantReports.page + 1 },
        }))}
        onNotesChange={(value) => onChange((prev) => ({ ...prev, assistantReportNotes: value }))}
        busy={busy}
        actionButtons={[
          { label: 'Reviewing', status: 'reviewing' },
          { label: 'Resolved', status: 'resolved' },
          { label: 'Closed', status: 'closed' },
        ]}
        onAction={(row, status) => onModerateAssistantReport(row.id, status)}
        renderTitle={(row) => `${row.report_type || 'report'} #${row.id}`}
        renderMeta={(row) => `Severity: ${row.severity || '-'} - Status: ${row.status || '-'} - User: ${row.user_email || row.user_username || '-'}`}
        renderBody={(row) => row.message}
      />

      <QueueCard
        title="Dispute Tickets"
        icon={Gavel}
        loading={loading}
        rows={data.disputeTickets.results || []}
        page={data.disputeTickets.page}
        totalCount={data.disputeTickets.count}
        hasPrevious={Boolean(data.disputeTickets.previous)}
        hasNext={Boolean(data.disputeTickets.next)}
        status={data.disputeTickets.status}
        reason={data.disputeTickets.seller_type}
        statuses={DISPUTE_STATUSES}
        reasons={['verified', 'unverified']}
        filterLabel="all seller types"
        notesValue={data.disputeDecisionReason}
        onStatusChange={(value) => onChange((prev) => ({
          ...prev,
          disputeTickets: { ...prev.disputeTickets, page: 1, status: value },
        }))}
        onReasonChange={(value) => onChange((prev) => ({
          ...prev,
          disputeTickets: { ...prev.disputeTickets, page: 1, seller_type: value },
        }))}
        onPrevPage={() => onChange((prev) => ({
          ...prev,
          disputeTickets: { ...prev.disputeTickets, page: Math.max(1, prev.disputeTickets.page - 1) },
        }))}
        onNextPage={() => onChange((prev) => ({
          ...prev,
          disputeTickets: { ...prev.disputeTickets, page: prev.disputeTickets.page + 1 },
        }))}
        onNotesChange={(value) => onChange((prev) => ({ ...prev, disputeDecisionReason: value }))}
        busy={busy}
        actionButtons={[
          { label: 'Reviewing', status: 'UNDER_REVIEW' },
          { label: 'Escalate', status: 'ESCALATED' },
          { label: 'Senior Review', status: 'UNDER_SENIOR_REVIEW' },
          { label: 'Approve', status: 'RESOLVED_APPROVED' },
          { label: 'Deny', status: 'RESOLVED_DENIED' },
          { label: 'Close', status: 'CLOSED' },
        ]}
        onAction={(row, status) => onDisputeTicketAction(row.ticket_id, status)}
        renderTitle={(row) => `${row.ticket_id} - ${row.dispute_category || 'dispute'}`}
        renderMeta={(row) => `Status: ${row.status || '-'} - Buyer: ${row.buyer_email || '-'} - Seller: ${row.seller_email || '-'} - Product: ${row.product_title || '-'}`}
        renderBody={(row) => row.description}
      />

      <QueueCard
        title="Product Reports"
        icon={ShieldCheck}
        loading={loading}
        rows={data.productReports.results || []}
        page={data.productReports.page}
        totalCount={data.productReports.count}
        hasPrevious={Boolean(data.productReports.previous)}
        hasNext={Boolean(data.productReports.next)}
        status={data.productReports.status}
        reason={data.productReports.reason}
        statuses={MODERATION_STATUSES}
        reasons={REPORT_REASONS}
        notesValue={data.reportNotes}
        onStatusChange={(value) => onChange((prev) => ({
          ...prev,
          productReports: { ...prev.productReports, page: 1, status: value },
        }))}
        onReasonChange={(value) => onChange((prev) => ({
          ...prev,
          productReports: { ...prev.productReports, page: 1, reason: value },
        }))}
        onPrevPage={() => onChange((prev) => ({
          ...prev,
          productReports: { ...prev.productReports, page: Math.max(1, prev.productReports.page - 1) },
        }))}
        onNextPage={() => onChange((prev) => ({
          ...prev,
          productReports: { ...prev.productReports, page: prev.productReports.page + 1 },
        }))}
        onNotesChange={(value) => onChange((prev) => ({ ...prev, reportNotes: value }))}
        busy={busy}
        actionButtons={[
          { label: 'Reviewing', status: 'reviewing' },
          { label: 'Resolved', status: 'resolved' },
          { label: 'Dismissed', status: 'dismissed' },
        ]}
        onAction={(row, status) => onModerateReport(row.id, status)}
        renderTitle={(row) => row.product_title || row.id}
        renderMeta={(row) => `Reason: ${row.reason || '-'} - Status: ${row.status || '-'} - Reporter: ${row.reporter_name || '-'}`}
      />

      <QueueCard
        title="Review Flags"
        icon={CheckCircle2}
        loading={loading}
        rows={data.reviewFlags.results || []}
        page={data.reviewFlags.page}
        totalCount={data.reviewFlags.count}
        hasPrevious={Boolean(data.reviewFlags.previous)}
        hasNext={Boolean(data.reviewFlags.next)}
        status={data.reviewFlags.status}
        reason={data.reviewFlags.reason}
        statuses={MODERATION_STATUSES}
        reasons={FLAG_REASONS}
        notesValue={data.flagNotes}
        onStatusChange={(value) => onChange((prev) => ({
          ...prev,
          reviewFlags: { ...prev.reviewFlags, page: 1, status: value },
        }))}
        onReasonChange={(value) => onChange((prev) => ({
          ...prev,
          reviewFlags: { ...prev.reviewFlags, page: 1, reason: value },
        }))}
        onPrevPage={() => onChange((prev) => ({
          ...prev,
          reviewFlags: { ...prev.reviewFlags, page: Math.max(1, prev.reviewFlags.page - 1) },
        }))}
        onNextPage={() => onChange((prev) => ({
          ...prev,
          reviewFlags: { ...prev.reviewFlags, page: prev.reviewFlags.page + 1 },
        }))}
        onNotesChange={(value) => onChange((prev) => ({ ...prev, flagNotes: value }))}
        busy={busy}
        actionButtons={[
          { label: 'Reviewing', status: 'reviewing' },
          { label: 'Resolved', status: 'resolved' },
          { label: 'Dismissed', status: 'dismissed' },
        ]}
        onAction={(row, status) => onModerateFlag(row.id, status)}
        renderTitle={(row) => row.id}
        renderMeta={(row) => `Reason: ${row.reason || '-'} - Status: ${row.status || '-'} - Flagger: ${row.flagger_name || '-'}`}
      />
    </div>
  );
}

function QueueCard({
  title,
  icon: Icon,
  loading,
  rows,
  page,
  totalCount,
  hasPrevious,
  hasNext,
  status,
  reason,
  statuses,
  reasons,
  filterLabel = 'all reasons',
  notesValue,
  onStatusChange,
  onReasonChange,
  onPrevPage,
  onNextPage,
  onNotesChange,
  actionButtons,
  onAction,
  renderTitle,
  renderMeta,
  renderBody,
  busy,
}) {
  const start = totalCount === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const end = Math.min(page * PAGE_SIZE, totalCount);
  const hasReasonFilter = Array.isArray(reasons) && reasons.length > 0;
  const hasNotes = typeof notesValue === 'string';

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
          {Icon && <Icon className="w-5 h-5 text-blue-600 dark:text-blue-400" />}
          {title}
        </h3>
        <span className="text-sm text-gray-500 dark:text-gray-400">{start}-{end} of {totalCount}</span>
      </div>

      <div className={`grid ${hasReasonFilter ? 'md:grid-cols-2' : 'md:grid-cols-1'} gap-3 mb-3`}>
        <select value={status} onChange={(e) => onStatusChange(e.target.value)} className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm">
          {statuses.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        {hasReasonFilter && (
          <select value={reason} onChange={(e) => onReasonChange(e.target.value)} className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm">
            <option value="">{filterLabel}</option>
            {reasons.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        )}
      </div>

      {hasNotes && (
        <input value={notesValue} onChange={(e) => onNotesChange(e.target.value)} className="w-full mb-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm" placeholder="Notes for actions (optional)" />
      )}

      {loading ? (
        <p className="text-sm text-gray-500">Loading queue...</p>
      ) : rows.length === 0 ? (
        <p className="text-sm text-gray-500">No queued records.</p>
      ) : (
        <div className="space-y-3">
          {rows.map((row) => (
            <div key={row.id} className="rounded-lg border border-gray-200 dark:border-gray-700 p-3">
              <p className="text-sm font-semibold text-gray-900 dark:text-white">{renderTitle(row)}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">{renderMeta(row)}</p>
              {renderBody && row && (
                <p className="text-xs text-gray-600 dark:text-gray-300 mb-2 line-clamp-2">{renderBody(row) || ''}</p>
              )}
              <div className="flex flex-wrap gap-2">
                {actionButtons.map((action) => (
                  <button key={action.status} onClick={() => onAction(row, action.status)} disabled={busy} className="px-3 py-1 text-xs rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50">
                    {action.label}
                  </button>
                ))}
              </div>
            </div>
          ))}

          <div className="flex items-center justify-end gap-2 pt-1">
            <button onClick={onPrevPage} disabled={!hasPrevious} className="px-3 py-1 text-xs rounded border border-gray-300 dark:border-gray-600 disabled:opacity-50">Prev</button>
            <span className="text-xs text-gray-500 dark:text-gray-400">Page {page}</span>
            <button onClick={onNextPage} disabled={!hasNext} className="px-3 py-1 text-xs rounded border border-gray-300 dark:border-gray-600 disabled:opacity-50">Next</button>
          </div>
        </div>
      )}
    </div>
  );
}

function SmallActionButton({ children, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="px-3 py-1 text-xs rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700"
    >
      {children}
    </button>
  );
}

function ListTable({ title, rows, columns, loading, page, totalCount, hasPrevious, hasNext, onChangePage, renderActions = null }) {
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
                {renderActions && (
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900 dark:text-white">
                    Actions
                  </th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {rows.map((row, idx) => (
                <tr key={row.id || row.order_number || idx} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  {columns.map((col) => (
                    <td key={col} className="px-6 py-4 text-sm text-gray-700 dark:text-gray-300">{String(row[col] ?? '-')}</td>
                  ))}
                  {renderActions && (
                    <td className="px-6 py-4 text-sm text-gray-700 dark:text-gray-300">
                      {renderActions(row)}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex items-center justify-between px-6 py-3 border-t border-gray-200 dark:border-gray-700 text-sm text-gray-600 dark:text-gray-300">
            <span>Showing {start}-{end} of {totalCount}</span>
            <div className="flex items-center gap-2">
              <button onClick={() => onChangePage(page - 1)} disabled={!hasPrevious} className="px-3 py-1 rounded border border-gray-300 dark:border-gray-600 disabled:opacity-50">Prev</button>
              <span>Page {page}</span>
              <button onClick={() => onChangePage(page + 1)} disabled={!hasNext} className="px-3 py-1 rounded border border-gray-300 dark:border-gray-600 disabled:opacity-50">Next</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
