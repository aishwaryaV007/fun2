import React, { useEffect, useRef, useState } from 'react';
import { StyleSheet, TouchableOpacity, Text, View, Animated } from 'react-native';
import useAppStore from '../store/useAppStore';
import { useRealLocation } from '../hooks/useRealLocation';
import axios from 'axios';
import api from '../config/api';
import logger from '../utils/logger';

/**
 * Mini SOS Button - Top Right
 * Long-press to trigger SOS with countdown, press to cancel
 */
export const MiniSOSButton: React.FC = () => {
    const isSOSActive = useAppStore((s) => s.isSOSActive);
    const triggerSOS = useAppStore((s) => s.triggerSOS);
    const cancelSOS = useAppStore((s) => s.cancelSOS);

    const { location } = useRealLocation();
    const [countdown, setCountdown] = useState<number>(-1);
    const pulseAnim = useRef(new Animated.Value(1)).current;
    const intervalRef = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        let animation: Animated.CompositeAnimation | null = null;
        if (isSOSActive) {
            animation = Animated.loop(
                Animated.sequence([
                    Animated.timing(pulseAnim, { toValue: 1.08, duration: 500, useNativeDriver: true }),
                    Animated.timing(pulseAnim, { toValue: 1, duration: 500, useNativeDriver: true }),
                ])
            );
            animation.start();
        }
        return () => {
            if (animation) animation.stop();
        };
    }, [isSOSActive, pulseAnim]);

    useEffect(() => {
        // -1 = idle, skip
        if (countdown < 0) return;

        if (countdown === 0) {
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
                intervalRef.current = null;
            }
            // Countdown finished — fire SOS
            doSendSOS();
            return;
        }

        if (!intervalRef.current) {
            intervalRef.current = setInterval(() => setCountdown((c) => c - 1), 1000);
        }

        return () => {
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
                intervalRef.current = null;
            }
        };
    }, [countdown]);

    const doSendSOS = async () => {
        try {
            if (!location) {
                logger.error('[MiniSOS] No location available');
                cancelSOS();
                return;
            }

            const payload = {
                latitude: location.lat,
                longitude: location.lng,
                timestamp: new Date().toISOString(),
                trigger: 'button',
            };

            logger.warn('[MiniSOS] Sending SOS', payload);
            await axios.post(`${api.BASE_URL}/sos`, payload);
            cancelSOS();
        } catch (err) {
            logger.error('[MiniSOS] send failed', err);
        }
    };

    const handleLongPress = () => {
        triggerSOS();
        setCountdown(3);
    };

    const handlePress = () => {
        // allow cancel during countdown or active
        if (countdown > 0 || isSOSActive) {
            cancelSOS();
            setCountdown(-1);
            logger.info('[MiniSOS] Cancelled');
        }
    };

    const isCounting = countdown > 0;

    return (
        <Animated.View style={[styles.container, { transform: [{ scale: pulseAnim }] }]} pointerEvents="box-none">
            <TouchableOpacity
                style={[styles.sosButton, isCounting && styles.sosButtonCounting, isSOSActive && styles.sosButtonActive]}
                onLongPress={handleLongPress}
                delayLongPress={800}
                onPress={handlePress}
                activeOpacity={0.8}
            >
                {isCounting ? <Text style={styles.countdownText}>{countdown}</Text> : <Text style={styles.sosText}>SOS</Text>}
            </TouchableOpacity>

            {isSOSActive && !isCounting && (
                <View style={styles.statusBadge}>
                    <Text style={styles.statusText}>ACTIVE</Text>
                </View>
            )}
        </Animated.View>
    );
};

const styles = StyleSheet.create({
    container: {
        position: 'absolute',
        top: 48,
        right: 18,
        zIndex: 999,
    },
    sosButton: {
        width: 64,
        height: 64,
        borderRadius: 32,
        backgroundColor: '#dc143c',
        justifyContent: 'center',
        alignItems: 'center',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.3,
        shadowRadius: 5,
        elevation: 8,
    },
    sosButtonActive: {
        backgroundColor: '#ff4444',
        borderWidth: 2,
        borderColor: '#fff',
    },
    sosButtonCounting: {
        backgroundColor: '#ff6b6b',
    },
    sosText: {
        color: '#fff',
        fontWeight: '700',
        fontSize: 16,
    },
    countdownText: {
        color: '#fff',
        fontWeight: '800',
        fontSize: 22,
    },
    statusBadge: {
        position: 'absolute',
        top: -10,
        right: -10,
        backgroundColor: '#ff4444',
        borderRadius: 10,
        paddingHorizontal: 6,
        paddingVertical: 2,
        borderWidth: 2,
        borderColor: '#fff',
    },
    statusText: {
        fontSize: 9,
        color: '#fff',
        fontWeight: 'bold',
    },
});

export default MiniSOSButton;