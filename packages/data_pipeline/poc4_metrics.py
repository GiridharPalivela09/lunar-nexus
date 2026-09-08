"""NEXUS-LUNAR POC-4: Quantitative Evaluation Metrics & Failure Case Tracking Engine.

Implements Recall@K with strict ground truth verification, Inlier Ratio,
Registration RMSE, Alignment Success Criteria, Improvement Delta calculations,
and Failure Case tracking.
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np

from .poc4_matching import KeypointMatch


def calculate_recall_at_k(
    matches: List[KeypointMatch],
    ground_truth_transform: Optional[np.ndarray],
    k_list: List[int] = [1, 5, 10],
    dist_thresh_px: float = 5.0,
    ground_truth_type: str = "SYNTHETIC_AFFINE",
) -> Dict[str, Any]:
    """Calculates Recall@K based on strict ground truth geometric transformation.
    
    If ground truth is unavailable or None, it returns None values with:
    "ground_truth_status": "GROUND TRUTH UNAVAILABLE"
    to ensure scientific transparency and prevent fabricated scores.
    """
    if ground_truth_transform is None or ground_truth_type == "UNAVAILABLE":
        result = {f"recall_at_{k}": None for k in k_list}
        result["ground_truth_status"] = "GROUND TRUTH UNAVAILABLE"
        result["ground_truth_type"] = "UNAVAILABLE"
        result["ground_truth_tolerance_px"] = float(dist_thresh_px)
        return result

    if not matches:
        result = {f"recall_at_{k}": 0.0 for k in k_list}
        result["ground_truth_status"] = "AVAILABLE"
        result["ground_truth_type"] = ground_truth_type
        result["ground_truth_tolerance_px"] = float(dist_thresh_px)
        return result

    # Transform ground truth: p_ref_true = A * p_src + t
    A = ground_truth_transform[:2, :2]
    t = ground_truth_transform[:2, 2] if ground_truth_transform.shape[1] > 2 else np.zeros(2)

    src_pts = np.array([m.src_pt for m in matches], dtype=np.float64)
    ref_pts = np.array([m.ref_pt for m in matches], dtype=np.float64)

    proj_true = (A @ src_pts.T).T + t
    spatial_errors = np.linalg.norm(proj_true - ref_pts, axis=1)
    is_correct = spatial_errors <= dist_thresh_px

    n_matches = len(matches)
    result = {
        "ground_truth_status": "AVAILABLE",
        "ground_truth_type": ground_truth_type,
        "ground_truth_tolerance_px": float(dist_thresh_px),
    }

    # For pairwise matches sorted by descriptor distance, Recall@K evaluates
    # fraction of correct matches within top-K candidates
    for k in k_list:
        sub_k = min(k, n_matches)
        correct_in_k = np.count_nonzero(is_correct[:sub_k])
        # Recall relative to evaluated K slice
        recall_k = float(correct_in_k / max(1, sub_k))
        result[f"recall_at_{k}"] = round(recall_k, 4)

    return result


def calculate_inlier_ratio(inlier_count: int, valid_match_count: int) -> float:
    """Calculates inlier ratio safely, guarding against division by zero."""
    if valid_match_count <= 0:
        return 0.0
    return float(np.clip(inlier_count / valid_match_count, 0.0, 1.0))


def calculate_registration_rmse(
    src_pts: np.ndarray,
    ref_pts: np.ndarray,
    affine_matrix: Optional[np.ndarray],
) -> float:
    """Calculates geometric registration RMSE across verified correspondences."""
    if affine_matrix is None or src_pts.size == 0 or ref_pts.size == 0:
        return float("inf")

    if src_pts.shape[0] != ref_pts.shape[0]:
        raise ValueError("Source and reference points must have the same count")

    A = affine_matrix[:2, :2]
    t = affine_matrix[:2, 2] if affine_matrix.shape[1] > 2 else np.zeros(2)

    proj = (A @ src_pts.T).T + t
    errors = np.linalg.norm(proj - ref_pts, axis=1)
    return float(np.sqrt(np.mean(errors ** 2)))


def calculate_alignment_success(
    rmse: float,
    inlier_count: int,
    max_rmse_thresh: float = 5.0,
    min_inliers_thresh: int = 8,
) -> bool:
    """Evaluates whether registration succeeded according to strict scientific criteria."""
    return bool(np.isfinite(rmse) and (rmse <= max_rmse_thresh) and (inlier_count >= min_inliers_thresh))


def calculate_improvement_deltas(
    method_metrics: Dict[str, Any],
    raw_metrics: Dict[str, Any],
) -> Dict[str, Any]:
    """Calculates metric deltas and percentage improvements relative to the RAW baseline.
    
    Higher-is-better metrics (Recall@K, Inlier Ratio):
        delta = method_metric - raw_metric
    Lower-is-better metrics (RMSE):
        delta_rmse = raw_rmse - method_rmse (positive means reduced error)
    """
    deltas: Dict[str, Any] = {}

    # Recall deltas
    for k in [1, 5, 10]:
        key = f"recall_at_{k}"
        m_val = method_metrics.get(key)
        r_val = raw_metrics.get(key)
        if m_val is not None and r_val is not None:
            deltas[f"delta_{key}"] = round(float(m_val - r_val), 4)
        else:
            deltas[f"delta_{key}"] = None

    # Inlier ratio delta
    m_ir = method_metrics.get("inlier_ratio", 0.0)
    r_ir = raw_metrics.get("inlier_ratio", 0.0)
    deltas["delta_inlier_ratio"] = round(float(m_ir - r_ir), 4)

    # RMSE delta (raw_rmse - method_rmse)
    m_rmse = method_metrics.get("rmse", float("inf"))
    r_rmse = raw_metrics.get("rmse", float("inf"))
    if np.isfinite(m_rmse) and np.isfinite(r_rmse):
        deltas["delta_rmse"] = round(float(r_rmse - m_rmse), 4)
        if r_rmse > 1e-4:
            pct_rmse_reduction = ((r_rmse - m_rmse) / r_rmse) * 100.0
            deltas["pct_rmse_reduction"] = round(float(pct_rmse_reduction), 2)
        else:
            deltas["pct_rmse_reduction"] = 0.0
    else:
        deltas["delta_rmse"] = 0.0
        deltas["pct_rmse_reduction"] = 0.0

    # Alignment success change
    m_succ = int(bool(method_metrics.get("alignment_success", False)))
    r_succ = int(bool(raw_metrics.get("alignment_success", False)))
    deltas["delta_alignment_success"] = m_succ - r_succ

    return deltas


@dataclass
class FailureCaseTracker:
    """Tracks, aggregates, and exports failure instances across experiment runs."""
    counts: Dict[str, int] = field(
        default_factory=lambda: {
            "no_features": 0,
            "no_descriptors": 0,
            "no_matches": 0,
            "insufficient_matches": 0,
            "ransac_failure": 0,
            "high_rmse": 0,
            "alignment_failure": 0,
        }
    )
    details: List[Dict[str, Any]] = field(default_factory=list)

    def record_failure(
        self,
        condition: str,
        representation: str,
        failure_type: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        if failure_type in self.counts:
            self.counts[failure_type] += 1
        else:
            self.counts["alignment_failure"] += 1

        record = {
            "condition": condition,
            "representation": representation,
            "failure_type": failure_type,
            "extra": extra or {},
        }
        self.details.append(record)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "failure_counts": self.counts,
            "total_failures": sum(self.counts.values()),
            "failure_details": self.details,
        }

    def export_json(self, output_path: Union[str, Path]) -> None:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
