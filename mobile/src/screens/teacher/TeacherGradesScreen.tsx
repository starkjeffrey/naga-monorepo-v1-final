import React from 'react';
import { View, StyleSheet, ScrollView, Text } from 'react-native';
import { Card, Title, List, Chip } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';

const TeacherGradesScreen: React.FC = () => {
  const pendingGrades = [
    { course: 'CS101', assessment: 'Midterm Exam', students: 32 },
    { course: 'CS301', assessment: 'Assignment 2', students: 28 },
  ];

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Title style={styles.title}>Grade Management</Title>

        <Card style={styles.card}>
          <Card.Content>
            <Title style={styles.sectionTitle}>Pending Grades</Title>
            <List.Section>
              {pendingGrades.map((item, index) => (
                <List.Item
                  key={index}
                  title={item.assessment}
                  description={`${item.course} • ${item.students} students`}
                  right={() => <Chip compact>Pending</Chip>}
                />
              ))}
            </List.Section>
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
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  card: {
    elevation: 2,
  },
  sectionTitle: {
    fontSize: 18,
    marginBottom: 12,
  },
});

export default TeacherGradesScreen;