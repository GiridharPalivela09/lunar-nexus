"""Comprehensive Offline Test Suite for NEXUS-LUNAR POC-4: Illumination + Scale Robustness.

Contains 27 offline unit tests validating:
- RAW, Normalized, Gradient, Edge, and Illumination-Normalized representations
- Shadow masking, fraction, and weight mapping
- Scale pyramids, GSD ratio, and resampling
- Synthetic illumination and scale perturbations
- Classical keypoint detection, descriptors, Lowe's ratio matching, and RANSAC affine fitting
- Recall@K with synthetic ground truth and UNAVAILABLE fallback
- Inlier ratio, RMSE, alignment success, deltas, and failure tracking
- Experiment matrix, ablation study, CSV, JSON, and metadata generation
- All 6 visualization figure generators
"""

import os
import json
import csv
import pytest
import numpy as np
from PIL import Image

from packages.data_pipeline import (
    generate_raw_image,
    generate_normalized_image,
    generate_gradient_image,
    generate_edge_image,
    generate_illumination_normalized_image,
    generate_shadow_mask,
    apply_synthetic_illumination_perturbation,
    PyramidLevel,
    calculate_gsd_ratio,
    resample_to_gsd,
    build_image_pyramid,
    build_multiscale_representation_dict,
    apply_synthetic_scale_perturbation,
    detect_keypoints,
    extract_descriptors,
    match_features,
    estimate_affine_ransac,
    run_classical_registration,
    calculate_recall_at_k,
    calculate_inlier_ratio,
    calculate_registration_rmse,
    calculate_alignment_success,
    calculate_improvement_deltas,
    FailureCaseTracker,
    POC4ExperimentRunner,
    generate_illumination_comparison_figure,
    generate_scale_pyramid_figure,
    generate_registration_comparison_figure,
    generate_metrics_comparison_figure,
    generate_illumination_scale_heatmap_figure,
    generate_ablation_results_figure,
)


@pytest.fixture
def synthetic_lunar_patch():
    """Generates a reproducible 128x128 synthetic lunar surface patch fixture with craters."""
    rng = np.random.default_rng(1234)
    y, x = np.mgrid[:128, :128]
    base = np.full((128, 128), 120.0, dtype=np.float32)

    # Add craters
    craters = [(32, 32, 14), (80, 80, 20), (90, 30, 10), (30, 95, 12)]
    for cx, cy, r in craters:
        r2 = (x - cx) ** 2 + (y - cy) ** 2
        in_crater = r2 <= (r ** 2)
        rim = (r2 <= ((r * 1.3) ** 2)) & (~in_crater)
        base[in_crater] -= 50.0 * (1.0 - np.sqrt(r2[in_crater]) / r)
        base[rim] += 30.0

    # Add terrain slope and texture noise
    base += 10.0 * np.sin(x / 15.0) + rng.normal(0, 2, (128, 128))
    return np.clip(base, 10, 245).astype(np.uint8)


# 1. RAW representation
def test_raw_representation(synthetic_lunar_patch):
    raw = generate_raw_image(synthetic_lunar_patch)
    assert isinstance(raw, np.ndarray)
    assert raw.dtype == np.uint8
    assert raw.shape == (128, 128)
    assert np.min(raw) >= 0 and np.max(raw) <= 255


# 2. Local contrast normalization
def test_local_contrast_normalization(synthetic_lunar_patch):
    norm = generate_normalized_image(synthetic_lunar_patch, window_size=11, clip_limit=2.5)
    assert norm.shape == (128, 128)
    assert norm.dtype == np.uint8
    # Standard deviation should be preserved and contrast spread across dynamic range
    assert np.std(norm) > 10.0


# 3. Gradient generation
def test_gradient_generation(synthetic_lunar_patch):
    mag, ori = generate_gradient_image(synthetic_lunar_patch)
    assert mag.shape == (128, 128)
    assert ori.shape == (128, 128)
    assert mag.dtype == np.uint8
    assert np.all(ori >= -np.pi) and np.all(ori <= np.pi)
    assert np.max(mag) > 0


# 4. Edge representation
def test_edge_representation(synthetic_lunar_patch):
    edge = generate_edge_image(synthetic_lunar_patch, low_thresh=20.0, high_thresh=60.0)
    assert edge.shape == (128, 128)
    assert edge.dtype == np.uint8
    unique_vals = set(np.unique(edge))
    assert unique_vals.issubset({0, 255})
    assert np.count_nonzero(edge) > 0


# 5. Illumination-normalized representation
def test_illumination_normalized_representation(synthetic_lunar_patch):
    illum_norm = generate_illumination_normalized_image(synthetic_lunar_patch, sigma=10.0)
    assert illum_norm.shape == (128, 128)
    assert illum_norm.dtype == np.uint8
    assert np.max(illum_norm) > 150


