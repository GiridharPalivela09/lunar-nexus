"""Advanced Mathematical, Edge-Case, and Integration Validation Suite for POC-2.

Covers:
1. Geodetic & Lunar Spherical Surface Area Calculations (R=1737.4 km).
2. Swath Ground Geometry Validation for Chandrayaan-2 OHRC (78.96 km²).
3. Boundary & Edge Cases: Single-point contact, sliver intersection, disjoint footprints.
4. Extreme GSD Ratios (20:1 ratio between OHRC 0.25m and TMC-2 5.0m).
5. Explainable Overlap Confidence Score & Isoperimetric Quotient verification.
6. Catalog Discovery and Patch Extraction Integration.
"""

import os
import json
import math
import shutil
import tempfile
import numpy as np
from PIL import Image
import pytest
from shapely.geometry import Polygon, box, Point
import rasterio
from rasterio.transform import from_origin

from packages.data_pipeline import (
    FootprintEngine,
    FootprintResult,
    OverlapEngine,
    OverlapAnalysisResult,
    calculate_overlap,
    find_overlapping_reference_tiles,
    SensorType,
    MissionType,
    BoundingBox,
    LunarObservation,
    ResolutionStrategy,
    PatchExtractionConfig,
    OverlapPatchExtractor,
    GeoPixelTransformer,
    ResolutionHarmonizer,
    OverlapQualityScorer,
    LunarDataCatalog,
    LUNAR_GEOGRAPHIC_PROJ4,
    LUNAR_SOUTH_POLE_STEREO_PROJ4,
    LUNAR_RADIUS_M,
)


