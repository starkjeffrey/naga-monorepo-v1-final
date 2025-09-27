import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { useTheme } from 'react-native-paper';

// Student Screens
import StudentDashboardScreen from '@/screens/student/StudentDashboardScreen';
import AttendanceScreen from '@/screens/student/AttendanceScreen';
import GradesScreen from '@/screens/student/GradesScreen';
import ScheduleScreen from '@/screens/student/ScheduleScreen';
import ProfileScreen from '@/screens/student/ProfileScreen';
import IDCardScreen from '@/screens/student/IDCardScreen';
import PermissionScreen from '@/screens/student/PermissionScreen';
import ProfilePhotoScreen from '@/screens/student/ProfilePhotoScreen';
import FinancesScreen from '@/screens/student/FinancesScreen';
import AnnouncementsScreen from '@/screens/student/AnnouncementsScreen';
import MessagesScreen from '@/screens/student/MessagesScreen';

export type StudentTabParamList = {
  Dashboard: undefined;
  Attendance: undefined;
  Schedule: undefined;
  Grades: undefined;
  More: undefined;
};

export type StudentStackParamList = {
  TabNavigator: undefined;
  IDCard: undefined;
  Permission: undefined;
  ProfilePhoto: undefined;
  Finances: undefined;
  Announcements: undefined;
  Messages: undefined;
  Profile: undefined;
};

const Tab = createBottomTabNavigator<StudentTabParamList>();
const Stack = createNativeStackNavigator<StudentStackParamList>();

const StudentTabNavigator: React.FC = () => {
  const theme = useTheme();

  return (
    <Tab.Navigator
      screenOptions={{
        tabBarActiveTintColor: theme.colors.primary,
        tabBarInactiveTintColor: '#666',
        tabBarStyle: {
          borderTopWidth: 1,
          borderTopColor: '#e0e0e0',
          paddingBottom: 5,
          height: 60,
        },
        tabBarLabelStyle: {
          fontSize: 12,
        },
        headerShown: false,
      }}
    >
      <Tab.Screen
        name="Dashboard"
        component={StudentDashboardScreen}
        options={{
          tabBarLabel: 'Home',
          tabBarIcon: ({ color, size }) => (
            <Icon name="home" color={color} size={size} />
          ),
        }}
      />
      <Tab.Screen
        name="Attendance"
        component={AttendanceScreen}
        options={{
          tabBarIcon: ({ color, size }) => (
            <Icon name="calendar-check" color={color} size={size} />
          ),
        }}
      />
      <Tab.Screen
        name="Schedule"
        component={ScheduleScreen}
        options={{
          tabBarIcon: ({ color, size }) => (
            <Icon name="timetable" color={color} size={size} />
          ),
        }}
      />
      <Tab.Screen
        name="Grades"
        component={GradesScreen}
        options={{
          tabBarIcon: ({ color, size }) => (
            <Icon name="school" color={color} size={size} />
          ),
        }}
      />
      <Tab.Screen
        name="More"
        component={ProfileScreen}
        options={{
          tabBarIcon: ({ color, size }) => (
            <Icon name="dots-horizontal" color={color} size={size} />
          ),
        }}
      />
    </Tab.Navigator>
  );
};

const StudentNavigator: React.FC = () => {
  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
      }}
    >
      <Stack.Screen name="TabNavigator" component={StudentTabNavigator} />
      <Stack.Screen
        name="IDCard"
        component={IDCardScreen}
        options={{
          headerShown: true,
          title: 'Student ID Card',
          headerBackTitle: 'Back',
        }}
      />
      <Stack.Screen
        name="Permission"
        component={PermissionScreen}
        options={{
          headerShown: true,
          title: 'Request Permission',
          headerBackTitle: 'Back',
        }}
      />
      <Stack.Screen
        name="ProfilePhoto"
        component={ProfilePhotoScreen}
        options={{
          headerShown: true,
          title: 'Update Photo',
          headerBackTitle: 'Back',
        }}
      />
      <Stack.Screen
        name="Finances"
        component={FinancesScreen}
        options={{
          headerShown: true,
          title: 'Financial Balance',
          headerBackTitle: 'Back',
        }}
      />
      <Stack.Screen
        name="Announcements"
        component={AnnouncementsScreen}
        options={{
          headerShown: true,
          title: 'Announcements',
          headerBackTitle: 'Back',
        }}
      />
      <Stack.Screen
        name="Messages"
        component={MessagesScreen}
        options={{
          headerShown: true,
          title: 'Messages',
          headerBackTitle: 'Back',
        }}
      />
      <Stack.Screen
        name="Profile"
        component={ProfileScreen}
        options={{
          headerShown: true,
          title: 'My Profile',
          headerBackTitle: 'Back',
        }}
      />
    </Stack.Navigator>
  );
};

export default StudentNavigator;