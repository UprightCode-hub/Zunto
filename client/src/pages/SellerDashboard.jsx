import React, { useState } from 'react';
import { Plus, Edit2, Trash2, Eye, TrendingUp, Package, DollarSign, ShoppingCart, Inbox } from 'lucide-react';
import MarketplaceInbox from '../components/chat/MarketplaceInbox';

const SellerDashboard = () => {
  const [activeTab, setActiveTab] = useState('products');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [products, setProducts] = useState([
    {
      id: 1,
      name: 'Premium Headphones',
      category: 'Electronics',
      price: '$199.99',
      stock: 45,
      sales: 234,
      rating: 4.8,
      image: 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%22100%22 viewBox=%220 0 100 100%22%3E%3Crect fill=%22%23e5e7eb%22 width=%22100%22 height=%22100%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 font-family=%22sans-serif%22 font-size=%227%22 fill=%22%239ca3af%22%3EImage%3C/text%3E%3C/svg%3E',
      status: 'Active',
    },
    {
      id: 2,
      name: 'Wireless Mouse',
      category: 'Electronics',
      price: '$49.99',
      stock: 120,
      sales: 567,
      rating: 4.6,
      image: 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%22100%22 viewBox=%220 0 100 100%22%3E%3Crect fill=%22%23e5e7eb%22 width=%22100%22 height=%22100%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 font-family=%22sans-serif%22 font-size=%227%22 fill=%22%239ca3af%22%3EImage%3C/text%3E%3C/svg%3E',
      status: 'Active',
    },
    {
      id: 3,
      name: 'USB-C Cable',
      category: 'Accessories',
      price: '$14.99',
      stock: 500,
      sales: 1203,
      rating: 4.9,
      image: 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%22100%22 viewBox=%220 0 100 100%22%3E%3Crect fill=%22%23e5e7eb%22 width=%22100%22 height=%22100%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 font-family=%22sans-serif%22 font-size=%227%22 fill=%22%239ca3af%22%3EImage%3C/text%3E%3C/svg%3E',
      status: 'Active',
    },
  ]);

  const [formData, setFormData] = useState({
    name: '',
    category: '',
    price: '',
    stock: '',
    description: '',
  });

  const stats = [
    { label: 'Total Products', value: products.length.toString(), icon: Package, change: '+2' },
    { label: 'Total Sales', value: products.reduce((sum, p) => sum + parseInt(p.sales), 0).toString(), icon: ShoppingCart, change: '+450' },
    { label: 'Revenue', value: '$12,450', icon: DollarSign, change: '+$2,500' },
    { label: 'Avg Rating', value: '4.8★', icon: TrendingUp, change: '+0.2' },
  ];

  const handleAddProduct = (e) => {
    e.preventDefault();
    const newProduct = {
      id: products.length + 1,
      ...formData,
      sales: Math.floor(Math.random() * 1000),
      rating: (Math.random() * 1 + 4).toFixed(1),
      image: 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%22100%22 viewBox=%220 0 100 100%22%3E%3Crect fill=%22%23e5e7eb%22 width=%22100%22 height=%22100%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 font-family=%22sans-serif%22 font-size=%227%22 fill=%22%239ca3af%22%3EImage%3C/text%3E%3C/svg%3E',
      stock: parseInt(formData.stock),
      status: 'Active',
    };
    setProducts([...products, newProduct]);
    setFormData({ name: '', category: '', price: '', stock: '', description: '' });
    setShowCreateModal(false);
  };

  const handleDeleteProduct = (id) => {
    setProducts(products.filter(p => p.id !== id));
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">Seller Dashboard</h1>
          <p className="text-gray-600 dark:text-gray-400">Manage your products and sales</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {stats.map((stat, index) => {
            const Icon = stat.icon;
            return (
              <div key={index} className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
                <div className="flex justify-between items-start mb-4">
                  <Icon className="w-8 h-8 text-green-600 dark:text-green-400" />
                  <span className="text-green-600 text-sm font-semibold">{stat.change}</span>
                </div>
                <p className="text-gray-600 dark:text-gray-400 text-sm mb-1">{stat.label}</p>
                <p className="text-3xl font-bold text-gray-900 dark:text-white">{stat.value}</p>
              </div>
            );
          })}
        </div>

        {/* Navigation and Add Product Button */}
        <div className="flex justify-between items-center mb-6 gap-4 flex-wrap">
          <div className="border-b border-gray-200 dark:border-gray-700 flex gap-4 flex-grow min-w-max">
            {['products', 'analytics', 'inbox', 'settings'].map((tab) => (
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
              className="flex items-center gap-2 bg-green-600 hover:bg-green-700 dark:bg-green-700 dark:hover:bg-green-600 text-white font-semibold px-6 py-3 rounded-lg transition-colors"
            >
              <Plus className="w-5 h-5" /> Add Product
            </button>
          )}
        </div>

        {/* Products Tab */}
        {activeTab === 'products' && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">Your Products</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-gray-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900 dark:text-white">Product</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900 dark:text-white">Category</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900 dark:text-white">Price</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900 dark:text-white">Stock</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900 dark:text-white">Sales</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900 dark:text-white">Rating</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900 dark:text-white">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {products.map((product) => (
                    <tr key={product.id} className="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                      <td className="px-6 py-4 text-sm">
                        <div className="flex items-center gap-3">
                          <img src={product.image} alt={product.name} className="w-10 h-10 rounded object-cover" />
                          <span className="text-gray-900 dark:text-white font-medium">{product.name}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">{product.category}</td>
                      <td className="px-6 py-4 text-sm font-semibold text-gray-900 dark:text-white">{product.price}</td>
                      <td className="px-6 py-4 text-sm">
                        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                          product.stock > 100
                            ? 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200'
                            : product.stock > 0
                            ? 'bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200'
                            : 'bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200'
                        }`}>
                          {product.stock}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">{product.sales}</td>
                      <td className="px-6 py-4 text-sm">
                        <span className="text-yellow-500">★</span>
                        <span className="text-gray-900 dark:text-white font-semibold">{product.rating}</span>
                      </td>
                      <td className="px-6 py-4 text-sm flex gap-2">
                        <button className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 p-1">
                          <Eye className="w-4 h-4" />
                        </button>
                        <button className="text-yellow-600 hover:text-yellow-800 dark:text-yellow-400 dark:hover:text-yellow-300 p-1">
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDeleteProduct(product.id)}
                          className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 p-1"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Analytics Tab */}
        {activeTab === 'analytics' && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-8">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="p-6 border border-gray-200 dark:border-gray-700 rounded-lg">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Sales Trend</h3>
                <div className="h-40 bg-gradient-to-r from-green-100 to-green-50 dark:from-green-900 dark:to-gray-800 rounded flex items-end justify-around p-4">
                  {[30, 45, 60, 55, 70, 85, 90].map((value, i) => (
                    <div key={i} className="flex flex-col items-center">
                      <div className="w-6 bg-green-600 rounded-t" style={{ height: `${value}%` }}></div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="p-6 border border-gray-200 dark:border-gray-700 rounded-lg">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Top Products</h3>
                <div className="space-y-3">
                  {products.slice(0, 3).map((product) => (
                    <div key={product.id} className="flex justify-between items-center pb-3 border-b border-gray-200 dark:border-gray-700 last:border-0">
                      <span className="text-gray-600 dark:text-gray-400">{product.name}</span>
                      <span className="font-semibold text-gray-900 dark:text-white">{product.sales} sales</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}



        {/* Inbox Tab */}
        {activeTab === 'inbox' && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <Inbox className="w-5 h-5" />
                Seller Inbox
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Reply to buyer conversations from your product listings.
              </p>
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

        {/* Settings Tab */}
        {activeTab === 'settings' && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Seller Settings</h2>
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">Store Name</label>
                <input
                  type="text"
                  defaultValue="My Store"
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:border-green-600"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">Description</label>
                <textarea
                  defaultValue="My amazing store description..."
                  rows="4"
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:border-green-600"
                />
              </div>
              <button className="bg-green-600 hover:bg-green-700 text-white font-semibold px-6 py-2 rounded-lg transition-colors">
                Save Settings
              </button>
            </div>
          </div>
        )}

        {/* Create Product Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Add New Product</h2>
              <form onSubmit={handleAddProduct} className="space-y-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">Product Name</label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:border-green-600"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">Category</label>
                  <select
                    required
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:border-green-600"
                  >
                    <option value="">Select Category</option>
                    <option value="Electronics">Electronics</option>
                    <option value="Accessories">Accessories</option>
                    <option value="Fashion">Fashion</option>
                    <option value="Home">Home</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">Price</label>
                  <input
                    type="text"
                    required
                    value={formData.price}
                    onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                    placeholder="$0.00"
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:border-green-600"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">Stock Quantity</label>
                  <input
                    type="number"
                    required
                    value={formData.stock}
                    onChange={(e) => setFormData({ ...formData, stock: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:border-green-600"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">Description</label>
                  <textarea
                    rows="3"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:border-green-600"
                  />
                </div>
                <div className="flex gap-4 pt-4">
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-semibold transition-colors"
                  >
                    Add Product
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SellerDashboard;
