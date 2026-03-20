import React, { useEffect, useRef, useState } from 'react';
import { StyleSheet, TouchableOpacity, Text, Vibration, Alert, View } from 'react-native';
import { useAppStore } from '../store/useAppStore';
import { useRealLocation } from '../hooks/useRealLocation';
import { useShakeDetection } from "../hooks/useShakeDetection";
import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import NetInfo from '@react-native-community/netinfo';
import { HEARTBEAT_WS_URL, SOS_TRIGGER_URL } from '../config/backend';
import { getOrCreateClientId } from '../utils/clientIdentity';

const SOS_QUEUE_KEY = '@sos_queue';
const HEARTBEAT_INTERVAL_MS = 20_000;
const HEARTBEAT_RECONNECT_DELAY_MS = 5_000;

interface SOSPayload {
    user_id: string;
    latitude: number;
    longitude: number;
    timestamp: string;
    trigger_type: string;
    message: string;
    device_info: string;
    delayed?: boolean;
}

function parseQueue(queueStr: string | null): SOSPayload[] {
    if (!queueStr) {
        return [];
    }

    try {
        const parsed = JSON.parse(queueStr);
        return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
        console.warn('[SOS] Invalid offline queue payload, resetting queue', error);
        return [];
    }
}

export const SOSButton = () => {
    const { isSOSActive, triggerSOS, cancelSOS } = useAppStore();
    const { location, error: locationError, isLoading: locationLoading, isUsingFallback } = useRealLocation();
    const [countdown, setCountdown] = useState<number | null>(null);
    const [clientId, setClientId] = useState<string>('user-123');
    const heartbeatSocketRef = useRef<WebSocket | null>(null);
    const heartbeatIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    // Handle shake detection — automatically trigger SOS if not already active
    const handleShakeDetected = () => {
        if (!isSOSActive && countdown === null) {
            console.log('[SOSButton] Shake triggered SOS!');
            triggerSOS();
            setCountdown(3);
        } else {
            console.log('[SOSButton] Shake ignored — SOS already active or countdown in progress');
        }
    };

    // Enable shake detection with 5-second debounce and [100, 50, 100] vibration pattern
    useShakeDetection({
        onShakeDetected: handleShakeDetected,
        debounceMs: 5000,
        vibrationPattern: [100, 50, 100],
        enabled: true,
    });

    useEffect(() => {
        let isMounted = true;

        getOrCreateClientId()
            .then((id) => {
                if (isMounted) {
                    setClientId(id);
                }
            })
            .catch((error) => {
                console.warn('[SOS] Failed to load client identity, using fallback ID', error);
            });

        return () => {
            isMounted = false;
        };
    }, []);

    // Method to process any queued SOS alerts from AsyncStorage when offline
    const processQueue = async () => {
        try {
            const queue = parseQueue(await AsyncStorage.getItem(SOS_QUEUE_KEY));
            if (queue.length === 0) {
                return;
            }

            console.log(`Network restored! Attempting to sync ${queue.length} offline SOS alerts...`);
            const remainingQueue: SOSPayload[] = [];

            for (const payload of queue) {
                try {
                    await axios.post(SOS_TRIGGER_URL, { ...payload, delayed: true });
                } catch (error) {
                    console.warn('[SOS] Failed to sync queued alert, leaving it in storage', error);
                    remainingQueue.push({ ...payload, delayed: true });
                }
            }

            if (remainingQueue.length > 0) {
                await AsyncStorage.setItem(SOS_QUEUE_KEY, JSON.stringify(remainingQueue));
                console.log(`[SOS] ${remainingQueue.length} queued alert(s) still pending sync.`);
                return;
            }

            await AsyncStorage.removeItem(SOS_QUEUE_KEY);
            console.log('Offline SOS queue synced and cleared successfully.');
        } catch (error) {
            console.error('Error processing offline SOS queue:', error);
        }
    };

    // ── WebSocket Heartbeat — registers device as an active user ───────────
    useEffect(() => {
        let isMounted = true;

        const clearHeartbeatInterval = () => {
            if (heartbeatIntervalRef.current) {
                clearInterval(heartbeatIntervalRef.current);
                heartbeatIntervalRef.current = null;
            }
        };

        const scheduleReconnect = () => {
            if (!isMounted || reconnectTimeoutRef.current) {
                return;
            }

            reconnectTimeoutRef.current = setTimeout(() => {
                reconnectTimeoutRef.current = null;
                connect();
            }, HEARTBEAT_RECONNECT_DELAY_MS);
        };

        const connect = () => {
            try {
                const socket = new WebSocket(HEARTBEAT_WS_URL);
                heartbeatSocketRef.current = socket;

                socket.onopen = () => {
                    console.log('[Heartbeat] Connected to backend');
                    clearHeartbeatInterval();
                    heartbeatIntervalRef.current = setInterval(() => {
                        if (socket.readyState === WebSocket.OPEN) {
                            socket.send('ping');
                        }
                    }, HEARTBEAT_INTERVAL_MS);
                };

                socket.onerror = (event) => {
                    console.warn('[Heartbeat] WS error', event);
                };

                socket.onclose = () => {
                    clearHeartbeatInterval();
                    if (heartbeatSocketRef.current === socket) {
                        heartbeatSocketRef.current = null;
                    }
                    if (isMounted) {
                        scheduleReconnect();
                    }
                };
            } catch (error) {
                console.warn('[Heartbeat] Could not connect', error);
                scheduleReconnect();
            }
        };

        connect();
        return () => {
            isMounted = false;
            clearHeartbeatInterval();
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
                reconnectTimeoutRef.current = null;
            }
            if (heartbeatSocketRef.current) {
                heartbeatSocketRef.current.close();
                heartbeatSocketRef.current = null;
            }
        };
    }, []);

    // ── Offline Queue Sync ─────────────────────────────────────────────
    // Set up a listener to detect when network connection is restored
    useEffect(() => {
        const unsubscribe = NetInfo.addEventListener(state => {
            if (state.isConnected && state.isInternetReachable !== false) {
                // Device came back online, sync the queue!
                processQueue();
            }
        });

        // Initial queue process check on mount
        NetInfo.fetch().then(state => {
            if (state.isConnected) processQueue();
        });

        // Cleanup the listener on component unmount
        return () => unsubscribe();
    }, []);

    // Core SOS trigger logic handling online vs offline routing
    const sendSOSAlert = async () => {
        // Construct the payload with REAL location from GPS
        const payload: SOSPayload = {
            user_id: clientId,
            latitude: location.lat,
            longitude: location.lng,
            timestamp: new Date().toISOString(),
            trigger_type: 'button',
            message: 'SOS Alert triggered via mobile app',
            device_info: `SafeRoute Mobile (${isUsingFallback ? 'fallback location' : 'real GPS'})`,
            delayed: false,
        };

        try {
            const state = await NetInfo.fetch();
            if (state.isConnected && state.isInternetReachable !== false) {
                // Online: Try sending directly to backend
                await axios.post(SOS_TRIGGER_URL, payload);
                console.log(`[SOS] Alert dispatched to backend at ${location.lat.toFixed(6)}, ${location.lng.toFixed(6)}`);
                if (isUsingFallback) {
                    console.warn('[SOS] ⚠️  Using fallback location (GPS unavailable)');
                }
            } else {
                // Offline: Throw error to fall into catch block and queue
                throw new Error('Device is offline');
            }
        } catch (error) {
            // Either the POST failed (e.g. server down) or the device was offline. Cache the alert.
            console.log('[SOS] Failed to send SOS immediately. Saving to offline queue...', error);
            try {
                const queue = parseQueue(await AsyncStorage.getItem(SOS_QUEUE_KEY));
                queue.push({ ...payload, delayed: true });
                await AsyncStorage.setItem(SOS_QUEUE_KEY, JSON.stringify(queue));
                console.log('[SOS] Alert securely cached offline.');
            } catch (storageError) {
                console.error('[SOS] Critical Failure: Could not save to Offline Queue', storageError);
            }
        }
    };

    useEffect(() => {
        let timer: NodeJS.Timeout;
        if (countdown !== null && countdown > 0) {
            timer = setTimeout(() => {
                setCountdown(countdown - 1);
                Vibration.vibrate(200); // Vibrate on each tick
            }, 1000);
        } else if (countdown === 0) {
            // Countdown finished! Trigger the actual backend alerting process.
            Vibration.vibrate(1000); // Long vibrate
            Alert.alert(
                "SOS Triggered",
                "Emergency Contacts and Data Centers Notified.",
                [{ text: "OK", onPress: cancelSOS }]
            );
            setCountdown(null);

            // Send the network request
            sendSOSAlert();
        }

        return () => {
            if (timer) clearTimeout(timer);
        };
    }, [countdown, cancelSOS]);

    const handlePress = () => {
        if (!isSOSActive && countdown === null) {
            triggerSOS();
            setCountdown(3);
            Vibration.vibrate(200);
        }
    };

    const handleCancel = () => {
        cancelSOS();
        setCountdown(null);
    };

    if (countdown !== null) {
        return (
            <View style={styles.countdownContainer}>
                <Text style={styles.countdownText}>SOS in {countdown}...</Text>
                <TouchableOpacity style={styles.cancelButton} onPress={handleCancel}>
                    <Text style={styles.cancelText}>CANCEL</Text>
                </TouchableOpacity>
            </View>
        );
    }

    return (
        <View>
            <TouchableOpacity style={styles.sosButton} onPress={handlePress} activeOpacity={0.8}>
                <Text style={styles.sosText}>SOS</Text>
            </TouchableOpacity>
            
            {/* Location Status Indicator */}
            <View style={styles.locationStatusContainer}>
                <Text style={styles.locationStatusText}>
                    {locationLoading ? '📍 Acquiring location...' : isUsingFallback ? '⚠️ Using fallback location' : '✓ Real GPS active'}
                </Text>
                {location && (
                    <Text style={styles.coordinatesText}>
                        {location.lat.toFixed(6)}, {location.lng.toFixed(6)}
                    </Text>
                )}
                {locationError && (
                    <Text style={styles.errorText}>{locationError}</Text>
                )}
            </View>
        </View>
    );
};

