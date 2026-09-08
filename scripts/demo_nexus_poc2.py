#!/usr/bin/env python3
"""NEXUS POC 2 Demo: Terrain Intelligence Engine.

Demonstrates:
1. Loading / generating 2D Digital Elevation Models (DEM)
2. Deriving surface slope and aspect using Horn's finite-difference gradient
3. Computing surface roughness and flagging steep escarpments/hazards
4. Evaluating candidate landing & habitat sites for terrain stability
5. Generating quantitative terrain intelligence reports and visualizations
"""

import json
import sys
from pathlib import Path
import numpy as np

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.nexus_core.poc2_terrain_intelligence import (
    TerrainIntelligenceEngine,
    generate_synthetic_boguslawsky_dem,
)


def run_demo():
    print("=" * 72)
    print(" NEXUS POC 2: TERRAIN INTELLIGENCE ENGINE")
    print("=" * 72)

    # 1. Initialize Elevation Model
    print("\n[*] Initializing Lunar DEM for Boguslawsky Crater Region...")
    resolution_m = 5.0
    size = 256
    dem = generate_synthetic_boguslawsky_dem(size=size, resolution_m=resolution_m)
    engine = TerrainIntelligenceEngine(
        elevation_grid=dem,
        resolution_m=resolution_m,
        bounds=(-73.1, -72.6, 42.8, 43.6),
    )

    print(f"    Grid Dimensions:     {engine.width} x {engine.height} cells")
    print(f"    Ground Resolution:   {engine.resolution_m} m/pixel ({size * resolution_m / 1000.0:.2f} km footprint)")
    print(f"    Elevation Range:     {np.min(dem):.1f} m to {np.max(dem):.1f} m (Relief: {np.ptp(dem):.1f} m)")

    # 2. Derive Geomorphometric Rasters
    print("\n[*] Computing Slope, Aspect, and Roughness Derivatives...")
    slope, aspect = engine.compute_slope_and_aspect()
    roughness = engine.compute_surface_roughness()
    hazards = engine.compute_hazard_mask(critical_slope_deg=15.0, critical_roughness_m=1.0)

    print(f"    Mean Surface Slope:  {np.mean(slope):.2f}° (Max: {np.max(slope):.2f}°)")
    print(f"    Mean RMS Roughness:  {np.mean(roughness):.3f} m")
    hazard_pct = (np.sum(hazards) / hazards.size) * 100.0
    print(f"    Hazard Zone Density: {hazard_pct:.2f}% of terrain flagged as critical")

    # 3. Evaluate Candidate Sites
    print("\n[*] Performing Localized Site Stability Evaluations:")
    sites = [
        ("site_01_north_plateau", 38, 217, "North Rim Plateau (Proposed Base)"),
        ("site_02_basin_floor", 150, 130, "Central Crater Floor"),
        ("site_03_steep_escarpment", 141, 38, "South-West Crater Rim Wall"),
    ]

    profiles = []
    for s_id, r, c, desc in sites:
        prof = engine.evaluate_site(s_id, center_row=r, center_col=c, radius_pixels=15)
        profiles.append(prof)
        print(f"\n    [{s_id.upper()}] - {desc}")
        print(f"      • Coordinates:      Lat {prof.center_lat:.3f}°, Lon {prof.center_lon:.3f}°")
        print(f"      • Mean Slope:       {prof.mean_slope_deg:.2f}° (Max: {prof.max_slope_deg:.2f}°)")
        print(f"      • Roughness (RMS):  {prof.mean_roughness_rms_m:.3f} m")
        print(f"      • Hazard Density:   {prof.hazard_cell_ratio * 100:.1f}%")
        print(f"      • Stability Score:  {prof.terrain_stability_score:.1f} / 100 ({prof.terrain_verdict})")

    # 4. Export Artifacts
    out_dir = Path("outputs/nexus_terrain")
    out_dir.mkdir(parents=True, exist_ok=True)

    report_path = out_dir / "terrain_intelligence_report.json"
    data_out = {
        "region": "Boguslawsky Lunar Highland",
        "dem_resolution_m": resolution_m,
        "grid_shape": [size, size],
        "statistics": {
            "mean_elevation_m": round(float(np.mean(dem)), 2),
            "mean_slope_deg": round(float(np.mean(slope)), 2),
            "max_slope_deg": round(float(np.max(slope)), 2),
            "hazard_area_pct": round(hazard_pct, 2),
        },
        "candidate_site_evaluations": [p.to_dict() for p in profiles],
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(data_out, f, indent=2)

    print(f"\n[✓] Terrain Intelligence Report: {report_path}")
    print("=" * 72)
    print(" NEXUS POC 2 COMPLETED SUCCESSFULLY")
    print("=" * 72)


if __name__ == "__main__":
    run_demo()
