"""NEXUS-LUNAR POC-4: Deterministic Classical Registration & Feature Matching Baseline.

Provides high-performance, pure-NumPy feature detection, rotation-resilient
gradient descriptors, Lowe's ratio test matching, and RANSAC affine geometric verification.
Zero external C++ dependencies (no OpenCV required).
"""

from __future__ import annotations
import math
import time
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
from PIL import Image, ImageFilter

from .illumination_robustness import generate_raw_image, generate_shadow_mask, gaussian_blur_2d


@dataclass
class Keypoint:
    x: float
    y: float
    response: float
    scale: float = 1.0
    angle: float = 0.0

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)


@dataclass
class KeypointMatch:
    src_idx: int
    ref_idx: int
    distance: float
    src_pt: Tuple[float, float]
    ref_pt: Tuple[float, float]
    is_inlier: bool = False


@dataclass
class RegistrationResult:
    success: bool
    affine_matrix: Optional[np.ndarray] = None
    src_keypoints: List[Keypoint] = field(default_factory=list)
    ref_keypoints: List[Keypoint] = field(default_factory=list)
    tentative_matches: List[KeypointMatch] = field(default_factory=list)
    inlier_matches: List[KeypointMatch] = field(default_factory=list)
    inlier_ratio: float = 0.0
    rmse: float = float("inf")
    feature_count_source: int = 0
    feature_count_reference: int = 0
    tentative_match_count: int = 0
    inlier_count: int = 0
    processing_time_ms: float = 0.0
    failure_reason: Optional[str] = None

    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "success": bool(self.success),
            "affine_matrix": self.affine_matrix.tolist() if self.affine_matrix is not None else None,
            "feature_count_source": int(self.feature_count_source),
            "feature_count_reference": int(self.feature_count_reference),
            "tentative_match_count": int(self.tentative_match_count),
            "inlier_count": int(self.inlier_count),
            "inlier_ratio": round(float(self.inlier_ratio), 4),
            "rmse": round(float(self.rmse), 4) if np.isfinite(self.rmse) else 999.0,
            "processing_time_ms": round(float(self.processing_time_ms), 2),
            "failure_reason": self.failure_reason,
        }


