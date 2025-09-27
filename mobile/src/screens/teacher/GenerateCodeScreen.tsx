import React, { useState, useEffect } from 'react';
import { View, StyleSheet, ScrollView, Share, Pressable } from 'react-native';
import { Card, Title, Text, Button, Chip, useTheme, TextInput, SegmentedButtons, ActivityIndicator } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import QRCode from 'react-native-qrcode-svg';
import { useNavigation } from '@react-navigation/native';

interface Course {
  id: string;
  name: string;
  code: string;
  students: number;
}

const GenerateCodeScreen: React.FC = () => {
  const theme = useTheme();
  const navigation = useNavigation();
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);
  const [codeType, setCodeType] = useState<'numeric' | 'qr'>('numeric');
  const [validityMinutes, setValidityMinutes] = useState('5');
  const [generatedCode, setGeneratedCode] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [timeRemaining, setTimeRemaining] = useState<number>(0);

  const courses: Course[] = [
    { id: '1', name: 'Computer Science 101', code: 'CS101', students: 32 },
    { id: '2', name: 'Database Systems', code: 'CS301', students: 28 },
    { id: '3', name: 'Web Development', code: 'CS302', students: 35 },
    { id: '4', name: 'Mobile Computing', code: 'CS303', students: 30 },
  ];

  useEffect(() => {
    if (timeRemaining > 0) {
      const timer = setTimeout(() => {
        setTimeRemaining(timeRemaining - 1);
      }, 1000);
      return () => clearTimeout(timer);
    } else if (timeRemaining === 0 && generatedCode) {
      // Code expired
      setGeneratedCode(null);
    }
  }, [timeRemaining, generatedCode]);

  const generateAttendanceCode = () => {
    if (!selectedCourse) return;

    setIsGenerating(true);

    // Simulate API call
    setTimeout(() => {
      // Generate a 6-digit code
      const code = Math.floor(100000 + Math.random() * 900000).toString();
      setGeneratedCode(code);
      setTimeRemaining(parseInt(validityMinutes) * 60);
      setIsGenerating(false);
    }, 1000);
  };

  const shareCode = async () => {
    if (!generatedCode || !selectedCourse) return;

    try {
      const message = `Attendance Code for ${selectedCourse.name} (${selectedCourse.code}):\n\n${generatedCode}\n\nValid for ${validityMinutes} minutes.\nOpen Naga SIS app and enter this code to mark your attendance.`;

      await Share.share({
        message,
        title: 'Attendance Code',
      });
    } catch (error) {
      console.error('Error sharing code:', error);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const regenerateCode = () => {
    setGeneratedCode(null);
    generateAttendanceCode();
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {!generatedCode ? (
          <>
            {/* Course Selection */}
            <Card style={styles.card}>
              <Card.Content>
                <Title style={styles.cardTitle}>Select Course</Title>
                <View style={styles.courseList}>
                  {courses.map((course) => (
                    <Pressable
                      key={course.id}
                      onPress={() => setSelectedCourse(course)}
                    >
                      <Card
                        style={[
                          styles.courseCard,
                          selectedCourse?.id === course.id && styles.selectedCourseCard,
                        ]}
                      >
                        <Card.Content style={styles.courseCardContent}>
                          <View style={styles.courseInfo}>
                            <Text style={styles.courseName}>{course.name}</Text>
                            <Text style={styles.courseCode}>{course.code}</Text>
                          </View>
                          <View style={styles.courseStats}>
                            <Icon name="account-group" size={16} color="#666" />
                            <Text style={styles.studentCount}>{course.students}</Text>
                          </View>
                          {selectedCourse?.id === course.id && (
                            <Icon name="check-circle" size={20} color={theme.colors.primary} />
                          )}
                        </Card.Content>
                      </Card>
                    </Pressable>
                  ))}
                </View>
              </Card.Content>
            </Card>

            {/* Code Settings */}
            <Card style={styles.card}>
              <Card.Content>
                <Title style={styles.cardTitle}>Code Settings</Title>

                <Text style={styles.label}>Code Type</Text>
                <SegmentedButtons
                  value={codeType}
                  onValueChange={(value) => setCodeType(value as 'numeric' | 'qr')}
                  buttons={[
                    {
                      value: 'numeric',
                      label: 'Numeric Code',
                      icon: 'numeric',
                    },
                    {
                      value: 'qr',
                      label: 'QR Code',
                      icon: 'qrcode',
                    },
                  ]}
                  style={styles.segmentedButtons}
                />

                <Text style={styles.label}>Validity Duration</Text>
                <View style={styles.validityOptions}>
                  {['2', '5', '10', '15'].map((minutes) => (
                    <Chip
                      key={minutes}
                      mode="outlined"
                      selected={validityMinutes === minutes}
                      onPress={() => setValidityMinutes(minutes)}
                      style={styles.validityChip}
                    >
                      {minutes} min
                    </Chip>
                  ))}
                </View>

                <TextInput
                  label="Custom duration (minutes)"
                  value={validityMinutes}
                  onChangeText={setValidityMinutes}
                  keyboardType="numeric"
                  mode="outlined"
                  style={styles.customInput}
                />
              </Card.Content>
            </Card>

            {/* Generate Button */}
            <Button
              mode="contained"
              onPress={generateAttendanceCode}
              disabled={!selectedCourse || isGenerating}
              loading={isGenerating}
              style={styles.generateButton}
              contentStyle={styles.generateButtonContent}
            >
              Generate Attendance Code
            </Button>
          </>
        ) : (
          <>
            {/* Generated Code Display */}
            <Card style={styles.codeCard}>
              <Card.Content style={styles.codeCardContent}>
                <View style={styles.codeHeader}>
                  <Title style={styles.codeTitle}>Attendance Code</Title>
                  <Chip
                    mode="flat"
                    style={[
                      styles.timerChip,
                      timeRemaining <= 60 && styles.timerChipWarning,
                    ]}
                  >
                    <Icon name="clock-outline" size={16} />
                    {' '}
                    {formatTime(timeRemaining)}
                  </Chip>
                </View>

                <Card style={styles.courseInfoCard}>
                  <Card.Content>
                    <Text style={styles.courseNameDisplay}>{selectedCourse?.name}</Text>
                    <Text style={styles.courseCodeDisplay}>{selectedCourse?.code}</Text>
                  </Card.Content>
                </Card>

                {codeType === 'numeric' ? (
                  <View style={styles.numericCodeContainer}>
                    <Text style={styles.numericCode}>{generatedCode}</Text>
                    <Text style={styles.codeInstruction}>
                      Share this code with your students
                    </Text>
                  </View>
                ) : (
                  <View style={styles.qrCodeContainer}>
                    <QRCode
                      value={generatedCode}
                      size={200}
                      color="#000"
                      backgroundColor="#fff"
                    />
                    <Text style={styles.codeInstruction}>
                      Students can scan this QR code
                    </Text>
                  </View>
                )}

                {/* Action Buttons */}
                <View style={styles.actionButtons}>
                  <Button
                    mode="outlined"
                    icon="share-variant"
                    onPress={shareCode}
                    style={styles.actionButton}
                  >
                    Share Code
                  </Button>
                  <Button
                    mode="contained"
                    icon="refresh"
                    onPress={regenerateCode}
                    style={styles.actionButton}
                  >
                    New Code
                  </Button>
                </View>

                {/* Live Tracking */}
                <Card style={styles.trackingCard}>
                  <Card.Content>
                    <View style={styles.trackingHeader}>
                      <Text style={styles.trackingTitle}>Live Tracking</Text>
                      <ActivityIndicator size="small" color={theme.colors.primary} />
                    </View>
                    <View style={styles.trackingStats}>
                      <View style={styles.trackingStat}>
                        <Text style={styles.trackingValue}>0</Text>
                        <Text style={styles.trackingLabel}>Marked</Text>
                      </View>
                      <View style={styles.trackingStat}>
                        <Text style={styles.trackingValue}>{selectedCourse?.students}</Text>
                        <Text style={styles.trackingLabel}>Total</Text>
                      </View>
                      <View style={styles.trackingStat}>
                        <Text style={styles.trackingValue}>0%</Text>
                        <Text style={styles.trackingLabel}>Present</Text>
                      </View>
                    </View>
                  </Card.Content>
                </Card>
              </Card.Content>
            </Card>

            {/* Actions */}
            <Button
              mode="text"
              onPress={() => setGeneratedCode(null)}
              style={styles.backButton}
            >
              Generate for Another Course
            </Button>

            <Button
              mode="contained-tonal"
              icon="clipboard-check"
              onPress={() => navigation.navigate('ManualAttendance', {
                courseId: selectedCourse?.id
              })}
              style={styles.manualButton}
            >
              Switch to Manual Attendance
            </Button>
          </>
        )}
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
  card: {
    marginBottom: 16,
    elevation: 2,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 16,
  },
  courseList: {
    gap: 12,
  },
  courseCard: {
    elevation: 1,
  },
  selectedCourseCard: {
    borderWidth: 2,
    borderColor: '#2196F3',
  },
  courseCardContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  courseInfo: {
    flex: 1,
  },
  courseName: {
    fontSize: 16,
    fontWeight: '500',
  },
  courseCode: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  courseStats: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginRight: 12,
  },
  studentCount: {
    fontSize: 14,
    color: '#666',
  },
  label: {
    fontSize: 14,
    fontWeight: '500',
    marginBottom: 8,
    marginTop: 16,
  },
  segmentedButtons: {
    marginBottom: 16,
  },
  validityOptions: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 12,
  },
  validityChip: {
    height: 32,
  },
  customInput: {
    marginTop: 8,
  },
  generateButton: {
    marginTop: 16,
  },
  generateButtonContent: {
    paddingVertical: 8,
  },
  codeCard: {
    elevation: 3,
  },
  codeCardContent: {
    alignItems: 'center',
  },
  codeHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    width: '100%',
    marginBottom: 16,
  },
  codeTitle: {
    fontSize: 20,
    fontWeight: '600',
  },
  timerChip: {
    backgroundColor: '#E8F5E9',
  },
  timerChipWarning: {
    backgroundColor: '#FFF3E0',
  },
  courseInfoCard: {
    width: '100%',
    marginBottom: 24,
    elevation: 1,
  },
  courseNameDisplay: {
    fontSize: 16,
    fontWeight: '500',
  },
  courseCodeDisplay: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
  numericCodeContainer: {
    alignItems: 'center',
    marginVertical: 24,
  },
  numericCode: {
    fontSize: 48,
    fontWeight: 'bold',
    color: '#2196F3',
    letterSpacing: 8,
  },
  qrCodeContainer: {
    alignItems: 'center',
    marginVertical: 24,
  },
  codeInstruction: {
    fontSize: 14,
    color: '#666',
    marginTop: 12,
  },
  actionButtons: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 24,
  },
  actionButton: {
    flex: 1,
  },
  trackingCard: {
    width: '100%',
    marginTop: 24,
    backgroundColor: '#F5F5F5',
  },
  trackingHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  trackingTitle: {
    fontSize: 16,
    fontWeight: '500',
  },
  trackingStats: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  trackingStat: {
    alignItems: 'center',
  },
  trackingValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  trackingLabel: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  backButton: {
    marginTop: 16,
  },
  manualButton: {
    marginTop: 8,
  },
});

export default GenerateCodeScreen;