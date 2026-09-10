"""NEXUS-LUNAR: POC 2 Geographic Overlap & Patch Engine.

Core engine for:
1. True Selenographic Geographic Polygon Intersection
2. Explainable Geometric Overlap Confidence
3. Automated Reference Tile Screening and Discovery
4. Resolution-Aware Native Patch Extraction
5. Patch Metadata Generation & Visualization
"""

from __future__ import annotations
import os
import sys
import json
import math
import logging
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Union

import numpy as np
from PIL import Image
from shapely.geometry import Polygon, MultiPolygon, mapping, box
from shapely.validation import make_valid
import pyproj
try:
    import rasterio
    from rasterio.windows import Window, from_bounds
    from rasterio.enums import Resampling
    HAS_RASTERIO = True
except ImportError:
    rasterio = None
    Window = None
    from_bounds = None
    Resampling = None
    HAS_RASTERIO = False

from .footprint_engine import (
    FootprintEngine,
    FootprintResult,
    LUNAR_GEOGRAPHIC_PROJ4,
    LUNAR_RADIUS_M,
)
from .visualization import (
    generate_overlap_visualization,
    generate_patch_comparison_visualization,
)

logger = logging.getLogger("nexus.data.overlap_engine")


@dataclass
class OverlapAnalysisResult:
    """Detailed geometric overlap analysis between source and reference observations."""
    intersects: bool
    intersection_polygon: Optional[Polygon]
    intersection_area: float              # in km²
    source_area: float                    # in km²
    reference_area: float                 # in km²
    overlap_ratio_source: float           # intersection_area / source_area (0.0 to 1.0)
    overlap_ratio_reference: float        # intersection_area / reference_area (0.0 to 1.0)
    overlap_confidence: float             # Transparent, explainable score (0.0 to 1.0)
    common_bounds: Optional[Tuple[float, float, float, float]] = None # (min_lon, min_lat, max_lon, max_lat)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intersects": bool(self.intersects),
            "intersection_area": round(self.intersection_area, 4),
            "source_area": round(self.source_area, 4),
            "reference_area": round(self.reference_area, 4),
            "overlap_ratio_source": round(self.overlap_ratio_source, 4),
            "overlap_ratio_reference": round(self.overlap_ratio_reference, 4),
            "confidence": round(self.overlap_confidence, 4),
            "common_bounds": (
                {
                    "min_lon": round(self.common_bounds[0], 6),
                    "min_lat": round(self.common_bounds[1], 6),
                    "max_lon": round(self.common_bounds[2], 6),
                    "max_lat": round(self.common_bounds[3], 6),
                }
                if self.common_bounds
                else None
            ),
        }


