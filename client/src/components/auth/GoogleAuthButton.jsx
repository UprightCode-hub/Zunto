import React, { useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import axios from 'axios';

const GoogleAuthButton = ({ onSuccess, onError, mode = 'signup' }) => {
  const [loading, setLoading] = useState(false);

  const handleGoogleSuccess = async (credentialResponse) => {
    setLoading(true);
    
    try {
      const response = await axios.post(
        `${import.meta.env.VITE_API_URL}/api/accounts/auth/google/`,
        {
          token: credentialResponse.credential
        },
        {
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      console.log('Google authentication successful:', response.data);

      // Store tokens in localStorage (matching your AuthContext format)
      localStorage.setItem('access_token', response.data.access);
      localStorage.setItem('refresh_token', response.data.refresh);
      localStorage.setItem('token', response.data.access);
      localStorage.setItem('user', JSON.stringify(response.data.user));

      // Call success callback
      if (onSuccess) {
        onSuccess(response.data);
      } else {
        // Default: reload to trigger auth state update
        window.location.href = '/';
      }
      
    } catch (error) {
      console.error('Google authentication failed:', error.response?.data || error.message);
      
      const errorMessage = error.response?.data?.error || 
                          error.response?.data?.detail || 
                          'Google authentication failed. Please try again.';
      
      if (onError) {
        onError(errorMessage);
      } else {
        alert(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleError = () => {
    console.error('Google Login Failed');
    const errorMessage = 'Google login failed. Please try again.';
    
    if (onError) {
      onError(errorMessage);
    } else {
      alert(errorMessage);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-3.5">
        <div className="w-6 h-6 border-2 border-gray-300 border-t-[#2c77d1] rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="w-full flex justify-center">
      <GoogleLogin
        onSuccess={handleGoogleSuccess}
        onError={handleGoogleError}
        useOneTap
        text={mode === 'signin' ? 'signin_with' : 'signup_with'}
        shape="rectangular"
        theme="filled_black"
        size="large"
        width="350"
        logo_alignment="left"
      />
    </div>
  );
};

export default GoogleAuthButton;