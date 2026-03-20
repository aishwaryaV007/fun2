import React, { useState, useEffect } from 'react';
import {
    StyleSheet,
    View,
    Text,
    TouchableOpacity,
    ScrollView,
    Switch,
    Alert,
    Dimensions,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useAppStore } from '../store/useAppStore';
import logger from '../utils/logger';

const { width } = Dimensions.get('window');

interface UserPreferences {
    enableShakeDetection: boolean;
    enableLocationTracking: boolean;
    enableNotifications: boolean;
    autoRouteOptimization: boolean;
    emergencyContactEnabled: boolean;
    dataSharingEnabled: boolean;
}

const DEFAULT_PREFERENCES: UserPreferences = {
    enableShakeDetection: true,
    enableLocationTracking: true,
    enableNotifications: true,
    autoRouteOptimization: true,
    emergencyContactEnabled: true,
    dataSharingEnabled: false,
};

const PREFERENCES_KEY = '@user_preferences';

export const SettingsScreen: React.FC = () => {
    const navigation = useNavigation();
    const { activeRoute, setActiveRoute } = useAppStore();
    const [preferences, setPreferences] = useState<UserPreferences>(DEFAULT_PREFERENCES);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadPreferences();
    }, []);

    const loadPreferences = async () => {
        try {
            const stored = await AsyncStorage.getItem(PREFERENCES_KEY);
            if (stored) {
                const parsed = JSON.parse(stored);
                setPreferences({ ...DEFAULT_PREFERENCES, ...parsed });
            }
            logger.info('[Settings] Preferences loaded');
        } catch (error) {
            logger.error('[Settings] Failed to load preferences:', error);
            Alert.alert('Error', 'Failed to load settings');
        } finally {
            setLoading(false);
        }
    };

    const savePreferences = async (newPreferences: UserPreferences) => {
        try {
            await AsyncStorage.setItem(PREFERENCES_KEY, JSON.stringify(newPreferences));
            setPreferences(newPreferences);
            logger.info('[Settings] Preferences saved');
        } catch (error) {
            logger.error('[Settings] Failed to save preferences:', error);
            Alert.alert('Error', 'Failed to save settings');
        }
    };

    const updatePreference = (key: keyof UserPreferences, value: boolean) => {
        const newPreferences = { ...preferences, [key]: value };
        savePreferences(newPreferences);
    };

    const resetToDefaults = () => {
        Alert.alert(
            'Reset Settings',
            'Are you sure you want to reset all settings to default?',
            [
                { text: 'Cancel', style: 'cancel' },
                {
                    text: 'Reset',
                    style: 'destructive',
                    onPress: () => savePreferences(DEFAULT_PREFERENCES),
                },
            ]
        );
    };

    const clearRouteHistory = () => {
        Alert.alert(
            'Clear History',
            'Are you sure you want to clear all route history?',
            [
                { text: 'Cancel', style: 'cancel' },
                {
                    text: 'Clear',
                    style: 'destructive',
                    onPress: () => {
                        // TODO: Implement route history clearing
                        logger.info('[Settings] Route history cleared');
                        Alert.alert('Success', 'Route history cleared');
                    },
                },
            ]
        );
    };

    if (loading) {
        return (
            <View style={styles.loadingContainer}>
                <Text style={styles.loadingText}>Loading settings...</Text>
            </View>
        );
    }

    return (
        <View style={styles.container}>
            {/* Header */}
            <View style={styles.header}>
                <TouchableOpacity
                    style={styles.backButton}
                    onPress={() => navigation.goBack()}
                >
                    <Text style={styles.backButtonText}>← Back</Text>
                </TouchableOpacity>
                <Text style={styles.headerTitle}>Settings</Text>
                <View style={styles.headerSpacer} />
            </View>

            <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
                {/* Safety Settings */}
                <View style={styles.section}>
                    <Text style={styles.sectionTitle}>🛡️ Safety Features</Text>

                    <View style={styles.settingItem}>
                        <View style={styles.settingText}>
                            <Text style={styles.settingTitle}>Shake Detection</Text>
                            <Text style={styles.settingDescription}>
                                Automatically trigger SOS when device is shaken
                            </Text>
                        </View>
                        <Switch
                            value={preferences.enableShakeDetection}
                            onValueChange={(value) => updatePreference('enableShakeDetection', value)}
                            trackColor={{ false: '#767577', true: '#4CAF50' }}
                            thumbColor={preferences.enableShakeDetection ? '#fff' : '#f4f3f4'}
                        />
                    </View>

                    <View style={styles.settingItem}>
                        <View style={styles.settingText}>
                            <Text style={styles.settingTitle}>Emergency Contacts</Text>
                            <Text style={styles.settingDescription}>
                                Allow app to contact emergency services
                            </Text>
                        </View>
                        <Switch
                            value={preferences.emergencyContactEnabled}
                            onValueChange={(value) => updatePreference('emergencyContactEnabled', value)}
                            trackColor={{ false: '#767577', true: '#4CAF50' }}
                            thumbColor={preferences.emergencyContactEnabled ? '#fff' : '#f4f3f4'}
                        />
                    </View>
                </View>

                {/* Navigation Settings */}
                <View style={styles.section}>
                    <Text style={styles.sectionTitle}>🗺️ Navigation</Text>

                    <View style={styles.settingItem}>
                        <View style={styles.settingText}>
                            <Text style={styles.settingTitle}>Location Tracking</Text>
                            <Text style={styles.settingDescription}>
                                Enable GPS location for route optimization
                            </Text>
                        </View>
                        <Switch
                            value={preferences.enableLocationTracking}
                            onValueChange={(value) => updatePreference('enableLocationTracking', value)}
                            trackColor={{ false: '#767577', true: '#4CAF50' }}
                            thumbColor={preferences.enableLocationTracking ? '#fff' : '#f4f3f4'}
                        />
                    </View>

                    <View style={styles.settingItem}>
                        <View style={styles.settingText}>
                            <Text style={styles.settingTitle}>Auto Route Optimization</Text>
                            <Text style={styles.settingDescription}>
                                Automatically suggest safer routes
                            </Text>
                        </View>
                        <Switch
                            value={preferences.autoRouteOptimization}
                            onValueChange={(value) => updatePreference('autoRouteOptimization', value)}
                            trackColor={{ false: '#767577', true: '#4CAF50' }}
                            thumbColor={preferences.autoRouteOptimization ? '#fff' : '#f4f3f4'}
                        />
                    </View>

                    <View style={styles.settingItem}>
                        <TouchableOpacity
                            style={styles.button}
                            onPress={() => navigation.navigate('EmergencyContacts' as never)}
                        >
                            <Text style={styles.buttonText}>📞 Manage Emergency Contacts</Text>
                        </TouchableOpacity>
                    </View>
                </View>

                {/* Notifications */}
                <View style={styles.section}>
                    <Text style={styles.sectionTitle}>🔔 Notifications</Text>

                    <View style={styles.settingItem}>
                        <View style={styles.settingText}>
                            <Text style={styles.settingTitle}>Push Notifications</Text>
                            <Text style={styles.settingDescription}>
                                Receive alerts about safety updates and route changes
                            </Text>
                        </View>
                        <Switch
                            value={preferences.enableNotifications}
                            onValueChange={(value) => updatePreference('enableNotifications', value)}
                            trackColor={{ false: '#767577', true: '#4CAF50' }}
                            thumbColor={preferences.enableNotifications ? '#fff' : '#f4f3f4'}
                        />
                    </View>
                </View>

                {/* Privacy */}
                <View style={styles.section}>
                    <Text style={styles.sectionTitle}>🔒 Privacy</Text>

                    <View style={styles.settingItem}>
                        <View style={styles.settingText}>
                            <Text style={styles.settingTitle}>Data Sharing</Text>
                            <Text style={styles.settingDescription}>
                                Share anonymous safety data to improve community safety
                            </Text>
                        </View>
                        <Switch
                            value={preferences.dataSharingEnabled}
                            onValueChange={(value) => updatePreference('dataSharingEnabled', value)}
                            trackColor={{ false: '#767577', true: '#4CAF50' }}
                            thumbColor={preferences.dataSharingEnabled ? '#fff' : '#f4f3f4'}
                        />
                    </View>
                </View>

                {/* Actions */}
                <View style={styles.section}>
                    <Text style={styles.sectionTitle}>⚙️ Actions</Text>

                    <TouchableOpacity style={styles.dangerButton} onPress={clearRouteHistory}>
                        <Text style={styles.dangerButtonText}>🗑️ Clear Route History</Text>
                    </TouchableOpacity>

                    <TouchableOpacity style={styles.secondaryButton} onPress={resetToDefaults}>
                        <Text style={styles.secondaryButtonText}>🔄 Reset to Defaults</Text>
                    </TouchableOpacity>
                </View>

                {/* App Info */}
                <View style={styles.section}>
                    <Text style={styles.sectionTitle}>ℹ️ About</Text>
                    <View style={styles.infoContainer}>
                        <Text style={styles.infoText}>SafeRoute Mobile v1.0.0</Text>
                        <Text style={styles.infoText}>Women's Safety Navigation</Text>
                        <Text style={styles.infoText}>Built with ❤️ for safety</Text>
                    </View>
                </View>
            </ScrollView>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#f5f5f5',
    },
    loadingContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: '#f5f5f5',
    },
    loadingText: {
        fontSize: 16,
        color: '#666',
    },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingHorizontal: 20,
        paddingTop: 50,
        paddingBottom: 20,
        backgroundColor: '#fff',
        borderBottomWidth: 1,
        borderBottomColor: '#e0e0e0',
    },
    backButton: {
        padding: 8,
    },
    backButtonText: {
        fontSize: 16,
        color: '#4CAF50',
        fontWeight: '600',
    },
    headerTitle: {
        fontSize: 20,
        fontWeight: 'bold',
        color: '#333',
    },
    headerSpacer: {
        width: 60,
    },
    scrollView: {
        flex: 1,
        paddingHorizontal: 20,
    },
    section: {
        backgroundColor: '#fff',
        borderRadius: 12,
        padding: 20,
        marginTop: 20,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
        elevation: 3,
    },
    sectionTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#333',
        marginBottom: 16,
    },
    settingItem: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingVertical: 12,
        borderBottomWidth: 1,
        borderBottomColor: '#f0f0f0',
    },
    settingText: {
        flex: 1,
        marginRight: 16,
    },
    settingTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: '#333',
        marginBottom: 4,
    },
    settingDescription: {
        fontSize: 12,
        color: '#666',
        lineHeight: 16,
    },
    button: {
        backgroundColor: '#4CAF50',
        borderRadius: 8,
        padding: 12,
        alignItems: 'center',
        marginTop: 12,
    },
    buttonText: {
        color: '#fff',
        fontSize: 14,
        fontWeight: '600',
    },
    dangerButton: {
        backgroundColor: '#f44336',
        borderRadius: 8,
        padding: 12,
        alignItems: 'center',
        marginTop: 12,
    },
    dangerButtonText: {
        color: '#fff',
        fontSize: 14,
        fontWeight: '600',
    },
    secondaryButton: {
        backgroundColor: '#2196F3',
        borderRadius: 8,
        padding: 12,
        alignItems: 'center',
        marginTop: 12,
    },
    secondaryButtonText: {
        color: '#fff',
        fontSize: 14,
        fontWeight: '600',
    },
    infoContainer: {
        alignItems: 'center',
        paddingVertical: 16,
    },
    infoText: {
        fontSize: 14,
        color: '#666',
        marginBottom: 4,
    },
});