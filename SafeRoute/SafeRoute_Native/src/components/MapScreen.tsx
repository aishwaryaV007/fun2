import React from 'react';
import { StyleSheet, View } from 'react-native';
import MapView, { Heatmap, Polyline, PROVIDER_GOOGLE } from 'react-native-maps';
import { useAppStore } from '../store/useAppStore';
import { MOCK_USER_LOCATION, HEATMAP_POINTS, FASTEST_ROUTE, SAFEST_ROUTE } from '../utils/mockData';
import { useRealLocation } from '../hooks/useRealLocation';

export const MapScreen = () => {
    const { activeRoute, currentRoute } = useAppStore();
    const { location, isUsingFallback } = useRealLocation();

    // Use real route from API if available, otherwise fall back to mock data
    const routeCoordinates = currentRoute?.type === activeRoute 
        ? currentRoute.coordinates 
        : (activeRoute === 'fastest' ? FASTEST_ROUTE : SAFEST_ROUTE);

    const routeColor = activeRoute === 'fastest' ? '#2196F3' : '#4CAF50';
    const initialRegion = {
        latitude: location?.lat ?? MOCK_USER_LOCATION.latitude,
        longitude: location?.lng ?? MOCK_USER_LOCATION.longitude,
        latitudeDelta: MOCK_USER_LOCATION.latitudeDelta,
        longitudeDelta: MOCK_USER_LOCATION.longitudeDelta,
    };

    return (
        <View style={styles.container}>
            <MapView
                style={styles.map}
                initialRegion={initialRegion}
                provider={PROVIDER_GOOGLE}
                showsUserLocation={!isUsingFallback}
                showsMyLocationButton={!isUsingFallback}
            >
                {/* Heatmap Layer */}
                <Heatmap
                    points={HEATMAP_POINTS as any}
                    radius={50}
                    opacity={0.6}
                    gradient={{
                        colors: ['#00000000', '#FFFF00', '#FF0000'],
                        startPoints: [0, 0.5, 1],
                        colorMapSize: 256,
                    }}
                />

                {/* Dynamic Route Polyline */}
                <Polyline
                    coordinates={routeCoordinates}
                    strokeColor={routeColor}
                    strokeWidth={4}
                    lineDashPattern={[1]}
                />
            </MapView>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#000',
    },
    map: {
        width: '100%',
        height: '100%',
    },
});
