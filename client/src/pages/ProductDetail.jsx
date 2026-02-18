import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { Star, ShoppingCart, Heart, Share2, Truck, Shield, RefreshCw, Plus, Minus, MessageCircle } from 'lucide-react';
import { getProductDetail, getProductReviews, toggleFavorite, createProductReview, shareProduct, getOrCreateConversation } from '../services/api';
import { useCart } from '../context/CartContext';
import { useAuth } from '../context/AuthContext';
import { getProductImage, getProductTitle } from '../utils/product';

export default function ProductDetail() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const { addToCart } = useCart();
  const { user } = useAuth();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reviews, setReviews] = useState([]);
  const [loadingReviews, setLoadingReviews] = useState(false);
  const [quantity, setQuantity] = useState(1);
  const [selectedImage, setSelectedImage] = useState(0);
  const [addingToCart, setAddingToCart] = useState(false);
  const [isFavorite, setIsFavorite] = useState(false);
  const [showReviewForm, setShowReviewForm] = useState(false);
  const [reviewText, setReviewText] = useState('');
  const [reviewRating, setReviewRating] = useState(5);
  const [submittingReview, setSubmittingReview] = useState(false);

  useEffect(() => {
    fetchProduct();
    fetchReviews();
  }, [fetchProduct, fetchReviews]);

  const fetchProduct = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getProductDetail(slug);
      setProduct(data);
      setIsFavorite(data.is_favorited || false);
    } catch (error) {
      console.error('Error fetching product:', error);
    } finally {
      setLoading(false);
    }
  }, [slug]);

  const fetchReviews = useCallback(async () => {
    try {
      setLoadingReviews(true);
      const data = await getProductReviews(slug);
      setReviews(Array.isArray(data) ? data : data.results || []);
    } catch (error) {
      console.error('Error fetching reviews:', error);
    } finally {
      setLoadingReviews(false);
    }
  }, [slug]);

  const handleAddToCart = async () => {
    try {
      setAddingToCart(true);
      await addToCart(product.id, quantity);
      alert('Product added to cart!');
    } catch {
      alert('Failed to add to cart');
    } finally {
      setAddingToCart(false);
    }
  };

  const handleToggleFavorite = async () => {
    try {
      await toggleFavorite(slug);
      setIsFavorite(!isFavorite);
    } catch (error) {
      console.error('Error toggling favorite:', error);
    }
  };


  const handleShareProduct = async () => {
    if (!user) {
      alert('Please login to share this product');
      return;
    }

    try {
      await shareProduct(slug, { shared_via: 'link' });
      const shareUrl = `${window.location.origin}/product/${slug}`;

      if (navigator.share) {
        await navigator.share({
          title: getProductTitle(product),
          text: product.description || getProductTitle(product),
          url: shareUrl,
        });
      } else if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(shareUrl);
        alert('Product link copied to clipboard');
      } else {
        alert(shareUrl);
      }
    } catch (error) {
      console.error('Error sharing product:', error);
      alert(error?.data?.error || 'Unable to share this product');
    }
  };



  const handleMessageSeller = async () => {
    if (!user) {
      alert('Please login to message this seller');
      navigate('/login');
      return;
    }

    try {
      const result = await getOrCreateConversation(product.id);
      const conversationId = result?.conversation?.id;

      if (!conversationId) {
        throw new Error('Unable to open seller chat');
      }

      navigate(`/chat?conversation=${conversationId}`);
    } catch (error) {
      console.error('Error opening conversation:', error);
      alert(error?.data?.error || 'Unable to message seller right now');
    }
  };

  const handleSubmitReview = async () => {
    if (!user) {
      alert('Please login to submit a review');
      return;
    }
    if (!reviewText.trim()) {
      alert('Review text is required');
      return;
    }
    
    try {
      setSubmittingReview(true);
      await createProductReview(slug, {
        rating: reviewRating,
        comment: reviewText,
      });
      setReviewText('');
      setReviewRating(5);
      setShowReviewForm(false);
      fetchReviews();
      alert('Review submitted successfully!');
    } catch {
      alert('Failed to submit review');
    } finally {
      setSubmittingReview(false);
    }
  };

  const incrementQuantity = () => {
    if (product.stock > quantity) {
      setQuantity(prev => prev + 1);
    }
  };

  const decrementQuantity = () => {
    if (quantity > 1) {
      setQuantity(prev => prev - 1);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center pt-20">
        <div className="w-16 h-16 border-4 border-[#2c77d1] border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="min-h-screen flex items-center justify-center pt-20">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-4">Product not found</h2>
          <Link to="/shop" className="text-[#2c77d1] hover:text-[#9426f4]">
            Back to Shop
          </Link>
        </div>
      </div>
    );
  }

  const productTitle = getProductTitle(product);
  const images = Array.isArray(product.images) && product.images.length > 0
    ? product.images.map((image) => (typeof image === 'string' ? image : image.image)).filter(Boolean)
    : [getProductImage(product)];

  const productVideos = Array.isArray(product.videos)
    ? product.videos
      .map((video) => (typeof video === 'string' ? video : video.video))
      .filter(Boolean)
    : [];

  return (
    <div className="min-h-screen pt-20 pb-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm text-gray-400 mb-8">
          <Link to="/" className="hover:text-[#2c77d1]">Home</Link>
          <span>/</span>
          <Link to="/shop" className="hover:text-[#2c77d1]">Shop</Link>
          <span>/</span>
          <span className="text-white">{productTitle}</span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
          {/* Images */}
          <div>
            <div className="bg-gradient-to-br from-[#2c77d1]/20 to-[#9426f4]/20 rounded-2xl aspect-square mb-4 overflow-hidden">
              <img
                src={images[selectedImage] || '/placeholder.svg'}
                alt={productTitle}
                className="w-full h-full object-cover"
              />
            </div>
            {images.length > 1 && (
              <div className="grid grid-cols-4 gap-4">
                {images.map((img, idx) => (
                  <button
                    key={idx}
                    onClick={() => setSelectedImage(idx)}
                    className={`aspect-square rounded-lg overflow-hidden border-2 transition ${
                      selectedImage === idx ? 'border-[#2c77d1]' : 'border-[#2c77d1]/20'
                    }`}
                  >
                    <img src={img} alt={`${productTitle} ${idx + 1}`} className="w-full h-full object-cover" />
                  </button>
                ))}
              </div>
            )}

            {productVideos.length > 0 && (
              <div className="mt-6 rounded-2xl border border-[#2c77d1]/20 bg-[#050d1b]/60 p-4">
                <h3 className="text-lg font-semibold mb-3">Product Videos</h3>
                <div className="space-y-3">
                  {productVideos.map((videoUrl, index) => (
                    <video
                      key={videoUrl}
                      controls
                      preload="metadata"
                      className="w-full rounded-xl border border-[#2c77d1]/20 bg-black"
                      aria-label={`Product video ${index + 1}`}
                    >
                      <source src={videoUrl} type="video/mp4" />
                      Your browser does not support product video playback.
                    </video>
                  ))}
                </div>
                <p className="text-xs text-gray-400 mt-2">Sellers can upload up to 2 videos (max 20MB each).</p>
              </div>
            )}
          </div>

          {/* Product Info */}
          <div>
            {product.on_sale && (
              <span className="inline-block bg-[#9426f4] text-white text-sm px-4 py-1 rounded-full font-semibold mb-4">
                On Sale
              </span>
            )}
            <h1 className="text-4xl font-bold mb-4">{productTitle}</h1>
            
            <div className="flex items-center gap-4 mb-6">
              <div className="flex items-center gap-2">
                <div className="flex">
                  {[...Array(5)].map((_, i) => (
                    <Star
                      key={i}
                      className={`w-5 h-5 ${
                        i < Math.floor(product.rating || 4.5)
                          ? 'text-yellow-400 fill-current'
                          : 'text-gray-600'
                      }`}
                    />
                  ))}
                </div>
                <span className="text-lg">{product.rating || 4.5}</span>
              </div>
              <span className="text-gray-400">
                ({product.reviews_count || 0} reviews)
              </span>
            </div>

            <div className="flex items-center gap-4 mb-6">
              <span className="text-4xl font-bold text-[#2c77d1]">
                ${product.price}
              </span>
              {product.old_price && (
                <span className="text-2xl text-gray-400 line-through">
                  ${product.old_price}
                </span>
              )}
              {product.old_price && (
                <span className="bg-red-500/20 text-red-400 px-3 py-1 rounded-full text-sm font-semibold">
                  Save {Math.round(((product.old_price - product.price) / product.old_price) * 100)}%
                </span>
              )}
            </div>

            <p className="text-gray-300 mb-8 leading-relaxed">
              {product.description}
            </p>

            {/* Stock Status */}
            <div className="mb-6">
              {product.stock > 0 ? (
                <span className="text-green-400">✓ In Stock ({product.stock} available)</span>
              ) : (
                <span className="text-red-400">✗ Out of Stock</span>
              )}
            </div>

            {/* Quantity Selector */}
            <div className="mb-8">
              <label className="block text-sm font-medium mb-3">Quantity</label>
              <div className="flex items-center gap-4">
                <div className="flex items-center border border-[#2c77d1]/30 rounded-lg">
                  <button
                    onClick={decrementQuantity}
                    disabled={quantity <= 1}
                    className="p-3 hover:bg-[#2c77d1]/10 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Minus className="w-5 h-5" />
                  </button>
                  <span className="px-6 font-semibold">{quantity}</span>
                  <button
                    onClick={incrementQuantity}
                    disabled={quantity >= product.stock}
                    className="p-3 hover:bg-[#2c77d1]/10 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Plus className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="space-y-3 mb-8">
              <div className="flex gap-4">
                <button
                  onClick={handleAddToCart}
                  disabled={product.stock === 0 || addingToCart}
                  className="flex-1 bg-gradient-to-r from-[#2c77d1] to-[#9426f4] py-4 rounded-full font-semibold text-lg flex items-center justify-center gap-2 hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ShoppingCart className="w-5 h-5" />
                  {addingToCart ? 'Adding...' : 'Add to Cart'}
                </button>
                <button
                  onClick={handleToggleFavorite}
                  className={`p-4 border-2 rounded-full hover:bg-[#2c77d1]/10 transition ${
                    isFavorite ? 'border-red-500 bg-red-500/10' : 'border-[#2c77d1]'
                  }`}
                >
                  <Heart className={`w-6 h-6 ${isFavorite ? 'fill-red-500 text-red-500' : ''}`} />
                </button>
                <button
                  onClick={handleShareProduct}
                  className="p-4 border-2 border-[#2c77d1] rounded-full hover:bg-[#2c77d1]/10 transition"
                  title="Share product"
                >
                  <Share2 className="w-6 h-6" />
                </button>
              </div>

              <button
                onClick={handleMessageSeller}
                className="w-full py-3 px-5 rounded-full border border-[#2c77d1]/40 bg-[#2c77d1]/10 hover:bg-[#2c77d1]/20 transition flex items-center justify-center gap-2 font-semibold"
              >
                <MessageCircle className="w-5 h-5" />
                Message Seller
              </button>
            </div>

            {/* Features */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
              <div className="flex items-center gap-3 p-4 bg-[#2c77d1]/10 rounded-lg">
                <Truck className="w-6 h-6 text-[#2c77d1]" />
                <div>
                  <p className="font-semibold text-sm">Free Shipping</p>
                  <p className="text-xs text-gray-400">Orders over $50</p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-4 bg-[#2c77d1]/10 rounded-lg">
                <Shield className="w-6 h-6 text-[#2c77d1]" />
                <div>
                  <p className="font-semibold text-sm">Secure Payment</p>
                  <p className="text-xs text-gray-400">100% protected</p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-4 bg-[#2c77d1]/10 rounded-lg">
                <RefreshCw className="w-6 h-6 text-[#2c77d1]" />
                <div>
                  <p className="font-semibold text-sm">Easy Returns</p>
                  <p className="text-xs text-gray-400">30-day policy</p>
                </div>
              </div>
            </div>

            {/* Product Details */}
            <div className="border-t border-[#2c77d1]/20 pt-6">
              <h3 className="font-semibold mb-4">Product Details</h3>
              <div className="space-y-2 text-gray-300">
                <div className="flex justify-between">
                  <span className="text-gray-400">SKU:</span>
                  <span>{product.sku || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Category:</span>
                  <span>{product.category_name || 'Uncategorized'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Brand:</span>
                  <span>{product.brand || 'N/A'}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Reviews Section */}
        <div className="mt-16 border-t border-[#2c77d1]/20 pt-12">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-3xl font-bold mb-2">Customer Reviews</h2>
              <p className="text-gray-400">{reviews.length} reviews</p>
            </div>
            <button
              onClick={() => setShowReviewForm(!showReviewForm)}
              className="px-6 py-3 bg-gradient-to-r from-[#2c77d1] to-[#9426f4] rounded-full font-semibold hover:opacity-90 transition"
            >
              {showReviewForm ? 'Cancel' : 'Write Review'}
            </button>
          </div>

          {showReviewForm && (
            <div className="bg-[#1a1a1a] border border-[#2c77d1]/20 rounded-2xl p-6 mb-8">
              <h3 className="text-xl font-semibold mb-4">Write Your Review</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Rating</label>
                  <div className="flex gap-2">
                    {[1, 2, 3, 4, 5].map(star => (
                      <button
                        key={star}
                        onClick={() => setReviewRating(star)}
                        className="transition"
                      >
                        <Star
                          className={`w-8 h-8 ${
                            star <= reviewRating
                              ? 'text-yellow-400 fill-current'
                              : 'text-gray-600'
                          }`}
                        />
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Review</label>
                  <textarea
                    value={reviewText}
                    onChange={(e) => setReviewText(e.target.value)}
                    placeholder="Share your experience with this product..."
                    className="w-full bg-[#2a2a2a] border border-[#2c77d1]/20 rounded-lg p-4 focus:outline-none focus:border-[#2c77d1] text-white placeholder-gray-500 resize-none h-32"
                  />
                </div>
                <button
                  onClick={handleSubmitReview}
                  disabled={submittingReview}
                  className="w-full bg-gradient-to-r from-[#2c77d1] to-[#9426f4] py-3 rounded-lg font-semibold hover:opacity-90 transition disabled:opacity-50"
                >
                  {submittingReview ? 'Submitting...' : 'Submit Review'}
                </button>
              </div>
            </div>
          )}

          {loadingReviews ? (
            <div className="text-center py-8">
              <div className="w-8 h-8 border-2 border-[#2c77d1] border-t-transparent rounded-full animate-spin mx-auto"></div>
            </div>
          ) : reviews.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              No reviews yet. Be the first to review this product!
            </div>
          ) : (
            <div className="space-y-6">
              {reviews.map((review) => (
                <div key={review.id} className="border-b border-[#2c77d1]/20 pb-6 last:border-0">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <p className="font-semibold">{review.reviewer_name || 'Anonymous'}</p>
                      <p className="text-sm text-gray-400">
                        {new Date(review.created_at || review.date).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="flex">
                      {[...Array(5)].map((_, i) => (
                        <Star
                          key={i}
                          className={`w-4 h-4 ${
                            i < (review.rating || 0)
                              ? 'text-yellow-400 fill-current'
                              : 'text-gray-600'
                          }`}
                        />
                      ))}
                    </div>
                  </div>
                  {review.title && <h4 className="font-semibold mb-2">{review.title}</h4>}
                  <p className="text-gray-300">{review.comment || review.text}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}