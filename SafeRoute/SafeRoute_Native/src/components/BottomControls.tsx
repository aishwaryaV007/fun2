import React, { useState } from 'react';
import { StyleSheet, View, Text, TouchableOpacity, Animated, Easing } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useAppStore } from '../store/useAppStore';
import { RouteSelector } from './RouteSelector';
import logger from '../utils/logger';

/**
 * BottomControls Component
 * Provides route mode selection and navigation controls
 */
export const BottomControls = () => {
    const navigation = useNavigation();
    const { activeRoute, setActiveRoute, currentRoute } = useAppStore();
    const [routeSelectorVisible, setRouteSelectorVisible] = useState(false);
    const [scaleAnim] = React.useState(new Animated.Value(1));

    const handleRouteChange = (route: 'fastest' | 'safest') => {
        setActiveRoute(route);
        
        // Visual feedback
        Animated.sequence([
            Animated.timing(scaleAnim, {
                toValue: 1.05,
                duration: 100,
                easing: Easing.inOut(Easing.ease),
                useNativeDriver: true,
            }),
            Animated.timing(scaleAnim, {
                toValue: 1,
                duration: 100,
                easing: Easing.inOut(Easing.ease),
                useNativeDriver: true,
            }),
        ]).start();

        logger.info('[BottomControls] Route changed', { route });
    };

    const handleRouteSelector = () => {
        navigation.navigate('RouteSearch' as never);
        logger.info('[BottomControls] Navigating to route search');
    };

    return (
        <>
            <Animated.View 
                style={[
                    styles.container,
                    {
                        transform: [{ scale: scaleAnim }],
                    },
                ]}
            >
                {/* Route Info */}
                {currentRoute && (
                    <View style={styles.routeInfoContainer}>
                        <View style={styles.infoLeft}>
                            <Text style={styles.routeInfo}>
                                📏 {(currentRoute.distance / 1000).toFixed(1)} km
                            </Text>
                            <Text style={styles.separator}>•</Text>
                            <Text style={styles.routeInfo}>
                                ⏱️ {(currentRoute.estimatedTime / 60).toFixed(0)} min
                            </Text>
                        </View>
                        {currentRoute.safetyScore > 0 && (
                            <View style={styles.safetyBadge}>
                                <Text style={styles.safetyScore}>
                                    🛡️ {currentRoute.safetyScore}%
                                </Text>
                            </View>
                        )}
                    </View>
                )}

                {/* Control Buttons */}
                <View style={styles.buttonContainer}>
                    <TouchableOpacity
                        style={[
                            styles.button,
                            activeRoute === 'fastest' && styles.activeButtonFast,
                        ]}
                        onPress={() => handleRouteChange('fastest')}
                        activeOpacity={0.7}
                    >
                        <Text style={styles.buttonIcon}>⚡</Text>
                        <Text
                            style={[
                                styles.buttonText,
                                activeRoute === 'fastest' && styles.activeText,
                            ]}
                        >
                            Fastest
                        </Text>
                    </TouchableOpacity>

                    <TouchableOpacity
                        style={[
                            styles.button,
                            activeRoute === 'safest' && styles.activeButtonSafe,
                        ]}
                        onPress={() => handleRouteChange('safest')}
                        activeOpacity={0.7}
                    >
                        <Text style={styles.buttonIcon}>✓</Text>
                        <Text
                            style={[
                                styles.buttonText,
                                activeRoute === 'safest' && styles.activeText,
                            ]}
                        >
                            Safest
                        </Text>
                    </TouchableOpacity>

                    <TouchableOpacity
                        style={styles.routeButton}
                        onPress={handleRouteSelector}
                        activeOpacity={0.7}
                    >
                        <Text style={styles.routeButtonText}>🗺️ Routes</Text>
                    </TouchableOpacity>
                </View>
            </Animated.View>
        </>
    );
};

const styles = StyleSheet.create({
    container: {
        position: 'absolute',
        bottom: 20,
        left: 16,
        right: 16,
        backgroundColor: 'rgba(255,255,255,0.98)',
        borderRadius: 16,
        padding: 16,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 6 },
        shadowOpacity: 0.25,
        shadowRadius: 8,
        elevation: 10,
    },
    routeInfoContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        backgroundColor: '#f0f7ff',
        borderRadius: 10,
        padding: 10,
        marginBottom: 14,
        borderLeftWidth: 3,
        borderLeftColor: '#4CAF50',
    },
    infoLeft: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    routeInfo: {
        fontSize: 12,
        color: '#333',
        fontWeight: '600',
    },
    separator: {
        marginHorizontal: 8,
        color: '#ddd',
        fontSize: 14,
    },
    safetyBadge: {
        backgroundColor: '#4CAF50',
        paddingHorizontal: 10,
        paddingVertical: 4,
        borderRadius: 6,
    },
    safetyScore: {
        fontSize: 11,
        color: '#fff',
        fontWeight: 'bold',
    },
    buttonContainer: {
        flexDirection: 'row',
        gap: 8,
    },
    button: {
        flex: 1,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        paddingVertical: 12,
        paddingHorizontal: 8,
        borderRadius: 10,
        borderWidth: 2,
        borderColor: '#e0e0e0',
        backgroundColor: '#fff',
    },
    activeButtonFast: {
        backgroundColor: '#e3f2fd',
        borderColor: '#2196F3',
    },
    activeButtonSafe: {
        backgroundColor: '#e8f5e9',
        borderColor: '#4CAF50',
    },
    buttonIcon: {
        fontSize: 16,
        marginRight: 4,
    },
    buttonText: {
        fontSize: 12,
        fontWeight: '600',
        color: '#666',
    },
    activeText: {
        color: '#333',
    },
    routeButton: {
        flex: 1.2,
        paddingVertical: 12,
        paddingHorizontal: 10,
        borderRadius: 10,
        backgroundColor: '#FFC107',
        alignItems: 'center',
        justifyContent: 'center',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 3 },
        shadowOpacity: 0.2,
        shadowRadius: 4,
        elevation: 5,
    },
    routeButtonText: {
        fontSize: 12,
        fontWeight: '600',
        color: '#fff',
    },
});
