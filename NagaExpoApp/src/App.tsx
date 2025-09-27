import React from 'react';
import { StatusBar } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PaperProvider, MD3LightTheme } from 'react-native-paper';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import ErrorBoundary from '@/components/ErrorBoundary';
import AuthNavigator from '@/navigation/AuthNavigator';
import MainNavigator from '@/navigation/MainNavigator';
import { useAuthStore } from '@/store/authStore';

// Configure React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      cacheTime: 1000 * 60 * 10, // 10 minutes
    },
  },
});

const App: React.FC = () => {
  const { isAuthenticated } = useAuthStore();

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <PaperProvider theme={MD3LightTheme}>
          <SafeAreaProvider>
            <GestureHandlerRootView style={{ flex: 1 }}>
              <StatusBar
                barStyle="dark-content"
                backgroundColor="transparent"
                translucent
              />
              <NavigationContainer>
                {isAuthenticated ? <MainNavigator /> : <AuthNavigator />}
              </NavigationContainer>
            </GestureHandlerRootView>
          </SafeAreaProvider>
        </PaperProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
};

export default App;