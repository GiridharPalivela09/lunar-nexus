"""NEXUS-LUNAR POC-4: Illumination Robustness Pipeline.

Provides deterministic illumination representations, local contrast normalization,
gradient and edge extractions, high-pass illumination normalization, shadow masking,
and controlled synthetic illumination perturbations for lunar imagery.
"""

from __future__ import annotations
import math
from typing import Tuple, Dict, Any, Optional, Union
import numpy as np
from PIL import Image, ImageFilter


def generate_raw_image(image: Union[np.ndarray, Image.Image]) -> np.ndarray:
    """Validates and returns raw image intensity array as uint8 [0, 255].
    
    Preserves original relative intensity without photometric alteration.
    """
    if isinstance(image, Image.Image):
        arr = np.array(image.convert("L"), dtype=np.float32)
    elif isinstance(image, np.ndarray):
        arr = image.astype(np.float32)
        if arr.ndim == 3:
            arr = np.mean(arr, axis=-1)
    else:
        raise TypeError(f"Unsupported image type: {type(image)}")

    if arr.size == 0:
        raise ValueError("Cannot process empty image array")

    min_val = np.nanmin(arr)
    max_val = np.nanmax(arr)
    if max_val > min_val:
        if max_val <= 1.0 and min_val >= 0.0:
            arr = arr * 255.0
        else:
            arr = np.clip(arr, 0.0, 255.0)
    else:
        arr = np.zeros_like(arr)

    return np.nan_to_num(arr, nan=0.0).astype(np.uint8)


def box_blur_2d(arr: np.ndarray, radius: int) -> np.ndarray:
    """Vectorized O(1) separable 2D box blur using cumulative sum in pure NumPy."""
    r = max(1, int(radius))
    w_len = 2 * r + 1
    # Horizontal pass
    pad_h = np.pad(arr, ((0, 0), (r + 1, r)), mode="reflect")
    cs_h = np.cumsum(pad_h, axis=1)
    out_h = (cs_h[:, w_len:] - cs_h[:, :-w_len]) / float(w_len)
    # Vertical pass
    pad_v = np.pad(out_h, ((r + 1, r), (0, 0)), mode="reflect")
    cs_v = np.cumsum(pad_v, axis=0)
    out = (cs_v[w_len:, :] - cs_v[:-w_len, :]) / float(w_len)
    return out.astype(np.float32)


def gaussian_blur_2d(arr: np.ndarray, sigma: float = 1.5) -> np.ndarray:
    """Fast 3-pass box blur Gaussian approximation in O(1) time per pixel."""
    sig = max(0.5, float(sigma))
    # Box radius that matches Gaussian variance: sigma^2 ~ 3 * (w^2 - 1) / 12 => w = sqrt(4 * sigma^2 + 1)
    w_ideal = math.sqrt(4.0 * sig * sig + 1.0)
    wl = int(math.floor(w_ideal))
    if wl % 2 == 0:
        wl -= 1
    r = max(1, (wl - 1) // 2)

    # 3 successive box blurs yield near-perfect Gaussian bell curve
    b1 = box_blur_2d(arr, r)
    b2 = box_blur_2d(b1, r)
    b3 = box_blur_2d(b2, r)
    return b3



def generate_normalized_image(
    image: Union[np.ndarray, Image.Image],
    tile_grid_size: Tuple[int, int] = (8, 8),
    clip_limit: float = 3.0,
    window_size: int = 15,
    epsilon: float = 1e-5,
) -> np.ndarray:
    """Performs local contrast normalization (adaptive local mean and variance standardization).
    
    This suppresses large-scale regional illumination disparities while accentuating
    local terrain relief (e.g. crater rims and boulder fields) across shadowed and illuminated areas.
    """
    raw = generate_raw_image(image).astype(np.float32)
    h, w = raw.shape

    # Ensure window size is odd and valid
    k = max(3, int(window_size) | 1)
    k = min(k, min(h, w) | 1)
    if k < 3:
        return raw.astype(np.uint8)

    radius = k // 2
    local_mean = box_blur_2d(raw, radius)
    local_sq_mean = box_blur_2d(raw ** 2, radius)

    local_var = np.maximum(0.0, local_sq_mean - (local_mean ** 2))
    local_std = np.sqrt(local_var + epsilon)

    # Standardize and clip extreme outliers to prevent noise blowup in flat shadow basins
    normalized = (raw - local_mean) / local_std
    clipped = np.clip(normalized, -clip_limit, clip_limit)

    # Rescale back to uint8 [0, 255]
    rescaled = ((clipped + clip_limit) / (2.0 * clip_limit)) * 255.0
    return np.clip(rescaled, 0, 255).astype(np.uint8)


def generate_gradient_image(
    image: Union[np.ndarray, Image.Image],
) -> Tuple[np.ndarray, np.ndarray]:
    """Calculates spatial gradient representations using 3x3 Sobel operators.
    
    Returns:
        gradient_magnitude: Normalized gradient magnitude as uint8 [0, 255].
        gradient_orientation: Gradient orientation in radians [-pi, pi] as float32.
    """
    raw = generate_raw_image(image).astype(np.float32)
    h, w = raw.shape

    if h < 3 or w < 3:
        return np.zeros((h, w), dtype=np.uint8), np.zeros((h, w), dtype=np.float32)

    # Sobel kernels
    sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32) / 8.0
    sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float32) / 8.0

    # Padded convolution using pure numpy
    pad = np.pad(raw, 1, mode="reflect")
    gx = (
        pad[:-2, 2:] * sobel_x[0, 2] + pad[:-2, :-2] * sobel_x[0, 0] +
        pad[1:-1, 2:] * sobel_x[1, 2] + pad[1:-1, :-2] * sobel_x[1, 0] +
        pad[2:, 2:] * sobel_x[2, 2] + pad[2:, :-2] * sobel_x[2, 0]
    )
    gy = (
        pad[2:, :-2] * sobel_y[2, 0] + pad[2:, 1:-1] * sobel_y[2, 1] + pad[2:, 2:] * sobel_y[2, 2] +
        pad[:-2, :-2] * sobel_y[0, 0] + pad[:-2, 1:-1] * sobel_y[0, 1] + pad[:-2, 2:] * sobel_y[0, 2]
    )

    magnitude = np.sqrt(gx ** 2 + gy ** 2)
    orientation = np.arctan2(gy, gx)

    # Normalize magnitude to uint8
    max_mag = np.percentile(magnitude, 99.5) if magnitude.size > 0 else 1.0
    if max_mag > 1e-4:
        norm_mag = np.clip((magnitude / max_mag) * 255.0, 0.0, 255.0)
    else:
        norm_mag = np.zeros_like(magnitude)

    return norm_mag.astype(np.uint8), orientation.astype(np.float32)


