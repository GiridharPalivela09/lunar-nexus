"""REST API Schema, Schema Validation, and Backend-to-UI Consistency Tests."""

import json
import socket
import threading
import time
import urllib.request
import urllib.error
from pathlib import Path
import pytest

from scripts.launch_dashboard import ReusableThreadingHTTPServer, NexusDashboardHandler

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


@pytest.fixture(scope="session")
def api_base_url():
    """Returns base URL. Uses running dashboard if available, or starts test server on port 8089."""
    if is_port_in_use(8000):
        yield "http://127.0.0.1:8000"
        return

    test_port = 8089
    server = ReusableThreadingHTTPServer(("127.0.0.1", test_port), NexusDashboardHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)

    yield f"http://127.0.0.1:{test_port}"
    server.shutdown()


def http_get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "NEXUS-LUNAR-TestRunner"})
    with urllib.request.urlopen(req) as resp:
        data = resp.read().decode("utf-8")
        return resp.status, json.loads(data)


class TestDashboardRestAPI:
    """Validates HTTP status codes, JSON schemas, consistency, and error states across all dashboard endpoints."""

    def test_get_catalog_schema_and_integrity(self, api_base_url):
        status, catalog = http_get_json(f"{api_base_url}/api/catalog")
        assert status == 200
        assert isinstance(catalog, list)
        assert len(catalog) >= 5, "Catalog should return indexed lunar observations"

        required_keys = {"product_id", "mission", "sensor", "resolution_m", "bbox"}
        for obs in catalog:
            missing = required_keys - set(obs.keys())
            assert not missing, f"Observation {obs.get('product_id')} missing required keys: {missing}"

            bbox = obs["bbox"]
            assert -90.0 <= bbox["min_lat"] <= bbox["max_lat"] <= 90.0
            assert bbox["min_lon"] <= bbox["max_lon"]
            if obs["resolution_m"] is not None:
                assert obs["resolution_m"] > 0

    def test_get_overlapping_pairs_and_consistency(self, api_base_url):
        # 1. Fetch catalog to verify cross-reference integrity
        _, catalog = http_get_json(f"{api_base_url}/api/catalog")
        catalog_ids = {obs["product_id"] for obs in catalog}

        # 2. Fetch overlapping candidate pairs
        status, pairs = http_get_json(f"{api_base_url}/api/pairs")
        assert status == 200
        assert isinstance(pairs, list)
        assert len(pairs) >= 1, "Expected candidate overlap pairs"

        for pair in pairs:
            # Verify source and reference IDs actually exist in the catalog
            src_id = pair["source_product_id"]
            ref_id = pair["reference_product_id"]
            assert src_id in catalog_ids, f"Source product {src_id} not found in catalog"
            assert ref_id in catalog_ids, f"Reference product {ref_id} not found in catalog"

            # Check overlap percentages and geometry
            overlap_src = pair["overlap_percent_of_source"]
            overlap_ref = pair["overlap_percent_of_reference"]
            assert 0.0 < overlap_src <= 100.0
            assert 0.0 < overlap_ref <= 100.0
            assert pair["overlap_area_km2"] > 0

            # Verify intersection bounding box
            ibox = pair["intersection_bbox"]
            assert ibox["min_lat"] <= ibox["max_lat"]
            assert ibox["min_lon"] <= ibox["max_lon"]

    def test_get_manifest_valid_and_missing_param(self, api_base_url):
        # 1. Missing pair_id parameter returns 400 Bad Request
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(f"{api_base_url}/api/manifest")
        assert exc_info.value.code == 400

        # 2. Valid pair_id returns valid manifest JSON schema
        pair_id = "ch2_ohr_ncp_20230915t041230_boguslawsky_d18___M1345982701LR_BOGUSLAWSKY_REF"
        status, manifest = http_get_json(f"{api_base_url}/api/manifest?pair_id={pair_id}")
        assert status == 200
        assert manifest["source_product_id"] == "ch2_ohr_ncp_20230915t041230_boguslawsky_d18"
        assert manifest["reference_product_id"] == "M1345982701LR_BOGUSLAWSKY_REF"
        assert manifest["total_patches"] >= 1
        assert "patches" in manifest

    def test_registration_methods_endpoint(self, api_base_url):
        status, methods = http_get_json(f"{api_base_url}/api/registration/methods")
        assert status == 200
        algo_ids = [a["id"] for a in methods["algorithms"]]
        assert "SIFT" in algo_ids
        assert "RootSIFT" in algo_ids
        assert "ORB" in algo_ids
        assert "AKAZE" in algo_ids

        transform_ids = [t["id"] for t in methods["transformations"]]
        assert "Homography" in transform_ids
        assert "Affine" in transform_ids

    def test_first_principles_science_telemetry(self, api_base_url):
        status, science = http_get_json(f"{api_base_url}/api/nexus/science/first_principles")
        assert status == 200
        assert science["status"] == "SUCCESS"
        assert "frequency" in science
        assert "physics" in science
        assert "chemistry" in science
        assert "biology" in science
        assert "pinn" in science

        # Validate physics parameters
        assert "hapke" in science["physics"]
        assert "thermal" in science["physics"]
        assert "terramechanics" in science["physics"]

    def test_mission_summary_endpoint(self, api_base_url):
        status, summary = http_get_json(f"{api_base_url}/api/nexus/summary")
        assert status == 200
        assert summary["status"] == "ONLINE"
        assert "pocs" in summary
        poc_ids = [p["id"] for p in summary["pocs"]]
        assert "POC-1" in poc_ids
        assert "POC-2" in poc_ids
        assert "POC-3" in poc_ids

    def test_static_asset_serving(self, api_base_url):
        # 1. HTML index
        with urllib.request.urlopen(f"{api_base_url}/") as resp:
            assert resp.status == 200
            assert "text/html" in resp.headers.get("Content-Type", "")

        # 2. Patch image PNG serving
        patch_url = f"{api_base_url}/data/processed/patches/ch2_ohr_ncp_20230915t041230_boguslawsky_d18___M1345982701LR_BOGUSLAWSKY_REF/patch_0001_src.png"
        with urllib.request.urlopen(patch_url) as resp:
            assert resp.status == 200
            assert "image/png" in resp.headers.get("Content-Type", "")
            assert int(resp.headers.get("Content-Length", 0)) > 1000

    def test_unknown_endpoint_returns_404(self, api_base_url):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(f"{api_base_url}/api/unknown_non_existent_route")
        assert exc_info.value.code == 404
