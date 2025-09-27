import React from 'react';
import { View, StyleSheet, ScrollView } from 'react-native';
import {
  Card,
  Title,
  Paragraph,
  Button,
  Chip,
  Text,
} from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';

import { useAuthStore } from '@/store/authStore';
import QuickActionButton from '@/components/QuickActionButton';

const DashboardScreen: React.FC = () => {
  const { user, logout } = useAuthStore();

  const quickActions = [
    { id: 1, title: 'View Attendance', icon: 'calendar-check', color: '#4CAF50' },
    { id: 2, title: 'Check Grades', icon: 'school', color: '#2196F3' },
    { id: 3, title: 'Schedule', icon: 'timetable', color: '#FF9800' },
    { id: 4, title: 'Finances', icon: 'cash', color: '#9C27B0' },
  ];

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.greeting}>Hello, {user?.name}</Text>
          <Text style={styles.subtitle}>Welcome back to NAGA</Text>
        </View>

        {/* Student Status */}
        <Card style={styles.statusCard}>
          <Card.Content>
            <Title>Student Status</Title>
            <View style={styles.statusRow}>
              <Chip icon="check-circle" mode="outlined" style={[styles.chip, { backgroundColor: '#E8F5E8' }]}>
                Active
              </Chip>
              <Chip icon="school" mode="outlined" style={styles.chip}>
                {user?.role === 'student' ? 'Student' : 'Teacher'}
              </Chip>
            </View>
          </Card.Content>
        </Card>

        {/* Quick Actions */}
        <Card style={styles.card}>
          <Card.Content>
            <Title>Quick Actions</Title>
            <View style={styles.actionsGrid}>
              {quickActions.map((action) => (
                <QuickActionButton
                  key={action.id}
                  title={action.title}
                  icon={action.icon}
                  color={action.color}
                  onPress={() => console.log(`Navigate to ${action.title}`)}
                />
              ))}
            </View>
          </Card.Content>
        </Card>

        {/* Recent Activity */}
        <Card style={styles.card}>
          <Card.Content>
            <Title>Recent Activity</Title>
            <View style={styles.activityItem}>
              <Icon name="calendar-check" size={20} color="#4CAF50" />
              <View style={styles.activityText}>
                <Text style={styles.activityTitle}>Attendance Recorded</Text>
                <Text style={styles.activityDate}>Today, 9:00 AM</Text>
              </View>
            </View>
            <View style={styles.activityItem}>
              <Icon name="school" size={20} color="#2196F3" />
              <View style={styles.activityText}>
                <Text style={styles.activityTitle}>New Grade Posted</Text>
                <Text style={styles.activityDate}>Yesterday, 2:30 PM</Text>
              </View>
            </View>
          </Card.Content>
        </Card>

        {/* Debug Logout Button */}
        <Button
          mode="outlined"
          onPress={logout}
          style={styles.logoutButton}
          textColor="#f44336"
        >
          Logout
        </Button>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  scrollContent: {
    padding: 16,
  },
  header: {
    marginBottom: 24,
  },
  greeting: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
    marginTop: 4,
  },
  statusCard: {
    marginBottom: 16,
    elevation: 2,
  },
  card: {
    marginBottom: 16,
    elevation: 2,
  },
  statusRow: {
    flexDirection: 'row',
    marginTop: 12,
    gap: 8,
  },
  chip: {
    marginRight: 8,
  },
  actionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginTop: 16,
  },
  actionButton: {
    flex: 1,
    minWidth: '45%',
  },
  actionButtonContent: {
    paddingVertical: 8,
  },
  activityItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  activityText: {
    marginLeft: 12,
    flex: 1,
  },
  activityTitle: {
    fontSize: 16,
    fontWeight: '500',
  },
  activityDate: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  logoutButton: {
    marginTop: 16,
    borderColor: '#f44336',
  },
});

export default DashboardScreen;