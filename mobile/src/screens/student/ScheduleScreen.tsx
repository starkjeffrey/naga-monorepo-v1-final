import React from 'react';
import { View, StyleSheet, ScrollView, Text } from 'react-native';
import { Card, Title, Chip } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';

const ScheduleScreen: React.FC = () => {
  const schedule = {
    Monday: [
      { time: '08:00-09:30', subject: 'Database Systems', room: 'A-201' },
      { time: '10:00-11:30', subject: 'Web Development', room: 'Lab B-105' },
    ],
    Tuesday: [
      { time: '08:00-09:30', subject: 'Mobile Computing', room: 'C-301' },
      { time: '14:00-15:30', subject: 'Data Structures', room: 'A-101' },
    ],
    Wednesday: [
      { time: '10:00-11:30', subject: 'Database Systems', room: 'A-201' },
      { time: '14:00-15:30', subject: 'Web Development', room: 'Lab B-105' },
    ],
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Title style={styles.title}>Class Schedule</Title>

        {Object.entries(schedule).map(([day, classes]) => (
          <Card key={day} style={styles.dayCard}>
            <Card.Content>
              <Title style={styles.dayTitle}>{day}</Title>
              {classes.map((cls, index) => (
                <View key={index} style={styles.classItem}>
                  <Text style={styles.timeText}>{cls.time}</Text>
                  <View style={styles.classDetails}>
                    <Text style={styles.subjectText}>{cls.subject}</Text>
                    <Chip compact>{cls.room}</Chip>
                  </View>
                </View>
              ))}
            </Card.Content>
          </Card>
        ))}
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
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  dayCard: {
    marginBottom: 16,
  },
  dayTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 12,
  },
  classItem: {
    flexDirection: 'row',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  timeText: {
    width: 100,
    fontSize: 14,
    fontWeight: '500',
    color: '#2196F3',
  },
  classDetails: {
    flex: 1,
  },
  subjectText: {
    fontSize: 14,
    fontWeight: '500',
    marginBottom: 4,
  },
});

export default ScheduleScreen;