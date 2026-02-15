// client/src/context/AuthContext.jsx
import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  login as loginAPI,
  register as registerAPI,
  verifyRegistration as verifyRegistrationAPI,
  resendRegistrationCode as resendRegistrationCodeAPI,
  logout as logoutAPI,
  getUserProfile,
} from '../services/api';

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

  useEffect(() => {
    const accessToken = localStorage.getItem('access_token');
    const userData = localStorage.getItem('user');

    if (accessToken) {
      setToken(accessToken);
      if (userData) {
        setUser(JSON.parse(userData));
      } else {
        fetchUserProfile();
      }
    }

    setLoading(false);
  }, []);

  const fetchUserProfile = async () => {
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

      localStorage.setItem('access_token', data.access);
      localStorage.setItem('refresh_token', data.refresh);
      localStorage.setItem('token', data.access);

      const userData = data.user || { email };
      localStorage.setItem('user', JSON.stringify(userData));

      setToken(data.access);
      setUser(userData);

      return { success: true, data };
    } catch (error) {
      const errorData = error.data;
      let errorMessage = 'Login failed. Please try again.';

      if (errorData) {
        if (errorData.detail) {
          errorMessage = errorData.detail;
        } else if (errorData.non_field_errors) {
          errorMessage = Array.isArray(errorData.non_field_errors)
            ? errorData.non_field_errors[0]
            : errorData.non_field_errors;
        } else if (errorData.error) {
          errorMessage = errorData.error;
        }
      }

      return { success: false, error: errorMessage };
    }
  };

  const register = async (userData) => {
    try {
      const data = await registerAPI(userData);
      return { success: true, data };
    } catch (error) {
      const errorData = error.data;
      let errorMessage = 'Registration failed. Please try again.';

      if (errorData) {
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
        } else if (errorData.error) {
          errorMessage = errorData.error;
        } else if (errorData.non_field_errors) {
          errorMessage = Array.isArray(errorData.non_field_errors)
            ? errorData.non_field_errors[0]
            : errorData.non_field_errors;
        }
      }

      return { success: false, error: errorMessage };
    }
  };

  const verifyRegistration = async (email, code) => {
    try {
      const data = await verifyRegistrationAPI(email, code);

      if (!data.access || !data.refresh || !data.user) {
        throw new Error('Invalid response from server during verification');
      }

      localStorage.setItem('access_token', data.access);
      localStorage.setItem('refresh_token', data.refresh);
      localStorage.setItem('token', data.access);
      localStorage.setItem('user', JSON.stringify(data.user));

      setToken(data.access);
      setUser(data.user);

      return { success: true, data };
    } catch (error) {
      const errorData = error.data;
      const errorMessage = errorData?.error || errorData?.detail || error.message || 'Verification failed.';
      return { success: false, error: errorMessage };
    }
  };

  const resendRegistrationCode = async (email) => {
    try {
      const data = await resendRegistrationCodeAPI(email);
      return { success: true, data };
    } catch (error) {
      const errorData = error.data;
      const errorMessage = errorData?.error || errorData?.detail || error.message || 'Failed to resend verification code.';
      return { success: false, error: errorMessage };
    }
  };

  const googleAuth = async (googleData) => {
    try {
      if (!googleData.access || !googleData.refresh || !googleData.user) {
        throw new Error('Invalid response from Google authentication');
      }

      localStorage.setItem('access_token', googleData.access);
      localStorage.setItem('refresh_token', googleData.refresh);
      localStorage.setItem('token', googleData.access);
      localStorage.setItem('user', JSON.stringify(googleData.user));

      setToken(googleData.access);
      setUser(googleData.user);

      return { success: true, data: googleData };
    } catch (error) {
      console.error('Google auth state update failed:', error);
      return {
        success: false,
        error: error.message || 'Failed to update authentication state',
      };
    }
  };

  const logout = async () => {
    try {
      const refresh = localStorage.getItem('refresh_token');
      await logoutAPI(refresh);
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
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
    verifyRegistration,
    resendRegistrationCode,
    googleAuth,
    logout,
    isAuthenticated: !!token,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
