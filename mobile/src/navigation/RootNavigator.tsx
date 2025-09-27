import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useAuthStore } from '@/store/authStore';
import AuthNavigator from './AuthNavigator';
import StudentNavigator from './StudentNavigator';
import TeacherNavigator from './TeacherNavigator';
import RoleSwitcherScreen from '@/screens/auth/RoleSwitcherScreen';

export type RootStackParamList = {
  Auth: undefined;
  Student: undefined;
  Teacher: undefined;
  RoleSwitcher: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

const RootNavigator: React.FC = () => {
  const { isAuthenticated, user, selectedRole } = useAuthStore();

  const getMainNavigator = () => {
    if (!isAuthenticated || !user) {
      return <Stack.Screen name="Auth" component={AuthNavigator} options={{ headerShown: false }} />;
    }

    // MA Teacher needs to select a role first
    if (user.role === 'ma_teacher' && !selectedRole) {
      return <Stack.Screen name="RoleSwitcher" component={RoleSwitcherScreen} options={{ headerShown: false }} />;
    }

    // Route based on role
    const effectiveRole = user.role === 'ma_teacher' ? selectedRole : user.role;

    if (effectiveRole === 'teacher' || effectiveRole === 'admin') {
      return <Stack.Screen name="Teacher" component={TeacherNavigator} options={{ headerShown: false }} />;
    }

    // Default to student view
    return <Stack.Screen name="Student" component={StudentNavigator} options={{ headerShown: false }} />;
  };

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {getMainNavigator()}
      </Stack.Navigator>
    </NavigationContainer>
  );
};

export default RootNavigator;