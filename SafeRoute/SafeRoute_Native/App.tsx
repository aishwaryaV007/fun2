import { StatusBar } from 'expo-status-bar';
import React from 'react';
import { StyleSheet, View } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { MapScreen } from './src/components/MapScreen';
import { BottomControls } from './src/components/BottomControls';
import { SOSButton } from './src/components/SOSButton';

export default function App() {
    return (
        <NavigationContainer>
            <View style={styles.container}>
                <StatusBar style="dark" />
                <MapScreen />
                <BottomControls />
                <SOSButton />
            </View>
        </NavigationContainer>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#fff',
    },
});