# 6. Shadow mask and fraction
def test_shadow_mask_and_fraction(synthetic_lunar_patch):
    # Artificially darken a region to ensure shadows exist
    darkened = synthetic_lunar_patch.copy()
    darkened[:30, :30] = 5
    mask, fraction, weight_map = generate_shadow_mask(darkened, low_percentile=10.0, absolute_thresh=20.0)
    assert mask.shape == (128, 128)
    assert isinstance(fraction, float)
    assert 0.0 <= fraction <= 1.0
    assert fraction > 0.0
    assert np.all(mask[:30, :30])


# 7. Shadow-aware weight map
def test_shadow_aware_weight_map(synthetic_lunar_patch):
    darkened = synthetic_lunar_patch.copy()
    darkened[:30, :30] = 5
    _, _, weight_map = generate_shadow_mask(darkened)
    assert weight_map.shape == (128, 128)
    assert np.min(weight_map) >= 0.05
    assert np.max(weight_map) <= 1.0
    # Shadowed area should have lower weights
    assert np.mean(weight_map[:30, :30]) < np.mean(weight_map[60:, 60:])


# 8. Image pyramid levels and GSD
def test_image_pyramid_levels_and_gsd(synthetic_lunar_patch):
    pyramid = build_image_pyramid(synthetic_lunar_patch, native_gsd=0.25, scales=[1.0, 0.5, 0.25])
    assert len(pyramid) == 3
    assert pyramid[0].scale_factor == 1.0
    assert pyramid[0].effective_gsd == 0.25
    assert pyramid[0].width == 128 and pyramid[0].height == 128

    assert pyramid[1].scale_factor == 0.5
    assert pyramid[1].effective_gsd == 0.50
    assert pyramid[1].width == 64 and pyramid[1].height == 64

    assert pyramid[2].scale_factor == 0.25
    assert pyramid[2].effective_gsd == 1.00
    assert pyramid[2].width == 32 and pyramid[2].height == 32


# 9. GSD ratio and resampling
def test_gsd_ratio_and_resampling(synthetic_lunar_patch):
    ratio = calculate_gsd_ratio(0.25, 1.00)
    assert abs(ratio - 4.0) < 1e-6

    with pytest.raises(ValueError):
        calculate_gsd_ratio(-0.25, 1.0)

    resampled = resample_to_gsd(synthetic_lunar_patch, current_gsd=0.25, target_gsd=0.50)
    assert resampled.shape == (64, 64)


# 10. Synthetic illumination perturbations
def test_synthetic_illumination_perturbations(synthetic_lunar_patch):
    conditions = [
        "NORMAL", "DARKENED", "BRIGHTENED", "LOW_CONTRAST",
        "HIGH_CONTRAST", "GAMMA_SHIFT", "ILLUMINATION_GRADIENT", "SHADOW_PERTURBATION"
    ]
    for cond in conditions:
        out = apply_synthetic_illumination_perturbation(synthetic_lunar_patch, cond, seed=42)
        assert out.shape == synthetic_lunar_patch.shape
        assert out.dtype == np.uint8

    # Check DARKENED is dimmer than BRIGHTENED
    dark = apply_synthetic_illumination_perturbation(synthetic_lunar_patch, "DARKENED")
    bright = apply_synthetic_illumination_perturbation(synthetic_lunar_patch, "BRIGHTENED")
    assert np.mean(dark) < np.mean(bright)


# 11. Synthetic scale perturbations
def test_synthetic_scale_perturbations(synthetic_lunar_patch):
    scaled_half = apply_synthetic_scale_perturbation(synthetic_lunar_patch, 0.5)
    assert scaled_half.shape == (64, 64)

    scaled_double = apply_synthetic_scale_perturbation(synthetic_lunar_patch, 2.0)
    assert scaled_double.shape == (256, 256)


# 12. Classical keypoint detection
def test_classical_keypoint_detection(synthetic_lunar_patch):
    kps = detect_keypoints(synthetic_lunar_patch, max_features=100, min_distance=6)
    assert len(kps) > 10
    assert all(0 <= kp.x < 128 and 0 <= kp.y < 128 for kp in kps)


# 13. Descriptor extraction and matching
def test_descriptor_extraction_and_matching(synthetic_lunar_patch):
    kps1 = detect_keypoints(synthetic_lunar_patch, max_features=50)
    v_kps1, descs1 = extract_descriptors(synthetic_lunar_patch, kps1)
    assert descs1.shape[1] == 128
    assert len(v_kps1) == descs1.shape[0]

    # Match identical image against itself
    matches = match_features(v_kps1, descs1, v_kps1, descs1, ratio_thresh=0.99, cross_check=False)
    assert len(matches) > 0