def detect_keypoints(
    image: np.ndarray,
    max_features: int = 600,
    quality_level: float = 0.01,
    min_distance: int = 8,
    shadow_weight_map: Optional[np.ndarray] = None,
) -> List[Keypoint]:
    """Detects stable, spatially distributed corner features using Harris corner response.
    
    Incorporates shadow-aware down-weighting so keypoints preferentially form
    on illuminated crater rims and structural terrain instead of noisy shadow floors.
    """
    raw = generate_raw_image(image).astype(np.float32)
    h, w = raw.shape
    if h < 16 or w < 16:
        return []

    # Sobel derivatives
    sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32) / 8.0
    sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float32) / 8.0

    pad = np.pad(raw, 1, mode="reflect")
    ix = (
        pad[:-2, 2:] * sobel_x[0, 2] + pad[:-2, :-2] * sobel_x[0, 0] +
        pad[1:-1, 2:] * sobel_x[1, 2] + pad[1:-1, :-2] * sobel_x[1, 0] +
        pad[2:, 2:] * sobel_x[2, 2] + pad[2:, :-2] * sobel_x[2, 0]
    )
    iy = (
        pad[2:, :-2] * sobel_y[2, 0] + pad[2:, 1:-1] * sobel_y[2, 1] + pad[2:, 2:] * sobel_y[2, 2] +
        pad[:-2, :-2] * sobel_y[0, 0] + pad[:-2, 1:-1] * sobel_y[0, 1] + pad[:-2, 2:] * sobel_y[0, 2]
    )

    # Structure tensor components smoothed with Gaussian blur
    ix2 = ix * ix
    iy2 = iy * iy
    ixiy = ix * iy

    s_ix2 = gaussian_blur_2d(ix2, sigma=1.5)
    s_iy2 = gaussian_blur_2d(iy2, sigma=1.5)
    s_ixiy = gaussian_blur_2d(ixiy, sigma=1.5)


    # Harris response: det(M) - k * trace(M)^2
    det = (s_ix2 * s_iy2) - (s_ixiy ** 2)
    trace = s_ix2 + s_iy2
    k = 0.04
    harris_resp = det - k * (trace ** 2)

    # Apply shadow weight map if provided
    if shadow_weight_map is not None and shadow_weight_map.shape == (h, w):
        harris_resp = harris_resp * shadow_weight_map

    # Discard borders
    border = max(min_distance, 12)
    harris_resp[:border, :] = 0
    harris_resp[-border:, :] = 0
    harris_resp[:, :border] = 0
    harris_resp[:, -border:] = 0

    # Non-maximum suppression over min_distance window
    max_resp = np.max(harris_resp)
    if max_resp <= 0.0:
        return []

    thresh = max_resp * quality_level
    pil_resp = Image.fromarray(np.maximum(0.0, harris_resp))
    local_max = np.array(pil_resp.filter(ImageFilter.MaxFilter(size=min_distance * 2 + 1)), dtype=np.float32)

    # Valid candidate mask
    candidates = (harris_resp == local_max) & (harris_resp >= thresh)
    ys, xs = np.where(candidates)
    if len(xs) == 0:
        return []

    responses = harris_resp[ys, xs]
    # Sort descending by response strength
    order = np.argsort(-responses)
    top_indices = order[:max_features]

    keypoints: List[Keypoint] = []
    for idx in top_indices:
        x_pt = float(xs[idx])
        y_pt = float(ys[idx])
        resp_val = float(responses[idx])
        
        # Calculate local dominant gradient angle
        local_ix = ix[int(y_pt), int(x_pt)]
        local_iy = iy[int(y_pt), int(x_pt)]
        angle = float(math.atan2(local_iy, local_ix))

        keypoints.append(Keypoint(x=x_pt, y=y_pt, response=resp_val, angle=angle))

    return keypoints


def extract_descriptors(
    image: np.ndarray,
    keypoints: List[Keypoint],
    patch_radius: int = 16,
    num_bins: int = 8,
) -> Tuple[List[Keypoint], np.ndarray]:
    """Computes a multi-cell spatial gradient orientation descriptor (SIFT-style).
    
    Extracts a (2*patch_radius) x (2*patch_radius) patch, divided into 4x4 spatial cells,
    accumulating gradient magnitudes into 8 orientation bins = 128-D L2-normalized vector.
    """
    raw = generate_raw_image(image).astype(np.float32)
    h, w = raw.shape
    if not keypoints:
        return [], np.zeros((0, 128), dtype=np.float32)

    # Gradients
    pad = np.pad(raw, 1, mode="reflect")
    gx = (pad[1:-1, 2:] - pad[1:-1, :-2]) * 0.5
    gy = (pad[2:, 1:-1] - pad[:-2, 1:-1]) * 0.5
    mag = np.sqrt(gx ** 2 + gy ** 2)
    ang = (np.arctan2(gy, gx) + 2 * np.pi) % (2 * np.pi)  # [0, 2*pi)

    valid_kps: List[Keypoint] = []
    descriptors_list: List[np.ndarray] = []
    cell_size = (2 * patch_radius) // 4
    bin_width = (2 * np.pi) / num_bins

    for kp in keypoints:
        cx, cy = int(round(kp.x)), int(round(kp.y))
        if cx - patch_radius < 0 or cx + patch_radius > w or cy - patch_radius < 0 or cy + patch_radius > h:
            continue

        desc = np.zeros(4 * 4 * num_bins, dtype=np.float32)
        patch_mag = mag[cy - patch_radius : cy + patch_radius, cx - patch_radius : cx + patch_radius]
        patch_ang = (ang[cy - patch_radius : cy + patch_radius, cx - patch_radius : cx + patch_radius] - kp.angle + 2 * np.pi) % (2 * np.pi)

        # Accumulate into 4x4 spatial cells
        for ci in range(4):
            for cj in range(4):
                cell_mag = patch_mag[ci * cell_size : (ci + 1) * cell_size, cj * cell_size : (cj + 1) * cell_size]
                cell_ang = patch_ang[ci * cell_size : (ci + 1) * cell_size, cj * cell_size : (cj + 1) * cell_size]
                
                bin_idx = np.clip((cell_ang / bin_width).astype(int), 0, num_bins - 1)
                offset = (ci * 4 + cj) * num_bins
                for b in range(num_bins):
                    desc[offset + b] = np.sum(cell_mag[bin_idx == b])

        # L2 normalize, clip at 0.2, and re-normalize (robust to non-linear illumination changes)
        norm = np.linalg.norm(desc)
        if norm > 1e-6:
            desc = desc / norm
            desc = np.clip(desc, 0.0, 0.2)
            desc = desc / max(1e-6, np.linalg.norm(desc))
        else:
            desc = np.zeros_like(desc)

        valid_kps.append(kp)
        descriptors_list.append(desc)

    if not descriptors_list:
        return [], np.zeros((0, 128), dtype=np.float32)

    return valid_kps, np.vstack(descriptors_list).astype(np.float32)


