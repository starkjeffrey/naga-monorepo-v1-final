import React from 'react';
import { View, StyleSheet, ScrollView } from 'react-native';
import { Card, Title, Text, Button, Avatar, useTheme } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { useNavigation } from '@react-navigation/native';
import { useAuthStore } from '@/store/authStore';

const RoleSwitcherScreen: React.FC = () => {
  const theme = useTheme();
  const navigation = useNavigation<any>();
  const { user, switchRole } = useAuthStore();

  const handleRoleSelect = (role: 'student' | 'teacher') => {
    switchRole(role);
    // Navigate to appropriate dashboard
    if (role === 'teacher') {
      navigation.reset({
        index: 0,
        routes: [{ name: 'Teacher' }],
      });
    } else {
      navigation.reset({
        index: 0,
        routes: [{ name: 'Student' }],
      });
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Header */}
        <View style={styles.header}>
          <Icon name="account-switch" size={64} color={theme.colors.primary} />
          <Title style={styles.title}>Choose Your Role</Title>
          <Text style={styles.subtitle}>
            As an MA student who teaches, you can switch between student and teacher views.
          </Text>
        </View>

        {/* Role Cards */}
        <View style={styles.cardsContainer}>
          {/* Student Role */}
          <Card style={styles.roleCard}>
            <Card.Content style={styles.roleCardContent}>
              <Avatar.Icon
                size={80}
                icon="school"
                style={[styles.roleIcon, { backgroundColor: '#2196F3' }]}
              />
              <Title style={styles.roleTitle}>Student</Title>
              <Text style={styles.roleDescription}>
                Access your courses, grades, attendance, and student resources.
              </Text>
              <View style={styles.featuresList}>
                <View style={styles.featureItem}>
                  <Icon name="check" size={16} color="#4CAF50" />
                  <Text style={styles.featureText}>View your attendance</Text>
                </View>
                <View style={styles.featureItem}>
                  <Icon name="check" size={16} color="#4CAF50" />
                  <Text style={styles.featureText}>Check your grades</Text>
                </View>
                <View style={styles.featureItem}>
                  <Icon name="check" size={16} color="#4CAF50" />
                  <Text style={styles.featureText}>Access class schedule</Text>
                </View>
                <View style={styles.featureItem}>
                  <Icon name="check" size={16} color="#4CAF50" />
                  <Text style={styles.featureText}>Student ID card</Text>
                </View>
              </View>
              <Button
                mode="contained"
                onPress={() => handleRoleSelect('student')}
                style={[styles.selectButton, { backgroundColor: '#2196F3' }]}
              >
                Continue as Student
              </Button>
            </Card.Content>
          </Card>

          {/* Teacher Role */}
          <Card style={styles.roleCard}>
            <Card.Content style={styles.roleCardContent}>
              <Avatar.Icon
                size={80}
                icon="teach"
                style={[styles.roleIcon, { backgroundColor: '#4CAF50' }]}
              />
              <Title style={styles.roleTitle}>Teacher</Title>
              <Text style={styles.roleDescription}>
                Manage your classes, take attendance, and enter grades for your students.
              </Text>
              <View style={styles.featuresList}>
                <View style={styles.featureItem}>
                  <Icon name="check" size={16} color="#4CAF50" />
                  <Text style={styles.featureText}>Generate attendance codes</Text>
                </View>
                <View style={styles.featureItem}>
                  <Icon name="check" size={16} color="#4CAF50" />
                  <Text style={styles.featureText}>Mark manual attendance</Text>
                </View>
                <View style={styles.featureItem}>
                  <Icon name="check" size={16} color="#4CAF50" />
                  <Text style={styles.featureText}>Enter student grades</Text>
                </View>
                <View style={styles.featureItem}>
                  <Icon name="check" size={16} color="#4CAF50" />
                  <Text style={styles.featureText}>View class statistics</Text>
                </View>
              </View>
              <Button
                mode="contained"
                onPress={() => handleRoleSelect('teacher')}
                style={[styles.selectButton, { backgroundColor: '#4CAF50' }]}
              >
                Continue as Teacher
              </Button>
            </Card.Content>
          </Card>
        </View>

        {/* Info Section */}
        <Card style={styles.infoCard}>
          <Card.Content>
            <View style={styles.infoHeader}>
              <Icon name="information" size={20} color={theme.colors.primary} />
              <Text style={styles.infoTitle}>About Role Switching</Text>
            </View>
            <Text style={styles.infoText}>
              You can switch between roles at any time from your profile menu. Your data and
              progress in both roles are saved separately.
            </Text>
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
    padding: 20,
  },
  header: {
    alignItems: 'center',
    marginBottom: 30,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    marginTop: 16,
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    paddingHorizontal: 20,
  },
  cardsContainer: {
    gap: 20,
  },
  roleCard: {
    elevation: 3,
  },
  roleCardContent: {
    alignItems: 'center',
    paddingVertical: 24,
  },
  roleIcon: {
    marginBottom: 16,
  },
  roleTitle: {
    fontSize: 24,
    fontWeight: '600',
    marginBottom: 8,
  },
  roleDescription: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    marginBottom: 20,
    paddingHorizontal: 20,
  },
  featuresList: {
    width: '100%',
    paddingHorizontal: 20,
    marginBottom: 20,
  },
  featureItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  featureText: {
    fontSize: 14,
    color: '#333',
  },
  selectButton: {
    paddingHorizontal: 32,
  },
  infoCard: {
    marginTop: 20,
    backgroundColor: '#E3F2FD',
  },
  infoHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  infoTitle: {
    fontSize: 16,
    fontWeight: '600',
  },
  infoText: {
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
  },
});

export default RoleSwitcherScreen;