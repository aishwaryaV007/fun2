import { useEffect, useRef } from "react";
import { Accelerometer } from "expo-sensors";
import { Vibration } from "react-native";

interface ShakeDetectionConfig {
  onShakeDetected: () => void;
  /** Minimum acceleration sum to count as a shake. Higher = less sensitive. Default: 3.5 */
  threshold?: number;
  /** Minimum ms between shake events to avoid repeated triggers. Default: 3000 */
  debounceMs?: number;
  /** Vibration pattern to play on detection, e.g. [100, 50, 100]. Default: [200] */
  vibrationPattern?: number[];
  /** Whether shake detection is active. Default: true */
  enabled?: boolean;
}

export function useShakeDetection({
  onShakeDetected,
  threshold = 3.5,
  debounceMs = 3000,
  vibrationPattern = [200],
  enabled = true,
}: ShakeDetectionConfig) {
  const lastTriggerRef = useRef<number>(0);

  useEffect(() => {
    if (!enabled) return;

    Accelerometer.setUpdateInterval(100);

    const subscription = Accelerometer.addListener((data) => {
      const totalForce =
        Math.abs(data.x) + Math.abs(data.y) + Math.abs(data.z);

      if (totalForce > threshold) {
        const now = Date.now();
        if (now - lastTriggerRef.current < debounceMs) {
          return; // still in debounce window, ignore
        }
        lastTriggerRef.current = now;
        Vibration.vibrate(vibrationPattern);
        onShakeDetected();
      }
    });

    return () => {
      subscription.remove();
    };
  }, [enabled, threshold, debounceMs]);
}