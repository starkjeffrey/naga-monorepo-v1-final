import React from 'react';
import { render, screen } from '@testing-library/react-native';
import App from '../App';

// Mock navigation
jest.mock('@react-navigation/native', () => ({
  NavigationContainer: ({ children }: { children: React.ReactNode }) => children,
}));

describe('App', () => {
  it('renders without crashing', () => {
    render(<App />);
    // Basic smoke test - just ensure app renders
    expect(screen.getByTestId('app-container')).toBeDefined();
  });

  it('displays the main navigation', () => {
    render(<App />);
    // Test that navigation is present
    expect(screen.getByTestId('main-navigation')).toBeDefined();
  });
});