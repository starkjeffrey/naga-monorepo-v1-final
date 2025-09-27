import React from 'react';
import { View, StyleSheet, ScrollView, Text } from 'react-native';
import { Card, Title, Chip, ProgressBar } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';

const GradesScreen: React.FC = () => {
  const courses = [
    {
      id: '1',
      name: 'Database Systems',
      code: 'CS301',
      credits: 4,
      grade: 'A',
      percentage: 92,
      assessments: [
        { name: 'Midterm', score: 88, total: 100 },
        { name: 'Assignment 1', score: 95, total: 100 },
        { name: 'Assignment 2', score: 92, total: 100 },
        { name: 'Final', score: 94, total: 100 },
      ],
    },
    {
      id: '2',
      name: 'Web Development',
      code: 'CS302',
      credits: 4,
      grade: 'B+',
      percentage: 86,
      assessments: [
        { name: 'Project 1', score: 85, total: 100 },
        { name: 'Midterm', score: 82, total: 100 },
        { name: 'Project 2', score: 90, total: 100 },
      ],
    },
  ];

  const getGradeColor = (grade: string) => {
    if (grade.startsWith('A')) return '#4CAF50';
    if (grade.startsWith('B')) return '#2196F3';
    if (grade.startsWith('C')) return '#FF9800';
    return '#f44336';
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Title style={styles.title}>Academic Performance</Title>

        <Card style={styles.summaryCard}>
          <Card.Content>
            <View style={styles.summaryRow}>
              <View style={styles.summaryItem}>
                <Text style={styles.summaryLabel}>Current GPA</Text>
                <Text style={styles.summaryValue}>3.67</Text>
              </View>
              <View style={styles.summaryItem}>
                <Text style={styles.summaryLabel}>Credits Earned</Text>
                <Text style={styles.summaryValue}>48</Text>
              </View>
              <View style={styles.summaryItem}>
                <Text style={styles.summaryLabel}>Semester</Text>
                <Text style={styles.summaryValue}>Fall 2024</Text>
              </View>
            </View>
          </Card.Content>
        </Card>

        {courses.map((course) => (
          <Card key={course.id} style={styles.courseCard}>
            <Card.Content>
              <View style={styles.courseHeader}>
                <View>
                  <Text style={styles.courseName}>{course.name}</Text>
                  <Text style={styles.courseCode}>{course.code} • {course.credits} credits</Text>
                </View>
                <Chip
                  mode="flat"
                  style={{ backgroundColor: getGradeColor(course.grade) + '20' }}
                  textStyle={{ color: getGradeColor(course.grade) }}
                >
                  {course.grade}
                </Chip>
              </View>

              <View style={styles.progressSection}>
                <Text style={styles.percentageText}>{course.percentage}%</Text>
                <ProgressBar
                  progress={course.percentage / 100}
                  color={getGradeColor(course.grade)}
                  style={styles.progressBar}
                />
              </View>

              <View style={styles.assessments}>
                <Text style={styles.assessmentsTitle}>Assessments</Text>
                {course.assessments.map((assessment, index) => (
                  <View key={index} style={styles.assessmentItem}>
                    <Text style={styles.assessmentName}>{assessment.name}</Text>
                    <Text style={styles.assessmentScore}>
                      {assessment.score}/{assessment.total}
                    </Text>
                  </View>
                ))}
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
  summaryCard: {
    marginBottom: 16,
    elevation: 2,
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  summaryItem: {
    alignItems: 'center',
  },
  summaryLabel: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
  },
  summaryValue: {
    fontSize: 20,
    fontWeight: 'bold',
  },
  courseCard: {
    marginBottom: 16,
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
  progressSection: {
    marginBottom: 16,
  },
  percentageText: {
    fontSize: 14,
    fontWeight: '500',
    marginBottom: 4,
  },
  progressBar: {
    height: 6,
    borderRadius: 3,
  },
  assessments: {
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
    paddingTop: 12,
  },
  assessmentsTitle: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  assessmentItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 4,
  },
  assessmentName: {
    fontSize: 13,
    color: '#666',
  },
  assessmentScore: {
    fontSize: 13,
    fontWeight: '500',
  },
});

export default GradesScreen;