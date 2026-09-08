#!/usr/bin/env python3
"""NEXUS POC 1 Demo: Lunar Spatial Knowledge Graph (SKG).

Demonstrates:
1. Building a heterogeneous Lunar Spatial Knowledge Graph for Boguslawsky Crater
2. Querying spatial context and hazard constraints for candidate landing/habitat sites
3. Tracing observation lineage back to Chandrayaan-2 (OHRC, TMC-2, IIRS) and LRO NAC
4. Exporting the graph to GeoJSON and Three.js-ready JSON
"""

import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.nexus_core.poc1_knowledge_graph import (
    build_boguslawsky_knowledge_graph,
)


def run_demo():
    print("=" * 72)
    print(" NEXUS POC 1: LUNAR SPATIAL KNOWLEDGE GRAPH (SKG) ENGINE")
    print("=" * 72)

    # 1. Build Graph
    print("\n[*] Constructing Lunar Knowledge Graph for Boguslawsky South Pole Region...")
    skg = build_boguslawsky_knowledge_graph()
    print(f"    Total Nodes: {skg.num_nodes}")
    print(f"    Total Edges: {skg.num_edges}")

    # Node Breakdown
    node_types = {}
    for _, data in skg.graph.nodes(data=True):
        ntype = data.get("node_type", "Unknown")
        node_types[ntype] = node_types.get(ntype, 0) + 1

    print("\n[*] Node Distribution:")
    for ntype, count in sorted(node_types.items()):
        print(f"    - {ntype:22s}: {count:2d}")

    # 2. Query Candidate Site Context
    site_id = "site_candidate_01_north_rim"
    print(f"\n[*] Querying Spatial Context for '{site_id}'...")
    ctx = skg.get_site_context(site_id)
    site_info = ctx["site"]
    print(f"    Site Name:           {site_info['name']}")
    print(f"    Coordinates:         Lat {site_info['lat']:.2f}°, Lon {site_info['lon']:.2f}°")
    print(f"    Elevation:           {site_info['elevation_m']:.1f} m")
    print(f"    Mean Slope:          {site_info.get('mean_slope_deg')}°")
    print(f"    Solar Availability:  {site_info.get('solar_availability_pct')}%")
    print(f"    Earth Line-of-Sight: {site_info.get('earth_line_of_sight_pct')}%")

    print("\n    [+] Suitable Habitat Components:")
    for comp in ctx["suitable_components"]:
        print(f"        • {comp['name']} ({comp['type']})")

    print("\n    [+] Potential Resources Nearby:")
    for res in ctx["spectral_indicators"]:
        print(f"        • {res['name']} (Band depth: {res.get('band_depth_pct')}%, Proxy: {res.get('resource_proxy')})")

    # 3. Observation Lineage
    print(f"\n[*] Scientific Lineage Tracing for '{site_id}':")
    lineage = skg.trace_observation_lineage(site_id)
    print(f"    Grounding Sensors: {', '.join(lineage['sensors'])}")
    print("    Registered Observations:")
    for obs in lineage["observations"]:
        print(f"        • [{obs.get('sensor')}] {obs.get('name')} (Product ID: {obs.get('product_id')})")

    # 4. Check Constrained Site #02
    site2_id = "site_candidate_02_floor"
    print(f"\n[*] Evaluating Hazard Constraints for '{site2_id}'...")
    ctx2 = skg.get_site_context(site2_id)
    for h in ctx2["hazards"]:
        hazard_data = h["hazard"]
        print(f"    [!] Hazard: {hazard_data['name']} (Type: {hazard_data.get('hazard_type')}, Risk: {hazard_data.get('risk_level')})")
    for c in ctx2["constraints"]:
        c_source = c["source"]["name"]
        rule = c["data"].get("properties", {}).get("constraint_rule", "Active constraint")
        print(f"    [!] Constraint from {c_source}: '{rule}'")

    # 5. Export Graph Files
    out_dir = Path("outputs/nexus_skg")
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "boguslawsky_knowledge_graph.json"
    geojson_path = out_dir / "boguslawsky_knowledge_graph.geojson"

    skg.export_json(json_path)
    with open(geojson_path, "w", encoding="utf-8") as f:
        json.dump(skg.to_geojson(), f, indent=2)

    print(f"\n[✓] Exported Graph to:    {json_path}")
    print(f"[✓] Exported GeoJSON to:  {geojson_path}")
    print("=" * 72)
    print(" NEXUS POC 1 COMPLETED SUCCESSFULLY")
    print("=" * 72)


if __name__ == "__main__":
    run_demo()
