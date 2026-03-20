import Constants from 'expo-constants';

// Attempt to derive the local dev host when running in Expo
const debugHost = (() => {
  // Expo provides manifest with debuggerHost like '192.168.1.5:19000'
  const manifest: any = (Constants as any).manifest || (Constants as any).expoConfig;
  const debuggerHost = manifest?.debuggerHost as string | undefined;
  if (debuggerHost && debuggerHost.includes(':')) {
    return debuggerHost.split(':')[0];
  }
  return undefined;
})();

const DEFAULT_LOCAL_IP = '192.168.1.100'; // Replace with your machine IP if needed

export const BASE_HOST = __DEV__ ? debugHost || DEFAULT_LOCAL_IP : 'api.saferoute.example.com';
export const BASE_URL = __DEV__ ? `http://${BASE_HOST}:8000` : `https://${BASE_HOST}`;
export const WS_URL = BASE_URL.replace(/^http/, 'ws') + '/ws/sos';

export default {
  BASE_URL,
  WS_URL,
};
