"""Unit tests for Lunar Observation Models, Bounding Boxes, and Schemas."""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from packages.data_pipeline.models import (
    SensorType,
    MissionType,
    BoundingBox,
    ObservationGeometry,
    LunarObservation,
    PatchExtractionConfig,
    ResolutionStrategy,
    PixelBox,
    ExtractedPatchPair,
    PatchManifest,
)


class TestBoundingBoxModel:
    """Tests for BoundingBox validation, properties, and constraints."""

    def test_valid_bounding_box(self):
        bbox = BoundingBox(min_lat=-74.5, max_lat=-72.0, min_lon=24.0, max_lon=28.0)
        assert bbox.min_lat == -74.5
        assert bbox.max_lat == -72.0
        assert bbox.min_lon == 24.0
        assert bbox.max_lon == 28.0

        # Center calculation: (-73.25, 26.0)
        center_lat, center_lon = bbox.center
        assert pytest.approx(center_lat, 1e-4) == -73.25
        assert pytest.approx(center_lon, 1e-4) == 26.0

        # Polygon closed ring: 5 points, start == end
        coords = bbox.polygon_coords
        assert len(coords) == 5
        assert coords[0] == coords[-1]
        assert coords[0] == (24.0, -74.5)
        assert coords[2] == (28.0, -72.0)

    def test_inverted_latitude_rejection(self):
        """min_lat > max_lat must raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            BoundingBox(min_lat=-70.0, max_lat=-75.0, min_lon=20.0, max_lon=30.0)
        assert "Inverted latitude bounds" in str(exc_info.value)

    def test_inverted_longitude_rejection(self):
        """min_lon > max_lon must raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            BoundingBox(min_lat=-75.0, max_lat=-70.0, min_lon=35.0, max_lon=20.0)
        assert "Inverted longitude bounds" in str(exc_info.value)

    def test_latitude_out_of_range(self):
        """Latitude outside [-90, 90] must raise ValidationError."""
        with pytest.raises(ValidationError):
            BoundingBox(min_lat=-95.0, max_lat=-70.0, min_lon=0.0, max_lon=10.0)

        with pytest.raises(ValidationError):
            BoundingBox(min_lat=70.0, max_lat=95.0, min_lon=0.0, max_lon=10.0)

    def test_longitude_out_of_range(self):
        """Longitude outside valid domain [-180, 360] must raise ValidationError."""
        with pytest.raises(ValidationError):
            BoundingBox(min_lat=-10.0, max_lat=10.0, min_lon=-200.0, max_lon=10.0)

        with pytest.raises(ValidationError):
            BoundingBox(min_lat=-10.0, max_lat=10.0, min_lon=0.0, max_lon=400.0)

    def test_edge_case_single_point_box(self):
        """Zero-area box (min == max) is geometrically valid as a degenerate point box."""
        bbox = BoundingBox(min_lat=-73.0, max_lat=-73.0, min_lon=25.0, max_lon=25.0)
        assert bbox.center == (-73.0, 25.0)