def match_features(
    src_kps: List[Keypoint],
    src_descs: np.ndarray,
    ref_kps: List[Keypoint],
    ref_descs: np.ndarray,
    ratio_thresh: float = 0.75,
    cross_check: bool = True,
) -> List[KeypointMatch]:
    """Matches descriptors between source and reference using Lowe's ratio test and optional cross-checking."""
    if len(src_kps) == 0 or len(ref_kps) == 0 or src_descs.shape[0] == 0 or ref_descs.shape[0] == 0:
        return []

    # Vectorized pairwise Euclidean distance matrix
    # ||u - v||^2 = ||u||^2 + ||v||^2 - 2 * u . v
    u2 = np.sum(src_descs ** 2, axis=1, keepdims=True)
    v2 = np.sum(ref_descs ** 2, axis=1, keepdims=True).T
    dists_sq = np.maximum(0.0, u2 + v2 - 2.0 * np.dot(src_descs, ref_descs.T))
    dists = np.sqrt(dists_sq)

    matches: List[KeypointMatch] = []
    # Forward matching: src -> ref
    for i in range(len(src_kps)):
        sorted_indices = np.argsort(dists[i])
        if len(sorted_indices) < 2:
            continue
        best_j = sorted_indices[0]
        second_j = sorted_indices[1]

        best_dist = dists[i, best_j]
        second_dist = dists[i, second_j]

        # Lowe's ratio test
        if best_dist < ratio_thresh * second_dist:
            if cross_check:
                # Reverse check: is i the best match for best_j?
                rev_best_i = np.argmin(dists[:, best_j])
                if rev_best_i != i:
                    continue

            matches.append(
                KeypointMatch(
                    src_idx=i,
                    ref_idx=best_j,
                    distance=float(best_dist),
                    src_pt=src_kps[i].to_tuple(),
                    ref_pt=ref_kps[best_j].to_tuple(),
                )
            )

    return matches


