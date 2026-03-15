"""
services/route_graph_loader.py
==============================
Load and manage the road network graph for routing operations.

This module provides utilities to:
- Load the pre-generated road graph from JSON
- Query nearest junctions by coordinates
- Run pathfinding algorithms (Dijkstra, A*)
- Apply safety weights to path scores

Usage:
------
loader = RoadGraphLoader()
path = loader.find_safest_route(
    start=(17.440, 78.345),
    end=(17.448, 78.355),
    weight_type="safety_score"
)
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Optional

import networkx as nx

logger = logging.getLogger(__name__)

# Data directory
DATA_DIR = Path(__file__).parent.parent / "data"
ROAD_GRAPH_FILE = DATA_DIR / "gachibowli_road_graph.json"
JUNCTIONS_FILE = DATA_DIR / "gachibowli_junctions.json"
EDGES_FILE = DATA_DIR / "gachibowli_edges.json"


class RoadGraphLoader:
    """
    Manages the road network graph and provides routing utilities.
    """

    def __init__(
        self,
        graph_file: Path = ROAD_GRAPH_FILE,
        junctions_file: Path = JUNCTIONS_FILE,
        edges_file: Path = EDGES_FILE,
    ):
        """
        Initialize the road graph loader.

        Parameters
        ----------
        graph_file : Path
            Path to simplified road graph JSON
        junctions_file : Path
            Path to detailed junctions JSON
        edges_file : Path
            Path to detailed edges JSON
        """
        self.graph_file = graph_file
        self.junctions_file = junctions_file
        self.edges_file = edges_file

        # Data containers
        self.nx_graph: Optional[nx.Graph] = None
        self.junctions: list[dict] = []
        self.edges: list[dict] = []
        self.junction_lookup: dict = {}  # (lat, lng) → junction data
        self.node_tree: Optional[list] = None  # For spatial queries

        # Load data
        self._load_from_files()

    def _load_from_files(self) -> None:
        """Load graph data from JSON files."""
        try:
            # Load simplified graph
            if self.graph_file.exists():
                logger.info("Loading graph from %s", self.graph_file)
                with open(self.graph_file, encoding="utf-8") as f:
                    graph_data = json.load(f)
                self._build_networkx_graph(graph_data)
            else:
                logger.warning("Graph file not found: %s", self.graph_file)

            # Load detailed junctions
            if self.junctions_file.exists():
                logger.info("Loading junctions from %s", self.junctions_file)
                with open(self.junctions_file, encoding="utf-8") as f:
                    self.junctions = json.load(f)
                self._build_junction_lookup()
            else:
                logger.warning("Junctions file not found: %s", self.junctions_file)

            # Load detailed edges
            if self.edges_file.exists():
                logger.info("Loading edges from %s", self.edges_file)
                with open(self.edges_file, encoding="utf-8") as f:
                    self.edges = json.load(f)
            else:
                logger.warning("Edges file not found: %s", self.edges_file)

        except Exception as e:
            logger.error("Failed to load graph data: %s", e)
            raise

    def _build_networkx_graph(self, graph_data: dict) -> None:
        """
        Build NetworkX graph from JSON data.

        Parameters
        ----------
        graph_data : dict
            Graph data with 'nodes' and 'edges' keys
        """
        G = nx.Graph()

        # Add nodes
        for node in graph_data.get("nodes", []):
            node_id = (node["lat"], node["lng"])
            G.add_node(node_id, junction_id=node["id"])

        # Add edges
        for edge in graph_data.get("edges", []):
            # Get junction coordinates
            start_junction = self._get_junction_by_id(edge["from"])
            end_junction = self._get_junction_by_id(edge["to"])

            if not start_junction or not end_junction:
                continue

            start_node = (start_junction["latitude"], start_junction["longitude"])
            end_node = (end_junction["latitude"], end_junction["longitude"])

            # Add edge with weights
            safety_score = edge.get("safety_score", 50.0)
            distance = edge.get("distance", 0.0)

            # Weight = distance by default, can be overridden
            G.add_edge(
                start_node,
                end_node,
                distance=distance,
                safety_score=safety_score,
                weight=distance,  # Default weight
            )

        self.nx_graph = G
        logger.info(
            "Built NetworkX graph: %d nodes, %d edges",
            G.number_of_nodes(),
            G.number_of_edges(),
        )

    def _build_junction_lookup(self) -> None:
        """Build lookup table for junctions by (lat, lng) coordinates."""
        self.junction_lookup = {
            (j["latitude"], j["longitude"]): j for j in self.junctions
        }

    def _get_junction_by_id(self, junction_id: int) -> Optional[dict]:
        """Get junction data by ID."""
        for j in self.junctions:
            if j.get("junction_id") == junction_id:
                return j
        return None

    def find_nearest_junction(
        self,
        lat: float,
        lng: float,
        max_distance: float = 500.0,  # meters
    ) -> Optional[tuple[tuple[float, float], dict]]:
        """
        Find nearest junction to given coordinates.

        Parameters
        ----------
        lat : float
            Latitude
        lng : float
            Longitude
        max_distance : float
            Maximum search distance in meters

        Returns
        -------
        ((lat, lng), junction_data) or None
            Nearest junction location and data, or None if not found
        """
        if not self.nx_graph or not self.nx_graph.nodes():
            logger.warning("Graph is empty")
            return None

        min_distance = float("inf")
        nearest = None

        for node in self.nx_graph.nodes():
            node_lat, node_lng = node
            distance = self._haversine_distance(lat, lng, node_lat, node_lng)

            if distance < min_distance:
                min_distance = distance
                nearest = node

        # Check if within max distance
        if nearest and min_distance <= max_distance:
            junction_data = self.junction_lookup.get(nearest, {})
            return nearest, junction_data

        logger.warning(
            "No junction found within %.0f m of (%.4f, %.4f)",
            max_distance, lat, lng,
        )
        return None

    def _haversine_distance(
        self,
        lat1: float,
        lng1: float,
        lat2: float,
        lng2: float,
    ) -> float:
        """
        Calculate distance between two points using Haversine formula.

        Returns distance in meters.
        """
        R = 6371000  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lng2 - lng1)

        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))
        return R * c

    def find_shortest_path(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        weight: str = "distance",
    ) -> Optional[list[tuple[float, float]]]:
        """
        Find shortest path between two junctions using Dijkstra.

        Parameters
        ----------
        start : (lat, lng)
            Start junction
        end : (lat, lng)
            End junction
        weight : str
            Edge weight to use ('distance', 'safety_score', etc.)

        Returns
        -------
        list[(lat, lng), ...] or None
            Path as list of coordinates, or None if no path found
        """
        if not self.nx_graph:
            logger.error("Graph not loaded")
            return None

        try:
            path = nx.shortest_path(
                self.nx_graph,
                source=start,
                target=end,
                weight=weight,
            )
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound) as e:
            logger.warning("No path found: %s", e)
            return None

    def find_safest_path(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> Optional[list[tuple[float, float]]]:
        """
        Find safest path between two junctions using safety_score weights.

        Maximizes safety by using inverse safety score as distance.

        Parameters
        ----------
        start : (lat, lng)
            Start junction
        end : (lat, lng)
            End junction

        Returns
        -------
        list[(lat, lng), ...] or None
            Path as list of coordinates, or None if no path found
        """
        if not self.nx_graph:
            logger.error("Graph not loaded")
            return None

        # Convert safety_score to weight (lower = safer)
        # Map safety_score (0-100) to weight (infinity to 1)
        for u, v, data in self.nx_graph.edges(data=True):
            safety_score = data.get("safety_score", 50.0)
            # Invert: 100 (safe) → weight 0, 0 (dangerous) → weight 100
            safety_weight = 100 - safety_score
            data["safety_weight"] = safety_weight

        try:
            path = nx.shortest_path(
                self.nx_graph,
                source=start,
                target=end,
                weight="safety_weight",
            )
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound) as e:
            logger.warning("No safest path found: %s", e)
            return None

    def find_balanced_path(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        safety_weight: float = 0.6,  # 60% safety, 40% distance
    ) -> Optional[list[tuple[float, float]]]:
        """
        Find balanced path between distance and safety.

        Parameters
        ----------
        start : (lat, lng)
            Start junction
        end : (lat, lng)
            End junction
        safety_weight : float
            Weight for safety (0-1). 1.0 = pure safety, 0.0 = pure distance

        Returns
        -------
        list[(lat, lng), ...] or None
            Path as list of coordinates, or None if no path found
        """
        if not self.nx_graph:
            logger.error("Graph not loaded")
            return None

        # Combine distance and safety into composite weight
        for u, v, data in self.nx_graph.edges(data=True):
            distance = data.get("distance", 1000.0)
            safety_score = data.get("safety_score", 50.0)

            # Normalize distance (0-1 scale, assume max distance is 1000m)
            norm_distance = min(distance / 1000.0, 1.0)

            # Normalize safety (0-1 scale, lower is worse)
            norm_safety = 1.0 - (safety_score / 100.0)

            # Composite weight
            composite_weight = (
                (1.0 - safety_weight) * norm_distance +
                safety_weight * norm_safety
            )
            data["composite_weight"] = composite_weight

        try:
            path = nx.shortest_path(
                self.nx_graph,
                source=start,
                target=end,
                weight="composite_weight",
            )
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound) as e:
            logger.warning("No balanced path found: %s", e)
            return None

    def get_path_stats(
        self,
        path: list[tuple[float, float]],
    ) -> dict:
        """
        Calculate statistics for a path.

        Parameters
        ----------
        path : list[(lat, lng), ...]
            Path coordinates

        Returns
        -------
        dict
            Stats including total_distance, avg_safety_score, etc.
        """
        if len(path) < 2:
            return {"error": "Path too short"}

        total_distance = 0.0
        safety_scores = []

        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]

            if self.nx_graph.has_edge(u, v):
                edge_data = self.nx_graph[u][v]
                total_distance += edge_data.get("distance", 0.0)
                safety_scores.append(edge_data.get("safety_score", 50.0))

        avg_safety = sum(safety_scores) / len(safety_scores) if safety_scores else 50.0

        return {
            "distance_meters": round(total_distance, 2),
            "distance_km": round(total_distance / 1000, 2),
            "num_segments": len(path) - 1,
            "avg_safety_score": round(avg_safety, 2),
            "min_safety_score": min(safety_scores) if safety_scores else 50.0,
            "max_safety_score": max(safety_scores) if safety_scores else 50.0,
        }

    def get_graph_stats(self) -> dict:
        """Get overall graph statistics."""
        if not self.nx_graph:
            return {"error": "Graph not loaded"}

        return {
            "num_junctions": self.nx_graph.number_of_nodes(),
            "num_roads": self.nx_graph.number_of_edges(),
            "is_connected": nx.is_connected(self.nx_graph),
        }


# Global loader instance
_loader: Optional[RoadGraphLoader] = None


def get_loader() -> RoadGraphLoader:
    """Get or create global road graph loader."""
    global _loader
    if _loader is None:
        _loader = RoadGraphLoader()
    return _loader


def load_graph() -> RoadGraphLoader:
    """Alias for get_loader()."""
    return get_loader()
