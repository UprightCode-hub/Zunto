import React, { createContext, useContext, useState, useEffect } from 'react';
import { login as loginAPI, register as registerAPI, logout as logoutAPI, getUserProfile } from '../services/api';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(null);

  // Initialize from localStorage on mount
  useEffect(() => {
    const accessToken = localStorage.getItem('access_token');
    const refreshToken = localStorage.getItem('refresh_token');
    const userData = localStorage.getItem('user');
    
    if (accessToken) {
      setToken(accessToken);
      if (userData) {
        setUser(JSON.parse(userData));
      } else {
        // Try to fetch user profile if we have token but no user data
        fetchUserProfile(accessToken);
      }
    }
    setLoading(false);
  }, []);

  const fetchUserProfile = async (accessToken) => {
    try {
      const data = await getUserProfile();
      localStorage.setItem('user', JSON.stringify(data));
      setUser(data);
    } catch (error) {
      console.error('Failed to fetch user profile:', error);
      logout();
    }
  };

  const login = async (email, password) => {
    try {
      const data = await loginAPI(email, password);
      
      // Save tokens (JWT format: {access, refresh})
      localStorage.setItem('access_token', data.access);
      localStorage.setItem('refresh_token', data.refresh);
      localStorage.setItem('token', data.access); // For backwards compatibility
      
      // Save user data
      const userData = data.user || { email };
      localStorage.setItem('user', JSON.stringify(userData));
      
      setToken(data.access);
      setUser(userData);
      
      return { success: true, data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  };

  const register = async (userData) => {
    try {
      const data = await registerAPI(userData);
      
      // Save tokens
      localStorage.setItem('access_token', data.access);
      localStorage.setItem('refresh_token', data.refresh);
      localStorage.setItem('token', data.access);
      
      // Save user data
      const userInfo = data.user || userData;
      localStorage.setItem('user', JSON.stringify(userInfo));
      
      setToken(data.access);
      setUser(userInfo);
      
      return { success: true, data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  };

  const logout = async () => {
    try {
      const refresh = localStorage.getItem('refresh_token');
      await logoutAPI(refresh);
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear local storage
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      
      setUser(null);
      setToken(null);
    }
  };

  const value = {
    user,
    token,
    loading,
    login,
    register,
    logout,
    isAuthenticated: !!token,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
