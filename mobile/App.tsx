import React, { useEffect, useRef } from 'react';
import { View, StyleSheet, ScrollView, Dimensions, Animated, Easing } from 'react-native';
import {
  Provider as PaperProvider,
  Card,
  Title,
  Text,
  Button,
  DefaultTheme,
  Avatar,
  Surface,
  Divider,
  List,
  Chip,
  FAB,
  Appbar,
  useTheme
} from 'react-native-paper';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { LinearGradient } from 'expo-linear-gradient';
import * as Font from 'expo-font';
import * as SplashScreen from 'expo-splash-screen';

const { width } = Dimensions.get('window');
const isTablet = width > 768;

// Keep splash screen visible while we load resources
SplashScreen.preventAutoHideAsync();

// Light theme
const lightTheme = {
  ...DefaultTheme,
  roundness: 12,
  colors: {
    ...DefaultTheme.colors,
    primary: '#2196F3',
    accent: '#4CAF50',
    background: '#f8f9fa',
    surface: '#ffffff',
    text: '#212121',
    disabled: '#9E9E9E',
    placeholder: '#666666',
    backdrop: 'rgba(0, 0, 0, 0.5)',
  },
  fonts: {
    regular: {
      // fontFamily: 'Inter-Regular',
      fontWeight: 'normal' as const,
    },
    medium: {
      // fontFamily: 'Inter-Medium',
      fontWeight: '500' as const,
    },
    light: {
      // fontFamily: 'Inter-Light',
      fontWeight: '300' as const,
    },
    thin: {
      // fontFamily: 'Inter-Thin',
      fontWeight: '100' as const,
    },
  },
};

// Dark theme
const darkTheme = {
  ...DefaultTheme,
  dark: true,
  roundness: 12,
  colors: {
    ...DefaultTheme.colors,
    primary: '#64B5F6',
    accent: '#81C784',
    background: '#121212',
    surface: '#1e1e1e',
    text: '#ffffff',
    disabled: '#666666',
    placeholder: '#aaaaaa',
    backdrop: 'rgba(0, 0, 0, 0.8)',
  },
  fonts: lightTheme.fonts,
};

