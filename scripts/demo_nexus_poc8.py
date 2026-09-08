#!/usr/bin/env python3
"""NEXUS POC 8 Demo: Habitat Constraint Planner & 3D Digital Twin.

Demonstrates:
1. Translating spatial constraints into an optimized modular lunar base layout
2. Verifying engineering constraints (slope limits, >1000m landing standoff buffer, cabling limits)
3. Exporting 3D Wavefront OBJ terrain mesh from high-resolution DEM
4. Exporting structured Digital Twin layout for Three.js WebGL and Blender rendering
"""

import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.nexus_core.poc2_terrain_intelligence import (
    generate_synthetic_boguslawsky_dem,
)
from packages.nexus_core.poc8_habitat_planner import (
    HabitatConstraintPlanner,
    export_dem_to_obj_mesh,
)


def run_demo():
    print("=" * 72)
    print(" NEXUS POC 8: HABITAT CONSTRAINT PLANNER & 3D DIGITAL TWIN")
    print("=" * 72)

    # 1. Initialize Terrain & Planner
    print("\n[*] Initializing Lunar Elevation Grid for Habitat Layout Planning...")
    resolution_m = 5.0
    size = 256
    dem = generate_synthetic_boguslawsky_dem(size=size, resolution_m=resolution_m)
    planner = HabitatConstraintPlanner(dem, resolution_m=resolution_m)

    # 2. Generate Constraint-Driven Base Layout
    print("\n[*] Synthesizing Engineering Constraints to Place Base Modules...")
    # Offset center towards favorable North Rim plateau (+380m X, +350m Y)
    plan = planner.generate_layout(
        site_id="site_candidate_01_north_rim",
        site_name="North Rim Base Site #01",
        hab_center_offset=(380.0, 350.0),
    )

    print(f"    Base Layout Status:    {'[✓] ALL CONSTRAINTS SATISFIED' if plan.all_constraints_passed else '[!] VIOLATION DETECTED'}")
    print(f"    Total Installed Power: {plan.total_power_capacity_kw:.1f} kW")
    print(f"    Occupied Footprint:    {plan.total_footprint_area_m2:.1f} m²")

    print("\n    [+] Deployed Habitat Infrastructure Modules:")
    for m in plan.modules:
        pos = m.to_dict()["position_m"]
        print(f"        • {m.name:45s} -> Pos: ({pos['x']:+7.1f}m, {pos['y']:+7.1f}m, {pos['z']:+7.1f}m) | Slope: {m.slope_at_site_deg:.1f}°")

    print("\n    [+] Engineering Constraint Verification Checks:")
    for c in plan.constraint_checks:
        status_sym = "[PASS]" if c.is_satisfied else "[FAIL]"
        print(f"        • {status_sym} {c.rule_name:30s}: Measured {c.actual_value:7.1f} {c.unit} (Threshold {c.threshold_value:.1f} {c.unit})")
        print(f"               Details: {c.details}")

    # 3. Export 3D Digital Twin Mesh (.obj)
    out_dir = Path("outputs/nexus_3d")
    out_dir.mkdir(parents=True, exist_ok=True)
    obj_path = out_dir / "nexus_boguslawsky_mesh.obj"

    print(f"\n[*] Generating 3D Polygon Mesh for Digital Twin...")
    export_dem_to_obj_mesh(dem, resolution_m=resolution_m, output_obj_path=obj_path, subsample_factor=2)
    print(f"    [✓] 3D Mesh Saved: {obj_path} ({obj_path.stat().st_size / 1024:.1f} KB)")

    # 4. Save Layout JSON
    layout_path = out_dir / "habitat_layout_plan.json"
    with open(layout_path, "w", encoding="utf-8") as f:
        json.dump(plan.to_dict(), f, indent=2)

    print(f"    [✓] Digital Twin Layout JSON: {layout_path}")
    print("=" * 72)
    print(" NEXUS POC 8 COMPLETED SUCCESSFULLY")
    print("=" * 72)


if __name__ == "__main__":
    run_demo()
