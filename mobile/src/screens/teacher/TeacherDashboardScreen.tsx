import React, { useState } from 'react';
import { View, StyleSheet, ScrollView, RefreshControl, Pressable } from 'react-native';
import { Card, Title, Text, Button, Chip, useTheme, ProgressBar } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { useNavigation } from '@react-navigation/native';
import { useAuthStore } from '@/store/authStore';

interface StatCard {
  id: string;
  title: string;
  value: string | number;
  icon: string;
  color: string;
  trend?: 'up' | 'down' | 'neutral';
}

interface TodaysClass {
  id: string;
  name: string;
  time: string;
  room: string;
  students: number;
  status: 'upcoming' | 'in-progress' | 'completed';
}

const TeacherDashboardScreen: React.FC = () => {
  const theme = useTheme();
  const navigation = useNavigation<any>();
  const { user, selectedRole } = useAuthStore();
  const [refreshing, setRefreshing] = useState(false);

  const stats: StatCard[] = [
    {
      id: 'courses',
      title: 'Total Courses',
      value: 4,
      icon: 'book-open-variant',
      color: '#2196F3',
    },
    {
      id: 'students',
      title: 'Total Students',
      value: 127,
      icon: 'account-group',
      color: '#4CAF50',
    },
    {
      id: 'attendance',
      title: 'Avg Attendance',
      value: '87%',
      icon: 'chart-arc',
      color: '#FF9800',
      trend: 'up',
    },
    {
      id: 'pending',
      title: 'Pending Grades',
      value: 23,
      icon: 'clock-alert',
      color: '#f44336',
    },
  ];

  const todaysClasses: TodaysClass[] = [
    {
      id: '1',
      name: 'Computer Science 101',
      time: '08:00 - 09:30',
      room: 'Room A-101',
      students: 32,
      status: 'completed',
    },
    {
      id: '2',
      name: 'Database Systems',
      time: '10:00 - 11:30',
      room: 'Lab B-205',
      students: 28,
      status: 'in-progress',
    },
    {
      id: '3',
      name: 'Web Development',
      time: '14:00 - 15:30',
      room: 'Lab C-301',
      students: 35,
      status: 'upcoming',
    },
  ];

  const onRefresh = React.useCallback(() => {
    setRefreshing(true);
    setTimeout(() => {
      setRefreshing(false);
    }, 2000);
  }, []);

  const getClassStatusColor = (status: string) => {
    switch (status) {
      case 'upcoming':
        return '#2196F3';
      case 'in-progress':
        return '#4CAF50';
      case 'completed':
        return '#9E9E9E';
      default:
        return '#9E9E9E';
    }
  };

  const getClassStatusIcon = (status: string) => {
    switch (status) {
      case 'upcoming':
        return 'clock-outline';
      case 'in-progress':
        return 'play-circle';
      case 'completed':
        return 'check-circle';
      default:
        return 'help-circle';
    }
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
          <View>
            <Text style={styles.greeting}>Good morning,</Text>
            <Title style={styles.userName}>{user?.name || 'Teacher'}</Title>
            <Text style={styles.subtitle}>Here's your teaching overview</Text>
          </View>
          {isMATeacher && (
            <Chip
              icon="account-switch"
              mode="outlined"
              onPress={() => navigation.navigate('RoleSwitcher')}
              style={styles.roleChip}
            >
              Teacher Mode
            </Chip>
          )}
        </View>

        {/* Quick Stats */}
        <View style={styles.statsContainer}>
          {stats.map((stat) => (
            <Pressable key={stat.id} style={styles.statCard}>
              <Card style={styles.statCardContent}>
                <Card.Content style={styles.statCardInner}>
                  <Icon name={stat.icon} size={28} color={stat.color} />
                  <Text style={styles.statValue}>{stat.value}</Text>
                  <Text style={styles.statTitle}>{stat.title}</Text>
                  {stat.trend && (
                    <Icon
                      name={stat.trend === 'up' ? 'trending-up' : 'trending-down'}
                      size={16}
                      color={stat.trend === 'up' ? '#4CAF50' : '#f44336'}
                      style={styles.trendIcon}
                    />
                  )}
                </Card.Content>
              </Card>
            </Pressable>
          ))}
        </View>

        {/* Quick Actions */}
        <Card style={styles.actionCard}>
          <Card.Content>
            <Title style={styles.sectionTitle}>Quick Actions</Title>
            <View style={styles.actionButtons}>
              <Button
                mode="contained"
                icon="qrcode"
                onPress={() => navigation.navigate('GenerateCode')}
                style={[styles.actionButton, { backgroundColor: theme.colors.primary }]}
              >
                Generate Code
              </Button>
              <Button
                mode="contained"
                icon="clipboard-check"
                onPress={() => navigation.navigate('ManualAttendance')}
                style={[styles.actionButton, { backgroundColor: '#4CAF50' }]}
              >
                Manual Attendance
              </Button>
              <Button
                mode="contained"
                icon="pencil"
                onPress={() => navigation.navigate('Grades')}
                style={[styles.actionButton, { backgroundColor: '#FF9800' }]}
              >
                Enter Grades
              </Button>
              <Button
                mode="contained"
                icon="account-group"
                onPress={() => navigation.navigate('Courses')}
                style={[styles.actionButton, { backgroundColor: '#9C27B0' }]}
              >
                View Students
              </Button>
            </View>
          </Card.Content>
        </Card>

        {/* Today's Classes */}
        <Card style={styles.classesCard}>
          <Card.Content>
            <View style={styles.sectionHeader}>
              <Title style={styles.sectionTitle}>Today's Classes</Title>
              <Chip compact>{todaysClasses.length} classes</Chip>
            </View>
            {todaysClasses.map((classItem) => (
              <Pressable
                key={classItem.id}
                style={styles.classItem}
                onPress={() => navigation.navigate('CourseDetails', { courseId: classItem.id })}
              >
                <View style={styles.classItemLeft}>
                  <Icon
                    name={getClassStatusIcon(classItem.status)}
                    size={24}
                    color={getClassStatusColor(classItem.status)}
                  />
                </View>
                <View style={styles.classItemContent}>
                  <Text style={styles.className}>{classItem.name}</Text>
                  <View style={styles.classDetails}>
                    <View style={styles.classDetailItem}>
                      <Icon name="clock-outline" size={14} color="#666" />
                      <Text style={styles.classDetailText}>{classItem.time}</Text>
                    </View>
                    <View style={styles.classDetailItem}>
                      <Icon name="map-marker" size={14} color="#666" />
                      <Text style={styles.classDetailText}>{classItem.room}</Text>
                    </View>
                    <View style={styles.classDetailItem}>
                      <Icon name="account-group" size={14} color="#666" />
                      <Text style={styles.classDetailText}>{classItem.students}</Text>
                    </View>
                  </View>
                </View>
                <Chip
                  compact
                  mode="flat"
                  style={{
                    backgroundColor: getClassStatusColor(classItem.status) + '20',
                  }}
                  textStyle={{
                    color: getClassStatusColor(classItem.status),
                    fontSize: 10,
                  }}
                >
                  {classItem.status}
                </Chip>
              </Pressable>
            ))}
          </Card.Content>
        </Card>

        {/* Recent Activity */}
        <Card style={styles.activityCard}>
          <Card.Content>
            <Title style={styles.sectionTitle}>Recent Activity</Title>
            <View style={styles.activityItem}>
              <Icon name="qrcode" size={20} color={theme.colors.primary} />
              <View style={styles.activityText}>
                <Text style={styles.activityTitle}>Generated attendance code</Text>
                <Text style={styles.activityDescription}>CS101 - 30 minutes ago</Text>
              </View>
            </View>
            <View style={styles.activityItem}>
              <Icon name="pencil" size={20} color="#FF9800" />
              <View style={styles.activityText}>
                <Text style={styles.activityTitle}>Updated grades</Text>
                <Text style={styles.activityDescription}>Database Systems midterm - 2 hours ago</Text>
              </View>
            </View>
            <View style={styles.activityItem}>
              <Icon name="clipboard-check" size={20} color="#4CAF50" />
              <View style={styles.activityText}>
                <Text style={styles.activityTitle}>Marked manual attendance</Text>
                <Text style={styles.activityDescription}>Web Development - Yesterday</Text>
              </View>
            </View>
            <View style={styles.activityItem}>
              <Icon name="file-document" size={20} color="#2196F3" />
              <View style={styles.activityText}>
                <Text style={styles.activityTitle}>Posted assignment</Text>
                <Text style={styles.activityDescription}>CS101 Final Project - 2 days ago</Text>
              </View>
            </View>
          </Card.Content>
        </Card>

        {/* Attendance Overview */}
        <Card style={styles.attendanceCard}>
          <Card.Content>
            <Title style={styles.sectionTitle}>Weekly Attendance Overview</Title>
            <View style={styles.attendanceStats}>
              <View style={styles.attendanceStat}>
                <Text style={styles.attendanceLabel}>CS101</Text>
                <ProgressBar progress={0.92} color="#4CAF50" style={styles.progressBar} />
                <Text style={styles.attendanceValue}>92%</Text>
              </View>
              <View style={styles.attendanceStat}>
                <Text style={styles.attendanceLabel}>Database Systems</Text>
                <ProgressBar progress={0.87} color="#2196F3" style={styles.progressBar} />
                <Text style={styles.attendanceValue}>87%</Text>
              </View>
              <View style={styles.attendanceStat}>
                <Text style={styles.attendanceLabel}>Web Development</Text>
                <ProgressBar progress={0.78} color="#FF9800" style={styles.progressBar} />
                <Text style={styles.attendanceValue}>78%</Text>
              </View>
              <View style={styles.attendanceStat}>
                <Text style={styles.attendanceLabel}>Mobile Computing</Text>
                <ProgressBar progress={0.85} color="#9C27B0" style={styles.progressBar} />
                <Text style={styles.attendanceValue}>85%</Text>
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
  subtitle: {
    fontSize: 14,
    color: '#888',
    marginTop: 2,
  },
  roleChip: {
    backgroundColor: '#E3F2FD',
  },
  statsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    padding: 12,
    gap: 8,
  },
  statCard: {
    width: '48%',
  },
  statCardContent: {
    elevation: 1,
  },
  statCardInner: {
    alignItems: 'center',
    paddingVertical: 16,
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    marginTop: 8,
  },
  statTitle: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  trendIcon: {
    position: 'absolute',
    top: 8,
    right: 8,
  },
  actionCard: {
    margin: 16,
    elevation: 2,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 12,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  actionButtons: {
    gap: 10,
  },
  actionButton: {
    marginBottom: 8,
  },
  classesCard: {
    margin: 16,
    elevation: 2,
  },
  classItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  classItemLeft: {
    marginRight: 12,
  },
  classItemContent: {
    flex: 1,
  },
  className: {
    fontSize: 16,
    fontWeight: '500',
    marginBottom: 4,
  },
  classDetails: {
    flexDirection: 'row',
    gap: 12,
  },
  classDetailItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  classDetailText: {
    fontSize: 12,
    color: '#666',
  },
  activityCard: {
    margin: 16,
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
  activityDescription: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  attendanceCard: {
    margin: 16,
    marginBottom: 80,
    elevation: 2,
  },
  attendanceStats: {
    gap: 16,
  },
  attendanceStat: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  attendanceLabel: {
    fontSize: 14,
    width: 120,
  },
  progressBar: {
    flex: 1,
    height: 8,
    borderRadius: 4,
  },
  attendanceValue: {
    fontSize: 14,
    fontWeight: '600',
    width: 40,
    textAlign: 'right',
  },
});

export default TeacherDashboardScreen;