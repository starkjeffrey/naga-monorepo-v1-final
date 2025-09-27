import React from 'react';
import { View, StyleSheet, ScrollView, Text } from 'react-native';
import { Card, Title, Button, Avatar } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';

const ProfilePhotoScreen: React.FC = () => {
  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Title style={styles.title}>Update Profile Photo</Title>

        <Card style={styles.card}>
          <Card.Content style={styles.cardContent}>
            <Avatar.Text size={120} label="JS" style={styles.avatar} />
            <Text style={styles.instruction}>
              Upload a clear photo of yourself for your student profile
            </Text>
            <View style={styles.buttons}>
              <Button mode="contained" icon="camera" style={styles.button}>
                Take Photo
              </Button>
              <Button mode="outlined" icon="image" style={styles.button}>
                Choose from Gallery
              </Button>
            </View>
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
  cardContent: {
    alignItems: 'center',
    paddingVertical: 24,
  },
  avatar: {
    marginBottom: 24,
  },
  instruction: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    marginBottom: 24,
    paddingHorizontal: 20,
  },
  buttons: {
    gap: 12,
    width: '100%',
  },
  button: {
    marginBottom: 8,
  },
});

export default ProfilePhotoScreen;