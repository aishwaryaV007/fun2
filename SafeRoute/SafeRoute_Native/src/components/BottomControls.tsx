import React from 'react';
import { StyleSheet, View, Text, TouchableOpacity } from 'react-native';
import { useAppStore } from '../store/useAppStore';
import { RouteSelector } from './RouteSelector';

export const BottomControls = () => {
    const { activeRoute, setActiveRoute, currentRoute } = useAppStore();
    const [routeSelectorVisible, setRouteSelectorVisible] = React.useState(false);

    return (
        <>
            <View style={styles.container}>
                <Text style={styles.title}>Navigation Mode</Text>
                
                {/* Route Info */}
                {currentRoute && (
                    <View style={styles.routeInfoContainer}>
                        <Text style={styles.routeInfo}>
                            {(currentRoute.distance / 1000).toFixed(1)} km • {(currentRoute.estimatedTime / 60).toFixed(0)} min
                        </Text>
                        {currentRoute.safetyScore > 0 && (
                            <Text style={styles.safetyScore}>
                                Safety: {currentRoute.safetyScore}%
                            </Text>
                        )}
                    </View>
                )}

                <View style={styles.buttonContainer}>
                    <TouchableOpacity
                        style={[styles.button, activeRoute === 'fastest' && styles.activeButtonFast]}
                        onPress={() => setActiveRoute('fastest')}
                    >
                        <Text style={[styles.buttonText, activeRoute === 'fastest' && styles.activeText]}>
                            ⚡ Fastest
                        </Text>
                    </TouchableOpacity>

                    <TouchableOpacity
                        style={[styles.button, activeRoute === 'safest' && styles.activeButtonSafe]}
                        onPress={() => setActiveRoute('safest')}
                    >
                        <Text style={[styles.buttonText, activeRoute === 'safest' && styles.activeText]}>
                            ✓ Safest
                        </Text>
                    </TouchableOpacity>

                    <TouchableOpacity
                        style={styles.routeButton}
                        onPress={() => setRouteSelectorVisible(true)}
                    >
                        <Text style={styles.routeButtonText}>🗺️ Routes</Text>
                    </TouchableOpacity>
                </View>
            </View>

            {/* Route Selector Modal */}
            {routeSelectorVisible && (
                <RouteSelector 
                    visible={routeSelectorVisible}
                    onClose={() => setRouteSelectorVisible(false)}
                />
            )}
        </>
    );
};

const styles = StyleSheet.create({
    container: {
        position: 'absolute',
        bottom: 40,
        left: 20,
        right: 20,
        backgroundColor: 'rgba(255,255,255,0.95)',
        borderRadius: 20,
        padding: 20,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.3,
        shadowRadius: 5,
        elevation: 8,
    },
    title: {
        fontSize: 16,
        fontWeight: 'bold',
        marginBottom: 10,
        color: '#333',
        textAlign: 'center',
    },
    routeInfoContainer: {
        backgroundColor: '#f5f5f5',
        borderRadius: 8,
        padding: 8,
        marginBottom: 12,
        alignItems: 'center',
    },
    routeInfo: {
        fontSize: 12,
        color: '#666',
        fontWeight: '500',
    },
    safetyScore: {
        fontSize: 11,
        color: '#4CAF50',
        marginTop: 4,
    },
    buttonContainer: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        gap: 8,
    },
    button: {
        flex: 1,
        paddingVertical: 12,
        borderRadius: 10,
        backgroundColor: '#f0f0f0',
        alignItems: 'center',
    },
    activeButtonFast: {
        backgroundColor: '#2196F3',
    },
    activeButtonSafe: {
        backgroundColor: '#4CAF50',
    },
    buttonText: {
        fontSize: 13,
        fontWeight: '600',
        color: '#666',
    },
    activeText: {
        color: '#FFF',
    },
    routeButton: {
        backgroundColor: '#2196F3',
        borderRadius: 10,
        paddingHorizontal: 12,
        paddingVertical: 12,
        justifyContent: 'center',
        alignItems: 'center',
    },
    routeButtonText: {
        color: '#fff',
        fontSize: 13,
        fontWeight: '600',
    },
});
