"""Tests for POC-2 Resolution-Harmonized Patch Extraction Subsystem."""

import json
from pathlib import Path
import pytest
from PIL import Image
import numpy as np

from packages.data_pipeline.models import (
    SensorType,
    MissionType,
    BoundingBox,
    LunarObservation,
    PatchExtractionConfig,
    ResolutionStrategy,
    PatchManifest,
)
from packages.data_pipeline.patch_extractor import (
    GeoPixelTransformer,
    ResolutionHarmonizer,
    OverlapPatchExtractor,
)


@pytest.fixture
def synthetic_lunar_images():
    """Generates synthetic high-res source (512x512) and reference (256x256) images."""
    np.random.seed(42)
    src_arr = np.random.randint(40, 220, (512, 512), dtype=np.uint8)
    ref_arr = np.random.randint(40, 220, (256, 256), dtype=np.uint8)

    src_img = Image.fromarray(src_arr, mode="L")
    ref_img = Image.fromarray(ref_arr, mode="L")
    return src_img, ref_img


@pytest.fixture
def overlapping_observations():
    src_bbox = BoundingBox(min_lat=-74.0, max_lat=-72.0, min_lon=24.0, max_lon=28.0)
    ref_bbox = BoundingBox(min_lat=-74.5, max_lat=-72.5, min_lon=25.0, max_lon=29.0)

    src_obs = LunarObservation(
        product_id="test_ohrc_source",
        mission=MissionType.CHANDRAYAAN2,
        sensor=SensorType.OHRC,
        spatial_resolution_m=0.25,
        bbox=src_bbox,
    )
    ref_obs = LunarObservation(
        product_id="test_lro_reference",
        mission=MissionType.LRO,
        sensor=SensorType.LRO_NAC,
        spatial_resolution_m=0.50,
        bbox=ref_bbox,
    )
    return src_obs, ref_obs


class TestGeoPixelTransformer:
    """Validates coordinate mapping between lunar selenographic space and image raster pixels."""

    def test_bidirectional_roundtrip_precision(self):
        bbox = BoundingBox(min_lat=-74.0, max_lat=-72.0, min_lon=24.0, max_lon=28.0)
        transformer = GeoPixelTransformer(bbox=bbox, image_width=1000, image_height=1000)

        # Test center point
        lat_in, lon_in = -73.0, 26.0
        px, py = transformer.geo_to_pixel(lat_in, lon_in)
        assert pytest.approx(px, 1e-4) == 500.0
        assert pytest.approx(py, 1e-4) == 500.0

        lat_out, lon_out = transformer.pixel_to_geo(px, py)
        assert pytest.approx(lat_out, 1e-4) == lat_in
        assert pytest.approx(lon_out, 1e-4) == lon_in

    def test_bbox_to_pixel_box_clamping(self):
        bbox = BoundingBox(min_lat=-74.0, max_lat=-72.0, min_lon=24.0, max_lon=28.0)
        transformer = GeoPixelTransformer(bbox=bbox, image_width=1000, image_height=1000)

        sub_bbox = BoundingBox(min_lat=-73.0, max_lat=-72.5, min_lon=25.0, max_lon=27.0)
        pbox = transformer.bbox_to_pixel_box(sub_bbox)

        assert 0 <= pbox.x <= 1000
        assert 0 <= pbox.y <= 1000
        assert pbox.width > 0 and pbox.height > 0


class TestResolutionHarmonizer:
    """Validates multi-scale GSD harmonization strategies."""

    def test_gsd_strategies(self):
        # Match coarser: should pick max(0.25, 0.5) = 0.5m
        gsd_coarse = ResolutionHarmonizer.calculate_effective_gsd(
            0.25, 0.50, strategy=ResolutionStrategy.MATCH_COARSER
        )
        assert gsd_coarse == 0.50

        # Match finer: should pick min(0.25, 0.5) = 0.25m
        gsd_finer = ResolutionHarmonizer.calculate_effective_gsd(
            0.25, 0.50, strategy=ResolutionStrategy.MATCH_FINER
        )
        assert gsd_finer == 0.25

        # Explicit target overrides strategy
        gsd_explicit = ResolutionHarmonizer.calculate_effective_gsd(
            0.25, 0.50, strategy=ResolutionStrategy.MATCH_COARSER, explicit_target=1.0
        )
        assert gsd_explicit == 1.0


