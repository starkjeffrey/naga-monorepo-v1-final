# NAGA Mobile App Setup Guide

Complete setup instructions for developing the React Native mobile app with Android Studio and Xcode.

## Prerequisites

### Required Software
1. **Node.js 24.8.0** - JavaScript runtime (latest)
2. **npm or yarn** - Package manager
3. **Android Studio** - Android development
4. **Xcode** - iOS development (macOS only)
5. **React Native CLI** - React Native command line tools

### Install Prerequisites

```bash
# Install Node.js 24.8.0 (using nvm recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 24.8.0
nvm use 24.8.0

# Install React Native CLI
npm install -g @react-native-community/cli

# Install dependencies
cd mobile
npm install
```

## Android Setup

### 1. Install Android Studio
- Download from: https://developer.android.com/studio
- Install with default settings
- Open Android Studio and complete the setup wizard

### 2. Configure Android SDK
1. Open Android Studio
2. Go to **Tools > SDK Manager**
3. Install these SDK components:
   - **Android SDK Platform 34** (Android 14)
   - **Android SDK Build-Tools 34.0.0**
   - **Android Emulator**
   - **Android SDK Platform-Tools**

### 3. Set Environment Variables
Add to your `~/.bashrc` or `~/.zshrc`:

```bash
export ANDROID_HOME=$HOME/Library/Android/sdk  # macOS
# OR
export ANDROID_HOME=$HOME/Android/Sdk          # Linux

export PATH=$PATH:$ANDROID_HOME/emulator
export PATH=$PATH:$ANDROID_HOME/platform-tools
```

### 4. Create Android Virtual Device (AVD)
1. Open Android Studio
2. Go to **Tools > AVD Manager**
3. Click **Create Virtual Device**
4. Select **Phone > Pixel 7** (recommended)
5. Select **Tiramisu (API level 33)** system image
6. Click **Finish**

### 5. Run on Android
```bash
cd mobile

# Start Metro bundler
npm start

# In another terminal, run Android app
npm run android

# OR with specific device
npx react-native run-android --deviceId=<device-id>
```

## iOS Setup (macOS only)

### 1. Install Xcode
- Install from Mac App Store
- Open Xcode and accept license agreements
- Install additional components when prompted

### 2. Install Xcode Command Line Tools
```bash
xcode-select --install
```

### 3. Install CocoaPods
```bash
sudo gem install cocoapods

# Navigate to iOS directory and install pods
cd mobile/ios
pod install
cd ..
```

### 4. Run on iOS
```bash
cd mobile

# Start Metro bundler
npm start

# In another terminal, run iOS app
npm run ios

# OR specify simulator
npx react-native run-ios --simulator="iPhone 15 Pro"
```

## Development Commands

### Start Development Server
```bash
# Start Metro bundler (required for both platforms)
npm start

# Or with cache reset
npm start -- --reset-cache
```

### Run on Devices
```bash
# Android
npm run android                    # Run on connected device/emulator
npm run android -- --port 8082     # Use different port

# iOS
npm run ios                        # Run on simulator
npm run ios -- --device           # Run on connected device
npm run ios -- --simulator="iPhone 15 Pro"  # Specific simulator
```

### Code Quality
```bash
npm run lint                       # ESLint checking
npm run typecheck                  # TypeScript validation
npm run test                       # Jest unit tests
```

## Android Studio Usage

### Opening the Project
1. Open Android Studio
2. Select **Open an existing Android Studio project**
3. Navigate to `mobile/android` directory
4. Click **OK**

### Key Features
- **Device Manager**: Manage virtual devices (AVDs)
- **Logcat**: View device logs and debug information
- **Profiler**: Monitor app performance
- **Layout Inspector**: Debug UI layouts

### Running from Android Studio
1. Select your target device/emulator from dropdown
2. Click the **Run** button (green play icon)
3. The app will build and deploy automatically

## Xcode Usage

### Opening the Project
1. Open Xcode
2. File > Open
3. Navigate to `mobile/ios/NagaMobileApp.xcworkspace`
4. Click **Open** (important: use .xcworkspace, not .xcodeproj)

### Key Features
- **Simulator**: Test on various iOS device sizes
- **Console**: View debug logs and errors
- **Instruments**: Performance profiling tools
- **Interface Builder**: Visual UI editing (not commonly used with RN)

### Running from Xcode
1. Select your target simulator/device from dropdown
2. Click the **Run** button (play icon)
3. The app will build and deploy automatically

## Debugging

### React Native Debugger
```bash
# Install React Native Debugger (recommended)
brew install --cask react-native-debugger

# Or download from GitHub releases
```

### Chrome DevTools
1. Shake device/press Cmd+D on simulator
2. Select "Debug with Chrome"
3. Open Chrome DevTools on the opened page

### Debug Menu
- **iOS Simulator**: Cmd+D
- **Android Emulator**: Cmd+M (macOS) or Ctrl+M (Windows/Linux)
- **Physical Device**: Shake the device

Debug menu options:
- **Reload**: Refresh the app
- **Debug with Chrome**: Enable Chrome debugging
- **Toggle Inspector**: Element inspector
- **Fast Refresh**: Auto-reload on file changes

## Common Issues & Solutions

### Android Issues
```bash
# Clear cache and rebuild
cd mobile/android
./gradlew clean
cd ..
npx react-native start --reset-cache

# Fix Gradle issues
cd android
chmod +x gradlew
./gradlew wrapper --gradle-version=8.0.2
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

### Metro Issues
```bash
# Clear Metro cache
npx react-native start --reset-cache

# Clear node modules
rm -rf node_modules
npm install
```

## Project Structure
```
mobile/
├── src/
│   ├── components/        # Reusable components
│   ├── navigation/        # Navigation configuration
│   ├── screens/          # App screens
│   ├── store/            # Zustand state management
│   ├── types/            # TypeScript definitions
│   └── App.tsx           # Main app component
├── android/              # Android native code
├── ios/                  # iOS native code
├── index.js              # App entry point
├── package.json          # Dependencies
└── README.md            # Project documentation
```

## Next Steps

1. **Install Prerequisites**: Node.js, Android Studio, Xcode
2. **Run Setup Commands**: `npm install` in mobile directory
3. **Test Android**: Create AVD and run `npm run android`
4. **Test iOS**: Install pods and run `npm run ios`
5. **Start Development**: Edit code and see live changes

The app includes:
- ✅ Authentication screens (Login/Register)
- ✅ Bottom tab navigation
- ✅ Dashboard with quick actions
- ✅ Attendance tracking
- ✅ Grades display
- ✅ User profile management
- ✅ State management with Zustand
- ✅ TypeScript support
- ✅ React Native Paper UI components