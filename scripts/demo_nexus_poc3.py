#!/usr/bin/env python3
"""NEXUS POC 3 Demo: Illumination & Solar Power Intelligence.

Demonstrates:
1. Simulating solar illumination and shadow casting over lunar terrain
2. Tracing the 360-degree diurnal solar cycle (708-hour lunar synodic day)
3. Identifying Peaks of Eternal Light (PEL) candidates and Permanently Shadowed Regions (PSRs)
4. Estimating solar photovoltaic energy generation yield (kWh/m²)
5. Evaluating candidate landing/habitat sites for energy viability
"""

import json
import sys
from pathlib import Path
import numpy as np

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.nexus_core.poc2_terrain_intelligence import (
    generate_synthetic_boguslawsky_dem,
)
from packages.nexus_core.poc3_illumination_intelligence import (
    IlluminationIntelligenceEngine,
)


def run_demo():
    print("=" * 72)
    print(" NEXUS POC 3: ILLUMINATION & SOLAR POWER INTELLIGENCE ENGINE")
    print("=" * 72)

    # 1. Initialize Elevation Grid
    print("\n[*] Initializing Lunar DEM for Solar Shadow Raytracing...")
    resolution_m = 5.0
    size = 256
    dem = generate_synthetic_boguslawsky_dem(size=size, resolution_m=resolution_m)
    engine = IlluminationIntelligenceEngine(dem, resolution_m=resolution_m)

    # 2. Run Diurnal Cycle Simulation
    print("\n[*] Simulating 708-Hour Diurnal Solar Cycle (Low-Elevation Polar Sun)...")
    diurnal = engine.simulate_diurnal_cycle(mean_sun_elevation_deg=3.5, num_azimuth_steps=16)

    illum = diurnal["illumination_fraction"]
    pels = diurnal["pel_mask"]
    psrs = diurnal["psr_mask"]
    energy = diurnal["solar_energy_kwh_m2"]

    pel_pct = (np.sum(pels) / pels.size) * 100.0
    psr_pct = (np.sum(psrs) / psrs.size) * 100.0

    print(f"    Mean Regional Illumination: {np.mean(illum) * 100:.2f}%")
    print(f"    Peak Illumination Reached:  {np.max(illum) * 100:.2f}%")
    print(f"    PEL Zone Area (>70% Sun):   {pel_pct:.2f}% of terrain (High Solar Potential)")
    print(f"    PSR Zone Area (0% Sun):     {psr_pct:.2f}% of terrain (Volatile Cold Traps)")
    print(f"    Max Solar Harvest Yield:    {np.max(energy):.1f} kWh/m² / lunar day")

    # 3. Evaluate Specific Candidate Sites
    print("\n[*] Assessing Solar Viability for Candidate Sites:")
    sites = [
        ("site_01_north_plateau", 38, 217, "North Rim Plateau (Proposed Base)"),
        ("site_02_crater_bowl", 141, 128, "Deep Crater Interior Basin"),
        ("site_03_steep_rim", 141, 38, "South-West Escarpment"),
    ]

    profiles = []
    for s_id, r, c, desc in sites:
        prof = engine.evaluate_site_solar(s_id, center_row=r, center_col=c, radius_pixels=15, diurnal_results=diurnal)
        profiles.append(prof)
        print(f"\n    [{s_id.upper()}] - {desc}")
        print(f"      • Mean Sunlight Access:   {prof.mean_illumination_fraction * 100:.1f}% (Range: {prof.min_illumination_fraction*100:.1f}% - {prof.max_illumination_fraction*100:.1f}%)")
        print(f"      • Classification:         {prof.to_dict()['classification']}")
        print(f"      • Solar Power Yield:      {prof.estimated_solar_energy_kwh_m2:.1f} kWh/m²")
        print(f"      • Solar Energy Score:     {prof.solar_suitability_score:.1f} / 100")

    # 4. Save Report
    out_dir = Path("outputs/nexus_illumination")
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "illumination_intelligence_report.json"

    data_out = {
        "region": "Boguslawsky Polar Highland",
        "sun_elevation_deg": 3.5,
        "azimuth_steps": 16,
        "metrics": {
            "mean_illumination_pct": round(float(np.mean(illum) * 100), 2),
            "pel_candidate_area_pct": round(pel_pct, 2),
            "psr_cold_trap_area_pct": round(psr_pct, 2),
            "max_solar_energy_yield_kwh_m2": round(float(np.max(energy)), 2),
        },
        "site_evaluations": [p.to_dict() for p in profiles],
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(data_out, f, indent=2)

    print(f"\n[✓] Illumination Report: {report_path}")
    print("=" * 72)
    print(" NEXUS POC 3 COMPLETED SUCCESSFULLY")
    print("=" * 72)


if __name__ == "__main__":
    run_demo()
