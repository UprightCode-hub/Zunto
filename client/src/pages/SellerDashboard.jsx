import React, { Suspense, lazy, useEffect, useMemo, useState } from 'react';
import {
  BarChart3,
  Headphones,
  Home,
  Plus,
  Trash2,
  Pencil,
  TrendingUp,
  Package,
  DollarSign,
  ShoppingCart,
  RefreshCw,
  ImagePlus,
  Video,
  X,
  LogOut,
  Store,
  MessageSquare,
  Settings,
  ClipboardList,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  createProduct,
  deleteProduct,
  deleteProductImage,
  getCategories,
  getLocations,
  getMyProducts,
  getProductDetail,
  getSellerOrderDetail,
  getSellerOrders,
  getSellerStatistics,
  getChatRooms,
  markProductAsSold,
  reactivateProduct,
  updateProduct,
  updateOrderItemStatus,
  updateUserProfile,
  uploadProductImage,
  uploadProductVideo,
} from '../services/api';
import { formatNaira } from '../utils/helpers';
import ProductImage from '../components/products/ProductImage';
import { getProductImage } from '../utils/product';

const OrdersTab = lazy(() => import('./sellerTabs/OrdersTab'));
const InboxTab = lazy(() => import('./sellerTabs/InboxTab'));
const SettingsTab = lazy(() => import('./sellerTabs/SettingsTab'));
const InboxAI = lazy(() => import('./InboxAI'));

const INITIAL_FORM = {
  title: '',
  description: '',
  category: '',
  location: '',
  price: '',
  quantity: '1',
  listing_type: 'product',
  condition: 'new',
  brand: '',
  negotiable: false,
  status: 'active',
};

const MAX_IMAGES = 5;
const MAX_VIDEOS = 2;
const MAX_VIDEO_BYTES = 20 * 1024 * 1024;
const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
const ALLOWED_IMAGE_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp']);
const SELLER_NAV_ITEMS = [
  { key: 'overview', label: 'Dashboard/Overview', icon: Home },
  { key: 'products', label: 'Products', icon: Package },
  { key: 'orders', label: 'Orders', icon: ClipboardList },
  { key: 'inbox', label: 'Messages', icon: MessageSquare },
  { key: 'support', label: 'Customer Support', icon: Headphones },
  { key: 'analytics', label: 'Analytics', icon: BarChart3 },
  { key: 'settings', label: 'Settings', icon: Settings },
];

const SellerDashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('overview');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showMediaModal, setShowMediaModal] = useState(false);
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [messagesUnreadCount, setMessagesUnreadCount] = useState(0);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [orderDetailLoading, setOrderDetailLoading] = useState(false);
  const [updatingItemId, setUpdatingItemId] = useState('');
  const [sellerStats, setSellerStats] = useState({
    total_orders: 0,
    total_sales: 0,
    total_items_sold: 0,
    pending_items: 0,
    shipped_items: 0,
    cancelled_items: 0,
  });
  const [categories, setCategories] = useState([]);
  const [locations, setLocations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [formError, setFormError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [formData, setFormData] = useState(INITIAL_FORM);
  const [pendingImages, setPendingImages] = useState([]);
  const [editingProduct, setEditingProduct] = useState(null);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [mediaLoading, setMediaLoading] = useState(false);
  const [mediaError, setMediaError] = useState('');
  const [mediaSuccess, setMediaSuccess] = useState('');
  const [storeSettings, setStoreSettings] = useState({
    seller_commerce_mode: (user?.sellerCommerceMode || 'direct') === 'managed',
    bio: user?.bio || '',
  });
  const [savingSettings, setSavingSettings] = useState(false);

  const refreshUnreadCount = async () => {
    try {
      const data = await getChatRooms();
      const conversations = Array.isArray(data) ? data : data?.results || [];
      setMessagesUnreadCount(conversations.reduce((total, conversation) => total + Number(conversation.unread_count || 0), 0));
    } catch {
      setMessagesUnreadCount(0);
    }
  };

  const fetchDashboardData = async (showLoader = true) => {
    try {
      if (showLoader) {
        setLoading(true);
      }
      setOrdersLoading(true);
      setRefreshing(!showLoader);
      setError('');

      const [
        productsData,
        categoriesData,
        locationsData,
        ordersData,
        statsData,
      ] = await Promise.all([
        getMyProducts(),
        getCategories(),
        getLocations(),
        getSellerOrders(),
        getSellerStatistics(),
      ]);

      setProducts(productsData?.results || productsData || []);
      setCategories(categoriesData?.results || categoriesData || []);
      setLocations(locationsData?.results || locationsData || []);
      setOrders(ordersData?.results || ordersData || []);
      setSellerStats({
        total_orders: Number(statsData?.total_orders || 0),
        total_sales: Number(statsData?.total_sales || 0),
        total_items_sold: Number(statsData?.total_items_sold || 0),
        pending_items: Number(statsData?.pending_items || 0),
        shipped_items: Number(statsData?.shipped_items || 0),
        cancelled_items: Number(statsData?.cancelled_items || 0),
      });
      refreshUnreadCount();
    } catch (fetchError) {
      setError(fetchError?.message || 'Unable to load seller dashboard data.');
    } finally {
      setLoading(false);
      setOrdersLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  useEffect(() => {
    setStoreSettings({
      seller_commerce_mode: (user?.sellerCommerceMode || 'direct') === 'managed',
      bio: user?.bio || '',
    });
  }, [user]);

  const stats = useMemo(() => {
    const pendingOrders = orders.filter((order) => ['pending', 'processing', 'paid'].includes(String(order.status || '').toLowerCase())).length;
    return [
      { label: 'Products Listed', value: String(products.length), icon: Package, accent: 'text-blue-600 dark:text-blue-400' },
      { label: 'Orders Received', value: String(sellerStats.total_orders), icon: ShoppingCart, accent: 'text-emerald-600 dark:text-emerald-400' },
      { label: 'Total Revenue', value: formatNaira(sellerStats.total_sales), icon: DollarSign, accent: 'text-purple-600 dark:text-purple-400' },
      { label: 'Pending Action', value: String(Math.max(pendingOrders, Number(sellerStats.pending_items || 0))), icon: TrendingUp, accent: 'text-amber-600 dark:text-amber-400' },
    ];
  }, [orders, products.length, sellerStats]);

  const handleOpenOrder = async (orderNumber) => {
    try {
      setOrderDetailLoading(true);
      setError('');
      const detail = await getSellerOrderDetail(orderNumber);
      setSelectedOrder(detail);
    } catch (detailError) {
      setError(detailError?.message || 'Unable to load order detail.');
    } finally {
      setOrderDetailLoading(false);
    }
  };

  const handleOrderItemStatusUpdate = async (itemId, statusValue) => {
    if (!itemId || !statusValue) return;

    try {
      setUpdatingItemId(String(itemId));
      setError('');
      await updateOrderItemStatus(itemId, statusValue);
      if (selectedOrder?.order_number) {
        const refreshed = await getSellerOrderDetail(selectedOrder.order_number);
        setSelectedOrder(refreshed);
      }
      const refreshedOrders = await getSellerOrders();
      setOrders(refreshedOrders?.results || refreshedOrders || []);
      const refreshedStats = await getSellerStatistics();
      setSellerStats({
        total_orders: Number(refreshedStats?.total_orders || 0),
        total_sales: Number(refreshedStats?.total_sales || 0),
        total_items_sold: Number(refreshedStats?.total_items_sold || 0),
        pending_items: Number(refreshedStats?.pending_items || 0),
        shipped_items: Number(refreshedStats?.shipped_items || 0),
        cancelled_items: Number(refreshedStats?.cancelled_items || 0),
      });
      setSuccessMessage('Order item status updated successfully.');
    } catch (updateError) {
      setError(updateError?.message || 'Unable to update order item status.');
    } finally {
      setUpdatingItemId('');
    }
  };

  const handleMarkAsSold = async (slug) => {
    try {
      setError('');
      await markProductAsSold(slug);
      await fetchDashboardData(false);
      setSuccessMessage('Product marked as sold.');
    } catch (statusError) {
      setError(statusError?.message || 'Unable to mark product as sold.');
    }
  };

  const handleReactivateProduct = async (slug) => {
    try {
      setError('');
      await reactivateProduct(slug);
      await fetchDashboardData(false);
      setSuccessMessage('Product reactivated successfully.');
    } catch (statusError) {
      setError(statusError?.message || 'Unable to reactivate product.');
    }
  };

  const handleDeactivateProduct = async (slug) => {
    try {
      setError('');
      await updateProduct(slug, { status: 'suspended' });
      await fetchDashboardData(false);
      setSuccessMessage('Product deactivated successfully.');
    } catch (statusError) {
      setError(statusError?.message || 'Unable to deactivate product.');
    }
  };

  const resetPendingImages = () => {
    pendingImages.forEach((image) => {
      if (image.previewUrl) {
        URL.revokeObjectURL(image.previewUrl);
      }
    });
    setPendingImages([]);
  };

  const closeCreateModal = () => {
    resetPendingImages();
    setShowCreateModal(false);
    setFormError('');
    setFormData(INITIAL_FORM);
  };

  const closeEditModal = () => {
    resetPendingImages();
    setShowEditModal(false);
    setEditingProduct(null);
    setFormError('');
    setFormData(INITIAL_FORM);
  };

  const handlePendingImageSelection = (event) => {
    const files = Array.from(event.target.files || []);
    event.target.value = '';
    if (!files.length) {
      return;
    }

    setFormError('');
    setPendingImages((current) => {
      const availableSlots = MAX_IMAGES - current.length;
      const nextImages = [...current];

      if (availableSlots <= 0) {
        setFormError(`Maximum ${MAX_IMAGES} images allowed.`);
        return current;
      }

      let nextError = '';
      files.slice(0, availableSlots).forEach((file) => {
        if (!ALLOWED_IMAGE_TYPES.has(file.type)) {
          nextError = 'Only JPG, PNG, and WebP images are allowed.';
          return;
        }

        if (file.size > MAX_IMAGE_BYTES) {
          nextError = 'Each image must be 5MB or smaller.';
          return;
        }

        nextImages.push({
          id: `${file.name}-${file.size}-${file.lastModified}`,
          file,
          previewUrl: URL.createObjectURL(file),
        });
      });

      if (!nextError && files.length > availableSlots) {
        nextError = `Only ${availableSlots} more image${availableSlots === 1 ? '' : 's'} can be added.`;
      }

      if (nextError) {
        setFormError(nextError);
      }

      return nextImages;
    });
  };

  const handlePendingImageRemove = (imageId) => {
    setPendingImages((current) => {
      const target = current.find((image) => image.id === imageId);
      if (target?.previewUrl) {
        URL.revokeObjectURL(target.previewUrl);
      }
      return current.filter((image) => image.id !== imageId);
    });
  };

  const openEditModal = async (slug) => {
    try {
      setSubmitting(true);
      setFormError('');
      resetPendingImages();
      const detail = await getProductDetail(slug);
      setEditingProduct(detail);
      setFormData({
        title: detail.title || '',
        description: detail.description || '',
        category: detail.category?.id || detail.category || '',
        location: detail.location?.id || detail.location || '',
        price: detail.price || '',
        quantity: detail.quantity || '1',
        listing_type: detail.listing_type || 'product',
        condition: detail.condition || 'new',
        brand: detail.brand || '',
        negotiable: Boolean(detail.negotiable),
        status: detail.status || 'active',
      });
      setShowEditModal(true);
    } catch (detailError) {
      setError(detailError?.message || 'Unable to load product for editing.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleAddProduct = async (event) => {
    event.preventDefault();
    setFormError('');
    setSuccessMessage('');

    try {
      setSubmitting(true);
      const createdProduct = await createProduct({
        ...formData,
        category: formData.category,
        location: formData.location,
        price: Number(formData.price),
        quantity: Number(formData.quantity),
      });

      if (pendingImages.length && createdProduct?.slug) {
        try {
          await Promise.all(
            pendingImages.map((image) => uploadProductImage(createdProduct.slug, image.file)),
          );
        } catch {
          closeCreateModal();
          await fetchDashboardData(false);
          setSuccessMessage('Product created, but one or more images failed to upload. Open Media Manager to retry.');
          return;
        }
      }

      closeCreateModal();
      await fetchDashboardData(false);
      setSuccessMessage(
        pendingImages.length
          ? 'Product created and images uploaded successfully.'
          : 'Product created successfully.',
      );
    } catch (createError) {
      setFormError(createError?.message || 'Unable to create product.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleEditProduct = async (event) => {
    event.preventDefault();
    if (!editingProduct?.slug) {
      return;
    }

    setFormError('');
    setSuccessMessage('');

    try {
      setSubmitting(true);
      await updateProduct(editingProduct.slug, {
        ...formData,
        category: formData.category,
        location: formData.location,
        price: Number(formData.price),
        quantity: Number(formData.quantity),
      });

      if (pendingImages.length) {
        const existingImages = editingProduct.images?.length || 0;
        if (existingImages + pendingImages.length > MAX_IMAGES) {
          setFormError(`This product can only have ${MAX_IMAGES} images in total.`);
          return;
        }

        try {
          await Promise.all(
            pendingImages.map((image) => uploadProductImage(editingProduct.slug, image.file)),
          );
        } catch {
          await fetchDashboardData(false);
          const refreshedProduct = await getProductDetail(editingProduct.slug);
          setEditingProduct(refreshedProduct);
          resetPendingImages();
          setSuccessMessage('Product updated, but one or more new images failed to upload.');
          return;
        }
      }

      closeEditModal();
      await fetchDashboardData(false);
      setSuccessMessage(
        pendingImages.length
          ? 'Product and images updated successfully.'
          : 'Product updated successfully.',
      );
    } catch (updateError) {
      setFormError(updateError?.message || 'Unable to update product.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteProduct = async (slug) => {
    const confirmed = window.confirm('Delete this product? This action cannot be undone.');
    if (!confirmed) {
      return;
    }

    try {
      setSuccessMessage('');
      await deleteProduct(slug);
      setProducts((current) => current.filter((item) => item.slug !== slug));
      setSuccessMessage('Product deleted successfully.');
    } catch (deleteError) {
      setError(deleteError?.message || 'Unable to delete product.');
    }
  };

  const openMediaManager = async (slug) => {
    try {
      setMediaError('');
      setMediaSuccess('');
      setMediaLoading(true);
      const detail = await getProductDetail(slug);
      setSelectedProduct(detail);
      setShowMediaModal(true);
    } catch (detailError) {
      setError(detailError?.message || 'Unable to load product media manager.');
    } finally {
      setMediaLoading(false);
    }
  };

  const reloadSelectedProduct = async () => {
    if (!selectedProduct?.slug) {
      return;
    }

    const detail = await getProductDetail(selectedProduct.slug);
    setSelectedProduct(detail);
  };

  const handleImageUpload = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file || !selectedProduct?.slug) {
      return;
    }

    const currentImages = selectedProduct?.images?.length || 0;
    if (currentImages >= MAX_IMAGES) {
      setMediaError(`Maximum ${MAX_IMAGES} images allowed.`);
      return;
    }

    try {
      setMediaLoading(true);
      setMediaError('');
      await uploadProductImage(selectedProduct.slug, file);
      await reloadSelectedProduct();
      setMediaSuccess('Image uploaded successfully.');
    } catch (uploadError) {
      setMediaError(uploadError?.message || 'Unable to upload image.');
    } finally {
      setMediaLoading(false);
    }
  };

  const handleVideoUpload = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file || !selectedProduct?.slug) {
      return;
    }

    const currentVideos = selectedProduct?.videos?.length || 0;
    if (currentVideos >= MAX_VIDEOS) {
      setMediaError(`Maximum ${MAX_VIDEOS} videos allowed.`);
      return;
    }

    if (file.size > MAX_VIDEO_BYTES) {
      setMediaError('Video file must not exceed 20MB.');
      return;
    }

    try {
      setMediaLoading(true);
      setMediaError('');
      await uploadProductVideo(selectedProduct.slug, file);
      await reloadSelectedProduct();
      setMediaSuccess('Video uploaded successfully.');
    } catch (uploadError) {
      setMediaError(uploadError?.message || 'Unable to upload video.');
    } finally {
      setMediaLoading(false);
    }
  };

  const handleDeleteImage = async (imageId) => {
    if (!selectedProduct?.slug) {
      return;
    }

    try {
      setMediaLoading(true);
      await deleteProductImage(selectedProduct.slug, imageId);
      await reloadSelectedProduct();
      setMediaSuccess('Image removed successfully.');
    } catch (deleteError) {
      setMediaError(deleteError?.message || 'Unable to remove image.');
    } finally {
      setMediaLoading(false);
    }
  };

  const handleDeleteEditImage = async (imageId) => {
    if (!editingProduct?.slug) {
      return;
    }

    try {
      setSubmitting(true);
      setFormError('');
      await deleteProductImage(editingProduct.slug, imageId);
      const refreshedProduct = await getProductDetail(editingProduct.slug);
      setEditingProduct(refreshedProduct);
      setSuccessMessage('Image removed successfully.');
    } catch (deleteError) {
      setFormError(deleteError?.message || 'Unable to remove image.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleStoreSettingsSave = async (event) => {
    event.preventDefault();

    try {
      setSavingSettings(true);
      setError('');
      setSuccessMessage('');
      const updated = await updateUserProfile({
        seller_commerce_mode: storeSettings.seller_commerce_mode,
        bio: storeSettings.bio,
      });
      localStorage.setItem('user', JSON.stringify(updated));
      setSuccessMessage('Seller settings saved successfully.');
    } catch (saveError) {
      setError(saveError?.message || 'Unable to save seller settings.');
    } finally {
      setSavingSettings(false);
    }
  };

  const handleExitSellerDashboard = () => {
    if (window.confirm('Leave Seller Dashboard and return to buyer view?')) {
      navigate('/');
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 dark:bg-gray-950">
      <div className="mx-auto flex min-h-screen max-w-[1600px] gap-6 px-4 py-6">
        <aside className="sticky top-6 flex h-[calc(100vh-3rem)] w-72 shrink-0 flex-col rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-gray-950">
          <div className="mb-6">
            <div className="inline-flex items-center gap-2 rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold uppercase tracking-wide text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-200">
              <Store className="h-4 w-4" />
              Seller Mode
            </div>
            <h1 className="mt-4 text-xl font-bold text-gray-950 dark:text-white">Zunto Seller</h1>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Commerce operations workspace</p>
          </div>

          <nav className="space-y-1">
            {SELLER_NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const active = activeTab === item.key;
              return (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => setActiveTab(item.key)}
                  className={`flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-left text-sm font-semibold transition ${
                    active
                      ? 'bg-emerald-600 text-white shadow-sm'
                      : 'text-gray-700 hover:bg-slate-100 dark:text-gray-200 dark:hover:bg-gray-900'
                  }`}
                >
                  <span className="flex items-center gap-3">
                    <Icon className="h-4 w-4" />
                    {item.label}
                  </span>
                  {item.key === 'inbox' && messagesUnreadCount > 0 && (
                    <span className={`rounded-full px-2 py-0.5 text-xs ${active ? 'bg-white text-emerald-700' : 'bg-emerald-600 text-white'}`}>
                      {messagesUnreadCount}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          <div className="mt-auto border-t border-slate-200 pt-4 dark:border-gray-800">
            <button
              type="button"
              onClick={handleExitSellerDashboard}
              className="flex w-full items-center justify-center gap-2 rounded-lg border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 hover:bg-red-50 dark:border-red-900/50 dark:text-red-300 dark:hover:bg-red-950/30"
            >
              <LogOut className="h-4 w-4" />
              Exit Seller Dashboard
            </button>
          </div>
        </aside>

        <main className="min-w-0 flex-1">
          <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700 dark:text-emerald-300">{SELLER_NAV_ITEMS.find((item) => item.key === activeTab)?.label}</p>
              <h2 className="mt-1 text-3xl font-bold text-gray-950 dark:text-white">Seller Dashboard</h2>
            </div>
            <div className="flex flex-wrap gap-3">
              {activeTab === 'products' && (
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-5 py-2 text-sm font-semibold text-white transition-colors hover:bg-emerald-700"
                >
                  <Plus className="h-4 w-4" /> Add New Product
                </button>
              )}
              <button
                type="button"
                onClick={() => fetchDashboardData(false)}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-200 dark:hover:bg-gray-900"
              >
                <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
          </div>

        {error && <p className="mb-4 rounded-lg bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300 px-4 py-3">{error}</p>}
        {successMessage && <p className="mb-4 rounded-lg bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300 px-4 py-3">{successMessage}</p>}

        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {stats.map((stat) => {
              const Icon = stat.icon;
              return (
                <div key={stat.label} className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
                  <div className="flex justify-between items-start mb-3">
                    <Icon className={`w-8 h-8 ${stat.accent}`} />
                  </div>
                  <p className="text-gray-600 dark:text-gray-400 text-sm mb-1">{stat.label}</p>
                  <p className="text-3xl font-bold text-gray-900 dark:text-white">{stat.value}</p>
                </div>
              );
            })}
          </div>
        )}

        {activeTab === 'products' && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-x-auto">
            {loading ? (
              <div className="p-10 text-center text-gray-500 dark:text-gray-400">Loading products...</div>
            ) : products.length === 0 ? (
              <div className="p-10 text-center text-gray-500 dark:text-gray-400">No products yet. Create your first listing.</div>
            ) : (
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
                  <tr>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900 dark:text-white">Product</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900 dark:text-white">Status</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900 dark:text-white">Price</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900 dark:text-white">Stock</th>
                    <th className="px-6 py-4 text-right text-sm font-semibold text-gray-900 dark:text-white">Quick Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {products.map((product) => (
                    <tr key={product.slug} className="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="h-14 w-14 overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-100 dark:bg-gray-700 flex items-center justify-center shrink-0">
                            {getProductImage(product, '') ? (
                              <ProductImage
                                src={getProductImage(product, '')}
                                alt={product.title || product.name}
                                className="h-full w-full object-cover"
                              />
                            ) : (
                              <ImagePlus className="w-5 h-5 text-gray-400 dark:text-gray-500" />
                            )}
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{product.title || product.name}</p>
                            <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                              {getProductImage(product, '') ? 'Image ready' : 'No image yet'}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm">
                        <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${
                          product.status === 'active'
                            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-200'
                            : 'bg-slate-100 text-slate-700 dark:bg-slate-500/15 dark:text-slate-200'
                        }`}>
                          {product.status || 'draft'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm font-semibold text-gray-900 dark:text-white">{formatNaira(product.price)}</td>
                      <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">{product.quantity ?? 0}</td>
                      <td className="px-6 py-4 text-sm">
                        <div className="flex justify-end gap-2">
                        <button
                          onClick={() => openEditModal(product.slug)}
                          className="inline-flex items-center gap-1 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-900"
                          aria-label={`Edit ${product.title || product.name}`}
                        >
                          <Pencil className="h-3.5 w-3.5" /> Edit
                        </button>
                        <button
                          onClick={() => openMediaManager(product.slug)}
                          className="inline-flex items-center gap-1 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-900"
                          aria-label={`Manage media for ${product.title || product.name}`}
                        >
                          <ImagePlus className="h-3.5 w-3.5" /> Media
                        </button>
                        {product.status === 'active' ? (
                          <button
                            onClick={() => handleDeactivateProduct(product.slug)}
                            className="rounded-lg border border-red-200 px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-50 dark:border-red-900/50 dark:text-red-300 dark:hover:bg-red-950/30"
                          >
                            Deactivate
                          </button>
                        ) : (
                          <button
                            onClick={() => handleReactivateProduct(product.slug)}
                            className="rounded-lg border border-emerald-200 px-3 py-1.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-50 dark:border-emerald-900/50 dark:text-emerald-300 dark:hover:bg-emerald-950/30"
                          >
                            Reactivate
                          </button>
                        )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        <Suspense fallback={<div className="p-8 text-center text-gray-500 dark:text-gray-400">Loading tab...</div>}>
          {activeTab === 'orders' && (
            <OrdersTab
              orders={orders}
              ordersLoading={ordersLoading}
              onOpenOrder={handleOpenOrder}
              selectedOrder={selectedOrder}
              orderDetailLoading={orderDetailLoading}
              onUpdateOrderItemStatus={handleOrderItemStatusUpdate}
              updatingItemId={updatingItemId}
            />
          )}

          {activeTab === 'inbox' && <InboxTab onUnreadCountChange={setMessagesUnreadCount} />}

          {activeTab === 'support' && (
            <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-950">
              <InboxAI
                embedded
                defaultAssistantMode="customer_service"
                initialTitle="Zunto Seller Support"
              />
            </div>
          )}

          {activeTab === 'analytics' && (
            <div className="grid gap-6 lg:grid-cols-2">
              <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-950">
                <h2 className="text-xl font-bold text-gray-950 dark:text-white">Sales Over Time</h2>
                <div className="mt-5 space-y-4">
                  {orders.slice(0, 6).map((order) => {
                    const maxValue = Math.max(...orders.map((item) => Number(item.total_amount || 0)), 1);
                    const width = Math.max(8, (Number(order.total_amount || 0) / maxValue) * 100);
                    return (
                      <div key={order.order_number}>
                        <div className="mb-1 flex justify-between text-sm">
                          <span className="text-gray-500">{new Date(order.created_at).toLocaleDateString()}</span>
                          <span className="font-semibold text-gray-950 dark:text-white">{formatNaira(order.total_amount)}</span>
                        </div>
                        <div className="h-3 rounded-full bg-gray-100 dark:bg-gray-800">
                          <div className="h-3 rounded-full bg-emerald-600" style={{ width: `${width}%` }} />
                        </div>
                      </div>
                    );
                  })}
                  {orders.length === 0 && <p className="text-sm text-gray-500">No order revenue yet.</p>}
                </div>
              </div>

              <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-950">
                <h2 className="text-xl font-bold text-gray-950 dark:text-white">Top Performing Products</h2>
                <div className="mt-5 space-y-3">
                  {products
                    .slice()
                    .sort((a, b) => Number(b.views_count || 0) - Number(a.views_count || 0))
                    .slice(0, 6)
                    .map((product) => (
                      <div key={product.slug} className="flex items-center justify-between rounded-lg border border-gray-200 px-4 py-3 dark:border-gray-800">
                        <div>
                          <p className="text-sm font-semibold text-gray-950 dark:text-white">{product.title || product.name}</p>
                          <p className="text-xs text-gray-500">{product.views_count || 0} views - stock {product.quantity ?? 0}</p>
                        </div>
                        <span className="text-sm font-bold text-emerald-700 dark:text-emerald-300">{formatNaira(product.price)}</span>
                      </div>
                    ))}
                  {products.length === 0 && <p className="text-sm text-gray-500">No product analytics yet.</p>}
                </div>
              </div>

              <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-950 lg:col-span-2">
                <h2 className="text-xl font-bold text-gray-950 dark:text-white">Revenue Trend</h2>
                <div className="mt-4 grid gap-4 sm:grid-cols-3">
                  <div className="rounded-lg bg-gray-50 p-4 dark:bg-gray-900">
                    <p className="text-sm text-gray-500">Paid Revenue</p>
                    <p className="mt-1 text-2xl font-bold text-gray-950 dark:text-white">{formatNaira(sellerStats.total_sales)}</p>
                  </div>
                  <div className="rounded-lg bg-gray-50 p-4 dark:bg-gray-900">
                    <p className="text-sm text-gray-500">Items Sold</p>
                    <p className="mt-1 text-2xl font-bold text-gray-950 dark:text-white">{sellerStats.total_items_sold}</p>
                  </div>
                  <div className="rounded-lg bg-gray-50 p-4 dark:bg-gray-900">
                    <p className="text-sm text-gray-500">Shipped Items</p>
                    <p className="mt-1 text-2xl font-bold text-gray-950 dark:text-white">{sellerStats.shipped_items}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'settings' && (
            <SettingsTab
              storeSettings={storeSettings}
              setStoreSettings={setStoreSettings}
              handleStoreSettingsSave={handleStoreSettingsSave}
              savingSettings={savingSettings}
            />
          )}
        </Suspense>
        </main>

        {showCreateModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-xl w-full p-6 max-h-[90vh] overflow-auto">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-5">Add New Product</h2>
              <form onSubmit={handleAddProduct} className="space-y-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">Title</label>
                  <input
                    type="text"
                    required
                    value={formData.title}
                    onChange={(event) => setFormData((current) => ({ ...current, title: event.target.value }))}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">Description</label>
                  <textarea
                    rows="3"
                    required
                    value={formData.description}
                    onChange={(event) => setFormData((current) => ({ ...current, description: event.target.value }))}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">Category</label>
                    <select
                      required
                      value={formData.category}
                      onChange={(event) => setFormData((current) => ({ ...current, category: event.target.value }))}
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="">Select Category</option>
                      {categories.map((category) => (
                        <option key={category.id} value={category.id}>{category.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">Location</label>
                    <select
                      required
                      value={formData.location}
                      onChange={(event) => setFormData((current) => ({ ...current, location: event.target.value }))}
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="">Select Location</option>
                      {locations.map((location) => (
                        <option key={location.id} value={location.id}>{location.full_address || `${location.city}, ${location.state}`}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">Price</label>
                    <input
                      type="text"
                      inputMode="decimal"
                      min="0"
                      step="0.01"
                      required
                      value={formData.price}
                      onChange={(event) => setFormData((current) => ({ ...current, price: event.target.value }))}
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">Quantity</label>
                    <input
                      type="text"
                      inputMode="numeric"
                      min="1"
                      required
                      value={formData.quantity}
                      onChange={(event) => setFormData((current) => ({ ...current, quantity: event.target.value }))}
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">Brand (optional)</label>
                  <input
                    type="text"
                    value={formData.brand}
                    onChange={(event) => setFormData((current) => ({ ...current, brand: event.target.value }))}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <div className="flex items-center justify-between gap-3 mb-2">
                    <label className="block text-sm font-semibold text-gray-900 dark:text-white">Product Images</label>
                    <span className="text-xs text-gray-500 dark:text-gray-400">{pendingImages.length}/{MAX_IMAGES} selected</span>
                  </div>
                  <label className="flex items-center justify-center gap-2 w-full px-4 py-3 border border-dashed border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700/50 text-gray-700 dark:text-gray-200 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition">
                    <ImagePlus className="w-4 h-4" />
                    <span>Add up to {MAX_IMAGES} images</span>
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      multiple
                      className="hidden"
                      onChange={handlePendingImageSelection}
                    />
                  </label>
                  <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">Accepted formats: JPG, PNG, WebP. Maximum 5MB each.</p>
                  {pendingImages.length > 0 && (
                    <div className="mt-4 grid grid-cols-2 md:grid-cols-3 gap-3">
                      {pendingImages.map((image) => (
                        <div key={image.id} className="relative overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
                          <ProductImage src={image.previewUrl} alt={image.file.name} className="h-24 w-full object-cover" />
                          <div className="px-2 py-2">
                            <p className="text-xs text-gray-700 dark:text-gray-200 truncate">{image.file.name}</p>
                          </div>
                          <button
                            type="button"
                            onClick={() => handlePendingImageRemove(image.id)}
                            className="absolute top-2 right-2 rounded-full bg-black/70 p-1 text-white hover:bg-black/85"
                            aria-label={`Remove ${image.file.name}`}
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                {formError && <p className="text-sm text-red-600 dark:text-red-300">{formError}</p>}
                <div className="flex gap-4 pt-2">
                  <button
                    type="button"
                    onClick={closeCreateModal}
                    className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white hover:bg-gray-50 dark:hover:bg-gray-700"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-70 text-white rounded-lg font-semibold"
                  >
                    {submitting ? 'Saving...' : 'Create Product'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {showEditModal && editingProduct && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-3xl w-full p-6 max-h-[90vh] overflow-auto">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-5">Edit Product</h2>
              <form onSubmit={handleEditProduct} className="space-y-5">
                <div>
                  <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">Title</label>
                  <input
                    type="text"
                    required
                    value={formData.title}
                    onChange={(event) => setFormData((current) => ({ ...current, title: event.target.value }))}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">Description</label>
                  <textarea
                    rows="3"
                    required
                    value={formData.description}
                    onChange={(event) => setFormData((current) => ({ ...current, description: event.target.value }))}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">Category</label>
                    <select
                      required
                      value={formData.category}
                      onChange={(event) => setFormData((current) => ({ ...current, category: event.target.value }))}
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="">Select Category</option>
                      {categories.map((category) => (
                        <option key={category.id} value={category.id}>{category.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">Location</label>
                    <select
                      required
                      value={formData.location}
                      onChange={(event) => setFormData((current) => ({ ...current, location: event.target.value }))}
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="">Select Location</option>
                      {locations.map((location) => (
                        <option key={location.id} value={location.id}>{location.full_address || `${location.city}, ${location.state}`}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">Price</label>
                    <input
                      type="text"
                      inputMode="decimal"
                      min="0"
                      step="0.01"
                      required
                      value={formData.price}
                      onChange={(event) => setFormData((current) => ({ ...current, price: event.target.value }))}
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">Quantity</label>
                    <input
                      type="text"
                      inputMode="numeric"
                      min="1"
                      required
                      value={formData.quantity}
                      onChange={(event) => setFormData((current) => ({ ...current, quantity: event.target.value }))}
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">Brand (optional)</label>
                    <input
                      type="text"
                      value={formData.brand}
                      onChange={(event) => setFormData((current) => ({ ...current, brand: event.target.value }))}
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">Status</label>
                    <select
                      value={formData.status}
                      onChange={(event) => setFormData((current) => ({ ...current, status: event.target.value }))}
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="draft">Draft</option>
                      <option value="active">Active</option>
                      <option value="sold">Sold</option>
                      <option value="reserved">Reserved</option>
                      <option value="suspended">Suspended</option>
                      <option value="expired">Expired</option>
                    </select>
                  </div>
                </div>

                <div className="space-y-4 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Existing Images</h3>
                    <span className="text-xs text-gray-500 dark:text-gray-400">{editingProduct.images?.length || 0}/{MAX_IMAGES} uploaded</span>
                  </div>
                  {editingProduct.images?.length ? (
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                      {editingProduct.images.map((image) => (
                        <div key={image.id} className="relative overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
                          <ProductImage src={image.image} alt={image.caption || 'Product image'} className="h-28 w-full object-cover" />
                          <button
                            type="button"
                            onClick={() => handleDeleteEditImage(image.id)}
                            className="absolute top-2 right-2 rounded-full bg-black/70 p-1 text-white hover:bg-black/85"
                            aria-label="Remove image"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500 dark:text-gray-400">No images uploaded yet.</p>
                  )}

                  <div>
                    <div className="flex items-center justify-between gap-3 mb-2">
                      <label className="block text-sm font-semibold text-gray-900 dark:text-white">Add More Images</label>
                      <span className="text-xs text-gray-500 dark:text-gray-400">{pendingImages.length} queued</span>
                    </div>
                    <label className="flex items-center justify-center gap-2 w-full px-4 py-3 border border-dashed border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700/50 text-gray-700 dark:text-gray-200 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition">
                      <ImagePlus className="w-4 h-4" />
                      <span>Queue new images</span>
                      <input
                        type="file"
                        accept="image/jpeg,image/png,image/webp"
                        multiple
                        className="hidden"
                        onChange={handlePendingImageSelection}
                      />
                    </label>
                    <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">Total existing and queued images cannot exceed {MAX_IMAGES}.</p>
                    {pendingImages.length > 0 && (
                      <div className="mt-4 grid grid-cols-2 md:grid-cols-3 gap-3">
                        {pendingImages.map((image) => (
                          <div key={image.id} className="relative overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
                            <ProductImage src={image.previewUrl} alt={image.file.name} className="h-24 w-full object-cover" />
                            <div className="px-2 py-2">
                              <p className="text-xs text-gray-700 dark:text-gray-200 truncate">{image.file.name}</p>
                            </div>
                            <button
                              type="button"
                              onClick={() => handlePendingImageRemove(image.id)}
                              className="absolute top-2 right-2 rounded-full bg-black/70 p-1 text-white hover:bg-black/85"
                              aria-label={`Remove ${image.file.name}`}
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {formError && <p className="text-sm text-red-600 dark:text-red-300">{formError}</p>}
                <div className="flex gap-4 pt-2">
                  <button
                    type="button"
                    onClick={closeEditModal}
                    className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white hover:bg-gray-50 dark:hover:bg-gray-700"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-70 text-white rounded-lg font-semibold"
                  >
                    {submitting ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {showMediaModal && selectedProduct && (
          <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
            <div className="w-full max-w-5xl bg-white dark:bg-gray-900 rounded-2xl shadow-2xl max-h-[90vh] overflow-auto">
              <div className="sticky top-0 z-10 flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
                <div>
                  <h3 className="text-xl font-bold text-gray-900 dark:text-white">Media Manager</h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">{selectedProduct.title}</p>
                </div>
                <button onClick={() => setShowMediaModal(false)} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800">
                  <X className="w-5 h-5 text-gray-700 dark:text-gray-300" />
                </button>
              </div>

              <div className="p-6 space-y-6">
                {mediaError && <p className="rounded-lg bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300 px-4 py-2">{mediaError}</p>}
                {mediaSuccess && <p className="rounded-lg bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300 px-4 py-2">{mediaSuccess}</p>}
                {mediaLoading && <p className="text-sm text-gray-500 dark:text-gray-400">Processing media request...</p>}

                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="font-semibold text-gray-900 dark:text-white">Images ({selectedProduct.images?.length || 0}/{MAX_IMAGES})</h4>
                    <label className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white cursor-pointer hover:bg-blue-700 transition">
                      <ImagePlus className="w-4 h-4" /> Upload Image
                      <input type="file" accept="image/*" className="hidden" onChange={handleImageUpload} />
                    </label>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {(selectedProduct.images || []).map((image) => (
                      <div key={image.id} className="relative border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                        <ProductImage src={image.image} alt={image.caption || 'Product image'} className="w-full h-32 object-cover" />
                        <button
                          type="button"
                          onClick={() => handleDeleteImage(image.id)}
                          className="absolute top-2 right-2 bg-black/60 text-white rounded-full p-1 hover:bg-black/80"
                          aria-label="Delete image"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="font-semibold text-gray-900 dark:text-white">Videos ({selectedProduct.videos?.length || 0}/{MAX_VIDEOS})</h4>
                    <label className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-purple-600 text-white cursor-pointer hover:bg-purple-700 transition">
                      <Video className="w-4 h-4" /> Upload Video
                      <input type="file" accept="video/*" className="hidden" onChange={handleVideoUpload} />
                    </label>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">Video files must be 20MB or smaller.</p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {(selectedProduct.videos || []).map((video) => (
                      <video key={video.id} controls preload="metadata" className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-black">
                        <source src={video.video} type="video/mp4" />
                        Your browser does not support video playback.
                      </video>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SellerDashboard;
