"""Unit and integration tests for POC 2: Geographic Overlap & Patch Engine."""

import os
import shutil
import tempfile
import numpy as np
from PIL import Image
import pytest

from packages.data_pipeline import (
    SensorType,
    MissionType,
    BoundingBox,
    LunarObservation,
    ResolutionStrategy,
    PixelBox,
    PatchExtractionConfig,
    GeoPixelTransformer,
    ResolutionHarmonizer,
    OverlapQualityScorer,
    OverlapPatchExtractor,
)


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp(prefix="nexus_test_patches_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def test_geo_pixel_transformer():
    # Lunar region: lat [-85.0, -84.0], lon [10.0, 12.0]
    bbox = BoundingBox(min_lat=-85.0, max_lat=-84.0, min_lon=10.0, max_lon=12.0)
    width, height = 1000, 500
    transformer = GeoPixelTransformer(bbox, width, height)

    # Top-Left should be (0, 0) -> (max_lat, min_lon)
    px, py = transformer.geo_to_pixel(lat=-84.0, lon=10.0)
    assert px == pytest.approx(0.0, abs=1e-3)
    assert py == pytest.approx(0.0, abs=1e-3)

    # Bottom-Right should be (width, height) -> (min_lat, max_lon)
    px, py = transformer.geo_to_pixel(lat=-85.0, lon=12.0)
    assert px == pytest.approx(1000.0, abs=1e-3)
    assert py == pytest.approx(500.0, abs=1e-3)

    # Center point
    center_lat, center_lon = bbox.center
    px, py = transformer.geo_to_pixel(center_lat, center_lon)
    assert px == pytest.approx(500.0, abs=1e-3)
    assert py == pytest.approx(250.0, abs=1e-3)

    # Round trip test
    lat_orig, lon_orig = -84.4, 11.2
    px, py = transformer.geo_to_pixel(lat_orig, lon_orig)
    lat_back, lon_back = transformer.pixel_to_geo(px, py)
    assert lat_back == pytest.approx(lat_orig, abs=1e-5)
    assert lon_back == pytest.approx(lon_orig, abs=1e-5)

    # Sub-bounding box to pixel box
    sub_bbox = BoundingBox(min_lat=-84.8, max_lat=-84.2, min_lon=10.5, max_lon=11.5)
    pbox = transformer.bbox_to_pixel_box(sub_bbox)
    assert pbox.x == 250
    assert pbox.y == 100
    assert pbox.width == 500
    assert pbox.height == 300


def test_resolution_harmonizer():
    src_gsd = 0.25   # OHRC
    ref_gsd = 0.50   # LRO NAC

    # Match coarser should pick max(0.25, 0.50) = 0.50
    eff_coarser = ResolutionHarmonizer.calculate_effective_gsd(
        src_gsd, ref_gsd, ResolutionStrategy.MATCH_COARSER
    )
    assert eff_coarser == 0.50

    # Match finer should pick min(0.25, 0.50) = 0.25
    eff_finer = ResolutionHarmonizer.calculate_effective_gsd(
        src_gsd, ref_gsd, ResolutionStrategy.MATCH_FINER
    )
    assert eff_finer == 0.25

    # Resample test: downsample 200x200 image at 0.25m to 0.50m -> 100x100
    dummy_img = Image.fromarray(np.zeros((200, 200), dtype=np.uint8))
    resampled = ResolutionHarmonizer.resample_patch(dummy_img, current_gsd=0.25, target_gsd=0.50)
    assert resampled.size == (100, 100)


def test_overlap_quality_scorer():
    sub_bbox = BoundingBox(min_lat=-85.0, max_lat=-84.0, min_lon=10.0, max_lon=12.0)
    area = OverlapQualityScorer.compute_ground_area_km2(sub_bbox)
    assert area > 0.0

    # 100% overlap, identical resolutions, 0 deg illumination diff -> ~1.0
    score_perfect = OverlapQualityScorer.score(
        overlap_pct=100.0, source_gsd=0.5, reference_gsd=0.5, sun_incidence_diff_deg=0.0
    )
    assert score_perfect == pytest.approx(1.0, abs=0.05)

    # Low overlap, high sun diff -> lower score
    score_low = OverlapQualityScorer.score(
        overlap_pct=5.0, source_gsd=0.25, reference_gsd=5.0, sun_incidence_diff_deg=50.0
    )
    assert 0.0 <= score_low < score_perfect


def test_geographic_intersection():
    extractor = OverlapPatchExtractor()

    box_a = BoundingBox(min_lat=-85.0, max_lat=-83.0, min_lon=10.0, max_lon=20.0)
    box_b = BoundingBox(min_lat=-84.0, max_lat=-82.0, min_lon=15.0, max_lon=25.0)

    inter_box, pct_a, pct_b = extractor.find_geographic_intersection(box_a, box_b)
    assert inter_box is not None
    assert inter_box.min_lat == -84.0
    assert inter_box.max_lat == -83.0
    assert inter_box.min_lon == 15.0
    assert inter_box.max_lon == 20.0
    assert pct_a == pytest.approx(25.0, abs=1.0)
    assert pct_b == pytest.approx(25.0, abs=1.0)

    # Disjoint boxes
    box_disjoint = BoundingBox(min_lat=0.0, max_lat=5.0, min_lon=0.0, max_lon=5.0)
    inter_none, pct_src, pct_ref = extractor.find_geographic_intersection(box_a, box_disjoint)
    assert inter_none is None
    assert pct_src == 0.0


def test_end_to_end_patch_extraction(temp_dir):
    # Setup two synthetic overlapping observations
    bbox_src = BoundingBox(min_lat=-85.0, max_lat=-84.0, min_lon=10.0, max_lon=12.0)
    bbox_ref = BoundingBox(min_lat=-84.8, max_lat=-83.8, min_lon=10.5, max_lon=12.5)

    # Images
    src_img = Image.fromarray(np.random.randint(50, 200, (400, 400), dtype=np.uint8))
    ref_img = Image.fromarray(np.random.randint(50, 200, (200, 200), dtype=np.uint8))

    src_path = os.path.join(temp_dir, "src.png")
    ref_path = os.path.join(temp_dir, "ref.png")
    src_img.save(src_path)
    ref_img.save(ref_path)

    obs_src = LunarObservation(
        product_id="TEST_OHRC_001",
        mission=MissionType.CHANDRAYAAN2,
        sensor=SensorType.OHRC,
        spatial_resolution_m=0.25,
        bbox=bbox_src,
        primary_image_path=src_path,
    )
    obs_ref = LunarObservation(
        product_id="TEST_LRO_001",
        mission=MissionType.LRO,
        sensor=SensorType.LRO_NAC,
        spatial_resolution_m=0.50,
        bbox=bbox_ref,
        primary_image_path=ref_path,
    )

    config = PatchExtractionConfig(
        patch_size=64,
        stride=32,
        min_overlap_pct=5.0,
        resolution_strategy=ResolutionStrategy.MATCH_COARSER,
    )
    extractor = OverlapPatchExtractor(config=config)

    manifest = extractor.extract_patch_pairs(
        source_obs=obs_src,
        reference_obs=obs_ref,
        output_dir=temp_dir,
    )

    assert manifest.total_patches > 0
    assert len(manifest.patches) == manifest.total_patches
    assert manifest.intersection_area_km2 > 0

    # Verify first extracted patch pair files
    first_pair = manifest.patches[0]
    assert os.path.exists(first_pair.source_patch_path)
    assert os.path.exists(first_pair.reference_patch_path)

    # Check that patches match the requested patch size
    p_src = Image.open(first_pair.source_patch_path)
    p_ref = Image.open(first_pair.reference_patch_path)
    assert p_src.size == (64, 64)
    assert p_ref.size == (64, 64)


def test_rotated_polygon_intersection():
    extractor = OverlapPatchExtractor()

    # Create two rotated quadrilaterals (tilted swaths)
    poly_src = [(10.0, -84.0), (12.0, -83.0), (13.0, -85.0), (11.0, -86.0), (10.0, -84.0)]
    poly_ref = [(11.0, -83.5), (13.0, -83.0), (14.0, -85.5), (12.0, -86.0), (11.0, -83.5)]

    bbox_src = BoundingBox(min_lat=-86.0, max_lat=-83.0, min_lon=10.0, max_lon=13.0)
    bbox_ref = BoundingBox(min_lat=-86.0, max_lat=-83.0, min_lon=11.0, max_lon=14.0)

    inter_box, pct_src, pct_ref = extractor.find_geographic_intersection(
        source_bbox=bbox_src,
        ref_bbox=bbox_ref,
        source_polygon=poly_src,
        ref_polygon=poly_ref,
    )

    assert inter_box is not None
    assert pct_src > 0.0
    assert pct_ref > 0.0


def test_16bit_scientific_dynamic_range_stretching(temp_dir):
    extractor = OverlapPatchExtractor()

    # Create raw 16-bit array in typical planetary sensor range [1200, 3800]
    raw_16bit = np.random.randint(1200, 3800, size=(100, 100), dtype=np.uint16)
    img_16 = Image.fromarray(raw_16bit)
    tif_path = os.path.join(temp_dir, "raw_16bit.png")
    img_16.save(tif_path)

    bbox = BoundingBox(min_lat=-85.0, max_lat=-84.0, min_lon=10.0, max_lon=11.0)
    obs = LunarObservation(
        product_id="TEST_16BIT_001",
        mission=MissionType.CHANDRAYAAN2,
        sensor=SensorType.OHRC,
        spatial_resolution_m=0.25,
        bbox=bbox,
        primary_image_path=tif_path,
    )

    loaded = extractor._load_observation_image(obs)
    assert loaded is not None
    arr_8bit = np.array(loaded)
    assert arr_8bit.dtype == np.uint8
    # Contrast stretching should span full 0-255 range, not be pitch black (< 15)
    assert arr_8bit.max() > 200
    assert arr_8bit.min() < 50

