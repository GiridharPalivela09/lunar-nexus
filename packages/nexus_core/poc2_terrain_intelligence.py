"""NEXUS POC 2: Terrain Intelligence Engine.

Derives engineering-grade spatial metrics from Digital Elevation Models (DEM):
- Slope (Zevenbergen-Thorne / Horn finite difference)
- Aspect (compass azimuth of steepest descent)
- Surface Roughness (RMS elevation standard deviation)
- Curvature (plan and profile terrain curvature)
- Hazard boundary detection (steep crater escarpments, boulder fields)
- Candidate site terrain stability scoring (0 - 100)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.ndimage import uniform_filter

logger = logging.getLogger(__name__)


@dataclass
class TerrainProfile:
    """Quantitative terrain characteristics for a localized lunar site or patch."""
    site_id: str
    center_lat: float
    center_lon: float
    mean_elevation_m: float
    min_elevation_m: float
    max_elevation_m: float
    elevation_range_m: float
    mean_slope_deg: float
    max_slope_deg: float
    slope_p95_deg: float
    mean_roughness_rms_m: float
    hazard_cell_ratio: float
    terrain_stability_score: float
    terrain_verdict: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "site_id": self.site_id,
            "coordinates": {"lat": self.center_lat, "lon": self.center_lon},
            "elevation": {
                "mean_m": round(self.mean_elevation_m, 2),
                "min_m": round(self.min_elevation_m, 2),
                "max_m": round(self.max_elevation_m, 2),
                "relief_m": round(self.elevation_range_m, 2),
            },
            "slope": {
                "mean_deg": round(self.mean_slope_deg, 2),
                "max_deg": round(self.max_slope_deg, 2),
                "p95_deg": round(self.slope_p95_deg, 2),
            },
            "roughness_rms_m": round(self.mean_roughness_rms_m, 3),
            "hazard_density_pct": round(self.hazard_cell_ratio * 100, 2),
            "stability_score": round(self.terrain_stability_score, 1),
            "verdict": self.terrain_verdict,
        }


class TerrainIntelligenceEngine:
    """Analyzes 2D lunar elevation rasters to extract morphometric and engineering metrics."""

    def __init__(
        self,
        elevation_grid: np.ndarray,
        resolution_m: float = 5.0,
        bounds: Optional[Tuple[float, float, float, float]] = None,
    ):
        """
        Args:
            elevation_grid: 2D numpy array of surface heights in meters.
            resolution_m: Ground sampling distance in meters per pixel.
            bounds: Tuple of (min_lat, max_lat, min_lon, max_lon).
        """
        if elevation_grid.ndim != 2:
            raise ValueError(f"Elevation grid must be 2D, got shape {elevation_grid.shape}")

        self.elevation = elevation_grid.astype(np.float64)
        self.resolution_m = float(resolution_m)
        self.height, self.width = self.elevation.shape
        self.bounds = bounds or (-73.1, -72.6, 42.8, 43.6)

        # Lazily computed raster maps
        self._slope_deg: Optional[np.ndarray] = None
        self._aspect_deg: Optional[np.ndarray] = None
        self._roughness: Optional[np.ndarray] = None
        self._hazard_mask: Optional[np.ndarray] = None

    # -------------------------------------------------------------------------
    # Core Geomorphometric Derivative Calculations
    # -------------------------------------------------------------------------
    def compute_slope_and_aspect(self) -> Tuple[np.ndarray, np.ndarray]:
        """Calculates surface slope and aspect using Horn's 3x3 finite-difference operator.

        Returns:
            slope_deg: Slope raster in degrees [0, 90].
            aspect_deg: Aspect raster in degrees [0, 360], where 0 = North, 90 = East.
        """
        if self._slope_deg is not None and self._aspect_deg is not None:
            return self._slope_deg, self._aspect_deg

        res = self.resolution_m
        z = self.elevation

        # Pad borders to handle edges seamlessly
        padded = np.pad(z, pad_width=1, mode="edge")

        # 3x3 neighbors
        z1 = padded[:-2, :-2]
        z2 = padded[:-2, 1:-1]
        z3 = padded[:-2, 2:]
        z4 = padded[1:-1, :-2]
        z6 = padded[1:-1, 2:]
        z7 = padded[2:, :-2]
        z8 = padded[2:, 1:-1]
        z9 = padded[2:, 2:]

        # Finite difference gradients (dz/dx and dz/dy)
        # Horn's weighting gives higher weight to orthogonal neighbors
        dz_dx = ((z3 + 2.0 * z6 + z9) - (z1 + 2.0 * z4 + z7)) / (8.0 * res)
        dz_dy = ((z7 + 2.0 * z8 + z9) - (z1 + 2.0 * z2 + z3)) / (8.0 * res)

        # Slope magnitude
        p = dz_dx
        q = dz_dy
        rise_run = np.sqrt(p**2 + q**2)
        slope_rad = np.arctan(rise_run)
        slope_deg = np.degrees(slope_rad)

        # Aspect (direction of steepest descent)
        # aspect = 57.29578 * atan2(dz/dy, -dz/dx)
        aspect_rad = np.arctan2(q, -p)
        aspect_deg = np.degrees(aspect_rad)
        aspect_deg = np.where(aspect_deg < 0, 90.0 - aspect_deg, 360.0 - aspect_deg + 90.0)
        aspect_deg = aspect_deg % 360.0

        self._slope_deg = np.clip(slope_deg, 0.0, 90.0)
        self._aspect_deg = aspect_deg
        return self._slope_deg, self._aspect_deg

    def compute_surface_roughness(self, window_size: int = 5) -> np.ndarray:
        """Calculates surface roughness as the local standard deviation of elevation

        within a moving spatial window (in meters).
        """
        if self._roughness is not None:
            return self._roughness

        z = self.elevation
        mean = uniform_filter(z, size=window_size, mode="reflect")
        mean_sq = uniform_filter(z**2, size=window_size, mode="reflect")
        variance = np.maximum(mean_sq - mean**2, 0.0)
        roughness = np.sqrt(variance)

        self._roughness = roughness
        return self._roughness

    def compute_hazard_mask(
        self,
        critical_slope_deg: float = 15.0,
        critical_roughness_m: float = 1.2,
    ) -> np.ndarray:
        """Flags high-risk lunar terrain:

        - Escarpments / crater rims with slope > critical_slope_deg
        - Boulder-strewn / fractured terrain with roughness > critical_roughness_m
        """
        if self._hazard_mask is not None:
            return self._hazard_mask

        slope, _ = self.compute_slope_and_aspect()
        roughness = self.compute_surface_roughness()

        hazard_mask = (slope >= critical_slope_deg) | (roughness >= critical_roughness_m)
        self._hazard_mask = hazard_mask
        return self._hazard_mask

    # -------------------------------------------------------------------------
    # Localized Candidate Site Evaluation
    # -------------------------------------------------------------------------
    def evaluate_site(
        self,
        site_id: str,
        center_row: int,
        center_col: int,
        radius_pixels: int = 20,
    ) -> TerrainProfile:
        """Extracts and scores a localized candidate site radius."""
        slope_grid, _ = self.compute_slope_and_aspect()
        roughness_grid = self.compute_surface_roughness()
        hazard_grid = self.compute_hazard_mask()

        # Extract circular or bounding window
        r0 = max(0, center_row - radius_pixels)
        r1 = min(self.height, center_row + radius_pixels + 1)
        c0 = max(0, center_col - radius_pixels)
        c1 = min(self.width, center_col + radius_pixels + 1)

        sub_elev = self.elevation[r0:r1, c0:c1]
        sub_slope = slope_grid[r0:r1, c0:c1]
        sub_rough = roughness_grid[r0:r1, c0:c1]
        sub_hazard = hazard_grid[r0:r1, c0:c1]

        # Convert row/col to approximate lat/lon
        min_lat, max_lat, min_lon, max_lon = self.bounds
        lat = max_lat - (center_row / self.height) * (max_lat - min_lat)
        lon = min_lon + (center_col / self.width) * (max_lon - min_lon)

        mean_elev = float(np.mean(sub_elev))
        min_elev = float(np.min(sub_elev))
        max_elev = float(np.max(sub_elev))
        elevation_range = max_elev - min_elev

        mean_slope = float(np.mean(sub_slope))
        max_slope = float(np.max(sub_slope))
        p95_slope = float(np.percentile(sub_slope, 95))
        mean_roughness = float(np.mean(sub_rough))
        hazard_ratio = float(np.mean(sub_hazard))

        # Terrain Stability Score (0 to 100)
        # High score = flat, smooth, hazard-free
        # Base: 100
        score = 100.0

        # Slope penalty
        if mean_slope > 3.0:
            score -= (mean_slope - 3.0) * 5.0
        if max_slope > 10.0:
            score -= (max_slope - 10.0) * 3.0

        # Roughness penalty
        if mean_roughness > 0.3:
            score -= (mean_roughness - 0.3) * 35.0

        # Hazard ratio penalty (any hazard in proximity is penalized heavily)
        score -= hazard_ratio * 60.0

        stability_score = float(np.clip(score, 0.0, 100.0))

        if stability_score >= 80.0:
            verdict = "EXCELLENT_TERRAIN"
        elif stability_score >= 60.0:
            verdict = "ACCEPTABLE_TERRAIN"
        elif stability_score >= 40.0:
            verdict = "MARGINAL_RISK"
        else:
            verdict = "HAZARDOUS_TERRAIN"

        return TerrainProfile(
            site_id=site_id,
            center_lat=lat,
            center_lon=lon,
            mean_elevation_m=mean_elev,
            min_elevation_m=min_elev,
            max_elevation_m=max_elev,
            elevation_range_m=elevation_range,
            mean_slope_deg=mean_slope,
            max_slope_deg=max_slope,
            slope_p95_deg=p95_slope,
            mean_roughness_rms_m=mean_roughness,
            hazard_cell_ratio=hazard_ratio,
            terrain_stability_score=stability_score,
            terrain_verdict=verdict,
        )


# -----------------------------------------------------------------------------
# Synthetic & Real DEM Generator for Testing & Simulation
# -----------------------------------------------------------------------------
def generate_synthetic_boguslawsky_dem(
    size: int = 256,
    resolution_m: float = 5.0,
    seed: int = 42,
) -> np.ndarray:
    """Generates a scientifically grounded DEM containing:

    - A large impact crater basin (Boguslawsky model)
    - Raised rim escarpment with variable slope
    - North rim plateau suitable for landing
    - Rough micro-topography with fractal noise
    """
    rng = np.random.default_rng(seed)
    y, x = np.ogrid[:size, :size]
    center_y, center_x = size * 0.55, size * 0.50

    dist_from_center = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
    crater_radius = size * 0.35

    # Base highland plateau elevation (~ -1000m)
    elevation = np.full((size, size), -1000.0, dtype=np.float64)

    # Rim crest (+45m elevation above base at radius, producing realistic 15-22 deg rim slopes)
    rim_profile = 45.0 * np.exp(-((dist_from_center - crater_radius) ** 2) / (2 * (size * 0.06) ** 2))
    elevation += rim_profile

    # Crater bowl depression (-75m depth inside rim)
    bowl_mask = dist_from_center < crater_radius
    bowl_depth = -75.0 * (1.0 - (dist_from_center / crater_radius) ** 2)
    elevation[bowl_mask] += bowl_depth[bowl_mask]

    # Smooth North Rim Plateau (Candidate Site 01 region around row size*0.15, col size*0.85)
    plateau_dist = np.sqrt((x - size * 0.85) ** 2 + (y - size * 0.15) ** 2)
    plateau_lift = 12.0 * np.exp(-(plateau_dist**2) / (2 * (size * 0.15) ** 2))
    elevation += plateau_lift

    # Add gentle micro-topography
    noise = rng.normal(0.0, 0.15, size=(size, size))
    elevation += uniform_filter(noise, size=3)

    return elevation
