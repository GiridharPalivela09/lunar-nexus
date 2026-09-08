"""NEXUS-LUNAR POC-4: Scale Robustness & Multi-Scale Pyramid Engine.

Provides GSD-aware ratio calculations, resolution-harmonizing resampling,
multi-scale image pyramid generation, and scale-aware representations across sensors.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Union, Optional, Tuple
import numpy as np
from PIL import Image

from .illumination_robustness import (
    generate_raw_image,
    generate_normalized_image,
    generate_gradient_image,
    generate_illumination_normalized_image,
)


@dataclass
class PyramidLevel:
    """Represents a single level of an image pyramid."""
    scale_factor: float
    width: int
    height: int
    effective_gsd: float
    array: np.ndarray
    representation_type: str = "RAW"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scale_factor": float(self.scale_factor),
            "width": int(self.width),
            "height": int(self.height),
            "effective_gsd": float(self.effective_gsd),
            "representation_type": str(self.representation_type),
        }


def calculate_gsd_ratio(source_gsd: float, reference_gsd: float) -> float:
    """Calculates the exact physical Ground Sampling Distance (GSD) ratio.
    
    Example:
        source_gsd = 0.25 m/pixel (Chandrayaan-2 OHRC)
        reference_gsd = 1.00 m/pixel (NASA LROC NAC)
        ratio = 1.00 / 0.25 = 4.0
    
    IMPORTANT: GSD ratio describes spatial resolution disparity between sensors.
    It must NOT be treated as or equated to image registration success.
    """
    if source_gsd <= 0.0 or reference_gsd <= 0.0:
        raise ValueError(f"GSD values must be strictly positive (got source={source_gsd}, ref={reference_gsd})")
    return float(reference_gsd / source_gsd)


def resample_to_gsd(
    image: Union[np.ndarray, Image.Image],
    current_gsd: float,
    target_gsd: float,
) -> np.ndarray:
    """Resamples an image to harmonize spatial resolution to a target GSD in meters/pixel.
    
    Uses high-quality Lanczos downsampling when lowering resolution (current < target)
    and Bicubic interpolation when upsampling (current > target).
    """
    if current_gsd <= 0.0 or target_gsd <= 0.0:
        raise ValueError(f"GSD values must be positive: current={current_gsd}, target={target_gsd}")

    raw_arr = generate_raw_image(image)
    if abs(current_gsd - target_gsd) < 1e-4:
        return raw_arr

    pil_img = Image.fromarray(raw_arr)
    scale = current_gsd / target_gsd
    target_w = max(1, int(round(pil_img.width * scale)))
    target_h = max(1, int(round(pil_img.height * scale)))

    resample_filter = Image.Resampling.LANCZOS if scale < 1.0 else Image.Resampling.BICUBIC
    resampled_pil = pil_img.resize((target_w, target_h), resample=resample_filter)
    return np.array(resampled_pil, dtype=np.uint8)


def build_image_pyramid(
    image: Union[np.ndarray, Image.Image],
    native_gsd: float,
    scales: List[float] = [1.0, 0.5, 0.25, 0.125],
    representation_type: str = "RAW",
) -> List[PyramidLevel]:
    """Constructs a multi-scale pyramid for a single representation.
    
    Each level maintains:
        - scale_factor
        - width
        - height
        - effective_gsd = native_gsd / scale_factor
        - array
    """
    if native_gsd <= 0.0:
        raise ValueError(f"native_gsd must be positive (got {native_gsd})")

    base_arr = generate_raw_image(image)
    pil_base = Image.fromarray(base_arr)
    w_base, h_base = pil_base.size

    levels: List[PyramidLevel] = []
    # Ensure scales are sorted descending and valid
    valid_scales = sorted([float(s) for s in scales if s > 0.0], reverse=True)
    if not valid_scales:
        valid_scales = [1.0]

    for s in valid_scales:
        new_w = max(1, int(round(w_base * s)))
        new_h = max(1, int(round(h_base * s)))
        
        if abs(s - 1.0) < 1e-4:
            level_arr = base_arr
        else:
            filter_mode = Image.Resampling.LANCZOS if s < 1.0 else Image.Resampling.BICUBIC
            resized_pil = pil_base.resize((new_w, new_h), resample=filter_mode)
            level_arr = np.array(resized_pil, dtype=np.uint8)

        effective_gsd = native_gsd / s
        levels.append(
            PyramidLevel(
                scale_factor=s,
                width=new_w,
                height=new_h,
                effective_gsd=effective_gsd,
                array=level_arr,
                representation_type=representation_type,
            )
        )

    return levels


def build_multiscale_representation_dict(
    image: Union[np.ndarray, Image.Image],
    native_gsd: float,
    scales: List[float] = [1.0, 0.5, 0.25, 0.125],
) -> Dict[str, List[PyramidLevel]]:
    """Builds multi-scale pyramids for all key POC-4 representations:
        1. RAW PYRAMID
        2. NORMALIZED PYRAMID
        3. GRADIENT PYRAMID
        4. ILLUMINATION-NORMALIZED PYRAMID
    """
    raw_arr = generate_raw_image(image)
    norm_arr = generate_normalized_image(raw_arr)
    grad_mag, _ = generate_gradient_image(raw_arr)
    illum_arr = generate_illumination_normalized_image(raw_arr)

    return {
        "RAW": build_image_pyramid(raw_arr, native_gsd, scales, "RAW"),
        "NORMALIZED": build_image_pyramid(norm_arr, native_gsd, scales, "NORMALIZED"),
        "GRADIENT": build_image_pyramid(grad_mag, native_gsd, scales, "GRADIENT"),
        "ILLUMINATION_NORMALIZED": build_image_pyramid(illum_arr, native_gsd, scales, "ILLUMINATION_NORMALIZED"),
    }


def apply_synthetic_scale_perturbation(
    image: Union[np.ndarray, Image.Image],
    scale_factor: float,
) -> np.ndarray:
    """Rescales an image by a controlled factor to simulate cross-resolution observations."""
    if scale_factor <= 0.0:
        raise ValueError(f"scale_factor must be positive (got {scale_factor})")
    
    raw_arr = generate_raw_image(image)
    if abs(scale_factor - 1.0) < 1e-4:
        return raw_arr

    pil_img = Image.fromarray(raw_arr)
    new_w = max(1, int(round(pil_img.width * scale_factor)))
    new_h = max(1, int(round(pil_img.height * scale_factor)))
    filter_mode = Image.Resampling.LANCZOS if scale_factor < 1.0 else Image.Resampling.BICUBIC
    return np.array(pil_img.resize((new_w, new_h), resample=filter_mode), dtype=np.uint8)
