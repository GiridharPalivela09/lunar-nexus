"""NEXUS POC 3: Illumination & Solar Power Intelligence Engine.

Turns the SIH illumination variation challenge into mission intelligence:
- Solar vector geometry (elevation, azimuth) for high-latitude polar lunar regions
- Physical shadow-casting raytracer over Digital Elevation Models (DEM)
- Incident solar irradiance accounting for terrain slope and aspect
- Diurnal cycle simulation across 360° solar rotation (708h lunar day)
- Delineation of:
  * Peaks of Eternal Light (PEL candidates: >70% illumination)
  * Permanently Shadowed Regions (PSRs: 0% illumination cold traps)
  * Solar photovoltaic power potential (kWh/m²/lunar day)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Solar constant at lunar distance (~1361 W/m^2)
SOLAR_CONSTANT_W_M2 = 1361.0
LUNAR_DAY_HOURS = 708.7


@dataclass
class IlluminationProfile:
    """Illumination and solar energy profile for a localized site."""
    site_id: str
    mean_illumination_fraction: float
    min_illumination_fraction: float
    max_illumination_fraction: float
    is_pel_candidate: bool
    is_psr_cold_trap: bool
    estimated_solar_energy_kwh_m2: float
    solar_suitability_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "site_id": self.site_id,
            "illumination_fraction_pct": round(self.mean_illumination_fraction * 100, 2),
            "range_pct": [
                round(self.min_illumination_fraction * 100, 2),
                round(self.max_illumination_fraction * 100, 2),
            ],
            "classification": (
                "PEAK_OF_ETERNAL_LIGHT_CANDIDATE"
                if self.is_pel_candidate
                else ("PERMANENTLY_SHADOWED_REGION" if self.is_psr_cold_trap else "MODERATE_SOLAR_ZONE")
            ),
            "solar_energy_yield_kwh_m2": round(self.estimated_solar_energy_kwh_m2, 2),
            "solar_score": round(self.solar_suitability_score, 1),
        }


class IlluminationIntelligenceEngine:
    """Simulates physical solar rays, shadow casting, and solar power harvest across lunar terrain."""

    def __init__(
        self,
        elevation_grid: np.ndarray,
        resolution_m: float = 5.0,
        slope_grid: Optional[np.ndarray] = None,
        aspect_grid: Optional[np.ndarray] = None,
    ):
        """
        Args:
            elevation_grid: 2D numpy array of elevation in meters.
            resolution_m: Pixel spacing in meters.
            slope_grid: Precomputed slope grid in degrees (optional).
            aspect_grid: Precomputed aspect grid in degrees (optional).
        """
        if elevation_grid.ndim != 2:
            raise ValueError("Elevation grid must be 2D.")

        self.elevation = elevation_grid.astype(np.float64)
        self.resolution_m = float(resolution_m)
        self.height, self.width = self.elevation.shape

        if slope_grid is None or aspect_grid is None:
            from packages.nexus_core.poc2_terrain_intelligence import (
                TerrainIntelligenceEngine,
            )
            t_engine = TerrainIntelligenceEngine(self.elevation, resolution_m=self.resolution_m)
            self.slope_deg, self.aspect_deg = t_engine.compute_slope_and_aspect()
        else:
            self.slope_deg = slope_grid
            self.aspect_deg = aspect_grid

    # -------------------------------------------------------------------------
    # Raytraced Shadow Casting
    # -------------------------------------------------------------------------
    def compute_shadow_mask(
        self,
        sun_elevation_deg: float,
        sun_azimuth_deg: float,
        max_ray_distance_pixels: int = 150,
    ) -> np.ndarray:
        """Computes direct line-of-sight shadow casting from terrain obstructions.

        Args:
            sun_elevation_deg: Sun height above horizon in degrees (>0).
            sun_azimuth_deg: Solar azimuth (0=N, 90=E, 180=S, 270=W).
            max_ray_distance_pixels: Maximum horizon search distance.

        Returns:
            illuminated_mask: Boolean 2D array where True = direct sunlight, False = shadow.
        """
        if sun_elevation_deg <= 0.0:
            # Sun below horizon -> total darkness
            return np.zeros((self.height, self.width), dtype=bool)

        sun_elev_rad = np.radians(sun_elevation_deg)
        tan_elev = np.tan(sun_elev_rad)

        # Azimuth direction vector (pointing TOWARDS the sun)
        # Azimuth: 0=N (-y), 90=E (+x), 180=S (+y), 270=W (-x)
        az_rad = np.radians(sun_azimuth_deg)
        dir_x = np.sin(az_rad)
        dir_y = -np.cos(az_rad)

        # Normalize step length
        step_len = max(abs(dir_x), abs(dir_y))
        if step_len > 0:
            dx = dir_x / step_len
            dy = dir_y / step_len
        else:
            dx, dy = 0.0, 0.0

        illuminated = np.ones((self.height, self.width), dtype=bool)

        # 1. Local slope self-shadowing check
        # Cosine of incidence angle theta_i:
        slope_rad = np.radians(self.slope_deg)
        aspect_rad = np.radians(self.aspect_deg)
        cos_inc = np.sin(sun_elev_rad) * np.cos(slope_rad) + np.cos(sun_elev_rad) * np.sin(slope_rad) * np.cos(az_rad - aspect_rad)
        self_shadow = cos_inc <= 0.0
        illuminated[self_shadow] = False

        # 2. Raytracing for external horizon shadows
        # Cast ray steps outward towards the sun
        curr_x = np.broadcast_to(np.arange(self.width, dtype=np.float64), (self.height, self.width)).copy()
        curr_y = np.broadcast_to(np.arange(self.height, dtype=np.float64)[:, None], (self.height, self.width)).copy()

        # Vectorized stepping along ray
        for step in range(1, max_ray_distance_pixels + 1):
            curr_x += dx
            curr_y += dy

            ix = np.round(curr_x).astype(np.int32)
            iy = np.round(curr_y).astype(np.int32)

            valid = (ix >= 0) & (ix < self.width) & (iy >= 0) & (iy < self.height)
            if not np.any(valid):
                break

            # Distance along ray in meters
            dist_m = step * self.resolution_m
            ray_elev_threshold = self.elevation + dist_m * tan_elev

            # Check if terrain at (iy, ix) blocks the sun
            terrain_elev = np.zeros_like(self.elevation)
            terrain_elev[valid] = self.elevation[iy[valid], ix[valid]]

            blocked = valid & (terrain_elev > ray_elev_threshold)
            illuminated[blocked] = False

        return illuminated

    # -------------------------------------------------------------------------
    # Diurnal Solar Cycle Simulation
    # -------------------------------------------------------------------------
    def simulate_diurnal_cycle(
        self,
        mean_sun_elevation_deg: float = 3.5,
        num_azimuth_steps: int = 16,
    ) -> Dict[str, np.ndarray]:
        """Simulates the 360-degree solar rotation over one lunar day.

        Returns dictionary containing:
        - illumination_fraction: (H, W) array of fraction of time illuminated [0.0, 1.0]
        - pel_mask: Peaks of Eternal Light candidates (> 0.70)
        - psr_mask: Permanently Shadowed Regions (== 0.0)
        - solar_energy_kwh_m2: Cumulative energy density
        """
        azimuths = np.linspace(0.0, 360.0, num_azimuth_steps, endpoint=False)
        illum_accumulator = np.zeros((self.height, self.width), dtype=np.float64)

        for az in azimuths:
            shadow_mask = self.compute_shadow_mask(
                sun_elevation_deg=mean_sun_elevation_deg,
                sun_azimuth_deg=az,
                max_ray_distance_pixels=80,
            )
            illum_accumulator += shadow_mask.astype(np.float64)

        illum_fraction = illum_accumulator / float(num_azimuth_steps)

        # Classifications
        pel_mask = illum_fraction >= 0.70
        psr_mask = illum_fraction == 0.0

        # Energy yield: Solar constant * illumination fraction * duration in hours / 1000
        # Efficiency proxy ~ 25% for solar panels
        solar_energy_kwh = (SOLAR_CONSTANT_W_M2 / 1000.0) * illum_fraction * (LUNAR_DAY_HOURS * 0.5)

        return {
            "illumination_fraction": illum_fraction,
            "pel_mask": pel_mask,
            "psr_mask": psr_mask,
            "solar_energy_kwh_m2": solar_energy_kwh,
        }

    # -------------------------------------------------------------------------
    # Site Solar Evaluation
    # -------------------------------------------------------------------------
    def evaluate_site_solar(
        self,
        site_id: str,
        center_row: int,
        center_col: int,
        radius_pixels: int = 15,
        diurnal_results: Optional[Dict[str, np.ndarray]] = None,
    ) -> IlluminationProfile:
        """Evaluates localized solar availability and power yield for a site."""
        if diurnal_results is None:
            diurnal_results = self.simulate_diurnal_cycle()

        illum = diurnal_results["illumination_fraction"]
        energy = diurnal_results["solar_energy_kwh_m2"]

        r0 = max(0, center_row - radius_pixels)
        r1 = min(self.height, center_row + radius_pixels + 1)
        c0 = max(0, center_col - radius_pixels)
        c1 = min(self.width, center_col + radius_pixels + 1)

        sub_illum = illum[r0:r1, c0:c1]
        sub_energy = energy[r0:r1, c0:c1]

        mean_illum = float(np.mean(sub_illum))
        min_illum = float(np.min(sub_illum))
        max_illum = float(np.max(sub_illum))
        mean_energy = float(np.mean(sub_energy))

        is_pel = bool(mean_illum >= 0.70)
        is_psr = bool(mean_illum == 0.0)

        # Score (0 to 100) based on continuous energy harvest
        # 100% illumination -> 100, 50% -> 50, 0% -> 0
        suitability_score = float(np.clip(mean_illum * 100.0, 0.0, 100.0))

        return IlluminationProfile(
            site_id=site_id,
            mean_illumination_fraction=mean_illum,
            min_illumination_fraction=min_illum,
            max_illumination_fraction=max_illum,
            is_pel_candidate=is_pel,
            is_psr_cold_trap=is_psr,
            estimated_solar_energy_kwh_m2=mean_energy,
            solar_suitability_score=suitability_score,
        )
