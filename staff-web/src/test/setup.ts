/**
 * Vitest setup file for React Testing Library and Jest DOM
 */

import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, beforeAll, afterAll, vi } from 'vitest';
import { server } from './mocks/server';

// Setup MSW server
beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' });
});

// Clean up after each test
afterEach(() => {
  cleanup();
  server.resetHandlers();
  // Clear all mocks
  vi.clearAllMocks();
  // Clear localStorage and sessionStorage
  window.localStorage.clear();
  window.sessionStorage.clear();
});

// Close server after all tests
afterAll(() => {
  server.close();
});

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock IntersectionObserver
class MockIntersectionObserver implements IntersectionObserver {
  readonly root: Element | null = null;
  readonly rootMargin: string = '';
  readonly thresholds: ReadonlyArray<number> = [];

  constructor(_callback: IntersectionObserverCallback) {
    // Mock implementation - callback is intentionally unused
  }

  disconnect(): void {
    // Mock implementation
  }

  observe(): void {
    // Mock implementation
  }

  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }

  unobserve(): void {
    // Mock implementation
  }
}

Object.defineProperty(window, 'IntersectionObserver', {
  writable: true,
  configurable: true,
  value: MockIntersectionObserver,
});

Object.defineProperty(global, 'IntersectionObserver', {
  writable: true,
  configurable: true,
  value: MockIntersectionObserver,
});

// Mock ResizeObserver
class MockResizeObserver implements ResizeObserver {
  constructor(_callback: ResizeObserverCallback) {
    // Mock implementation - callback is intentionally unused
  }

  disconnect(): void {
    // Mock implementation
  }

  observe(): void {
    // Mock implementation
  }

  unobserve(): void {
    // Mock implementation
  }
}

Object.defineProperty(window, 'ResizeObserver', {
  writable: true,
  configurable: true,
  value: MockResizeObserver,
});

// Mock scrollTo
Object.defineProperty(window, 'scrollTo', {
  writable: true,
  value: vi.fn(),
});

// Mock console methods to avoid noise in tests
global.console = {
  ...console,
  // Uncomment to ignore specific console methods
  // log: vi.fn(),
  // warn: vi.fn(),
  // error: vi.fn(),
};

// Set up DOM environment
Object.defineProperty(document, 'getElementById', {
  writable: true,
  value: vi.fn((id: string) => {
    // Create a mock element for common IDs
    if (id === 'email' || id === 'password') {
      const mockElement = document.createElement('input');
      mockElement.id = id;
      mockElement.focus = vi.fn();
      return mockElement;
    }
    return null;
  }),
});