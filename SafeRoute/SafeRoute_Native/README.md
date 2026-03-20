# SafeRoute Mobile App

React Native mobile application for navigating safely with SOS features and real-time mapping.

## Features

- Interactive map for route selection
- Selection between safest, fastest, and balanced routes
- Dedicated SOS emergency trigger button
- Shake detection for automatic SOS triggering
- Emergency contact management

## Tech Stack

- React Native
- Expo
- TypeScript
- react-native-maps
- Zustand

## Folder Structure

```text
SafeRoute_Native/
├── App.tsx → Mobile application entry point
├── app.json → Expo configuration settings
├── babel.config.js → Babel transformation settings
├── package.json → Dependencies and scripts
├── package-lock.json → Dependency lockfile
├── package-lock 2.json → Backup dependency lockfile
├── tsconfig.json → TypeScript configuration
└── src/
    ├── components/
    │   ├── BottomControls.tsx → Navigational action bar
    │   ├── MapScreen.tsx → Interactive map interface
    │   ├── MiniSOSButton.tsx → Quick-access emergency trigger
    │   ├── RouteSelector.tsx → Selection between route types
    │   └── SOSButton.tsx → Primary emergency interface
    ├── config/
    │   ├── api.ts → Base API endpoint configuration
    │   └── backend.ts → Specific route path definitions
    ├── hooks/
    │   ├── useRealLocation.ts → GPS coordinate retrieval
    │   └── useShakeDetection.ts → Accelerometer listener
    ├── screens/
    │   ├── EmergencyContactsScreen.tsx → Contact management UI
    │   ├── RouteSearchScreen.tsx → Destination input interface
    │   └── SettingsScreen.tsx → Preferences and configuration
    ├── store/
    │   └── useAppStore.ts → Zustand global state manager
    └── utils/
        ├── clientIdentity.ts → Device UUID generator
        ├── logger.ts → Standardized logging utility
        └── mockData.ts → Testing static payloads
```

## Setup Instructions

- Ensure Node.js v18+ is installed
- Install Expo CLI globally
- Download the Expo Go app for local device testing

## Run Commands

- `npm install`
- `npm start`

## Key Functionalities

- Communicates with FastAPI backend for route calculation
- Connects to WebSockets for nearby SOS broadcasts
- Monitors real-time location via GPS APIs

## Notes

- API base URLs are configured in `src/config/api.ts`
- Expo Go handles both iOS and Android environments
