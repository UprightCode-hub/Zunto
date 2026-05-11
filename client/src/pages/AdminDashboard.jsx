import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2, Gavel, Package, RefreshCw, Search, ShieldCheck, Store, Users, XCircle } from 'lucide-react';
import {
  getAdminDisputeCases,
  getCompanyAdminOperations,
  getDashboardAnalytics,
  getDashboardCustomers,
  getDashboardProducts,
  getSellerApplications,
  updateDashboardProduct,
  updateSellerApplication,
} from '../services/api';

const PAGE_SIZE = 50;
const ADMIN_TABS = [
  { key: 'sellerApplications', label: 'Seller Applications', icon: Store },
  { key: 'users', label: 'User Management', icon: Users },
  { key: 'products', label: 'Product Moderation', icon: Package },
  { key: 'disputes', label: 'Dispute Cases', icon: Gavel },
];

const normalizePaginated = (data) => {
  if (Array.isArray(data)) return { count: data.length, results: data };
  return {
    count: Number(data?.count ?? data?.results?.length ?? 0),
    results: Array.isArray(data?.results) ? data.results : [],
  };
};

const statusBadge = (status = '') => {
  const normalized = String(status).toLowerCase();
  if (['approved', 'resolved', 'active', 'verified'].includes(normalized)) return 'bg-emerald-100 text-emerald-700';
  if (['pending', 'open', 'draft'].includes(normalized)) return 'bg-amber-100 text-amber-700';
  if (['rejected', 'suspended', 'removed'].includes(normalized)) return 'bg-red-100 text-red-700';
  return 'bg-slate-100 text-slate-700';
};