def generate_edge_image(
    image: Union[np.ndarray, Image.Image],
    low_thresh: float = 25.0,
    high_thresh: float = 80.0,
) -> np.ndarray:
    """Generates a stable structural edge representation using gradient magnitude thresholding.
    
    Produces a crisp terrain skeleton highlighting topographic rim crests.
    """
    grad_mag, _ = generate_gradient_image(image)
    mag_f = grad_mag.astype(np.float32)

    # Deterministic hysteresis-style edge classification
    strong_edges = mag_f >= high_thresh
    weak_edges = (mag_f >= low_thresh) & (mag_f < high_thresh)

    # Edge dilation for connectivity
    pil_strong = Image.fromarray(strong_edges.astype(np.uint8) * 255)
    dilated_strong = np.array(pil_strong.filter(ImageFilter.MaxFilter(3))) > 0
    connected_edges = strong_edges | (weak_edges & dilated_strong)

    return (connected_edges.astype(np.uint8) * 255)


def generate_illumination_normalized_image(
    image: Union[np.ndarray, Image.Image],
    sigma: float = 15.0,
    epsilon: float = 1e-3,
) -> np.ndarray:
    """Generates an illumination-normalized representation by high-pass spatial filtering.
    
    Decomposes the intensity I into slow-varying low-frequency illumination L
    and high-frequency reflectance/topographic structure R:
        L = GaussianBlur(I, sigma)
        R = I / (L + epsilon)
    
    R is rescaled to a stable [0, 255] uint8 representation.
    Note: This is an illumination-normalized representation, not physically exact photometry.
    """
    raw = generate_raw_image(image).astype(np.float32)

    # Apply Gaussian blur to estimate macro illumination field
    low_freq = gaussian_blur_2d(raw, sigma=max(1.0, float(sigma)))

    # Compute high-frequency ratio R = I / (L + eps)
    r = raw / (low_freq + epsilon)

    # Robust scaling around median ratio ~1.0
    p2, p98 = np.percentile(r, (2, 98))
    if p98 > p2:
        norm_r = np.clip((r - p2) / (p98 - p2), 0.0, 1.0) * 255.0
    else:
        norm_r = np.full_like(r, 128.0)

    return norm_r.astype(np.uint8)


