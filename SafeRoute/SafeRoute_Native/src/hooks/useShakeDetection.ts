import { useEffect } from "react";
import { Accelerometer } from "expo-sensors";
import { Vibration } from "react-native";

interface ShakeDetectionConfig {
  onShakeDetected: () => void;
  threshold?: number;
}

export function useShakeDetection({
  onShakeDetected,
  threshold = 1.8,
}: ShakeDetectionConfig) {
  useEffect(() => {
    const subscription = Accelerometer.addListener((data) => {
      const totalForce =
        Math.abs(data.x) + Math.abs(data.y) + Math.abs(data.z);

      if (totalForce > threshold) {
        Vibration.vibrate(300);
        onShakeDetected();
      }
    });

    Accelerometer.setUpdateInterval(200);

    return () => {
      subscription.remove();
    };
  }, []);
}