import React from 'react';
import { View, StyleSheet, ScrollView, Text } from 'react-native';
import { Card, Title, List, Avatar } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';

const MessagesScreen: React.FC = () => {
  const messages = [
    {
      id: '1',
      sender: 'Prof. Smith',
      subject: 'Assignment Feedback',
      preview: 'Your recent assignment submission has been reviewed...',
      time: '2 hours ago',
      unread: true,
    },
    {
      id: '2',
      sender: 'Academic Office',
      subject: 'Registration Reminder',
      preview: 'Course registration for next semester starts...',
      time: 'Yesterday',
      unread: false,
    },
    {
      id: '3',
      sender: 'Library',
      subject: 'Book Return Due',
      preview: 'Please return the borrowed books by...',
      time: '2 days ago',
      unread: false,
    },
  ];

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Title style={styles.title}>Messages</Title>

        <Card style={styles.card}>
          <List.Section>
            {messages.map((message) => (
              <List.Item
                key={message.id}
                title={message.subject}
                description={message.preview}
                left={(props) => (
                  <Avatar.Text
                    {...props}
                    size={40}
                    label={message.sender.split(' ').map(n => n[0]).join('')}
                    style={message.unread ? styles.unreadAvatar : undefined}
                  />
                )}
                right={() => (
                  <View style={styles.messageRight}>
                    <Text style={styles.time}>{message.time}</Text>
                    {message.unread && <View style={styles.unreadDot} />}
                  </View>
                )}
                titleStyle={message.unread ? styles.unreadTitle : undefined}
                style={styles.messageItem}
              />
            ))}
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
  messageItem: {
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  messageRight: {
    alignItems: 'flex-end',
  },
  time: {
    fontSize: 12,
    color: '#666',
  },
  unreadDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#2196F3',
    marginTop: 4,
  },
  unreadTitle: {
    fontWeight: '600',
  },
  unreadAvatar: {
    backgroundColor: '#2196F3',
  },
});

export default MessagesScreen;