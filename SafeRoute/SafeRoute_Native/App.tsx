import { StatusBar } from 'expo-status-bar';
import React, { useEffect, useState } from 'react';
import { StyleSheet, View, ActivityIndicator, Text } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import MapScreen from './src/components/MapScreen';
import { BottomControls } from './src/components/BottomControls';
import MiniSOSButton from './src/components/MiniSOSButton';
import { SettingsScreen } from './src/screens/SettingsScreen';
import { EmergencyContactsScreen } from './src/screens/EmergencyContactsScreen';
import { RouteSearchScreen } from './src/screens/RouteSearchScreen';
import logger from './src/utils/logger';

const Stack = createNativeStackNavigator();

/**
 * Error Boundary Component
 * Catches and displays errors gracefully
 */
class ErrorBoundary extends React.Component<any, { hasError: boolean; error: string }> {
    constructor(props: any) {
        super(props);
        this.state = { hasError: false, error: '' };
    }

    static getDerivedStateFromError(error: Error) {
        logger.error('App Error Boundary caught error:', error);
        return { hasError: true, error: error.message };
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        logger.error('Error caught in boundary:', { error: error.toString(), ...errorInfo });
    }

    render() {
        if (this.state.hasError) {
            return (
                <View style={styles.errorContainer}>
                    <Text style={styles.errorText}>⚠️ App Error</Text>
                    <Text style={styles.errorMessage}>{this.state.error}</Text>
                    <Text style={styles.errorHint}>Please restart the app</Text>
                </View>
            );
        }

        return this.props.children;
    }
}

/**
 * Main Navigation Stack
 * Provides screens for navigation and settings
 */
function MainStack() {
    return (
        <Stack.Navigator
            screenOptions={{
                headerShown: false,
            }}
        >
            <Stack.Screen name="MapStack" component={MapStackScreen} />
            <Stack.Screen 
                name="RouteSearch" 
                component={RouteSearchScreen}
            />
            <Stack.Screen 
                name="Settings" 
                component={SettingsScreen}
            />
            <Stack.Screen 
                name="EmergencyContacts" 
                component={EmergencyContactsScreen}
            />
        </Stack.Navigator>
    );
}

/**
 * Map Stack - Contains the main map view with controls
 */
function MapStackScreen() {
    const [isInitialized, setIsInitialized] = useState(false);

    useEffect(() => {
        // Initialize app on mount
        const initializeApp = async () => {
            try {
                logger.info('[App] Initializing SafeRoute Mobile...');
                setIsInitialized(true);
                logger.info('[App] SafeRoute Mobile initialized successfully');
            } catch (error) {
                logger.error('[App] Initialization failed:', error);
                setIsInitialized(true); // Still initialize to show app
            }
        };

        initializeApp();
    }, []);

    if (!isInitialized) {
        return (
            <View style={styles.loadingContainer}>
                <ActivityIndicator size="large" color="#4CAF50" />
                <Text style={styles.loadingText}>Initializing SafeRoute...</Text>
            </View>
        );
    }

    return (
        <View style={styles.container}>
            <StatusBar barStyle="dark-content" />
            <MapScreen />
            <MiniSOSButton />
            <BottomControls />
        </View>
    );
}

export default function App() {
    return (
        <ErrorBoundary>
            <NavigationContainer>
                <MainStack />
            </NavigationContainer>
        </ErrorBoundary>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#fff',
    },
    loadingContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: '#fff',
    },
    loadingText: {
        marginTop: 12,
        fontSize: 14,
        color: '#666',
    },
    errorContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: '#fff',
        paddingHorizontal: 20,
    },
    errorText: {
        fontSize: 24,
        fontWeight: 'bold',
        marginBottom: 12,
        color: '#d32f2f',
    },
    errorMessage: {
        fontSize: 16,
        color: '#666',
        textAlign: 'center',
        marginBottom: 12,
    },
    errorHint: {
        fontSize: 12,
        color: '#999',
        textAlign: 'center',
    },
});