def estimate_affine_ransac(
    matches: List[KeypointMatch],
    max_reproj_error: float = 4.0,
    max_iterations: int = 2000,
    confidence: float = 0.99,
    min_inliers_thresh: int = 6,
    seed: int = 42,
) -> Tuple[Optional[np.ndarray], List[KeypointMatch], float]:
    """Estimates an affine transformation matrix [A | t] via RANSAC.
    
    Transforms source coordinates to reference coordinates:
        [x_ref, y_ref]^T = A * [x_src, y_src]^T + t
    
    Returns:
        affine_matrix: 2x3 affine matrix or None if estimation fails.
        inlier_matches: List of inlier matches.
        rmse: Reprojection root mean squared error.
    """
    if len(matches) < 3:
        return None, [], float("inf")

    src_pts = np.array([m.src_pt for m in matches], dtype=np.float64)  # (N, 2)
    ref_pts = np.array([m.ref_pt for m in matches], dtype=np.float64)  # (N, 2)
    n = len(matches)

    rng = np.random.default_rng(seed)
    best_inliers_mask: Optional[np.ndarray] = None
    best_inlier_count = 0
    best_affine: Optional[np.ndarray] = None

    for _ in range(max_iterations):
        sample_indices = rng.choice(n, size=3, replace=False)
        p_src = src_pts[sample_indices]
        p_ref = ref_pts[sample_indices]

        # Fit minimal affine model (3 correspondences -> 6 linear equations)
        # [[x0, y0, 1, 0, 0, 0], [0, 0, 0, x0, y0, 1], ...]
        M = np.zeros((6, 6), dtype=np.float64)
        b = np.zeros(6, dtype=np.float64)
        for k in range(3):
            M[2 * k] = [p_src[k, 0], p_src[k, 1], 1.0, 0.0, 0.0, 0.0]
            M[2 * k + 1] = [0.0, 0.0, 0.0, p_src[k, 0], p_src[k, 1], 1.0]
            b[2 * k] = p_ref[k, 0]
            b[2 * k + 1] = p_ref[k, 1]

        try:
            params = np.linalg.solve(M, b)
        except np.linalg.LinAlgError:
            continue

        affine = np.array([[params[0], params[1], params[2]], [params[3], params[4], params[5]]])

        # Project all source points
        proj_pts = (affine[:2, :2] @ src_pts.T).T + affine[:2, 2]
        errors = np.linalg.norm(proj_pts - ref_pts, axis=1)

        inliers_mask = errors <= max_reproj_error
        inlier_count = int(np.count_nonzero(inliers_mask))

        if inlier_count > best_inlier_count:
            best_inlier_count = inlier_count
            best_inliers_mask = inliers_mask
            best_affine = affine

            # Adaptive iteration limit based on inlier fraction
            inlier_ratio = inlier_count / n
            if inlier_ratio > 0.8:
                break

    if best_inliers_mask is None or best_inlier_count < min_inliers_thresh:
        return None, [], float("inf")

    # Re-estimate affine model using ALL inliers via least squares
    inlier_src = src_pts[best_inliers_mask]
    inlier_ref = ref_pts[best_inliers_mask]

    # Build overdetermined system
    num_inl = inlier_src.shape[0]
    A_mat = np.zeros((2 * num_inl, 6), dtype=np.float64)
    b_vec = np.zeros(2 * num_inl, dtype=np.float64)
    for k in range(num_inl):
        A_mat[2 * k] = [inlier_src[k, 0], inlier_src[k, 1], 1.0, 0.0, 0.0, 0.0]
        A_mat[2 * k + 1] = [0.0, 0.0, 0.0, inlier_src[k, 0], inlier_src[k, 1], 1.0]
        b_vec[2 * k] = inlier_ref[k, 0]
        b_vec[2 * k + 1] = inlier_ref[k, 1]

    refined_params, _, _, _ = np.linalg.lstsq(A_mat, b_vec, rcond=None)
    refined_affine = np.array([
        [refined_params[0], refined_params[1], refined_params[2]],
        [refined_params[3], refined_params[4], refined_params[5]],
    ])

    # Final inlier projection error and RMSE
    proj_inliers = (refined_affine[:2, :2] @ inlier_src.T).T + refined_affine[:2, 2]
    inlier_errors = np.linalg.norm(proj_inliers - inlier_ref, axis=1)
    rmse = float(np.sqrt(np.mean(inlier_errors ** 2)))

    inlier_matches: List[KeypointMatch] = []
    for idx, is_inl in enumerate(best_inliers_mask):
        m = matches[idx]
        m.is_inlier = bool(is_inl)
        if is_inl:
            inlier_matches.append(m)

    return refined_affine, inlier_matches, rmse


