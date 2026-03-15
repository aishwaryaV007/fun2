import React, { useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';
import {
  Circle,
  GoogleMap,
  HeatmapLayer,
  InfoWindow,
  Marker,
  useJsApiLoader,
} from '@react-google-maps/api';
import type { Libraries } from '@react-google-maps/api';
import type { ActiveUser, SOSAlert } from '../App';
import {
  DANGER_ZONES_API_URL,
  GOOGLE_MAPS_API_KEY,
  HEATMAP_API_URL,
} from '../config/backend';

const MAP_LIBRARIES: Libraries = ['visualization'];
const GACHIBOWLI_CENTER = {
  lat: 17.4435,
  lng: 78.3484,
};
const SAFETY_LAYER_REFRESH_INTERVAL_MS = 60000;

interface MapViewProps {
  lambda: number;
  alerts: SOSAlert[];
  activeUserLocations: Map<string, ActiveUser>;
}

interface HeatmapPoint {
  lat: number;
  lng: number;
  weight: number;
}

interface HeatmapResponse {
  heatmap?: Array<{
    latitude?: number;
    longitude?: number;
    lat?: number;
    lng?: number;
    weight?: number;
  }>;
  segments?: Array<{
    start?: { lat?: number; lng?: number };
    end?: { lat?: number; lng?: number };
    safety_score?: number;
  }>;
}

interface DangerZoneResponse {
  danger_zones?: Array<{
    id?: number | string;
    center_lat?: number;
    center_lng?: number;
    lat?: number;
    lng?: number;
    radius?: number;
    radius_degrees?: number;
    risk_score?: number;
  }>;
}

interface DangerZone {
  id: string;
  lat: number;
  lng: number;
  radiusMeters: number;
  fillColor: string;
  opacity: number;
}

function normalizeHeatmap(response: HeatmapResponse): HeatmapPoint[] {
  if (Array.isArray(response.heatmap)) {
    return response.heatmap.flatMap((point) => {
      const lat = typeof point.latitude === 'number' ? point.latitude : point.lat;
      const lng = typeof point.longitude === 'number' ? point.longitude : point.lng;

      if (typeof lat !== 'number' || typeof lng !== 'number') {
        return [];
      }

      return [
        {
          lat,
          lng,
          weight: typeof point.weight === 'number' ? point.weight : 1,
        },
      ];
    });
  }

  if (Array.isArray(response.segments)) {
    return response.segments.flatMap((segment) => {
      const startLat = segment.start?.lat;
      const startLng = segment.start?.lng;
      const endLat = segment.end?.lat;
      const endLng = segment.end?.lng;

      if (
        typeof startLat !== 'number' ||
        typeof startLng !== 'number' ||
        typeof endLat !== 'number' ||
        typeof endLng !== 'number'
      ) {
        return [];
      }

      return [
        {
          lat: (startLat + endLat) / 2,
          lng: (startLng + endLng) / 2,
          weight: Math.max(1, 100 - (segment.safety_score ?? 50)),
        },
      ];
    });
  }

  return [];
}

function degreesToMeters(degrees: number): number {
  return Math.max(degrees * 111320, 100);
}

function normalizeDangerZones(response: DangerZoneResponse): DangerZone[] {
  if (!Array.isArray(response.danger_zones)) {
    return [];
  }

  return response.danger_zones.flatMap((zone, index) => {
    const lat = typeof zone.center_lat === 'number' ? zone.center_lat : zone.lat;
    const lng = typeof zone.center_lng === 'number' ? zone.center_lng : zone.lng;

    if (typeof lat !== 'number' || typeof lng !== 'number') {
      return [];
    }

    const riskScore = typeof zone.risk_score === 'number' ? zone.risk_score : 0.5;
    const rawRadius =
      typeof zone.radius === 'number'
        ? zone.radius
        : typeof zone.radius_degrees === 'number'
          ? zone.radius_degrees
          : 0.002;

    return [
      {
        id: String(zone.id ?? `${lat}:${lng}:${index}`),
        lat,
        lng,
        radiusMeters: rawRadius > 10 ? rawRadius : degreesToMeters(rawRadius),
        fillColor: riskScore >= 0.75 ? '#ef4444' : riskScore >= 0.5 ? '#f97316' : '#f59e0b',
        opacity: riskScore >= 0.75 ? 0.32 : 0.24,
      },
    ];
  });
}

const GoogleMapView: React.FC<MapViewProps> = ({ lambda, alerts, activeUserLocations }) => {
  const mapRef = useRef<google.maps.Map | null>(null);
  const [selectedAlert, setSelectedAlert] = useState<SOSAlert | null>(null);
  const [selectedUser, setSelectedUser] = useState<string | null>(null);
  const [heatmapPoints, setHeatmapPoints] = useState<HeatmapPoint[]>([]);
  const [dangerZones, setDangerZones] = useState<DangerZone[]>([]);
  const { isLoaded, loadError } = useJsApiLoader({
    googleMapsApiKey: GOOGLE_MAPS_API_KEY,
    libraries: MAP_LIBRARIES,
  });

  const mapOptions = useMemo<google.maps.MapOptions | undefined>(() => {
    if (!isLoaded) {
      return undefined;
    }

    return {
      zoom: 14,
      center: GACHIBOWLI_CENTER,
      mapTypeId: 'roadmap',
      styles: [
        { featureType: 'all', elementType: 'labels.text.fill', stylers: [{ color: '#ffffff' }] },
        {
          featureType: 'all',
          elementType: 'labels.text.stroke',
          stylers: [{ color: '#000000' }, { lightness: 13 }],
        },
        { featureType: 'administrative', elementType: 'geometry.fill', stylers: [{ color: '#000000' }] },
        {
          featureType: 'administrative',
          elementType: 'geometry.stroke',
          stylers: [{ color: '#144cba' }, { lightness: 14 }, { weight: 1.6 }],
        },
        { featureType: 'landscape', elementType: 'all', stylers: [{ color: '#08304b' }] },
        {
          featureType: 'poi',
          elementType: 'geometry',
          stylers: [{ color: '#0c4152' }, { lightness: 5 }],
        },
        { featureType: 'road.highway', elementType: 'geometry.fill', stylers: [{ color: '#000000' }] },
        {
          featureType: 'road.highway',
          elementType: 'geometry.stroke',
          stylers: [{ color: '#0b3d51' }, { lightness: 25 }],
        },
        { featureType: 'road.arterial', elementType: 'geometry.fill', stylers: [{ color: '#000000' }] },
        {
          featureType: 'road.arterial',
          elementType: 'geometry.stroke',
          stylers: [{ color: '#0b3d51' }, { lightness: 16 }],
        },
        { featureType: 'road.local', elementType: 'geometry', stylers: [{ color: '#000000' }] },
        { featureType: 'transit', elementType: 'all', stylers: [{ color: '#146474' }] },
        { featureType: 'water', elementType: 'all', stylers: [{ color: '#021019' }] },
      ],
      disableDefaultUI: true,
      zoomControl: true,
      zoomControlOptions: {
        position: google.maps.ControlPosition.RIGHT_CENTER,
      },
    };
  }, [isLoaded]);

  const heatmapData = useMemo<google.maps.visualization.WeightedLocation[]>(() => {
    if (!isLoaded) {
      return [];
    }

    return heatmapPoints.map((point) => ({
      location: new google.maps.LatLng(point.lat, point.lng),
      weight: point.weight,
    }));
  }, [heatmapPoints, isLoaded]);

  const activeUserMarkerIcon = useMemo<google.maps.Symbol | undefined>(() => {
    if (!isLoaded) {
      return undefined;
    }

    return {
      path: google.maps.SymbolPath.CIRCLE,
      scale: 8,
      fillColor: '#2563eb',
      fillOpacity: 1,
      strokeColor: '#ffffff',
      strokeWeight: 2,
    };
  }, [isLoaded]);

  const sosMarkerIcon = useMemo<google.maps.Symbol | undefined>(() => {
    if (!isLoaded) {
      return undefined;
    }

    return {
      path: 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm3.5-9c.83 0 1.5-.67 1.5-1.5S16.33 8 15.5 8 14 8.67 14 9.5s.67 1.5 1.5 1.5zm-7 0c.83 0 1.5-.67 1.5-1.5S9.33 8 8.5 8 7 8.67 7 9.5 7.67 11 8.5 11zm3.5 6.5c2.33 0 4.31-1.46 5.11-3.5H6.89c.8 2.04 2.78 3.5 5.11 3.5z',
      scale: 1.5,
      fillColor: '#ef4444',
      fillOpacity: 1,
      strokeColor: '#fff',
      strokeWeight: 2,
      anchor: new google.maps.Point(12, 12),
    };
  }, [isLoaded]);

  const fetchSafetyLayers = async () => {
    try {
      const [heatmapResponse, dangerZonesResponse] = await Promise.all([
        axios.get<HeatmapResponse>(HEATMAP_API_URL),
        axios.get<DangerZoneResponse>(DANGER_ZONES_API_URL),
      ]);

      setHeatmapPoints(normalizeHeatmap(heatmapResponse.data));
      setDangerZones(normalizeDangerZones(dangerZonesResponse.data));
    } catch (error) {
      console.error('[Map] Failed to fetch safety layers', error);
    }
  };

  useEffect(() => {
    void fetchSafetyLayers();

    const intervalId = setInterval(() => {
      void fetchSafetyLayers();
    }, SAFETY_LAYER_REFRESH_INTERVAL_MS);

    return () => clearInterval(intervalId);
  }, []);

  useEffect(() => {
    if (alerts.length > 0 && mapRef.current) {
      const latest = alerts[0];
      mapRef.current.panTo({
        lat: latest.location.lat,
        lng: latest.location.lng,
      });
      mapRef.current.setZoom(15);
    }
  }, [alerts]);

  useEffect(() => {
    if (mapRef.current) {
      const offset = (lambda / 500000) * 0.01;
      mapRef.current.panTo({
        lat: GACHIBOWLI_CENTER.lat + offset,
        lng: GACHIBOWLI_CENTER.lng,
      });
    }
  }, [lambda]);

  if (loadError) {
    return (
      <div className="flex h-full items-center justify-center bg-zinc-950 text-sm text-red-300">
        Failed to load Google Maps.
      </div>
    );
  }

  if (!isLoaded || !mapOptions || !activeUserMarkerIcon || !sosMarkerIcon) {
    return (
      <div className="flex h-full items-center justify-center bg-zinc-950 text-sm text-zinc-400">
        Loading map…
      </div>
    );
  }

  return (
    <GoogleMap
      mapContainerStyle={{
        height: '100%',
        width: '100%',
      }}
      options={mapOptions}
      onLoad={(map) => {
        mapRef.current = map;
        console.log('[GoogleMap] Map loaded');
      }}
      center={GACHIBOWLI_CENTER}
      zoom={14}
    >
      {heatmapData.length > 0 && (
        <HeatmapLayer
          data={heatmapData}
          options={{
            radius: 30,
            opacity: 0.6,
            gradient: ['#0000ff', '#00ff00', '#ffff00', '#ff7f00', '#ff0000'],
          }}
        />
      )}

      {dangerZones.map((zone) => (
        <Circle
          key={zone.id}
          center={{ lat: zone.lat, lng: zone.lng }}
          radius={zone.radiusMeters}
          options={{
            fillColor: zone.fillColor,
            fillOpacity: zone.opacity,
            strokeColor: zone.fillColor,
            strokeOpacity: 0.6,
            strokeWeight: 2,
          }}
        />
      ))}

      {Array.from(activeUserLocations.values()).map((user) => (
        <Marker
          key={`user-${user.userId}`}
          position={{ lat: user.location.lat, lng: user.location.lng }}
          icon={activeUserMarkerIcon}
          title={`Active User: ${user.userId}`}
          onClick={() => setSelectedUser(user.userId)}
        />
      ))}

      {selectedUser && activeUserLocations.has(selectedUser) && (() => {
        const user = activeUserLocations.get(selectedUser)!;
        return (
          <InfoWindow
            position={{ lat: user.location.lat, lng: user.location.lng }}
            onCloseClick={() => setSelectedUser(null)}
          >
            <div className="w-max max-w-xs rounded bg-white p-2 text-xs text-gray-900">
              <div className="mb-1 flex items-center space-x-1">
                <span className="h-1.5 w-1.5 rounded-full bg-blue-500"></span>
                <span className="font-semibold">Active User</span>
              </div>
              <div className="text-gray-700">
                <p><strong>User ID:</strong> {user.userId}</p>
                <p><strong>Latitude:</strong> {user.location.lat.toFixed(4)}</p>
                <p><strong>Longitude:</strong> {user.location.lng.toFixed(4)}</p>
                <p className="mt-1 text-xs text-gray-500">
                  Last seen: {new Date(user.lastSeen).toLocaleTimeString()}
                </p>
              </div>
            </div>
          </InfoWindow>
        );
      })()}

      {alerts.map((alert) => (
        <div key={`sos-${alert.userId}-${alert.timestamp}`}>
          <Circle
            center={{ lat: alert.location.lat, lng: alert.location.lng }}
            radius={200}
            options={{
              fillColor: '#ef4444',
              fillOpacity: 0.25,
              strokeColor: '#ef4444',
              strokeOpacity: 0.6,
              strokeWeight: 2,
            }}
          />

          <Marker
            position={{ lat: alert.location.lat, lng: alert.location.lng }}
            icon={sosMarkerIcon}
            title={`SOS Alert - ${alert.userId}`}
            onClick={() => setSelectedAlert(alert)}
          />
        </div>
      ))}

      {selectedAlert && (
        <InfoWindow
          position={{ lat: selectedAlert.location.lat, lng: selectedAlert.location.lng }}
          onCloseClick={() => setSelectedAlert(null)}
        >
          <div className="w-max max-w-xs rounded bg-white p-2 text-xs text-gray-900">
            <div className="mb-1 flex items-center space-x-1">
              <span className="h-1.5 w-1.5 animate-ping rounded-full bg-red-600"></span>
              <h3 className="text-xs font-bold text-red-600">SOS ALERT</h3>
            </div>
            <p className="mb-1 text-[10px] font-bold">User: {selectedAlert.userId}</p>
            <p className="text-[10px] text-gray-600">
              {selectedAlert.location.lat.toFixed(5)}, {selectedAlert.location.lng.toFixed(5)}
            </p>
            <p className="mt-1 text-[10px] text-gray-500">
              {new Date(selectedAlert.timestamp).toLocaleString()}
            </p>
          </div>
        </InfoWindow>
      )}
    </GoogleMap>
  );
};

export default GoogleMapView;
