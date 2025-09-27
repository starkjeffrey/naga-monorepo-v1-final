module.exports = {
  preset: 'react-native',

  // Module resolution
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json'],

  // Transform files
  transform: {
    '^.+\\.(ts|tsx)$': 'babel-jest',
    '^.+\\.(js|jsx)$': 'babel-jest',
  },

  // Test patterns
  testMatch: [
    '**/__tests__/**/*.(ts|tsx|js|jsx)',
    '**/*.(test|spec).(ts|tsx|js|jsx)',
  ],

  // Setup files
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],

  // Module name mapping
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
  },

  // Ignore patterns
  testPathIgnorePatterns: [
    '<rootDir>/node_modules/',
    '<rootDir>/android/',
    '<rootDir>/ios/',
  ],

  // Coverage configuration
  collectCoverageFrom: [
    'src/**/*.{ts,tsx,js,jsx}',
    '!src/**/*.d.ts',
    '!src/**/*.stories.{ts,tsx,js,jsx}',
    '!src/**/index.{ts,tsx,js,jsx}',
  ],

  // Environment
  testEnvironment: 'jsdom',

  // Transformers to ignore
  transformIgnorePatterns: [
    'node_modules/(?!(react-native|@react-native|react-native-vector-icons|react-native-paper|react-native-reanimated)/)',
  ],
};