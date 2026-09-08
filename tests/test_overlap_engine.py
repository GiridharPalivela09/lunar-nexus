"""Comprehensive Unit & Integration Test Suite for POC-2: Geographic Overlap & Patch Engine."""

import os
import shutil
import tempfile
import json
import numpy as np
import pytest
from shapely.geometry import Polygon, box
from shapely.validation import make_valid
import rasterio
from rasterio.transform import from_origin
import pyproj

from packages.data_pipeline import (
    FootprintEngine,
    FootprintResult,
    OverlapEngine,
    OverlapAnalysisResult,
    calculate_overlap,
    find_overlapping_reference_tiles,
    LUNAR_GEOGRAPHIC_PROJ4,
    LUNAR_SOUTH_POLE_STEREO_PROJ4,
)


@pytest.fixture
def temp_workspace():
    d = tempfile.mkdtemp(prefix="nexus_poc2_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def create_synthetic_geotiff(
    path: str,
    top_left_x: float,
    top_left_y: float,
    pixel_size: float,
    width: int,
    height: int,
    crs_proj4: str = LUNAR_SOUTH_POLE_STEREO_PROJ4,
    value: int = 120,
):
    """Helper to create a valid georeferenced Lunar GeoTIFF."""
    transform = from_origin(top_left_x, top_left_y, pixel_size, pixel_size)
    crs_obj = rasterio.crs.CRS.from_string(crs_proj4)

    # Generate synthetic crater-like lunar pattern
    y, x = np.ogrid[:height, :width]
    cx, cy = width // 2, height // 2
    r2 = (x - cx) ** 2 + (y - cy) ** 2
    data = (value + 50 * np.sin(r2 / 100.0)).clip(10, 240).astype(np.uint8)

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype=np.uint8,
        crs=crs_obj,
        transform=transform,
    ) as dst:
        dst.write(data, 1)


# =========================================================================
# 1. Complete Overlap Test
# =========================================================================
def test_complete_overlap():
    engine = FootprintEngine()
    # Footprint A contains Footprint B
    poly_a = box(10.0, -85.0, 15.0, -80.0)
    poly_b = box(11.0, -84.0, 14.0, -81.0)

    overlap = calculate_overlap(poly_a, poly_b, footprint_engine=engine)
    assert overlap.intersects is True
    assert overlap.intersection_area > 0.0
    # Overlap ratio of smaller footprint B should be ~1.0 (complete containment)
    assert overlap.overlap_ratio_reference == pytest.approx(1.0, abs=0.01)
    assert 0.0 < overlap.overlap_ratio_source < 1.0
    assert overlap.overlap_confidence > 0.5


# =========================================================================
# 2. Partial Overlap Test
# =========================================================================
def test_partial_overlap():
    engine = FootprintEngine()
    poly_a = box(10.0, -85.0, 20.0, -80.0)
    poly_b = box(15.0, -85.0, 25.0, -80.0)

    overlap = calculate_overlap(poly_a, poly_b, footprint_engine=engine)
    assert overlap.intersects is True
    assert overlap.intersection_polygon is not None
    # Half of each polygon overlaps
    assert overlap.overlap_ratio_source == pytest.approx(0.5, abs=0.05)
    assert overlap.overlap_ratio_reference == pytest.approx(0.5, abs=0.05)
    assert overlap.overlap_confidence > 0.3


# =========================================================================
# 3. No Overlap (Disjoint) Test
# =========================================================================
def test_no_overlap():
    engine = FootprintEngine()
    poly_south_pole = box(10.0, -85.0, 15.0, -80.0)
    poly_equator = box(10.0, 0.0, 15.0, 5.0)

    overlap = calculate_overlap(poly_south_pole, poly_equator, footprint_engine=engine)
    assert overlap.intersects is False
    assert overlap.intersection_polygon is None
    assert overlap.intersection_area == 0.0
    assert overlap.overlap_ratio_source == 0.0
    assert overlap.overlap_ratio_reference == 0.0
    assert overlap.overlap_confidence == 0.0


