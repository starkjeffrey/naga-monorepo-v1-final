import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { useTheme } from 'react-native-paper';

// Teacher Screens
import TeacherDashboardScreen from '@/screens/teacher/TeacherDashboardScreen';
import TeacherCoursesScreen from '@/screens/teacher/TeacherCoursesScreen';
import TeacherAttendanceScreen from '@/screens/teacher/TeacherAttendanceScreen';
import TeacherGradesScreen from '@/screens/teacher/TeacherGradesScreen';
import TeacherProfileScreen from '@/screens/teacher/TeacherProfileScreen';
import GenerateCodeScreen from '@/screens/teacher/GenerateCodeScreen';
import ManualAttendanceScreen from '@/screens/teacher/ManualAttendanceScreen';
import CourseDetailsScreen from '@/screens/teacher/CourseDetailsScreen';
import StudentListScreen from '@/screens/teacher/StudentListScreen';
import GradeEntryScreen from '@/screens/teacher/GradeEntryScreen';

export type TeacherTabParamList = {
  Dashboard: undefined;
  Courses: undefined;
  Attendance: undefined;
  Grades: undefined;
  Profile: undefined;
};

export type TeacherStackParamList = {
  TabNavigator: undefined;
  GenerateCode: { courseId?: string };
  ManualAttendance: { courseId?: string };
  CourseDetails: { courseId: string };
  StudentList: { courseId: string };
  GradeEntry: { courseId: string; assessmentId?: string };
};

const Tab = createBottomTabNavigator<TeacherTabParamList>();
const Stack = createNativeStackNavigator<TeacherStackParamList>();

const TeacherTabNavigator: React.FC = () => {
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
        component={TeacherDashboardScreen}
        options={{
          tabBarLabel: 'Home',
          tabBarIcon: ({ color, size }) => (
            <Icon name="home" color={color} size={size} />
          ),
        }}
      />
      <Tab.Screen
        name="Courses"
        component={TeacherCoursesScreen}
        options={{
          tabBarIcon: ({ color, size }) => (
            <Icon name="book-open-variant" color={color} size={size} />
          ),
        }}
      />
      <Tab.Screen
        name="Attendance"
        component={TeacherAttendanceScreen}
        options={{
          tabBarIcon: ({ color, size }) => (
            <Icon name="clipboard-check" color={color} size={size} />
          ),
        }}
      />
      <Tab.Screen
        name="Grades"
        component={TeacherGradesScreen}
        options={{
          tabBarIcon: ({ color, size }) => (
            <Icon name="chart-line" color={color} size={size} />
          ),
        }}
      />
      <Tab.Screen
        name="Profile"
        component={TeacherProfileScreen}
        options={{
          tabBarIcon: ({ color, size }) => (
            <Icon name="account" color={color} size={size} />
          ),
        }}
      />
    </Tab.Navigator>
  );
};

const TeacherNavigator: React.FC = () => {
  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
      }}
    >
      <Stack.Screen name="TabNavigator" component={TeacherTabNavigator} />
      <Stack.Screen
        name="GenerateCode"
        component={GenerateCodeScreen}
        options={{
          headerShown: true,
          title: 'Generate Attendance Code',
          headerBackTitle: 'Back',
        }}
      />
      <Stack.Screen
        name="ManualAttendance"
        component={ManualAttendanceScreen}
        options={{
          headerShown: true,
          title: 'Manual Attendance',
          headerBackTitle: 'Back',
        }}
      />
      <Stack.Screen
        name="CourseDetails"
        component={CourseDetailsScreen}
        options={{
          headerShown: true,
          title: 'Course Details',
          headerBackTitle: 'Back',
        }}
      />
      <Stack.Screen
        name="StudentList"
        component={StudentListScreen}
        options={{
          headerShown: true,
          title: 'Student List',
          headerBackTitle: 'Back',
        }}
      />
      <Stack.Screen
        name="GradeEntry"
        component={GradeEntryScreen}
        options={{
          headerShown: true,
          title: 'Enter Grades',
          headerBackTitle: 'Back',
        }}
      />
    </Stack.Navigator>
  );
};

export default TeacherNavigator;