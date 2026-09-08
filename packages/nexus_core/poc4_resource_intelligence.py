"""NEXUS POC 4: IIRS Spectral & Resource Intelligence Engine.

Processes Chandrayaan-2 IIRS (0.8 - 5.0 µm) hyperspectral data to derive:
- 2.8 - 3.0 µm hydration/hydroxyl band depth (BD_3000) for volatile proxies
- 1.0 µm & 2.0 µm mafic mineral absorption indices (Pyroxene / Olivine)
- Continuum slope & optical space weathering maturity
- Multi-component spatial resource indicator maps with confidence quantification

Important scientific guideline:
Outputs are characterized as 'spectral indicators' and 'mineral proxies' rather
than definitive economic mining claims.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ResourceProfile:
    """Localized spectral and resource indicator profile for a lunar site."""
    site_id: str
    hydroxyl_band_depth_pct: float
    hydroxyl_confidence: float
    mafic_pyroxene_index: float
    regolith_maturity_index: float
    resource_indicator_score: float
    scientific_summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "site_id": self.site_id,
            "hydroxyl_absorption_bd3000_pct": round(self.hydroxyl_band_depth_pct, 2),
            "hydroxyl_indicator_confidence": round(self.hydroxyl_confidence, 2),
            "mafic_mineral_index": round(self.mafic_pyroxene_index, 3),
            "optical_maturity": round(self.regolith_maturity_index, 2),
            "resource_score": round(self.resource_indicator_score, 1),
            "scientific_interpretation": self.scientific_summary,
            "disclaimer": "Diagnostic spectral proxy; physical ground truth requires in-situ rover sampling.",
        }


class IIRSResourceEngine:
    """Hyperspectral analyzer for Chandrayaan-2 IIRS observations."""

    def __init__(
        self,
        spectral_cube: np.ndarray,
        wavelengths_um: np.ndarray,
        resolution_m: float = 20.0,
    ):
        """
        Args:
            spectral_cube: 3D numpy array of reflectance (Height, Width, Bands).
            wavelengths_um: 1D array of band center wavelengths in micrometers.
            resolution_m: Spatial resolution in meters per pixel.
        """
        if spectral_cube.ndim != 3:
            raise ValueError(f"Spectral cube must be 3D (H, W, Bands), got shape {spectral_cube.shape}")
        if len(wavelengths_um) != spectral_cube.shape[2]:
            raise ValueError(
                f"Number of wavelengths ({len(wavelengths_um)}) must match bands in cube ({spectral_cube.shape[2]})"
            )

        self.cube = spectral_cube.astype(np.float64)
        self.wavelengths = wavelengths_um.astype(np.float64)
        self.height, self.width, self.num_bands = self.cube.shape
        self.resolution_m = float(resolution_m)

    def _find_band_index(self, target_um: float) -> int:
        """Finds closest band index for a given wavelength."""
        return int(np.argmin(np.abs(self.wavelengths - target_um)))

    # -------------------------------------------------------------------------
    # Spectral Band Depth Derivative Calculations
    # -------------------------------------------------------------------------
    def compute_band_depth(
        self,
        center_um: float,
        continuum_left_um: float,
        continuum_right_um: float,
    ) -> np.ndarray:
        """Calculates normalized absorption band depth:

        BD = 1.0 - ( R(center) / R_continuum(center) )
        where R_continuum is linearly interpolated between left and right shoulders.
        """
        idx_c = self._find_band_index(center_um)
        idx_l = self._find_band_index(continuum_left_um)
        idx_r = self._find_band_index(continuum_right_um)

        w_c = self.wavelengths[idx_c]
        w_l = self.wavelengths[idx_l]
        w_r = self.wavelengths[idx_r]

        if w_r == w_l:
            raise ValueError("Continuum shoulders cannot have identical wavelengths.")

        r_c = self.cube[:, :, idx_c]
        r_l = self.cube[:, :, idx_l]
        r_r = self.cube[:, :, idx_r]

        # Linear continuum interpolation at center wavelength
        weight_r = (w_c - w_l) / (w_r - w_l)
        r_continuum = r_l + weight_r * (r_r - r_l)

        # Avoid division by zero
        r_continuum = np.maximum(r_continuum, 1e-6)
        band_depth = 1.0 - (r_c / r_continuum)
        return np.clip(band_depth, 0.0, 1.0)

    def compute_resource_maps(self) -> Dict[str, np.ndarray]:
        """Generates 2D spatial distribution maps for key diagnostic lunar minerals:

        - bd_3000: Hydroxyl / H2O volatile proxy at 2.85 µm
        - bd_1000: 1.0 µm mafic absorption (pyroxene / olivine)
        - bd_2000: 2.0 µm clinopyroxene absorption
        - spectral_slope: VIS-NIR continuum reddening
        """
        # 1. 2.85 um Hydroxyl absorption
        # Shoulders at 2.55 um and 3.20 um
        bd_3000 = self.compute_band_depth(center_um=2.85, continuum_left_um=2.55, continuum_right_um=3.20)

        # 2. 1.05 um Pyroxene/Olivine absorption
        bd_1000 = self.compute_band_depth(center_um=1.05, continuum_left_um=0.85, continuum_right_um=1.50)

        # 3. 2.0 um Pyroxene absorption
        bd_2000 = self.compute_band_depth(center_um=2.00, continuum_left_um=1.55, continuum_right_um=2.40)

        # 4. Visible-to-NIR Slope: (R_1500 - R_0850) / (1.50 - 0.85)
        idx_850 = self._find_band_index(0.85)
        idx_1500 = self._find_band_index(1.50)
        slope = (self.cube[:, :, idx_1500] - self.cube[:, :, idx_850]) / (1.50 - 0.85)

        # Integrated resource indicator index (combining volatile and mineral potential)
        # Higher score near regions with pronounced absorption anomalies
        resource_index = np.clip((bd_3000 * 6.0) + (bd_1000 * 2.0), 0.0, 1.0)

        return {
            "bd_3000_hydroxyl": bd_3000,
            "bd_1000_pyroxene": bd_1000,
            "bd_2000_pyroxene": bd_2000,
            "spectral_slope": slope,
            "resource_index": resource_index,
        }

    # -------------------------------------------------------------------------
    # Site Resource Evaluation
    # -------------------------------------------------------------------------
    def evaluate_site_resources(
        self,
        site_id: str,
        center_row: int,
        center_col: int,
        radius_pixels: int = 5,
        resource_maps: Optional[Dict[str, np.ndarray]] = None,
    ) -> ResourceProfile:
        """Evaluates localized spectral resource indicators for a candidate site."""
        if resource_maps is None:
            resource_maps = self.compute_resource_maps()

        bd3k = resource_maps["bd_3000_hydroxyl"]
        bd1k = resource_maps["bd_1000_pyroxene"]
        slope = resource_maps["spectral_slope"]
        res_idx = resource_maps["resource_index"]

        r0 = max(0, center_row - radius_pixels)
        r1 = min(self.height, center_row + radius_pixels + 1)
        c0 = max(0, center_col - radius_pixels)
        c1 = min(self.width, center_col + radius_pixels + 1)

        mean_bd3k = float(np.mean(bd3k[r0:r1, c0:c1]))
        mean_bd1k = float(np.mean(bd1k[r0:r1, c0:c1]))
        mean_slope = float(np.mean(slope[r0:r1, c0:c1]))
        mean_res_idx = float(np.mean(res_idx[r0:r1, c0:c1]))

        # Confidence is higher when absorption depth exceeds sensor noise threshold (~1.5%)
        confidence = float(np.clip((mean_bd3k - 0.015) / 0.05, 0.0, 1.0))

        # Overall resource score (0 - 100)
        resource_score = float(np.clip(mean_res_idx * 100.0, 0.0, 100.0))

        if mean_bd3k >= 0.04:
            summary = "Significant 2.85µm absorption anomaly detected; elevated volatile/hydroxyl signature."
        elif mean_bd3k >= 0.02:
            summary = "Moderate 2.85µm absorption; consistent with typical polar highland regolith hydration."
        else:
            summary = "Weak volatile absorption; predominantly dry, weathered anorthositic highland regolith."

        return ResourceProfile(
            site_id=site_id,
            hydroxyl_band_depth_pct=mean_bd3k * 100.0,
            hydroxyl_confidence=confidence,
            mafic_pyroxene_index=mean_bd1k,
            regolith_maturity_index=mean_slope,
            resource_indicator_score=resource_score,
            scientific_summary=summary,
        )


# -----------------------------------------------------------------------------
# Realistic Synthetic IIRS Hyperspectral Cube Generator
# -----------------------------------------------------------------------------
def generate_synthetic_iirs_cube(
    height: int = 64,
    width: int = 64,
    num_bands: int = 64,
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray]:
    """Generates a calibrated synthetic Chandrayaan-2 IIRS reflectance cube:

    - Wavelengths spanning 0.8 µm to 3.5 µm
    - Continuum baseline with positive NIR reddening
    - Localized 2.85 µm absorption anomaly in shielded cold-trap margins
    - 1.05 µm pyroxene mineral absorption
    - Realistic sensor detector Gaussian noise
    """
    rng = np.random.default_rng(seed)
    wavelengths = np.linspace(0.8, 3.5, num_bands)

    cube = np.zeros((height, width, num_bands), dtype=np.float64)

    # Base reflectance continuum (anorthositic highland: ~0.15 at 0.8um to ~0.25 at 3.0um)
    base_continuum = 0.15 + 0.04 * (wavelengths - 0.8)

    for b in range(num_bands):
        cube[:, :, b] = base_continuum[b]

    # Spatial anomaly zone: cold trap / shielded margin near (row 20, col 45)
    y, x = np.ogrid[:height, :width]
    dist_anomaly = np.sqrt((x - 45) ** 2 + (y - 20) ** 2)
    anomaly_intensity = np.exp(-(dist_anomaly**2) / (2 * 8.0**2))

    # Apply 2.85 um absorption feature
    idx_285 = int(np.argmin(np.abs(wavelengths - 2.85)))
    for b in range(num_bands):
        wl = wavelengths[b]
        # Gaussian absorption curve centered at 2.85 um with FWHM ~ 0.2 um
        abs_shape = np.exp(-((wl - 2.85) ** 2) / (2 * 0.08**2))
        # 8% max absorption in anomaly core, 2% ambient background
        depth = (0.02 + 0.06 * anomaly_intensity) * abs_shape
        cube[:, :, b] *= (1.0 - depth)

    # Apply 1.05 um pyroxene absorption
    for b in range(num_bands):
        wl = wavelengths[b]
        pyroxene_shape = np.exp(-((wl - 1.05) ** 2) / (2 * 0.15**2))
        cube[:, :, b] *= (1.0 - 0.04 * pyroxene_shape)

    # Add realistic detector noise (SNR ~ 200:1)
    noise = rng.normal(0.0, 0.001, size=(height, width, num_bands))
    cube = np.clip(cube + noise, 0.01, 1.0)

    return cube, wavelengths