# =========================================================================
# 4. Different CRS Handling Test
# =========================================================================
def test_different_crs_handling(temp_workspace):
    engine = FootprintEngine()

    # Create a raster in Polar Stereographic projection
    ps_tif = os.path.join(temp_workspace, "polar_stereo.tif")
    create_synthetic_geotiff(
        ps_tif,
        top_left_x=10000.0,
        top_left_y=-20000.0,
        pixel_size=1.0,
        width=500,
        height=500,
        crs_proj4=LUNAR_SOUTH_POLE_STEREO_PROJ4,
    )

    fp = engine.extract_from_raster(ps_tif)
    assert fp.is_valid is True
    assert fp.area_km2 > 0.0
    # Coordinates should be converted to lunar selenographic (lon, lat)
    min_lon, min_lat, max_lon, max_lat = fp.bounds
    assert -90.0 <= min_lat <= -80.0  # Must be in southern lunar polar latitudes
    assert -180.0 <= min_lon <= 180.0


# =========================================================================
# 5. Invalid Polygon Handling & Repair
# =========================================================================
def test_invalid_polygon_handling():
    engine = FootprintEngine()
    # Create a self-intersecting "bowtie" polygon
    bowtie_coords = [(0.0, 0.0), (2.0, 2.0), (0.0, 2.0), (2.0, 0.0), (0.0, 0.0)]
    invalid_poly = Polygon(bowtie_coords)
    assert not invalid_poly.is_valid

    # FootprintEngine and calculate_overlap must repair it safely
    valid_box = box(0.5, 0.5, 1.5, 1.5)
    overlap = calculate_overlap(invalid_poly, valid_box, footprint_engine=engine)
    assert overlap.intersects is True
    assert overlap.intersection_area > 0.0


# =========================================================================
# 6. Different Resolutions & GSD Preservation Test
# =========================================================================
def test_different_resolutions(temp_workspace):
    # OHRC at 0.25 m/pixel
    ohrc_path = os.path.join(temp_workspace, "ohrc_sim.tif")
    create_synthetic_geotiff(
        ohrc_path,
        top_left_x=50000.0,
        top_left_y=-100000.0,
        pixel_size=0.25,
        width=800,
        height=800,
        value=150,
    )

    # LROC at 1.0 m/pixel over the identical ground region (800 px @ 0.25m = 200m = 200 px @ 1.0m)
    lroc_path = os.path.join(temp_workspace, "lroc_sim.tif")
    create_synthetic_geotiff(
        lroc_path,
        top_left_x=50000.0,
        top_left_y=-100000.0,
        pixel_size=1.0,
        width=200,
        height=200,
        value=120,
    )

    engine = OverlapEngine()
    out_dir = os.path.join(temp_workspace, "out_res")
    result = engine.run_pipeline(
        source_raster=ohrc_path,
        reference_raster=lroc_path,
        output_dir=out_dir,
        source_res_m=0.25,
        ref_res_m=1.0,
    )

    assert result["overlap"]["intersects"] is True
    # The source patch dimensions must be ~4x larger in pixels than the reference patch
    src_w = result["patch_dimensions"]["source_width"]
    ref_w = result["patch_dimensions"]["reference_width"]
    ratio = src_w / ref_w
    assert ratio == pytest.approx(4.0, abs=0.2)


# =========================================================================
# 7. Patch Extraction from Geographic Intersection
# =========================================================================
def test_patch_extraction_from_intersection(temp_workspace):
    # Raster 1: [0 to 300m X, 0 to -300m Y]
    r1_path = os.path.join(temp_workspace, "r1.tif")
    create_synthetic_geotiff(r1_path, top_left_x=0.0, top_left_y=0.0, pixel_size=1.0, width=300, height=300)

    # Raster 2 partially overlaps: [150m to 450m X, -150m to -450m Y]
    r2_path = os.path.join(temp_workspace, "r2.tif")
    create_synthetic_geotiff(r2_path, top_left_x=150.0, top_left_y=-150.0, pixel_size=1.0, width=300, height=300)

    engine = OverlapEngine()
    out_dir = os.path.join(temp_workspace, "out_patches")
    result = engine.run_pipeline(source_raster=r1_path, reference_raster=r2_path, output_dir=out_dir)

    assert result["overlap"]["intersects"] is True
    assert os.path.exists(result["source"]["patch_path"])
    assert os.path.exists(result["reference"]["patch_path"])

    # Verify both extracted patches exist and have positive dimensions
    from PIL import Image as PILImage
    src_img = PILImage.open(result["source"]["patch_path"])
    assert src_img.width > 0 and src_img.height > 0


