const API_BASE_URL = 'http://localhost:8000/api'; // Update with your Django backend URL

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
      throw new Error(data.message || 'Something went wrong');
    }
    
    return data;
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
};

// Products API
export const getProducts = (params = {}) => {
  const queryString = new URLSearchParams(params).toString();
  return apiCall(`/products/?${queryString}`);
};

export const getProductById = (id) => {
  return apiCall(`/products/${id}/`);
};

export const getCategories = () => {
  return apiCall('/categories/');
};

// Cart API
export const getCart = () => {
  return apiCall('/cart/');
};

export const addToCart = (productId, quantity = 1) => {
  return apiCall('/cart/add/', {
    method: 'POST',
    body: JSON.stringify({ product_id: productId, quantity }),
  });
};

export const updateCartItem = (itemId, quantity) => {
  return apiCall(`/cart/update/${itemId}/`, {
    method: 'PUT',
    body: JSON.stringify({ quantity }),
  });
};

export const removeFromCart = (itemId) => {
  return apiCall(`/cart/remove/${itemId}/`, {
    method: 'DELETE',
  });
};

// Auth API
export const login = (email, password) => {
  return apiCall('/auth/login/', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
};

export const signup = (userData) => {
  return apiCall('/auth/signup/', {
    method: 'POST',
    body: JSON.stringify(userData),
  });
};

export const logout = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
};

// Orders API
export const createOrder = (orderData) => {
  return apiCall('/orders/', {
    method: 'POST',
    body: JSON.stringify(orderData),
  });
};

export const getOrders = () => {
  return apiCall('/orders/');
};