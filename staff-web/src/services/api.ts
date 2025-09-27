/**
 * API Integration Services
 * Centralized API client with error handling and retry logic
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
const API_TIMEOUT = 10000; // 10 seconds
const MAX_RETRIES = 3;

// Request/Response Types
interface ApiResponse<T = any> {
  data: T;
  message?: string;
  status: 'success' | 'error';
  pagination?: {
    page: number;
    pageSize: number;
    total: number;
    totalPages: number;
  };
}

interface ApiError {
  message: string;
  code?: string;
  details?: Record<string, any>;
  status?: number;
}

// Retry configuration
interface RetryConfig {
  retries: number;
  retryDelay: number;
  retryCondition: (error: any) => boolean;
}

const defaultRetryConfig: RetryConfig = {
  retries: MAX_RETRIES,
  retryDelay: 1000,
  retryCondition: (error) => {
    return !error.response || error.response.status >= 500;
  },
};

// Create axios instance
const createApiClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: API_BASE_URL,
    timeout: API_TIMEOUT,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Request interceptor
  client.interceptors.request.use(
    (config) => {
      // Add auth token if available
      const token = localStorage.getItem('authToken');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }

      // Add request timestamp
      config.metadata = { startTime: new Date() };

      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // Response interceptor
  client.interceptors.response.use(
    (response: AxiosResponse) => {
      // Log request duration
      const endTime = new Date();
      const duration = endTime.getTime() - response.config.metadata?.startTime?.getTime();
      console.log(`API Request: ${response.config.method?.toUpperCase()} ${response.config.url} - ${duration}ms`);

      return response;
    },
    async (error) => {
      const originalRequest = error.config;

      // Handle auth errors
      if (error.response?.status === 401) {
        localStorage.removeItem('authToken');
        window.location.href = '/login';
        return Promise.reject(error);
      }

      // Retry logic
      if (!originalRequest._retry && defaultRetryConfig.retryCondition(error)) {
        originalRequest._retry = true;
        originalRequest._retryCount = (originalRequest._retryCount || 0) + 1;

        if (originalRequest._retryCount <= defaultRetryConfig.retries) {
          await new Promise(resolve =>
            setTimeout(resolve, defaultRetryConfig.retryDelay * originalRequest._retryCount)
          );
          return client(originalRequest);
        }
      }

      return Promise.reject(error);
    }
  );

  return client;
};

// API Client instance
export const apiClient = createApiClient();

// Generic API methods
export class ApiService {
  private client: AxiosInstance;

  constructor(client?: AxiosInstance) {
    this.client = client || apiClient;
  }

  async get<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    try {
      const response = await this.client.get<ApiResponse<T>>(url, config);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    try {
      const response = await this.client.post<ApiResponse<T>>(url, data, config);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    try {
      const response = await this.client.put<ApiResponse<T>>(url, data, config);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async patch<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    try {
      const response = await this.client.patch<ApiResponse<T>>(url, data, config);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    try {
      const response = await this.client.delete<ApiResponse<T>>(url, config);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  private handleError(error: any): ApiError {
    if (error.response) {
      // Server responded with error status
      return {
        message: error.response.data?.message || 'Server error occurred',
        code: error.response.data?.code,
        details: error.response.data?.details,
        status: error.response.status,
      };
    } else if (error.request) {
      // Request was made but no response
      return {
        message: 'Network error - unable to reach server',
        code: 'NETWORK_ERROR',
      };
    } else {
      // Something else happened
      return {
        message: error.message || 'An unexpected error occurred',
        code: 'UNKNOWN_ERROR',
      };
    }
  }
}

// Default API service instance
export const api = new ApiService();

// Specialized service classes
export class StudentService extends ApiService {
  async getStudents(params?: {
    page?: number;
    pageSize?: number;
    search?: string;
    status?: string;
  }) {
    return this.get('/students', { params });
  }

  async getStudent(id: string) {
    return this.get(`/students/${id}`);
  }

  async createStudent(data: any) {
    return this.post('/students', data);
  }

  async updateStudent(id: string, data: any) {
    return this.put(`/students/${id}`, data);
  }

  async deleteStudent(id: string) {
    return this.delete(`/students/${id}`);
  }

  async getStudentEnrollments(id: string) {
    return this.get(`/students/${id}/enrollments`);
  }
}

export class CourseService extends ApiService {
  async getCourses(params?: {
    page?: number;
    pageSize?: number;
    search?: string;
    department?: string;
  }) {
    return this.get('/courses', { params });
  }

  async getCourse(id: string) {
    return this.get(`/courses/${id}`);
  }

  async createCourse(data: any) {
    return this.post('/courses', data);
  }

  async updateCourse(id: string, data: any) {
    return this.put(`/courses/${id}`, data);
  }

  async deleteCourse(id: string) {
    return this.delete(`/courses/${id}`);
  }
}

export class EnrollmentService extends ApiService {
  async getEnrollments(params?: {
    page?: number;
    pageSize?: number;
    studentId?: string;
    courseId?: string;
    term?: string;
  }) {
    return this.get('/enrollments', { params });
  }

  async createEnrollment(data: any) {
    return this.post('/enrollments', data);
  }

  async updateEnrollment(id: string, data: any) {
    return this.put(`/enrollments/${id}`, data);
  }

  async deleteEnrollment(id: string) {
    return this.delete(`/enrollments/${id}`);
  }
}

export class FinanceService extends ApiService {
  async getInvoices(params?: {
    page?: number;
    pageSize?: number;
    studentId?: string;
    status?: string;
  }) {
    return this.get('/finance/invoices', { params });
  }

  async getPayments(params?: {
    page?: number;
    pageSize?: number;
    studentId?: string;
    dateFrom?: string;
    dateTo?: string;
  }) {
    return this.get('/finance/payments', { params });
  }

  async createPayment(data: any) {
    return this.post('/finance/payments', data);
  }

  async getFinancialReports(type: string, params?: any) {
    return this.get(`/finance/reports/${type}`, { params });
  }
}

export class DashboardService extends ApiService {
  async getDashboardMetrics() {
    return this.get('/dashboard/metrics');
  }

  async getStudentMetrics() {
    return this.get('/dashboard/students');
  }

  async getFinanceMetrics() {
    return this.get('/dashboard/finance');
  }

  async getAcademicMetrics() {
    return this.get('/dashboard/academic');
  }
}

// Service instances
export const studentService = new StudentService();
export const courseService = new CourseService();
export const enrollmentService = new EnrollmentService();
export const financeService = new FinanceService();
export const dashboardService = new DashboardService();

export default api;