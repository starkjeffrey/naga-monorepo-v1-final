import React from 'react';
import { View, StyleSheet, ScrollView } from 'react-native';
import { Card, Title, List, Text } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';

const GradesScreen: React.FC = () => {
  const grades = [
    { id: 1, course: 'Mathematics', grade: 'A', points: 4.0 },
    { id: 2, course: 'Physics', grade: 'B+', points: 3.5 },
    { id: 3, course: 'Chemistry', grade: 'A-', points: 3.7 },
    { id: 4, course: 'Biology', grade: 'A', points: 4.0 },
  ];

  const getGradeColor = (grade: string) => {
    if (grade.startsWith('A')) return '#4CAF50';
    if (grade.startsWith('B')) return '#2196F3';
    if (grade.startsWith('C')) return '#FF9800';
    return '#f44336';
  };

  const gpa = grades.reduce((acc, curr) => acc + curr.points, 0) / grades.length;

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Card style={styles.gpaCard}>
          <Card.Content style={styles.gpaContent}>
            <Title>Current GPA</Title>
            <Text style={styles.gpaValue}>{gpa.toFixed(2)}</Text>
          </Card.Content>
        </Card>

        <Card style={styles.card}>
          <Card.Content>
            <Title>Course Grades</Title>
            {grades.map((grade) => (
              <List.Item
                key={grade.id}
                title={grade.course}
                description={`${grade.points} points`}
                right={() => (
                  <Text style={[styles.gradeText, { color: getGradeColor(grade.grade) }]}>
                    {grade.grade}
                  </Text>
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
  gpaCard: {
    marginBottom: 16,
    elevation: 2,
  },
  gpaContent: {
    alignItems: 'center',
  },
  gpaValue: {
    fontSize: 48,
    fontWeight: 'bold',
    color: '#2196F3',
    marginTop: 8,
  },
  card: {
    elevation: 2,
  },
  gradeText: {
    fontSize: 18,
    fontWeight: 'bold',
    alignSelf: 'center',
  },
});

export default GradesScreen;