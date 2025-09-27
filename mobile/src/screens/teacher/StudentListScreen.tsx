import React from 'react';
import { View, StyleSheet, ScrollView } from 'react-native';
import { Card, Title, List } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';

const StudentListScreen: React.FC = () => {
  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Title style={styles.title}>Student List</Title>
        <Card style={styles.card}>
          <List.Section>
            <List.Item title="John Doe" description="CS101" />
            <List.Item title="Jane Smith" description="CS102" />
            <List.Item title="Bob Johnson" description="CS103" />
          </List.Section>
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

export default StudentListScreen;