class TestOverlapPatchExtractor:
    """Validates end-to-end patch extraction, manifest JSON generation, and file integrity."""

    def test_patch_extraction_files_and_manifest(
        self, tmp_path, overlapping_observations, synthetic_lunar_images
    ):
        src_obs, ref_obs = overlapping_observations
        src_img, ref_img = synthetic_lunar_images

        config = PatchExtractionConfig(patch_size=128, stride=128, resolution_strategy=ResolutionStrategy.MATCH_COARSER)
        extractor = OverlapPatchExtractor(config=config)

        manifest = extractor.extract_patch_pairs(
            source_obs=src_obs,
            reference_obs=ref_obs,
            source_img=src_img,
            ref_img=ref_img,
            output_dir=tmp_path,
        )

        assert isinstance(manifest, PatchManifest)
        assert manifest.total_patches > 0
        assert manifest.source_product_id == src_obs.product_id
        assert manifest.reference_product_id == ref_obs.product_id

        # Verify on-disk manifest JSON exists and is valid
        pair_key = f"{src_obs.product_id}___{ref_obs.product_id}"
        manifest_file = tmp_path / pair_key / "patch_manifest.json"
        assert manifest_file.exists()

        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest_json = json.load(f)
        assert manifest_json["total_patches"] == manifest.total_patches

        # Verify every patch pair references actual image files on disk with exact requested dimensions
        for patch in manifest.patches:
            src_path = Path(patch.source_patch_path)
            ref_path = Path(patch.reference_patch_path)

            assert src_path.exists(), f"Source patch {src_path} must exist on disk"
            assert ref_path.exists(), f"Reference patch {ref_path} must exist on disk"

            with Image.open(src_path) as s_im:
                assert s_im.size == (128, 128)
            with Image.open(ref_path) as r_im:
                assert r_im.size == (128, 128)

            assert 0.0 <= patch.quality_score <= 1.0

    def test_non_overlapping_observations_yields_zero_patches(self, tmp_path, synthetic_lunar_images):
        src_img, ref_img = synthetic_lunar_images
        src_obs = LunarObservation(
            product_id="src_disjoint",
            mission=MissionType.CHANDRAYAAN2,
            sensor=SensorType.OHRC,
            bbox=BoundingBox(min_lat=0.0, max_lat=2.0, min_lon=0.0, max_lon=2.0),
        )
        ref_obs = LunarObservation(
            product_id="ref_disjoint",
            mission=MissionType.LRO,
            sensor=SensorType.LRO_NAC,
            bbox=BoundingBox(min_lat=50.0, max_lat=52.0, min_lon=50.0, max_lon=52.0),
        )

        extractor = OverlapPatchExtractor()
        manifest = extractor.extract_patch_pairs(
            source_obs=src_obs,
            reference_obs=ref_obs,
            source_img=src_img,
            ref_img=ref_img,
            output_dir=tmp_path,
        )

        assert manifest.total_patches == 0
        assert len(manifest.patches) == 0

    def test_missing_image_files_raises_file_not_found(self, tmp_path, overlapping_observations):
        src_obs, ref_obs = overlapping_observations
        extractor = OverlapPatchExtractor()

        # Both source and reference images are None and point to non-existent disk paths
        with pytest.raises(FileNotFoundError):
            extractor.extract_patch_pairs(
                source_obs=src_obs,
                reference_obs=ref_obs,
                source_img=None,
                ref_img=None,
                output_dir=tmp_path,
            )