def generate_shadow_mask(
    image: Union[np.ndarray, Image.Image],
    low_percentile: float = 5.0,
    absolute_thresh: float = 25.0,
) -> Tuple[np.ndarray, float, np.ndarray]:
    """Detects deep shadowed lunar regions and computes shadow statistics.
    
    Returns:
        shadow_mask: Binary boolean mask where True indicates shadow.
        shadow_fraction: Float in [0.0, 1.0] representing percentage of shadowed area.
        shadow_aware_weight_map: Float32 weight array in [0.05, 1.0] for feature weighting.
    """
    raw = generate_raw_image(image)
    if raw.size == 0:
        return np.zeros((0, 0), dtype=bool), 0.0, np.zeros((0, 0), dtype=np.float32)

    # Determine adaptive shadow threshold based on percentile and absolute cutoff
    p_val = np.percentile(raw, low_percentile)
    effective_thresh = min(float(p_val), float(absolute_thresh))
    # Guarantee a reasonable minimum boundary
    effective_thresh = max(effective_thresh, 10.0)

    shadow_mask = raw <= effective_thresh
    shadow_fraction = float(np.count_nonzero(shadow_mask) / raw.size)

    # Weight map: smooth transition from 0.05 inside deep shadows up to 1.0 in lit terrain
    weight_map = np.ones_like(raw, dtype=np.float32)
    weight_map[shadow_mask] = 0.05

    # Smooth weight map to avoid sharp step discontinuities
    smooth_weight = box_blur_2d(weight_map, radius=2)
    weight_map = np.clip(smooth_weight, 0.05, 1.0)

    return shadow_mask, shadow_fraction, weight_map



def apply_synthetic_illumination_perturbation(
    image: Union[np.ndarray, Image.Image],
    condition: str,
    seed: int = 42,
) -> np.ndarray:
    """Applies a controlled, deterministic synthetic illumination perturbation.
    
    Valid conditions:
        - NORMAL: Identity baseline
        - DARKENED: Depressed solar lighting (x0.35)
        - BRIGHTENED: Saturated highland glare (x1.65)
        - LOW_CONTRAST: Severely narrowed dynamic range
        - HIGH_CONTRAST: Expanded dynamic range with heavy clipping
        - GAMMA_SHIFT: Non-linear photometric sensor distortion (gamma = 0.45 or 2.2)
        - ILLUMINATION_GRADIENT: Slanted solar incident angle gradient ramp across image
        - SHADOW_PERTURBATION: Amplified deep polar crater shadows
    """
    raw = generate_raw_image(image).astype(np.float32)
    h, w = raw.shape
    rng = np.random.default_rng(seed)
    cond_upper = condition.strip().upper()

    if cond_upper == "NORMAL":
        return raw.astype(np.uint8)

    elif cond_upper == "DARKENED":
        # Simulates low albedo / steep phase angle
        perturbed = raw * 0.35
        return np.clip(perturbed, 0, 255).astype(np.uint8)

    elif cond_upper == "BRIGHTENED":
        # Simulates high solar altitude / specular highland bloom
        perturbed = raw * 1.65
        return np.clip(perturbed, 0, 255).astype(np.uint8)

    elif cond_upper == "LOW_CONTRAST":
        # Compress dynamic range towards image mean
        mean_val = np.mean(raw)
        perturbed = (raw - mean_val) * 0.25 + mean_val
        return np.clip(perturbed, 0, 255).astype(np.uint8)

    elif cond_upper == "HIGH_CONTRAST":
        # Stretch dynamic range with aggressive threshold clipping
        p15, p85 = np.percentile(raw, (15, 85))
        if p85 > p15:
            perturbed = ((raw - p15) / (p85 - p15)) * 255.0
        else:
            perturbed = raw
        return np.clip(perturbed, 0, 255).astype(np.uint8)

    elif cond_upper == "GAMMA_SHIFT":
        # Photometric power-law non-linearity
        gamma = 2.2 if (seed % 2 == 0) else 0.45
        norm = raw / 255.0
        perturbed = (norm ** gamma) * 255.0
        return np.clip(perturbed, 0, 255).astype(np.uint8)

    elif cond_upper == "ILLUMINATION_GRADIENT":
        # Directional ramp simulating grazing solar incidence across lunar terrain
        y, x = np.mgrid[:h, :w]
        ramp = 0.2 + 0.8 * ((x / max(1, w - 1)) * 0.7 + (y / max(1, h - 1)) * 0.3)
        perturbed = raw * ramp
        return np.clip(perturbed, 0, 255).astype(np.uint8)

    elif cond_upper == "SHADOW_PERTURBATION":
        # Intensifies existing low-radiance zones into pitch-black lunar shadows
        shadow_mask, _, _ = generate_shadow_mask(raw, low_percentile=15.0, absolute_thresh=45.0)
        perturbed = raw.copy()
        perturbed[shadow_mask] = perturbed[shadow_mask] * 0.1
        # Add a localized synthetic crater shadow patch
        cx, cy = w // 2, h // 2
        r = min(w, h) // 4
        y, x = np.mgrid[:h, :w]
        crater_mask = ((x - cx) ** 2 + (y - cy) ** 2) <= (r ** 2)
        perturbed[crater_mask] = perturbed[crater_mask] * 0.15
        return np.clip(perturbed, 0, 255).astype(np.uint8)

    else:
        raise ValueError(f"Unknown illumination perturbation condition: {condition}")
