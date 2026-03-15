"""
services/road_graph_generator.py
=================================
Real OSM-based road network generator for SafeRoute.

Downloads the actual road network from OpenStreetMap (via OSMnx)
for Gachibowli, Hyderabad and extracts:
  - Junction nodes (intersections)
  - Road edges (street segments)

Converts to NetworkX graph and exports as JSON.

Usage:
------
python -m services.road_graph_generator

Dependencies:
  osmnx
  networkx
  numpy
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import networkx as nx
import numpy as np

logger = logging.getLogger(__name__)

# Try to import osmnx (optional, for OSM download)
try:
    import osmnx as ox
    OSMNX_AVAILABLE = True
except ImportError:
    OSMNX_AVAILABLE = False
    logger.warning(
        "OSMnx not installed. Install with: pip install osmnx. "
        "You can still use pre-downloaded OSM data if available."
    )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Gachibowli, Hyderabad coordinates
GACHIBOWLI_LAT = 17.4435
GACHIBOWLI_LNG = 78.3484
RADIUS_METERS = 5000  # 5 km radius

# Data directory
DATA_DIR = Path(__file__).parent.parent / "data"
ROAD_GRAPH_FILE = DATA_DIR / "gachibowli_road_graph.json"
JUNCTIONS_FILE = DATA_DIR / "gachibowli_junctions.json"
EDGES_FILE = DATA_DIR / "gachibowli_edges.json"


# ---------------------------------------------------------------------------
# Step 1: Download OSM road network
# ---------------------------------------------------------------------------

def download_osm_network(
    center_lat: float = GACHIBOWLI_LAT,
    center_lng: float = GACHIBOWLI_LNG,
    radius: int = RADIUS_METERS,
    network_type: str = "drive",
) -> Optional[nx.MultiDiGraph]:
    """
    Download road network from OpenStreetMap using OSMnx.

    Parameters
    ----------
    center_lat : float
        Center latitude
    center_lng : float
        Center longitude
    radius : int
        Search radius in meters
    network_type : str
        'drive', 'walk', 'bike', 'all'

    Returns
    -------
    nx.MultiDiGraph or None
        OSM network graph, or None if download fails
    """
    if not OSMNX_AVAILABLE:
        logger.error("OSMnx not available. Install with: pip install osmnx")
        return None

    logger.info(
        "Downloading OSM network for Gachibowli (%.4f, %.4f) within %d m...",
        center_lat, center_lng, radius,
    )

    try:
        # Configure OSMnx to use local cache
        ox.settings.use_cache = True
        ox.settings.cache_folder = str(DATA_DIR / ".osm_cache")
        ox.settings.log_console = False

        # Download graph from OSM
        graph = ox.graph_from_point(
            (center_lat, center_lng),
            dist=radius,
            network_type=network_type,
            simplify=True,
            retain_all=False,
            truncate_by_edge=True,
        )

        logger.info(
            "Downloaded OSM network: %d nodes, %d edges",
            graph.number_of_nodes(), graph.number_of_edges(),
        )
        return graph

    except Exception as e:
        logger.error("Failed to download OSM network: %s", e)
        return None


# ---------------------------------------------------------------------------
# Step 2: Extract junction nodes from OSM graph
# ---------------------------------------------------------------------------

def extract_junctions_from_osm(
    osm_graph: nx.MultiDiGraph,
    start_id: int = 1,
) -> list[dict]:
    """
    Extract junction nodes from OSM graph.

    Each node becomes a junction with its lat/lng coordinates.
    Attributes like connectivity are preserved.

    Parameters
    ----------
    osm_graph : nx.MultiDiGraph
        OSM network graph
    start_id : int
        Starting junction ID

    Returns
    -------
    list[dict]
        Junctions in format:
        {
            "junction_id": int,
            "osm_node_id": int,
            "latitude": float,
            "longitude": float,
            "junction_name": str,
            "connecting_roads": int,
            "junction_type": str,
            "cctv_count": int (synthetic),
            "crowd_count": int (synthetic),
            "lighting_score": float (synthetic),
            "crime_density": float (synthetic),
        }
    """
    junctions: list[dict] = []

    for idx, (osm_id, node_data) in enumerate(osm_graph.nodes(data=True), start=start_id):
        lat = node_data.get("y")
        lng = node_data.get("x")

        if lat is None or lng is None:
            continue

        # Count connected roads (degree)
        degree = osm_graph.degree(osm_id)

        # Determine junction type based on connectivity
        if degree >= 4:
            junction_type = "intersection"
        elif degree == 3:
            junction_type = "T-junction"
        else:
            junction_type = "endpoint"

        # Synthetic safety attributes (to be updated from real data sources)
        # In production, these would come from crime databases, CCTV registries, etc.
        cctv_count = min(int(degree * 1.5), 10)  # More CCTVs at major intersections
        crowd_count = np.random.randint(100, 1000)
        lighting_score = np.random.uniform(3.0, 7.0)
        crime_density = np.random.uniform(0.3, 0.8)

        junction = {
            "junction_id": idx,
            "osm_node_id": osm_id,
            "latitude": float(lat),
            "longitude": float(lng),
            "junction_name": f"Junction_{idx}",
            "connecting_roads": degree,
            "junction_type": junction_type,
            "cctv_count": cctv_count,
            "crowd_count": crowd_count,
            "lighting_score": lighting_score,
            "crime_density": crime_density,
        }
        junctions.append(junction)

    logger.info("Extracted %d junctions from OSM network", len(junctions))
    return junctions


# ---------------------------------------------------------------------------
# Step 3: Extract road edges from OSM graph
# ---------------------------------------------------------------------------

def extract_edges_from_osm(
    osm_graph: nx.MultiDiGraph,
    junctions: list[dict],
) -> list[dict]:
    """
    Extract road edges from OSM graph.

    Each edge represents a road segment between two junctions.

    Parameters
    ----------
    osm_graph : nx.MultiDiGraph
        OSM network graph
    junctions : list[dict]
        Junction list (to map OSM node IDs to junction IDs)

    Returns
    -------
    list[dict]
        Edges in format:
        {
            "edge_id": int,
            "segment_id": str,
            "start_junction_id": int,
            "end_junction_id": int,
            "start_lat": float,
            "start_lon": float,
            "end_lat": float,
            "end_lon": float,
            "length_meters": float,
            "road_name": str,
            "road_type": str,
            "crime_density": float (synthetic),
            "cctv_count": int (synthetic),
            "crowd_density": int (synthetic),
            "lights_per_100m": float (synthetic),
            "safe_zone_flag": bool,
            "incident_report_count": int,
            "incident_severity_avg": float,
        }
    """
    edges: list[dict] = []

    # Build OSM node ID → junction ID mapping
    osm_to_junction_id: dict[int, int] = {}
    for junction in junctions:
        osm_to_junction_id[junction["osm_node_id"]] = junction["junction_id"]

    edge_id = 0
    for u, v, key, edge_data in osm_graph.edges(keys=True, data=True):
        edge_id += 1

        # Get start and end junction IDs
        start_junction_id = osm_to_junction_id.get(u)
        end_junction_id = osm_to_junction_id.get(v)

        if start_junction_id is None or end_junction_id is None:
            logger.warning(
                "Edge (%s, %s) has unmapped junctions. Skipping.", u, v,
            )
            continue

        # Get coordinates from OSM graph nodes
        start_node = osm_graph.nodes[u]
        end_node = osm_graph.nodes[v]
        start_lat = start_node.get("y")
        start_lon = start_node.get("x")
        end_lat = end_node.get("y")
        end_lon = end_node.get("x")

        if None in (start_lat, start_lon, end_lat, end_lon):
            continue

        # Get distance (OSMnx provides it in meters)
        distance_m = edge_data.get("length", 0.0)

        # Get road attributes from OSM
        road_name = edge_data.get("name", "Unnamed Road")
        if isinstance(road_name, list):
            road_name = "; ".join(road_name)

        highway_type = edge_data.get("highway", "unknown")
        if isinstance(highway_type, list):
            highway_type = highway_type[0]

        # Determine road type
        road_type = classify_road_type(highway_type)

        # Synthetic safety attributes
        crime_density = np.random.uniform(0.3, 0.8)
        cctv_count = int(np.random.uniform(0, 3))
        crowd_density = np.random.randint(50, 200)
        lights_per_100m = np.random.uniform(1.0, 5.0)
        safe_zone_flag = cctv_count > 0

        edge = {
            "edge_id": edge_id,
            "segment_id": f"edge_{start_junction_id}_to_{end_junction_id}",
            "start_junction_id": start_junction_id,
            "end_junction_id": end_junction_id,
            "start_lat": float(start_lat),
            "start_lon": float(start_lon),
            "end_lat": float(end_lat),
            "end_lon": float(end_lon),
            "length_meters": round(float(distance_m), 2),
            "road_name": road_name,
            "road_type": road_type,
            "crime_density": crime_density,
            "cctv_count": cctv_count,
            "crowd_density": crowd_density,
            "lights_per_100m": lights_per_100m,
            "safe_zone_flag": safe_zone_flag,
            "incident_report_count": 0,
            "incident_severity_avg": 0.0,
        }
        edges.append(edge)

    logger.info("Extracted %d edges from OSM network", len(edges))
    return edges


# ---------------------------------------------------------------------------
# Helper: Classify road types
# ---------------------------------------------------------------------------

def classify_road_type(highway_type: str) -> str:
    """
    Classify OSM highway type to SafeRoute road types.

    Parameters
    ----------
    highway_type : str
        OSM highway type (e.g., 'primary', 'secondary', 'residential')

    Returns
    -------
    str
        Classified road type
    """
    if highway_type in ("motorway", "trunk", "primary"):
        return "major_road"
    elif highway_type in ("secondary", "tertiary"):
        return "medium_road"
    elif highway_type in ("residential", "unclassified", "service"):
        return "local_road"
    elif highway_type == "footway":
        return "pedestrian"
    else:
        return "unknown"


# ---------------------------------------------------------------------------
# Step 4: Build NetworkX graph
# ---------------------------------------------------------------------------

def build_networkx_graph(
    junctions: list[dict],
    edges: list[dict],
) -> nx.Graph:
    """
    Build a NetworkX graph from junctions and edges.

    Parameters
    ----------
    junctions : list[dict]
        Junction nodes
    edges : list[dict]
        Road edges

    Returns
    -------
    nx.Graph
        NetworkX graph with nodes as (lat, lng) tuples
    """
    G = nx.Graph()

    # Add nodes
    for j in junctions:
        G.add_node(
            (j["latitude"], j["longitude"]),
            junction_id=j["junction_id"],
            osm_node_id=j["osm_node_id"],
            junction_name=j["junction_name"],
            junction_type=j["junction_type"],
            connecting_roads=j["connecting_roads"],
            cctv_count=j["cctv_count"],
            crowd_count=j["crowd_count"],
            lighting_score=j["lighting_score"],
            crime_density=j["crime_density"],
        )

    # Add edges
    for e in edges:
        start_node = (e["start_lat"], e["start_lon"])
        end_node = (e["end_lat"], e["end_lon"])

        G.add_edge(
            start_node,
            end_node,
            edge_id=e["edge_id"],
            segment_id=e["segment_id"],
            length_meters=e["length_meters"],
            road_name=e["road_name"],
            road_type=e["road_type"],
            crime_density=e["crime_density"],
            cctv_count=e["cctv_count"],
            crowd_density=e["crowd_density"],
            lights_per_100m=e["lights_per_100m"],
            safe_zone_flag=e["safe_zone_flag"],
            weight=e["length_meters"],  # Default weight for shortest path
        )

    logger.info(
        "Built NetworkX graph: %d nodes, %d edges",
        G.number_of_nodes(), G.number_of_edges(),
    )
    return G


# ---------------------------------------------------------------------------
# Safety scoring function
# ---------------------------------------------------------------------------

def calculate_safety_score(
    edge_attrs: dict,
    hour_of_day: int = 12,
) -> tuple[float, str]:
    """
    Calculate safety score for a road edge based on multiple attributes.
    
    Higher score = Safer road.
    
    Parameters
    ----------
    edge_attrs : dict
        Edge attributes including crime_density, cctv_count, etc.
    hour_of_day : int
        Hour of day (0-23) for time-based adjustments
        
    Returns
    -------
    (safety_score, risk_level)
        Score 0-100 and risk level 'safe'/'moderate'/'dangerous'
    """
    crime_density = edge_attrs.get("crime_density", 0.5)  # 0-1, lower is safer
    cctv_count = edge_attrs.get("cctv_count", 0)
    lights_per_100m = edge_attrs.get("lights_per_100m", 2.0)
    crowd_density = edge_attrs.get("crowd_density", 100)  # people/segment
    safe_zone_flag = edge_attrs.get("safe_zone_flag", False)
    incident_report_count = edge_attrs.get("incident_report_count", 0)
    incident_severity_avg = edge_attrs.get("incident_severity_avg", 0.0)
    
    # Base score (100 = perfectly safe)
    score = 100.0
    
    # Crime density impact (0-40 points)
    crime_impact = crime_density * 40
    score -= crime_impact
    
    # Incident history impact (0-20 points)
    incident_impact = min(incident_report_count * 2, 20)
    score -= incident_impact
    
    # Incident severity impact (0-10 points)
    severity_impact = incident_severity_avg * 10
    score -= severity_impact
    
    # CCTV coverage bonus (0-15 points)
    cctv_bonus = min(cctv_count * 5, 15)
    score += cctv_bonus
    
    # Street lighting bonus (0-15 points)
    lighting_bonus = min(lights_per_100m * 3, 15)
    score += lighting_bonus
    
    # Crowd density bonus (more people = safer, 0-10 points)
    crowd_bonus = min((crowd_density / 100) * 10, 10)
    score += crowd_bonus
    
    # Time-of-day adjustment (night is riskier)
    if hour_of_day < 6 or hour_of_day > 22:  # 10 PM - 6 AM
        score -= 10
    elif hour_of_day < 8 or hour_of_day > 20:  # 8 PM - 8 AM
        score -= 5
    
    # Safe zone bonus
    if safe_zone_flag:
        score += 5
    
    # Clamp score to 0-100
    score = max(0, min(100, score))
    
    # Determine risk level
    if score >= 70:
        risk_level = "safe"
    elif score >= 50:
        risk_level = "moderate"
    else:
        risk_level = "dangerous"
    
    return score, risk_level


# ---------------------------------------------------------------------------
# Step 5: Save graph data to JSON
# ---------------------------------------------------------------------------

def save_graph_data(
    junctions: list[dict],
    edges: list[dict],
    junctions_file: Path = JUNCTIONS_FILE,
    edges_file: Path = EDGES_FILE,
    combined_file: Path = ROAD_GRAPH_FILE,
) -> None:
    """
    Save junctions and edges to JSON files.

    Parameters
    ----------
    junctions : list[dict]
        Junction nodes
    edges : list[dict]
        Road edges
    junctions_file : Path
        Output file for junctions
    edges_file : Path
        Output file for edges
    combined_file : Path
        Output file for combined data
    """
    junctions_file.parent.mkdir(parents=True, exist_ok=True)

    # Save separate files
    logger.info("Saving junctions to %s", junctions_file)
    with open(junctions_file, "w", encoding="utf-8") as f:
        json.dump(junctions, f, indent=2)

    logger.info("Saving edges to %s", edges_file)
    with open(edges_file, "w", encoding="utf-8") as f:
        json.dump(edges, f, indent=2)

    # Save combined file
    combined_data = {
        "metadata": {
            "center_lat": GACHIBOWLI_LAT,
            "center_lng": GACHIBOWLI_LNG,
            "radius_meters": RADIUS_METERS,
            "junction_count": len(junctions),
            "edge_count": len(edges),
        },
        "junctions": junctions,
        "edges": edges,
    }

    logger.info("Saving combined data to %s", combined_file)
    with open(combined_file, "w", encoding="utf-8") as f:
        json.dump(combined_data, f, indent=2)

    logger.info(
        "Saved: %d junctions, %d edges",
        len(junctions), len(edges),
    )

    # Also save a simplified road graph representation (nodes + edges only)
    # This is used for lightweight routing clients and matches the requested
    # `gachibowli_road_graph.json` structure.
    simplified = {
        "nodes": [
            {"id": j["junction_id"], "lat": j["latitude"], "lng": j["longitude"]}
            for j in junctions
        ],
        "edges": [
            {
                "from": e["start_junction_id"],
                "to": e["end_junction_id"],
                "distance": e["length_meters"],
                "safety_score": calculate_safety_score({
                    "crime_density": e.get("crime_density", 0.0),
                    "cctv_count": e.get("cctv_count", 0),
                    "lights_per_100m": e.get("lights_per_100m", 0.0),
                    "crowd_density": e.get("crowd_density", 0.0),
                    "safe_zone_flag": e.get("safe_zone_flag", False),
                    "incident_report_count": e.get("incident_report_count", 0),
                    "incident_severity_avg": e.get("incident_severity_avg", 0.0),
                }, int(datetime.now().hour))[0],
            }
            for e in edges
        ],
    }

    road_graph_file = DATA_DIR / "gachibowli_road_graph.json"
    logger.info("Saving simplified road graph to %s", road_graph_file)
    with open(road_graph_file, "w", encoding="utf-8") as f:
        json.dump(simplified, f, indent=2)


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def generate_road_graph() -> tuple[list[dict], list[dict], nx.Graph]:
    """
    Complete pipeline: Download OSM → Extract junctions/edges → Build graph.

    Returns
    -------
    (junctions, edges, graph)
        Junctions, edges, and NetworkX graph
    """
    logger.info(
        "Starting road graph generation for Gachibowli "
        "(%.4f, %.4f) within %d m...",
        GACHIBOWLI_LAT, GACHIBOWLI_LNG, RADIUS_METERS,
    )

    # Step 1: Download OSM network
    osm_graph = download_osm_network(
        GACHIBOWLI_LAT, GACHIBOWLI_LNG, RADIUS_METERS, "drive"
    )
    if osm_graph is None:
        logger.error("Failed to download OSM network.")
        raise RuntimeError("OSM network download failed")

    # Step 2: Extract junctions
    junctions = extract_junctions_from_osm(osm_graph)
    if not junctions:
        logger.error("No junctions extracted.")
        raise RuntimeError("Junction extraction failed")

    # Step 3: Extract edges
    edges = extract_edges_from_osm(osm_graph, junctions)
    if not edges:
        logger.error("No edges extracted.")
        raise RuntimeError("Edge extraction failed")

    # Step 4: Build NetworkX graph
    graph = build_networkx_graph(junctions, edges)

    # Step 5: Save to files
    save_graph_data(junctions, edges)

    logger.info(
        "Road graph generation complete: %d junctions, %d edges",
        len(junctions), len(edges),
    )

    return junctions, edges, graph


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    try:
        junctions, edges, graph = generate_road_graph()
        print(f"\n✓ Road graph generation successful!")
        print(f"  Junctions: {len(junctions)}")
        print(f"  Edges: {len(edges)}")
        print(f"  Graph nodes: {graph.number_of_nodes()}")
        print(f"  Graph edges: {graph.number_of_edges()}")
    except Exception as e:
        logger.error("Road graph generation failed: %s", e)
        sys.exit(1)