const styles = StyleSheet.create({
    sosButton: {
        position: 'absolute',
        bottom: 100,
        right: 20,
        width: 72,
        height: 72,
        borderRadius: 36,
        backgroundColor: '#FF3B30',
        justifyContent: 'center',
        alignItems: 'center',
        shadowColor: '#FF0000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.6,
        shadowRadius: 10,
        elevation: 10,
        zIndex: 999,
    },
    sosText: {
        color: '#FFF',
        fontSize: 22,
        fontWeight: '900',
        letterSpacing: 1,
    },
    countdownContainer: {
        position: 'absolute',
        bottom: 100,
        right: 20,
        backgroundColor: 'rgba(255, 59, 48, 0.95)',
        borderRadius: 20,
        padding: 15,
        alignItems: 'center',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.4,
        shadowRadius: 8,
        elevation: 10,
        zIndex: 999,
    },
    countdownText: {
        color: '#FFF',
        fontSize: 18,
        fontWeight: 'bold',
        marginBottom: 10,
    },
    cancelButton: {
        backgroundColor: '#FFF',
        paddingHorizontal: 20,
        paddingVertical: 8,
        borderRadius: 15,
    },
    cancelText: {
        color: '#FF3B30',
        fontWeight: 'bold',
    },
    locationStatusContainer: {
        position: 'absolute',
        bottom: 20,
        left: 12,
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        paddingHorizontal: 12,
        paddingVertical: 8,
        borderRadius: 8,
        maxWidth: 220,
    },
    locationStatusText: {
        color: '#FFF',
        fontSize: 11,
        fontWeight: '600',
        marginBottom: 4,
    },
    coordinatesText: {
        color: '#4CAF50',
        fontSize: 10,
        fontFamily: 'monospace',
        marginBottom: 2,
    },
    errorText: {
        color: '#FF9800',
        fontSize: 10,
        marginTop: 2,
    },
});
