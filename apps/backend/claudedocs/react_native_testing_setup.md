# React Native Testing Setup - Complete Configuration

## 🎯 **Optimal Testing Stack Installed**

### Core Testing Tools
- ✅ **Jest** - Main testing framework (already included with React Native)
- ✅ **React Native Testing Library** - React-focused testing utilities
- ✅ **@testing-library/jest-native** - Custom Jest matchers for React Native
- ✅ **@testing-library/react-hooks** - Hook testing utilities
- ✅ **jest-environment-jsdom** - Browser-like test environment

### Why This Stack?
- **Jest** - Industry standard, great performance, built-in mocking
- **React Native Testing Library** - Encourages testing user behavior, not implementation
- **Better than Enzyme** - More maintainable, actively supported
- **React 18 Compatible** - Works with latest React features

## 📁 **Configuration Files Created**

### 1. Jest Configuration (`jest.config.js`)
```javascript
module.exports = {
  preset: 'react-native',
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],

  // Transform patterns for React Native modules
  transformIgnorePatterns: [
    'node_modules/(?!(react-native|@react-native|react-native-vector-icons|react-native-paper)/)',
  ],

  // Coverage collection
  collectCoverageFrom: [
    'src/**/*.{ts,tsx,js,jsx}',
    '!src/**/*.stories.{ts,tsx,js,jsx}',
  ],
};
```

### 2. Jest Setup (`jest.setup.js`)
- ✅ **React Native modules** mocked
- ✅ **AsyncStorage** mock configured
- ✅ **Navigation** mock included
- ✅ **Gesture Handler** mock setup
- ✅ **Reanimated** mock configured
- ✅ **Vector Icons** mocks included

### 3. Sample Tests Created
- ✅ `src/__tests__/App.test.tsx` - App component test
- ✅ `src/components/__tests__/Button.test.tsx` - Button component test

## 🚀 **Running Tests**

### Basic Commands
```bash
# Run all tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run tests with coverage
npm test -- --coverage

# Run specific test file
npm test -- App.test.tsx

# Run tests matching pattern
npm test -- --testNamePattern="Button"
```

### Advanced Testing Commands
```bash
# Update snapshots
npm test -- --updateSnapshot

# Run tests in specific directory
npm test -- src/components

# Verbose output
npm test -- --verbose

# Run tests once (CI mode)
npm test -- --watchAll=false
```

## 📝 **Testing Patterns & Examples**

### Component Testing
```typescript
import React from 'react';
import { render, fireEvent, screen } from '@testing-library/react-native';
import { Button } from 'react-native-paper';

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent title="Test" />);
    expect(screen.getByText('Test')).toBeDefined();
  });

  it('handles user interaction', () => {
    const mockFn = jest.fn();
    render(<Button onPress={mockFn}>Click me</Button>);

    fireEvent.press(screen.getByText('Click me'));
    expect(mockFn).toHaveBeenCalledTimes(1);
  });
});
```

### Hook Testing
```typescript
import { renderHook, act } from '@testing-library/react-hooks';
import { useCounter } from '../hooks/useCounter';

describe('useCounter', () => {
  it('should increment counter', () => {
    const { result } = renderHook(() => useCounter());

    act(() => {
      result.current.increment();
    });

    expect(result.current.count).toBe(1);
  });
});
```

### Async Testing
```typescript
import { waitFor } from '@testing-library/react-native';

test('async data loading', async () => {
  render(<AsyncComponent />);

  expect(screen.getByText('Loading...')).toBeDefined();

  await waitFor(() => {
    expect(screen.getByText('Data loaded')).toBeDefined();
  });
});
```

### Navigation Testing
```typescript
import { NavigationContainer } from '@react-navigation/native';

const renderWithNavigation = (component: React.ReactElement) => {
  return render(
    <NavigationContainer>
      {component}
    </NavigationContainer>
  );
};
```

## 🔧 **Available Jest Matchers**

