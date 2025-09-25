/**
 * API client configuration with authentication interceptors
 */

import axios, { AxiosError } from 'axios';
import type { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios';
import { API_BASE_URL, API_TIMEOUT, DEFAULT_HEADERS, AUTH_ENDPOINTS, ERROR_MESSAGES } from '../utils/constants';
import { TokenStorage } from '../utils/tokenStorage';
import type { ApiError, RefreshTokenResponse } from '../types/auth.types';

/**
 * Create axios instance with default configuration
 */
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: DEFAULT_HEADERS,
});

/**
 * Flag to prevent multiple refresh token requests
 */
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: any) => void;
}> = [];

/**
 * Process queued requests after token refresh
 */
const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error);
    } else {
      resolve(token!);
    }
  });

  failedQueue = [];
};

/**
 * Request interceptor to add authentication token
 */
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = TokenStorage.getAccessToken();

    if (token && !TokenStorage.isTokenExpired(token)) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

/**
 * Response interceptor to handle token refresh and errors
 */
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // Handle 401 Unauthorized errors
    if (error.response?.status === 401 && !originalRequest._retry) {
      const refreshToken = TokenStorage.getRefreshToken();

      if (!refreshToken) {
        // No refresh token available, redirect to login
        TokenStorage.clearAuthData();
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }

      if (isRefreshing) {
        // Token refresh is already in progress, queue this request
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
            }
            return apiClient(originalRequest);
          })
          .catch((err) => {
            return Promise.reject(err);
          });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        // Attempt to refresh the token
        const response = await axios.post<RefreshTokenResponse>(
          `${API_BASE_URL}${AUTH_ENDPOINTS.REFRESH}`,
          { refresh_token: refreshToken },
          { headers: DEFAULT_HEADERS }
        );

        const { access_token, refresh_token: newRefreshToken, user } = response.data;

        // Store the new tokens
        TokenStorage.setAccessToken(access_token);
        TokenStorage.setRefreshToken(newRefreshToken);
        TokenStorage.setUserData(user);

        // Process the queued requests
        processQueue(null, access_token);

        // Retry the original request with new token
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
        }

        return apiClient(originalRequest);
      } catch (refreshError) {
        // Refresh failed, clear auth data and redirect to login
        processQueue(refreshError, null);
        TokenStorage.clearAuthData();

        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }

        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    // Handle other errors
    return Promise.reject(formatApiError(error));
  }
);

/**
 * Format API errors into a consistent structure
 */
const formatApiError = (error: AxiosError): ApiError => {
  if (!error.response) {
    // Network error
    return {
      message: ERROR_MESSAGES.NETWORK_ERROR,
      status: 0,
    };
  }

  const { status, data } = error.response;
  let message: string;

  switch (status) {
    case 400:
      message = (data as any)?.detail || (data as any)?.message || 'Bad request';
      break;
    case 401:
      message = ERROR_MESSAGES.INVALID_CREDENTIALS;
      break;
    case 403:
      message = ERROR_MESSAGES.UNAUTHORIZED;
      break;
    case 404:
      message = 'Resource not found';
      break;
    case 500:
      message = ERROR_MESSAGES.SERVER_ERROR;
      break;
    default:
      message = ERROR_MESSAGES.UNKNOWN_ERROR;
  }

  return {
    message,
    status,
    detail: (data as any)?.detail || (data as any)?.message,
  };
};

/**
 * Generic API request wrapper with error handling
 */
export const apiRequest = async <T>(
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH',
  url: string,
  data?: any,
  config?: any
): Promise<T> => {
  try {
    const response = await apiClient.request<T>({
      method,
      url,
      data,
      ...config,
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};

/**
 * Convenience methods for common HTTP operations
 */
export const api = {
  get: <T>(url: string, config?: any) => apiRequest<T>('GET', url, undefined, config),
  post: <T>(url: string, data?: any, config?: any) => apiRequest<T>('POST', url, data, config),
  put: <T>(url: string, data?: any, config?: any) => apiRequest<T>('PUT', url, data, config),
  patch: <T>(url: string, data?: any, config?: any) => apiRequest<T>('PATCH', url, data, config),
  delete: <T>(url: string, config?: any) => apiRequest<T>('DELETE', url, undefined, config),
};

export default apiClient;