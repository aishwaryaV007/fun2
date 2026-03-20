import { useEffect, useState, useCallback } from 'react';
import * as Location from 'expo-location';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import NetInfo from '@react-native-community/netinfo';
import logger from '../utils/logger';

/**
 * Hook: useRealLocation
 *
 * Real GPS tracking using expo-location API with offline support.
 * - Requests FOREGROUND_LOCATION permission
 * - Watches device position every 10 seconds OR 10 meters
 * - Caches location data for offline use
 * - Returns { lat, lng } coordinates
 * - Fallback: 17.4435, 78.3484 (Gachibowli, Hyderabad)
 */

export interface RealLocationCoordinates {
    lat: number;
    lng: number;
}

export interface RealLocationState {
    location: RealLocationCoordinates | null;
    error: string | null;
    isLoading: boolean;
    accuracy: number | null;
    lastUpdated: Date | null;
    isOnline: boolean;
}

const FALLBACK_LOCATION: RealLocationCoordinates = {
    lat: 17.4435, // Gachibowli center
    lng: 78.3484,
};

const LOCATION_UPDATE_INTERVAL_MS = 10000; // 10 seconds
const LOCATION_UPDATE_DISTANCE_M = 10;     // 10 meters
const CACHED_LOCATION_KEY = '@cached_location';
const LOCATION_CACHE_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes

interface CachedLocation extends RealLocationCoordinates {
    timestamp: number;
}

export const useRealLocation = () => {
    const [state, setState] = useState<RealLocationState>({
        location: null,
        error: null,
        isLoading: true,
        accuracy: null,
        lastUpdated: null,
        isOnline: true,
    });

    // Monitor network connectivity
    useEffect(() => {
        const unsubscribe = NetInfo.addEventListener((s) => {
            const isOnline = s.isConnected ?? true;
            logger.info('[Location] Network status', { isOnline });
            setState((prev) => ({ ...prev, isOnline }));
        });

        return () => unsubscribe();
    }, []);

    // Load cached location from AsyncStorage
    const loadCachedLocation = useCallback(async () => {
        try {
            const cached = await AsyncStorage.getItem(CACHED_LOCATION_KEY);
            if (cached) {
                const location: CachedLocation = JSON.parse(cached);
                const age = Date.now() - location.timestamp;

                if (age < LOCATION_CACHE_TIMEOUT_MS) {
                    logger.info('[Location] Loaded cached location', { age: age / 1000 });
                    return { lat: location.lat, lng: location.lng };
                } else {
                    logger.debug('[Location] Cached location expired');
                }
            }
        } catch (error) {
            logger.warn('[Location] Failed to load cached location', error);
        }
        return null;
    }, []);

    // Save location to cache
    const cacheLocation = useCallback(async (location: RealLocationCoordinates) => {
        try {
            const cached: CachedLocation = {
                ...location,
                timestamp: Date.now(),
            };
            await AsyncStorage.setItem(CACHED_LOCATION_KEY, JSON.stringify(cached));
        } catch (error) {
            logger.warn('[Location] Failed to cache location', error);
        }
    }, []);

    // Request foreground location permission
    const requestLocationPermission = useCallback(async () => {
        try {
            const { status } = await Location.requestForegroundPermissionsAsync();

            if (status !== 'granted') {
                setState((prev) => ({ ...prev, error: 'Location permission denied by user', isLoading: false }));
                logger.warn('[Location] Permission denied — using fallback coordinates');
                return false;
            }

            logger.info('[Location] Permission granted');
            return true;
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : String(err);
            setState((prev) => ({ ...prev, error: `Permission request failed: ${errorMessage}`, isLoading: false }));
            logger.error('[Location] Permission request error', err);
            return false;
        }
    }, []);

    // Watch device position
    const watchPosition = useCallback(async () => {
        try {
            const watcher = await Location.watchPositionAsync(
                {
                    accuracy: Location.Accuracy.High,
                    timeInterval: LOCATION_UPDATE_INTERVAL_MS,
                    distanceInterval: LOCATION_UPDATE_DISTANCE_M,
                },
                (position) => {
                    const { latitude, longitude, accuracy } = position.coords;

                    // Validate coordinates
                    if (
                        typeof latitude === 'number' &&
                        typeof longitude === 'number' &&
                        isFinite(latitude) &&
                        isFinite(longitude) &&
                        latitude >= -90 &&
                        latitude <= 90 &&
                        longitude >= -180 &&
                        longitude <= 180
                    ) {
                        const newLocation = { lat: latitude, lng: longitude };

                        setState((prev) => ({
                            ...prev,
                            location: newLocation,
                            accuracy: accuracy || null,
                            lastUpdated: new Date(),
                            isLoading: false,
                            error: null,
                        }));

                        cacheLocation(newLocation);

                        logger.debug('[Location] Updated position', {
                            lat: latitude.toFixed(6),
                            lng: longitude.toFixed(6),
                            accuracy: accuracy?.toFixed(1),
                        });
                    } else {
                        logger.warn('[Location] Invalid coordinates received', { latitude, longitude });
                    }
                }
            );

            logger.info('[Location] Started watching position');
            return watcher;
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : String(err);
            setState((prev) => ({
                ...prev,
                error: `Failed to start location tracking: ${errorMessage}`,
                isLoading: false,
            }));
            logger.error('[Location] Watch position error', err);
            return null;
        }
    }, [cacheLocation]);

    // Get single location as fallback
    const getCurrentLocation = useCallback(async () => {
        try {
            const location = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High });
            const { latitude, longitude, accuracy } = location.coords;
            const newLocation = { lat: latitude, lng: longitude };

            setState((prev) => ({
                ...prev,
                location: newLocation,
                accuracy: accuracy || null,
                lastUpdated: new Date(),
                isLoading: false,
                error: null,
            }));

            cacheLocation(newLocation);
            logger.info('[Location] Got current position', { lat: latitude.toFixed(6), lng: longitude.toFixed(6) });
            return newLocation;
        } catch (err) {
            logger.error('[Location] Get current position error', err);
            return null;
        }
    }, [cacheLocation]);

    // Initialize location tracking on mount
    useEffect(() => {
        let watcher: Location.LocationSubscription | null = null;
        let isMounted = true;

        const initializeLocation = async () => {
            logger.info('[Location] Initializing location tracking...');

            // Step 1: Try to load cached location first
            const cachedLoc = await loadCachedLocation();
            if (cachedLoc && isMounted) {
                setState((prev) => ({ ...prev, location: cachedLoc, isLoading: false, error: null }));
            }

            // Step 2: Request permission
            const permissionGranted = await requestLocationPermission();
            if (!permissionGranted || !isMounted) return;

            // Step 3: Try to get current location
            await getCurrentLocation();
            if (!isMounted) return;

            // Step 4: Start watching position
            watcher = await watchPosition();
        };

        initializeLocation();

        return () => {
            isMounted = false;
            if (watcher) {
                watcher.remove();
                logger.info('[Location] Stopped watching position');
            }
        };
    }, [requestLocationPermission, watchPosition, getCurrentLocation, loadCachedLocation]);

    return {
        location: state.location || FALLBACK_LOCATION,
        error: state.error,
        isLoading: state.isLoading,
        accuracy: state.accuracy,
        lastUpdated: state.lastUpdated,
        isOnline: state.isOnline,
        isUsingFallback:
            !state.location ||
            (state.location.lat === FALLBACK_LOCATION.lat && state.location.lng === FALLBACK_LOCATION.lng),
    };
};
