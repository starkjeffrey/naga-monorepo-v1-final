import React from 'react';
import { View, StyleSheet, ScrollView } from 'react-native';
import { Card, Title, TextInput, Button } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';

const GradeEntryScreen: React.FC = () => {
  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Title style={styles.title}>Enter Grades</Title>
        <Card style={styles.card}>
          <Card.Content>
            <TextInput
              label="Student ID"
              mode="outlined"
              style={styles.input}
            />
            <TextInput
              label="Grade"
              mode="outlined"
              style={styles.input}
            />
            <Button mode="contained">Submit Grade</Button>
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
  input: {
    marginBottom: 16,
  },
});

export default GradeEntryScreen;