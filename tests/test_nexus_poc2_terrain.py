"""Tests for NEXUS POC 2: Terrain Intelligence Engine."""

import numpy as np
import pytest

from packages.nexus_core.poc2_terrain_intelligence import (
    TerrainIntelligenceEngine,
    TerrainProfile,
    generate_synthetic_boguslawsky_dem,
)


def test_terrain_engine_initialization():
    """Verify TerrainIntelligenceEngine initializes properly with 2D DEM."""
    dem = np.zeros((100, 100))
    engine = TerrainIntelligenceEngine(elevation_grid=dem, resolution_m=10.0)

    assert engine.height == 100
    assert engine.width == 100
    assert engine.resolution_m == 10.0

    with pytest.raises(ValueError):
        TerrainIntelligenceEngine(elevation_grid=np.zeros((10, 10, 3)))


def test_flat_surface_slope_and_roughness():
    """Verify that a perfectly flat surface yields 0 slope and 0 roughness."""
    flat_dem = np.full((50, 50), -1500.0)
    engine = TerrainIntelligenceEngine(flat_dem, resolution_m=5.0)

    slope, aspect = engine.compute_slope_and_aspect()
    roughness = engine.compute_surface_roughness()
    hazards = engine.compute_hazard_mask()

    assert np.allclose(slope, 0.0, atol=1e-5)
    assert np.allclose(roughness, 0.0, atol=1e-5)
    assert np.sum(hazards) == 0


def test_tilted_plane_slope():
    """Verify that a planar ramp with known gradient produces the exact expected slope."""
    res = 5.0
    y, x = np.mgrid[:50, :50]
    # dz/dx = 0.5 -> rise/run = 0.5 -> slope = arctan(0.5) = 26.565 degrees
    tilted_dem = x * (0.5 * res)
    engine = TerrainIntelligenceEngine(tilted_dem, resolution_m=res)

    slope, _ = engine.compute_slope_and_aspect()
    # Exclude borders
    interior_slope = slope[5:-5, 5:-5]
    expected_deg = np.degrees(np.arctan(0.5))
    assert np.allclose(interior_slope, expected_deg, atol=0.1)


def test_synthetic_boguslawsky_dem_analysis():
    """Verify morphometric analysis on realistic crater DEM."""
    dem = generate_synthetic_boguslawsky_dem(size=128, resolution_m=5.0)
    engine = TerrainIntelligenceEngine(dem, resolution_m=5.0)

    slope, aspect = engine.compute_slope_and_aspect()
    roughness = engine.compute_surface_roughness()
    hazards = engine.compute_hazard_mask(critical_slope_deg=15.0)

    assert slope.shape == (128, 128)
    assert aspect.shape == (128, 128)
    assert roughness.shape == (128, 128)

    # Slopes should be reasonable on a lunar crater (e.g. rim walls > 15 deg)
    assert np.max(slope) > 15.0
    assert np.min(slope) >= 0.0
    assert np.sum(hazards) > 0  # rim walls should be flagged as hazards


def test_candidate_site_evaluation_scoring():
    """Verify candidate site extraction distinguishes safe plateau from steep crater rim."""
    dem = generate_synthetic_boguslawsky_dem(size=256, resolution_m=5.0)
    engine = TerrainIntelligenceEngine(dem, resolution_m=5.0)

    # 1. North Rim Plateau (smooth zone around row 38, col 217)
    plateau_profile = engine.evaluate_site("site_plateau", center_row=38, center_col=217, radius_pixels=15)
    assert isinstance(plateau_profile, TerrainProfile)
    assert plateau_profile.mean_slope_deg < 8.0
    assert plateau_profile.terrain_stability_score > 60.0

    # 2. Steep Crater Rim Wall (around row 141, col 38)
    rim_profile = engine.evaluate_site("site_steep_rim", center_row=141, center_col=38, radius_pixels=15)
    assert rim_profile.max_slope_deg > 10.0
    # Rim profile must score lower than smooth plateau
    assert rim_profile.terrain_stability_score < plateau_profile.terrain_stability_score
