import React from 'react';
import { View, StyleSheet, ScrollView } from 'react-native';
import { Card, Title, List, Chip } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';

const AttendanceScreen: React.FC = () => {
  const attendanceData = [
    { id: 1, course: 'Mathematics', date: '2024-01-15', status: 'present' },
    { id: 2, course: 'Physics', date: '2024-01-15', status: 'present' },
    { id: 3, course: 'Chemistry', date: '2024-01-14', status: 'absent' },
    { id: 4, course: 'Biology', date: '2024-01-14', status: 'present' },
  ];

  const getStatusColor = (status: string) => {
    return status === 'present' ? '#4CAF50' : '#f44336';
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Card style={styles.card}>
          <Card.Content>
            <Title>Attendance Record</Title>
            {attendanceData.map((record) => (
              <List.Item
                key={record.id}
                title={record.course}
                description={record.date}
                right={() => (
                  <Chip
                    mode="outlined"
                    textStyle={{ color: getStatusColor(record.status) }}
                    style={{ borderColor: getStatusColor(record.status) }}
                  >
                    {record.status.toUpperCase()}
                  </Chip>
                )}
              />
            ))}
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
    padding: 16,
  },
  card: {
    elevation: 2,
  },
});

export default AttendanceScreen;