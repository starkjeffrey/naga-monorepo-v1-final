import React, { useState, useEffect } from 'react';
import { View, StyleSheet, ScrollView, RefreshControl, Pressable } from 'react-native';
import { Card, Title, Text, Chip, ProgressBar, Button, useTheme, FAB } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { Calendar } from 'react-native-calendars';
import { useNavigation } from '@react-navigation/native';

interface CourseAttendance {
  id: string;
  courseName: string;
  courseCode: string;
  totalClasses: number;
  attendedClasses: number;
  percentage: number;
  status: 'good' | 'warning' | 'critical';
}

interface AttendanceRecord {
  date: string;
  status: 'present' | 'absent' | 'late' | 'excused';
  course: string;
  time: string;
}

const AttendanceScreen: React.FC = () => {
  const theme = useTheme();
  const navigation = useNavigation<any>();
  const [refreshing, setRefreshing] = useState(false);
  const [selectedMonth, setSelectedMonth] = useState(new Date().toISOString().slice(0, 7));
  const [viewMode, setViewMode] = useState<'overview' | 'calendar'>('overview');

  const courseAttendance: CourseAttendance[] = [
    {
      id: '1',
      courseName: 'Database Systems',
      courseCode: 'CS301',
      totalClasses: 30,
      attendedClasses: 27,
      percentage: 90,
      status: 'good',
    },
    {
      id: '2',
      courseName: 'Web Development',
      courseCode: 'CS302',
      totalClasses: 28,
      attendedClasses: 23,
      percentage: 82,
      status: 'good',
    },
    {
      id: '3',
      courseName: 'Mobile Computing',
      courseCode: 'CS303',
      totalClasses: 25,
      attendedClasses: 18,
      percentage: 72,
      status: 'warning',
    },
    {
      id: '4',
      courseName: 'Data Structures',
      courseCode: 'CS201',
      totalClasses: 32,
      attendedClasses: 20,
      percentage: 62,
      status: 'critical',
    },
  ];

  const recentAttendance: AttendanceRecord[] = [
    {
      date: '2024-01-26',
      status: 'present',
      course: 'Database Systems',
      time: '08:00 AM',
    },
    {
      date: '2024-01-26',
      status: 'late',
      course: 'Web Development',
      time: '10:00 AM',
    },
    {
      date: '2024-01-25',
      status: 'present',
      course: 'Mobile Computing',
      time: '02:00 PM',
    },
    {
      date: '2024-01-25',
      status: 'absent',
      course: 'Data Structures',
      time: '04:00 PM',
    },
  ];

  const onRefresh = React.useCallback(() => {
    setRefreshing(true);
    setTimeout(() => {
      setRefreshing(false);
    }, 2000);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'good':
        return '#4CAF50';
      case 'warning':
        return '#FF9800';
      case 'critical':
        return '#f44336';
      default:
        return '#9E9E9E';
    }
  };

  const getAttendanceStatusColor = (status: string) => {
    switch (status) {
      case 'present':
        return '#4CAF50';
      case 'late':
        return '#FF9800';
      case 'absent':
        return '#f44336';
      case 'excused':
        return '#2196F3';
      default:
        return '#9E9E9E';
    }
  };

  const getAttendanceStatusIcon = (status: string) => {
    switch (status) {
      case 'present':
        return 'check-circle';
      case 'late':
        return 'clock-alert';
      case 'absent':
        return 'close-circle';
      case 'excused':
        return 'file-document';
      default:
        return 'help-circle';
    }
  };

  const markedDates = {
    '2024-01-26': { marked: true, dotColor: '#4CAF50' },
    '2024-01-25': { marked: true, dotColor: '#f44336' },
    '2024-01-24': { marked: true, dotColor: '#4CAF50' },
    '2024-01-23': { marked: true, dotColor: '#4CAF50' },
    '2024-01-22': { marked: true, dotColor: '#FF9800' },
  };

  const overallAttendance = Math.round(
    courseAttendance.reduce((acc, course) => acc + course.percentage, 0) / courseAttendance.length
  );

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Title style={styles.headerTitle}>Attendance</Title>
        <View style={styles.headerButtons}>
          <Chip
            mode="outlined"
            selected={viewMode === 'overview'}
            onPress={() => setViewMode('overview')}
            style={styles.viewModeChip}
          >
            Overview
          </Chip>
          <Chip
            mode="outlined"
            selected={viewMode === 'calendar'}
            onPress={() => setViewMode('calendar')}
            style={styles.viewModeChip}
          >
            Calendar
          </Chip>
        </View>
      </View>

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        {/* Overall Summary */}
        <Card style={styles.summaryCard}>
          <Card.Content>
            <View style={styles.summaryHeader}>
              <View>
                <Text style={styles.summaryLabel}>Overall Attendance</Text>
                <Text style={styles.summaryValue}>{overallAttendance}%</Text>
              </View>
              <Chip
                mode="flat"
                style={{
                  backgroundColor:
                    overallAttendance >= 75 ? '#E8F5E9' : '#FFEBEE',
                }}
                textStyle={{
                  color: overallAttendance >= 75 ? '#4CAF50' : '#f44336',
                }}
              >
                {overallAttendance >= 75 ? 'Good Standing' : 'Needs Improvement'}
              </Chip>
            </View>
            <ProgressBar
              progress={overallAttendance / 100}
              color={overallAttendance >= 75 ? '#4CAF50' : '#f44336'}
              style={styles.progressBar}
            />
            <Text style={styles.summaryInfo}>
              Minimum 75% attendance required for exam eligibility
            </Text>
          </Card.Content>
        </Card>

        {viewMode === 'overview' ? (
          <>
            {/* Course-wise Attendance */}
            <Title style={styles.sectionTitle}>Course-wise Attendance</Title>
            {courseAttendance.map((course) => (
              <Card key={course.id} style={styles.courseCard}>
                <Card.Content>
                  <View style={styles.courseHeader}>
                    <View>
                      <Text style={styles.courseName}>{course.courseName}</Text>
                      <Text style={styles.courseCode}>{course.courseCode}</Text>
                    </View>
                    <View style={styles.courseStats}>
                      <Text style={styles.courseAttendance}>{course.percentage}%</Text>
                      <Icon
                        name={
                          course.status === 'good'
                            ? 'check-circle'
                            : course.status === 'warning'
                            ? 'alert-circle'
                            : 'close-circle'
                        }
                        size={20}
                        color={getStatusColor(course.status)}
                      />
                    </View>
                  </View>
                  <ProgressBar
                    progress={course.percentage / 100}
                    color={getStatusColor(course.status)}
                    style={styles.courseProgressBar}
                  />
                  <View style={styles.courseDetails}>
                    <Text style={styles.courseDetailText}>
                      Attended: {course.attendedClasses}/{course.totalClasses} classes
                    </Text>
                    {course.status === 'critical' && (
                      <Text style={styles.warningText}>
                        ⚠️ Below minimum requirement
                      </Text>
                    )}
                  </View>
                </Card.Content>
              </Card>
            ))}

            {/* Recent Attendance */}
            <Title style={styles.sectionTitle}>Recent Attendance</Title>
            <Card style={styles.recentCard}>
              <Card.Content>
                {recentAttendance.map((record, index) => (
                  <View key={index} style={styles.recentItem}>
                    <Icon
                      name={getAttendanceStatusIcon(record.status)}
                      size={24}
                      color={getAttendanceStatusColor(record.status)}
                    />
                    <View style={styles.recentContent}>
                      <Text style={styles.recentCourse}>{record.course}</Text>
                      <Text style={styles.recentDetails}>
                        {record.date} • {record.time}
                      </Text>
                    </View>
                    <Chip
                      compact
                      style={{
                        backgroundColor:
                          getAttendanceStatusColor(record.status) + '20',
                      }}
                      textStyle={{
                        color: getAttendanceStatusColor(record.status),
                        fontSize: 10,
                      }}
                    >
                      {record.status}
                    </Chip>
                  </View>
                ))}
              </Card.Content>
            </Card>
          </>
        ) : (
          <>
            {/* Calendar View */}
            <Card style={styles.calendarCard}>
              <Card.Content>
                <Calendar
                  markedDates={markedDates}
                  theme={{
                    backgroundColor: '#ffffff',
                    calendarBackground: '#ffffff',
                    textSectionTitleColor: '#666',
                    selectedDayBackgroundColor: theme.colors.primary,
                    selectedDayTextColor: '#ffffff',
                    todayTextColor: theme.colors.primary,
                    dayTextColor: '#333',
                    dotColor: theme.colors.primary,
                    selectedDotColor: '#ffffff',
                    arrowColor: theme.colors.primary,
                    monthTextColor: '#333',
                    textDayFontWeight: '300',
                    textMonthFontWeight: 'bold',
                    textDayHeaderFontWeight: '500',
                  }}
                />
              </Card.Content>
            </Card>

            {/* Legend */}
            <Card style={styles.legendCard}>
              <Card.Content>
                <Title style={styles.legendTitle}>Legend</Title>
                <View style={styles.legendItems}>
                  <View style={styles.legendItem}>
                    <View style={[styles.legendDot, { backgroundColor: '#4CAF50' }]} />
                    <Text>Present</Text>
                  </View>
                  <View style={styles.legendItem}>
                    <View style={[styles.legendDot, { backgroundColor: '#FF9800' }]} />
                    <Text>Late</Text>
                  </View>
                  <View style={styles.legendItem}>
                    <View style={[styles.legendDot, { backgroundColor: '#f44336' }]} />
                    <Text>Absent</Text>
                  </View>
                  <View style={styles.legendItem}>
                    <View style={[styles.legendDot, { backgroundColor: '#2196F3' }]} />
                    <Text>Excused</Text>
                  </View>
                </View>
              </Card.Content>
            </Card>
          </>
        )}
      </ScrollView>

      {/* FAB for marking attendance */}
      <FAB
        icon="qrcode-scan"
        style={styles.fab}
        onPress={() => navigation.navigate('EnterCode')}
        label="Mark Attendance"
      />
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    backgroundColor: '#fff',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
  },
  headerButtons: {
    flexDirection: 'row',
    gap: 8,
  },
  viewModeChip: {
    height: 32,
  },
  scrollContent: {
    paddingBottom: 100,
  },
  summaryCard: {
    margin: 16,
    elevation: 2,
  },
  summaryHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  summaryLabel: {
    fontSize: 14,
    color: '#666',
  },
  summaryValue: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#333',
  },
  progressBar: {
    height: 8,
    borderRadius: 4,
    marginBottom: 8,
  },
  summaryInfo: {
    fontSize: 12,
    color: '#888',
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginHorizontal: 16,
    marginTop: 16,
    marginBottom: 12,
  },
  courseCard: {
    marginHorizontal: 16,
    marginBottom: 12,
    elevation: 1,
  },
  courseHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  courseName: {
    fontSize: 16,
    fontWeight: '500',
  },
  courseCode: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  courseStats: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  courseAttendance: {
    fontSize: 20,
    fontWeight: 'bold',
  },
  courseProgressBar: {
    height: 6,
    borderRadius: 3,
    marginBottom: 8,
  },
  courseDetails: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  courseDetailText: {
    fontSize: 12,
    color: '#666',
  },
  warningText: {
    fontSize: 12,
    color: '#f44336',
    fontWeight: '500',
  },
  recentCard: {
    margin: 16,
    elevation: 2,
  },
  recentItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  recentContent: {
    flex: 1,
    marginLeft: 12,
  },
  recentCourse: {
    fontSize: 14,
    fontWeight: '500',
  },
  recentDetails: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  calendarCard: {
    margin: 16,
    elevation: 2,
  },
  legendCard: {
    margin: 16,
    elevation: 1,
  },
  legendTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 12,
  },
  legendItems: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 16,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  legendDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  fab: {
    position: 'absolute',
    right: 16,
    bottom: 16,
    backgroundColor: '#2196F3',
  },
});

export default AttendanceScreen;