export default function App() {
  const [role, setRole] = React.useState<'student' | 'teacher' | null>(null);
  const [isDarkMode, setIsDarkMode] = React.useState(false);
  const [fontsLoaded, setFontsLoaded] = React.useState(false);

  // Animation values
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0.9)).current;
  const slideAnim = useRef(new Animated.Value(50)).current;
  const rotateAnim = useRef(new Animated.Value(0)).current;
  const cardAnimations = useRef([
    new Animated.Value(0),
    new Animated.Value(0),
  ]).current;

  const theme = isDarkMode ? darkTheme : lightTheme;

  // Load custom fonts
  useEffect(() => {
    async function loadFonts() {
      try {
        // Uncomment when you add Inter font files to assets/fonts/
        // await Font.loadAsync({
        //   'Inter-Regular': require('./assets/fonts/Inter-Regular.ttf'),
        //   'Inter-Medium': require('./assets/fonts/Inter-Medium.ttf'),
        //   'Inter-Bold': require('./assets/fonts/Inter-Bold.ttf'),
        //   'Inter-Light': require('./assets/fonts/Inter-Light.ttf'),
        //   'Inter-Thin': require('./assets/fonts/Inter-Thin.ttf'),
        // });
        setFontsLoaded(true);
      } catch (e) {
        console.log('Fonts not loaded, using system fonts');
        setFontsLoaded(true);
      } finally {
        await SplashScreen.hideAsync();
      }
    }
    loadFonts();
  }, []);

  // Initial animations
  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 1000,
        useNativeDriver: true,
      }),
      Animated.spring(scaleAnim, {
        toValue: 1,
        tension: 20,
        friction: 7,
        useNativeDriver: true,
      }),
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 800,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),
    ]).start();

    // Staggered card animations
    Animated.stagger(200, [
      Animated.spring(cardAnimations[0], {
        toValue: 1,
        tension: 20,
        friction: 7,
        useNativeDriver: true,
      }),
      Animated.spring(cardAnimations[1], {
        toValue: 1,
        tension: 20,
        friction: 7,
        useNativeDriver: true,
      }),
    ]).start();

    // Continuous rotation for logo
    Animated.loop(
      Animated.sequence([
        Animated.timing(rotateAnim, {
          toValue: 1,
          duration: 10000,
          easing: Easing.linear,
          useNativeDriver: true,
        }),
        Animated.timing(rotateAnim, {
          toValue: 0,
          duration: 0,
          useNativeDriver: true,
        }),
      ])
    ).start();
  }, []);

  if (!fontsLoaded) {
    return null;
  }

  if (!role) {
    return (
      <SafeAreaProvider>
        <PaperProvider theme={theme}>
          <LinearGradient
            colors={isDarkMode ? ['#1a1a1a', '#2d2d2d', '#1a1a1a'] : ['#667eea', '#764ba2', '#f093fb']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={styles.loginContainer}>
            <Animated.View
              style={[
                styles.loginContent,
                {
                  opacity: fadeAnim,
                  transform: [
                    { scale: scaleAnim },
                    { translateY: slideAnim }
                  ]
                }
              ]}>
              {/* Logo Section with Animation */}
              <View style={styles.logoSection}>
                <Animated.View
                  style={{
                    transform: [{
                      rotate: rotateAnim.interpolate({
                        inputRange: [0, 1],
                        outputRange: ['0deg', '360deg']
                      })
                    }]
                  }}
                >
                  <Avatar.Icon
                    size={90}
                    icon="school"
                    style={[styles.logo, { backgroundColor: isDarkMode ? '#64B5F6' : '#2196F3' }]}
                  />
                </Animated.View>
                <Title style={[styles.appTitle, { color: '#ffffff' }]}>NAGA SIS</Title>
                <Text style={[styles.appSubtitle, { color: 'rgba(255,255,255,0.9)' }]}>Student Information System</Text>
              </View>

              {/* Dark Mode Toggle */}
              <View style={styles.darkModeToggle}>
                <Button
                  mode="outlined"
                  onPress={() => setIsDarkMode(!isDarkMode)}
                  icon={isDarkMode ? 'weather-sunny' : 'weather-night'}
                  textColor="#ffffff"
                  style={{ borderColor: 'rgba(255,255,255,0.5)' }}
                >
                  {isDarkMode ? 'Light Mode' : 'Dark Mode'}
                </Button>
              </View>

              {/* Role Selection Cards with Animations */}
              <View style={styles.roleCards}>
                <Animated.View
                  style={{
                    flex: 1,
                    opacity: cardAnimations[0],
                    transform: [{
                      translateY: cardAnimations[0].interpolate({
                        inputRange: [0, 1],
                        outputRange: [50, 0]
                      })
                    }]
                  }}
                >
                  <Surface style={[styles.roleCard, isDarkMode && styles.darkCard]} elevation={4}>
                    <Card.Content style={styles.roleCardContent}>
                      <Avatar.Icon
                        size={60}
                        icon="account-school"
                        style={[styles.roleIcon, { backgroundColor: isDarkMode ? '#1565C0' : '#E3F2FD' }]}
                        color={isDarkMode ? '#90CAF9' : '#2196F3'}
                      />
                      <Title style={[styles.roleTitle, isDarkMode && { color: '#ffffff' }]}>Student</Title>
                      <Text style={[styles.roleDescription, isDarkMode && { color: '#bbbbbb' }]}>
                        Access your grades, attendance, schedule, and more
                      </Text>
                      <Button
                        mode="contained"
                        onPress={() => setRole('student')}
                        style={styles.roleButton}
                        contentStyle={styles.buttonContent}
                      >
                        Login as Student
                      </Button>
                    </Card.Content>
                  </Surface>
                </Animated.View>

                <Animated.View
                  style={{
                    flex: 1,
                    opacity: cardAnimations[1],
                    transform: [{
                      translateY: cardAnimations[1].interpolate({
                        inputRange: [0, 1],
                        outputRange: [50, 0]
                      })
                    }]
                  }}
                >
                  <Surface style={[styles.roleCard, isDarkMode && styles.darkCard]} elevation={4}>
                    <Card.Content style={styles.roleCardContent}>
                      <Avatar.Icon
                        size={60}
                        icon="teach"
                        style={[styles.roleIcon, { backgroundColor: isDarkMode ? '#2E7D32' : '#E8F5E9' }]}
                        color={isDarkMode ? '#A5D6A7' : '#4CAF50'}
                      />
                      <Title style={[styles.roleTitle, isDarkMode && { color: '#ffffff' }]}>Teacher</Title>
                      <Text style={[styles.roleDescription, isDarkMode && { color: '#bbbbbb' }]}>
                        Manage attendance, grades, and course materials
                      </Text>
                      <Button
                        mode="contained"
                        onPress={() => setRole('teacher')}
                        style={[styles.roleButton, { backgroundColor: isDarkMode ? '#388E3C' : '#4CAF50' }]}
                        contentStyle={styles.buttonContent}
                      >
                        Login as Teacher
                      </Button>
                    </Card.Content>
                  </Surface>
                </Animated.View>
              </View>

              <Text style={[styles.footer, { color: 'rgba(255,255,255,0.7)' }]}>
                © 2024 NAGA University. All rights reserved.
              </Text>
            </Animated.View>
          </LinearGradient>
        </PaperProvider>
      </SafeAreaProvider>
    );
  }

  // Dashboard View
  return (
    <SafeAreaProvider>
      <PaperProvider theme={theme}>
        <LinearGradient
          colors={isDarkMode ? ['#1a1a1a', '#2d2d2d'] : ['#ffffff', '#f8f9fa']}
          style={{ flex: 1 }}
        >
          <SafeAreaView style={[styles.container, { backgroundColor: 'transparent' }]}>
            {/* Header with Gradient */}
            <LinearGradient
              colors={isDarkMode ? ['#2d2d2d', '#1a1a1a'] : ['#2196F3', '#1976D2']}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
            >
              <Appbar.Header style={[styles.header, { backgroundColor: 'transparent', elevation: 0 }]}>
                <Appbar.Content
                  title={role === 'student' ? 'Student Portal' : 'Teacher Portal'}
                  subtitle="Welcome back!"
                  titleStyle={{ color: '#ffffff' }}
                  subtitleStyle={{ color: 'rgba(255,255,255,0.8)' }}
                />
                <Appbar.Action icon="bell" onPress={() => {}} color="#ffffff" />
                <Appbar.Action icon={isDarkMode ? 'weather-sunny' : 'weather-night'} onPress={() => setIsDarkMode(!isDarkMode)} color="#ffffff" />
                <Appbar.Action icon="logout" onPress={() => setRole(null)} color="#ffffff" />
              </Appbar.Header>
            </LinearGradient>

            <ScrollView style={styles.scrollView}>
              <View style={styles.dashboardContent}>
                {/* Welcome Card with Animation */}
                <Animated.View
                  style={{
                    opacity: fadeAnim,
                    transform: [{
                      translateY: fadeAnim.interpolate({
                        inputRange: [0, 1],
                        outputRange: [-20, 0]
                      })
                    }]
                  }}
                >
                  <Surface style={[styles.welcomeCard, isDarkMode && styles.darkCard]} elevation={3}>
                    <LinearGradient
                      colors={isDarkMode ? ['#2d2d2d', '#1e1e1e'] : ['#ffffff', '#f8f9fa']}
                      style={{ padding: 20, borderRadius: 12 }}
                    >
                      <View style={styles.welcomeHeader}>
                        <Avatar.Text
                          size={48}
                          label={role === 'student' ? 'JS' : 'JT'}
                          style={[styles.avatar, { backgroundColor: isDarkMode ? '#64B5F6' : '#2196F3' }]}
                        />
                        <View style={styles.welcomeText}>
                          <Title style={[styles.userName, isDarkMode && { color: '#ffffff' }]}>
                            {role === 'student' ? 'Jane Student' : 'John Teacher'}
                          </Title>
                          <Text style={[styles.userRole, isDarkMode && { color: '#bbbbbb' }]}>
                            {role === 'student' ? 'Computer Science, Year 3' : 'Computer Science Department'}
                          </Text>
                        </View>
                      </View>
                      <View style={styles.statsRow}>
                        {role === 'student' ? (
                          <>
                            <View style={styles.statItem}>
                              <Text style={[styles.statValue, isDarkMode && { color: '#64B5F6' }]}>3.8</Text>
                              <Text style={[styles.statLabel, isDarkMode && { color: '#aaaaaa' }]}>GPA</Text>
                            </View>
                            <Divider style={[styles.verticalDivider, isDarkMode && { backgroundColor: '#444' }]} />
                            <View style={styles.statItem}>
                              <Text style={[styles.statValue, isDarkMode && { color: '#81C784' }]}>92%</Text>
                              <Text style={[styles.statLabel, isDarkMode && { color: '#aaaaaa' }]}>Attendance</Text>
                            </View>
                            <Divider style={[styles.verticalDivider, isDarkMode && { backgroundColor: '#444' }]} />
                            <View style={styles.statItem}>
                              <Text style={[styles.statValue, isDarkMode && { color: '#FFB74D' }]}>6</Text>
                              <Text style={[styles.statLabel, isDarkMode && { color: '#aaaaaa' }]}>Courses</Text>
                            </View>
                          </>
                        ) : (
                          <>
                            <View style={styles.statItem}>
                              <Text style={[styles.statValue, isDarkMode && { color: '#64B5F6' }]}>4</Text>
                              <Text style={[styles.statLabel, isDarkMode && { color: '#aaaaaa' }]}>Courses</Text>
                            </View>
                            <Divider style={[styles.verticalDivider, isDarkMode && { backgroundColor: '#444' }]} />
                            <View style={styles.statItem}>
                              <Text style={[styles.statValue, isDarkMode && { color: '#81C784' }]}>127</Text>
                              <Text style={[styles.statLabel, isDarkMode && { color: '#aaaaaa' }]}>Students</Text>
                            </View>
                            <Divider style={[styles.verticalDivider, isDarkMode && { backgroundColor: '#444' }]} />
                            <View style={styles.statItem}>
                              <Text style={[styles.statValue, isDarkMode && { color: '#FFB74D' }]}>23</Text>
                              <Text style={[styles.statLabel, isDarkMode && { color: '#aaaaaa' }]}>Pending</Text>
                            </View>
                          </>
                        )}
                      </View>
                    </LinearGradient>
                  </Surface>
                </Animated.View>

                {/* Quick Actions */}
                <Title style={[styles.sectionTitle, isDarkMode && { color: '#ffffff' }]}>Quick Actions</Title>
                <View style={styles.actionGrid}>
                  {role === 'student' ? (
                    <>
                      <Surface style={[styles.actionCard, isDarkMode && styles.darkActionCard]} elevation={2}>
                        <Card.Content style={styles.actionContent}>
                          <Avatar.Icon
                            size={48}
                            icon="calendar-check"
                            style={[styles.actionIcon, { backgroundColor: isDarkMode ? '#6A1B9A' : '#F3E5F5' }]}
                            color={isDarkMode ? '#CE93D8' : '#9C27B0'}
                          />
                          <Text style={[styles.actionTitle, isDarkMode && { color: '#ffffff' }]}>Attendance</Text>
                          <Chip compact style={styles.actionChip}>92%</Chip>
                        </Card.Content>
                      </Surface>
                      <Surface style={[styles.actionCard, isDarkMode && styles.darkActionCard]} elevation={2}>
                        <Card.Content style={styles.actionContent}>
                          <Avatar.Icon
                            size={48}
                            icon="chart-line"
                            style={[styles.actionIcon, { backgroundColor: isDarkMode ? '#1565C0' : '#E3F2FD' }]}
                            color={isDarkMode ? '#90CAF9' : '#2196F3'}
                          />
                          <Text style={[styles.actionTitle, isDarkMode && { color: '#ffffff' }]}>Grades</Text>
                          <Chip compact style={styles.actionChip}>3.8 GPA</Chip>
                        </Card.Content>
                      </Surface>
                      <Surface style={[styles.actionCard, isDarkMode && styles.darkActionCard]} elevation={2}>
                        <Card.Content style={styles.actionContent}>
                          <Avatar.Icon
                            size={48}
                            icon="calendar-clock"
                            style={[styles.actionIcon, { backgroundColor: isDarkMode ? '#E65100' : '#FFF3E0' }]}
                            color={isDarkMode ? '#FFB74D' : '#FF9800'}
                          />
                          <Text style={[styles.actionTitle, isDarkMode && { color: '#ffffff' }]}>Schedule</Text>
                          <Chip compact style={styles.actionChip}>Today</Chip>
                        </Card.Content>
                      </Surface>
                      <Surface style={[styles.actionCard, isDarkMode && styles.darkActionCard]} elevation={2}>
                        <Card.Content style={styles.actionContent}>
                          <Avatar.Icon
                            size={48}
                            icon="card-account-details"
                            style={[styles.actionIcon, { backgroundColor: isDarkMode ? '#F57C00' : '#FFF9C4' }]}
                            color={isDarkMode ? '#FFD54F' : '#FFC107'}
                          />
                          <Text style={[styles.actionTitle, isDarkMode && { color: '#ffffff' }]}>ID Card</Text>
                        </Card.Content>
                      </Surface>
                    </>
                  ) : (
                    <>
                      <Surface style={[styles.actionCard, isDarkMode && styles.darkActionCard]} elevation={2}>
                        <Card.Content style={styles.actionContent}>
                          <Avatar.Icon
                            size={48}
                            icon="qrcode"
                            style={[styles.actionIcon, { backgroundColor: isDarkMode ? '#1565C0' : '#E3F2FD' }]}
                            color={isDarkMode ? '#90CAF9' : '#2196F3'}
                          />
                          <Text style={[styles.actionTitle, isDarkMode && { color: '#ffffff' }]}>Generate Code</Text>
                        </Card.Content>
                      </Surface>
                      <Surface style={[styles.actionCard, isDarkMode && styles.darkActionCard]} elevation={2}>
                        <Card.Content style={styles.actionContent}>
                          <Avatar.Icon
                            size={48}
                            icon="clipboard-check"
                            style={[styles.actionIcon, { backgroundColor: isDarkMode ? '#2E7D32' : '#E8F5E9' }]}
                            color={isDarkMode ? '#A5D6A7' : '#4CAF50'}
                          />
                          <Text style={[styles.actionTitle, isDarkMode && { color: '#ffffff' }]}>Attendance</Text>
                          <Chip compact style={styles.actionChip}>Mark</Chip>
                        </Card.Content>
                      </Surface>
                      <Surface style={[styles.actionCard, isDarkMode && styles.darkActionCard]} elevation={2}>
                        <Card.Content style={styles.actionContent}>
                          <Avatar.Icon
                            size={48}
                            icon="pencil"
                            style={[styles.actionIcon, { backgroundColor: isDarkMode ? '#E65100' : '#FFF3E0' }]}
                            color={isDarkMode ? '#FFB74D' : '#FF9800'}
                          />
                          <Text style={[styles.actionTitle, isDarkMode && { color: '#ffffff' }]}>Grades</Text>
                          <Chip compact style={styles.actionChip}>23 pending</Chip>
                        </Card.Content>
                      </Surface>
                      <Surface style={[styles.actionCard, isDarkMode && styles.darkActionCard]} elevation={2}>
                        <Card.Content style={styles.actionContent}>
                          <Avatar.Icon
                            size={48}
                            icon="book-open"
                            style={[styles.actionIcon, { backgroundColor: isDarkMode ? '#6A1B9A' : '#F3E5F5' }]}
                            color={isDarkMode ? '#CE93D8' : '#9C27B0'}
                          />
                          <Text style={[styles.actionTitle, isDarkMode && { color: '#ffffff' }]}>Courses</Text>
                        </Card.Content>
                      </Surface>
                    </>
                  )}
                </View>

                {/* Recent Activity */}
                <Title style={[styles.sectionTitle, isDarkMode && { color: '#ffffff' }]}>Recent Activity</Title>
                <Surface style={[styles.activityCard, isDarkMode && styles.darkCard]} elevation={2}>
                  <List.Section>
                    <List.Item
                      title={role === 'student' ? "Attendance marked for CS301" : "Generated code for CS101"}
                      description="2 hours ago"
                      left={props => <List.Icon {...props} icon="check-circle" color="#4CAF50" />}
                      titleStyle={[isDarkMode && { color: '#ffffff' }]}
                      descriptionStyle={[isDarkMode && { color: '#aaaaaa' }]}
                    />
                    <Divider style={isDarkMode && { backgroundColor: '#444' }} />
                    <List.Item
                      title={role === 'student' ? "New grade posted: Web Dev" : "Updated grades for Database Systems"}
                      description="Yesterday"
                      left={props => <List.Icon {...props} icon="star" color="#FFC107" />}
                      titleStyle={[isDarkMode && { color: '#ffffff' }]}
                      descriptionStyle={[isDarkMode && { color: '#aaaaaa' }]}
                    />
                    <Divider style={isDarkMode && { backgroundColor: '#444' }} />
                    <List.Item
                      title={role === 'student' ? "Assignment submitted" : "New student enrolled"}
                      description="2 days ago"
                      left={props => <List.Icon {...props} icon="file-document" color="#2196F3" />}
                      titleStyle={[isDarkMode && { color: '#ffffff' }]}
                      descriptionStyle={[isDarkMode && { color: '#aaaaaa' }]}
                    />
                  </List.Section>
                </Surface>
              </View>
            </ScrollView>

            {/* FAB */}
            <FAB
              icon="plus"
              style={[styles.fab, { backgroundColor: isDarkMode ? '#64B5F6' : '#2196F3' }]}
              onPress={() => console.log('FAB pressed')}
              color="#ffffff"
            />
          </SafeAreaView>
        </LinearGradient>
      </PaperProvider>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  // Login Styles
  loginContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loginContent: {
    width: '100%',
    maxWidth: isTablet ? 800 : 400,
    padding: 20,
  },
  logoSection: {
    alignItems: 'center',
    marginBottom: 30,
  },
  logo: {
    marginBottom: 16,
  },
  appTitle: {
    fontSize: 36,
    fontWeight: 'bold',
    letterSpacing: 1,
    marginTop: 10,
  },
  appSubtitle: {
    fontSize: 16,
    marginTop: 4,
  },
  darkModeToggle: {
    alignItems: 'center',
    marginBottom: 30,
  },
  roleCards: {
    flexDirection: isTablet ? 'row' : 'column',
    gap: 16,
    marginBottom: 40,
  },
  roleCard: {
    flex: 1,
    borderRadius: 16,
    overflow: 'hidden',
  },
  darkCard: {
    backgroundColor: '#2d2d2d',
  },
  roleCardContent: {
    padding: 24,
    alignItems: 'center',
  },
  roleIcon: {
    marginBottom: 16,
  },
  roleTitle: {
    fontSize: 22,
    fontWeight: '600',
    marginBottom: 8,
  },
  roleDescription: {
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 20,
    minHeight: 40,
  },
  roleButton: {
    width: '100%',
    borderRadius: 8,
  },
  buttonContent: {
    paddingVertical: 8,
  },

  // Dashboard Styles
  container: {
    flex: 1,
  },
  header: {
    elevation: 0,
  },
  scrollView: {
    flex: 1,
  },
  dashboardContent: {
    padding: 16,
    paddingBottom: 80,
    maxWidth: isTablet ? 1200 : '100%',
    alignSelf: 'center',
    width: '100%',
  },
  welcomeCard: {
    borderRadius: 16,
    marginBottom: 24,
    overflow: 'hidden',
  },
  welcomeHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
  },
  avatar: {
    backgroundColor: '#2196F3',
  },
  welcomeText: {
    marginLeft: 16,
    flex: 1,
  },
  userName: {
    fontSize: 20,
    fontWeight: '600',
  },
  userRole: {
    fontSize: 14,
    marginTop: 2,
  },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  statItem: {
    alignItems: 'center',
    flex: 1,
  },
  statValue: {
    fontSize: 26,
    fontWeight: 'bold',
  },
  statLabel: {
    fontSize: 12,
    marginTop: 4,
  },
  verticalDivider: {
    width: 1,
    backgroundColor: '#e0e0e0',
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '600',
    marginBottom: 16,
    marginTop: 8,
  },
  actionGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginBottom: 24,
  },
  actionCard: {
    flex: 1,
    minWidth: isTablet ? '23%' : '47%',
    borderRadius: 12,
  },
  darkActionCard: {
    backgroundColor: '#2d2d2d',
  },
  actionContent: {
    alignItems: 'center',
    paddingVertical: 20,
  },
  actionIcon: {
    marginBottom: 12,
  },
  actionTitle: {
    fontSize: 14,
    fontWeight: '500',
    marginBottom: 8,
  },
  actionChip: {
    height: 24,
  },
  activityCard: {
    borderRadius: 12,
    overflow: 'hidden',
  },
  fab: {
    position: 'absolute',
    margin: 16,
    right: 0,
    bottom: 0,
  },
  footer: {
    fontSize: 12,
    textAlign: 'center',
  },
});