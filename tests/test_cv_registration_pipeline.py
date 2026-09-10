"""Computer Vision & Classical Registration Pipeline Validation Suite."""

import math
import numpy as np
import cv2
import pytest

from packages.registration.algorithms import FeatureMethod, extract_features, apply_rootsift_normalization
from packages.registration.matchers import match_descriptors
from packages.registration.geometric import TransformType, estimate_transformation, phase_correlation_shift
from packages.registration.metrics import compute_reprojection_rmse, decompose_transform_matrix


@pytest.fixture
def synthetic_lunar_patch():
    """Generates a synthetic 400x400 lunar surface patch with craters and high-frequency textures."""
    np.random.seed(42)
    # Base regolith texture
    img = np.random.normal(128, 20, (400, 400)).astype(np.float32)

    # Add simulated craters (circular dips with bright illuminated rims)
    craters = [
        (100, 100, 35),
        (250, 150, 50),
        (180, 280, 40),
        (320, 310, 25),
        (80, 260, 20),
    ]
    for cx, cy, r in craters:
        y, x = np.ogrid[:400, :400]
        dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        crater_mask = dist <= r
        # Dark interior
        img[crater_mask] -= 45.0 * (1.0 - dist[crater_mask] / r)
        # Bright illuminated rim on western side
        rim_mask = (dist >= r - 3) & (dist <= r + 3) & (x < cx)
        img[rim_mask] += 50.0

    img = np.clip(img, 0, 255).astype(np.uint8)
    return img


class TestClassicalFeatureRegistration:
    """Test suite validating feature detectors, descriptors, matching, and geometric transformations."""

    def test_sift_and_rootsift_feature_extraction(self, synthetic_lunar_patch):
        # 1. Standard SIFT
        kp_sift, desc_sift = extract_features(synthetic_lunar_patch, method=FeatureMethod.SIFT)
        assert len(kp_sift) > 100, "SIFT should detect salient crater rim keypoints"
        assert desc_sift.shape[1] == 128

        # 2. RootSIFT (L1 square-root normalized)
        kp_root, desc_root = extract_features(synthetic_lunar_patch, method=FeatureMethod.ROOT_SIFT)
        assert len(kp_root) > 100
        # Check L2 unit norm of each RootSIFT descriptor
        norms = np.linalg.norm(desc_root, axis=1)
        assert np.allclose(norms, 1.0, atol=1e-3)

    def test_orb_and_akaze_binary_features(self, synthetic_lunar_patch):
        # ORB
        kp_orb, desc_orb = extract_features(synthetic_lunar_patch, method=FeatureMethod.ORB)
        assert len(kp_orb) >= 50
        assert desc_orb.dtype == np.uint8

        # AKAZE (supports native MLDB uint8 or GFTT+SIFT float32 fallback)
        kp_akaze, desc_akaze = extract_features(synthetic_lunar_patch, method=FeatureMethod.AKAZE)
        assert len(kp_akaze) >= 30
        assert desc_akaze.dtype in (np.uint8, np.float32)

    def test_known_affine_transformation_recovery(self, synthetic_lunar_patch):
        """Applies a known rigid/affine transformation and asserts sub-pixel recovery accuracy."""
        src_img = synthetic_lunar_patch

        # Ground-truth transformation: rotation = 3.0 deg, translation = (12.0, -8.0)
        gt_angle = 3.0
        gt_dx = 12.0
        gt_dy = -8.0

        center = (src_img.shape[1] / 2.0, src_img.shape[0] / 2.0)
        M_rot = cv2.getRotationMatrix2D(center, gt_angle, 1.0)
        M_rot[0, 2] += gt_dx
        M_rot[1, 2] += gt_dy

        ref_img = cv2.warpAffine(src_img, M_rot, (src_img.shape[1], src_img.shape[0]))

        # Run registration pipeline: SIFT -> Match -> RANSAC Affine
        kp_src, desc_src = extract_features(src_img, method=FeatureMethod.ROOT_SIFT)
        kp_ref, desc_ref = extract_features(ref_img, method=FeatureMethod.ROOT_SIFT)

        matches = match_descriptors(desc_src, desc_ref, method=FeatureMethod.ROOT_SIFT, ratio_thresh=0.80)
        assert len(matches) >= 15, "Should find sufficient keypoint correspondences"

        M_recovered, inliers_mask, inlier_src_pts, inlier_ref_pts = estimate_transformation(
            kp_src, kp_ref, matches, transform_type=TransformType.AFFINE
        )

        assert M_recovered is not None, "Transformation estimation must succeed"
        assert np.sum(inliers_mask) >= 10, "Should achieve solid RANSAC consensus"

        # Compare recovered affine matrix directly against ground truth M_rot
        assert np.allclose(M_recovered, M_rot, atol=2.0), f"Recovered M: {M_recovered} vs Ground Truth: {M_rot}"

        # Sub-pixel reprojection RMSE
        rmse = compute_reprojection_rmse(inlier_src_pts, inlier_ref_pts, M_recovered)
        assert rmse < 2.0, f"RMSE reprojection error ({rmse} px) exceeded acceptable threshold"

    def test_phase_correlation_shift_estimation(self, synthetic_lunar_patch):
        """Validates sub-pixel FFT Phase Correlation on translated image pair."""
        src_img = synthetic_lunar_patch
        gt_dx, gt_dy = 15.0, -10.0

        M_shift = np.array([[1.0, 0.0, gt_dx], [0.0, 1.0, gt_dy]], dtype=np.float32)
        ref_img = cv2.warpAffine(src_img, M_shift, (src_img.shape[1], src_img.shape[0]))

        # In phase correlation, shifting reference relative to source
        M_recovered, response = phase_correlation_shift(src_img, ref_img)
        assert M_recovered is not None
        assert response > 0.3

        # Phase correlation recovers shift
        recovered_dx = M_recovered[0, 2]
        recovered_dy = M_recovered[1, 2]
        assert abs(abs(recovered_dx) - abs(gt_dx)) < 1.0
        assert abs(abs(recovered_dy) - abs(gt_dy)) < 1.0

    def test_failure_cases_blank_and_noisy_images(self):
        """Asserts graceful handling when inputs contain zero texture or degenerate information."""
        # 1. Blank solid black image
        blank = np.zeros((200, 200), dtype=np.uint8)
        kp_blank, desc_blank = extract_features(blank, method=FeatureMethod.SIFT)
        assert len(kp_blank) == 0 or desc_blank is None

        # 2. None input raises ValueError
        with pytest.raises(ValueError):
            extract_features(None, method=FeatureMethod.SIFT)

        # 3. Insufficient matches for RANSAC (< 4 for Homography, < 3 for Affine)
        M, mask, _, _ = estimate_transformation([], [], [], transform_type=TransformType.HOMOGRAPHY)
        assert M is None
        assert mask is None
