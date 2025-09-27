import React from 'react';
import { View, StyleSheet, ScrollView, Text } from 'react-native';
import { Card, Title, Button } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';

const TeacherAttendanceScreen: React.FC = () => {
  const navigation = useNavigation<any>();

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Title style={styles.title}>Attendance Management</Title>

        <Card style={styles.card}>
          <Card.Content>
            <Title style={styles.sectionTitle}>Quick Actions</Title>
            <Button
              mode="contained"
              icon="qrcode"
              onPress={() => navigation.navigate('GenerateCode')}
              style={styles.button}
            >
              Generate Attendance Code
            </Button>
            <Button
              mode="outlined"
              icon="clipboard-check"
              onPress={() => navigation.navigate('ManualAttendance')}
              style={styles.button}
            >
              Manual Attendance
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
  sectionTitle: {
    fontSize: 18,
    marginBottom: 16,
  },
  button: {
    marginBottom: 12,
  },
});

export default TeacherAttendanceScreen;