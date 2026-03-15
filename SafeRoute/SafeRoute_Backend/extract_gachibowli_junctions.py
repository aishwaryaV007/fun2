import os
import json
import math
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # Convert decimal degrees to radians 
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371000 # Radius of earth in meters
    return c * r

def get_road_factor(highway_type):
    """
    Returns a safety factor based on road type.
    Higher values for more significant roads.
    """
    factors = {
        'motorway': 1.0,
        'trunk': 0.9,
        'primary': 0.8,
        'secondary': 0.7,
        'tertiary': 0.6,
        'residential': 0.4,
        'service': 0.3,
        'unclassified': 0.2
    }
    # Handle list if OSM returns multiple types for an edge
    if isinstance(highway_type, list):
        highway_type = highway_type[0]
    return factors.get(highway_type, 0.3)

def map_road_type(highway_type):
    """
    Maps OSM highway types to simplified road types.
    """
    mapping = {
        'motorway': 'highway',
        'trunk': 'highway',
        'primary': 'primary',
        'secondary': 'secondary',
        'tertiary': 'tertiary',
        'residential': 'residential',
        'living_street': 'residential',
        'service': 'service'
    }
    if isinstance(highway_type, list):
        highway_type = highway_type[0]
    return mapping.get(highway_type, 'unclassified')

def estimate_safety_metrics(distance_from_center, degree, highway_type=None):
    """
    Heuristic-based safety metric estimation.
    """
    centrality_factor = max(0, 1 - distance_from_center / 5000)
    
    road_factor = 0.5
    if highway_type:
        road_factor = get_road_factor(highway_type)
    
    # Heuristics based on requirements
    cctv_count = int(2 + centrality_factor * 8 + road_factor * 5)
    crowd_count = int(50 + centrality_factor * 2000 + road_factor * 500)
    
    # Additional heuristics
    lighting_score = min(10.0, 4.0 + centrality_factor * 4.0 + road_factor * 2.0)
    crime_density = max(0.1, 0.5 - centrality_factor * 0.3 + (1 - road_factor) * 0.2)
    
    return {
        "cctv_count": cctv_count,
        "crowd_count": crowd_count,
        "lighting_score": float(f"{lighting_score:.2f}"),
        "crime_density": float(f"{crime_density:.3f}")
    }

def main():
    try:
        import osmnx as ox
        import networkx as nx
    except ImportError:
        logger.error("OSMnx or NetworkX not installed. Please install via: pip install osmnx networkx geopy")
        return

    # Configuration
    CENTER_LAT, CENTER_LON = 17.4435, 78.3484
    RADIUS = 5000  # 5 km
    DATA_DIR = "data"
    
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        logger.info(f"Created directory: {DATA_DIR}")

    logger.info(f"Downloading road network for Gachibowli (5km radius)...")
    try:
        # Download graph
        G = ox.graph_from_point((CENTER_LAT, CENTER_LON), dist=RADIUS, network_type='drive', simplify=True)
        logger.info(f"Network downloaded. Initial nodes: {len(G.nodes)}, edges: {len(G.edges)}")
    except Exception as e:
        logger.error(f"Failed to download network: {e}")
        return

    if not G.nodes:
        logger.warning("Empty results from OpenStreetMap. Check coordinates or radius.")
        return

    logger.info("Extracting junction data...")
    junctions = []
    node_id_map = {} # Maps OSM node ID to sequential junction_id

    for i, (node_id, data) in enumerate(G.nodes(data=True)):
        lat = round(data['y'], 6)
        lon = round(data['x'], 6)
        
        # Degree in nx graph (number of incident edges)
        degree = G.degree(node_id)
        
        distance = haversine_distance(CENTER_LAT, CENTER_LON, lat, lon)
        safety = estimate_safety_metrics(distance, degree)
        
        junction_id = i + 1
        node_id_map[node_id] = junction_id
        
        junction_name = data.get('name', f"Junction_{junction_id}")
        if isinstance(junction_name, list): junction_name = junction_name[0]
        
        junctions.append({
            "junction_id": junction_id,
            "osm_node_id": node_id,
            "latitude": lat,
            "longitude": lon,
            "junction_name": junction_name,
            "connecting_roads": degree,
            "junction_type": "intersection" if degree > 2 else "endpoint",
            **safety
        })

    logger.info(f"Extracted {len(junctions)} junctions.")

    logger.info("Extracting road segments (edges)...")
    edges = []
    road_type_counts = {}

    for i, (u, v, data) in enumerate(G.edges(data=True)):
        start_j = node_id_map[u]
        end_j = node_id_map[v]
        
        u_data = G.nodes[u]
        v_data = G.nodes[v]
        
        highway = data.get('highway', 'unclassified')
        road_type = map_road_type(highway)
        
        # Update statistics
        road_type_counts[road_type] = road_type_counts.get(road_type, 0) + 1
        
        # Calculate length if missing
        length = data.get('length', haversine_distance(u_data['y'], u_data['x'], v_data['y'], v_data['x']))
        
        dist_from_center = (haversine_distance(CENTER_LAT, CENTER_LON, u_data['y'], u_data['x']) + 
                           haversine_distance(CENTER_LAT, CENTER_LON, v_data['y'], v_data['x'])) / 2
        
        safety = estimate_safety_metrics(dist_from_center, 0, highway)
        
        road_name = data.get('name', 'Unnamed Road')
        if isinstance(road_name, list): road_name = road_name[0]

        edges.append({
            "edge_id": i + 1,
            "segment_id": f"edge_{start_j}_to_{end_j}",
            "start_junction_id": start_j,
            "end_junction_id": end_j,
            "start_lat": round(u_data['y'], 6),
            "start_lon": round(u_data['x'], 6),
            "end_lat": round(v_data['y'], 6),
            "end_lon": round(v_data['x'], 6),
            "length_meters": round(length, 2),
            "road_name": road_name,
            "road_type": road_type,
            "highway_type": str(highway),
            "one_way": data.get('oneway', False),
            "max_speed": data.get('maxspeed', "unknown"),
            **safety
        })

    logger.info(f"Extracted {len(edges)} edges.")

    # Save files
    logger.info("Saving data to JSON files...")
    
    paths = {
        "junctions": os.path.join(DATA_DIR, "gachibowli_junctions.json"),
        "edges": os.path.join(DATA_DIR, "gachibowli_edges.json"),
        "complete": os.path.join(DATA_DIR, "gachibowli_complete.json")
    }

    with open(paths["junctions"], "w") as f:
        json.dump(junctions, f, indent=2)
    
    with open(paths["edges"], "w") as f:
        json.dump(edges, f, indent=2)
        
    complete_data = {
        "metadata": {
            "area": "Gachibowli, Hyderabad",
            "center": [CENTER_LAT, CENTER_LON],
            "radius_meters": RADIUS,
            "extracted_at": datetime.now().isoformat(),
            "statistics": {
                "junction_count": len(junctions),
                "edge_count": len(edges),
                "road_type_breakdown": road_type_counts
            }
        },
        "junctions": junctions,
        "edges": edges
    }
    
    with open(paths["complete"], "w") as f:
        json.dump(complete_data, f, indent=2)

    logger.info("--- Extraction Summary ---")
    logger.info(f"Junctions: {len(junctions)}")
    logger.info(f"Edges: {len(edges)}")
    logger.info("Road Type Breakdown:")
    for rtype, count in road_type_counts.items():
        logger.info(f"  - {rtype}: {count}")
    logger.info(f"Files saved in {DATA_DIR}/ directory.")

if __name__ == "__main__":
    main()
