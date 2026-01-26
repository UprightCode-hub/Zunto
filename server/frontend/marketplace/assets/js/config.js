const API_CONFIG = {
    // Use relative URL - works with Django serving
    BASE_URL: window.location.origin,
    
    AUTH: {
        LOGIN: '/login/',
        LOGOUT: '/logout/',
        REGISTER: '/register/',
        PROFILE: '/profile/',
        CHANGE_PASSWORD: '/change-password/',
    },
    
    PRODUCTS: {
        LIST: '/api/market/products/',
        DETAIL: (slug) => `/api/market/products/${slug}/`,
        CREATE: '/api/market/products/',
        MY_PRODUCTS: '/api/market/products/my-products/',
        FAVORITE: (slug) => `/api/market/products/${slug}/favorite/`,
        CATEGORIES: '/api/market/categories/',
        FEATURED: '/api/market/products/featured/',
    },
    
    CART: {
        GET: '/api/cart/',
        ADD: '/api/cart/add/',
        UPDATE: (itemId) => `/api/cart/update/${itemId}/`,
        REMOVE: (itemId) => `/api/cart/remove/${itemId}/`,
        CLEAR: '/api/cart/clear/',
    },
    
    ORDERS: {
        CHECKOUT: '/api/orders/checkout/',
        MY_ORDERS: '/api/orders/my-orders/',
        DETAIL: (orderNumber) => `/api/orders/orders/${orderNumber}/`,
        CANCEL: (orderNumber) => `/api/orders/orders/${orderNumber}/cancel/`,
    },
    
    CHAT: {
        GET_OR_CREATE_CONVERSATION: '/chat/conversations/get_or_create/',
        MESSAGES: (conversationId) => `/chat/conversations/${conversationId}/messages/`,
        SEND_MESSAGE: '/chat/messages/',
        WEBSOCKET: (conversationId, token) => {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            return `${protocol}//${window.location.host}/ws/chat/${conversationId}/?token=${token}`;
        }
    },
    
    REVIEWS: {
        PRODUCT_REVIEWS: (slug) => `/api/reviews/products/${slug}/reviews/`,
        SELLER_REVIEWS: (sellerId) => `/api/reviews/sellers/${sellerId}/reviews/`,
    },
    
    NOTIFICATIONS: {
        PREFERENCES: '/api/notifications/preferences/',
    }
};

// Authentication utilities
function getAuthToken() {
    return localStorage.getItem('access_token');
}

function setAuthToken(access, refresh) {
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
}

function getUserData() {
    const userData = localStorage.getItem('user_data');
    return userData ? JSON.parse(userData) : null;
}

function setUserData(user) {
    localStorage.setItem('user_data', JSON.stringify(user));
}

function clearAuth() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_data');
}

function isAuthenticated() {
    return !!getAuthToken();
}

// API request wrapper
async function apiRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        }
    };
    
    if (!options.skipAuth) {
        const token = getAuthToken();
        if (token) {
            defaultOptions.headers['Authorization'] = `Bearer ${token}`;
        }
    }
    
    const mergedOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers,
        }
    };
    
    try {
        const response = await fetch(url, mergedOptions);
        
        if (response.status === 401 && !options.skipAuth) {
            clearAuth();
            window.location.href = '/marketplace/auth/login/';
        }
        
        return response;
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}