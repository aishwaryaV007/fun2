#!/usr/bin/env python3
"""
generate_graph.py
=================
Generate the Gachibowli road network from OpenStreetMap.

This script downloads the real road network for Gachibowli, Hyderabad
using OSMnx, extracts junctions and edges, and saves them to JSON files
for use by the SafeRoute routing engine.

Usage
-----
python generate_graph.py

Requirements
------------
pip install osmnx networkx numpy

Output Files
------------
- SafeRoute_Backend/data/gachibowli_junctions.json    (all junctions/intersections)
- SafeRoute_Backend/data/gachibowli_edges.json        (all road segments)
- SafeRoute_Backend/data/gachibowli_road_graph.json   (simplified graph format)
- SafeRoute_Backend/data/gachibowli_complete.json     (combined data)

Expected Output
---------------
- Thousands of junction nodes
- Thousands of road edges
- Complete road network for 5 km radius around Gachibowli
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path so we can import services
sys.path.insert(0, str(Path(__file__).parent))

from services.road_graph_generator import (
    generate_road_graph,
    GACHIBOWLI_LAT,
    GACHIBOWLI_LNG,
    RADIUS_METERS,
)


def main():
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger = logging.getLogger(__name__)

    print("""
╔════════════════════════════════════════════════════════════════╗
║         SafeRoute Road Network Generator                       ║
║         OpenStreetMap → Gachibowli Road Graph                  ║
╚════════════════════════════════════════════════════════════════╝
    """)

    print(f"Target Area: Gachibowli, Hyderabad")
    print(f"Coordinates: {GACHIBOWLI_LAT}, {GACHIBOWLI_LNG}")
    print(f"Radius: {RADIUS_METERS} meters ({RADIUS_METERS / 1000} km)")
    print()

    try:
        print("Generating road network...")
        junctions, edges, graph = generate_road_graph()

        print()
        print(f"✓ Road network generated successfully!")
        print()
        print(f"Statistics:")
        print(f"  Junctions (nodes): {len(junctions):,}")
        print(f"  Road edges: {len(edges):,}")
        print(f"  Graph connectivity: {graph.number_of_nodes():,} nodes, {graph.number_of_edges():,} edges")
        print()

        # Show some statistics
        if junctions:
            total_roads = sum(j.get("connecting_roads", 0) for j in junctions)
            avg_roads = total_roads / len(junctions) if junctions else 0
            print(f"  Average roads per junction: {avg_roads:.1f}")

        if edges:
            total_distance = sum(e.get("length_meters", 0) for e in edges)
            avg_distance = total_distance / len(edges) if edges else 0
            print(f"  Total road network distance: {total_distance / 1000:.1f} km")
            print(f"  Average segment length: {avg_distance:.1f} m")

        print()
        print("Output files:")
        data_dir = Path(__file__).parent / "data"
        files = [
            "gachibowli_junctions.json",
            "gachibowli_edges.json",
            "gachibowli_complete.json",
            "gachibowli_road_graph.json",
        ]
        for f in files:
            file_path = data_dir / f
            if file_path.exists():
                size_kb = file_path.stat().st_size / 1024
                print(f"  ✓ {f} ({size_kb:.1f} KB)")

        print()
        print("Ready to use for routing!")
        print()

        return 0

    except Exception as e:
        logger.error("Road network generation failed: %s", e, exc_info=True)
        print()
        print(f"✗ Error: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Install required packages: pip install osmnx networkx numpy")
        print("  2. Check internet connection (OSMnx downloads from OpenStreetMap)")
        print("  3. Check that Gachibowli coordinates are valid")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
