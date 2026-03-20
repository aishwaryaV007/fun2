import React, { useMemo } from 'react';
import { StyleSheet, View, ActivityIndicator, Text } from 'react-native';
import MapView, { Marker, Polyline, PROVIDER_GOOGLE, Region } from 'react-native-maps';
import useAppStore from '../store/useAppStore';
import { useRealLocation } from '../hooks/useRealLocation';
import { SOSButton } from './SOSButton';

export const MapScreen: React.FC = () => {
    const { location, isLoading, isUsingFallback } = useRealLocation();

    const currentRoute = useAppStore((s) => s.currentRoute);

    const region: Region = useMemo(
        () => ({
            latitude: location?.lat ?? 17.4435,
            longitude: location?.lng ?? 78.3484,
            latitudeDelta: 0.01,
            longitudeDelta: 0.01,
        }),
        [location]
    );

    const pathCoordinates = useMemo(() => {
        return (
            currentRoute?.coordinates?.map((c) => ({ latitude: c.latitude, longitude: c.longitude })) || []
        );
    }, [currentRoute]);

    return (
        <View style={styles.container}>
            <MapView
                provider={PROVIDER_GOOGLE}
                style={styles.map}
                initialRegion={region}
                showsUserLocation={true}
                followsUserLocation={true}
            >
                {pathCoordinates.length > 0 && <Polyline coordinates={pathCoordinates} strokeWidth={4} strokeColor="#1976D2" />}

                {pathCoordinates.length > 0 && <Marker coordinate={pathCoordinates[0]} pinColor="green" />}
                {pathCoordinates.length > 1 && <Marker coordinate={pathCoordinates[pathCoordinates.length - 1]} pinColor="red" />}
            </MapView>

            {/* Render SOS button AFTER the map so it sits on top */}
            <SOSButton />

            {(isLoading || !location) && (
                <View style={styles.loadingOverlay} pointerEvents="none">
                    <ActivityIndicator size="large" color="#1976D2" />
                    <Text style={styles.loadingText}>{isUsingFallback ? 'Using fallback location' : 'Fetching location…'}</Text>
                </View>
            )}
        </View>
    );
};

const styles = StyleSheet.create({
    container: { flex: 1 },
    map: { flex: 1 },
    loadingOverlay: {
        position: 'absolute',
        left: 0,
        right: 0,
        top: 0,
        bottom: 0,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: 'rgba(255,255,255,0.6)',
    },
    loadingText: { marginTop: 8, color: '#333' },
});

export default MapScreen;
