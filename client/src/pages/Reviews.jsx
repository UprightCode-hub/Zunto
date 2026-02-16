import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { getProductReviews, getMyProductReviews, updateReview, deleteReview, getMyProducts } from '../services/api';
import { Star, Trash2, Edit2, MessageSquare } from 'lucide-react';

export default function Reviews() {
  const { user } = useAuth();
  const [reviews, setReviews] = useState([]);
  const [myProducts, setMyProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedProductSlug, setSelectedProductSlug] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [editText, setEditText] = useState('');
  const [editRating, setEditRating] = useState(5);
  const [filterRating, setFilterRating] = useState(0);
  const [activeTab, setActiveTab] = useState('browse'); // browse or my-reviews

  useEffect(() => {
    if (user?.role === 'seller') {
      fetchMyProducts();
    }
  }, [user]);

  const fetchMyProducts = async () => {
    try {
      const data = await getMyProducts();
      setMyProducts(Array.isArray(data) ? data : data.results || []);
    } catch (error) {
      console.error('Error fetching products:', error);
    }
  };

  const fetchReviews = useCallback(async () => {
    if (!selectedProductSlug && activeTab === 'browse') {
      setReviews([]);
      return;
    }

    try {
      setLoading(true);
      let data;
      if (activeTab === 'my-reviews') {
        data = await getMyProductReviews();
      } else if (selectedProductSlug) {
        data = await getProductReviews(selectedProductSlug);
      }
      setReviews(Array.isArray(data) ? data : data.results || []);
    } catch (error) {
      console.error('Error fetching reviews:', error);
      setReviews([]);
    } finally {
      setLoading(false);
    }
  }, [activeTab, selectedProductSlug]);

  useEffect(() => {
    fetchReviews();
  }, [fetchReviews]);

  const handleEditReview = (review) => {
    setEditingId(review.id);
    setEditText(review.comment || review.text || '');
    setEditRating(review.rating);
  };

  const handleSaveEdit = async (reviewId) => {
    try {
      await updateReview(reviewId, {
        rating: editRating,
        comment: editText,
      });
      setEditingId(null);
      fetchReviews();
      alert('Review updated successfully!');
    } catch {
      alert('Failed to update review');
    }
  };

  const handleDeleteReview = async (reviewId) => {
    if (!window.confirm('Are you sure you want to delete this review?')) return;
    
    try {
      await deleteReview(reviewId);
      fetchReviews();
      alert('Review deleted successfully!');
    } catch {
      alert('Failed to delete review');
    }
  };

  const filteredReviews = filterRating > 0 ? reviews.filter(r => r.rating === filterRating) : reviews;

  return (
    <div className="min-h-screen pt-20 pb-12">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Product Reviews</h1>
          <p className="text-gray-400">Browse and manage product reviews</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-4 mb-8 border-b border-[#2c77d1]/20">
          <button
            onClick={() => setActiveTab('browse')}
            className={`pb-4 px-4 font-semibold transition ${
              activeTab === 'browse'
                ? 'border-b-2 border-[#2c77d1] text-[#2c77d1]'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Browse Reviews
          </button>
          {user?.role === 'seller' && (
            <button
              onClick={() => setActiveTab('my-reviews')}
              className={`pb-4 px-4 font-semibold transition ${
                activeTab === 'my-reviews'
                  ? 'border-b-2 border-[#2c77d1] text-[#2c77d1]'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              My Reviews
            </button>
          )}
        </div>

        {/* Browse Tab */}
        {activeTab === 'browse' && (
          <div className="mb-8">
            <label className="block text-sm font-medium mb-3">Select Product</label>
            <select
              value={selectedProductSlug}
              onChange={(e) => setSelectedProductSlug(e.target.value)}
              className="w-full max-w-sm px-4 py-3 bg-[#2a2a2a] border border-[#2c77d1]/20 rounded-lg focus:outline-none focus:border-[#2c77d1] text-white"
            >
              <option value="">-- Choose a product --</option>
              {myProducts.map(product => (
                <option key={product.id} value={product.slug}>
                  {product.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Filter by Rating */}
        {reviews.length > 0 && (
          <div className="mb-6 flex gap-2 flex-wrap">
            <button
              onClick={() => setFilterRating(0)}
              className={`px-4 py-2 rounded-full transition ${
                filterRating === 0
                  ? 'bg-[#2c77d1] text-white'
                  : 'bg-[#2c77d1]/10 text-gray-300 hover:bg-[#2c77d1]/20'
              }`}
            >
              All ({reviews.length})
            </button>
            {[5, 4, 3, 2, 1].map(rating => {
              const count = reviews.filter(r => r.rating === rating).length;
              return (
                <button
                  key={rating}
                  onClick={() => setFilterRating(rating)}
                  className={`px-4 py-2 rounded-full transition ${
                    filterRating === rating
                      ? 'bg-[#2c77d1] text-white'
                      : 'bg-[#2c77d1]/10 text-gray-300 hover:bg-[#2c77d1]/20'
                  }`}
                >
                  {rating}★ ({count})
                </button>
              );
            })}
          </div>
        )}

        {/* Reviews List */}
        <div>
          {loading ? (
            <div className="flex justify-center py-12">
              <div className="w-8 h-8 border-2 border-[#2c77d1] border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : filteredReviews.length === 0 ? (
            <div className="text-center py-12 bg-[#1a1a1a] rounded-2xl border border-[#2c77d1]/20">
              <MessageSquare className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400 text-lg">
                {activeTab === 'browse' && selectedProductSlug
                  ? 'No reviews yet for this product'
                  : 'Select a product to view reviews'}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredReviews.map(review => (
                <div
                  key={review.id}
                  className="bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl p-6 hover:border-[#2c77d1]/40 transition"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <div className="flex gap-1">
                          {[...Array(5)].map((_, i) => (
                            <Star
                              key={i}
                              className={`w-4 h-4 ${
                                i < review.rating
                                  ? 'text-yellow-400 fill-current'
                                  : 'text-gray-600'
                              }`}
                            />
                          ))}
                        </div>
                        <span className="font-semibold">{review.rating}/5</span>
                      </div>
                      <p className="text-gray-400 text-sm">
                        By {review.reviewer_name || 'Anonymous'} • {new Date(review.created_at || review.date).toLocaleDateString()}
                      </p>
                    </div>
                    {activeTab === 'my-reviews' && (
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleEditReview(review)}
                          className="p-2 hover:bg-[#2c77d1]/10 rounded transition"
                        >
                          <Edit2 className="w-5 h-5 text-[#2c77d1]" />
                        </button>
                        <button
                          onClick={() => handleDeleteReview(review.id)}
                          className="p-2 hover:bg-red-500/10 rounded transition"
                        >
                          <Trash2 className="w-5 h-5 text-red-500" />
                        </button>
                      </div>
                    )}
                  </div>

                  {editingId === review.id ? (
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium mb-2">Rating</label>
                        <div className="flex gap-2">
                          {[1, 2, 3, 4, 5].map(star => (
                            <button
                              key={star}
                              onClick={() => setEditRating(star)}
                              className="transition"
                            >
                              <Star
                                className={`w-6 h-6 ${
                                  star <= editRating
                                    ? 'text-yellow-400 fill-current'
                                    : 'text-gray-600'
                                }`}
                              />
                            </button>
                          ))}
                        </div>
                      </div>
                      <textarea
                        value={editText}
                        onChange={(e) => setEditText(e.target.value)}
                        className="w-full bg-[#2a2a2a] border border-[#2c77d1]/20 rounded-lg p-4 focus:outline-none focus:border-[#2c77d1] text-white resize-none h-24"
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleSaveEdit(review.id)}
                          className="px-4 py-2 bg-[#2c77d1] rounded-lg font-semibold hover:opacity-90 transition"
                        >
                          Save
                        </button>
                        <button
                          onClick={() => setEditingId(null)}
                          className="px-4 py-2 bg-gray-600 rounded-lg font-semibold hover:opacity-90 transition"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <p className="text-gray-300 leading-relaxed">{review.comment || review.text}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
