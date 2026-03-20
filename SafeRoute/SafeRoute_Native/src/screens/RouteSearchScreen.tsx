import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, TextInput, StyleSheet, TouchableOpacity, FlatList, Keyboard } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import api from '../config/api';
import { useAppStore } from '../store/useAppStore';

const RECENT_KEY = '@recent_searches';

export const RouteSearchScreen: React.FC = () => {
    const navigation = useNavigation();
    const setCurrentRoute = useAppStore((s) => s.setCurrentRoute);

    const [start, setStart] = useState('');
    const [dest, setDest] = useState('');
    const [recent, setRecent] = useState<string[]>([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        (async () => {
            const raw = await AsyncStorage.getItem(RECENT_KEY);
            if (raw) setRecent(JSON.parse(raw));
        })();
    }, []);

    const saveRecent = useCallback(async (entry: string) => {
        try {
            const next = [entry, ...recent.filter((r) => r !== entry)].slice(0, 10);
            setRecent(next);
            await AsyncStorage.setItem(RECENT_KEY, JSON.stringify(next));
        } catch (e) {
            // ignore
        }
    }, [recent]);

    const parseCoord = (text: string) => {
        const parts = text.split(',').map((p) => p.trim());
        if (parts.length !== 2) return null;
        const lat = Number(parts[0]);
        const lng = Number(parts[1]);
        if (isNaN(lat) || isNaN(lng)) return null;
        return { lat, lng };
    };

    const onCalculate = useCallback(async () => {
        Keyboard.dismiss();
        const s = parseCoord(start);
        const e = parseCoord(dest);
        if (!s || !e) return alert('Enter coordinates as: lat, lng');

        setLoading(true);
        try {
            const res = await fetch(`${api.BASE_URL}/safest_route`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ start: { lat: s.lat, lng: s.lng }, end: { lat: e.lat, lng: e.lng } }),
            });
            if (!res.ok) {
                const errText = await res.text();
                throw new Error(`Server error ${res.status}: ${errText}`);
            }
            const data = await res.json();

            // Backend returns safest_route as array of [lat, lng] tuples or {lat, lng} objects
            const rawRoute: any[] = data.safest_route || data.route || [];
            const coords = rawRoute.map((p: any) => {
                if (Array.isArray(p)) return { latitude: p[0], longitude: p[1] };
                return { latitude: p.lat ?? p.latitude, longitude: p.lng ?? p.longitude };
            });

            setCurrentRoute({
                type: 'safest',
                coordinates: coords,
                distance: data.distance_km ?? data.distance_meters ?? 0,
                estimatedTime: data.estimated_time_min ?? 0,
                safetyScore: data.avg_safety_score ?? data.safety_score ?? 0,
            });

            saveRecent(`${s.lat}, ${s.lng} → ${e.lat}, ${e.lng}`);
            navigation.goBack();
        } catch (err: any) {
            console.warn('route calc error', err);
            alert(`Failed to calculate route.\n${err?.message || 'Check your coordinates and network.'}`);
        } finally {
            setLoading(false);
        }
    }, [start, dest, navigation, saveRecent, setCurrentRoute]);

    const onSwap = () => {
        setStart(dest);
        setDest(start);
    };

    return (
        <View style={styles.container}>
            <View style={styles.header}>
                <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
                    <Text style={styles.backText}>← Back</Text>
                </TouchableOpacity>
                <Text style={styles.title}>Plan Route</Text>
            </View>

            <View style={styles.form}>
                <Text style={styles.label}>Start (lat, lng)</Text>
                <TextInput value={start} onChangeText={setStart} placeholder="17.4435, 78.3484" style={styles.input} keyboardType="default" />

                <Text style={[styles.label, { marginTop: 12 }]}>Destination (lat, lng)</Text>
                <TextInput value={dest} onChangeText={setDest} placeholder="17.4500, 78.3500" style={styles.input} keyboardType="default" />

                <View style={styles.row}>
                    <TouchableOpacity style={styles.swapBtn} onPress={onSwap}><Text style={styles.swapTxt}>Swap</Text></TouchableOpacity>
                    <TouchableOpacity style={styles.calcBtn} onPress={onCalculate} disabled={loading}><Text style={styles.calcTxt}>{loading ? 'Calculating…' : 'Calculate'}</Text></TouchableOpacity>
                </View>
            </View>

            <View style={styles.recentWrap}>
                <Text style={styles.sectionTitle}>Recent</Text>
                <FlatList data={recent} keyExtractor={(i) => i} renderItem={({ item }) => (
                    <TouchableOpacity style={styles.recentItem} onPress={() => { setStart(item.split('→')[0].trim()); setDest(item.split('→')[1]?.trim() || ''); }}>
                        <Text style={styles.recentText}>{item}</Text>
                    </TouchableOpacity>
                )} />
            </View>
        </View>
    );
};

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: '#fff', padding: 16 },
    header: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
    backBtn: { padding: 8 },
    backText: { color: '#4CAF50' },
    title: { flex: 1, textAlign: 'center', fontWeight: '700' },
    form: { marginTop: 8 },
    label: { fontSize: 13, color: '#333', marginBottom: 6 },
    input: { borderWidth: 1, borderColor: '#e5e5e5', padding: 10, borderRadius: 8, backgroundColor: '#fff' },
    row: { flexDirection: 'row', marginTop: 12, justifyContent: 'space-between' },
    swapBtn: { padding: 12, borderRadius: 8, backgroundColor: '#f0f0f0' },
    swapTxt: { color: '#333' },
    calcBtn: { padding: 12, borderRadius: 8, backgroundColor: '#4CAF50' },
    calcTxt: { color: '#fff', fontWeight: '600' },
    recentWrap: { marginTop: 20 },
    sectionTitle: { fontWeight: '700', marginBottom: 8 },
    recentItem: { padding: 10, borderRadius: 8, backgroundColor: '#fafafa', marginBottom: 8 },
    recentText: { color: '#333' },
});