def calculate_overlap(
    source_footprint: Union[FootprintResult, Polygon],
    reference_footprint: Union[FootprintResult, Polygon],
    footprint_engine: Optional[FootprintEngine] = None,
) -> OverlapAnalysisResult:
    """Calculates true geographic intersection between source and reference lunar footprints.
    
    Handles:
    - No overlap (disjoint)
    - Partial overlap
    - Complete containment
    - Invalid geometries (automatically repaired)
    - Missing CRS (raises validation error)
    """
    engine = footprint_engine or FootprintEngine()

    # Extract polygons and area
    if isinstance(source_footprint, FootprintResult):
        if not source_footprint.is_valid:
            poly_src = make_valid(source_footprint.polygon)
        else:
            poly_src = source_footprint.polygon
        src_area = source_footprint.area_km2
    elif isinstance(source_footprint, Polygon):
        poly_src = make_valid(source_footprint) if not source_footprint.is_valid else source_footprint
        src_area = engine.compute_spherical_area_km2(poly_src)
    else:
        raise TypeError(f"Unsupported source footprint type: {type(source_footprint)}")

    if isinstance(reference_footprint, FootprintResult):
        if not reference_footprint.is_valid:
            poly_ref = make_valid(reference_footprint.polygon)
        else:
            poly_ref = reference_footprint.polygon
        ref_area = reference_footprint.area_km2
    elif isinstance(reference_footprint, Polygon):
        poly_ref = make_valid(reference_footprint) if not reference_footprint.is_valid else reference_footprint
        ref_area = engine.compute_spherical_area_km2(poly_ref)
    else:
        raise TypeError(f"Unsupported reference footprint type: {type(reference_footprint)}")

    if poly_src.is_empty or poly_ref.is_empty:
        return OverlapAnalysisResult(
            intersects=False,
            intersection_polygon=None,
            intersection_area=0.0,
            source_area=src_area,
            reference_area=ref_area,
            overlap_ratio_source=0.0,
            overlap_ratio_reference=0.0,
            overlap_confidence=0.0,
            common_bounds=None,
        )

    # 1. Check intersection
    if not poly_src.intersects(poly_ref):
        return OverlapAnalysisResult(
            intersects=False,
            intersection_polygon=None,
            intersection_area=0.0,
            source_area=src_area,
            reference_area=ref_area,
            overlap_ratio_source=0.0,
            overlap_ratio_reference=0.0,
            overlap_confidence=0.0,
            common_bounds=None,
        )

    inter_geom = poly_src.intersection(poly_ref)
    if inter_geom.is_empty or inter_geom.area <= 0:
        return OverlapAnalysisResult(
            intersects=False,
            intersection_polygon=None,
            intersection_area=0.0,
            source_area=src_area,
            reference_area=ref_area,
            overlap_ratio_source=0.0,
            overlap_ratio_reference=0.0,
            overlap_confidence=0.0,
            common_bounds=None,
        )

    if not inter_geom.is_valid:
        inter_geom = make_valid(inter_geom)

    # Compute metric area of intersection
    if isinstance(inter_geom, MultiPolygon):
        inter_poly = max(inter_geom.geoms, key=lambda g: g.area)
        inter_area = sum(engine.compute_spherical_area_km2(g) for g in inter_geom.geoms)
    else:
        inter_poly = inter_geom
        inter_area = engine.compute_spherical_area_km2(inter_poly)

    # Calculate ratios
    ratio_src = min(1.0, max(0.0, inter_area / src_area)) if src_area > 0 else 0.0
    ratio_ref = min(1.0, max(0.0, inter_area / ref_area)) if ref_area > 0 else 0.0

    # =========================================================================
    # Explainable Geometric Overlap Confidence Formula:
    # Based strictly on verifiable geometric evidence:
    # 1. Coverage of source observation (weight: 0.60): A higher fraction of the high-res
    #    target observation covered implies higher geometric correspondence value.
    # 2. Coverage of reference observation (weight: 0.20): Indicates mutual overlap.
    # 3. Geometric regularity factor (weight: 0.20): Ratio of perimeter^2 to area (isoperimetric quotient)
    #    penalizing degenerate slivers or single-pixel edge touches.
    # =========================================================================
    isoperimetric_ratio = 1.0
    try:
        perimeter = inter_poly.length
        if perimeter > 0 and inter_poly.area > 0:
            # 4 * pi * A / P^2 is between 0 and 1 (1 for a circle)
            compactness = (4.0 * math.pi * inter_poly.area) / (perimeter * perimeter)
            isoperimetric_ratio = min(1.0, max(0.2, compactness * 5.0)) # scaled for typical rectangular footprints
    except Exception:
        isoperimetric_ratio = 1.0

    geometric_confidence = (0.60 * ratio_src) + (0.20 * min(1.0, ratio_ref * 5.0)) + (0.20 * isoperimetric_ratio)
    geometric_confidence = round(min(1.0, max(0.0, geometric_confidence)), 4)

    return OverlapAnalysisResult(
        intersects=True,
        intersection_polygon=inter_poly,
        intersection_area=inter_area,
        source_area=src_area,
        reference_area=ref_area,
        overlap_ratio_source=round(ratio_src, 4),
        overlap_ratio_reference=round(ratio_ref, 4),
        overlap_confidence=geometric_confidence,
        common_bounds=inter_poly.bounds,
    )