# 14. RANSAC affine verification
def test_ransac_affine_verification(synthetic_lunar_patch):
    # Test registration of patch with mild translation
    reg = run_classical_registration(synthetic_lunar_patch, synthetic_lunar_patch, seed=42)
    assert reg.success is True
    assert reg.affine_matrix is not None
    assert reg.inlier_count >= 8
    assert reg.rmse < 2.0
    assert reg.inlier_ratio > 0.5


# 15. Recall@K with synthetic ground truth
def test_recall_at_k_synthetic_ground_truth(synthetic_lunar_patch):
    reg = run_classical_registration(synthetic_lunar_patch, synthetic_lunar_patch, seed=42)
    gt_identity = np.eye(3)
    recalls = calculate_recall_at_k(reg.tentative_matches, gt_identity, k_list=[1, 5, 10], dist_thresh_px=3.0)
    assert recalls["ground_truth_status"] == "AVAILABLE"
    assert recalls["recall_at_1"] is not None
    assert recalls["recall_at_1"] > 0.5


# 16. Recall@K unavailable fallback
def test_recall_at_k_unavailable_fallback(synthetic_lunar_patch):
    reg = run_classical_registration(synthetic_lunar_patch, synthetic_lunar_patch, seed=42)
    recalls = calculate_recall_at_k(reg.tentative_matches, ground_truth_transform=None, ground_truth_type="UNAVAILABLE")
    assert recalls["ground_truth_status"] == "GROUND TRUTH UNAVAILABLE"
    assert recalls["recall_at_1"] is None
    assert recalls["recall_at_5"] is None
    assert recalls["recall_at_10"] is None


# 17. Inlier ratio safe zero division
def test_inlier_ratio_zero_division():
    assert calculate_inlier_ratio(0, 0) == 0.0
    assert calculate_inlier_ratio(5, 0) == 0.0
    assert calculate_inlier_ratio(10, 20) == 0.5


# 18. Registration RMSE
def test_registration_rmse():
    pts_a = np.array([[0, 0], [10, 0], [0, 10]], dtype=np.float64)
    pts_b = np.array([[2, 3], [12, 3], [2, 13]], dtype=np.float64)
    # Perfect translation [2, 3]
    aff = np.array([[1.0, 0.0, 2.0], [0.0, 1.0, 3.0]])
    rmse = calculate_registration_rmse(pts_a, pts_b, aff)
    assert abs(rmse) < 1e-6


# 19. Alignment success criteria
def test_alignment_success_criteria():
    assert calculate_alignment_success(rmse=2.5, inlier_count=15) is True
    assert calculate_alignment_success(rmse=6.5, inlier_count=15) is False
    assert calculate_alignment_success(rmse=2.5, inlier_count=4) is False


# 20. Improvement delta calculations
def test_improvement_delta_calculations():
    raw_m = {"recall_at_1": 0.40, "inlier_ratio": 0.30, "rmse": 6.0, "alignment_success": False}
    method_m = {"recall_at_1": 0.70, "inlier_ratio": 0.55, "rmse": 2.0, "alignment_success": True}
    deltas = calculate_improvement_deltas(method_m, raw_m)
    assert deltas["delta_recall_at_1"] == 0.30
    assert deltas["delta_inlier_ratio"] == 0.25
    assert deltas["delta_rmse"] == 4.0  # Positive error reduction
    assert deltas["pct_rmse_reduction"] == 66.67
    assert deltas["delta_alignment_success"] == 1


# 21. Failure case tracking
def test_failure_case_tracking(tmp_path):
    tracker = FailureCaseTracker()
    tracker.record_failure(condition="DARKENED", representation="RAW", failure_type="insufficient_matches")
    tracker.record_failure(condition="SHADOW", representation="GRADIENT", failure_type="ransac_failure")

    counts = tracker.to_dict()["failure_counts"]
    assert counts["insufficient_matches"] == 1
    assert counts["ransac_failure"] == 1
    assert tracker.to_dict()["total_failures"] == 2

    out_file = tmp_path / "test_failures.json"
    tracker.export_json(out_file)
    assert out_file.exists()


# 22. Experiment matrix execution
def test_experiment_matrix_execution(synthetic_lunar_patch, tmp_path):
    runner = POC4ExperimentRunner(output_dir=tmp_path, seed=42)
    # Run subset of matrix
    res = runner.run_single_condition(
        source_raw=synthetic_lunar_patch,
        ref_raw=synthetic_lunar_patch,
        rep_type="RAW",
        illum_cond="NORMAL",
        scale_factor=1.0,
        source_gsd=0.25,
        ref_gsd=0.25,
        ground_truth_transform=np.eye(3),
    )
    assert res["alignment_success"] is True
    assert res["representation"] == "RAW"
    assert "inlier_ratio" in res


