"""
services/crime_heatmap_service.py
==================================
Crime heatmap generation from crime reports and SOS alerts.

Generates spatial heatmaps of crime density across the Gachibowli area.
Updates dynamically based on new crime reports and SOS incidents.

Usage:
------
heatmap_service = CrimeHeatmapService()
heatmap_grid = heatmap_service.generate_heatmap()
"""

from __future__ import annotations

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
from scipy.ndimage import gaussian_filter

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
CRIME_DB = DATA_DIR / "crime_reports.db"
SOS_DB = DATA_DIR / "sos_alerts.db"



class CrimeHeatmapService:
    """
    Generate crime density heatmaps from crime reports and SOS alerts.
    """

    def __init__(
        self,
        grid_resolution: float = 0.003,  # ~300m per cell
        decay_days: int = 30,  # Consider crimes from last 30 days
        sigma: float = 0.006,  # Gaussian blur radius ~2 cells
    ):
        """
        Initialize heatmap service.


        Parameters
        ----------
        grid_resolution : float
            Grid cell size in degrees (0.01 ≈ 1 km)
        decay_days : int
            How many days back to consider crime data
        sigma : float
            Gaussian blur sigma for smoothing
        """
        self.grid_resolution = grid_resolution
        self.decay_days = decay_days
        self.sigma = sigma

        # Gachibowli bounds (5 km radius)
        self.center_lat = 17.4435
        self.center_lng = 78.3484
        self.radius_degrees = 0.04  # ~4 km

        self.lat_min = self.center_lat - self.radius_degrees
        self.lat_max = self.center_lat + self.radius_degrees
        self.lng_min = self.center_lng - self.radius_degrees
        self.lng_max = self.center_lng + self.radius_degrees


        # Grid dimensions
        self.lat_bins = int((self.lat_max - self.lat_min) / grid_resolution) + 1
        self.lng_bins = int((self.lng_max - self.lng_min) / grid_resolution) + 1

        # Store last computed heatmap
        self._extend_schema()
        self.last_heatmap: Optional[list[dict]] = None
        self.last_update: Optional[datetime] = None


    def _extend_schema(self):
        """
        Idempotently extend crime_reports table with new fields.
        """
        try:
            with sqlite3.connect(CRIME_DB) as conn:
                table_info = conn.execute("PRAGMA table_info(crime_reports)").fetchall()
                columns = {row[1] for row in table_info}
                if 'severity' not in columns:
                    conn.execute("ALTER TABLE crime_reports ADD COLUMN severity REAL DEFAULT 5.0")
                if 'crime_type' not in columns:
                    conn.execute("ALTER TABLE crime_reports ADD COLUMN crime_type TEXT DEFAULT 'unknown'")
                if 'confidence_score' not in columns:
                    conn.execute("ALTER TABLE crime_reports ADD COLUMN confidence_score REAL DEFAULT 1.0")
                if 'reported_by' not in columns:
                    conn.execute("ALTER TABLE crime_reports ADD COLUMN reported_by TEXT DEFAULT 'anonymous'")
                if 'time_of_day' not in columns:
                    conn.execute("ALTER TABLE crime_reports ADD COLUMN time_of_day TEXT")
                if 'area_type' not in columns:
                    conn.execute("ALTER TABLE crime_reports ADD COLUMN area_type TEXT")
                conn.commit()
                logger.info("Schema extended")
        except Exception as e:
            logger.warning("Schema extension failed (may already exist): %s", e)


    def load_crime_data(self) -> list[dict]:
        """
        Load crime reports from DB + SOS alerts (weighted severity).
        Decay: last 30 days.
        """
        crimes = []
        cutoff = (datetime.now() - timedelta(days=self.decay_days)).isoformat()[:10]  # YYYY-MM-DD


        # Crime reports
        try:
            with sqlite3.connect(CRIME_DB) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute('''
                    SELECT 
                        lat AS latitude, 
                        lng AS longitude,
                        COALESCE(severity, CASE incident_type
                            WHEN "theft" THEN 5
                            WHEN "robbery" THEN 7
                            WHEN "harassment" THEN 8
                            WHEN "assault" THEN 10
                            ELSE 5 END) AS severity,
                        timestamp,
                        crime_type,
                        reported_by
                    FROM crime_reports 
                    WHERE date(timestamp) > date(?)
                ''', (cutoff,)).fetchall()
                for row in rows:
                    crimes.append(dict(row))
        except Exception as e:
            logger.warning("Crime DB load failed: %s", e)

        # SOS alerts (high severity)
        try:
            with sqlite3.connect(SOS_DB) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute('''
                    SELECT 
                        latitude, 
                        longitude, 
                        8.5 AS severity,
                        timestamp,
                        trigger_type AS crime_type,
                        device_info AS reported_by
                    FROM sos_alerts 
                    WHERE date(timestamp) > date(?) AND status = "active"
                    LIMIT 2000
                ''', (cutoff,)).fetchall()
                for row in rows:
                    crimes.append(dict(row))
        except Exception as e:
            logger.warning("SOS DB load failed: %s", e)

        logger.info("Loaded %d incidents (crimes + SOS)", len(crimes))
        return crimes


    def grid_coordinates(self) -> tuple[np.ndarray, np.ndarray]:
        """
        Generate grid coordinate arrays.

        Returns
        -------
        (lat_grid, lng_grid)
            Meshgrids for heatmap generation
        """
        lat_edges = np.arange(self.lat_min, self.lat_max + self.grid_resolution, 
                              self.grid_resolution)
        lng_edges = np.arange(self.lng_min, self.lng_max + self.grid_resolution,
                              self.grid_resolution)
        return np.meshgrid(lat_edges, lng_edges, indexing="ij")

    def compute_crime_density_grid(self, crimes: list[dict]) -> np.ndarray:
        """
        Compute crime density for each grid cell.

        Parameters
        ----------
        crimes : list[dict]
            Crime incidents with coordinates

        Returns
        -------
        np.ndarray
            2D grid of crime counts
        """
        # Initialize grid
        grid = np.zeros((self.lat_bins, self.lng_bins), dtype=float)

        # Accumulate crimes into grid cells
        for crime in crimes:
            lat = crime.get("latitude", self.center_lat)
            lng = crime.get("longitude", self.center_lng)
            severity = crime.get("severity", 1.0)

            # Find grid cell
            lat_idx = int((lat - self.lat_min) / self.grid_resolution)
            lng_idx = int((lng - self.lng_min) / self.grid_resolution)

            # Clamp to grid bounds
            lat_idx = max(0, min(self.lat_bins - 1, lat_idx))
            lng_idx = max(0, min(self.lng_bins - 1, lng_idx))

            # Add weighted crime
            grid[lat_idx, lng_idx] += severity

        logger.info("Crime grid computed: %d total weight", np.sum(grid))
        return grid

    def smooth_heatmap(self, grid: np.ndarray) -> np.ndarray:
        """
        Apply Gaussian smoothing to heatmap.

        Parameters
        ----------
        grid : np.ndarray
            Raw crime density grid

        Returns
        -------
        np.ndarray
            Smoothed grid
        """
        if np.sum(grid) == 0:
            return grid

        smoothed = gaussian_filter(grid, sigma=self.sigma)
        return smoothed

    def normalize_heatmap(self, grid: np.ndarray) -> np.ndarray:
        """
        Normalize heatmap values to 0-1 range.

        Parameters
        ----------
        grid : np.ndarray
            Heatmap grid

        Returns
        -------
        np.ndarray
            Normalized grid (0-1)
        """
        max_val = np.max(grid)
        if max_val > 0:
            return grid / max_val
        return grid

    def grid_to_points(self, grid: np.ndarray) -> list[dict]:
        """
        Convert grid to list of point heatmap cells.

        Parameters
        ----------
        grid : np.ndarray
            Normalized heatmap grid

        Returns
        -------
        list[dict]
            List of heatmap cells: {lat, lng, weight}
        """
        points = []

        for i in range(self.lat_bins):
            for j in range(self.lng_bins):
                weight = float(grid[i, j])
                if weight > 0.01:  # Only include non-negligible cells
                    lat = self.lat_min + i * self.grid_resolution
                    lng = self.lng_min + j * self.grid_resolution
                    points.append({
                        "latitude": round(lat, 6),
                        "longitude": round(lng, 6),
                        "weight": round(weight, 4),
                    })

        logger.info("Generated %d heatmap points", len(points))
        return points

    def generate_heatmap(self) -> list[dict]:
        """
        Generate complete crime heatmap.

        Pipeline:
        1. Load crime data
        2. Create density grid
        3. Apply Gaussian smoothing
        4. Normalize to 0-1
        5. Convert to point list

        Returns
        -------
        list[dict]
            Heatmap cells: {latitude, longitude, weight}
        """
        logger.info("Generating crime heatmap...")

        # Load crimes
        crimes = self.load_crime_data()

        # Create density grid
        grid = self.compute_crime_density_grid(crimes)

        # Smooth
        grid = self.smooth_heatmap(grid)

        # Normalize
        grid = self.normalize_heatmap(grid)

        # Convert to points
        heatmap = self.grid_to_points(grid)

        # Cache result
        self.last_heatmap = heatmap
        self.last_update = datetime.now()

        logger.info("Heatmap generated: %d cells", len(heatmap))
        return heatmap

    def get_heatmap(self, force_refresh: bool = False) -> list[dict]:
        """
        Get heatmap with optional caching.

        Parameters
        ----------
        force_refresh : bool
            Force recomputation instead of using cache

        Returns
        -------
        list[dict]
            Heatmap cells
        """
        if force_refresh or self.last_heatmap is None:
            return self.generate_heatmap()
        return self.last_heatmap

    def invalidate_cache(self) -> None:
        """Clear cached heatmap data after crime writes."""
        self.last_heatmap = None
        self.last_update = None

    def get_cell_weight(self, lat: float, lng: float) -> float:
        """
        Get heatmap weight for a specific location.

        Parameters
        ----------
        lat, lng : float
            Coordinates

        Returns
        -------
        float
            Heatmap weight (0-1)
        """
        if self.last_heatmap is None:
            self.generate_heatmap()

        # Find nearest cell
        min_distance = float("inf")
        weight = 0.0

        for cell in self.last_heatmap:
            dist = (
                (cell["latitude"] - lat) ** 2 +
                (cell["longitude"] - lng) ** 2
            ) ** 0.5
            if dist < min_distance:
                min_distance = dist
                weight = cell["weight"]

        return weight


# Global heatmap service instance
_heatmap_service: Optional[CrimeHeatmapService] = None


def get_heatmap_service() -> CrimeHeatmapService:
    """Get or create global heatmap service."""
    global _heatmap_service
    if _heatmap_service is None:
        _heatmap_service = CrimeHeatmapService()
    return _heatmap_service
