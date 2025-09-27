import React from 'react';
import { View, StyleSheet, ScrollView, Text } from 'react-native';
import { Card, Title, TextInput, Button } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';

const PermissionScreen: React.FC = () => {
  const [reason, setReason] = React.useState('');
  const [startDate, setStartDate] = React.useState('');
  const [endDate, setEndDate] = React.useState('');

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Title style={styles.title}>Request Permission</Title>

        <Card style={styles.card}>
          <Card.Content>
            <TextInput
              label="Reason for Leave"
              value={reason}
              onChangeText={setReason}
              mode="outlined"
              multiline
              numberOfLines={4}
              style={styles.input}
            />
            <TextInput
              label="Start Date"
              value={startDate}
              onChangeText={setStartDate}
              mode="outlined"
              style={styles.input}
            />
            <TextInput
              label="End Date"
              value={endDate}
              onChangeText={setEndDate}
              mode="outlined"
              style={styles.input}
            />
            <Button mode="contained" style={styles.button}>
              Submit Request
            </Button>
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
  button: {
    marginTop: 8,
  },
});

export default PermissionScreen;