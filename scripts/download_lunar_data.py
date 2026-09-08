#!/usr/bin/env python3
"""NEXUS-LUNAR: Lunar Data Download & Acquisition CLI.

Examples:
  # Query & download LRO NAC reference images around lunar south pole
  python scripts/download_lunar_data.py --sensor LRO_NAC --min-lat -85 --max-lat -80 --min-lon 0 --max-lon 30 --limit 5

  # Download by specific PDS Product ID
  python scripts/download_lunar_data.py --sensor LRO_NAC --product-id M1144485705LR

  # Generate verified local benchmark pairs for instant registration testing
  python scripts/download_lunar_data.py --benchmark
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
    PDSODEClient,
    LunarDataCatalog,
)
from packages.data_pipeline.sample_benchmark import create_sample_benchmark_suite

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("nexus.cli.download")


def main():
    parser = argparse.ArgumentParser(description="NEXUS-LUNAR: Lunar Data Acquisition CLI")
    parser.add_argument(
        "--sensor",
        type=str,
        choices=["LRO_NAC", "SELENE_TC", "SELENE_MI", "OHRC", "TMC2", "IIRS"],
        default="LRO_NAC",
        help="Target Lunar sensor payload",
    )
    parser.add_argument("--product-id", type=str, help="Specific Product ID to query/download")
    parser.add_argument("--min-lat", type=float, help="Minimum latitude in degrees (-90 to 90)")
    parser.add_argument("--max-lat", type=float, help="Maximum latitude in degrees (-90 to 90)")
    parser.add_argument("--min-lon", type=float, help="Minimum longitude in degrees (-180 to 180)")
    parser.add_argument("--max-lon", type=float, help="Maximum longitude in degrees (-180 to 180)")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of products to download")
    parser.add_argument("--preview-only", action="store_true", help="Download browse/preview images only")
    parser.add_argument("--output-dir", type=str, default="data/raw", help="Target output raw directory")
    parser.add_argument("--catalog-file", type=str, default="data/catalog.json", help="Path to catalog index")
    parser.add_argument("--benchmark", action="store_true", help="Generate verified local benchmark suite")

    args = parser.parse_args()

    if args.benchmark:
        logger.info("Generating verified benchmark dataset suite...")
        obs_list = create_sample_benchmark_suite("data")
        print("\n=== Benchmark Datasets Initialized ===")
        for obs in obs_list:
            print(f"[{obs.sensor.value}] {obs.product_id} | Res: {obs.spatial_resolution_m}m | File: {obs.primary_image_path}")
        print("\nBenchmark generation complete. Ready for registration pipelines.")
        return

    # Standard query mode via NASA ODE
    sensor = SensorType(args.sensor)
    bbox = None
    if all(x is not None for x in (args.min_lat, args.max_lat, args.min_lon, args.max_lon)):
        bbox = BoundingBox(
            min_lat=args.min_lat,
            max_lat=args.max_lat,
            min_lon=args.min_lon,
            max_lon=args.max_lon,
        )

    client = PDSODEClient(output_dir=args.output_dir)
    catalog = LunarDataCatalog(catalog_file=args.catalog_file)

    logger.info(f"Querying products for sensor={sensor.value}, bbox={bbox}, product_id={args.product_id}...")
    products = client.query_products(
        sensor=sensor,
        bbox=bbox,
        product_id=args.product_id,
        limit=args.limit,
    )

    if not products:
        logger.warning("No products found for the given criteria.")
        return

    print(f"\nFound {len(products)} products on NASA ODE. Starting download...")
    for idx, prod in enumerate(products, 1):
        obs = client.convert_ode_product_to_observation(prod, sensor=sensor)
        print(f"\n[{idx}/{len(products)}] Product ID: {obs.product_id} | Resolution: {obs.spatial_resolution_m}m")
        print(f"  Bounds: Lat [{obs.bbox.min_lat:.2f}, {obs.bbox.max_lat:.2f}], Lon [{obs.bbox.min_lon:.2f}, {obs.bbox.max_lon:.2f}]")
        if obs.geometry.incidence_angle_deg is not None:
            print(f"  Incidence: {obs.geometry.incidence_angle_deg:.1f} deg | Phase: {obs.geometry.phase_angle_deg or 'N/A'}")
        if obs.footprint_polygon:
            print(f"  Footprint: {len(obs.footprint_polygon)} polygon boundary vertices")
        
        obs = client.download_observation(obs, download_preview_only=args.preview_only)
        catalog.add_observation(obs)
        print(f"  Stored locally at: {obs.primary_image_path or obs.preview_image_path}")

    print(f"\nAll downloads completed and indexed into {args.catalog_file}!")


if __name__ == "__main__":
    main()
