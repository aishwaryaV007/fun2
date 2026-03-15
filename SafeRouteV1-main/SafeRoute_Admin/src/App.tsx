import { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import Layout from './components/Layout';
import GoogleMapView from './components/GoogleMapView';
import AnalyticsCards from './components/AnalyticsCards';
import TuningPanel from './components/TuningPanel';
import { AlertCircle, X } from 'lucide-react';
import {
  ACTIVE_USERS_COUNT_API_URL,
  SOS_ALERTS_API_URL,
  SOS_RESOLVE_API_BASE_URL,
  SOS_STREAM_WS_URL,
} from './config/backend';

export interface SOSAlert {
  id: number | null;
  userId: string;
  location: { lat: number; lng: number };
  timestamp: string;
  type: string;
  status: string;
  message: string;
  triggerType: string;
}

export interface ActiveUser {
  userId: string;
  location: { lat: number; lng: number };
  lastSeen: string;
}

interface BackendAlertPayload {
  id?: number | string;
  user_id?: string;
  latitude?: number;
  longitude?: number;
  location?: { lat?: number; lng?: number };
  timestamp?: string;
  type?: string;
  alert_type?: string;
  status?: string;
  message?: string;
  trigger_type?: string;
}

const MAX_WS_RETRIES = 10;
const WS_BACKOFF_DELAYS = [1000, 2000, 4000, 8000, 16000];
const ACTIVE_USERS_POLL_INTERVAL_MS = 15000;

function alertFingerprint(alert: SOSAlert): string {
  return [
    alert.userId,
    alert.timestamp,
    alert.location.lat.toFixed(6),
    alert.location.lng.toFixed(6),
  ].join(':');
}

function normalizeAlert(payload: BackendAlertPayload): SOSAlert | null {
  const userId = typeof payload.user_id === 'string' ? payload.user_id : null;
  const lat =
    typeof payload.location?.lat === 'number'
      ? payload.location.lat
      : typeof payload.latitude === 'number'
        ? payload.latitude
        : null;
  const lng =
    typeof payload.location?.lng === 'number'
      ? payload.location.lng
      : typeof payload.longitude === 'number'
        ? payload.longitude
        : null;

  if (!userId || lat === null || lng === null) {
    return null;
  }

  const parsedId =
    typeof payload.id === 'number'
      ? payload.id
      : typeof payload.id === 'string' && /^\d+$/.test(payload.id)
        ? Number(payload.id)
        : null;

  return {
    id: parsedId,
    userId,
    location: { lat, lng },
    timestamp: typeof payload.timestamp === 'string' ? payload.timestamp : new Date().toISOString(),
    type: typeof payload.alert_type === 'string' ? payload.alert_type : payload.type ?? 'SOS_ALERT',
    status: typeof payload.status === 'string' ? payload.status : 'active',
    message: typeof payload.message === 'string' ? payload.message : 'SOS Alert',
    triggerType: typeof payload.trigger_type === 'string' ? payload.trigger_type : 'button',
  };
}

function mergeAlerts(existing: SOSAlert[], incoming: SOSAlert[]): SOSAlert[] {
  const merged = new Map<string, SOSAlert>();

  for (const alert of [...existing, ...incoming]) {
    const key = alertFingerprint(alert);

    if (alert.status === 'resolved') {
      merged.delete(key);
      continue;
    }

    const current = merged.get(key);
    merged.set(
      key,
      current
        ? {
            ...current,
            ...alert,
            id: alert.id ?? current.id,
          }
        : alert
    );
  }

  return Array.from(merged.values()).sort((a, b) => {
    if (a.id !== null && b.id !== null && a.id !== b.id) {
      return b.id - a.id;
    }

    return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
  });
}

function normalizeActiveUser(data: Record<string, unknown>): ActiveUser | null {
  const userId = typeof data.user_id === 'string' ? data.user_id : null;
  const rawLocation =
    data.location && typeof data.location === 'object'
      ? (data.location as { lat?: number; lng?: number })
      : null;
  const lat =
    typeof rawLocation?.lat === 'number'
      ? rawLocation.lat
      : typeof data.latitude === 'number'
        ? data.latitude
        : null;
  const lng =
    typeof rawLocation?.lng === 'number'
      ? rawLocation.lng
      : typeof data.longitude === 'number'
        ? data.longitude
        : null;

  if (!userId || lat === null || lng === null) {
    return null;
  }

  return {
    userId,
    location: { lat, lng },
    lastSeen: new Date().toISOString(),
  };
}

function App() {
  const [activeTab, setActiveTab] = useState('map');
  const [lambda, setLambda] = useState(2500);
  const [alerts, setAlerts] = useState<SOSAlert[]>([]);
  const [activeUsers, setActiveUsers] = useState(0);
  const [activeUserLocations, setActiveUserLocations] = useState<Map<string, ActiveUser>>(new Map());
  const [resolving, setResolving] = useState<number | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadAlerts = async () => {
    try {
      const response = await axios.get<BackendAlertPayload[]>(SOS_ALERTS_API_URL, {
        params: { limit: 50 },
      });
      const nextAlerts = response.data
        .map(normalizeAlert)
        .filter((alert): alert is SOSAlert => alert !== null && alert.status !== 'resolved');
      setAlerts((prev) => mergeAlerts(prev, nextAlerts));
    } catch (error) {
      console.error('[Alerts] Failed to fetch alerts', error);
    }
  };

  const loadActiveUsers = async () => {
    try {
      const response = await axios.get<{ active_users?: number }>(ACTIVE_USERS_COUNT_API_URL);
      setActiveUsers(response.data.active_users ?? 0);
    } catch (error) {
      console.error('[ActiveUsers] Failed to fetch active user count', error);
    }
  };

  useEffect(() => {
    void loadAlerts();
    void loadActiveUsers();

    const intervalId = setInterval(() => {
      void loadActiveUsers();
    }, ACTIVE_USERS_POLL_INTERVAL_MS);

    return () => clearInterval(intervalId);
  }, []);

  useEffect(() => {
    let isUnmounting = false;

    const scheduleReconnect = () => {
      if (isUnmounting || reconnectCountRef.current >= MAX_WS_RETRIES) {
        return;
      }

      const delayIndex = Math.min(reconnectCountRef.current, WS_BACKOFF_DELAYS.length - 1);
      const delay = WS_BACKOFF_DELAYS[delayIndex];

      reconnectTimeoutRef.current = setTimeout(() => {
        reconnectCountRef.current += 1;
        connectWebSocket();
      }, delay);
    };

    const connectWebSocket = () => {
      if (isUnmounting || reconnectCountRef.current >= MAX_WS_RETRIES) {
        return;
      }

      try {
        const ws = new WebSocket(SOS_STREAM_WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
          reconnectCountRef.current = 0;
          console.log('[WS] Connected to', SOS_STREAM_WS_URL);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data) as Record<string, unknown>;

            if (data.type === 'SOS_ALERT') {
              const liveAlert = normalizeAlert(data);
              if (liveAlert) {
                setAlerts((prev) => mergeAlerts(prev, [liveAlert]));
                void loadAlerts();
              }
              return;
            }

            if (data.type === 'active_users') {
              setActiveUsers(typeof data.count === 'number' ? data.count : 0);
              return;
            }

            if (data.type === 'user_connected' || data.type === 'user_location_update') {
              const user = normalizeActiveUser(data);
              if (user) {
                setActiveUserLocations((prev) => {
                  const updated = new Map(prev);
                  updated.set(user.userId, user);
                  return updated;
                });
              }
              return;
            }

            if (data.type === 'user_disconnected' && typeof data.user_id === 'string') {
              setActiveUserLocations((prev) => {
                const updated = new Map(prev);
                updated.delete(data.user_id as string);
                return updated;
              });
            }
          } catch (error) {
            console.error('[WS] Failed to parse message', error);
          }
        };

        ws.onerror = (error) => {
          console.error('[WS] Error occurred', error);
        };

        ws.onclose = () => {
          if (isUnmounting) {
            return;
          }

          console.warn('[WS] Connection closed. Attempting to reconnect...');
          scheduleReconnect();
        };
      } catch (error) {
        console.error('[WS] Failed to create WebSocket', error);
        scheduleReconnect();
      }
    };

    connectWebSocket();

    return () => {
      isUnmounting = true;

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      if (wsRef.current) {
        if (
          wsRef.current.readyState === WebSocket.OPEN ||
          wsRef.current.readyState === WebSocket.CONNECTING
        ) {
          wsRef.current.close(1000, 'Component unmounting');
        }
        wsRef.current = null;
      }
    };
  }, []);

  const dismissAlert = (alert: SOSAlert) => {
    const key = alertFingerprint(alert);
    setAlerts((prev) => prev.filter((candidate) => alertFingerprint(candidate) !== key));
  };

  const resolveAlert = async (alert: SOSAlert) => {
    if (alert.id === null) {
      void loadAlerts();
      window.alert('This alert is still syncing from the backend. Try again in a moment.');
      return;
    }

    setResolving(alert.id);

    try {
      const response = await axios.post(`${SOS_RESOLVE_API_BASE_URL}/${alert.id}/resolve`, {
        status: 'resolved',
      });
      console.log('[Resolve] Success:', response.data);

      const key = alertFingerprint(alert);
      setAlerts((prev) => prev.filter((candidate) => alertFingerprint(candidate) !== key));
    } catch (error) {
      console.error('[Resolve] Failed:', error);
      const message = axios.isAxiosError(error)
        ? error.response?.data?.detail || error.message
        : error instanceof Error
          ? error.message
          : 'Unknown error';
      window.alert(`Failed to resolve alert: ${message}`);
    } finally {
      setResolving(null);
    }
  };

  return (
    <Layout activeTab={activeTab} setActiveTab={setActiveTab}>
      <div className="relative w-full h-full flex flex-row p-6">
        <div className="absolute top-8 left-1/2 z-50 flex w-full max-w-2xl -translate-x-1/2 flex-col items-center space-y-4 px-4 pointer-events-none">
          {alerts.map((alert) => {
            const alertKey = alertFingerprint(alert);
            return (
              <div
                key={alertKey}
                className="pointer-events-auto flex w-full items-center justify-between rounded-xl border-2 border-red-400 bg-red-600 p-4 text-white shadow-2xl animate-pulse"
              >
                <div className="flex items-center space-x-4">
                  <AlertCircle className="h-8 w-8 text-red-200" />
                  <div>
                    <h3 className="text-lg font-bold uppercase tracking-wider">Critical SOS Alert</h3>
                    <p className="text-sm text-red-100">
                      User: <span className="font-mono font-bold text-white">{alert.userId}</span> ·
                      Location:{' '}
                      <span className="font-mono">
                        {alert.location.lat.toFixed(4)}, {alert.location.lng.toFixed(4)}
                      </span>
                    </p>
                    <p className="mt-1 text-xs text-red-200">
                      Time: {new Date(alert.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => resolveAlert(alert)}
                    disabled={alert.id === null || resolving === alert.id}
                    className="rounded-lg bg-green-600 px-4 py-2 font-medium text-white transition-colors hover:bg-green-700 disabled:bg-green-800"
                    title="Resolve Alert"
                  >
                    {resolving === alert.id ? 'Resolving...' : 'Resolve'}
                  </button>
                  <button
                    onClick={() => dismissAlert(alert)}
                    className="rounded-full p-2 transition-colors hover:bg-red-700"
                    title="Dismiss Alert"
                  >
                    <X className="h-6 w-6" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {(activeTab === 'map' || activeTab === 'tuning') && (
          <div className="group relative flex-1 overflow-hidden rounded-3xl border border-zinc-800 bg-zinc-900 shadow-2xl">
            <GoogleMapView
              lambda={lambda}
              alerts={alerts}
              activeUserLocations={activeUserLocations}
            />

            <div className="pointer-events-none absolute left-0 top-0 z-10 w-full p-4">
              <div className="pointer-events-auto">
                <AnalyticsCards activeUsers={activeUsers} sosAlertCount={alerts.length} />
              </div>
            </div>
          </div>
        )}

        {activeTab === 'tuning' && (
          <div className="ml-6 translate-x-0 transform overflow-hidden rounded-3xl opacity-100 transition-all duration-500">
            <TuningPanel lambda={lambda} setLambda={setLambda} />
          </div>
        )}

        {activeTab === 'reports' && (
          <div className="flex-1 rounded-3xl border border-zinc-800 bg-zinc-900/50 p-8 backdrop-blur-md">
            <h2 className="mb-6 text-3xl font-bold text-white">Incident Reports Database</h2>

            <div className="flex h-full flex-col items-center justify-start overflow-y-auto text-zinc-500">
              {alerts.length > 0 ? (
                <div className="mt-4 w-full max-w-4xl space-y-4">
                  {alerts.map((alert) => {
                    const alertKey = alertFingerprint(alert);
                    return (
                      <div
                        key={alertKey}
                        className="flex items-center justify-between rounded-xl border border-red-500/50 bg-red-900/20 p-6 text-left shadow-lg"
                      >
                        <div>
                          <div className="mb-2 flex items-center space-x-2 font-bold text-red-400">
                            <AlertCircle className="h-5 w-5" />
                            <span>SOS ALERT TRIGGERED</span>
                          </div>
                          <p className="font-medium text-white">
                            User ID: <span className="font-mono text-zinc-400">{alert.userId}</span>
                          </p>
                          <p className="text-zinc-300">
                            Coordinates:{' '}
                            <span className="font-mono">
                              {alert.location.lat}, {alert.location.lng}
                            </span>
                          </p>
                          <p className="mt-2 text-sm text-zinc-500">
                            {new Date(alert.timestamp).toLocaleString()}
                          </p>
                        </div>
                        <button
                          onClick={() => resolveAlert(alert)}
                          disabled={alert.id === null || resolving === alert.id}
                          className="rounded-lg border border-green-500 bg-green-600 px-6 py-2 font-medium text-white transition-colors hover:bg-green-700 disabled:bg-green-800"
                        >
                          {resolving === alert.id ? 'Resolving...' : 'Resolve Incident'}
                        </button>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="flex h-full flex-col items-center justify-center">
                  <p>No active incidents.</p>
                  <p className="mt-2 text-sm">Historical tabular report data would render here.</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}

export default App;
