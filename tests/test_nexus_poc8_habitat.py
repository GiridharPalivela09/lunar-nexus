"""Tests for NEXUS POC 8: Habitat Constraint Planner & 3D Digital Twin Engine."""

import json
import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.nexus_core.poc2_terrain_intelligence import (
    generate_synthetic_boguslawsky_dem,
)
from packages.nexus_core.poc8_habitat_planner import (
    BaseLayoutPlan,
    HabitatConstraintPlanner,
    export_dem_to_obj_mesh,
)


def test_habitat_constraint_planner_layout_generation():
    """Verify modular habitat layout generation and constraint checks."""
    dem = generate_synthetic_boguslawsky_dem(size=256, resolution_m=5.0)
    planner = HabitatConstraintPlanner(dem, resolution_m=5.0)

    # Place habitat near the smooth North Rim plateau (+380m X, +350m Y)
    plan = planner.generate_layout(
        site_id="site_boguslawsky_rim",
        site_name="North Rim Base Site",
        hab_center_offset=(380.0, 350.0),
    )

    assert isinstance(plan, BaseLayoutPlan)
    assert len(plan.modules) == 5
    assert len(plan.constraint_checks) == 3

    # Check component types
    module_types = {m.module_type for m in plan.modules}
    assert "HABITAT_CORE" in module_types
    assert "SOLAR_FARM" in module_types
    assert "LANDING_PAD" in module_types
    assert "REGOLITH_BERM" in module_types
    assert "RESOURCE_STATION" in module_types

    # Constraint: Landing pad standoff distance must be >= 1000m
    standoff_check = next(c for c in plan.constraint_checks if c.target_component == "LANDING_PAD")
    assert standoff_check.is_satisfied
    assert standoff_check.actual_value >= 1000.0


def test_dem_to_obj_mesh_export(tmp_path: Path):
    """Verify 3D Wavefront OBJ mesh export format and vertex generation."""
    dem = np.zeros((32, 32), dtype=np.float64)
    dem[10:20, 10:20] = 15.0

    obj_path = tmp_path / "test_terrain.obj"
    export_dem_to_obj_mesh(dem, resolution_m=10.0, output_obj_path=obj_path, subsample_factor=2)

    assert obj_path.exists()
    content = obj_path.read_text()
    assert "v " in content  # Vertices
    assert "vt " in content  # Texture coordinates
    assert "f " in content  # Faces
    assert "terrain_surface" in content
