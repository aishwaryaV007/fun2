import React, { useState, useEffect } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Modal,
  Dimensions,
} from 'react-native';
import axios from 'axios';
import { useAppStore } from '../store/useAppStore';
import { useRealLocation } from '../hooks/useRealLocation';
import { ROUTES_API_URL } from '../config/backend';
import logger from '../utils/logger';

const DEFAULT_WALKING_SPEED_METERS_PER_SECOND = 1.4;

interface RouteCoordinates {
  lat: number;
  lng: number;
}

interface RouteResponse {
  route: RouteCoordinates[];
  distance_meters?: number;
  distance_km?: number;
  estimated_time?: number;
  safety_score?: number;
}

interface RouteSelectorProps {
  visible: boolean;
  onClose: () => void;
}

const { width } = Dimensions.get('window');

function estimateTravelTime(distanceMeters: number): number {
  if (!distanceMeters || distanceMeters <= 0) {
    return 0;
  }

  return Math.round(distanceMeters / DEFAULT_WALKING_SPEED_METERS_PER_SECOND);
}

/**
 * RouteSelector Component
 * Modal for selecting source and destination
 * Calculates safest and fastest routes
 */
export const RouteSelector: React.FC<RouteSelectorProps> = ({ visible, onClose }) => {
  const { location: userLocation } = useRealLocation();
  const { setCurrentRoute, setActiveRoute, addToHistory } = useAppStore();

  const [sourceInput, setSourceInput] = useState('');
  const [destinationInput, setDestinationInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedRoute, setSelectedRoute] = useState<'safest' | 'fastest' | null>(null);

  // Pre-fill source with current location when available
  useEffect(() => {
    if (userLocation && !sourceInput) {
      setSourceInput(`${userLocation.lat.toFixed(4)}, ${userLocation.lng.toFixed(4)}`);
      logger.info('[RouteSelector] Pre-filled source with current location');
    }
  }, [userLocation]);

  const parseCoordinates = (input: string): RouteCoordinates | null => {
    const trimmed = input.trim();
    const parts = trimmed.split(/[,\s]+/);
    
    if (parts.length >= 2) {
      const lat = parseFloat(parts[0]);
      const lng = parseFloat(parts[1]);
      
      if (!isNaN(lat) && !isNaN(lng) && lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180) {
        return { lat, lng };
      }
    }
    return null;
  };

  const fetchRoute = async (routeType: 'safest' | 'fastest') => {
    const source = parseCoordinates(sourceInput);
    const destination = parseCoordinates(destinationInput);

    if (!source) {
      Alert.alert('Invalid Source', 'Please enter valid source coordinates (lat, lng)');
      return;
    }

    if (!destination) {
      Alert.alert('Invalid Destination', 'Please enter valid destination coordinates (lat, lng)');
      return;
    }

    if (source.lat === destination.lat && source.lng === destination.lng) {
      Alert.alert('Invalid Route', 'Source and destination cannot be the same');
      return;
    }

    setLoading(true);
    setSelectedRoute(routeType);

    try {
      const endpoint = `${ROUTES_API_URL}/${routeType}`;
      const payload = {
        start: source,
        end: destination,
        user_id: 'user-123',
      };

      logger.info(`[RouteSelector] Requesting ${routeType} route`, {
        source,
        destination,
      });

      const response = await axios.post<RouteResponse>(endpoint, payload, {
        timeout: 15000,
      });
      const data = response.data;

      if (!Array.isArray(data.route) || data.route.length === 0) {
        throw new Error('Route response did not include any coordinates');
      }

      const distanceMeters =
        typeof data.distance_meters === 'number'
          ? data.distance_meters
          : typeof data.distance_km === 'number'
            ? data.distance_km * 1000
            : 0;
      const estimatedTime = typeof data.estimated_time === 'number'
        ? data.estimated_time
        : estimateTravelTime(distanceMeters);
      const safetyScore = typeof data.safety_score === 'number' ? data.safety_score : 0;

      logger.info(`[RouteSelector] ${routeType} route received`, {
        distance: distanceMeters,
        time: estimatedTime,
        pointCount: data.route.length,
        safetyScore,
      });

      const routeCoordinates = data.route.map((coord) => ({
        latitude: coord.lat,
        longitude: coord.lng,
      }));

      const routeData = {
        type: routeType,
        coordinates: routeCoordinates,
        distance: distanceMeters,
        estimatedTime,
        safetyScore,
      };

      setCurrentRoute(routeData);
      setActiveRoute(routeType);

      // Add to history
      addToHistory({
        id: Date.now().toString(),
        timestamp: Date.now(),
        route: routeData,
        startLocation: source,
        endLocation: destination,
      });

      const timeStr = (estimatedTime / 60).toFixed(1);
      const distStr = (distanceMeters / 1000).toFixed(1);
      Alert.alert(
        'Route Found',
        `${routeType === 'safest' ? '✓ Safest' : '⚡ Fastest'} Route\n\n${distStr} km • ${timeStr} min`,
        [{ text: 'OK', onPress: () => onClose() }]
      );
    } catch (error) {
      logger.error(`[RouteSelector] Error fetching ${routeType} route`, error);
      const errorMessage = axios.isAxiosError(error)
        ? error.response?.data?.detail || error.message
        : error instanceof Error
          ? error.message
          : 'Unknown error';
      Alert.alert(
        'Route Error',
        `Failed to fetch ${routeType} route: ${errorMessage}`
      );
    } finally {
      setLoading(false);
      setSelectedRoute(null);
    }
  };

  const useMyLocation = () => {
    if (userLocation) {
      setSourceInput(`${userLocation.lat.toFixed(4)}, ${userLocation.lng.toFixed(4)}`);
      logger.info('[RouteSelector] Updated source with current location');
    } else {
      Alert.alert('Location Not Available', 'Please enable location and try again');
    }
  };

  const swapInputs = () => {
    const temp = sourceInput;
    setSourceInput(destinationInput);
    setDestinationInput(temp);
    logger.info('[RouteSelector] Swapped source and destination');
  };

  return (
    <Modal visible={visible} animationType="slide" transparent={false}>
      <View style={styles.modalContainer}>
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity onPress={() => {
            onClose();
            logger.info('[RouteSelector] Closed');
          }}>
            <Text style={styles.closeButton}>✕</Text>
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Route Planner</Text>
          <View style={{ width: 40 }} />
        </View>

        {/* Content */}
        <View style={styles.content}>
          {/* Source Input */}
          <View style={styles.inputSection}>
            <Text style={styles.label}>Source</Text>
            <View style={styles.inputWrapper}>
              <TextInput
                style={styles.input}
                placeholder="Enter coordinates or address"
                placeholderTextColor="#999"
                value={sourceInput}
                onChangeText={setSourceInput}
                editable={!loading}
                keyboardType="decimal-pad"
              />
              {sourceInput && !loading && (
                <TouchableOpacity onPress={() => {
                  setSourceInput('');
                  logger.debug('[RouteSelector] Cleared source input');
                }}>
                  <Text style={styles.clearButton}>✕</Text>
                </TouchableOpacity>
              )}
            </View>
            <TouchableOpacity
              style={[styles.myLocationButton, !userLocation && styles.disabled]}
              onPress={useMyLocation}
              disabled={loading || !userLocation}
            >
              <Text style={styles.myLocationButtonText}>📍 Use My Location</Text>
            </TouchableOpacity>
          </View>

          {/* Swap Button */}
          <TouchableOpacity
            style={[styles.swapButton, loading && styles.disabled]}
            onPress={swapInputs}
            disabled={loading}
          >
            <Text style={styles.swapButtonText}>⇅</Text>
          </TouchableOpacity>

          {/* Destination Input */}
          <View style={styles.inputSection}>
            <Text style={styles.label}>Destination</Text>
            <View style={styles.inputWrapper}>
              <TextInput
                style={styles.input}
                placeholder="Enter coordinates or address"
                placeholderTextColor="#999"
                value={destinationInput}
                onChangeText={setDestinationInput}
                editable={!loading}
                keyboardType="decimal-pad"
              />
              {destinationInput && !loading && (
                <TouchableOpacity onPress={() => {
                  setDestinationInput('');
                  logger.debug('[RouteSelector] Cleared destination input');
                }}>
                  <Text style={styles.clearButton}>✕</Text>
                </TouchableOpacity>
              )}
            </View>
            <Text style={styles.hint}>Format: latitude, longitude</Text>
            <Text style={styles.hint}>Example: 17.3850, 78.4867</Text>
          </View>

          {/* Route Type Buttons */}
          <View style={styles.buttonSection}>
            <TouchableOpacity
              style={[
                styles.routeButton,
                styles.safestButton,
                loading && styles.disabled,
                selectedRoute === 'safest' && styles.activeRoute,
              ]}
              onPress={() => fetchRoute('safest')}
              disabled={loading}
            >
              {selectedRoute === 'safest' && loading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <>
                  <Text style={styles.routeButtonEmoji}>✓</Text>
                  <Text style={styles.routeButtonText}>Safest Route</Text>
                </>
              )}
            </TouchableOpacity>

            <TouchableOpacity
              style={[
                styles.routeButton,
                styles.fastestButton,
                loading && styles.disabled,
                selectedRoute === 'fastest' && styles.activeRoute,
              ]}
              onPress={() => fetchRoute('fastest')}
              disabled={loading}
            >
              {selectedRoute === 'fastest' && loading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <>
                  <Text style={styles.routeButtonEmoji}>⚡</Text>
                  <Text style={styles.routeButtonText}>Fastest Route</Text>
                </>
              )}
            </TouchableOpacity>
          </View>

          {/* Loading Indicator */}
          {loading && (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#2196F3" />
              <Text style={styles.loadingText}>Calculating route...</Text>
            </View>
          )}
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  modalContainer: {
    flex: 1,
    backgroundColor: '#fff',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    paddingTop: 50,
    backgroundColor: '#f5f5f5',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  closeButton: {
    fontSize: 24,
    color: '#666',
    fontWeight: '300',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
  },
  content: {
    flex: 1,
    padding: 16,
  },
  inputSection: {
    marginBottom: 16,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f5f5f5',
    borderRadius: 8,
    paddingHorizontal: 12,
    borderWidth: 1,
    borderColor: '#e0e0e0',
    marginBottom: 8,
  },
  input: {
    flex: 1,
    paddingVertical: 12,
    fontSize: 14,
    color: '#333',
  },
  clearButton: {
    fontSize: 18,
    color: '#999',
    marginLeft: 8,
  },
  myLocationButton: {
    backgroundColor: '#f5f5f5',
    borderRadius: 6,
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderWidth: 1,
    borderColor: '#2196F3',
  },
  disabled: {
    opacity: 0.5,
  },
  myLocationButtonText: {
    color: '#2196F3',
    fontSize: 12,
    fontWeight: '600',
    textAlign: 'center',
  },
  swapButton: {
    alignSelf: 'center',
    backgroundColor: '#f5f5f5',
    borderRadius: 50,
    width: 44,
    height: 44,
    justifyContent: 'center',
    alignItems: 'center',
    marginVertical: 12,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  swapButtonText: {
    fontSize: 20,
    color: '#666',
  },
  hint: {
    fontSize: 12,
    color: '#999',
    marginTop: 4,
  },
  buttonSection: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 24,
    marginBottom: 24,
  },
  routeButton: {
    flex: 1,
    flexDirection: 'row',
    paddingVertical: 14,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 8,
  },
  activeRoute: {
    opacity: 0.8,
  },
  safestButton: {
    backgroundColor: '#4CAF50',
  },
  fastestButton: {
    backgroundColor: '#FF9800',
  },
  routeButtonEmoji: {
    fontSize: 18,
  },
  routeButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  loadingContainer: {
    alignItems: 'center',
    marginVertical: 20,
  },
  loadingText: {
    marginTop: 12,
    color: '#666',
    fontSize: 14,
  },
});
