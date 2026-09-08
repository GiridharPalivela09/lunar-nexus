"""Tests for NEXUS POC 4: IIRS Spectral & Resource Intelligence Engine."""

import numpy as np
import pytest

from packages.nexus_core.poc4_resource_intelligence import (
    IIRSResourceEngine,
    ResourceProfile,
    generate_synthetic_iirs_cube,
)


def test_iirs_engine_initialization_and_validation():
    """Verify cube dimensions and wavelength array matches."""
    cube = np.zeros((30, 30, 20))
    wl = np.linspace(0.8, 3.2, 20)
    engine = IIRSResourceEngine(cube, wl, resolution_m=20.0)

    assert engine.height == 30
    assert engine.width == 30
    assert engine.num_bands == 20

    with pytest.raises(ValueError):
        # Mismatched band count
        IIRSResourceEngine(cube, wl[:10])

    with pytest.raises(ValueError):
        # Not 3D
        IIRSResourceEngine(np.zeros((10, 10)), wl)


def test_band_depth_flat_continuum():
    """Verify that a flat spectral continuum with no absorption produces 0 band depth."""
    cube = np.full((10, 10, 15), 0.25)
    wl = np.linspace(1.0, 3.5, 15)
    engine = IIRSResourceEngine(cube, wl)

    bd = engine.compute_band_depth(center_um=2.85, continuum_left_um=2.5, continuum_right_um=3.2)
    assert np.allclose(bd, 0.0, atol=1e-5)


def test_synthetic_iirs_absorption_detection():
    """Verify detection of localized 2.85 um hydroxyl absorption anomaly in synthetic cube."""
    cube, wavelengths = generate_synthetic_iirs_cube(height=40, width=40, num_bands=40, seed=123)
    engine = IIRSResourceEngine(cube, wavelengths, resolution_m=20.0)

    res_maps = engine.compute_resource_maps()
    bd3k = res_maps["bd_3000_hydroxyl"]

    assert bd3k.shape == (40, 40)
    assert np.all(bd3k >= 0.0) and np.all(bd3k <= 1.0)

    # Anomaly was placed around (row 20, col 45 -> inside 40x40 grid, let's check high vs low zone)
    # Background should have ~2% absorption, anomaly peak higher
    assert np.max(bd3k) > 0.03
    assert np.min(bd3k) >= 0.0


def test_site_resource_evaluation_and_profiles():
    """Verify evaluation of candidate site resource profiles."""
    cube, wavelengths = generate_synthetic_iirs_cube(height=50, width=50, num_bands=50, seed=42)
    engine = IIRSResourceEngine(cube, wavelengths, resolution_m=20.0)

    profile = engine.evaluate_site_resources("site_01", center_row=20, center_col=45, radius_pixels=4)
    assert isinstance(profile, ResourceProfile)
    assert profile.site_id == "site_01"
    assert profile.hydroxyl_band_depth_pct > 0.0
    assert 0.0 <= profile.hydroxyl_confidence <= 1.0
    assert 0.0 <= profile.resource_indicator_score <= 100.0

    profile_dict = profile.to_dict()
    assert "disclaimer" in profile_dict
    assert "scientific_interpretation" in profile_dict