### React Native Testing Library Matchers
```typescript
// Element queries
expect(screen.getByText('Hello')).toBeDefined();
expect(screen.queryByText('Not found')).toBeNull();
expect(screen.getAllByTestId('item')).toHaveLength(3);

// Custom Jest Native matchers
expect(element).toBeVisible();
expect(element).toHaveTextContent('expected text');
expect(element).toBeDisabled();
expect(element).toHaveProp('value', 'expected');
```

### Accessibility Testing
```typescript
expect(screen.getByRole('button')).toBeDefined();
expect(screen.getByLabelText('Search')).toBeDefined();
expect(element).toHaveAccessibilityValue({ text: '50%' });
```

## 📊 **Test Structure Recommendations**

### Directory Structure
```
src/
├── __tests__/           # App-level tests
├── components/
│   └── __tests__/       # Component tests
├── hooks/
│   └── __tests__/       # Hook tests
├── screens/
│   └── __tests__/       # Screen tests
└── utils/
    └── __tests__/       # Utility tests
```

### Test File Naming
- **Components**: `ComponentName.test.tsx`
- **Hooks**: `useHookName.test.ts`
- **Utils**: `utilityFunction.test.ts`
- **Screens**: `ScreenName.test.tsx`

## 🎭 **Mocking Patterns**

### API Mocking
```typescript
// Mock API calls
jest.mock('../services/api', () => ({
  fetchUser: jest.fn().mockResolvedValue({ id: 1, name: 'John' }),
}));
```

### Module Mocking
```typescript
// Mock specific modules
jest.mock('react-native-device-info', () => ({
  getVersion: () => '1.0.0',
}));
```

### State Management Mocking (Zustand)
```typescript
jest.mock('../store/useAuthStore', () => ({
  useAuthStore: jest.fn(() => ({
    user: { id: 1, name: 'Test User' },
    login: jest.fn(),
    logout: jest.fn(),
  })),
}));
```

## 🚦 **CI/CD Integration**

### Package.json Scripts
```json
{
  "scripts": {
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage",
    "test:ci": "jest --watchAll=false --coverage --testResultsProcessor=jest-junit"
  }
}
```

### Coverage Thresholds
```javascript
// In jest.config.js
coverageThreshold: {
  global: {
    branches: 80,
    functions: 80,
    lines: 80,
    statements: 80,
  },
},
```

## ⚡ **Performance Testing**

### Testing Performance
```typescript
import { measureRenders } from '@testing-library/react-native';

test('component renders efficiently', () => {
  const { rerender } = render(<MyComponent data={[]} />);

  // Measure render performance
  const measurements = measureRenders(() => {
    rerender(<MyComponent data={newData} />);
  });

  expect(measurements.averageRenderTime).toBeLessThan(16); // 60fps
});
```

## 🎯 **Testing Best Practices**

### Do's
- ✅ Test user behavior, not implementation details
- ✅ Use `data-testid` for complex queries
- ✅ Test accessibility features
- ✅ Mock external dependencies
- ✅ Write descriptive test names
- ✅ Use `screen` for queries
- ✅ Test error states and edge cases

### Don'ts
- ❌ Don't test implementation details
- ❌ Don't rely on component internal state
- ❌ Don't test third-party libraries
- ❌ Don't create overly complex test setups
- ❌ Don't ignore accessibility in tests

## 🔄 **Testing Workflow**

1. **Write failing test** - Red
2. **Make it pass** - Green
3. **Refactor** - Clean code
4. **Run full test suite** - Ensure no regressions
5. **Check coverage** - Maintain quality thresholds

## 📚 **Resources**

- [React Native Testing Library Docs](https://callstack.github.io/react-native-testing-library/)
- [Jest React Native Docs](https://jestjs.io/docs/tutorial-react-native)
- [Testing Best Practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)

---

## ✅ **Setup Complete!**

Your React Native app now has a production-ready testing environment with:
- **Jest** for test running
- **React Native Testing Library** for component testing
- **Proper mocks** for React Native modules
- **Sample tests** to get started
- **Coverage reporting** configured
- **CI-ready** configuration

Run `npm test` to start testing your React Native components!