# Mobile Development Guide - Android Studio & Xcode

**Complete guide for running the Naga mobile app and viewing output through Android Studio and Xcode**

## Quick Start Commands

### Root Level (Nx Monorepo)
```bash
# Start mobile development server
npm run dev:mobile
# OR
npm run mobile:start

# Run on Android
npm run mobile:android

# Run on iOS
npm run mobile:ios

# Run Storybook (UI component development)
npm run mobile:storybook
```

### Direct Mobile Directory
```bash
cd mobile

# Start Metro bundler
npm start

# Run on Android
npm run android

# Run on iOS
npm run ios

# Run web version (for testing)
npm run web

# Development tools
npm run lint
npm run typecheck
npm run test
```

## Prerequisites Setup

### 1. Node.js and Dependencies
```bash
# Check Node version (should be 24.8.0)
node --version

# Install dependencies from root
npm install

# Or from mobile directory
cd mobile && npm install
```

### 2. Android Studio Setup
**Download**: https://developer.android.com/studio

#### Required SDK Components
1. Open Android Studio
2. **Tools > SDK Manager**
3. Install:
   - ✅ Android SDK Platform 34 (Android 14)
   - ✅ Android SDK Build-Tools 34.0.0
   - ✅ Android Emulator
   - ✅ Android SDK Platform-Tools

#### Environment Variables (Add to ~/.zshrc or ~/.bashrc)
```bash
# macOS
export ANDROID_HOME=$HOME/Library/Android/sdk
# Linux
export ANDROID_HOME=$HOME/Android/Sdk

export PATH=$PATH:$ANDROID_HOME/emulator
export PATH=$PATH:$ANDROID_HOME/platform-tools
```

#### Create Virtual Device
1. **Tools > AVD Manager**
2. **Create Virtual Device**
3. Select **Pixel 7** (recommended)
4. System Image: **Tiramisu (API level 33)**
5. **Finish**

### 3. Xcode Setup (macOS only)
**Install**: Mac App Store → Xcode

```bash
# Install command line tools
xcode-select --install

# Install CocoaPods
sudo gem install cocoapods

# Install iOS dependencies
cd mobile/ios
pod install
cd ..
```

## Running the Mobile App

### Method 1: From Root Directory (Recommended)
```bash
# Terminal 1: Start development server
npm run dev:mobile

# Terminal 2: Run on Android
npm run mobile:android

# Terminal 2: Run on iOS
npm run mobile:ios
```

### Method 2: From Mobile Directory
```bash
cd mobile

# Terminal 1: Start Metro
npm start

# Terminal 2: Run platform
npm run android  # Android
npm run ios       # iOS
```

### Method 3: Platform-Specific Options
```bash
# Android with specific device
npx react-native run-android --deviceId=<device-id>

# iOS with specific simulator
npx react-native run-ios --simulator="iPhone 15 Pro"

# iOS on physical device
npm run ios -- --device
```

## Android Studio Usage

### Opening the Project
1. **Open Android Studio**
2. **Open an existing project**
3. Navigate to: `/path/to/naga-monorepo/mobile/android`
4. **Open**

### Key Android Studio Features

#### 1. Device Manager
- **Tools > Device Manager**
- Create/manage virtual devices (AVDs)
- Start/stop emulators

#### 2. Logcat (Essential for Debugging)
- **View > Tool Windows > Logcat**
- Filter logs by app: `com.nagamobileapp`
- Log levels: Error, Warn, Info, Debug
- Search functionality for specific errors

#### 3. Project View
- Browse Android-specific code
- `android/app/src/main/` - Android native files
- `android/app/build.gradle` - Android dependencies

#### 4. Build/Run Controls
- **Run** button (green play) - Build and run
- **Debug** button - Run with debugger attached
- Device dropdown - Select target device

### Viewing Output in Android Studio

#### Console Logs
```javascript
// In React Native code
console.log('Debug message');
console.warn('Warning message');
console.error('Error message');
```
**View in**: Logcat → Filter by your app

#### Metro Bundler Logs
- Separate terminal shows Metro bundler output
- Build progress, warnings, errors
- Hot reload notifications

#### Android Native Logs
- Logcat shows system-level logs
- Native crashes, memory issues
- Hardware sensor data

### Common Android Studio Workflows

#### Debug Mode
1. **Run > Debug app** or click debug button
2. Set breakpoints in Java/Kotlin code (android/ directory)
3. Use debugger controls to step through code

#### Performance Profiler
1. **Run > Profile app**
2. Monitor CPU, memory, network usage
3. Identify performance bottlenecks

#### Layout Inspector
1. **Tools > Layout Inspector**
2. Select running app process
3. Inspect view hierarchy (limited for RN)

## Xcode Usage

### Opening the Project
⚠️ **IMPORTANT**: Open the workspace, not the project!

1. **Open Xcode**
2. **File > Open**
3. Navigate to: `/path/to/naga-monorepo/mobile/ios/`
4. Select: **`NagaMobileApp.xcworkspace`** (NOT .xcodeproj)
5. **Open**

### Key Xcode Features

#### 1. Simulator Selection
- Top toolbar dropdown - select simulator
- iPhone 15 Pro, iPad Air, etc.
- Different iOS versions available

