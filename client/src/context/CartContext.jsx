/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';
import { useAuth } from './AuthContext';
import {
  getCart,
  addToCart as addToCartAPI,
  updateCartItem,
  removeFromCart,
  clearCart as clearCartAPI,
} from '../services/api';
import { PRODUCT_IMAGE_FALLBACK, getProductImage } from '../utils/product';

const CartContext = createContext();
const LOGIN_REDIRECT_STORAGE_KEY = 'zunto_post_login_redirect';

const getCurrentReturnPath = () => {
  if (typeof window === 'undefined') {
    return '/';
  }

  const path = `${window.location.pathname}${window.location.search}${window.location.hash}`;
  return path && path !== '/login' ? path : '/';
};

const redirectGuestToLogin = () => {
  if (typeof window === 'undefined') {
    return;
  }

  const returnPath = getCurrentReturnPath();
  localStorage.setItem(LOGIN_REDIRECT_STORAGE_KEY, returnPath);
  window.location.assign(`/login?next=${encodeURIComponent(returnPath)}`);
};

const normalizeCartItem = (item) => {
  const product = item?.product || {};
  const unitPrice = Number(item?.price_at_addition ?? product?.price ?? 0);
  const quantity = Number(item?.quantity ?? 0);
  const fallbackTotal = unitPrice * quantity;

  return {
    ...item,
    product,
    product_id: item?.product_id || product?.id,
    product_name: product?.title || item?.product_name || 'Untitled product',
    product_description: product?.description || item?.product_description || '',
    product_image: getProductImage(product, item?.product_image || PRODUCT_IMAGE_FALLBACK),
    seller_name: product?.seller_name || item?.seller_name || '',
    seller_commerce_mode: product?.seller_commerce_mode || item?.seller_commerce_mode || 'direct',
    seller_profile_status: product?.seller_profile_status || item?.seller_profile_status || null,
    is_managed_commerce_eligible: Boolean(product?.is_managed_commerce_eligible ?? item?.is_managed_commerce_eligible),
    unit_price: unitPrice,
    total_price: Number(item?.total_price ?? fallbackTotal),
    quantity,
  };
};

export const useCart = () => {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error('useCart must be used within CartProvider');
  }
  return context;
};

export const CartProvider = ({ children }) => {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const [cart, setCart] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchCart = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await getCart();
      const normalizedItems = (data?.items || []).map(normalizeCartItem);
      setCart(normalizedItems);
    } catch (fetchError) {
      console.error('Error fetching cart:', fetchError);
      setError(fetchError.message || 'Unable to load cart.');
    } finally {
      setLoading(false);
    }
  };

  const addToCart = async (productId, quantity = 1) => {
    if (!isAuthenticated) {
      setError('Please sign in to add items to cart.');
      redirectGuestToLogin();
      const authError = new Error('Please sign in to add items to cart.');
      authError.code = 'AUTH_REQUIRED';
      throw authError;
    }

    try {
      setError('');
      await addToCartAPI(productId, quantity);
      await fetchCart();
    } catch (addError) {
      console.error('Error adding to cart:', addError);
      setError(addError.message || 'Unable to add item to cart.');
      throw addError;
    }
  };

  const updateQuantity = async (itemId, quantity) => {
    try {
      setError('');
      await updateCartItem(itemId, quantity);
      await fetchCart();
    } catch (updateError) {
      console.error('Error updating cart:', updateError);
      setError(updateError.message || 'Unable to update cart quantity.');
      throw updateError;
    }
  };

  const removeItem = async (itemId) => {
    try {
      setError('');
      await removeFromCart(itemId);
      await fetchCart();
    } catch (removeError) {
      console.error('Error removing from cart:', removeError);
      setError(removeError.message || 'Unable to remove item from cart.');
      throw removeError;
    }
  };

  const clearCart = async () => {
    try {
      setError('');
      await clearCartAPI();
      await fetchCart();
    } catch (clearError) {
      console.error('Error clearing cart:', clearError);
      setError(clearError.message || 'Unable to clear cart.');
      throw clearError;
    }
  };

  const cartCount = useMemo(
    () => cart.reduce((total, item) => total + Number(item.quantity || 0), 0),
    [cart],
  );

  const cartTotal = useMemo(
    () => cart.reduce((total, item) => total + Number(item.total_price || 0), 0),
    [cart],
  );

  useEffect(() => {
    if (authLoading) {
      return;
    }

    if (isAuthenticated) {
      fetchCart();
      return;
    }

    setCart([]);
    setError('');
  }, [authLoading, isAuthenticated]);

  return (
    <CartContext.Provider
      value={{
        cart,
        loading,
        error,
        addToCart,
        updateQuantity,
        removeItem,
        clearCart,
        fetchCart,
        cartCount,
        cartTotal,
      }}
    >
      {children}
    </CartContext.Provider>
  );
};
