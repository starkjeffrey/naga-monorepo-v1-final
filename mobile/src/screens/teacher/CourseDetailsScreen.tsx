import React from 'react';
import { View, StyleSheet, ScrollView, Text } from 'react-native';
import { Card, Title } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';

const CourseDetailsScreen: React.FC = () => {
  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Title style={styles.title}>Course Details</Title>
        <Card style={styles.card}>
          <Card.Content>
            <Text>Course details will be displayed here</Text>
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
});

export default CourseDetailsScreen;