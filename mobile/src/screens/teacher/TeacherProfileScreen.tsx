import React from 'react';
import { View, StyleSheet, ScrollView, Text } from 'react-native';
import { Card, Title, Avatar, Button } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuthStore } from '@/store/authStore';

const TeacherProfileScreen: React.FC = () => {
  const { user, logout } = useAuthStore();

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Card style={styles.profileCard}>
          <Card.Content style={styles.profileContent}>
            <Avatar.Text
              size={80}
              label={user?.name?.split(' ').map((n: string) => n[0]).join('') || 'T'}
            />
            <Title style={styles.userName}>{user?.name || 'Teacher'}</Title>
            <Text style={styles.userEmail}>{user?.email}</Text>
            <Text style={styles.userId}>Teacher ID: {user?.teacherId || 'N/A'}</Text>
          </Card.Content>
        </Card>

        <Button
          mode="contained"
          onPress={logout}
          style={styles.logoutButton}
          buttonColor="#f44336"
        >
          Logout
        </Button>
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
  profileCard: {
    marginBottom: 16,
    elevation: 2,
  },
  profileContent: {
    alignItems: 'center',
    paddingVertical: 20,
  },
  userName: {
    fontSize: 20,
    fontWeight: 'bold',
    marginTop: 12,
  },
  userEmail: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
  userId: {
    fontSize: 12,
    color: '#888',
    marginTop: 4,
  },
  logoutButton: {
    marginTop: 16,
  },
});

export default TeacherProfileScreen;