# =========================================================================
# 8. Automatic Reference Tile Discovery
# =========================================================================
def test_automatic_reference_tile_discovery(temp_workspace):
    tiles_dir = os.path.join(temp_workspace, "lroc_tiles")
    os.makedirs(tiles_dir, exist_ok=True)

    # Source raster: X [10000, 10200], Y [-50200, -50000]
    src_path = os.path.join(temp_workspace, "source_ohrc.tif")
    create_synthetic_geotiff(src_path, top_left_x=10000.0, top_left_y=-50000.0, pixel_size=0.5, width=400, height=400)

    # Candidate Tile 1: Overlaps significantly (X: [9950, 10250], Y: [-50250, -49950])
    t1_path = os.path.join(tiles_dir, "tile_high_overlap.tif")
    create_synthetic_geotiff(t1_path, top_left_x=9950.0, top_left_y=-49950.0, pixel_size=1.0, width=300, height=300)

    # Candidate Tile 2: Overlaps partially (X: [10100, 10180], Y: [-50180, -50100])
    t2_path = os.path.join(tiles_dir, "tile_partial_overlap.tif")
    create_synthetic_geotiff(t2_path, top_left_x=10100.0, top_left_y=-50100.0, pixel_size=1.0, width=80, height=80)

    # Candidate Tile 3: Completely disjoint (like P878S3375 in real data)
    t3_path = os.path.join(tiles_dir, "tile_no_overlap_P878S3375.tif")
    create_synthetic_geotiff(t3_path, top_left_x=500000.0, top_left_y=-500000.0, pixel_size=1.0, width=500, height=500)

    matches = find_overlapping_reference_tiles(src_path, tiles_dir)

    # Candidate 3 must NOT be in matches
    matched_names = [m["tile"] for m in matches]
    assert "tile_high_overlap.tif" in matched_names
    assert "tile_partial_overlap.tif" in matched_names
    assert "tile_no_overlap_P878S3375.tif" not in matched_names

    # The matches must be sorted descending by intersection area
    assert matches[0]["tile"] == "tile_high_overlap.tif"
    assert matches[0]["intersection_area"] >= matches[1]["intersection_area"]


# =========================================================================
# 9. Metadata JSON Generation Schema Test
# =========================================================================
def test_metadata_json_generation(temp_workspace):
    r1_path = os.path.join(temp_workspace, "ohrc.tif")
    create_synthetic_geotiff(r1_path, top_left_x=20000.0, top_left_y=-80000.0, pixel_size=0.25, width=400, height=400)

    r2_path = os.path.join(temp_workspace, "lroc.tif")
    create_synthetic_geotiff(r2_path, top_left_x=20000.0, top_left_y=-80000.0, pixel_size=1.0, width=100, height=100)

    engine = OverlapEngine()
    out_dir = os.path.join(temp_workspace, "meta_test")
    res = engine.run_pipeline(
        source_raster=r1_path,
        reference_raster=r2_path,
        output_dir=out_dir,
        source_id="CH2_OHRC_SAMPLE",
        reference_id="LROC_NAC_SAMPLE",
    )

    json_path = os.path.join(out_dir, "patch_metadata.json")
    assert os.path.exists(json_path)

    with open(json_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    # Validate exact required keys from user specification
    assert "source" in meta
    assert meta["source"]["id"] == "CH2_OHRC_SAMPLE"
    assert "resolution_m_per_pixel" in meta["source"]
    assert "crs" in meta["source"]
    assert "patch_path" in meta["source"]

    assert "reference" in meta
    assert meta["reference"]["id"] == "LROC_NAC_SAMPLE"
    assert "resolution_m_per_pixel" in meta["reference"]
    assert "crs" in meta["reference"]
    assert "patch_path" in meta["reference"]

    assert "overlap" in meta
    assert meta["overlap"]["intersects"] is True
    assert "intersection_area" in meta["overlap"]
    assert "overlap_ratio_source" in meta["overlap"]
    assert "overlap_ratio_reference" in meta["overlap"]
    assert "confidence" in meta["overlap"]

    assert "common_ground_footprint" in meta
    assert "geometry" in meta["common_ground_footprint"]
    assert "bounds" in meta["common_ground_footprint"]
    bounds = meta["common_ground_footprint"]["bounds"]
    for k in ("min_lon", "min_lat", "max_lon", "max_lat"):
        assert k in bounds

    assert "patch_dimensions" in meta
    for k in ("source_width", "source_height", "reference_width", "reference_height"):
        assert k in meta["patch_dimensions"]
        assert meta["patch_dimensions"][k] > 0
