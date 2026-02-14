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
      // ✅ Better error handling for login
      const errorData = error.response?.data;
      let errorMessage = 'Login failed. Please try again.';
      
      if (errorData) {
        if (errorData.detail) {
          errorMessage = errorData.detail;
        } else if (errorData.non_field_errors) {
          errorMessage = Array.isArray(errorData.non_field_errors) 
            ? errorData.non_field_errors[0] 
            : errorData.non_field_errors;
        }
      }
      
      return { success: false, error: errorMessage };
    }
  };

  const register = async (userData) => {
    try {
      const data = await registerAPI(userData);
      
      // ✅ Validate response has required data
      if (!data.access || !data.refresh || !data.user) {
        throw new Error('Invalid response from server. Please try again.');
      }
      
      // Save tokens
      localStorage.setItem('access_token', data.access);
      localStorage.setItem('refresh_token', data.refresh);
      localStorage.setItem('token', data.access);
      
      // ✅ Save user data (ONLY from server, never raw form data)
      localStorage.setItem('user', JSON.stringify(data.user));
      
      setToken(data.access);
      setUser(data.user);
      
      return { success: true, data };
    } catch (error) {
      // ✅ Extract Django's detailed error messages
      const errorData = error.response?.data;
      let errorMessage = 'Registration failed. Please try again.';
      
      if (errorData) {
        // Check for field-specific errors (Django returns these)
        if (errorData.password) {
          errorMessage = Array.isArray(errorData.password) 
            ? errorData.password[0] 
            : errorData.password;
        } else if (errorData.email) {
          errorMessage = Array.isArray(errorData.email) 
            ? errorData.email[0] 
            : errorData.email;
        } else if (errorData.first_name) {
          errorMessage = Array.isArray(errorData.first_name) 
            ? errorData.first_name[0] 
            : errorData.first_name;
        } else if (errorData.last_name) {
          errorMessage = Array.isArray(errorData.last_name) 
            ? errorData.last_name[0] 
            : errorData.last_name;
        } else if (errorData.phone) {
          errorMessage = Array.isArray(errorData.phone) 
            ? errorData.phone[0] 
            : errorData.phone;
        } else if (errorData.detail) {
          errorMessage = errorData.detail;
        } else if (errorData.message) {
          errorMessage = errorData.message;
        } else if (errorData.non_field_errors) {
          errorMessage = Array.isArray(errorData.non_field_errors) 
            ? errorData.non_field_errors[0] 
            : errorData.non_field_errors;
        }
      }
      
      return { success: false, error: errorMessage };
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