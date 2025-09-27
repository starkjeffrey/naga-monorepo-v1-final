import React from 'react';
import { View, StyleSheet, ScrollView, Text } from 'react-native';
import { Card, Title, Chip } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';

const TeacherCoursesScreen: React.FC = () => {
  const courses = [
    { id: '1', name: 'Computer Science 101', code: 'CS101', students: 32, schedule: 'MWF 8:00-9:30' },
    { id: '2', name: 'Database Systems', code: 'CS301', students: 28, schedule: 'TTh 10:00-11:30' },
    { id: '3', name: 'Web Development', code: 'CS302', students: 35, schedule: 'MWF 14:00-15:30' },
  ];

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Title style={styles.title}>My Courses</Title>

        {courses.map((course) => (
          <Card key={course.id} style={styles.courseCard}>
            <Card.Content>
              <Text style={styles.courseName}>{course.name}</Text>
              <Text style={styles.courseCode}>{course.code}</Text>
              <View style={styles.courseInfo}>
                <Chip compact icon="account-group">{course.students} students</Chip>
                <Chip compact icon="calendar">{course.schedule}</Chip>
              </View>
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
  courseCard: {
    marginBottom: 12,
    elevation: 1,
  },
  courseName: {
    fontSize: 16,
    fontWeight: '500',
  },
  courseCode: {
    fontSize: 14,
    color: '#666',
    marginBottom: 8,
  },
  courseInfo: {
    flexDirection: 'row',
    gap: 8,
  },
});

export default TeacherCoursesScreen;