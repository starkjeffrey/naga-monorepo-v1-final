import React from 'react';
import { View, Text, StyleSheet, Button, ScrollView } from 'react-native';
import { Provider as PaperProvider, Card, Title, DefaultTheme } from 'react-native-paper';
import { SafeAreaProvider } from 'react-native-safe-area-context';

const theme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    primary: '#2196F3',
    accent: '#4CAF50',
  },
};

export default function App() {
  const [role, setRole] = React.useState<'student' | 'teacher' | null>(null);

  if (!role) {
    return (
      <SafeAreaProvider>
        <PaperProvider theme={theme}>
          <View style={styles.container}>
            <Title style={styles.title}>NAGA SIS Mobile</Title>
            <Text style={styles.subtitle}>Choose your role to continue</Text>

            <Card style={styles.card}>
              <Card.Content>
                <Button title="Login as Student" onPress={() => setRole('student')} />
              </Card.Content>
            </Card>

            <Card style={styles.card}>
              <Card.Content>
                <Button title="Login as Teacher" onPress={() => setRole('teacher')} />
              </Card.Content>
            </Card>
          </View>
        </PaperProvider>
      </SafeAreaProvider>
    );
  }

  return (
    <SafeAreaProvider>
      <PaperProvider theme={theme}>
        <ScrollView style={styles.scrollView}>
          <View style={styles.container}>
            <Title style={styles.title}>
              {role === 'student' ? 'Student Dashboard' : 'Teacher Dashboard'}
            </Title>

            <Card style={styles.card}>
              <Card.Content>
                <Text>Welcome to NAGA SIS Mobile App!</Text>
                <Text>You are logged in as: {role}</Text>
              </Card.Content>
            </Card>

            <Card style={styles.card}>
              <Card.Content>
                <Title>Quick Actions</Title>
                {role === 'student' ? (
                  <>
                    <Text>• View Attendance</Text>
                    <Text>• Check Grades</Text>
                    <Text>• View Schedule</Text>
                    <Text>• ID Card</Text>
                  </>
                ) : (
                  <>
                    <Text>• Generate Attendance Code</Text>
                    <Text>• Mark Manual Attendance</Text>
                    <Text>• Enter Grades</Text>
                    <Text>• View Courses</Text>
                  </>
                )}
              </Card.Content>
            </Card>

            <Button title="Logout" onPress={() => setRole(null)} />
          </View>
        </ScrollView>
      </PaperProvider>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#f5f5f5',
    justifyContent: 'center',
  },
  scrollView: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 10,
    color: '#1a365d',
  },
  subtitle: {
    fontSize: 16,
    textAlign: 'center',
    marginBottom: 30,
    color: '#666',
  },
  card: {
    marginBottom: 16,
    elevation: 2,
  },
});