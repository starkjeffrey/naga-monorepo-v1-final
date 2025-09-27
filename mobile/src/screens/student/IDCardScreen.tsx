import React from 'react';
import { View, StyleSheet, ScrollView, Dimensions } from 'react-native';
import { Card, Title, Text, Avatar, Chip, Button, useTheme } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import QRCode from 'react-native-qrcode-svg';
import { useAuthStore } from '@/store/authStore';

const { width } = Dimensions.get('window');

const IDCardScreen: React.FC = () => {
  const theme = useTheme();
  const { user } = useAuthStore();

  const studentData = {
    name: user?.name || 'Student Name',
    studentId: user?.studentId || 'STU2024001',
    email: user?.email || 'student@pucsr.edu',
    department: user?.department || 'Computer Science',
    academicYear: user?.currentAcademicYear || '2024-2025',
    enrollmentStatus: user?.enrollmentStatus || 'active',
    profilePhoto: user?.profilePhoto,
    bloodGroup: 'O+',
    emergencyContact: '+91 98765 43210',
    issuedDate: '01 Aug 2024',
    validUntil: '31 Jul 2025',
  };

  const qrData = JSON.stringify({
    id: studentData.studentId,
    name: studentData.name,
    dept: studentData.department,
  });

  const downloadCard = () => {
    // Implementation for downloading ID card as image
    console.log('Downloading ID card...');
  };

  const shareCard = () => {
    // Implementation for sharing ID card
    console.log('Sharing ID card...');
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* ID Card Front */}
        <Card style={styles.idCard}>
          <View style={styles.cardHeader}>
            <View style={styles.schoolInfo}>
              <Icon name="school" size={32} color="#fff" />
              <View>
                <Text style={styles.schoolName}>NAGA UNIVERSITY</Text>
                <Text style={styles.schoolTagline}>Excellence in Education</Text>
              </View>
            </View>
          </View>

          <Card.Content style={styles.cardContent}>
            {/* Photo and Basic Info */}
            <View style={styles.photoSection}>
              {studentData.profilePhoto ? (
                <Avatar.Image
                  size={100}
                  source={{ uri: studentData.profilePhoto }}
                  style={styles.photo}
                />
              ) : (
                <Avatar.Text
                  size={100}
                  label={studentData.name.split(' ').map((n: string) => n[0]).join('')}
                  style={styles.photo}
                />
              )}
              <View style={styles.qrContainer}>
                <QRCode
                  value={qrData}
                  size={100}
                  color="#000"
                  backgroundColor="#fff"
                />
              </View>
            </View>

            {/* Student Details */}
            <View style={styles.detailsSection}>
              <Text style={styles.studentName}>{studentData.name}</Text>
              <View style={styles.detailRow}>
                <Text style={styles.label}>Student ID:</Text>
                <Text style={styles.value}>{studentData.studentId}</Text>
              </View>
              <View style={styles.detailRow}>
                <Text style={styles.label}>Department:</Text>
                <Text style={styles.value}>{studentData.department}</Text>
              </View>
              <View style={styles.detailRow}>
                <Text style={styles.label}>Academic Year:</Text>
                <Text style={styles.value}>{studentData.academicYear}</Text>
              </View>
              <View style={styles.detailRow}>
                <Text style={styles.label}>Blood Group:</Text>
                <Text style={styles.value}>{studentData.bloodGroup}</Text>
              </View>
            </View>

            {/* Status Badge */}
            <View style={styles.statusSection}>
              <Chip
                mode="flat"
                style={styles.statusChip}
                textStyle={styles.statusText}
              >
                ACTIVE STUDENT
              </Chip>
            </View>
          </Card.Content>

          <View style={styles.cardFooter}>
            <Text style={styles.footerText}>Valid Until: {studentData.validUntil}</Text>
          </View>
        </Card>

        {/* ID Card Back (Additional Info) */}
        <Card style={styles.idCardBack}>
          <View style={styles.backHeader}>
            <Text style={styles.backTitle}>ADDITIONAL INFORMATION</Text>
          </View>

          <Card.Content style={styles.backContent}>
            <View style={styles.infoRow}>
              <Icon name="email" size={20} color="#666" />
              <View style={styles.infoText}>
                <Text style={styles.infoLabel}>Email</Text>
                <Text style={styles.infoValue}>{studentData.email}</Text>
              </View>
            </View>

            <View style={styles.infoRow}>
              <Icon name="phone" size={20} color="#666" />
              <View style={styles.infoText}>
                <Text style={styles.infoLabel}>Emergency Contact</Text>
                <Text style={styles.infoValue}>{studentData.emergencyContact}</Text>
              </View>
            </View>

            <View style={styles.infoRow}>
              <Icon name="calendar" size={20} color="#666" />
              <View style={styles.infoText}>
                <Text style={styles.infoLabel}>Issued Date</Text>
                <Text style={styles.infoValue}>{studentData.issuedDate}</Text>
              </View>
            </View>

            <View style={styles.instructionsSection}>
              <Text style={styles.instructionsTitle}>Instructions:</Text>
              <Text style={styles.instructionsText}>
                • This card is non-transferable{'\n'}
                • Must be carried at all times on campus{'\n'}
                • Report immediately if lost or damaged{'\n'}
                • Valid only for the mentioned academic year
              </Text>
            </View>

            <View style={styles.contactSection}>
              <Text style={styles.contactTitle}>Contact Information:</Text>
              <Text style={styles.contactText}>
                Administrative Office: +91 12345 67890{'\n'}
                Email: admin@naga.edu{'\n'}
                Website: www.naga.edu
              </Text>
            </View>
          </Card.Content>
        </Card>

        {/* Action Buttons */}
        <View style={styles.actionButtons}>
          <Button
            mode="contained"
            icon="download"
            onPress={downloadCard}
            style={[styles.actionButton, { backgroundColor: theme.colors.primary }]}
          >
            Download Card
          </Button>
          <Button
            mode="outlined"
            icon="share-variant"
            onPress={shareCard}
            style={styles.actionButton}
          >
            Share Card
          </Button>
        </View>

        {/* Info Card */}
        <Card style={styles.infoCard}>
          <Card.Content>
            <View style={styles.infoHeader}>
              <Icon name="information" size={20} color={theme.colors.primary} />
              <Text style={styles.infoTitle}>Digital ID Card</Text>
            </View>
            <Text style={styles.infoDescription}>
              This digital ID card is valid and can be used for identification purposes
              within the campus. The QR code can be scanned for quick verification.
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
    padding: 16,
    paddingBottom: 32,
  },
  idCard: {
    marginBottom: 16,
    elevation: 4,
    borderRadius: 12,
    overflow: 'hidden',
  },
  cardHeader: {
    backgroundColor: '#1a365d',
    padding: 16,
  },
  schoolInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  schoolName: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
    letterSpacing: 1,
  },
  schoolTagline: {
    color: '#fff',
    fontSize: 10,
    opacity: 0.9,
  },
  cardContent: {
    padding: 16,
    backgroundColor: '#fff',
  },
  photoSection: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  photo: {
    borderWidth: 3,
    borderColor: '#1a365d',
  },
  qrContainer: {
    padding: 8,
    backgroundColor: '#fff',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  detailsSection: {
    marginBottom: 16,
  },
  studentName: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#1a365d',
    marginBottom: 12,
    textAlign: 'center',
  },
  detailRow: {
    flexDirection: 'row',
    marginBottom: 8,
  },
  label: {
    fontSize: 12,
    color: '#666',
    width: 100,
    fontWeight: '500',
  },
  value: {
    fontSize: 12,
    color: '#333',
    flex: 1,
  },
  statusSection: {
    alignItems: 'center',
    marginTop: 8,
  },
  statusChip: {
    backgroundColor: '#E8F5E9',
  },
  statusText: {
    color: '#4CAF50',
    fontWeight: 'bold',
    fontSize: 12,
  },
  cardFooter: {
    backgroundColor: '#f0f0f0',
    padding: 8,
    alignItems: 'center',
  },
  footerText: {
    fontSize: 10,
    color: '#666',
  },
  idCardBack: {
    marginBottom: 16,
    elevation: 3,
    borderRadius: 12,
    overflow: 'hidden',
  },
  backHeader: {
    backgroundColor: '#2196F3',
    padding: 12,
    alignItems: 'center',
  },
  backTitle: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
    letterSpacing: 0.5,
  },
  backContent: {
    padding: 16,
    backgroundColor: '#fff',
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
    gap: 12,
  },
  infoText: {
    flex: 1,
  },
  infoLabel: {
    fontSize: 10,
    color: '#666',
    marginBottom: 2,
  },
  infoValue: {
    fontSize: 14,
    color: '#333',
  },
  instructionsSection: {
    marginTop: 16,
    padding: 12,
    backgroundColor: '#FFF9E6',
    borderRadius: 8,
  },
  instructionsTitle: {
    fontSize: 12,
    fontWeight: 'bold',
    marginBottom: 8,
    color: '#333',
  },
  instructionsText: {
    fontSize: 11,
    lineHeight: 18,
    color: '#666',
  },
  contactSection: {
    marginTop: 16,
    padding: 12,
    backgroundColor: '#f5f5f5',
    borderRadius: 8,
  },
  contactTitle: {
    fontSize: 12,
    fontWeight: 'bold',
    marginBottom: 8,
    color: '#333',
  },
  contactText: {
    fontSize: 11,
    lineHeight: 18,
    color: '#666',
  },
  actionButtons: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 16,
  },
  actionButton: {
    flex: 1,
  },
  infoCard: {
    backgroundColor: '#E3F2FD',
    elevation: 1,
  },
  infoHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  infoTitle: {
    fontSize: 14,
    fontWeight: '600',
  },
  infoDescription: {
    fontSize: 12,
    color: '#666',
    lineHeight: 18,
  },
});

export default IDCardScreen;