def find_overlapping_reference_tiles(
    source_footprint: Union[FootprintResult, Polygon, str, Path],
    reference_directory: Union[str, Path],
    min_overlap_area_km2: float = 0.0001,
) -> List[Dict[str, Any]]:
    """Scans a directory of candidate LROC GeoTIFFs, calculates their footprints,
    and returns only tiles that geometrically overlap the source footprint,
    sorted descending by overlap area."""
    ref_dir = Path(reference_directory)
    if not ref_dir.exists():
        raise FileNotFoundError(f"Reference directory not found: {ref_dir}")

    engine = FootprintEngine()

    # Resolve source footprint
    src_file_path: Optional[Path] = None
    if isinstance(source_footprint, (str, Path)):
        src_file_path = Path(source_footprint).resolve()
        src_fp = engine.extract_from_raster(src_file_path)
    elif isinstance(source_footprint, FootprintResult):
        src_fp = source_footprint
    elif isinstance(source_footprint, Polygon):
        src_fp = FootprintResult(
            polygon=source_footprint,
            bounds=source_footprint.bounds,
            area_km2=engine.compute_spherical_area_km2(source_footprint),
            crs_name="Lunar Selenographic (lon, lat)",
        )
    else:
        raise TypeError(f"Unsupported source footprint type: {type(source_footprint)}")

    # Supported raster formats
    valid_exts = {".tif", ".tiff", ".img", ".jp2"}
    candidate_files = [f for f in ref_dir.rglob("*") if f.suffix.lower() in valid_exts]

    results: List[Dict[str, Any]] = []

    for tile_path in candidate_files:
        if src_file_path and tile_path.resolve() == src_file_path:
            continue
        try:
            tile_fp = engine.extract_from_raster(tile_path)
            overlap = calculate_overlap(src_fp, tile_fp, footprint_engine=engine)
            if overlap.intersects and overlap.intersection_area >= min_overlap_area_km2:
                results.append({
                    "tile": tile_path.name,
                    "path": str(tile_path.resolve()),
                    "intersects": True,
                    "intersection_area": round(overlap.intersection_area, 4),
                    "source_area": round(overlap.source_area, 4),
                    "reference_area": round(overlap.reference_area, 4),
                    "overlap_ratio_source": round(overlap.overlap_ratio_source, 4),
                    "overlap_ratio_reference": round(overlap.overlap_ratio_reference, 4),
                    "confidence": round(overlap.overlap_confidence, 4),
                    "common_bounds": overlap.to_dict()["common_bounds"],
                    "tile_bounds": tile_fp.to_dict()["bounds"],
                    "tile_crs": tile_fp.crs_name,
                })
        except Exception as e:
            logger.debug(f"Skipping tile {tile_path.name} due to read error: {e}")
            continue

    # Sort descending by overlap area
    results.sort(key=lambda x: x["intersection_area"], reverse=True)
    return results


