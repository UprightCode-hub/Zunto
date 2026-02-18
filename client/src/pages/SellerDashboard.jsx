import React, { useEffect, useMemo, useState } from 'react';
import {
  Plus,
  Trash2,
  TrendingUp,
  Package,
  DollarSign,
  ShoppingCart,
  Inbox,
  RefreshCw,
  ImagePlus,
  Video,
  X,
} from 'lucide-react';
import MarketplaceInbox from '../components/chat/MarketplaceInbox';
import { useAuth } from '../context/AuthContext';
import {
  createProduct,
  deleteProduct,
  deleteProductImage,
  getCategories,
  getLocations,
  getMyProducts,
  getProductDetail,
  updateUserProfile,
  uploadProductImage,
  uploadProductVideo,
} from '../services/api';

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

const SellerDashboard = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('products');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showMediaModal, setShowMediaModal] = useState(false);
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [locations, setLocations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [formError, setFormError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [formData, setFormData] = useState(INITIAL_FORM);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [mediaLoading, setMediaLoading] = useState(false);
  const [mediaError, setMediaError] = useState('');
  const [mediaSuccess, setMediaSuccess] = useState('');
  const [storeSettings, setStoreSettings] = useState({
    seller_commerce_mode: Boolean(user?.seller_commerce_mode),
    bio: user?.bio || '',
  });
  const [savingSettings, setSavingSettings] = useState(false);

  const fetchDashboardData = async (showLoader = true) => {
    try {
      if (showLoader) {
        setLoading(true);
      }
      setRefreshing(!showLoader);
      setError('');

      const [productsData, categoriesData, locationsData] = await Promise.all([
        getMyProducts(),
        getCategories(),
        getLocations(),
      ]);

      setProducts(productsData?.results || productsData || []);
      setCategories(categoriesData?.results || categoriesData || []);
      setLocations(locationsData?.results || locationsData || []);
    } catch (fetchError) {
      setError(fetchError?.message || 'Unable to load seller dashboard data.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  useEffect(() => {
    setStoreSettings({
      seller_commerce_mode: Boolean(user?.seller_commerce_mode),
      bio: user?.bio || '',
    });
  }, [user]);

  const stats = useMemo(() => {
    const totalProducts = products.length;
    const totalViews = products.reduce((sum, item) => sum + Number(item.views_count || 0), 0);
    const totalFavorites = products.reduce((sum, item) => sum + Number(item.favorites_count || 0), 0);
    const activeCount = products.filter((item) => item.status === 'active').length;

    return [
      { label: 'Total Products', value: totalProducts.toString(), icon: Package, accent: 'text-blue-600 dark:text-blue-400' },
      { label: 'Active Listings', value: activeCount.toString(), icon: ShoppingCart, accent: 'text-green-600 dark:text-green-400' },
      { label: 'Total Views', value: totalViews.toString(), icon: TrendingUp, accent: 'text-purple-600 dark:text-purple-400' },
      { label: 'Favorites', value: totalFavorites.toString(), icon: DollarSign, accent: 'text-amber-600 dark:text-amber-400' },
    ];
  }, [products]);

  const closeModal = () => {
    setShowCreateModal(false);
    setFormError('');
    setFormData(INITIAL_FORM);
  };

  const handleAddProduct = async (event) => {
    event.preventDefault();
    setFormError('');
    setSuccessMessage('');

    try {
      setSubmitting(true);
      await createProduct({
        ...formData,
        category: Number(formData.category),
        location: Number(formData.location),
        price: Number(formData.price),
        quantity: Number(formData.quantity),
      });
      closeModal();
      await fetchDashboardData(false);
      setSuccessMessage('Product created successfully.');
    } catch (createError) {
      setFormError(createError?.message || 'Unable to create product.');
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

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8 flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">Seller Dashboard</h1>
            <p className="text-gray-600 dark:text-gray-400">Manage your products, media, and buyer conversations</p>
          </div>
          <button
            type="button"
            onClick={() => fetchDashboardData(false)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {error && <p className="mb-4 rounded-lg bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300 px-4 py-3">{error}</p>}
        {successMessage && <p className="mb-4 rounded-lg bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300 px-4 py-3">{successMessage}</p>}

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

        <div className="flex justify-between items-center mb-6 gap-4 flex-wrap">
          <div className="border-b border-gray-200 dark:border-gray-700 flex gap-4">
            {['products', 'inbox', 'settings'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-3 font-semibold transition-colors whitespace-nowrap ${
                  activeTab === tab
                    ? 'border-b-2 border-green-600 text-green-600 dark:text-green-400'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>
          {activeTab === 'products' && (
            <button
              onClick={() => setShowCreateModal(true)}
              className="bg-green-600 hover:bg-green-700 text-white font-semibold px-5 py-2 rounded-lg transition-colors flex items-center gap-2"
            >
              <Plus className="w-4 h-4" /> Add Product
            </button>
          )}
        </div>

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
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900 dark:text-white">Category</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900 dark:text-white">Price</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900 dark:text-white">Views</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900 dark:text-white">Favorites</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900 dark:text-white">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {products.map((product) => (
                    <tr key={product.slug} className="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                      <td className="px-6 py-4 text-sm text-gray-900 dark:text-white font-medium">{product.title || product.name}</td>
                      <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">{product.category_name || 'N/A'}</td>
                      <td className="px-6 py-4 text-sm font-semibold text-gray-900 dark:text-white">${product.price}</td>
                      <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">{product.views_count || 0}</td>
                      <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">{product.favorites_count || 0}</td>
                      <td className="px-6 py-4 text-sm flex gap-2">
                        <button
                          onClick={() => openMediaManager(product.slug)}
                          className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 p-1"
                          aria-label={`Manage media for ${product.title || product.name}`}
                        >
                          <ImagePlus className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDeleteProduct(product.slug)}
                          className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 p-1"
                          aria-label={`Delete ${product.title || product.name}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {activeTab === 'inbox' && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <Inbox className="w-5 h-5" />
                Seller Inbox
              </h2>
            </div>
            <div className="p-6">
              <MarketplaceInbox
                containerClassName="h-[70vh]"
                headerTitle="Seller Inbox"
                emptyListLabel="No buyer conversations yet"
              />
            </div>
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">Seller Settings</h2>
            <form onSubmit={handleStoreSettingsSave} className="space-y-5 max-w-3xl">
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
          </div>
        )}

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
                      type="number"
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
                      type="number"
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
                {formError && <p className="text-sm text-red-600 dark:text-red-300">{formError}</p>}
                <div className="flex gap-4 pt-2">
                  <button
                    type="button"
                    onClick={closeModal}
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
                        <img src={image.image} alt={image.caption || 'Product image'} className="w-full h-32 object-cover" />
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
