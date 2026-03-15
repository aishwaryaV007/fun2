import { create } from 'zustand';

type RouteType = 'fastest' | 'safest';

interface RouteData {
    type: RouteType;
    coordinates: Array<{ latitude: number; longitude: number }>;
    distance: number;
    estimatedTime: number;
    safetyScore: number;
}

interface AppState {
    activeRoute: RouteType;
    setActiveRoute: (route: RouteType) => void;
    currentRoute: RouteData | null;
    setCurrentRoute: (route: RouteData) => void;
    clearCurrentRoute: () => void;
    isSOSActive: boolean;
    triggerSOS: () => void;
    cancelSOS: () => void;
}

export const useAppStore = create<AppState>((set) => ({
    activeRoute: 'fastest',
    setActiveRoute: (route) => set({ activeRoute: route }),
    currentRoute: null,
    setCurrentRoute: (route) => set({ currentRoute: route }),
    clearCurrentRoute: () => set({ currentRoute: null }),
    isSOSActive: false,
    triggerSOS: () => set({ isSOSActive: true }),
    cancelSOS: () => set({ isSOSActive: false }),
}));
