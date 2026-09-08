"""NEXUS-LUNAR POC-4: Experiment Matrix, Ablation Study & Results Engine.

Runs comprehensive registration benchmarks across representations, illumination perturbations,
and scale disparities. Produces results.csv, results.json, poc4_metadata.json, and failure_cases.json.
"""

from __future__ import annotations
import os
import sys
import csv
import json
import time
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
from PIL import Image

from .illumination_robustness import (
    generate_raw_image,
    generate_normalized_image,
    generate_gradient_image,
    generate_illumination_normalized_image,
    generate_shadow_mask,
    apply_synthetic_illumination_perturbation,
)
from .scale_robustness import (
    calculate_gsd_ratio,
    resample_to_gsd,
    build_image_pyramid,
    apply_synthetic_scale_perturbation,
)
from .poc4_matching import run_classical_registration, RegistrationResult
from .poc4_metrics import (
    calculate_recall_at_k,
    calculate_inlier_ratio,
    calculate_registration_rmse,
    calculate_alignment_success,
    calculate_improvement_deltas,
    FailureCaseTracker,
)


def get_git_commit_hash(repo_dir: Optional[Path] = None) -> str:
    """Safely retrieves the current git commit hash if available."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_dir or Path.cwd()),
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return "UNKNOWN_COMMIT"


class POC4ExperimentRunner:
    """Executes the full POC-4 illumination and scale robustness experiment suite."""

    def __init__(
        self,
        output_dir: Union[str, Path] = "outputs/poc4",
        seed: int = 42,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.seed = seed
        self.failure_tracker = FailureCaseTracker()

    def prepare_representation(
        self,
        image: np.ndarray,
        rep_type: str,
        target_gsd: Optional[float] = None,
        native_gsd: float = 0.25,
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """Prepares a specific image representation and corresponding shadow weight map.
        
        Supported representations:
            - RAW
            - NORMALIZED
            - GRADIENT
            - MULTI_SCALE
            - MULTI_SCALE_ILLUMINATION_AWARE
            - ILLUMINATION_AWARE
        """
        raw = generate_raw_image(image)
        rep_clean = "".join(c if c.isalnum() else "_" for c in rep_type.upper())
        while "__" in rep_clean:
            rep_clean = rep_clean.replace("__", "_")
        rep_upper = rep_clean.strip("_")

        # Check if scale harmonization is requested
        if target_gsd is not None and abs(target_gsd - native_gsd) > 1e-4:
            work_img = resample_to_gsd(raw, native_gsd, target_gsd)
        else:
            work_img = raw

        _, _, shadow_weight = generate_shadow_mask(work_img)

        if rep_upper == "RAW":
            return work_img, shadow_weight

        elif rep_upper == "NORMALIZED":
            norm = generate_normalized_image(work_img)
            return norm, shadow_weight

        elif rep_upper == "GRADIENT":
            grad_mag, _ = generate_gradient_image(work_img)
            return grad_mag, shadow_weight

        elif rep_upper in ("ILLUMINATION_AWARE", "ILLUMINATION_NORMALIZED"):
            illum_norm = generate_illumination_normalized_image(work_img)
            return illum_norm, shadow_weight

        elif rep_upper in ("MULTI_SCALE", "MULTI_SCALE_RAW"):
            # Multi-scale resampled to reference GSD scale with raw representation
            return work_img, shadow_weight

        elif rep_upper in ("MULTI_SCALE_ILLUMINATION_AWARE", "MULTI_SCALE_ILLUMINATION", "ILLUMINATION_AWARE_SCALE"):
            # Harmonized GSD + Illumination-normalized decomposition
            illum_norm = generate_illumination_normalized_image(work_img)
            return illum_norm, shadow_weight


        else:
            raise ValueError(f"Unknown representation type: {rep_type}")

    def run_single_condition(
        self,
        source_raw: np.ndarray,
        ref_raw: np.ndarray,
        rep_type: str,
        illum_cond: str,
        scale_factor: float,
        source_gsd: float,
        ref_gsd: float,
        ground_truth_transform: Optional[np.ndarray] = None,
        ground_truth_type: str = "SYNTHETIC_AFFINE",
    ) -> Dict[str, Any]:
        """Runs registration under a single representation, illumination, and scale condition."""
        # 1. Apply synthetic perturbations if specified
        src_perturbed = apply_synthetic_illumination_perturbation(source_raw, illum_cond, seed=self.seed)
        
        if abs(scale_factor - 1.0) > 1e-4:
            src_perturbed = apply_synthetic_scale_perturbation(src_perturbed, scale_factor)

        # 2. Derive representations
        is_multiscale = ("MULTI" in rep_type.upper()) and ("SCALE" in rep_type.upper())
        target_gsd = ref_gsd if is_multiscale else source_gsd
        src_rep, src_w = self.prepare_representation(src_perturbed, rep_type, target_gsd=target_gsd, native_gsd=source_gsd)
        ref_rep, ref_w = self.prepare_representation(ref_raw, rep_type, target_gsd=ref_gsd, native_gsd=ref_gsd)

        # 3. Execute registration baseline
        reg = run_classical_registration(
            source_image=src_rep,
            reference_image=ref_rep,
            source_shadow_map=src_w,
            reference_shadow_map=ref_w,
            ratio_thresh=0.85,
            min_inliers_thresh=6,
            seed=self.seed,
        )


        if not reg.success and reg.failure_reason:
            self.failure_tracker.record_failure(
                condition=illum_cond,
                representation=rep_type,
                failure_type=reg.failure_reason,
                extra={"scale_factor": scale_factor, "rmse": reg.rmse},
            )

        # 4. Compute Recall@K
        # Adapt ground truth transform according to GSD and scale harmonization
        effective_gt = ground_truth_transform
        if effective_gt is not None:
            if target_gsd == ref_gsd and abs(source_gsd - ref_gsd) > 1e-4:
                # Source was scale-harmonized to reference GSD
                ratio_val = float(scale_factor)
            else:
                # Source remains at native GSD vs reference GSD
                ratio_val = float((source_gsd / ref_gsd) * scale_factor)

            S_mat = np.eye(3)
            S_mat[0, 0] = ratio_val
            S_mat[1, 1] = ratio_val
            effective_gt = S_mat @ ground_truth_transform

        recall_dict = calculate_recall_at_k(
            matches=reg.tentative_matches,
            ground_truth_transform=effective_gt,
            ground_truth_type=ground_truth_type,
        )


        # 5. Shadow fraction
        _, shadow_frac, _ = generate_shadow_mask(src_perturbed)

        return {
            "condition": f"{illum_cond}__scale_{scale_factor}x",
            "representation": rep_type,
            "illumination_condition": illum_cond,
            "scale_factor": float(scale_factor),
            "source_gsd": float(source_gsd),
            "reference_gsd": float(ref_gsd),
            "gsd_ratio": round(calculate_gsd_ratio(source_gsd, ref_gsd), 3),
            "recall_at_1": recall_dict["recall_at_1"],
            "recall_at_5": recall_dict["recall_at_5"],
            "recall_at_10": recall_dict["recall_at_10"],
            "ground_truth_status": recall_dict["ground_truth_status"],
            "inlier_ratio": round(reg.inlier_ratio, 4),
            "rmse": round(reg.rmse, 4) if np.isfinite(reg.rmse) else 999.0,
            "alignment_success": bool(reg.success),
            "feature_count_source": int(reg.feature_count_source),
            "feature_count_reference": int(reg.feature_count_reference),
            "match_count": int(reg.tentative_match_count),
            "valid_match_count": int(reg.tentative_match_count),
            "inlier_count": int(reg.inlier_count),
            "shadow_fraction": round(shadow_frac, 4),
            "processing_time_ms": round(reg.processing_time_ms, 2),
            "failure_reason": reg.failure_reason,
        }

    def run_full_matrix(
        self,
        source_image: np.ndarray,
        reference_image: np.ndarray,
        source_gsd: float = 0.25,
        ref_gsd: float = 1.00,
        ground_truth_transform: Optional[np.ndarray] = None,
        ground_truth_type: str = "SYNTHETIC_AFFINE",
    ) -> List[Dict[str, Any]]:
        """Executes the full experiment matrix across representations, illumination conditions, and scales."""
        representations = [
            "RAW",
            "NORMALIZED",
            "GRADIENT",
            "MULTI-SCALE",
            "MULTI-SCALE + ILLUMINATION-AWARE",
        ]
        illumination_conditions = [
            "NORMAL",
            "DARKENED",
            "BRIGHTENED",
            "LOW_CONTRAST",
            "HIGH_CONTRAST",
            "GAMMA_SHIFT",
            "ILLUMINATION_GRADIENT",
            "SHADOW_PERTURBATION",
        ]
        scale_factors = [1.0, 0.5, 0.25]

        all_results: List[Dict[str, Any]] = []

        # Run conditions
        for illum in illumination_conditions:
            for rep in representations:
                # Primary illumination test at native scale 1.0x
                res = self.run_single_condition(
                    source_raw=source_image,
                    ref_raw=reference_image,
                    rep_type=rep,
                    illum_cond=illum,
                    scale_factor=1.0,
                    source_gsd=source_gsd,
                    ref_gsd=ref_gsd,
                    ground_truth_transform=ground_truth_transform,
                    ground_truth_type=ground_truth_type,
                )
                all_results.append(res)

        # Scale variations under NORMAL illumination
        for s in [0.5, 0.25]:
            for rep in representations:
                res = self.run_single_condition(
                    source_raw=source_image,
                    ref_raw=reference_image,
                    rep_type=rep,
                    illum_cond="NORMAL",
                    scale_factor=s,
                    source_gsd=source_gsd,
                    ref_gsd=ref_gsd,
                    ground_truth_transform=ground_truth_transform,
                    ground_truth_type=ground_truth_type,
                )
                all_results.append(res)

        # Compute improvement deltas relative to RAW baseline for each condition
        indexed_by_cond: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for r in all_results:
            cond = r["condition"]
            rep = r["representation"]
            if cond not in indexed_by_cond:
                indexed_by_cond[cond] = {}
            indexed_by_cond[cond][rep] = r

        for cond, reps in indexed_by_cond.items():
            raw_res = reps.get("RAW")
            if raw_res:
                for rep_name, res_dict in reps.items():
                    deltas = calculate_improvement_deltas(res_dict, raw_res)
                    res_dict.update(deltas)

        return all_results

    def run_ablation_study(
        self,
        source_image: np.ndarray,
        reference_image: np.ndarray,
        source_gsd: float = 0.25,
        ref_gsd: float = 1.00,
        ground_truth_transform: Optional[np.ndarray] = None,
        ground_truth_type: str = "SYNTHETIC_AFFINE",
    ) -> List[Dict[str, Any]]:
        """Runs the 8-stage ablation study under challenging mixed illumination (DARKENED + GRADIENT) and scale."""
        ablation_configs = [
            ("1. RAW", "RAW", False),
            ("2. RAW + SCALE", "RAW", True),
            ("3. NORMALIZED", "NORMALIZED", False),
            ("4. NORMALIZED + SCALE", "NORMALIZED", True),
            ("5. GRADIENT", "GRADIENT", False),
            ("6. GRADIENT + SCALE", "GRADIENT", True),
            ("7. ILLUMINATION-AWARE", "ILLUMINATION_AWARE", False),
            ("8. ILLUMINATION-AWARE + SCALE", "MULTI-SCALE + ILLUMINATION-AWARE", True),
        ]

        ablation_results: List[Dict[str, Any]] = []
        raw_baseline: Optional[Dict[str, Any]] = None

        for label, rep_type, use_scale in ablation_configs:
            target_g = ref_gsd if use_scale else source_gsd
            src_rep, src_w = self.prepare_representation(
                source_image, rep_type, target_gsd=target_g, native_gsd=source_gsd
            )
            ref_rep, ref_w = self.prepare_representation(
                reference_image, rep_type, target_gsd=ref_gsd, native_gsd=ref_gsd
            )

            reg = run_classical_registration(
                source_image=src_rep,
                reference_image=ref_rep,
                source_shadow_map=src_w,
                reference_shadow_map=ref_w,
                seed=self.seed,
            )

            recall_dict = calculate_recall_at_k(
                matches=reg.tentative_matches,
                ground_truth_transform=ground_truth_transform,
                ground_truth_type=ground_truth_type,
            )

            row = {
                "configuration": label,
                "representation": rep_type,
                "scale_harmonized": use_scale,
                "recall_at_1": recall_dict["recall_at_1"],
                "recall_at_5": recall_dict["recall_at_5"],
                "recall_at_10": recall_dict["recall_at_10"],
                "inlier_ratio": round(reg.inlier_ratio, 4),
                "rmse": round(reg.rmse, 4) if np.isfinite(reg.rmse) else 999.0,
                "alignment_success": bool(reg.success),
                "inlier_count": int(reg.inlier_count),
                "match_count": int(reg.tentative_match_count),
                "processing_time_ms": round(reg.processing_time_ms, 2),
            }

            if raw_baseline is None:
                raw_baseline = row

            deltas = calculate_improvement_deltas(row, raw_baseline)
            row.update(deltas)
            ablation_results.append(row)

        return ablation_results

    def export_results(
        self,
        matrix_results: List[Dict[str, Any]],
        ablation_results: List[Dict[str, Any]],
        metadata: Dict[str, Any],
    ) -> Tuple[Path, Path, Path, Path]:
        """Saves results.csv, results.json, poc4_metadata.json, and failure_cases.json."""
        csv_path = self.output_dir / "results.csv"
        json_path = self.output_dir / "results.json"
        meta_path = self.output_dir / "poc4_metadata.json"
        failure_path = self.output_dir / "failure_cases.json"

        # 1. Export CSV
        if matrix_results:
            fieldnames = [
                "condition", "representation", "illumination_condition", "scale_factor",
                "source_gsd", "reference_gsd", "gsd_ratio",
                "recall_at_1", "recall_at_5", "recall_at_10", "ground_truth_status",
                "inlier_ratio", "rmse", "alignment_success",
                "feature_count_source", "feature_count_reference", "match_count",
                "valid_match_count", "inlier_count", "shadow_fraction",
                "processing_time_ms", "delta_recall_at_1", "delta_inlier_ratio",
                "delta_rmse", "pct_rmse_reduction", "failure_reason"
            ]
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                for row in matrix_results:
                    writer.writerow(row)

        # 2. Export Failure Cases
        self.failure_tracker.export_json(failure_path)

        # 3. Compute best representation dynamically (composite score)
        rep_scores: Dict[str, List[float]] = {}
        for r in matrix_results:
            rep = r["representation"]
            if rep not in rep_scores:
                rep_scores[rep] = []
            # Composite score = alignment_success * 50 + inlier_ratio * 30 + max(0, 20 - min(20, rmse))
            succ_score = 50.0 if r["alignment_success"] else 0.0
            inl_score = r["inlier_ratio"] * 30.0
            rmse_score = max(0.0, 20.0 - min(20.0, r["rmse"]))
            composite = succ_score + inl_score + rmse_score
            rep_scores[rep].append(composite)

        mean_rep_scores = {rep: float(np.mean(scores)) for rep, scores in rep_scores.items()}
        best_rep = max(mean_rep_scores.items(), key=lambda x: x[1])[0] if mean_rep_scores else "RAW"

        # 4. Statistical Summary & Representation Aggregates
        stat_summary: Dict[str, Any] = {}
        for metric in ["recall_at_1", "recall_at_5", "recall_at_10", "inlier_ratio", "rmse"]:
            vals = [float(r[metric]) for r in matrix_results if r.get(metric) is not None and np.isfinite(r[metric])]
            if vals:
                stat_summary[metric] = {
                    "mean": round(float(np.mean(vals)), 4),
                    "median": round(float(np.median(vals)), 4),
                    "std_dev": round(float(np.std(vals)), 4),
                }

        rep_summary_metrics: Dict[str, Any] = {}
        for r_name in ["RAW", "NORMALIZED", "GRADIENT", "MULTI-SCALE", "MULTI-SCALE + ILLUMINATION-AWARE"]:
            matching = [r for r in matrix_results if r["representation"].upper() == r_name.upper()]
            if matching:
                succ_rate = float(np.mean([1.0 if r["alignment_success"] else 0.0 for r in matching]))
                inlier_r = float(np.mean([r["inlier_ratio"] for r in matching]))
                valid_rmse = [r["rmse"] for r in matching if np.isfinite(r["rmse"]) and r["rmse"] < 50.0]
                mean_rmse = float(np.mean(valid_rmse)) if valid_rmse else 999.0
                valid_r1 = [r["recall_at_1"] for r in matching if r.get("recall_at_1") is not None]
                mean_r1 = float(np.mean(valid_r1)) if valid_r1 else 0.0
                rep_summary_metrics[r_name] = {
                    "success_rate": round(succ_rate, 4),
                    "mean_inlier_ratio": round(inlier_r, 4),
                    "mean_rmse": round(mean_rmse, 2),
                    "mean_recall_1": round(mean_r1, 4),
                }

        ablation_mapped = []
        for row in ablation_results:
            ablation_mapped.append({
                **row,
                "config_name": row.get("configuration", ""),
                "success": row.get("alignment_success", False),
            })

        summary_dict = {
            "best_representation": best_rep,
            "representation_metrics": rep_summary_metrics,
        }

        # 5. Export JSON
        full_json = {
            "experiment_id": metadata.get("experiment_id", f"EXP_POC4_{int(time.time())}"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "best_performing_representation": best_rep,
            "representation_ranking": sorted(mean_rep_scores.items(), key=lambda x: x[1], reverse=True),
            "summary": summary_dict,
            "statistical_summary": stat_summary,
            "statistical_disclaimer": "Single-pair demonstration; statistical generalization is not possible.",
            "sample_counts": metadata.get("sample_counts", {}),
            "data_provenance": metadata.get("data_provenance", {}),
            "matrix_results": matrix_results,
            "ablation_results": ablation_results,
            "ablation": ablation_mapped,
            "failure_summary": self.failure_tracker.counts,
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(full_json, f, indent=2)

        # 6. Export Metadata JSON
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        return csv_path, json_path, meta_path, failure_path
