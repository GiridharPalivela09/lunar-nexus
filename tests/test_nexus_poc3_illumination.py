"""Tests for NEXUS POC 3: Illumination & Solar Power Intelligence Engine."""

import numpy as np
import pytest

from packages.nexus_core.poc2_terrain_intelligence import (
    generate_synthetic_boguslawsky_dem,
)
from packages.nexus_core.poc3_illumination_intelligence import (
    IlluminationIntelligenceEngine,
    IlluminationProfile,
)


def test_illumination_engine_initialization():
    """Verify illumination engine initializes and checks 2D inputs."""
    dem = np.zeros((64, 64))
    engine = IlluminationIntelligenceEngine(dem, resolution_m=10.0)
    assert engine.height == 64
    assert engine.width == 64

    with pytest.raises(ValueError):
        IlluminationIntelligenceEngine(np.zeros((10, 10, 2)))


def test_flat_surface_full_illumination():
    """Verify that a flat surface with sun above horizon is completely illuminated."""
    flat_dem = np.full((32, 32), -1000.0)
    engine = IlluminationIntelligenceEngine(flat_dem, resolution_m=5.0)

    # Sun at 10 degrees elevation from East (azimuth 90)
    mask = engine.compute_shadow_mask(sun_elevation_deg=10.0, sun_azimuth_deg=90.0)
    assert np.all(mask)  # entire flat plane should receive sunlight


def test_sun_below_horizon_is_dark():
    """Verify that sun at or below horizon produces 0 illumination."""
    flat_dem = np.zeros((32, 32))
    engine = IlluminationIntelligenceEngine(flat_dem, resolution_m=5.0)

    mask = engine.compute_shadow_mask(sun_elevation_deg=0.0, sun_azimuth_deg=180.0)
    assert not np.any(mask)

    mask_neg = engine.compute_shadow_mask(sun_elevation_deg=-5.0, sun_azimuth_deg=180.0)
    assert not np.any(mask_neg)


def test_wall_shadow_casting():
    """Verify that a raised wall casts a physical shadow behind it."""
    # 64x64 grid with a vertical wall of +50m at column 20
    dem = np.zeros((64, 64), dtype=np.float64)
    dem[:, 20] = 50.0

    engine = IlluminationIntelligenceEngine(dem, resolution_m=5.0)

    # Sun coming from West (azimuth 270, angle 15 deg)
    # The terrain to the right (East, col > 20) should be in shadow
    mask = engine.compute_shadow_mask(sun_elevation_deg=15.0, sun_azimuth_deg=270.0)

    # Wall at col 20
    # Cells immediately east of the wall (col 21, 22) must be shadowed
    assert np.all(~mask[:, 21:24])
    # Cells west of wall (col 10) must be illuminated
    assert np.all(mask[:, 10])


def test_diurnal_cycle_on_synthetic_crater():
    """Verify diurnal simulation detects illuminated rim vs shadowed bowl."""
    dem = generate_synthetic_boguslawsky_dem(size=128, resolution_m=10.0)
    engine = IlluminationIntelligenceEngine(dem, resolution_m=10.0)

    results = engine.simulate_diurnal_cycle(mean_sun_elevation_deg=4.0, num_azimuth_steps=8)

    illum = results["illumination_fraction"]
    assert illum.shape == (128, 128)
    assert np.all(illum >= 0.0) and np.all(illum <= 1.0)

    # Evaluate Site on North Rim Plateau vs Crater Bowl Floor
    plateau_profile = engine.evaluate_site_solar("plateau", center_row=19, center_col=108, radius_pixels=8, diurnal_results=results)
    bowl_profile = engine.evaluate_site_solar("bowl_floor", center_row=70, center_col=64, radius_pixels=8, diurnal_results=results)

    assert isinstance(plateau_profile, IlluminationProfile)
    # High rim plateau should have substantially more solar exposure than deep crater bowl
    assert plateau_profile.mean_illumination_fraction > bowl_profile.mean_illumination_fraction
    assert plateau_profile.solar_suitability_score > bowl_profile.solar_suitability_score
