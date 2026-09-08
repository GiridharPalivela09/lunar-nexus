#!/usr/bin/env python3
"""NEXUS-LUNAR: Interactive Lunar Intelligence & POC 2 Studio Dashboard Server.

Usage:
  python scripts/launch_dashboard.py [--port 8000] [--no-browser]
"""

import sys
import os
import json
import logging
import argparse
import webbrowser
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from packages.data_pipeline import (
    SensorType,
    ResolutionStrategy,
    PatchExtractionConfig,
    OverlapPatchExtractor,
    LunarDataCatalog,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("nexus.dashboard")

WEB_DIR = PROJECT_ROOT / "web"
DATA_DIR = PROJECT_ROOT / "data"


class NexusDashboardHandler(SimpleHTTPRequestHandler):
    """Custom HTTP Handler serving both the SPA frontend and the REST API."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PROJECT_ROOT), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Serve favicon and common browser assets cleanly (suppress 404s)
        if path in ("/favicon.ico", "/favicon.svg", "/apple-touch-icon.png", "/apple-touch-icon-precomposed.png"):
            fav_path = WEB_DIR / "favicon.svg"
            if fav_path.exists():
                self.serve_file(fav_path, "image/svg+xml")
            else:
                self.send_response(204)
                self.end_headers()
            return

        # Suppress chrome devtools 404
        if path.startswith("/.well-known/"):
            self.send_response(204)
            self.end_headers()
            return

        # 1. API: Catalog Observations
        if path == "/api/catalog":
            self.send_json_response(self.get_catalog_data())
            return

        # 2. API: Overlapping Pairs (POC 2)
        if path == "/api/pairs":
            self.send_json_response(self.get_overlapping_pairs())
            return

        # 2b. API: Latest POC 2 Demo Metadata
        if path == "/api/poc2/demo":
            demo_meta_file = PROJECT_ROOT / "outputs" / "poc2_demo" / "patch_metadata.json"
            if demo_meta_file.exists():
                with open(demo_meta_file, "r", encoding="utf-8") as f:
                    self.send_json_response(json.load(f))
            else:
                self.send_error(404, "POC 2 demo metadata not generated yet. Run scripts/demo_poc2.py")
            return

        # 3. API: Patch Manifest for a Pair
        if path == "/api/manifest":
            query = parse_qs(parsed.query)
            pair_id = query.get("pair_id", [None])[0]
            if not pair_id:
                self.send_error(400, "Missing pair_id query parameter")
                return

            manifest_path = DATA_DIR / "processed" / "patches" / pair_id / "patch_manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self.send_json_response(data)
                except Exception as e:
                    self.send_error(500, f"Error reading manifest: {e}")
            else:
                self.send_json_response({
                    "total_patches": 0,
                    "patches": [],
                    "not_extracted": True,
                    "pair_id": pair_id,
                })
            return

        # 3b. API: POC 4 Results JSON
        if path == "/api/poc4/results":
            results_path = PROJECT_ROOT / "outputs" / "poc4" / "results.json"
            if results_path.exists():
                with open(results_path, "r", encoding="utf-8") as f:
                    self.send_json_response(json.load(f))
            else:
                self.send_error(404, "POC 4 results not found. Run scripts/demo_poc4.py")
            return

        # 3c. API: POC 4 Demo Summary & Visualizations
        if path == "/api/poc4/demo":
            meta_path = PROJECT_ROOT / "outputs" / "poc4" / "poc4_metadata.json"
            results_path = PROJECT_ROOT / "outputs" / "poc4" / "results.json"
            if meta_path.exists() and results_path.exists():
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta_data = json.load(f)
                with open(results_path, "r", encoding="utf-8") as f:
                    results_data = json.load(f)
                
                resp = {
                    "metadata": meta_data,
                    "best_performing_representation": results_data.get("best_performing_representation", "MULTI-SCALE + ILLUMINATION-AWARE"),
                    "statistical_summary": results_data.get("statistical_summary", {}),
                    "matrix_results": results_data.get("matrix_results", []),
                    "ablation_results": results_data.get("ablation_results", []),
                    "failure_summary": results_data.get("failure_summary", {}),
                    "figures": {
                        "illumination_comparison": "/outputs/poc4/illumination_comparison.png",
                        "scale_pyramid": "/outputs/poc4/scale_pyramid.png",
                        "registration_comparison": "/outputs/poc4/registration_comparison.png",
                        "metrics_comparison": "/outputs/poc4/metrics_comparison.png",
                        "illumination_scale_heatmap": "/outputs/poc4/illumination_scale_heatmap.png",
                        "ablation_results": "/outputs/poc4/ablation_results.png",
                    }
                }
                self.send_json_response(resp)
            else:
                self.send_error(404, "POC 4 metadata not found")
            return

        # 3d. API: POC 5 Results & Visualizations
        if path == "/api/poc5/results" or path == "/api/poc5/demo":
            results_path = PROJECT_ROOT / "outputs" / "poc5" / "results.json"
            if results_path.exists():
                with open(results_path, "r", encoding="utf-8") as f:
                    results_data = json.load(f)
                resp = {
                    "summary": results_data.get("summary", {}),
                    "queries": results_data.get("queries", []),
                    "figures": {
                        "two_tower_architecture": "/outputs/poc5/two_tower_architecture.png",
                        "retrieval_ranking_grid": "/outputs/poc5/retrieval_ranking_grid.png",
                        "embedding_clusters": "/outputs/poc5/embedding_clusters.png",
                        "recall_at_k_curve": "/outputs/poc5/recall_at_k_curve.png",
                        "similarity_distribution": "/outputs/poc5/similarity_distribution.png",
                    }
                }
                self.send_json_response(resp)
            else:
                self.send_error(404, "POC 5 results not found. Run scripts/demo_poc5.py")
            return

        # 3e. API: Blender MCP Server Status
        if path == "/api/nexus/blender/status":
            from packages.nexus_core.blender_mcp_client import BlenderMCPClient
            client = BlenderMCPClient(project_root=PROJECT_ROOT)
            online = client.is_server_online(timeout=0.3)
            bin_path = client.get_blender_binary()
            self.send_json_response({
                "online": online,
                "host": client.host,
                "port": client.port,
                "blender_bin": bin_path,
                "blender_available": bin_path is not None,
                "rendered_image_exists": (PROJECT_ROOT / "outputs" / "nexus_3d" / "nexus_blender_digital_twin.png").exists(),
                "rendered_image_url": "/outputs/nexus_3d/nexus_blender_digital_twin.png",
            })
            return

        # 3f. API: Habitat Layout Plan (POC 8)
        if path == "/api/nexus/habitat/plan":
            plan_path = PROJECT_ROOT / "outputs" / "nexus_3d" / "habitat_layout_plan.json"
            if not plan_path.exists():
                from packages.nexus_core.poc8_habitat_planner import HabitatConstraintPlanner
                planner = HabitatConstraintPlanner()
                planner.generate_habitat_layout()
            if plan_path.exists():
                with open(plan_path, "r", encoding="utf-8") as f:
                    self.send_json_response(json.load(f))
            else:
                self.send_error(404, "Habitat layout plan not available")
            return

        # 3g. API: All 8 POCs Summary
        if path == "/api/nexus/summary":
            sum_path = PROJECT_ROOT / "outputs" / "nexus_summary.json"
            if sum_path.exists():
                with open(sum_path, "r", encoding="utf-8") as f:
                    self.send_json_response(json.load(f))
            else:
                self.send_json_response({
                    "status": "ready",
                    "pocs": ["poc1_skg", "poc2_terrain", "poc3_illumination", "poc4_resource", "poc5_xai", "poc6_gnn", "poc7_snn", "poc8_habitat"],
                    "blender_mcp_port": 9876,
                })
            return


        # 4. Static Frontend Routing
        if path == "/" or path == "/index.html":
            self.serve_file(WEB_DIR / "index.html", "text/html")
            return
        elif path == "/style.css":
            self.serve_file(WEB_DIR / "style.css", "text/css")
            return
        elif path == "/app.js":
            self.serve_file(WEB_DIR / "app.js", "application/javascript")
            return

        # 5. Serve images and files from data directory
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/extract":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
                manifest = self.run_patch_extraction(payload)
                self.send_json_response(json.loads(manifest.model_dump_json()))
            except Exception as e:
                logger.error(f"Extraction error: {e}", exc_info=True)
                self.send_error(500, f"Extraction failed: {str(e)}")
            return

        if path == "/api/poc4/run":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                payload = json.loads(body) if body else {}
                seed = int(payload.get("seed", 42))
                from scripts.demo_poc4 import main as run_demo_main
                logger.info(f"Triggering POC-4 Experiment Run via Web API (seed={seed})...")
                run_demo_main(seed=seed)
                results_path = PROJECT_ROOT / "outputs" / "poc4" / "results.json"
                with open(results_path, "r", encoding="utf-8") as f:
                    self.send_json_response(json.load(f))
            except Exception as e:
                logger.error(f"POC-4 execution error: {e}", exc_info=True)
                self.send_error(500, f"POC-4 run failed: {str(e)}")
            return

        if path == "/api/poc5/run":
            try:
                from scripts.demo_poc5 import main as run_poc5_main
                logger.info("Triggering POC-5 Experiment Run via Web API...")
                run_poc5_main()
                results_path = PROJECT_ROOT / "outputs" / "poc5" / "results.json"
                with open(results_path, "r", encoding="utf-8") as f:
                    self.send_json_response(json.load(f))
            except Exception as e:
                logger.error(f"POC-5 execution error: {e}", exc_info=True)
                self.send_error(500, f"POC-5 run failed: {str(e)}")
            return

        if path == "/api/nexus/blender/build":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                payload = json.loads(body) if body else {}
                force_headless = bool(payload.get("force_headless", False))
                from packages.nexus_core.blender_mcp_client import BlenderMCPClient
                client = BlenderMCPClient(project_root=PROJECT_ROOT)
                logger.info(f"Triggering Blender 3D Infrastructure build (force_headless={force_headless})...")
                res = client.build_infrastructure_pipeline(force_headless=force_headless)
                self.send_json_response(res)
            except Exception as e:
                logger.error(f"Blender build execution error: {e}", exc_info=True)
                self.send_error(500, f"Blender build failed: {str(e)}")
            return

        self.send_error(404, "Endpoint not found")


    def get_catalog_data(self):
        catalog = LunarDataCatalog(catalog_file=DATA_DIR / "catalog.json")
        obs_list = catalog.list_observations()
        return [obs.to_summary_dict() for obs in obs_list]

    def get_overlapping_pairs(self):
        catalog = LunarDataCatalog(catalog_file=DATA_DIR / "catalog.json")
        pairs = []
        for src_sensor in [SensorType.OHRC, SensorType.TMC2]:
            pairs.extend(
                catalog.find_overlapping_pairs(
                    source_sensor=src_sensor,
                    reference_sensor=SensorType.LRO_NAC,
                    min_overlap_pct=5.0,
                )
            )
        return pairs

    def run_patch_extraction(self, payload):
        catalog = LunarDataCatalog(catalog_file=DATA_DIR / "catalog.json")
        src_id = payload.get("source_product_id")
        ref_id = payload.get("reference_product_id")
        patch_size = int(payload.get("patch_size", 512))
        stride = int(payload.get("stride", patch_size))
        strategy_str = payload.get("strategy", "match_coarser")

        src_obs = catalog.get_by_id(src_id)
        ref_obs = catalog.get_by_id(ref_id)

        if not src_obs or not ref_obs:
            raise ValueError(f"Could not find observation {src_id} or {ref_id}")

        config = PatchExtractionConfig(
            patch_size=patch_size,
            stride=stride,
            resolution_strategy=ResolutionStrategy(strategy_str),
        )
        extractor = OverlapPatchExtractor(config=config)
        return extractor.extract_patch_pairs(
            source_obs=src_obs,
            reference_obs=ref_obs,
            output_dir=DATA_DIR / "processed" / "patches",
        )

    def serve_file(self, filepath: Path, content_type: str):
        if not filepath.exists():
            self.send_error(404, f"File {filepath.name} not found")
            return
        try:
            with open(filepath, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error reading file: {e}")

    def send_json_response(self, data, status: int = 200):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Concise logging
        logger.info(f"{self.address_string()} - {format % args}")


def run_server(port: int = 8000, open_browser: bool = True):
    ThreadingHTTPServer.allow_reuse_address = True
    actual_port = port
    httpd = None

    # Try requested port or auto-fallback to next available ports
    for p in range(port, port + 20):
        try:
            server_address = ("", p)
            httpd = ThreadingHTTPServer(server_address, NexusDashboardHandler)
            actual_port = p
            break
        except OSError as e:
            if e.errno == 48: # Address already in use
                logger.warning(f"Port {p} is currently in use. Trying port {p + 1}...")
                continue
            raise

    if httpd is None:
        print(f"[!] Unable to bind server to any port in range {port} - {port + 20}.")
        sys.exit(1)

    url = f"http://localhost:{actual_port}"
    print(f"\n=======================================================")
    print(f"  NEXUS-LUNAR: Lunar Intelligence & Studio Dashboard")
    print(f"  Local URL:  {url}")
    print(f"  Features:   3D Space Studio | Blender MCP | GIS Map")
    print(f"=======================================================\n")

    if open_browser:
        webbrowser.open(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down dashboard server...")
        httpd.server_close()


def main():
    parser = argparse.ArgumentParser(description="NEXUS-LUNAR Dashboard Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")
    args = parser.parse_args()

    run_server(port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
