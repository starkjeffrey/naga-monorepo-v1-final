import React from 'react';
import { View, StyleSheet, ScrollView, Text } from 'react-native';
import { Card, Title, List, Checkbox } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';

const ManualAttendanceScreen: React.FC = () => {
  const [checkedStudents, setCheckedStudents] = React.useState<string[]>([]);

  const students = [
    { id: '1', name: 'John Doe', rollNo: 'CS101' },
    { id: '2', name: 'Jane Smith', rollNo: 'CS102' },
    { id: '3', name: 'Bob Johnson', rollNo: 'CS103' },
  ];

  const toggleStudent = (studentId: string) => {
    setCheckedStudents(prev =>
      prev.includes(studentId)
        ? prev.filter(id => id !== studentId)
        : [...prev, studentId]
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Title style={styles.title}>Manual Attendance</Title>

        <Card style={styles.card}>
          <Card.Content>
            <Title style={styles.sectionTitle}>Student List</Title>
            <List.Section>
              {students.map((student) => (
                <List.Item
                  key={student.id}
                  title={student.name}
                  description={`Roll: ${student.rollNo}`}
                  left={() => (
                    <Checkbox
                      status={checkedStudents.includes(student.id) ? 'checked' : 'unchecked'}
                      onPress={() => toggleStudent(student.id)}
                    />
                  )}
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

export default ManualAttendanceScreen;