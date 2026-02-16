const API_BASE_URL = import.meta.env.VITE_API_BASE || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const parseResponse = async (response) => {
  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return response.json();
  }

  const text = await response.text();
  return text ? { detail: text } : {};
};

const shouldSkipRefresh = (endpoint) => (
  endpoint.includes('/api/accounts/login/')
  || endpoint.includes('/api/accounts/token/refresh/')
  || endpoint.includes('/api/accounts/register/')
);

const performTokenRefresh = async () => {
  const refresh = localStorage.getItem('refresh_token');
  if (!refresh) {
    return null;
  }

  const response = await fetch(`${API_BASE_URL}/api/accounts/token/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  });

  if (!response.ok) {
    return null;
  }

  const data = await parseResponse(response);
  if (!data?.access) {
    return null;
  }

  localStorage.setItem('access_token', data.access);
  localStorage.setItem('token', data.access);
  return data.access;
};

const buildHeaders = (options = {}, accessToken = null) => {
  const isForm = options.body instanceof FormData;
  const defaultHeaders = isForm ? {} : { 'Content-Type': 'application/json' };
  const headers = {
    ...defaultHeaders,
    ...(accessToken && { Authorization: `Bearer ${accessToken}` }),
    ...options.headers,
  };

  if (headers['Content-Type'] === undefined) {
    delete headers['Content-Type'];
  }

  return headers;
};

const apiCall = async (endpoint, options = {}) => {
  let accessToken = localStorage.getItem('access_token') || localStorage.getItem('token');

  const sendRequest = (token) => {
    const headers = buildHeaders(options, token);
    const config = { ...options, headers };
    return fetch(`${API_BASE_URL}${endpoint}`, config);
  };

  try {
    let response = await sendRequest(accessToken);

    if (response.status === 401 && !shouldSkipRefresh(endpoint)) {
      const refreshedAccess = await performTokenRefresh();
      if (refreshedAccess) {
        accessToken = refreshedAccess;
        response = await sendRequest(accessToken);
      }
    }

    const data = await parseResponse(response);

    if (!response.ok) {
      if (response.status === 401) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('token');
        localStorage.removeItem('user');
      }

      const error = new Error(data?.message || data?.detail || 'Something went wrong');
      error.status = response.status;
      error.data = data;
      throw error;
    }

    return data;
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
};

// ==========================================
// AUTHENTICATION (accounts/urls.py)
// ==========================================

export const register = (userData) => {
  return apiCall('/api/accounts/register/', {
    method: 'POST',
    body: JSON.stringify(userData),
  });
};

export const verifyRegistration = (email, code) => {
  return apiCall('/api/accounts/register/verify/', {
    method: 'POST',
    body: JSON.stringify({ email, code }),
  });
};

export const resendRegistrationCode = (email) => {
  return apiCall('/api/accounts/register/resend/', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
};

export const login = (email, password) => {
  return apiCall('/api/accounts/login/', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
};

export const logout = (refreshToken) => {
  return apiCall('/api/accounts/logout/', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
};

export const refreshToken = (refreshToken) => {
  return apiCall('/api/accounts/token/refresh/', {
    method: 'POST',
    body: JSON.stringify({ refresh: refreshToken }),
  });
};

export const getUserProfile = () => {
  return apiCall('/api/accounts/profile/', {
    method: 'GET',
  });
};

export const updateUserProfile = (userData) => {
  return apiCall('/api/accounts/profile/', {
    method: 'PUT',
    body: JSON.stringify(userData),
  });
};

export const changePassword = (passwordData) => {
  return apiCall('/api/accounts/change-password/', {
    method: 'POST',
    body: JSON.stringify(passwordData),
  });
};

export const verifyEmail = (code) => {
  return apiCall('/api/accounts/verify-email/', {
    method: 'POST',
    body: JSON.stringify({ code }),
  });
};

export const resendVerificationEmail = () => {
  return apiCall('/api/accounts/resend-verification/', {
    method: 'POST',
  });
};

export const requestPasswordReset = (email) => {
  return apiCall('/api/accounts/password-reset/request/', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
};

export const confirmPasswordReset = (data) => {
  return apiCall('/api/accounts/password-reset/confirm/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
};
// ==========================================
// MARKET / PRODUCTS (market/urls.py)
// ==========================================

export const getCategories = () => {
  return apiCall('/api/market/categories/');
};

export const getLocations = () => {
  return apiCall('/api/market/locations/');
};

export const getProducts = (params = {}) => {
  const queryString = new URLSearchParams(params).toString();
  return apiCall(`/api/market/products/?${queryString}`);
};

export const getMyProducts = () => {
  return apiCall('/api/market/products/my-products/');
};

export const getFeaturedProducts = () => {
  return apiCall('/api/market/products/featured/');
};

export const getBoostedProducts = () => {
  return apiCall('/api/market/products/boosted/');
};

export const getAdProducts = () => {
  return apiCall('/api/market/products/ads/');
};

export const getProductDetail = (slug) => {
  return apiCall(`/api/market/products/${slug}/`);
};

export const createProduct = (productData) => {
  return apiCall('/api/market/products/', {
    method: 'POST',
    body: JSON.stringify(productData),
  });
};

export const updateProduct = (slug, productData) => {
  return apiCall(`/api/market/products/${slug}/`, {
    method: 'PUT',
    body: JSON.stringify(productData),
  });
};

export const deleteProduct = (slug) => {
  return apiCall(`/api/market/products/${slug}/`, {
    method: 'DELETE',
  });
};

export const getSimilarProducts = (slug) => {
  return apiCall(`/api/market/products/${slug}/similar/`);
};

export const getProductStats = (slug) => {
  return apiCall(`/api/market/products/${slug}/stats/`);
};

export const markProductAsSold = (slug) => {
  return apiCall(`/api/market/products/${slug}/mark-sold/`, {
    method: 'POST',
  });
};

export const reactivateProduct = (slug) => {
  return apiCall(`/api/market/products/${slug}/reactivate/`, {
    method: 'POST',
  });
};

// Media Uploads
export const uploadProductImage = (slug, imageFile) => {
  const formData = new FormData();
  formData.append('image', imageFile);
  
  return apiCall(`/api/market/products/${slug}/images/`, {
    method: 'POST',
    headers: { 'Content-Type': undefined }, // Let browser set multipart/form-data
    body: formData,
  });
};

export const deleteProductImage = (slug, imageId) => {
  return apiCall(`/api/market/products/${slug}/images/${imageId}/`, {
    method: 'DELETE',
  });
};

export const uploadProductVideo = (slug, videoFile) => {
  const formData = new FormData();
  formData.append('video', videoFile);
  
  return apiCall(`/api/market/products/${slug}/videos/`, {
    method: 'POST',
    headers: { 'Content-Type': undefined },
    body: formData,
  });
};

// Favorites
export const toggleFavorite = (slug) => {
  return apiCall(`/api/market/products/${slug}/favorite/`, {
    method: 'POST',
  });
};

export const getFavorites = () => {
  return apiCall('/api/market/favorites/');
};

// Reports
export const reportProduct = (slug, reportData) => {
  return apiCall(`/api/market/products/${slug}/report/`, {
    method: 'POST',
    body: JSON.stringify(reportData),
  });
};

export const shareProduct = (slug, payload = { shared_via: 'link' }) => {
  return apiCall(`/api/market/products/${slug}/share/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
};

// ==========================================
// CART (cart/urls.py)
// ==========================================

export const getCart = () => {
  return apiCall('/api/cart/');
};

export const addToCart = (productId, quantity = 1) => {
  return apiCall('/api/cart/add/', {
    method: 'POST',
    body: JSON.stringify({ product_id: productId, quantity }),
  });
};

export const updateCartItem = (itemId, quantity) => {
  return apiCall(`/api/cart/update/${itemId}/`, {
    method: 'PUT',
    body: JSON.stringify({ quantity }),
  });
};

export const removeFromCart = (itemId) => {
  return apiCall(`/api/cart/remove/${itemId}/`, {
    method: 'DELETE',
  });
};

export const clearCart = () => {
  return apiCall('/api/cart/clear/', {
    method: 'POST', // Changed to POST based on view definition usually being POST/DELETE, check server
  });
};

// ==========================================
// ORDERS (orders/urls.py)
// ==========================================

export const checkout = (checkoutData) => {
  return apiCall('/api/orders/checkout/', {
    method: 'POST',
    body: JSON.stringify(checkoutData),
  });
};

export const getMyOrders = (params = {}) => {
  const queryString = new URLSearchParams(params).toString();
  return apiCall(`/api/orders/my-orders/?${queryString}`);
};

export const getOrderDetail = (orderNumber) => {
  return apiCall(`/api/orders/orders/${orderNumber}/`);
};

export const cancelOrder = (orderNumber) => {
  return apiCall(`/api/orders/orders/${orderNumber}/cancel/`, {
    method: 'POST',
  });
};

export const verifyPayment = (orderNumber, reference) => {
  return apiCall(`/api/orders/orders/${orderNumber}/verify-payment/`, {
    method: 'POST',
    body: JSON.stringify({ reference }),
  });
};

export const initializeOrderPayment = (orderNumber, callbackUrl = null) => {
  return apiCall(`/api/payments/initialize/${orderNumber}/`, {
    method: 'POST',
    body: JSON.stringify(callbackUrl ? { callback_url: callbackUrl } : {}),
  });
};

export const verifyOrderPaymentStatus = (orderNumber, reference = null) => {
  const queryString = reference ? `?reference=${encodeURIComponent(reference)}` : '';
  return apiCall(`/api/payments/verify/${orderNumber}/${queryString}`);
};

export const reorder = (orderNumber) => {
  return apiCall(`/api/orders/orders/${orderNumber}/reorder/`, {
    method: 'POST',
  });
};

export const getOrderStatistics = () => {
  return apiCall('/api/orders/statistics/');
};

// Seller Orders
export const getSellerOrders = (params = {}) => {
  const queryString = new URLSearchParams(params).toString();
  return apiCall(`/api/orders/seller/orders/?${queryString}`);
};

export const getSellerOrderDetail = (orderNumber) => {
  return apiCall(`/api/orders/seller/orders/${orderNumber}/`);
};

export const updateOrderItemStatus = (itemId, status) => {
  return apiCall(`/api/orders/seller/items/${itemId}/update-status/`, {
    method: 'POST', // Check if PUT or POST
    body: JSON.stringify({ status }),
  });
};

export const getSellerStatistics = () => {
  return apiCall('/api/orders/seller/statistics/');
};

// Shipping Addresses
export const getShippingAddresses = () => {
  return apiCall('/api/orders/addresses/');
};

export const createShippingAddress = (addressData) => {
  return apiCall('/api/orders/addresses/', {
    method: 'POST',
    body: JSON.stringify(addressData),
  });
};

export const getShippingAddress = (id) => {
  return apiCall(`/api/orders/addresses/${id}/`);
};

export const updateShippingAddress = (id, addressData) => {
  return apiCall(`/api/orders/addresses/${id}/`, {
    method: 'PUT',
    body: JSON.stringify(addressData),
  });
};

export const deleteShippingAddress = (id) => {
  return apiCall(`/api/orders/addresses/${id}/`, {
    method: 'DELETE',
  });
};

export const setDefaultAddress = (id) => {
  return apiCall(`/api/orders/addresses/${id}/set-default/`, {
    method: 'POST',
  });
};

// Refunds
export const requestRefund = (refundData) => {
  return apiCall('/api/orders/refunds/request/', {
    method: 'POST',
    body: JSON.stringify(refundData),
  });
};

export const getMyRefunds = () => {
  return apiCall('/api/orders/refunds/');
};

// ==========================================
// REVIEWS (reviews/urls.py)
// ==========================================

export const getProductReviews = (slug, params = {}) => {
  const queryString = new URLSearchParams(params).toString();
  return apiCall(`/api/reviews/products/${slug}/reviews/?${queryString}`);
};

export const createProductReview = (slug, reviewData) => {
  return apiCall(`/api/reviews/products/${slug}/reviews/`, {
    method: 'POST',
    body: JSON.stringify(reviewData),
  });
};

export const getProductReviewStats = (slug) => {
  return apiCall(`/api/reviews/products/${slug}/reviews/stats/`);
};

export const getProductReviewDetail = (id) => {
  return apiCall(`/api/reviews/product-reviews/${id}/`);
};

export const getMyProductReviews = () => {
  return apiCall('/api/reviews/my-product-reviews/');
};

// Seller Reviews
export const getSellerReviews = (sellerId, params = {}) => {
  const queryString = new URLSearchParams(params).toString();
  return apiCall(`/api/reviews/sellers/${sellerId}/reviews/?${queryString}`);
};

export const createSellerReview = (sellerId, reviewData) => {
  return apiCall(`/api/reviews/sellers/${sellerId}/reviews/`, {
    method: 'POST',
    body: JSON.stringify(reviewData),
  });
};

export const getSellerReviewStats = (sellerId) => {
  return apiCall(`/api/reviews/sellers/${sellerId}/reviews/stats/`);
};

// Shared Review Actions
export const updateReview = (reviewId, reviewData) => {
  // Note: This might be tricky if endpoint differs for product/seller reviews.
  // Server uses 'product-reviews/<pk>/' and 'seller-reviews/<pk>/'.
  // We need to know which type it is, or try one. 
  // For now, assuming product review as default or need separate methods.
  // Let's split them to be safe.
  return apiCall(`/api/reviews/product-reviews/${reviewId}/`, {
    method: 'PUT',
    body: JSON.stringify(reviewData),
  });
};

export const deleteReview = (reviewId) => {
  return apiCall(`/api/reviews/product-reviews/${reviewId}/`, {
    method: 'DELETE',
  });
};

export const markReviewHelpful = (reviewType, reviewId) => {
  // reviewType: 'product' or 'seller' (matches server <str:review_type>)
  return apiCall(`/api/reviews/reviews/${reviewType}/${reviewId}/helpful/`, {
    method: 'POST',
  });
};

export const reportReview = (reviewData) => {
  return apiCall('/api/reviews/reviews/flag/', {
    method: 'POST',
    body: JSON.stringify(reviewData),
  });
};

// ==========================================
// NOTIFICATIONS (notifications/urls.py)
// ==========================================

export const getNotificationPreferences = () => {
  return apiCall('/api/notifications/preferences/');
};

export const updateNotificationPreferences = (prefsData) => {
  return apiCall('/api/notifications/preferences/', {
    method: 'PUT',
    body: JSON.stringify(prefsData),
  });
};

export const getNotifications = () => {
  return apiCall('/api/notifications/');
};

export const markNotificationAsRead = (notificationId) => {
  return apiCall(`/api/notifications/${notificationId}/mark-read/`, {
    method: 'POST',
  });
};

// ==========================================
// CHAT (chat/urls.py)
// ==========================================

export const getChatRooms = () => {
  return apiCall('/chat/conversations/');
};

export const getOrCreateConversation = (productId) => {
  return apiCall('/chat/conversations/get_or_create/', {
    method: 'POST',
    body: JSON.stringify({ product_id: productId }),
  });
};

export const getChatMessages = (conversationId) => {
  return apiCall(`/chat/conversations/${conversationId}/messages/`);
};

export const getConversationWsToken = (conversationId) => {
  return apiCall(`/chat/conversations/${conversationId}/ws_token/`);
};

export const getChatWebSocketUrl = (conversationId, wsToken) => {
  const wsBase = API_BASE_URL.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:');
  return `${wsBase}/ws/chat/${conversationId}/?token=${encodeURIComponent(wsToken)}`;
};

export const sendMarketplaceChatMessage = (conversationId, content, messageType = 'text') => {
  return apiCall('/chat/messages/', {
    method: 'POST',
    body: JSON.stringify({
      conversation_id: conversationId,
      content,
      message_type: messageType,
    }),
  });
};

export const sendAssistantMessage = (message, sessionId = null, userId = null) => {
  const payload = { message };
  if (sessionId) {
    payload.session_id = sessionId;
  }
  if (userId) {
    payload.user_id = userId;
  }

  return apiCall('/assistant/api/chat/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
};

// ==========================================
// DASHBOARD (dashboard/urls.py)
// ==========================================

export const getDashboardOverview = () => apiCall('/dashboard/');
export const getDashboardAnalytics = () => apiCall('/dashboard/analytics/');
export const getDashboardSales = () => apiCall('/dashboard/sales/');

const buildDashboardQuery = ({ page, pageSize } = {}) => {
  const params = new URLSearchParams();
  if (page) {
    params.set('page', String(page));
  }
  if (pageSize) {
    params.set('page_size', String(pageSize));
  }
  const query = params.toString();
  return query ? `?${query}` : '';
};

export const getDashboardProducts = (params) => apiCall(`/dashboard/products/${buildDashboardQuery(params)}`);
export const getDashboardOrders = (params) => apiCall(`/dashboard/orders/${buildDashboardQuery(params)}`);
export const getDashboardCustomers = (params) => apiCall(`/dashboard/customers/${buildDashboardQuery(params)}`);
