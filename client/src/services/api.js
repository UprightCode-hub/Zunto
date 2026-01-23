const API_BASE_URL = 'http://localhost:8000'; // Django backend URL

// Helper function for API calls
const apiCall = async (endpoint, options = {}) => {
  const token = localStorage.getItem('token');
  
  const config = {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  };

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.message || data.detail || 'Something went wrong');
    }
    
    return data;
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
};

// ===== AUTHENTICATION APIs =====
export const register = (userData) => {
  return apiCall('/register/', {
    method: 'POST',
    body: JSON.stringify(userData),
  });
};

export const login = (email, password) => {
  return apiCall('/login/', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
};

export const logout = () => {
  return apiCall('/logout/', {
    method: 'POST',
  });
};

export const refreshToken = (refreshToken) => {
  return apiCall('/token/refresh/', {
    method: 'POST',
    body: JSON.stringify({ refresh: refreshToken }),
  });
};

export const getUserProfile = () => {
  return apiCall('/profile/', {
    method: 'GET',
  });
};

export const updateUserProfile = (userData) => {
  return apiCall('/profile/', {
    method: 'PUT',
    body: JSON.stringify(userData),
  });
};

// ===== PRODUCTS APIs =====
export const getProducts = (params = {}) => {
  const queryString = new URLSearchParams(params).toString();
  return apiCall(`/api/market/products/?${queryString}`);
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

export const getMyProducts = () => {
  return apiCall('/api/market/products/my-products/');
};

export const getFeaturedProducts = () => {
  return apiCall('/api/market/products/featured/');
};

export const getBoostedProducts = () => {
  return apiCall('/api/market/products/boosted/');
};

export const getSimilarProducts = (productSlug) => {
  return apiCall(`/api/market/products/${productSlug}/similar/`);
};

export const getProductStats = (productSlug) => {
  return apiCall(`/api/market/products/${productSlug}/stats/`);
};

export const markProductAsSold = (productSlug) => {
  return apiCall(`/api/market/products/${productSlug}/mark-sold/`, {
    method: 'POST',
  });
};

export const reactivateProduct = (productSlug) => {
  return apiCall(`/api/market/products/${productSlug}/reactivate/`, {
    method: 'POST',
  });
};

// ===== CATEGORIES & LOCATIONS APIs =====
export const getCategories = () => {
  return apiCall('/api/market/categories/');
};

export const getLocations = () => {
  return apiCall('/api/market/locations/');
};

// ===== PRODUCT MEDIA APIs =====
export const uploadProductImage = (productSlug, imageFile) => {
  const formData = new FormData();
  formData.append('image', imageFile);
  
  return apiCall(`/api/market/products/${productSlug}/images/`, {
    method: 'POST',
    headers: { 'Content-Type': undefined }, // Let browser set multipart/form-data
    body: formData,
  });
};

export const deleteProductImage = (productSlug, imageId) => {
  return apiCall(`/api/market/products/${productSlug}/images/${imageId}/`, {
    method: 'DELETE',
  });
};

export const uploadProductVideo = (productSlug, videoFile) => {
  const formData = new FormData();
  formData.append('video', videoFile);
  
  return apiCall(`/api/market/products/${productSlug}/videos/`, {
    method: 'POST',
    headers: { 'Content-Type': undefined },
    body: formData,
  });
};

// ===== FAVORITES APIs =====
export const toggleFavorite = (productSlug) => {
  return apiCall(`/api/market/products/${productSlug}/favorite/`, {
    method: 'POST',
  });
};

export const getFavorites = () => {
  return apiCall('/api/market/favorites/');
};

// ===== PRODUCT REPORTS APIs =====
export const reportProduct = (productSlug, reportData) => {
  return apiCall(`/api/market/products/${productSlug}/report/`, {
    method: 'POST',
    body: JSON.stringify(reportData),
  });
};

// ===== CART APIs =====
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
    method: 'DELETE',
  });
};

// ===== ORDERS APIs =====
export const createOrder = (orderData) => {
  return apiCall('/api/orders/', {
    method: 'POST',
    body: JSON.stringify(orderData),
  });
};

export const getOrders = (params = {}) => {
  const queryString = new URLSearchParams(params).toString();
  return apiCall(`/api/orders/?${queryString}`);
};

export const getOrderDetail = (orderId) => {
  return apiCall(`/api/orders/${orderId}/`);
};

export const updateOrderStatus = (orderId, status) => {
  return apiCall(`/api/orders/${orderId}/`, {
    method: 'PUT',
    body: JSON.stringify({ status }),
  });
};

export const cancelOrder = (orderId) => {
  return apiCall(`/api/orders/${orderId}/cancel/`, {
    method: 'POST',
  });
};

// ===== REVIEWS & RATINGS APIs =====
export const getProductReviews = (productId, params = {}) => {
  const queryString = new URLSearchParams(params).toString();
  return apiCall(`/api/reviews/product/${productId}/?${queryString}`);
};

export const createReview = (productId, reviewData) => {
  return apiCall(`/api/reviews/product/${productId}/`, {
    method: 'POST',
    body: JSON.stringify(reviewData),
  });
};

export const updateReview = (reviewId, reviewData) => {
  return apiCall(`/api/reviews/${reviewId}/`, {
    method: 'PUT',
    body: JSON.stringify(reviewData),
  });
};

export const deleteReview = (reviewId) => {
  return apiCall(`/api/reviews/${reviewId}/`, {
    method: 'DELETE',
  });
};

// ===== NOTIFICATIONS APIs =====
export const getNotifications = (params = {}) => {
  const queryString = new URLSearchParams(params).toString();
  return apiCall(`/api/notifications/?${queryString}`);
};

export const markNotificationAsRead = (notificationId) => {
  return apiCall(`/api/notifications/${notificationId}/read/`, {
    method: 'POST',
  });
};

export const deleteNotification = (notificationId) => {
  return apiCall(`/api/notifications/${notificationId}/`, {
    method: 'DELETE',
  });
};

// ===== PAYMENTS APIs =====
export const initiatePayment = (paymentData) => {
  return apiCall('/api/payments/initiate/', {
    method: 'POST',
    body: JSON.stringify(paymentData),
  });
};

export const verifyPayment = (paymentId) => {
  return apiCall(`/api/payments/verify/${paymentId}/`, {
    method: 'GET',
  });
};

// ===== CHAT APIs =====
export const getConversations = () => {
  return apiCall('/chat/conversations/');
};

export const getConversationMessages = (conversationId) => {
  return apiCall(`/chat/conversations/${conversationId}/messages/`);
};

export const sendMessage = (conversationId, message) => {
  return apiCall(`/chat/conversations/${conversationId}/messages/`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  });
};

// ===== ASSISTANT APIs =====
export const getAssistantResponse = (message, context = {}) => {
  return apiCall('/assistant/chat/', {
    method: 'POST',
    body: JSON.stringify({ message, context }),
  });
};