/**
 * Naga SIS Mobile App
 * React Native/Expo implementation with Google OAuth authentication
 */

import React from 'react'
import {
  StyleSheet,
  Text,
  View,
  StatusBar,
  SafeAreaView,
  ScrollView,
  TouchableOpacity,
} from 'react-native'
import { GoogleSignInButton } from './src/components/GoogleSignInButton'
import { useMobileAuth } from './src/services/mobileAuth'
import type { GoogleAuthResponse } from './src/types/errors'

export default function App() {
  const { isAuthenticated, authData, isLoading, logout } = useMobileAuth()

  const handleSignInSuccess = (authResponse: GoogleAuthResponse) => {
    console.log('Sign in successful:', authResponse)
  }

  const handleSignInError = (error: string) => {
    console.error('Sign in failed:', error)
  }

  const handleLogout = async () => {
    try {
      await logout()
    } catch (error) {
      console.error('Logout failed:', error)
    }
  }

  if (isLoading) {
    return (
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="dark-content" backgroundColor="#ffffff" />
        <View style={styles.loadingContainer}>
          <Text style={styles.loadingText}>Loading...</Text>
        </View>
      </SafeAreaView>
    )
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="#ffffff" />
      <ScrollView contentContainerStyle={styles.scrollContainer}>
        <View style={styles.header}>
          <Text style={styles.title}>Naga SIS</Text>
          <Text style={styles.subtitle}>Student Information System</Text>
        </View>

        {!isAuthenticated ? (
          <View style={styles.authContainer}>
            <Text style={styles.welcomeText}>
              Welcome to Naga SIS Mobile App
            </Text>
            <Text style={styles.instructionText}>
              Please sign in with your PUCSR email address
            </Text>

            <GoogleSignInButton
              onSuccess={handleSignInSuccess}
              onError={handleSignInError}
              style={styles.signInButton}
            />
          </View>
        ) : (
          <View style={styles.authenticatedContainer}>
            <Text style={styles.welcomeBackText}>
              Welcome back, {authData?.profile?.full_name || authData?.email}!
            </Text>

            <View style={styles.profileCard}>
              <Text style={styles.profileLabel}>Student ID:</Text>
              <Text style={styles.profileValue}>{authData?.studentId}</Text>

              <Text style={styles.profileLabel}>Email:</Text>
              <Text style={styles.profileValue}>{authData?.email}</Text>

              <Text style={styles.profileLabel}>Status:</Text>
              <Text style={styles.profileValue}>
                {authData?.profile?.current_status || 'Active'}
              </Text>
            </View>

            <View style={styles.actionsContainer}>
              <Text style={styles.actionsTitle}>Quick Actions</Text>
              <Text style={styles.placeholderText}>
                • View Class Schedule
              </Text>
              <Text style={styles.placeholderText}>
                • Check Grades
              </Text>
              <Text style={styles.placeholderText}>
                • View Financial Account
              </Text>
              <Text style={styles.placeholderText}>
                • Academic Records
              </Text>
            </View>

            <TouchableOpacity style={styles.logoutContainer} onPress={handleLogout}>
              <Text style={styles.logoutButton}>Logout</Text>
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  scrollContainer: {
    flexGrow: 1,
    padding: 20,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    fontSize: 18,
    color: '#666',
  },
  header: {
    alignItems: 'center',
    marginBottom: 40,
    paddingTop: 20,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#1a365d',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
    fontWeight: '500',
  },
  authContainer: {
    alignItems: 'center',
    paddingHorizontal: 20,
  },
  welcomeText: {
    fontSize: 24,
    fontWeight: '600',
    color: '#1a365d',
    textAlign: 'center',
    marginBottom: 16,
  },
  instructionText: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    marginBottom: 40,
  },
  signInButton: {
    width: '100%',
    maxWidth: 300,
  },
  authenticatedContainer: {
    flex: 1,
  },
  welcomeBackText: {
    fontSize: 24,
    fontWeight: '600',
    color: '#1a365d',
    textAlign: 'center',
    marginBottom: 30,
  },
  profileCard: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 20,
    marginBottom: 30,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 3,
  },
  profileLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#666',
    marginTop: 12,
    marginBottom: 4,
  },
  profileValue: {
    fontSize: 16,
    color: '#1a365d',
    marginBottom: 8,
  },
  actionsContainer: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 20,
    marginBottom: 30,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 3,
  },
  actionsTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1a365d',
    marginBottom: 16,
  },
  placeholderText: {
    fontSize: 16,
    color: '#666',
    marginBottom: 12,
  },
  logoutContainer: {
    alignItems: 'center',
    marginTop: 20,
  },
  logoutButton: {
    fontSize: 16,
    color: '#dc3545',
    fontWeight: '600',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderWidth: 1,
    borderColor: '#dc3545',
    borderRadius: 8,
    textAlign: 'center',
    minWidth: 100,
  },
})
