import AsyncStorage from '@react-native-async-storage/async-storage';

const CLIENT_ID_KEY = '@saferoute_client_id';

function generateClientId(): string {
    const timestamp = Date.now().toString(36);
    const randomChunk = Math.random().toString(36).slice(2, 10);
    return `sr-mobile-${timestamp}-${randomChunk}`;
}

export async function getOrCreateClientId(): Promise<string> {
    const existingId = await AsyncStorage.getItem(CLIENT_ID_KEY);
    if (existingId) {
        return existingId;
    }

    const nextId = generateClientId();
    await AsyncStorage.setItem(CLIENT_ID_KEY, nextId);
    return nextId;
}
