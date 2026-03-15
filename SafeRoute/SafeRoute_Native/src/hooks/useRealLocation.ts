import { useEffect, useState, useCallback } from 'react';
import * as Location from 'expo-location';
import { Platform } from 'react-native';

/**
 * Hook: useRealLocation
 * 
 * Real GPS tracking using expo-location API.
 * - Requests FOREGROUND_LOCATION permission
 * - Watches device position every 10 seconds OR 10 meters
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
}

const FALLBACK_LOCATION: RealLocationCoordinates = {
    lat: 17.4435,   // Gachibowli center
    lng: 78.3484,
};

const LOCATION_UPDATE_INTERVAL_MS = 10000; // 10 seconds
const LOCATION_UPDATE_DISTANCE_M = 10;     // 10 meters

export const useRealLocation = () => {
    const [state, setState] = useState<RealLocationState>({
        location: null,
        error: null,
        isLoading: true,
        accuracy: null,
        lastUpdated: null,
    });

    // Request foreground location permission
    const requestLocationPermission = useCallback(async () => {
        try {
            const { status } = await Location.requestForegroundPermissionsAsync();
            
            if (status !== 'granted') {
                setState((prev) => ({
                    ...prev,
                    error: 'Location permission denied by user',
                    isLoading: false,
                    location: FALLBACK_LOCATION,
                }));
                console.warn('[Location] Permission denied — using fallback coordinates');
                return false;
            }

            console.log('[Location] Permission granted');
            return true;
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : String(err);
            setState((prev) => ({
                ...prev,
                error: `Permission request failed: ${errorMessage}`,
                isLoading: false,
                location: FALLBACK_LOCATION,
            }));
            console.error('[Location] Permission request error:', errorMessage);
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
                        setState((prev) => ({
                            ...prev,
                            location: { lat: latitude, lng: longitude },
                            accuracy: accuracy || null,
                            lastUpdated: new Date(),
                            isLoading: false,
                            error: null,
                        }));

                        console.log(
                            `[Location] Updated: ${latitude.toFixed(6)}, ${longitude.toFixed(6)} (accuracy: ${accuracy?.toFixed(1) || 'unknown'}m)`
                        );
                    } else {
                        console.warn('[Location] Invalid coordinates received:', { latitude, longitude });
                    }
                }
            );

            console.log('[Location] Started watching position');
            return watcher;
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : String(err);
            setState((prev) => ({
                ...prev,
                error: `Failed to start location tracking: ${errorMessage}`,
                isLoading: false,
                location: FALLBACK_LOCATION,
            }));
            console.error('[Location] Watch position error:', errorMessage);
            return null;
        }
    }, []);

    // Get single location as fallback
    const getCurrentLocation = useCallback(async () => {
        try {
            const location = await Location.getCurrentPositionAsync({
                accuracy: Location.Accuracy.High,
            });

            const { latitude, longitude, accuracy } = location.coords;

            setState((prev) => ({
                ...prev,
                location: { lat: latitude, lng: longitude },
                accuracy: accuracy || null,
                lastUpdated: new Date(),
                isLoading: false,
                error: null,
            }));

            console.log(`[Location] Got current position: ${latitude.toFixed(6)}, ${longitude.toFixed(6)}`);
            return { lat: latitude, lng: longitude };
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : String(err);
            console.error('[Location] Get current position error:', errorMessage);
            return null;
        }
    }, []);

    // Initialize location tracking on mount
    useEffect(() => {
        let watcher: Location.LocationSubscription | null = null;
        let isMounted = true;

        const initializeLocation = async () => {
            console.log('[Location] Initializing location tracking...');

            // Step 1: Request permission
            const permissionGranted = await requestLocationPermission();

            if (!permissionGranted || !isMounted) {
                return;
            }

            // Step 2: Try to get current location first
            const currentLoc = await getCurrentLocation();

            if (!isMounted) {
                return;
            }

            // Step 3: Start watching position
            watcher = await watchPosition();
        };

        initializeLocation();

        // Cleanup on unmount
        return () => {
            isMounted = false;
            if (watcher) {
                watcher.remove();
                console.log('[Location] Stopped watching position');
            }
        };
    }, [requestLocationPermission, watchPosition, getCurrentLocation]);

    return {
        location: state.location || FALLBACK_LOCATION,
        error: state.error,
        isLoading: state.isLoading,
        accuracy: state.accuracy,
        lastUpdated: state.lastUpdated,
        // Helper: check if using fallback
        isUsingFallback: !state.location || (
            state.location.lat === FALLBACK_LOCATION.lat &&
            state.location.lng === FALLBACK_LOCATION.lng
        ),
    };
};