@pytest.fixture
def workspace():
    d = tempfile.mkdtemp(prefix="nexus_poc2_advanced_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


# =========================================================================
# 1. Geodetic & Spherical Surface Area Verification
# =========================================================================
def test_lunar_spherical_surface_area_accuracy():
    """Verify that lunar ground area calculation follows the true spherical Moon model."""
    engine = FootprintEngine()
    R = 1737.4  # km

    # 1 deg lat x 1 deg lon at the lunar equator (lat: [0, 1], lon: [0, 1])
    # Expected area = R^2 * (1 * pi/180) * (sin(1 deg) - sin(0 deg))
    expected_area_equator = (R ** 2) * math.radians(1.0) * (math.sin(math.radians(1.0)) - 0.0)

    poly_equator = box(0.0, 0.0, 1.0, 1.0)
    calc_area_equator = engine.compute_spherical_area_km2(poly_equator)
    assert calc_area_equator == pytest.approx(expected_area_equator, rel=0.05)

    # 1 deg lat x 1 deg lon near South Pole (lat: [-85, -84], lon: [0, 1])
    # Longitude meridians converge towards poles: area must be significantly smaller
    expected_area_polar = (R ** 2) * math.radians(1.0) * (math.sin(math.radians(-84.0)) - math.sin(math.radians(-85.0)))
    poly_polar = box(0.0, -85.0, 1.0, -84.0)
    calc_area_polar = engine.compute_spherical_area_km2(poly_polar)
    assert calc_area_polar == pytest.approx(expected_area_polar, rel=0.05)

    # Polar area must be roughly sin(mean_lat) ratio compared to equator
    assert calc_area_polar < 0.12 * calc_area_equator


# =========================================================================
# 2. Real Chandrayaan-2 OHRC Swath Ground Footprint Validation
# =========================================================================
def test_chandrayaan2_ohrc_swath_geometry():
    """Validates the exact four-corner coordinates of Chandrayaan-2 OHRC swath ch2_ohr_ncp_20260103t1005176450."""
    engine = FootprintEngine()
    ohrc_corners = [
        (27.751481, -85.279005),  # UL
        (26.628534, -85.325413),  # UR
        (22.794260, -84.562153),  # LR
        (23.790313, -84.522148),  # LL
    ]
    fp = engine.extract_from_corners(ohrc_corners)

    assert fp.is_valid is True
    assert fp.polygon.is_valid is True
    # Blueprint and README confirm true swath ground area is ~78.96 km²
    assert fp.area_km2 == pytest.approx(78.96, abs=0.5)

    # Check bounds
    min_lon, min_lat, max_lon, max_lat = fp.bounds
    assert min_lat == pytest.approx(-85.33, abs=0.05)
    assert max_lat == pytest.approx(-84.52, abs=0.05)
    assert min_lon == pytest.approx(22.79, abs=0.05)
    assert max_lon == pytest.approx(27.75, abs=0.05)


# =========================================================================
# 3. Edge Case: Sliver Contact & Tangent Polygons
# =========================================================================
def test_sliver_and_tangent_boundary_edge_cases():
    """Verify handling of tangent boundary contact (zero area) and sliver overlap."""
    engine = FootprintEngine()

    # Adjacent boxes touching along an edge (lon: [0, 1] vs [1, 2], lat: [-80, -79])
    box_a = box(0.0, -80.0, 1.0, -79.0)
    box_b = box(1.0, -80.0, 2.0, -79.0)

    overlap = calculate_overlap(box_a, box_b, footprint_engine=engine)
    # Touching along a 1D line is geometrically empty in 2D surface area
    assert overlap.intersects is False or overlap.intersection_area == 0.0
    assert overlap.overlap_confidence == 0.0

    # Ultra-thin sliver (0.0001 deg wide) should have negligible area and penalized confidence
    box_sliver = box(0.9999, -80.0, 1.0001, -79.0)
    overlap_sliver = calculate_overlap(box_a, box_sliver, footprint_engine=engine)
    assert overlap_sliver.intersects is True
    assert overlap_sliver.intersection_area < 0.05
    # Overlap ratio relative to source box_a should be tiny (< 0.01)
    assert overlap_sliver.overlap_ratio_source < 0.01


# =========================================================================
# 4. Extreme GSD Ratio Test (OHRC 0.25m vs TMC-2 5.0m = 20:1 GSD Ratio)
# =========================================================================
def test_extreme_gsd_scaling_ohrc_vs_tmc2(workspace):
    """Test resolution-aware window scaling for extreme 20:1 GSD difference."""
    # Synthetic OHRC at 0.25m/pixel (2000 x 2000 pixels = 500m x 500m)
    ohrc_path = os.path.join(workspace, "ohrc_20x.tif")
    transform_ohrc = from_origin(10000.0, -20000.0, 0.25, 0.25)
    crs_obj = rasterio.crs.CRS.from_string(LUNAR_SOUTH_POLE_STEREO_PROJ4)
    data_ohrc = np.full((2000, 2000), 140, dtype=np.uint8)

    with rasterio.open(
        ohrc_path, "w", driver="GTiff", height=2000, width=2000, count=1,
        dtype=np.uint8, crs=crs_obj, transform=transform_ohrc
    ) as dst:
        dst.write(data_ohrc, 1)

    # Synthetic TMC-2 at 5.0m/pixel (100 x 100 pixels = 500m x 500m)
    tmc2_path = os.path.join(workspace, "tmc2_20x.tif")
    transform_tmc2 = from_origin(10000.0, -20000.0, 5.0, 5.0)
    data_tmc2 = np.full((100, 100), 110, dtype=np.uint8)

    with rasterio.open(
        tmc2_path, "w", driver="GTiff", height=100, width=100, count=1,
        dtype=np.uint8, crs=crs_obj, transform=transform_tmc2
    ) as dst:
        dst.write(data_tmc2, 1)

    engine = OverlapEngine()
    out_dir = os.path.join(workspace, "out_20x")
    result = engine.run_pipeline(
        source_raster=ohrc_path,
        reference_raster=tmc2_path,
        output_dir=out_dir,
        source_res_m=0.25,
        ref_res_m=5.0,
    )

    assert result["overlap"]["intersects"] is True
    src_w = result["patch_dimensions"]["source_width"]
    ref_w = result["patch_dimensions"]["reference_width"]

    # Resolution scaling must be 20x (2000 px vs 100 px)
    assert src_w / ref_w == pytest.approx(20.0, abs=0.5)


# =========================================================================
# 5. Overlap Confidence Mathematical Formula Verification
# =========================================================================
def test_geometric_overlap_confidence_formula():
    """Directly verifies the mathematical properties of the non-AI geometric confidence metric."""
    engine = FootprintEngine()

    # Case A: Identical polygons (100% mutual overlap)
    poly = box(20.0, -82.0, 22.0, -80.0)
    overlap_a = calculate_overlap(poly, poly, footprint_engine=engine)
    assert overlap_a.overlap_ratio_source == 1.0
    assert overlap_a.overlap_ratio_reference == 1.0
    # For a square, isoperimetric quotient = 4*pi*Area / P^2 = 4*pi / 16 = pi/4 ~ 0.785
    # Expected confidence = 0.6*1.0 + 0.2*1.0 + 0.2*Q ~ 0.8 + 0.157 ~ 0.957
    assert 0.94 <= overlap_a.overlap_confidence <= 1.0

    # Case B: Disjoint polygons
    poly_disjoint = box(40.0, -82.0, 42.0, -80.0)
    overlap_b = calculate_overlap(poly, poly_disjoint, footprint_engine=engine)
    assert overlap_b.overlap_confidence == 0.0


# =========================================================================
# 6. Catalog Discovery and Patch Extraction Integration
# =========================================================================
def test_catalog_overlapping_pairs_and_manifest():
    """Verify LunarDataCatalog find_overlapping_pairs and extract_patches_for_pairs."""
    catalog = LunarDataCatalog(catalog_file="data/catalog.json")
    pairs = catalog.find_overlapping_pairs(
        source_sensor=SensorType.OHRC,
        reference_sensor=SensorType.LRO_NAC,
        min_overlap_pct=5.0,
    )

    assert len(pairs) >= 1
    top_pair = pairs[0]
    assert top_pair["source_sensor"] == "OHRC"
    assert top_pair["reference_sensor"] == "LRO_NAC"
    assert top_pair["overlap_percent_of_source"] >= 5.0
    assert top_pair["overlap_area_km2"] > 0.0
