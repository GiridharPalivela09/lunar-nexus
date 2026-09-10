"""Comprehensive Tests for the Lunar Data Catalog and Query Subsystem."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
import pytest

from packages.data_pipeline.catalog import LunarDataCatalog
from packages.data_pipeline.models import (
    SensorType,
    MissionType,
    BoundingBox,
    LunarObservation,
    CatalogQuery,
)


@pytest.fixture
def temp_catalog_path(tmp_path):
    return tmp_path / "test_catalog.json"


@pytest.fixture
def sample_observations():
    obs1 = LunarObservation(
        product_id="src_ohrc_boguslawsky",
        mission=MissionType.CHANDRAYAAN2,
        sensor=SensorType.OHRC,
        spatial_resolution_m=0.25,
        bbox=BoundingBox(min_lat=-74.0, max_lat=-72.0, min_lon=24.0, max_lon=28.0),
    )
    obs2 = LunarObservation(
        product_id="ref_lro_boguslawsky",
        mission=MissionType.LRO,
        sensor=SensorType.LRO_NAC,
        spatial_resolution_m=0.5,
        bbox=BoundingBox(min_lat=-74.5, max_lat=-72.5, min_lon=25.0, max_lon=29.0),
    )
    obs3 = LunarObservation(
        product_id="src_tmc2_shackleton",
        mission=MissionType.CHANDRAYAAN2,
        sensor=SensorType.TMC2,
        spatial_resolution_m=5.0,
        bbox=BoundingBox(min_lat=-89.9, max_lat=-88.0, min_lon=0.0, max_lon=30.0),
    )
    return [obs1, obs2, obs3]


class TestLunarDataCatalog:
    """Test suite validating insertion, querying, persistence, and spatial search."""

    def test_load_existing_production_catalog(self):
        """Validates that data/catalog.json exists, loads cleanly, and instantiates LunarObservation models."""
        prod_cat_path = Path("data/catalog.json")
        assert prod_cat_path.exists(), "Production catalog data/catalog.json must exist"

        catalog = LunarDataCatalog(catalog_file=prod_cat_path)
        observations = catalog.list_observations()
        assert len(observations) >= 5, "Catalog should contain multiple indexed observations"

        for obs in observations:
            assert isinstance(obs, LunarObservation)
            assert obs.product_id
            assert obs.sensor in SensorType
            assert obs.mission in MissionType
            assert obs.bbox.min_lat <= obs.bbox.max_lat
            assert obs.bbox.min_lon <= obs.bbox.max_lon

    def test_add_and_retrieve_observation(self, temp_catalog_path, sample_observations):
        catalog = LunarDataCatalog(catalog_file=temp_catalog_path)
        obs1 = sample_observations[0]
        catalog.add_observation(obs1)

        retrieved = catalog.get_by_id("src_ohrc_boguslawsky")
        assert retrieved is not None
        assert retrieved.product_id == "src_ohrc_boguslawsky"
        assert retrieved.sensor == SensorType.OHRC
        assert retrieved.spatial_resolution_m == 0.25

        # Non-existent ID returns None
        assert catalog.get_by_id("non_existent_id") is None

    def test_duplicate_handling_updates_in_place(self, temp_catalog_path, sample_observations):
        catalog = LunarDataCatalog(catalog_file=temp_catalog_path)
        obs1 = sample_observations[0]
        catalog.add_observation(obs1)
        assert len(catalog.list_observations()) == 1

        # Add updated observation with same ID but updated resolution
        updated_obs = obs1.model_copy(update={"spatial_resolution_m": 0.20})
        catalog.add_observation(updated_obs)

        assert len(catalog.list_observations()) == 1
        assert catalog.get_by_id(obs1.product_id).spatial_resolution_m == 0.20

    def test_sensor_filtering(self, temp_catalog_path, sample_observations):
        catalog = LunarDataCatalog(catalog_file=temp_catalog_path)
        catalog.add_observations(sample_observations)

        ohrc_results = catalog.query(CatalogQuery(sensors=[SensorType.OHRC]))
        assert len(ohrc_results) == 1
        assert ohrc_results[0].sensor == SensorType.OHRC

        tmc_results = catalog.query(CatalogQuery(sensors=[SensorType.TMC2]))
        assert len(tmc_results) == 1
        assert tmc_results[0].sensor == SensorType.TMC2

        combined_results = catalog.query(CatalogQuery(sensors=[SensorType.OHRC, SensorType.LRO_NAC]))
        assert len(combined_results) == 2

    def test_spatial_bbox_query(self, temp_catalog_path, sample_observations):
        catalog = LunarDataCatalog(catalog_file=temp_catalog_path)
        catalog.add_observations(sample_observations)

        # Query Boguslawsky region [-75, -71], [23, 30] -> should match obs1 and obs2
        boguslawsky_query = CatalogQuery(
            bbox=BoundingBox(min_lat=-75.0, max_lat=-71.0, min_lon=23.0, max_lon=30.0)
        )
        results = catalog.query(boguslawsky_query)
        res_ids = {r.product_id for r in results}
        assert "src_ohrc_boguslawsky" in res_ids
        assert "ref_lro_boguslawsky" in res_ids
        assert "src_tmc2_shackleton" not in res_ids

        # Query North Pole region [80, 90] -> 0 results
        north_query = CatalogQuery(
            bbox=BoundingBox(min_lat=80.0, max_lat=90.0, min_lon=0.0, max_lon=10.0)
        )
        assert len(catalog.query(north_query)) == 0

    def test_find_overlapping_pairs_discovery(self, temp_catalog_path, sample_observations):
        catalog = LunarDataCatalog(catalog_file=temp_catalog_path)
        catalog.add_observations(sample_observations)

        # Search for OHRC vs LRO_NAC overlap
        pairs = catalog.find_overlapping_pairs(
            source_sensor=SensorType.OHRC,
            reference_sensor=SensorType.LRO_NAC,
            min_overlap_pct=5.0,
        )
        assert len(pairs) == 1
        pair = pairs[0]
        assert pair["source_product_id"] == "src_ohrc_boguslawsky"
        assert pair["reference_product_id"] == "ref_lro_boguslawsky"
        assert pair["overlap_percent_of_source"] > 0
        assert pair["overlap_percent_of_reference"] > 0
        assert pair["overlap_area_km2"] > 0
        assert "intersection_bbox" in pair

    def test_catalog_persistence_and_reload(self, temp_catalog_path, sample_observations):
        catalog1 = LunarDataCatalog(catalog_file=temp_catalog_path)
        catalog1.add_observations(sample_observations)

        # Instantiate second catalog pointing to same file
        catalog2 = LunarDataCatalog(catalog_file=temp_catalog_path)
        assert len(catalog2.list_observations()) == 3
        assert catalog2.get_by_id("src_ohrc_boguslawsky") is not None

    def test_missing_file_initializes_empty_catalog(self, tmp_path):
        non_existent = tmp_path / "does_not_exist.json"
        cat = LunarDataCatalog(catalog_file=non_existent)
        assert len(cat.list_observations()) == 0

    def test_query_catalog_cli(self):
        """Validates that scripts/query_catalog.py executes without error and outputs catalog items."""
        # 1. Test --list
        res_list = subprocess.run(
            [sys.executable, "scripts/query_catalog.py", "--list"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Lunar Data Catalog" in res_list.stdout

        # 2. Test --find-pairs
        res_pairs = subprocess.run(
            [sys.executable, "scripts/query_catalog.py", "--find-pairs", "--source", "OHRC", "--reference", "LRO_NAC"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Searching for overlapping pairs" in res_pairs.stdout
