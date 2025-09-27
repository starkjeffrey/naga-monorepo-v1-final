import React from 'react';
import { View, StyleSheet, ScrollView, Text } from 'react-native';
import { Card, Title, Chip } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';

const AnnouncementsScreen: React.FC = () => {
  const announcements = [
    {
      id: '1',
      title: 'Mid-Semester Exams Schedule',
      content: 'Mid-semester exams will begin from October 15, 2024. Detailed timetable available on the portal.',
      date: '2024-09-25',
      category: 'Academic',
      isNew: true,
    },
    {
      id: '2',
      title: 'Library Extended Hours',
      content: 'Library will remain open till 11 PM during exam period.',
      date: '2024-09-24',
      category: 'Facility',
      isNew: true,
    },
    {
      id: '3',
      title: 'Cultural Fest Registration',
      content: 'Registration for Annual Cultural Fest is now open. Last date: September 30.',
      date: '2024-09-20',
      category: 'Event',
      isNew: false,
    },
  ];

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'Academic': return '#2196F3';
      case 'Facility': return '#4CAF50';
      case 'Event': return '#FF9800';
      default: return '#9E9E9E';
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Title style={styles.title}>Announcements</Title>

        {announcements.map((announcement) => (
          <Card key={announcement.id} style={styles.card}>
            <Card.Content>
              <View style={styles.header}>
                <View style={styles.titleRow}>
                  <Text style={styles.announcementTitle}>{announcement.title}</Text>
                  {announcement.isNew && (
                    <Chip compact style={styles.newChip} textStyle={styles.newChipText}>
                      NEW
                    </Chip>
                  )}
                </View>
                <Chip
                  compact
                  style={{
                    backgroundColor: getCategoryColor(announcement.category) + '20',
                  }}
                  textStyle={{
                    color: getCategoryColor(announcement.category),
                    fontSize: 10,
                  }}
                >
                  {announcement.category}
                </Chip>
              </View>
              <Text style={styles.content}>{announcement.content}</Text>
              <Text style={styles.date}>{announcement.date}</Text>
            </Card.Content>
          </Card>
        ))}
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
    marginBottom: 12,
    elevation: 1,
  },
  header: {
    marginBottom: 8,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  announcementTitle: {
    fontSize: 16,
    fontWeight: '600',
    flex: 1,
  },
  newChip: {
    backgroundColor: '#f44336',
    marginLeft: 8,
  },
  newChipText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: 'bold',
  },
  content: {
    fontSize: 14,
    color: '#666',
    marginBottom: 8,
    lineHeight: 20,
  },
  date: {
    fontSize: 12,
    color: '#999',
  },
});

export default AnnouncementsScreen;