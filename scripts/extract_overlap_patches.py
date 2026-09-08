#!/usr/bin/env python3
"""NEXUS-LUNAR: POC 2 Resolution-Aware Geographic Overlap & Patch Extraction CLI.

Examples:
  # Extract patches for all catalog pairs between OHRC and LRO NAC:
  python scripts/extract_overlap_patches.py --all-pairs --patch-size 512

  # Extract patches for specific observation IDs:
  python scripts/extract_overlap_patches.py \
    --source-id CH2_OHRC_TEST_001 \
    --reference-id LRO_NAC_TEST_001 \
    --patch-size 256 --stride 128

  # Extract patches with dual-scale physical strategy:
  python scripts/extract_overlap_patches.py --all-pairs --strategy native_physical
"""

import sys
import argparse
import logging
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.data_pipeline import (
    SensorType,
    ResolutionStrategy,
    PatchExtractionConfig,
    OverlapPatchExtractor,
    LunarDataCatalog,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("nexus.scripts.extract_patches")


def main():
    parser = argparse.ArgumentParser(
        description="POC 2: Geographic Overlap & Resolution-Aware Patch Extraction CLI"
    )
    parser.add_argument(
        "--catalog-file",
        type=str,
        default="data/catalog.json",
        help="Path to catalog index database",
    )
    parser.add_argument(
        "--all-pairs",
        action="store_true",
        help="Extract patches for all overlapping pairs discovered in catalog",
    )
    parser.add_argument(
        "--source",
        type=str,
        help="Path to source raster file (GeoTIFF / IMG)",
    )
    parser.add_argument(
        "--reference",
        type=str,
        help="Path to reference raster file (GeoTIFF)",
    )
    parser.add_argument(
        "--reference-dir",
        type=str,
        help="Directory of candidate reference GeoTIFFs to screen automatically",
    )
    parser.add_argument(
        "--source-id",
        type=str,
        help="Specific source observation product ID (e.g. CH2_OHRC_...)",
    )
    parser.add_argument(
        "--reference-id",
        type=str,
        help="Specific reference observation product ID (e.g. LRO_NAC_...)",
    )
    parser.add_argument(
        "--source-sensor",
        type=str,
        default="OHRC",
        help="Source sensor type (OHRC, TMC2, IIRS)",
    )
    parser.add_argument(
        "--reference-sensor",
        type=str,
        default="LRO_NAC",
        help="Reference sensor type (LRO_NAC, SELENE_TC)",
    )
    parser.add_argument(
        "--patch-size",
        type=int,
        default=512,
        help="Square patch size in pixels (default: 512)",
    )
    parser.add_argument(
        "--stride",
        type=int,
        default=None,
        help="Sliding window stride in pixels (default: same as patch-size)",
    )
    parser.add_argument(
        "--min-overlap",
        type=float,
        default=5.0,
        help="Minimum overlap percentage threshold (default: 5.0)",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="match_coarser",
        choices=["match_coarser", "match_finer", "native_physical"],
        help="Resolution harmonization strategy (default: match_coarser)",
    )
    parser.add_argument(
        "--target-res",
        type=float,
        default=None,
        help="Explicit target GSD in meters per pixel (overrides strategy)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/processed/patches",
        help="Directory to save extracted patch pairs and manifests",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="png",
        choices=["png", "jpg", "tif"],
        help="Output image format for extracted patches (default: png)",
    )

    args = parser.parse_args()
    catalog = LunarDataCatalog(catalog_file=args.catalog_file)

    config = PatchExtractionConfig(
        patch_size=args.patch_size,
        stride=args.stride,
        min_overlap_pct=args.min_overlap,
        resolution_strategy=ResolutionStrategy(args.strategy),
        target_resolution_m=args.target_res,
        output_format=args.format,
    )
    extractor = OverlapPatchExtractor(config=config)

    # Mode 0: Direct Raster File Pipeline
    if args.source and (args.reference or args.reference_dir):
        from packages.data_pipeline import OverlapEngine, find_overlapping_reference_tiles, FootprintEngine
        engine = OverlapEngine()
        src_path = Path(args.source)
        if not src_path.exists():
            logger.error(f"Source file does not exist: {src_path}")
            sys.exit(1)

        if args.reference_dir:
            matches = find_overlapping_reference_tiles(src_path, args.reference_dir)
            if not matches:
                print("No overlapping reference tiles found.")
                return
            ref_path = Path(matches[0]["path"])
            print(f"Discovered top reference tile: {matches[0]['tile']} (Area: {matches[0]['intersection_area']} km²)")
        else:
            ref_path = Path(args.reference)

        res = engine.run_pipeline(
            source_raster=src_path,
            reference_raster=ref_path,
            output_dir=args.output_dir,
            source_id=args.source_id,
            reference_id=args.reference_id,
        )
        print(f"\nExtraction complete:")
        print(f"  Intersection Area: {res['overlap']['intersection_area']} km²")
        print(f"  Confidence:        {res['overlap']['confidence']}")
        print(f"  Metadata:          {Path(args.output_dir) / 'patch_metadata.json'}")
        return

    # Mode 1: Specific Pair
    if args.source_id and args.reference_id:
        src_obs = catalog.get_by_id(args.source_id)
        ref_obs = catalog.get_by_id(args.reference_id)

        if not src_obs:
            logger.error(f"Source product '{args.source_id}' not found in catalog {args.catalog_file}")
            sys.exit(1)
        if not ref_obs:
            logger.error(f"Reference product '{args.reference_id}' not found in catalog {args.catalog_file}")
            sys.exit(1)

        print(f"\n=======================================================")
        print(f"POC 2: Extracting Patches for Pair:")
        print(f"  Source:    {src_obs.product_id} ({src_obs.sensor.value}, {src_obs.spatial_resolution_m}m)")
        print(f"  Reference: {ref_obs.product_id} ({ref_obs.sensor.value}, {ref_obs.spatial_resolution_m}m)")
        print(f"  Patch Size: {config.patch_size}px | Strategy: {config.resolution_strategy.value}")
        print(f"=======================================================\n")

        manifest = extractor.extract_patch_pairs(
            source_obs=src_obs,
            reference_obs=ref_obs,
            output_dir=args.output_dir,
        )

        print(f"\nExtraction complete:")
        print(f"  Total Patches Generated: {manifest.total_patches}")
        print(f"  Intersection Area:       {manifest.intersection_area_km2} km²")
        print(f"  Output Directory:        {Path(args.output_dir) / (src_obs.product_id + '___' + ref_obs.product_id)}")
        return

    # Mode 2: All overlapping pairs in catalog
    if args.all_pairs:
        try:
            src_sensor = SensorType(args.source_sensor)
            ref_sensor = SensorType(args.reference_sensor)
        except ValueError as e:
            logger.error(f"Invalid sensor specification: {e}")
            sys.exit(1)

        pairs = catalog.find_overlapping_pairs(
            source_sensor=src_sensor,
            reference_sensor=ref_sensor,
            min_overlap_pct=args.min_overlap,
        )

        if not pairs:
            print(f"No overlapping pairs found between {src_sensor.value} and {ref_sensor.value} with >= {args.min_overlap}% overlap.")
            return

        print(f"\nFound {len(pairs)} candidate overlapping pair(s). Starting patch extraction...\n")

        total_extracted_pairs = 0
        for i, pair in enumerate(pairs, 1):
            src_obs = catalog.get_by_id(pair["source_product_id"])
            ref_obs = catalog.get_by_id(pair["reference_product_id"])
            if not src_obs or not ref_obs:
                continue

            print(f"[{i}/{len(pairs)}] Processing Pair:")
            print(f"  Source:    {src_obs.product_id} ({src_obs.sensor.value})")
            print(f"  Reference: {ref_obs.product_id} ({ref_obs.sensor.value})")
            print(f"  Overlap:   {pair['overlap_percent_of_source']}% | Area: {pair.get('overlap_area_km2', 'N/A')} km²")

            manifest = extractor.extract_patch_pairs(
                source_obs=src_obs,
                reference_obs=ref_obs,
                output_dir=args.output_dir,
            )
            print(f"  Generated: {manifest.total_patches} patch pairs\n")
            total_extracted_pairs += manifest.total_patches

        print(f"Finished. Extracted {total_extracted_pairs} total co-registered patch pairs across {len(pairs)} observations.")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
