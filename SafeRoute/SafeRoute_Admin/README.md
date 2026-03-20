# SafeRoute Admin Dashboard

React-based administration interface for the SafeRoute platform, enabling visual monitoring of heatmaps, SOS events, and safety parameters.

## Features

- Live crime heatmap visualization
- Real-time SOS alert monitoring
- Active user tracking
- Safety parameter tuning panel
- Key performance indicator dashboards

## Tech Stack

- React
- TypeScript
- Vite
- Tailwind CSS

## Folder Structure

```text
SafeRoute_Admin/
├── Dockerfile → Container configuration for the admin dashboard
├── eslint.config.js → Linter configuration
├── index.html → HTML entry point
├── package.json → Dependencies and scripts
├── package-lock.json → Dependency lockfile
├── postcss.config.js → PostCSS configuration
├── tailwind.config.js → Tailwind CSS configuration
├── tsconfig.json → TypeScript configuration
├── tsconfig.app.json → TypeScript app configuration
├── tsconfig.node.json → TypeScript node configuration
├── vite.config.ts → Vite builder configuration
├── public/
│   └── vite.svg → Favicon
└── src/
    ├── App.css → Global application styles
    ├── App.tsx → Main React component layout and routing
    ├── index.css → Root CSS resets and variables
    ├── main.tsx → React application initialization
    ├── assets/
    │   └── react.svg → React logo asset
    ├── components/
    │   ├── AnalyticsCards.tsx → KPI metric display cards
    │   ├── GoogleMapView.tsx → Map visualization component
    │   ├── Layout.tsx → Wrapper component for sidebar and content
    │   ├── Sidebar.tsx → Navigation sidebar
    │   └── TuningPanel.tsx → Settings adjustment interface
    └── config/
        └── backend.ts → Backend API URL configuration
```

## Setup Instructions

- Ensure Node.js v18+ is installed
- Install node package dependencies

## Run Commands

- `npm install`
- `npm run dev`
- `npm run build`

## Key Functionalities

- Connects to backend WebSocket for live updates
- Renders Google Maps integration for heatmap viewing
- Provides UI for adjusting safety weighting parameters

## Notes

- Development server runs on port 5173
- Production builds target the `dist` directory
