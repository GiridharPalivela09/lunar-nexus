#!/usr/bin/env python3
"""NEXUS POC 4 Demo: IIRS Spectral & Resource Intelligence.

Demonstrates:
1. Simulating Chandrayaan-2 IIRS (0.8 - 5.0 µm) hyperspectral reflectance cubes
2. Computing 2.85 µm hydroxyl ($BD_{3000}$) absorption band depth
3. Mapping 1.05 µm pyroxene / olivine mafic mineral absorption indices
4. Generating multi-component spatial resource indicator maps
5. Evaluating candidate landing/habitat sites for in-situ resource proxies
"""

import json
import sys
from pathlib import Path
import numpy as np

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.nexus_core.poc4_resource_intelligence import (
    IIRSResourceEngine,
    generate_synthetic_iirs_cube,
)


def run_demo():
    print("=" * 72)
    print(" NEXUS POC 4: IIRS SPECTRAL & RESOURCE INTELLIGENCE ENGINE")
    print("=" * 72)

    # 1. Initialize Hyperspectral Cube
    print("\n[*] Initializing Chandrayaan-2 IIRS Hyperspectral Observation...")
    height, width, num_bands = 64, 64, 64
    cube, wavelengths = generate_synthetic_iirs_cube(
        height=height, width=width, num_bands=num_bands, seed=42
    )
    engine = IIRSResourceEngine(cube, wavelengths, resolution_m=20.0)

    print(f"    Spatial Grid:        {width} x {height} pixels ({width * 20 / 1000.0:.2f} km footprint)")
    print(f"    Spectral Channels:   {num_bands} contiguous bands ({wavelengths[0]:.2f} µm to {wavelengths[-1]:.2f} µm)")
    print(f"    Spectral Resolution: ~{(wavelengths[1] - wavelengths[0]) * 1000:.1f} nm per channel")

    # 2. Extract Diagnostic Spectral Features
    print("\n[*] Deriving Diagnostic Absorption Features & Mineral Indices...")
    res_maps = engine.compute_resource_maps()

    bd3000 = res_maps["bd_3000_hydroxyl"]
    bd1000 = res_maps["bd_1000_pyroxene"]
    res_index = res_maps["resource_index"]

    print(f"    2.85µm Hydroxyl Depth (BD3000): Mean {np.mean(bd3000) * 100:.2f}% (Max {np.max(bd3000) * 100:.2f}%)")
    print(f"    1.05µm Pyroxene Mafic Depth:    Mean {np.mean(bd1000) * 100:.2f}% (Max {np.max(bd1000) * 100:.2f}%)")
    print(f"    Integrated Resource Confidence: Mean {np.mean(res_index):.3f} (Max {np.max(res_index):.3f})")

    # 3. Evaluate Candidate Sites
    print("\n[*] Evaluating In-Situ Resource Proxies for Candidate Sites:")
    sites = [
        ("site_01_north_plateau", 20, 45, "North Rim Plateau Margin (Near Hydroxyl Anomaly)"),
        ("site_02_ambient_highland", 40, 15, "Ambient Dry Highland Regolith"),
    ]

    profiles = []
    for s_id, r, c, desc in sites:
        prof = engine.evaluate_site_resources(s_id, center_row=r, center_col=c, radius_pixels=5, resource_maps=res_maps)
        profiles.append(prof)
        print(f"\n    [{s_id.upper()}] - {desc}")
        print(f"      • Hydroxyl Band Depth:    {prof.hydroxyl_band_depth_pct:.2f}% (Confidence: {prof.hydroxyl_confidence:.2f})")
        print(f"      • Mafic Mineral Index:    {prof.mafic_pyroxene_index:.3f}")
        print(f"      • Resource Score:         {prof.resource_indicator_score:.1f} / 100")
        print(f"      • Scientific Assessment:  {prof.scientific_summary}")

    # 4. Save Report
    out_dir = Path("outputs/nexus_resource")
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "resource_intelligence_report.json"

    data_out = {
        "instrument": "Chandrayaan-2 IIRS",
        "spectral_range_um": [float(wavelengths[0]), float(wavelengths[-1])],
        "metrics": {
            "mean_hydroxyl_bd3000_pct": round(float(np.mean(bd3000) * 100), 2),
            "max_hydroxyl_bd3000_pct": round(float(np.max(bd3000) * 100), 2),
            "mean_pyroxene_bd1000": round(float(np.mean(bd1000)), 4),
        },
        "site_evaluations": [p.to_dict() for p in profiles],
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(data_out, f, indent=2)

    print(f"\n[✓] Resource Report: {report_path}")
    print("=" * 72)
    print(" NEXUS POC 4 COMPLETED SUCCESSFULLY")
    print("=" * 72)


if __name__ == "__main__":
    run_demo()
