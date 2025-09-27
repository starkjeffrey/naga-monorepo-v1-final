import React, { useState, useEffect } from 'react';
import { View, StyleSheet, ScrollView, RefreshControl, Pressable } from 'react-native';
import { Card, Title, Text, Chip, Badge, useTheme, Avatar } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { useNavigation } from '@react-navigation/native';
import { useAuthStore } from '@/store/authStore';

interface QuickAction {
  id: string;
  title: string;
  description: string;
  icon: string;
  color: string;
  route: string;
  badge?: number;
}

const StudentDashboardScreen: React.FC = () => {
  const theme = useTheme();
  const navigation = useNavigation<any>();
  const { user, selectedRole } = useAuthStore();
  const [refreshing, setRefreshing] = useState(false);
  const [unreadAnnouncements, setUnreadAnnouncements] = useState(3);

  const quickActions: QuickAction[] = [
    {
      id: 'attendance',
      title: 'Attendance',
      description: 'View and track your attendance',
      icon: 'checkbox-marked-circle',
      color: '#9C27B0',
      route: 'Attendance',
    },
    {
      id: 'grades',
      title: 'Grades',
      description: 'Check your academic performance',
      icon: 'chart-line',
      color: '#2196F3',
      route: 'Grades',
    },
    {
      id: 'schedule',
      title: 'Schedule',
      description: 'View your class timetable',
      icon: 'calendar-clock',
      color: '#FF9800',
      route: 'Schedule',
    },
    {
      id: 'announcements',
      title: 'Announcements',
      description: 'School news and updates',
      icon: 'bullhorn',
      color: '#4CAF50',
      route: 'Announcements',
      badge: unreadAnnouncements,
    },
    {
      id: 'id-card',
      title: 'ID Card',
      description: 'Your digital student ID',
      icon: 'card-account-details',
      color: '#FFC107',
      route: 'IDCard',
    },
    {
      id: 'permission',
      title: 'Permission',
      description: 'Request leave or permissions',
      icon: 'file-document-edit',
      color: '#E91E63',
      route: 'Permission',
    },
    {
      id: 'profile-photo',
      title: 'Profile Photo',
      description: 'Update your profile picture',
      icon: 'camera',
      color: '#3F51B5',
      route: 'ProfilePhoto',
    },
    {
      id: 'finances',
      title: 'Finances',
      description: 'View your financial balance',
      icon: 'wallet',
      color: '#009688',
      route: 'Finances',
    },
  ];

  const onRefresh = React.useCallback(() => {
    setRefreshing(true);
    // Simulate data refresh
    setTimeout(() => {
      setRefreshing(false);
      setUnreadAnnouncements(Math.floor(Math.random() * 10));
    }, 2000);
  }, []);

  const handleActionPress = (route: string) => {
    navigation.navigate(route);
  };

  const isMATeacher = user?.role === 'ma_teacher';

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.headerContent}>
            <View>
              <Text style={styles.greeting}>Welcome back,</Text>
              <Title style={styles.userName}>{user?.name || 'Student'}</Title>
            </View>
            {isMATeacher && (
              <Chip
                icon="account-switch"
                mode="outlined"
                onPress={() => navigation.navigate('RoleSwitcher')}
                style={styles.roleChip}
              >
                {selectedRole === 'teacher' ? 'Teacher Mode' : 'Student Mode'}
              </Chip>
            )}
          </View>
        </View>

        {/* Status Card */}
        <Card style={styles.statusCard}>
          <Card.Content>
            <View style={styles.statusHeader}>
              <Title style={styles.statusTitle}>Your Status</Title>
              <Chip
                icon="check-circle"
                mode="flat"
                style={[styles.statusChip, { backgroundColor: '#E8F5E9' }]}
                textStyle={{ color: '#4CAF50' }}
              >
                Active
              </Chip>
            </View>
            <View style={styles.statusInfo}>
              <View style={styles.statusItem}>
                <Icon name="identifier" size={20} color={theme.colors.primary} />
                <Text style={styles.statusLabel}>ID: {user?.studentId || 'N/A'}</Text>
              </View>
              <View style={styles.statusItem}>
                <Icon name="school" size={20} color={theme.colors.primary} />
                <Text style={styles.statusLabel}>
                  {user?.department || 'Computer Science'}
                </Text>
              </View>
              <View style={styles.statusItem}>
                <Icon name="calendar" size={20} color={theme.colors.primary} />
                <Text style={styles.statusLabel}>
                  {user?.currentAcademicYear || '2024-2025'}
                </Text>
              </View>
            </View>
          </Card.Content>
        </Card>

        {/* Quick Actions Grid */}
        <Title style={styles.sectionTitle}>Quick Actions</Title>
        <View style={styles.actionsGrid}>
          {quickActions.map((action) => (
            <Pressable
              key={action.id}
              style={styles.actionCard}
              onPress={() => handleActionPress(action.route)}
            >
              <Card style={styles.actionCardContent}>
                <View style={styles.actionBadgeContainer}>
                  <Avatar.Icon
                    size={48}
                    icon={action.icon}
                    style={[styles.actionIcon, { backgroundColor: action.color + '20' }]}
                    color={action.color}
                  />
                  {action.badge && action.badge > 0 && (
                    <Badge style={styles.actionBadge}>{action.badge}</Badge>
                  )}
                </View>
                <Text style={styles.actionTitle}>{action.title}</Text>
                <Text style={styles.actionDescription} numberOfLines={2}>
                  {action.description}
                </Text>
              </Card>
            </Pressable>
          ))}
        </View>

        {/* Today's Schedule Preview */}
        <Card style={styles.scheduleCard}>
          <Card.Content>
            <Title style={styles.sectionTitle}>Today's Classes</Title>
            <View style={styles.scheduleItem}>
              <View style={styles.scheduleTime}>
                <Text style={styles.scheduleTimeText}>08:00</Text>
              </View>
              <View style={styles.scheduleDetails}>
                <Text style={styles.scheduleSubject}>Database Systems</Text>
                <Text style={styles.scheduleLocation}>Room A-201</Text>
              </View>
            </View>
            <View style={styles.scheduleItem}>
              <View style={styles.scheduleTime}>
                <Text style={styles.scheduleTimeText}>10:00</Text>
              </View>
              <View style={styles.scheduleDetails}>
                <Text style={styles.scheduleSubject}>Web Development</Text>
                <Text style={styles.scheduleLocation}>Lab B-105</Text>
              </View>
            </View>
            <View style={styles.scheduleItem}>
              <View style={styles.scheduleTime}>
                <Text style={styles.scheduleTimeText}>14:00</Text>
              </View>
              <View style={styles.scheduleDetails}>
                <Text style={styles.scheduleSubject}>Mobile Computing</Text>
                <Text style={styles.scheduleLocation}>Room C-301</Text>
              </View>
            </View>
          </Card.Content>
        </Card>

        {/* Recent Activity */}
        <Card style={styles.activityCard}>
          <Card.Content>
            <Title style={styles.sectionTitle}>Recent Activity</Title>
            <View style={styles.activityItem}>
              <Icon name="check-circle" size={20} color="#4CAF50" />
              <View style={styles.activityText}>
                <Text style={styles.activityTitle}>Attendance Marked</Text>
                <Text style={styles.activityDate}>Database Systems - Today, 8:15 AM</Text>
              </View>
            </View>
            <View style={styles.activityItem}>
              <Icon name="file-document" size={20} color="#2196F3" />
              <View style={styles.activityText}>
                <Text style={styles.activityTitle}>New Assignment Posted</Text>
                <Text style={styles.activityDate}>Web Development - Yesterday</Text>
              </View>
            </View>
            <View style={styles.activityItem}>
              <Icon name="trophy" size={20} color="#FFC107" />
              <View style={styles.activityText}>
                <Text style={styles.activityTitle}>Grade Released</Text>
                <Text style={styles.activityDate}>Mobile Computing Quiz - 2 days ago</Text>
              </View>
            </View>
          </Card.Content>
        </Card>
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
    paddingBottom: 20,
  },
  header: {
    backgroundColor: '#fff',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  headerContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  greeting: {
    fontSize: 14,
    color: '#666',
  },
  userName: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1a1a1a',
  },
  roleChip: {
    backgroundColor: '#E3F2FD',
  },
  statusCard: {
    margin: 16,
    elevation: 2,
  },
  statusHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  statusTitle: {
    fontSize: 18,
    fontWeight: '600',
  },
  statusChip: {
    height: 28,
  },
  statusInfo: {
    gap: 12,
  },
  statusItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  statusLabel: {
    fontSize: 14,
    color: '#666',
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginHorizontal: 16,
    marginTop: 16,
    marginBottom: 12,
  },
  actionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: 12,
    gap: 8,
  },
  actionCard: {
    width: '48%',
    marginBottom: 8,
  },
  actionCardContent: {
    padding: 16,
    alignItems: 'center',
    elevation: 1,
  },
  actionBadgeContainer: {
    position: 'relative',
  },
  actionIcon: {
    marginBottom: 8,
  },
  actionBadge: {
    position: 'absolute',
    top: -4,
    right: -4,
    backgroundColor: '#f44336',
  },
  actionTitle: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 4,
    textAlign: 'center',
  },
  actionDescription: {
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
  },
  scheduleCard: {
    margin: 16,
    elevation: 2,
  },
  scheduleItem: {
    flexDirection: 'row',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  scheduleTime: {
    width: 60,
    marginRight: 16,
  },
  scheduleTimeText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#2196F3',
  },
  scheduleDetails: {
    flex: 1,
  },
  scheduleSubject: {
    fontSize: 14,
    fontWeight: '500',
    marginBottom: 2,
  },
  scheduleLocation: {
    fontSize: 12,
    color: '#666',
  },
  activityCard: {
    margin: 16,
    marginBottom: 80,
    elevation: 2,
  },
  activityItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  activityText: {
    marginLeft: 12,
    flex: 1,
  },
  activityTitle: {
    fontSize: 14,
    fontWeight: '500',
  },
  activityDate: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
});

export default StudentDashboardScreen;