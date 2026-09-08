#!/usr/bin/env python3
"""NEXUS-LUNAR: Catalog Query & Spatial Overlap Finder CLI.

Examples:
  # List all cataloged observations
  python scripts/query_catalog.py --list

  # Find overlapping OHRC vs LRO NAC registration pairs
  python scripts/query_catalog.py --find-pairs --source OHRC --reference LRO_NAC

  # Spatial search in bounding box
  python scripts/query_catalog.py --min-lat -75 --max-lat -70 --min-lon 20 --max-lon 35
"""

import sys
import argparse
import logging
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.data_pipeline import (
    SensorType,
    BoundingBox,
    CatalogQuery,
    LunarDataCatalog,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main():
    parser = argparse.ArgumentParser(description="Lunar Data Catalog & Overlap Query CLI")
    parser.add_argument("--catalog-file", type=str, default="data/catalog.json", help="Path to catalog index")
    parser.add_argument("--list", action="store_true", help="List all cataloged products")
    parser.add_argument("--find-pairs", action="store_true", help="Search for overlapping co-registration pairs")
    parser.add_argument("--source", type=str, default="OHRC", help="Source sensor (e.g. OHRC, TMC2)")
    parser.add_argument("--reference", type=str, default="LRO_NAC", help="Reference sensor (e.g. LRO_NAC, SELENE_TC)")
    parser.add_argument("--min-overlap", type=float, default=5.0, help="Minimum overlap percentage")
    parser.add_argument("--min-lat", type=float, help="Filter min latitude")
    parser.add_argument("--max-lat", type=float, help="Filter max latitude")
    parser.add_argument("--min-lon", type=float, help="Filter min longitude")
    parser.add_argument("--max-lon", type=float, help="Filter max longitude")

    args = parser.parse_args()
    catalog = LunarDataCatalog(catalog_file=args.catalog_file)

    if args.list:
        obs_list = catalog.list_observations()
        print(f"\n=== Lunar Data Catalog ({len(obs_list)} products) ===")
        for obs in obs_list:
            print(f"* [{obs.sensor.value}] {obs.product_id}")
            print(f"    Mission: {obs.mission.value} | Res: {obs.spatial_resolution_m}m")
            print(f"    Bounds: Lat [{obs.bbox.min_lat:.2f}, {obs.bbox.max_lat:.2f}], Lon [{obs.bbox.min_lon:.2f}, {obs.bbox.max_lon:.2f}]")
            print(f"    Primary Image: {obs.primary_image_path or 'N/A'}")
        return

    if args.find_pairs:
        src_sensor = SensorType(args.source)
        ref_sensor = SensorType(args.reference)
        print(f"\nSearching for overlapping pairs: {src_sensor.value} <-> {ref_sensor.value} (Min overlap: {args.min_overlap}%)...")
        pairs = catalog.find_overlapping_pairs(
            source_sensor=src_sensor,
            reference_sensor=ref_sensor,
            min_overlap_pct=args.min_overlap,
        )

        if not pairs:
            print("No overlapping observation pairs found in catalog.")
            return

        print(f"Found {len(pairs)} overlapping candidate pair(s):\n")
        for idx, p in enumerate(pairs, 1):
            print(f"[{idx}] SOURCE:    [{p['source_sensor']}] {p['source_product_id']} ({p['source_resolution_m']}m)")
            print(f"    REFERENCE: [{p['reference_sensor']}] {p['reference_product_id']} ({p['reference_resolution_m']}m)")
            print(f"    OVERLAP:   {p['overlap_percent_of_source']}% of source | {p['overlap_percent_of_reference']}% of reference")
            print(f"    ROI BBOX:  Lat [{p['intersection_bbox']['min_lat']:.2f}, {p['intersection_bbox']['max_lat']:.2f}], Lon [{p['intersection_bbox']['min_lon']:.2f}, {p['intersection_bbox']['max_lon']:.2f}]")
            print(f"    INCIDENCE ANGLE DELTA: {p['solar_incidence_diff_deg']:.1f} deg\n")
        return

    # Spatial query
    bbox = None
    if all(x is not None for x in (args.min_lat, args.max_lat, args.min_lon, args.max_lon)):
        bbox = BoundingBox(
            min_lat=args.min_lat,
            max_lat=args.max_lat,
            min_lon=args.min_lon,
            max_lon=args.max_lon,
        )

    query = CatalogQuery(bbox=bbox)
    results = catalog.query(query)
    print(f"\nFound {len(results)} matching observation(s):")
    for obs in results:
        print(f"* [{obs.sensor.value}] {obs.product_id} | Lat [{obs.bbox.min_lat:.2f}, {obs.bbox.max_lat:.2f}] Lon [{obs.bbox.min_lon:.2f}, {obs.bbox.max_lon:.2f}]")


if __name__ == "__main__":
    main()
