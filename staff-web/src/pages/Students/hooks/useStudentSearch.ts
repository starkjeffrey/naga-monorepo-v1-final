/**
 * useStudentSearch Hook
 *
 * A comprehensive hook for student search functionality:
 * - Advanced filtering and sorting
 * - Voice search integration
 * - Photo-based search
 * - QR code scanning
 * - Search history management
 * - Debounced search execution
 * - Real-time suggestions
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import { message } from 'antd';
import { useDebounce } from '../../../hooks/useDebounce';
import type { Student, StudentSearchParams, StudentSearchResult } from '../types/Student';
import { studentService } from '../services/studentApi';

interface UseStudentSearchOptions {
  initialParams?: Partial<StudentSearchParams>;
  autoSearch?: boolean;
  debounceMs?: number;
  enableVoiceSearch?: boolean;
  enablePhotoSearch?: boolean;
  enableQRSearch?: boolean;
  maxSuggestions?: number;
}

interface UseStudentSearchReturn {
  // Search state
  searchParams: StudentSearchParams;
  results: StudentSearchResult;
  loading: boolean;
  error: string | null;

  // Search methods
  search: (params?: Partial<StudentSearchParams>) => Promise<void>;
  clearSearch: () => void;
  exportResults: (format: 'csv' | 'excel' | 'pdf') => Promise<void>;

  // Advanced search features
  voiceSearch: {
    isListening: boolean;
    startListening: () => void;
    stopListening: () => void;
    isSupported: boolean;
  };

  photoSearch: {
    searchByPhoto: (file: File) => Promise<void>;
    isProcessing: boolean;
  };

  qrSearch: {
    scanQR: () => Promise<void>;
    isScanning: boolean;
  };

  // Search history and suggestions
  searchHistory: StudentSearchParams[];
  suggestions: string[];
  addToHistory: (params: StudentSearchParams) => void;
  clearHistory: () => void;

  // Filter and sort utilities
  updateSearchParams: (updates: Partial<StudentSearchParams>) => void;
  resetFilters: () => void;
  applySavedSearch: (searchId: string) => void;
}

const defaultSearchParams: StudentSearchParams = {
  query: '',
  filters: {
    status: [],
    program: [],
    academicYear: [],
    enrollmentDateRange: undefined,
    gpaRange: undefined,
    hasAlerts: undefined,
  },
  sorting: {
    field: 'fullName',
    direction: 'asc',
  },
  pagination: {
    page: 1,
    pageSize: 25,
  },
};

export const useStudentSearch = (options: UseStudentSearchOptions = {}): UseStudentSearchReturn => {
  const {
    initialParams = {},
    autoSearch = true,
    debounceMs = 300,
    enableVoiceSearch = true,
    enablePhotoSearch = true,
    enableQRSearch = true,
    maxSuggestions = 10,
  } = options;

  // Search state
  const [searchParams, setSearchParams] = useState<StudentSearchParams>({
    ...defaultSearchParams,
    ...initialParams,
  });

  const [results, setResults] = useState<StudentSearchResult>({
    students: [],
    total: 0,
    page: 1,
    pageSize: 25,
    suggestions: [],
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Voice search state
  const [isListening, setIsListening] = useState(false);
  const [voiceRecognition, setVoiceRecognition] = useState<SpeechRecognition | null>(null);

  // Photo search state
  const [isPhotoProcessing, setIsPhotoProcessing] = useState(false);

  // QR search state
  const [isQRScanning, setIsQRScanning] = useState(false);

  // Search history
  const [searchHistory, setSearchHistory] = useState<StudentSearchParams[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);

  // Debounced search query
  const debouncedQuery = useDebounce(searchParams.query, debounceMs);

  // Initialize voice recognition
  useEffect(() => {
    if (enableVoiceSearch && 'webkitSpeechRecognition' in window) {
      const recognition = new (window as any).webkitSpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';

      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        updateSearchParams({ query: transcript });
        setIsListening(false);
      };

      recognition.onerror = () => {
        setIsListening(false);
        message.error('Voice recognition error');
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      setVoiceRecognition(recognition);
    }
  }, [enableVoiceSearch]);

  // Load search history from localStorage
  useEffect(() => {
    const savedHistory = localStorage.getItem('studentSearchHistory');
    if (savedHistory) {
      try {
        setSearchHistory(JSON.parse(savedHistory));
      } catch (error) {
        console.error('Failed to load search history:', error);
      }
    }
  }, []);

  // Auto-search when params change
  useEffect(() => {
    if (autoSearch && (debouncedQuery !== searchParams.query || searchParams.query === '')) {
      search();
    }
  }, [debouncedQuery, searchParams.filters, searchParams.sorting, autoSearch]);

  // Main search function
  const search = useCallback(async (newParams?: Partial<StudentSearchParams>) => {
    const finalParams = newParams ? { ...searchParams, ...newParams } : searchParams;

    setLoading(true);
    setError(null);

    try {
      const result = await studentService.searchStudents(finalParams);
      setResults(result);

      // Update suggestions
      if (result.suggestions) {
        setSuggestions(result.suggestions.slice(0, maxSuggestions));
      }

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Search failed';
      setError(errorMessage);
      message.error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [searchParams, maxSuggestions]);

  // Clear search results and reset params
  const clearSearch = useCallback(() => {
    setSearchParams(defaultSearchParams);
    setResults({
      students: [],
      total: 0,
      page: 1,
      pageSize: 25,
      suggestions: [],
    });
    setError(null);
  }, []);

  // Export search results
  const exportResults = useCallback(async (format: 'csv' | 'excel' | 'pdf') => {
    try {
      setLoading(true);
      await studentService.exportSearchResults(searchParams, format);
      message.success(`Export completed in ${format.toUpperCase()} format`);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Export failed';
      message.error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [searchParams]);

  // Voice search methods
  const startListening = useCallback(() => {
    if (voiceRecognition && !isListening) {
      setIsListening(true);
      voiceRecognition.start();
    }
  }, [voiceRecognition, isListening]);

  const stopListening = useCallback(() => {
    if (voiceRecognition && isListening) {
      voiceRecognition.stop();
      setIsListening(false);
    }
  }, [voiceRecognition, isListening]);

  // Photo search
  const searchByPhoto = useCallback(async (file: File) => {
    setIsPhotoProcessing(true);
    try {
      const result = await studentService.searchByPhoto(file);
      if (result.students.length > 0) {
        setResults(result);
        message.success(`Found ${result.students.length} potential matches`);
      } else {
        message.info('No matches found for this photo');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Photo search failed';
      message.error(errorMessage);
    } finally {
      setIsPhotoProcessing(false);
    }
  }, []);

  // QR code search
  const scanQR = useCallback(async () => {
    setIsQRScanning(true);
    try {
      // This would integrate with a QR scanner library
      const qrData = await new Promise<string>((resolve, reject) => {
        // Simulated QR scanning - replace with actual implementation
        setTimeout(() => {
          resolve('A12345678'); // Sample student ID
        }, 2000);
      });

      // Search by student ID
      await search({ query: qrData });
      message.success('Student found via QR code');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'QR scan failed';
      message.error(errorMessage);
    } finally {
      setIsQRScanning(false);
    }
  }, [search]);

  // Update search parameters
  const updateSearchParams = useCallback((updates: Partial<StudentSearchParams>) => {
    setSearchParams(prev => ({ ...prev, ...updates }));
  }, []);

  // Reset all filters
  const resetFilters = useCallback(() => {
    setSearchParams({
      ...defaultSearchParams,
      query: searchParams.query, // Keep the search query
    });
  }, [searchParams.query]);

  // Add search to history
  const addToHistory = useCallback((params: StudentSearchParams) => {
    const newHistory = [params, ...searchHistory.filter(h =>
      JSON.stringify(h) !== JSON.stringify(params)
    )].slice(0, 10); // Keep last 10 searches

    setSearchHistory(newHistory);
    localStorage.setItem('studentSearchHistory', JSON.stringify(newHistory));
  }, [searchHistory]);

  // Clear search history
  const clearHistory = useCallback(() => {
    setSearchHistory([]);
    localStorage.removeItem('studentSearchHistory');
  }, []);

  // Apply saved search
  const applySavedSearch = useCallback((searchId: string) => {
    const savedSearch = searchHistory.find(h => h.id === searchId);
    if (savedSearch) {
      setSearchParams(savedSearch);
      search(savedSearch);
    }
  }, [searchHistory, search]);

  // Computed values
  const voiceSearchSupported = useMemo(() =>
    enableVoiceSearch && 'webkitSpeechRecognition' in window,
    [enableVoiceSearch]
  );

  return {
    // Search state
    searchParams,
    results,
    loading,
    error,

    // Search methods
    search,
    clearSearch,
    exportResults,

    // Advanced search features
    voiceSearch: {
      isListening,
      startListening,
      stopListening,
      isSupported: voiceSearchSupported,
    },

    photoSearch: {
      searchByPhoto,
      isProcessing: isPhotoProcessing,
    },

    qrSearch: {
      scanQR,
      isScanning: isQRScanning,
    },

    // Search history and suggestions
    searchHistory,
    suggestions,
    addToHistory,
    clearHistory,

    // Filter and sort utilities
    updateSearchParams,
    resetFilters,
    applySavedSearch,
  };
};