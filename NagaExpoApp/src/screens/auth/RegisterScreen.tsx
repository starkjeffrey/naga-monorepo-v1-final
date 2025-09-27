import React, { useState } from 'react';
import {
  View,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from 'react-native';
import {
  Text,
  TextInput,
  Button,
  Card,
  Title,
  Paragraph,
} from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';

const RegisterScreen: React.FC = () => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleRegister = async () => {
    if (!name || !email || !password || !confirmPassword) {
      setError('Please fill in all fields');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      // Handle registration logic here
      console.log('Registration successful');
    } catch (err) {
      setError('Registration failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.flex}
      >
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <View style={styles.content}>
            <Card style={styles.card}>
              <Card.Content>
                <Title style={styles.title}>Create Account</Title>
                <Paragraph style={styles.subtitle}>
                  Join NAGA Mobile today
                </Paragraph>

                <TextInput
                  label="Full Name"
                  value={name}
                  onChangeText={setName}
                  mode="outlined"
                  style={styles.input}
                  disabled={isLoading}
                />

                <TextInput
                  label="Email"
                  value={email}
                  onChangeText={setEmail}
                  mode="outlined"
                  keyboardType="email-address"
                  autoCapitalize="none"
                  style={styles.input}
                  disabled={isLoading}
                />

                <TextInput
                  label="Password"
                  value={password}
                  onChangeText={setPassword}
                  mode="outlined"
                  secureTextEntry
                  style={styles.input}
                  disabled={isLoading}
                />

                <TextInput
                  label="Confirm Password"
                  value={confirmPassword}
                  onChangeText={setConfirmPassword}
                  mode="outlined"
                  secureTextEntry
                  style={styles.input}
                  disabled={isLoading}
                />

                {error ? (
                  <Text style={styles.errorText}>{error}</Text>
                ) : null}

                <Button
                  mode="contained"
                  onPress={handleRegister}
                  loading={isLoading}
                  disabled={isLoading}
                  style={styles.registerButton}
                >
                  Create Account
                </Button>
              </Card.Content>
            </Card>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  flex: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
  },
  content: {
    padding: 20,
    justifyContent: 'center',
  },
  card: {
    elevation: 4,
    borderRadius: 12,
  },
  title: {
    textAlign: 'center',
    marginBottom: 8,
    fontSize: 28,
    fontWeight: 'bold',
    color: '#2196F3',
  },
  subtitle: {
    textAlign: 'center',
    marginBottom: 32,
    color: '#666',
  },
  input: {
    marginBottom: 16,
  },
  registerButton: {
    marginTop: 16,
    paddingVertical: 6,
  },
  errorText: {
    color: '#f44336',
    textAlign: 'center',
    marginBottom: 16,
  },
});

export default RegisterScreen;