#### 2. Console Output
- **View > Debug Area > Console**
- Shows all console.log(), warnings, errors
- React Native bundler output

#### 3. Project Navigator
- Left sidebar - browse project files
- `ios/` - iOS-specific native code
- `Pods/` - CocoaPods dependencies

#### 4. Build/Run Controls
- **Play** button - Build and run
- **Stop** button - Stop app
- Device dropdown - Select simulator/device

### Viewing Output in Xcode

#### JavaScript Console Logs
```javascript
// React Native code
console.log('Hello from RN');
console.warn('Warning message');
console.error('Error occurred');
```
**View in**: Xcode Console (Debug Area)

#### iOS Native Logs
- System logs, crashes, warnings
- Memory management issues
- iOS-specific errors

#### Build Output
- Build progress and errors
- Compilation warnings
- Linking issues

### Common Xcode Workflows

#### Device/Simulator Management
1. **Window > Devices and Simulators**
2. Add/remove simulators
3. Install on physical devices
4. View device logs

#### Performance Instruments
1. **Product > Profile**
2. Choose profiling template
3. Monitor CPU, memory, graphics
4. Time Profiler for performance analysis

#### Debugging Native Code
1. Set breakpoints in Objective-C/Swift files
2. **Product > Run** in debug mode
3. Use debugger controls to inspect variables

## Debugging React Native Code

### React Native Debugger (Recommended)
```bash
# Install
brew install --cask react-native-debugger

# Start debugger
open "rndebugger://set-debugger-loc?host=localhost&port=8081"
```

### Chrome DevTools
1. **Shake device** or **Cmd+D** (iOS) / **Cmd+M** (Android)
2. Select **"Debug with Chrome"**
3. Chrome tab opens automatically
4. **F12** for DevTools

### Debug Menu Options
- **Reload**: Refresh app (Cmd+R)
- **Debug with Chrome**: Enable Chrome debugging
- **Toggle Inspector**: Element inspector
- **Fast Refresh**: Auto-reload on changes (usually enabled)

## Development Workflow

### 1. Start Development
```bash
# Terminal 1: Start Metro bundler
npm run dev:mobile

# Terminal 2: Run on desired platform
npm run mobile:android  # or mobile:ios
```

### 2. Code Changes
- Edit files in `mobile/src/`
- Fast Refresh automatically reloads
- Check console for errors in Android Studio/Xcode

### 3. View Logs
**Android Studio**: Logcat tab
**Xcode**: Console in Debug Area
**Terminal**: Metro bundler output

### 4. Debug Issues
1. Check Metro bundler terminal for build errors
2. Check platform-specific IDE for runtime errors
3. Use React Native debugger for JS debugging
4. Check physical device logs for device-specific issues

## Common Issues & Solutions

### Android Issues
```bash
# Clear build cache
cd mobile/android
./gradlew clean
cd ..

# Reset Metro cache
npm start -- --reset-cache

# Fix permissions (if needed)
chmod +x android/gradlew
```

### iOS Issues
```bash
# Clean iOS build
cd mobile/ios
xcodebuild clean
cd ..

# Reinstall pods
cd ios
rm -rf Pods Podfile.lock
pod install
cd ..
```

### Metro/React Native Issues
```bash
# Clear all caches
npx react-native start --reset-cache

# Reinstall dependencies
rm -rf node_modules
npm install

# Clear watchman cache (if installed)
watchman watch-del-all
```

## App Structure

The mobile app includes:
- ✅ **Authentication**: Login/Register screens
- ✅ **Navigation**: Bottom tabs + stack navigation
- ✅ **Dashboard**: Student overview with quick actions
- ✅ **Attendance**: Track and view attendance
- ✅ **Grades**: Display student grades
- ✅ **Profile**: User profile management
- ✅ **State Management**: Zustand for app state
- ✅ **UI Components**: React Native Paper components
- ✅ **TypeScript**: Full TypeScript support

### Key Directories
```
mobile/
├── src/
│   ├── components/     # Reusable UI components
│   ├── navigation/     # App navigation setup
│   ├── screens/       # App screens (Dashboard, Login, etc.)
│   ├── store/         # Zustand state management
│   ├── types/         # TypeScript type definitions
│   └── App.tsx        # Main app component
├── android/           # Android native code
├── ios/              # iOS native code
└── stories/          # Storybook component stories
```

## Storybook Development

For UI component development:
```bash
# Start Storybook server
npm run mobile:storybook
# Opens http://localhost:6006

# Build static Storybook
cd mobile
npm run build-storybook
```

## Testing

```bash
# Unit tests
npm run test:mobile

# Type checking
npm run typecheck:mobile

# Linting
npm run lint:mobile
```

## Production Builds

### Android APK
```bash
cd mobile/android
./gradlew assembleRelease
# Output: android/app/build/outputs/apk/release/app-release.apk
```

### iOS Archive
1. Open Xcode workspace
2. **Product > Archive**
3. Follow distribution workflow

---

This guide covers the complete mobile development workflow. Start with the Quick Start commands, then use Android Studio and Xcode to view detailed logs and debug your application.