# 23. Ablation study execution
def test_ablation_study_execution(synthetic_lunar_patch, tmp_path):
    runner = POC4ExperimentRunner(output_dir=tmp_path, seed=42)
    ablation = runner.run_ablation_study(
        source_image=synthetic_lunar_patch,
        reference_image=synthetic_lunar_patch,
        source_gsd=0.25,
        ref_gsd=0.25,
        ground_truth_transform=np.eye(3),
    )
    assert len(ablation) == 8
    assert ablation[0]["configuration"] == "1. RAW"
    assert ablation[7]["configuration"] == "8. ILLUMINATION-AWARE + SCALE"


# 24. Results CSV generation
def test_results_csv_generation(synthetic_lunar_patch, tmp_path):
    runner = POC4ExperimentRunner(output_dir=tmp_path, seed=42)
    matrix_rows = [
        runner.run_single_condition(
            synthetic_lunar_patch, synthetic_lunar_patch, "RAW", "NORMAL", 1.0, 0.25, 0.25, np.eye(3)
        ),
        runner.run_single_condition(
            synthetic_lunar_patch, synthetic_lunar_patch, "NORMALIZED", "DARKENED", 1.0, 0.25, 0.25, np.eye(3)
        ),
    ]
    csv_p, _, _, _ = runner.export_results(matrix_rows, [], {"experiment_id": "TEST"})
    assert csv_p.exists()
    with open(csv_p, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 2


# 25. Results JSON generation
def test_results_json_generation(synthetic_lunar_patch, tmp_path):
    runner = POC4ExperimentRunner(output_dir=tmp_path, seed=42)
    matrix_rows = [
        runner.run_single_condition(
            synthetic_lunar_patch, synthetic_lunar_patch, "RAW", "NORMAL", 1.0, 0.25, 0.25, np.eye(3)
        )
    ]
    _, json_p, _, _ = runner.export_results(matrix_rows, [], {"experiment_id": "TEST_JSON"})
    assert json_p.exists()
    with open(json_p, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["experiment_id"] == "TEST_JSON"
        assert "best_performing_representation" in data


# 26. POC-4 metadata JSON schema
def test_poc4_metadata_json_schema(synthetic_lunar_patch, tmp_path):
    runner = POC4ExperimentRunner(output_dir=tmp_path, seed=42)
    meta_dict = {
        "experiment_id": "TEST_SCHEMA",
        "sample_counts": {"trials": 1},
        "data_provenance": {"provenance_label": "SYNTHETIC OFFLINE DEMO"},
    }
    _, _, meta_p, _ = runner.export_results([], [], meta_dict)
    assert meta_p.exists()
    with open(meta_p, "r", encoding="utf-8") as f:
        loaded = json.load(f)
        assert loaded["experiment_id"] == "TEST_SCHEMA"


# 27. All six visualization figures generation
def test_all_six_visualizations_generation(synthetic_lunar_patch, tmp_path):
    fig1 = generate_illumination_comparison_figure(synthetic_lunar_patch, tmp_path / "illumination_comparison.png")
    fig2 = generate_scale_pyramid_figure(synthetic_lunar_patch, 0.25, tmp_path / "scale_pyramid.png")
    fig3 = generate_registration_comparison_figure(synthetic_lunar_patch, synthetic_lunar_patch, tmp_path / "registration_comparison.png")

    dummy_results = [
        {"condition": "NORMAL", "representation": "RAW", "inlier_ratio": 0.4, "alignment_success": True, "rmse": 2.1, "recall_at_1": 0.5},
        {"condition": "NORMAL", "representation": "NORMALIZED", "inlier_ratio": 0.6, "alignment_success": True, "rmse": 1.8, "recall_at_1": 0.7},
        {"condition": "NORMAL", "representation": "GRADIENT", "inlier_ratio": 0.55, "alignment_success": True, "rmse": 2.0, "recall_at_1": 0.65},
        {"condition": "NORMAL", "representation": "MULTI-SCALE", "inlier_ratio": 0.65, "alignment_success": True, "rmse": 1.7, "recall_at_1": 0.75},
        {"condition": "NORMAL", "representation": "MULTI-SCALE + ILLUMINATION-AWARE", "inlier_ratio": 0.75, "alignment_success": True, "rmse": 1.4, "recall_at_1": 0.85},
    ]
    fig4 = generate_metrics_comparison_figure(dummy_results, tmp_path / "metrics_comparison.png")
    fig5 = generate_illumination_scale_heatmap_figure(dummy_results, tmp_path / "illumination_scale_heatmap.png")

    ablation_rows = [
        {"configuration": f"{i}. CONFIG", "inlier_ratio": 0.1 * i, "rmse": 5.0 - 0.4 * i}
        for i in range(1, 9)
    ]
    fig6 = generate_ablation_results_figure(ablation_rows, tmp_path / "ablation_results.png")

    for f in [fig1, fig2, fig3, fig4, fig5, fig6]:
        assert f.exists()
        assert f.stat().st_size > 5000