def run_classical_registration(
    source_image: np.ndarray,
    reference_image: np.ndarray,
    source_shadow_map: Optional[np.ndarray] = None,
    reference_shadow_map: Optional[np.ndarray] = None,
    max_features: int = 500,
    ratio_thresh: float = 0.75,
    max_reproj_error: float = 4.0,
    min_inliers_thresh: int = 6,
    seed: int = 42,
) -> RegistrationResult:
    """Executes the complete classical keypoint detection, matching, and geometric verification pipeline.
    
    Acts as the fixed, constant baseline across all representation experiments.
    """
    start_time = time.perf_counter()

    # 1. Feature Detection
    src_kps = detect_keypoints(
        source_image, max_features=max_features, quality_level=0.005, min_distance=6, shadow_weight_map=source_shadow_map
    )
    ref_kps = detect_keypoints(
        reference_image, max_features=max_features, quality_level=0.005, min_distance=6, shadow_weight_map=reference_shadow_map
    )

    if len(src_kps) < 4 or len(ref_kps) < 4:
        elapsed = (time.perf_counter() - start_time) * 1000.0
        return RegistrationResult(
            success=False,
            feature_count_source=len(src_kps),
            feature_count_reference=len(ref_kps),
            processing_time_ms=elapsed,
            failure_reason="no_features" if (len(src_kps) == 0 or len(ref_kps) == 0) else "insufficient_features",
        )

    # 2. Descriptor Extraction
    src_valid_kps, src_descs = extract_descriptors(source_image, src_kps, patch_radius=12)
    ref_valid_kps, ref_descs = extract_descriptors(reference_image, ref_kps, patch_radius=12)


    if src_descs.shape[0] < 4 or ref_descs.shape[0] < 4:
        elapsed = (time.perf_counter() - start_time) * 1000.0
        return RegistrationResult(
            success=False,
            feature_count_source=len(src_valid_kps),
            feature_count_reference=len(ref_valid_kps),
            processing_time_ms=elapsed,
            failure_reason="no_descriptors",
        )

    # 3. Matching
    tentative_matches = match_features(src_valid_kps, src_descs, ref_valid_kps, ref_descs, ratio_thresh=ratio_thresh)

    if len(tentative_matches) < min_inliers_thresh:
        elapsed = (time.perf_counter() - start_time) * 1000.0
        return RegistrationResult(
            success=False,
            src_keypoints=src_valid_kps,
            ref_keypoints=ref_valid_kps,
            tentative_matches=tentative_matches,
            feature_count_source=len(src_valid_kps),
            feature_count_reference=len(ref_valid_kps),
            tentative_match_count=len(tentative_matches),
            processing_time_ms=elapsed,
            failure_reason="insufficient_matches" if len(tentative_matches) > 0 else "no_matches",
        )

    # 4. RANSAC Affine Verification
    affine_mat, inliers, rmse = estimate_affine_ransac(
        tentative_matches,
        max_reproj_error=max_reproj_error,
        min_inliers_thresh=min_inliers_thresh,
        seed=seed,
    )

    elapsed = (time.perf_counter() - start_time) * 1000.0
    inl_count = len(inliers)
    inl_ratio = (inl_count / len(tentative_matches)) if tentative_matches else 0.0
    is_success = (affine_mat is not None) and (inl_count >= min_inliers_thresh) and (rmse <= 5.0)

    failure_reason = None
    if not is_success:
        if affine_mat is None:
            failure_reason = "ransac_failure"
        elif rmse > 5.0:
            failure_reason = "high_rmse"
        else:
            failure_reason = "alignment_failure"

    return RegistrationResult(
        success=is_success,
        affine_matrix=affine_mat,
        src_keypoints=src_valid_kps,
        ref_keypoints=ref_valid_kps,
        tentative_matches=tentative_matches,
        inlier_matches=inliers,
        inlier_ratio=inl_ratio,
        rmse=rmse,
        feature_count_source=len(src_valid_kps),
        feature_count_reference=len(ref_valid_kps),
        tentative_match_count=len(tentative_matches),
        inlier_count=inl_count,
        processing_time_ms=elapsed,
        failure_reason=failure_reason,
    )
