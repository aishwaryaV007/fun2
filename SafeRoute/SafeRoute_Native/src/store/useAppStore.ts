import { create } from 'zustand';
import logger from '../utils/logger';

type RouteType = 'fastest' | 'safest';

export interface RouteData {
    type: RouteType;
    coordinates: Array<{ latitude: number; longitude: number }>;
    distance: number;
    estimatedTime: number;
    safetyScore: number;
}

export interface RouteHistory {
    id: string;
    timestamp: number;
    route: RouteData;
    startLocation: { lat: number; lng: number };
    endLocation: { lat: number; lng: number };
}

interface Preferences {
    enableShakeDetection: boolean;
    enableLocationTracking: boolean;
    emergencyContactsAdded: boolean;
}

interface AppState {
    // Route management
    activeRoute: RouteType;
    setActiveRoute: (route: RouteType) => void;

    currentRoute: RouteData | null;
    setCurrentRoute: (route: RouteData | null) => void;

    // Route history
    routeHistory: RouteHistory[];
    addToHistory: (history: RouteHistory) => void;
    clearHistory: () => void;

    // SOS state
    isSOSActive: boolean;
    triggerSOS: (details?: { lat?: number; lng?: number }) => void;
    cancelSOS: () => void;
    sosDetails: { timestamp: string; location: { lat: number; lng: number } | null } | null;

    // Preferences
    preferences: Preferences;
    updatePreferences: (prefs: Partial<Preferences>) => void;
}

export const useAppStore = create<AppState>((set) => ({
    // Route state
    activeRoute: 'fastest',
    setActiveRoute: (route) => {
        logger.info('[Store] Active route changed', { route });
        set({ activeRoute: route });
    },

    currentRoute: null,
    setCurrentRoute: (route) => {
        logger.info('[Store] Current route updated', { routeType: route?.type });
        set({ currentRoute: route });
    },

    // Route history
    routeHistory: [],
    addToHistory: (history) =>
        set((state) => {
            const newHistory = [history, ...state.routeHistory].slice(0, 50);
            logger.info('[Store] Route added to history', { id: history.id });
            return { routeHistory: newHistory };
        }),
    clearHistory: () => set({ routeHistory: [] }),

    // SOS
    isSOSActive: false,
    triggerSOS: (details) => {
        logger.warn('[Store] SOS activated', details || {});
        set({ isSOSActive: true, sosDetails: { timestamp: new Date().toISOString(), location: details ? { lat: details.lat ?? 0, lng: details.lng ?? 0 } : null } });
    },
    cancelSOS: () => {
        logger.info('[Store] SOS cancelled');
        set({ isSOSActive: false, sosDetails: null });
    },
    sosDetails: null,

    // Preferences
    preferences: {
        enableShakeDetection: true,
        enableLocationTracking: true,
        emergencyContactsAdded: false,
    },
    updatePreferences: (prefs) =>
        set((state) => {
            const next = { ...state.preferences, ...prefs };
            logger.info('[Store] Preferences updated', next);
            return { preferences: next };
        }),
}));

export default useAppStore;
