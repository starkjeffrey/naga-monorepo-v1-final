import React from 'react';
import { View, StyleSheet, ScrollView, Text } from 'react-native';
import { Card, Title, Avatar, List, Button } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { useAuthStore } from '@/store/authStore';
import { useNavigation } from '@react-navigation/native';

const ProfileScreen: React.FC = () => {
  const navigation = useNavigation<any>();
  const { user, logout } = useAuthStore();

  const menuItems = [
    { title: 'ID Card', icon: 'card-account-details', route: 'IDCard' },
    { title: 'Permission Request', icon: 'file-document-edit', route: 'Permission' },
    { title: 'Profile Photo', icon: 'camera', route: 'ProfilePhoto' },
    { title: 'Finances', icon: 'wallet', route: 'Finances' },
    { title: 'Announcements', icon: 'bullhorn', route: 'Announcements' },
    { title: 'Messages', icon: 'message-text', route: 'Messages' },
  ];

  const handleLogout = async () => {
    await logout();
    // Navigation will be handled by RootNavigator based on auth state
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Card style={styles.profileCard}>
          <Card.Content style={styles.profileContent}>
            <Avatar.Text
              size={80}
              label={user?.name?.split(' ').map((n: string) => n[0]).join('') || 'U'}
            />
            <Title style={styles.userName}>{user?.name || 'Student'}</Title>
            <Text style={styles.userEmail}>{user?.email}</Text>
            <Text style={styles.userId}>ID: {user?.studentId || 'N/A'}</Text>
          </Card.Content>
        </Card>

        <Card style={styles.menuCard}>
          <List.Section>
            {menuItems.map((item, index) => (
              <List.Item
                key={index}
                title={item.title}
                left={(props) => <List.Icon {...props} icon={item.icon} />}
                right={(props) => <List.Icon {...props} icon="chevron-right" />}
                onPress={() => navigation.navigate(item.route)}
                style={styles.menuItem}
              />
            ))}
          </List.Section>
        </Card>

        <Card style={styles.settingsCard}>
          <Card.Content>
            <Title style={styles.sectionTitle}>Settings</Title>
            <List.Item
              title="Notifications"
              left={(props) => <List.Icon {...props} icon="bell" />}
              right={(props) => <List.Icon {...props} icon="chevron-right" />}
            />
            <List.Item
              title="Language"
              left={(props) => <List.Icon {...props} icon="translate" />}
              right={(props) => <List.Icon {...props} icon="chevron-right" />}
            />
            <List.Item
              title="Privacy"
              left={(props) => <List.Icon {...props} icon="shield-lock" />}
              right={(props) => <List.Icon {...props} icon="chevron-right" />}
            />
          </Card.Content>
        </Card>

        <Button
          mode="contained"
          onPress={handleLogout}
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
    paddingBottom: 32,
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
  menuCard: {
    marginBottom: 16,
    elevation: 1,
  },
  menuItem: {
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  settingsCard: {
    marginBottom: 16,
    elevation: 1,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 8,
  },
  logoutButton: {
    marginTop: 16,
  },
});

export default ProfileScreen;