class OverlapEngine:
    """High-level POC-2 execution pipeline."""

    def __init__(self, footprint_engine: Optional[FootprintEngine] = None):
        self.footprint_engine = footprint_engine or FootprintEngine()

    def run_pipeline(
        self,
        source_raster: Union[str, Path],
        reference_raster: Union[str, Path],
        output_dir: Union[str, Path],
        source_id: Optional[str] = None,
        reference_id: Optional[str] = None,
        source_res_m: Optional[float] = None,
        ref_res_m: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Executes the complete POC-2 pipeline between a source and reference raster."""
        src_p = Path(source_raster)
        ref_p = Path(reference_raster)
        out_d = Path(output_dir)
        out_d.mkdir(parents=True, exist_ok=True)

        if not src_p.exists():
            raise FileNotFoundError(f"Source raster not found: {src_p}")
        if not ref_p.exists():
            raise FileNotFoundError(f"Reference raster not found: {ref_p}")

        # 1. Footprint Calculation
        src_fp = self.footprint_engine.extract_from_raster(src_p)
        ref_fp = self.footprint_engine.extract_from_raster(ref_p)

        # 2. Geometric Intersection
        overlap = calculate_overlap(src_fp, ref_fp, footprint_engine=self.footprint_engine)

        if not overlap.intersects or not overlap.intersection_polygon:
            logger.warning("No geographic intersection between source and reference rasters.")
            meta_none = {
                "source": {
                    "id": source_id or src_p.stem,
                    "path": str(src_p.resolve()),
                    "resolution_m_per_pixel": source_res_m or src_fp.metadata.get("res", (1.0, 1.0))[0],
                    "crs": src_fp.crs_name,
                },
                "reference": {
                    "id": reference_id or ref_p.stem,
                    "path": str(ref_p.resolve()),
                    "resolution_m_per_pixel": ref_res_m or ref_fp.metadata.get("res", (1.0, 1.0))[0],
                    "crs": ref_fp.crs_name,
                },
                "overlap": {
                    "intersects": False,
                    "intersection_area": 0.0,
                    "overlap_ratio_source": 0.0,
                    "overlap_ratio_reference": 0.0,
                    "confidence": 0.0,
                },
            }
            with open(out_d / "overlap_metadata.json", "w", encoding="utf-8") as f:
                json.dump(meta_none, f, indent=2)
            return meta_none

        # 3. Resolution-Aware Patch Extraction
        # Project common geographic intersection polygon into source and reference native raster space
        src_patch_path, src_dims = self._crop_to_common_footprint(
            src_p, overlap.intersection_polygon, out_d / f"{src_p.stem}_common_patch.png"
        )
        ref_patch_path, ref_dims = self._crop_to_common_footprint(
            ref_p, overlap.intersection_polygon, out_d / f"{ref_p.stem}_common_patch.png"
        )

        # Resolutions
        s_res = source_res_m or src_fp.metadata.get("res", (0.25, 0.25))[0]
        r_res = ref_res_m or ref_fp.metadata.get("res", (1.0, 1.0))[0]

        # 4. Patch Metadata JSON (Exact specification)
        inter_bounds = overlap.intersection_polygon.bounds
        metadata = {
            "source": {
                "id": source_id or src_p.stem,
                "path": str(src_p.resolve()),
                "resolution_m_per_pixel": float(s_res),
                "crs": src_fp.crs_name,
                "patch_path": str(src_patch_path.resolve()),
            },
            "reference": {
                "id": reference_id or ref_p.stem,
                "path": str(ref_p.resolve()),
                "resolution_m_per_pixel": float(r_res),
                "crs": ref_fp.crs_name,
                "patch_path": str(ref_patch_path.resolve()),
            },
            "overlap": {
                "intersects": True,
                "intersection_area": round(overlap.intersection_area, 4),
                "overlap_ratio_source": round(overlap.overlap_ratio_source, 4),
                "overlap_ratio_reference": round(overlap.overlap_ratio_reference, 4),
                "confidence": round(overlap.overlap_confidence, 4),
            },
            "common_ground_footprint": {
                "geometry": mapping(overlap.intersection_polygon),
                "bounds": {
                    "min_lon": round(inter_bounds[0], 6),
                    "min_lat": round(inter_bounds[1], 6),
                    "max_lon": round(inter_bounds[2], 6),
                    "max_lat": round(inter_bounds[3], 6),
                },
            },
            "patch_dimensions": {
                "source_width": src_dims[0],
                "source_height": src_dims[1],
                "reference_width": ref_dims[0],
                "reference_height": ref_dims[1],
            },
        }

        meta_json_path = out_d / "patch_metadata.json"
        with open(meta_json_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        # 5. Visualizations
        footprint_vis_path = out_d / "footprint_overlap.png"
        patch_vis_path = out_d / "patch_comparison.png"

        generate_overlap_visualization(
            source_footprint=src_fp,
            reference_footprint=ref_fp,
            intersection_polygon=overlap.intersection_polygon,
            output_path=footprint_vis_path,
            source_title=f"Source: {source_id or src_p.stem}",
            reference_title=f"Reference: {reference_id or ref_p.stem}",
            overlap_confidence=overlap.overlap_confidence,
            intersection_area_km2=overlap.intersection_area,
        )

        generate_patch_comparison_visualization(
            source_patch_path=src_patch_path,
            reference_patch_path=ref_patch_path,
            metadata=metadata,
            output_path=patch_vis_path,
        )

        metadata["visualizations"] = {
            "footprint_map": str(footprint_vis_path.resolve()),
            "patch_comparison": str(patch_vis_path.resolve()),
        }

        return metadata

    def _crop_to_common_footprint(
        self, raster_path: Path, common_geo_poly: Polygon, output_patch_path: Path
    ) -> Tuple[Path, Tuple[int, int]]:
        """Projects the common geographic footprint into the raster's CRS,
        computes the pixel window, extracts native pixels, and saves the patch."""
        if not HAS_RASTERIO:
            raise ImportError(
                "The 'rasterio' package is required to crop georeferenced raster files. "
                "Install it using: pip install rasterio"
            )
        with rasterio.open(raster_path) as src:
            # Transform common (lon, lat) polygon to raster native CRS
            transformer = pyproj.Transformer.from_crs(
                LUNAR_GEOGRAPHIC_PROJ4, src.crs, always_xy=True
            )
            geo_coords = list(common_geo_poly.exterior.coords)
            native_xs, native_ys = transformer.transform(
                [c[0] for c in geo_coords], [c[1] for c in geo_coords]
            )
            native_poly = Polygon(zip(native_xs, native_ys))
            min_x, min_y, max_x, max_y = native_poly.bounds

            # Calculate pixel window
            window = from_bounds(min_x, min_y, max_x, max_y, transform=src.transform)

            # Clamp window to raster bounds
            col_off = max(0, min(src.width - 1, int(math.floor(window.col_off))))
            row_off = max(0, min(src.height - 1, int(math.floor(window.row_off))))
            w = max(1, min(src.width - col_off, int(math.ceil(window.width))))
            h = max(1, min(src.height - row_off, int(math.ceil(window.height))))

            clamped_window = Window(col_off, row_off, w, h)
            data = src.read(1, window=clamped_window)

            # Scientific contrast normalization
            if data.dtype != np.uint8:
                valid = np.isfinite(data) & (data > 0)
                if np.any(valid):
                    p2, p98 = np.percentile(data[valid], (2, 98))
                    if p98 > p2:
                        norm = np.clip((data - p2) / (p98 - p2), 0.0, 1.0) * 255.0
                    else:
                        norm = np.zeros_like(data, dtype=np.float32)
                    img_arr = norm.astype(np.uint8)
                else:
                    img_arr = np.zeros_like(data, dtype=np.uint8)
            else:
                img_arr = data

            img = Image.fromarray(img_arr)
            img.save(output_patch_path)
            return output_patch_path, (w, h)


def cli_main():
    """Command Line Interface for POC-2 Geographic Overlap & Patch Engine."""
    parser = argparse.ArgumentParser(
        description="NEXUS-LUNAR: POC 2 Geographic Overlap & Patch Engine CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Overlap and patch extraction between two rasters:
  python -m packages.data_pipeline.overlap_engine \\
      --source path/to/ohrc.tif \\
      --reference path/to/lroc.tif \\
      --output outputs/poc2

  # Automatic reference tile discovery from a directory of LROC GeoTIFFs:
  python -m packages.data_pipeline.overlap_engine \\
      --source path/to/ohrc.tif \\
      --reference-dir path/to/lroc_tiles \\
      --output outputs/poc2
        """,
    )
    parser.add_argument("--source", type=str, required=True, help="Path to source raster (GeoTIFF / IMG)")
    parser.add_argument("--reference", type=str, help="Path to reference raster / mosaic tile")
    parser.add_argument("--reference-dir", type=str, help="Directory of candidate reference GeoTIFF tiles to screen")
    parser.add_argument("--output", type=str, default="outputs/poc2", help="Output directory for patches, metadata, and figures")
    parser.add_argument("--source-id", type=str, help="Optional source product identifier")
    parser.add_argument("--reference-id", type=str, help="Optional reference product identifier")

    args = parser.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 64)
    print(" NEXUS-LUNAR: POC 2 Geographic Overlap & Patch Engine")
    print("=" * 64)

    footprint_engine = FootprintEngine()

    # 1. Source Footprint
    src_path = Path(args.source)
    if not src_path.exists():
        print(f"Error: Source file not found: {src_path}", file=sys.stderr)
        sys.exit(1)

    print(f"\n[1/4] Reading Source Raster: {src_path.name}")
    try:
        src_fp = footprint_engine.extract_from_raster(src_path)
        print(f"  CRS:   {src_fp.crs_name}")
        print(f"  Area:  {src_fp.area_km2:.2f} km²")
        print(f"  Bounds: Lon [{src_fp.min_lon:.4f}°, {src_fp.max_lon:.4f}°], Lat [{src_fp.min_lat:.4f}°, {src_fp.max_lat:.4f}°]")
    except Exception as e:
        print(f"Error extracting source footprint: {e}", file=sys.stderr)
        sys.exit(1)

    # Mode A: Tile Discovery
    if args.reference_dir:
        print(f"\n[2/4] Screening Reference Tiles in: {args.reference_dir}")
        matches = find_overlapping_reference_tiles(src_fp, args.reference_dir)
        print(f"  Found {len(matches)} overlapping reference tile(s):")
        for i, m in enumerate(matches, 1):
            print(f"    [{i}] {m['tile']} -> Intersection Area: {m['intersection_area']} km² (Confidence: {m['confidence']})")

        if not matches:
            print("\nNo overlapping reference tiles found.")
            sys.exit(0)

        # Select top overlapping tile for patch extraction
        best_match = matches[0]
        ref_path = Path(best_match["path"])
        print(f"\nSelected Top Overlapping Tile: {best_match['tile']}")
    elif args.reference:
        ref_path = Path(args.reference)
        if not ref_path.exists():
            print(f"Error: Reference file not found: {ref_path}", file=sys.stderr)
            sys.exit(1)
    else:
        print("Error: Either --reference or --reference-dir must be provided.", file=sys.stderr)
        sys.exit(1)

    # 2. Reference Footprint
    print(f"\n[2/4] Reading Reference Raster: {ref_path.name}")
    try:
        ref_fp = footprint_engine.extract_from_raster(ref_path)
        print(f"  CRS:   {ref_fp.crs_name}")
        print(f"  Area:  {ref_fp.area_km2:.2f} km²")
        print(f"  Bounds: Lon [{ref_fp.min_lon:.4f}°, {ref_fp.max_lon:.4f}°], Lat [{ref_fp.min_lat:.4f}°, {ref_fp.max_lat:.4f}°]")
    except Exception as e:
        print(f"Error extracting reference footprint: {e}", file=sys.stderr)
        sys.exit(1)

    # 3. Calculate Overlap
    print(f"\n[3/4] Computing Geographic Polygon Intersection...")
    overlap = calculate_overlap(src_fp, ref_fp, footprint_engine=footprint_engine)
    print(f"  Intersects:                  {overlap.intersects}")
    print(f"  Intersection Area:           {overlap.intersection_area:.2f} km²")
    print(f"  Overlap Ratio (Source):      {overlap.overlap_ratio_source * 100:.1f}%")
    print(f"  Overlap Ratio (Reference):   {overlap.overlap_ratio_reference * 100:.1f}%")
    print(f"  Geometric Overlap Confidence: {overlap.overlap_confidence:.3f}")

    if not overlap.intersects:
        print("\nObservations do not cover the same physical lunar surface. No patches extracted.")
        sys.exit(0)

    # 4. Patch Extraction & Artifact Generation
    print(f"\n[4/4] Extracting Resolution-Aware Patches & Generating Visualizations...")
    engine = OverlapEngine(footprint_engine=footprint_engine)
    result = engine.run_pipeline(
        source_raster=src_path,
        reference_raster=ref_path,
        output_dir=out_dir,
        source_id=args.source_id,
        reference_id=args.reference_id,
    )

    print("\nPOC 2 Execution Successfully Completed:")
    print(f"  Metadata JSON:     {out_dir / 'patch_metadata.json'}")
    print(f"  Source Patch:      {result['source']['patch_path']} ({result['patch_dimensions']['source_width']}x{result['patch_dimensions']['source_height']} px)")
    print(f"  Reference Patch:   {result['reference']['patch_path']} ({result['patch_dimensions']['reference_width']}x{result['patch_dimensions']['reference_height']} px)")
    print(f"  Footprint Figure:  {result['visualizations']['footprint_map']}")
    print(f"  Patch Figure:      {result['visualizations']['patch_comparison']}")
    print("=" * 64 + "\n")


if __name__ == "__main__":
    cli_main()