class TestLunarObservationModel:
    """Tests for LunarObservation schema, required fields, and constraints."""

    def test_valid_lunar_observation(self):
        bbox = BoundingBox(min_lat=-74.5, max_lat=-72.0, min_lon=24.0, max_lon=28.0)
        obs = LunarObservation(
            product_id="ch2_ohr_ncp_20230915t041230_boguslawsky_d18",
            mission=MissionType.CHANDRAYAAN2,
            sensor=SensorType.OHRC,
            spatial_resolution_m=0.25,
            bbox=bbox,
            geometry=ObservationGeometry(incidence_angle_deg=62.5, emission_angle_deg=2.1),
        )
        assert obs.product_id == "ch2_ohr_ncp_20230915t041230_boguslawsky_d18"
        assert obs.mission == MissionType.CHANDRAYAAN2
        assert obs.sensor == SensorType.OHRC
        assert obs.spatial_resolution_m == 0.25
        assert obs.crs == "Moon 2000 (IAU2000:30100)"

        summary = obs.to_summary_dict()
        assert summary["product_id"] == obs.product_id
        assert summary["mission"] == "CHANDRAYAAN-2"
        assert summary["sensor"] == "OHRC"
        assert summary["resolution_m"] == 0.25
        assert summary["incidence_angle"] == 62.5

    def test_empty_product_id_rejection(self):
        bbox = BoundingBox(min_lat=-10.0, max_lat=10.0, min_lon=0.0, max_lon=20.0)
        with pytest.raises(ValidationError):
            LunarObservation(
                product_id="",
                mission=MissionType.LRO,
                sensor=SensorType.LRO_NAC,
                bbox=bbox,
            )

        with pytest.raises(ValidationError):
            LunarObservation(
                product_id="   ",
                mission=MissionType.LRO,
                sensor=SensorType.LRO_NAC,
                bbox=bbox,
            )

    def test_negative_or_zero_resolution_rejection(self):
        bbox = BoundingBox(min_lat=-10.0, max_lat=10.0, min_lon=0.0, max_lon=20.0)
        with pytest.raises(ValidationError) as exc_info:
            LunarObservation(
                product_id="test_neg_res",
                mission=MissionType.CHANDRAYAAN2,
                sensor=SensorType.TMC2,
                spatial_resolution_m=-5.0,
                bbox=bbox,
            )
        assert "Spatial resolution must be positive" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            LunarObservation(
                product_id="test_zero_res",
                mission=MissionType.CHANDRAYAAN2,
                sensor=SensorType.TMC2,
                spatial_resolution_m=0.0,
                bbox=bbox,
            )
        assert "Spatial resolution must be positive" in str(exc_info.value)

    def test_sensor_and_mission_enums(self):
        assert SensorType.OHRC.value == "OHRC"
        assert SensorType.TMC2.value == "TMC2"
        assert SensorType.IIRS.value == "IIRS"
        assert SensorType.LRO_NAC.value == "LRO_NAC"
        assert SensorType.SELENE_TC.value == "SELENE_TC"
        assert SensorType.SELENE_MI.value == "SELENE_MI"

        assert MissionType.CHANDRAYAAN2.value == "CHANDRAYAAN-2"
        assert MissionType.LRO.value == "LRO"
        assert MissionType.SELENE.value == "SELENE"


class TestPatchModels:
    """Tests for PatchExtractionConfig, ExtractedPatchPair, and PatchManifest."""

    def test_patch_extraction_config_defaults(self):
        config = PatchExtractionConfig()
        assert config.patch_size == 512
        assert config.min_overlap_pct == 5.0
        assert config.resolution_strategy == ResolutionStrategy.MATCH_COARSER
        assert config.output_format == "png"

    def test_patch_manifest_validation(self):
        bbox = BoundingBox(min_lat=-74.5, max_lat=-72.0, min_lon=24.0, max_lon=28.0)
        patch_pair = ExtractedPatchPair(
            pair_id="p1",
            patch_index=1,
            source_product_id="src1",
            reference_product_id="ref1",
            source_patch_path="p1_src.png",
            reference_patch_path="p1_ref.png",
            ground_bbox=bbox,
            source_pixel_box=PixelBox(x=0, y=0, width=256, height=256),
            reference_pixel_box=PixelBox(x=0, y=0, width=256, height=256),
            effective_resolution_m=0.5,
            overlap_pct=100.0,
            quality_score=0.95,
        )

        manifest = PatchManifest(
            source_product_id="src1",
            reference_product_id="ref1",
            total_patches=1,
            intersection_bbox=bbox,
            intersection_area_km2=2649.98,
            config=PatchExtractionConfig(patch_size=256),
            patches=[patch_pair],
        )

        assert manifest.total_patches == 1
        assert len(manifest.patches) == 1
        assert manifest.patches[0].quality_score == 0.95