const dateText = (value) => {
  if (!value) return '-';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '-' : date.toLocaleDateString();
};

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('sellerApplications');
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [analytics, setAnalytics] = useState({});
  const [ops, setOps] = useState({});
  const [sellerApplications, setSellerApplications] = useState({ count: 0, results: [] });
  const [users, setUsers] = useState({ count: 0, results: [] });
  const [products, setProducts] = useState({ count: 0, results: [] });
  const [disputeCases, setDisputeCases] = useState({ count: 0, results: [] });
  const [userRole, setUserRole] = useState('buyer');
  const [userSearch, setUserSearch] = useState('');

  const loadAll = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const [analyticsData, opsData, sellerData, productData, disputeData] = await Promise.all([
        getDashboardAnalytics(),
        getCompanyAdminOperations(),
        getSellerApplications({ status: 'pending', pageSize: PAGE_SIZE }),
        getDashboardProducts({ pageSize: PAGE_SIZE }),
        getAdminDisputeCases({ status: 'open', pageSize: PAGE_SIZE }),
      ]);
      setAnalytics(analyticsData || {});
      setOps(opsData || {});
      setSellerApplications(normalizePaginated(sellerData));
      setProducts(normalizePaginated(productData));
      setDisputeCases(normalizePaginated(disputeData));
    } catch (apiError) {
      setError(apiError?.data?.detail || apiError?.data?.error || apiError?.message || 'Failed to load admin portal data.');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadUsers = useCallback(async () => {
    try {
      const data = await getDashboardCustomers({
        role: userRole,
        search: userSearch,
        pageSize: PAGE_SIZE,
      });
      setUsers(normalizePaginated(data));
    } catch (apiError) {
      setError(apiError?.data?.detail || apiError?.data?.error || 'Failed to load users.');
    }
  }, [userRole, userSearch]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const summaryCards = useMemo(() => ([
    { label: 'Pending Seller Applications', value: ops?.seller_applications?.pending ?? sellerApplications.count, icon: Store },
    { label: 'Buyers', value: analytics?.users_by_role?.buyer ?? 0, icon: Users },
    { label: 'Sellers', value: analytics?.users_by_role?.seller ?? 0, icon: ShieldCheck },
    { label: 'Open Dispute Cases', value: ops?.dispute_cases?.open ?? disputeCases.count, icon: AlertTriangle },
  ]), [analytics, disputeCases.count, ops, sellerApplications.count]);

  const decideSellerApplication = async (applicationId, status) => {
    try {
      setBusyId(applicationId);
      setSuccess('');
      await updateSellerApplication(applicationId, { status, is_verified_seller: status === 'approved' });
      setSellerApplications((current) => ({
        ...current,
        count: Math.max(0, current.count - 1),
        results: current.results.filter((item) => item.id !== applicationId),
      }));
      setSuccess(`Seller application ${status}.`);
      await Promise.all([loadAll(), loadUsers()]);
    } catch (apiError) {
      setError(apiError?.data?.detail || apiError?.data?.error || `Failed to ${status} seller application.`);
    } finally {
      setBusyId('');
    }
  };

  const moderateProduct = async (productId, payload, message) => {
    try {
      setBusyId(productId);
      setSuccess('');
      const updated = await updateDashboardProduct(productId, payload);
      setProducts((current) => ({
        ...current,
        results: current.results.map((item) => (item.id === productId ? { ...item, ...updated } : item)),
      }));
      setSuccess(message);
    } catch (apiError) {
      setError(apiError?.data?.detail || apiError?.data?.error || 'Failed to update product.');
    } finally {
      setBusyId('');
    }
  };

  return (
    <div className="min-h-screen bg-[#f3f6fb] text-slate-950">
      <header className="border-b border-slate-200 bg-[#101827] text-white">
        <div className="mx-auto flex max-w-[1500px] flex-wrap items-center justify-between gap-4 px-6 py-5">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-200">Zunto Admin</p>
            <h1 className="mt-1 text-2xl font-bold">Management Portal</h1>
          </div>
          <button
            type="button"
            onClick={loadAll}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg border border-white/15 px-4 py-2 text-sm font-semibold hover:bg-white/10 disabled:opacity-60"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1500px] gap-6 px-6 py-6 lg:grid-cols-[260px_minmax(0,1fr)]">
        <aside className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
          <nav className="space-y-1">
            {ADMIN_TABS.map((tab) => {
              const Icon = tab.icon;
              const active = activeTab === tab.key;
              return (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => setActiveTab(tab.key)}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-semibold ${active ? 'bg-[#101827] text-white' : 'text-slate-700 hover:bg-slate-100'}`}
                >
                  <Icon className="h-4 w-4" />
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </aside>

        <main className="min-w-0 space-y-6">
          {error && <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">{error}</p>}
          {success && <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-700">{success}</p>}

          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {summaryCards.map((card) => {
              const Icon = card.icon;
              return (
                <div key={card.label} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
                  <Icon className="h-5 w-5 text-blue-700" />
                  <p className="mt-4 text-sm font-medium text-slate-500">{card.label}</p>
                  <p className="mt-1 text-3xl font-bold">{card.value}</p>
                </div>
              );
            })}
          </section>

          {activeTab === 'sellerApplications' && (
            <Panel title="Seller Application Approval Queue" subtitle="Pending applications ready for admin decision.">
              <DataTable
                columns={['Applicant', 'Business', 'Type', 'Category', 'Location', 'Date Applied', 'Actions']}
                emptyText={loading ? 'Loading seller applications...' : 'No pending seller applications.'}
                rows={sellerApplications.results}
                renderRow={(row) => (
                  <tr key={row.id} className="border-t border-slate-100">
                    <td className="px-4 py-3">
                      <p className="font-semibold">{row.name || row.email}</p>
                      <p className="text-xs text-slate-500">{row.email}</p>
                    </td>
                    <td className="px-4 py-3">{row.business_name}</td>
                    <td className="px-4 py-3 capitalize">{String(row.business_type || '').replace(/_/g, ' ')}</td>
                    <td className="px-4 py-3">{row.category || '-'}</td>
                    <td className="px-4 py-3">{row.location || '-'}</td>
                    <td className="px-4 py-3">{dateText(row.created_at)}</td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <ActionButton disabled={busyId === row.id} onClick={() => decideSellerApplication(row.id, 'approved')} tone="approve">
                          <CheckCircle2 className="h-4 w-4" /> Approve
                        </ActionButton>
                        <ActionButton disabled={busyId === row.id} onClick={() => decideSellerApplication(row.id, 'rejected')} tone="reject">
                          <XCircle className="h-4 w-4" /> Reject
                        </ActionButton>
                      </div>
                    </td>
                  </tr>
                )}
              />
            </Panel>
          )}

          {activeTab === 'users' && (
            <Panel title="User Management" subtitle="Buyers and sellers are separated for faster review.">
              <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-1">
                  {['buyer', 'seller'].map((role) => (
                    <button
                      key={role}
                      type="button"
                      onClick={() => setUserRole(role)}
                      className={`rounded-md px-4 py-2 text-sm font-semibold capitalize ${userRole === role ? 'bg-white text-blue-700 shadow-sm' : 'text-slate-600'}`}
                    >
                      {role}s ({analytics?.users_by_role?.[role] ?? 0})
                    </button>
                  ))}
                </div>
                <div className="relative">
                  <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                  <input
                    value={userSearch}
                    onChange={(event) => setUserSearch(event.target.value)}
                    placeholder="Search name or email"
                    className="h-10 rounded-lg border border-slate-200 bg-white pl-9 pr-3 text-sm outline-none focus:border-blue-600"
                  />
                </div>
              </div>
              <DataTable
                columns={['Name', 'Email', 'Role', 'Joined', 'Verification']}
                emptyText="No users found."
                rows={users.results}
                renderRow={(row) => (
                  <tr key={row.id} className="border-t border-slate-100">
                    <td className="px-4 py-3 font-semibold">{row.name || '-'}</td>
                    <td className="px-4 py-3">{row.email}</td>
                    <td className="px-4 py-3"><Badge value={row.role} /></td>
                    <td className="px-4 py-3">{dateText(row.created_at)}</td>
                    <td className="px-4 py-3">{row.is_verified ? 'Email verified' : 'Unverified'}</td>
                  </tr>
                )}
              />
            </Panel>
          )}

          {activeTab === 'products' && (
            <Panel title="Product Moderation" subtitle="Recently listed products with fast moderation controls.">
              <DataTable
                columns={['Product', 'Seller', 'Price', 'Category', 'Date Listed', 'Status', 'Actions']}
                emptyText={loading ? 'Loading products...' : 'No products found.'}
                rows={products.results}
                renderRow={(row) => (
                  <tr key={row.id} className="border-t border-slate-100">
                    <td className="px-4 py-3 font-semibold">{row.name || row.title}</td>
                    <td className="px-4 py-3">
                      <p>{row.seller || '-'}</p>
                      <p className="text-xs text-slate-500">{row.seller_email || ''}</p>
                    </td>
                    <td className="px-4 py-3">NGN {Number(row.price || 0).toLocaleString()}</td>
                    <td className="px-4 py-3">{row.category || '-'}</td>
                    <td className="px-4 py-3">{dateText(row.created_at)}</td>
                    <td className="px-4 py-3"><Badge value={row.status} /></td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <ActionButton disabled={busyId === row.id} onClick={() => moderateProduct(row.id, { status: 'suspended' }, 'Product removed from marketplace.')} tone="reject">
                          Remove
                        </ActionButton>
                        <ActionButton disabled={busyId === row.id} onClick={() => moderateProduct(row.id, { attributes_verified: false, is_featured: false, is_boosted: false }, 'Product flagged for review.')} tone="neutral">
                          Flag
                        </ActionButton>
                      </div>
                    </td>
                  </tr>
                )}
              />
            </Panel>
          )}

          {activeTab === 'disputes' && (
            <Panel title="Dispute Cases" subtitle="Structured AI escalations waiting for human review.">
              <DataTable
                columns={['Case', 'Category', 'Buyer', 'Seller', 'Reference', 'Status', 'Case File']}
                emptyText={loading ? 'Loading dispute cases...' : 'No open dispute cases.'}
                rows={disputeCases.results}
                renderRow={(row) => (
                  <tr key={row.id} className="border-t border-slate-100">
                    <td className="px-4 py-3 font-semibold">{row.case_id}</td>
                    <td className="px-4 py-3 capitalize">{String(row.complaint_category || '').replace(/_/g, ' ')}</td>
                    <td className="px-4 py-3">
                      <p>{row.buyer_name || '-'}</p>
                      <p className="text-xs text-slate-500">{row.buyer_email || ''}</p>
                    </td>
                    <td className="px-4 py-3">
                      <p>{row.seller_name || '-'}</p>
                      <p className="text-xs text-slate-500">{row.seller_email || ''}</p>
                    </td>
                    <td className="px-4 py-3">{row.reference || row.order_number || row.conversation_id || '-'}</td>
                    <td className="px-4 py-3"><Badge value={row.status} /></td>
                    <td className="px-4 py-3">
                      <a className="font-semibold text-blue-700 hover:underline" href={`/admin/assistant/disputecase/${row.id}/change/`}>
                        View case file
                      </a>
                    </td>
                  </tr>
                )}
              />
            </Panel>
          )}
        </main>
      </div>
    </div>
  );
}

function Panel({ title, subtitle, children }) {
  return (
    <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 px-5 py-4">
        <h2 className="text-lg font-bold">{title}</h2>
        <p className="text-sm text-slate-500">{subtitle}</p>
      </div>
      <div className="p-5">{children}</div>
    </section>
  );
}

function DataTable({ columns, rows, renderRow, emptyText }) {
  if (!rows.length) {
    return <div className="rounded-lg border border-dashed border-slate-200 p-8 text-center text-sm text-slate-500">{emptyText}</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-50 text-xs font-bold uppercase tracking-wide text-slate-500">
          <tr>
            {columns.map((column) => (
              <th key={column} className="px-4 py-3">{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>{rows.map(renderRow)}</tbody>
      </table>
    </div>
  );
}

function Badge({ value }) {
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-bold capitalize ${statusBadge(value)}`}>
      {String(value || '-').replace(/_/g, ' ')}
    </span>
  );
}

function ActionButton({ children, onClick, disabled, tone = 'neutral' }) {
  const classes = {
    approve: 'border-emerald-200 text-emerald-700 hover:bg-emerald-50',
    reject: 'border-red-200 text-red-700 hover:bg-red-50',
    neutral: 'border-slate-200 text-slate-700 hover:bg-slate-50',
  };

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center gap-1 rounded-lg border px-3 py-1.5 text-xs font-bold disabled:opacity-50 ${classes[tone] || classes.neutral}`}
    >
      {children}
    </button>
  );
}
