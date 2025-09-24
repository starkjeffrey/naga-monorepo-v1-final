# NAGA Mobile App v2.0

## Overview

A React Native student portal app with elegant mobile-first design and performance optimizations.

## Features

- 🎭 Enhanced Animations with Reanimated 3
- 🏗️ TypeScript-first Architecture
- 📱 Mobile-Native Design
- 🎨 Responsive UI Components
- ♿ Accessibility Support

## Prerequisites

- Node.js 16+
- React Native CLI
- Android Studio / Xcode
- TypeScript 4.8+

## Installation

```bash
npm install
cd ios && pod install  # iOS only
```

## Running the App

```bash
# Android
npm run android

# iOS
npm run ios
```

## Development Scripts

```bash
npm run lint          # ESLint checking
npm run typecheck     # TypeScript validation
npm run test          # Jest unit tests
```

## Tech Stack

- React Native 0.72.4
- TypeScript
- Zustand
- React Query
- React Native Paper

## Project Structure

```
mobile/
├── src/
│   ├── components/    # Reusable UI components
│   ├── constants/     # App constants and configuration
│   ├── hooks/         # Custom React hooks
│   ├── navigation/    # Navigation configuration
│   ├── screens/       # App screens/pages
│   ├── store/         # Zustand state management
│   ├── types/         # TypeScript type definitions
│   ├── utils/         # Utility functions
│   └── App.tsx        # Main application component
├── package.json
├── tsconfig.json
└── README.md
```

## License

[Add your license here]