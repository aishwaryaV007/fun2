import { NativeModules, Platform } from 'react-native';

const DEFAULT_BACKEND_PORT = '8000';

function extractHostFromScriptURL(scriptURL: string | undefined): string | null {
    if (!scriptURL) {
        return null;
    }

    const withoutScheme = scriptURL.replace(/^[a-z]+:\/\//i, '');
    const hostPort = withoutScheme.split('/')[0];
    const host = hostPort.split(':')[0];

    if (!host) {
        return null;
    }

    if (Platform.OS === 'android' && (host === 'localhost' || host === '127.0.0.1')) {
        return '10.0.2.2';
    }

    return host;
}

function normalizeBaseUrl(url: string): string {
    return url.replace(/\/+$/, '');
}

function resolveBackendBaseUrl(): string {
    const envUrl = process.env.EXPO_PUBLIC_BACKEND_URL?.trim();
    if (envUrl) {
        return normalizeBaseUrl(envUrl);
    }

    const metroHost = extractHostFromScriptURL(NativeModules.SourceCode?.scriptURL);
    if (metroHost) {
        return `http://${metroHost}:${DEFAULT_BACKEND_PORT}`;
    }

    const fallbackHost = Platform.OS === 'android' ? '10.0.2.2' : '127.0.0.1';
    return `http://${fallbackHost}:${DEFAULT_BACKEND_PORT}`;
}

export const API_BASE_URL = resolveBackendBaseUrl();
export const ROUTES_API_URL = `${API_BASE_URL}/routes`;
export const SOS_TRIGGER_URL = `${API_BASE_URL}/sos/trigger`;
export const HEARTBEAT_WS_URL = `${API_BASE_URL.replace(/^http/, 'ws')}/ws/users`;
