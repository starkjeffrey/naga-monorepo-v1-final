/**
 * Custom hook for managing axios interceptors and API error handling
 */

import { useEffect, useRef } from 'react';
import { AxiosError } from 'axios';
import type { AxiosResponse } from 'axios';
import apiClient from '../services/api';
import { useAuthStore } from '../store/authStore';
import { ERROR_MESSAGES } from '../utils/constants';

/**
 * Hook to set up axios interceptors for authentication and error handling
 */
export const useAxiosInterceptor = () => {
  const { logout, setError } = useAuthStore();
  const interceptorId = useRef<number | null>(null);

  useEffect(() => {
    // Set up response interceptor for global error handling
    const responseInterceptor = apiClient.interceptors.response.use(
      (response: AxiosResponse) => {
        // Clear any existing errors on successful requests
        setError(null);
        return response;
      },
      (error: AxiosError) => {
        // Handle global errors
        if (error.response?.status === 401) {
          // Unauthorized - token is invalid or expired
          // The API client will handle token refresh automatically
          // If refresh fails, user will be logged out
          return Promise.reject(error);
        }

        if (error.response?.status === 403) {
          // Forbidden - user doesn't have permission
          setError(ERROR_MESSAGES.UNAUTHORIZED);
          return Promise.reject(error);
        }

        if (error.response && error.response.status >= 500) {
          // Server error
          setError(ERROR_MESSAGES.SERVER_ERROR);
          return Promise.reject(error);
        }

        if (!error.response) {
          // Network error
          setError(ERROR_MESSAGES.NETWORK_ERROR);
          return Promise.reject(error);
        }

        // Let other errors pass through
        return Promise.reject(error);
      }
    );

    interceptorId.current = responseInterceptor;

    // Cleanup interceptor on unmount
    return () => {
      if (interceptorId.current !== null) {
        apiClient.interceptors.response.eject(interceptorId.current);
      }
    };
  }, [logout, setError]);

  return null; // This hook doesn't return anything
};

/**
 * Hook for handling API loading states
 */
export const useApiLoading = () => {
  const { isLoading, setLoading } = useAuthStore();

  const withLoading = async <T>(apiCall: Promise<T>): Promise<T> => {
    try {
      setLoading(true);
      const result = await apiCall;
      return result;
    } finally {
      setLoading(false);
    }
  };

  return {
    isLoading,
    withLoading,
  };
};

/**
 * Hook for handling API errors
 */
export const useApiError = () => {
  const { error, setError, clearError } = useAuthStore();

  const handleError = (error: any) => {
    if (error?.message) {
      setError(error.message);
    } else if (typeof error === 'string') {
      setError(error);
    } else {
      setError(ERROR_MESSAGES.UNKNOWN_ERROR);
    }
  };

  return {
    error,
    setError,
    clearError,
    handleError,
  };
};

export default useAxiosInterceptor;