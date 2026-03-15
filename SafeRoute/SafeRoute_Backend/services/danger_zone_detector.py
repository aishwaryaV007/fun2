"""
services/danger_zone_detector.py
===============================
Detects danger zones (clusters of high crime density) using DBSCAN.
"""

import logging
from typing import Dict, List, Optional

import numpy as np

try:
    from sklearn.cluster import DBSCAN
except ImportError:
    DBSCAN = None

from .crime_heatmap_service import get_heatmap_service

logger = logging.getLogger(__name__)

class DangerZoneDetector:
    def __init__(self, eps: float = 0.015, min_samples: int = 5):  # ~1.5km, min cluster size
        self.eps = eps
        self.min_samples = min_samples
        self.last_zones: Optional[List[Dict]] = None
        self.last_min_risk: Optional[float] = None

    def _cluster_coords(self, coords: np.ndarray) -> np.ndarray:
        """Cluster coordinates with DBSCAN when available, else use a simple proximity fallback."""
        if DBSCAN is not None:
            return DBSCAN(
                eps=self.eps,
                min_samples=self.min_samples,
                metric="haversine",
            ).fit(np.radians(coords)).labels_

        logger.warning("scikit-learn not installed. Using fallback clustering for danger zones.")
        labels = np.full(len(coords), -1, dtype=int)
        visited = np.zeros(len(coords), dtype=bool)
        current_label = 0

        for start_idx in range(len(coords)):
            if visited[start_idx]:
                continue

            stack = [start_idx]
            cluster: list[int] = []

            while stack:
                idx = stack.pop()
                if visited[idx]:
                    continue

                visited[idx] = True
                cluster.append(idx)

                deltas = coords - coords[idx]
                neighbor_dist = np.sqrt(np.sum(deltas ** 2, axis=1))
                neighbors = np.where(neighbor_dist <= self.eps)[0]

                for neighbor in neighbors:
                    if not visited[int(neighbor)]:
                        stack.append(int(neighbor))

            if len(cluster) >= self.min_samples:
                labels[cluster] = current_label
                current_label += 1

        return labels

    def detect_danger_zones(self, force_refresh: bool = False, min_risk: float = 0.3) -> List[Dict]:
        if self.last_zones is not None and not force_refresh and self.last_min_risk == min_risk:
            return self.last_zones

        heatmap = get_heatmap_service().get_heatmap(force_refresh=force_refresh)
        if not heatmap:
            self.last_zones = []
            self.last_min_risk = min_risk
            return []

        coords = np.array([[cell["latitude"], cell["longitude"]] for cell in heatmap if cell["weight"] > 0.1])
        weights = np.array([cell["weight"] for cell in heatmap if cell["weight"] > 0.1])
        if len(coords) < self.min_samples:
            self.last_zones = []
            self.last_min_risk = min_risk
            return []

        labels = self._cluster_coords(coords)
        zones = []
        unique_labels = set(labels)
        unique_labels.discard(-1)  # Ignore noise

        for label in unique_labels:
            cluster_mask = labels == label
            members = coords[cluster_mask]
            member_weights = weights[cluster_mask]
            center_lat = float(np.mean(members[:, 0]))
            center_lng = float(np.mean(members[:, 1]))
            distances = np.degrees(np.arccos(np.clip(np.sum(np.radians(members - [center_lat, center_lng]), axis=1), -1, 1)))
            radius_deg = float(np.max(distances))
            risk_score = float(np.mean(member_weights))
            if risk_score > min_risk:
                zones.append({
                    "center_lat": round(center_lat, 6),
                    "center_lng": round(center_lng, 6),
                    "radius_degrees": round(radius_deg, 5),
                    "risk_score": round(risk_score, 4),
                    "cluster_size": len(members),
                    "avg_weight": round(np.mean(member_weights), 4)
                })

        self.last_zones = zones
        self.last_min_risk = min_risk
        logger.info("Detected %d danger zones (min_risk=%.2f)", len(zones), min_risk)
        return zones

    def invalidate_cache(self) -> None:
        self.last_zones = None
        self.last_min_risk = None


_DETECTOR: Optional[DangerZoneDetector] = None


def get_danger_zone_detector():
    global _DETECTOR
    if _DETECTOR is None:
        _DETECTOR = DangerZoneDetector()
    return _DETECTOR
