#!/usr/bin/env python3
"""NEXUS-LUNAR: POC 4 CLI Experiment Runner.

Allows researchers to run the complete illumination and scale robustness experiment
on custom image patches or catalog entries from the command line.

Usage:
  python scripts/run_poc4_experiment.py --source <path> --reference <path> [--source-gsd 0.25] [--ref-gsd 1.0] [--output-dir outputs/poc4]
"""

import sys
import argparse
from pathlib import Path
from PIL import Image
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from packages.data_pipeline import (
    calculate_gsd_ratio,
    POC4ExperimentRunner,
    generate_illumination_comparison_figure,
    generate_scale_pyramid_figure,
    generate_registration_comparison_figure,
    generate_metrics_comparison_figure,
    generate_illumination_scale_heatmap_figure,
    generate_ablation_results_figure,
)
from packages.data_pipeline.poc4_experiment import get_git_commit_hash


def main():
    parser = argparse.ArgumentParser(description="NEXUS-LUNAR: POC-4 Illumination + Scale Experiment CLI")
    parser.add_argument("--source", type=str, required=True, help="Path to source patch image (e.g. OHRC 0.25 m/px)")
    parser.add_argument("--reference", type=str, required=True, help="Path to reference patch image (e.g. LROC 1.0 m/px)")
    parser.add_argument("--source-gsd", type=float, default=0.25, help="Source Ground Sampling Distance in m/pixel (default: 0.25)")
    parser.add_argument("--ref-gsd", type=float, default=1.00, help="Reference Ground Sampling Distance in m/pixel (default: 1.00)")
    parser.add_argument("--output-dir", type=str, default="outputs/poc4", help="Directory for experiment outputs (default: outputs/poc4)")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed (default: 42)")
    args = parser.parse_args()

    src_p = Path(args.source)
    ref_p = Path(args.reference)
    out_d = Path(args.output_dir)
    out_d.mkdir(parents=True, exist_ok=True)

    if not src_p.exists():
        print(f"Error: Source image not found: {src_p}", file=sys.stderr)
        sys.exit(1)
    if not ref_p.exists():
        print(f"Error: Reference image not found: {ref_p}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading Source:    {src_p}")
    print(f"Loading Reference: {ref_p}")
    src_img = np.array(Image.open(src_p).convert("L"))
    ref_img = np.array(Image.open(ref_p).convert("L"))

    gsd_ratio = calculate_gsd_ratio(args.source_gsd, args.ref_gsd)
    print(f"GSD Ratio:         {gsd_ratio:.2f}x")

    runner = POC4ExperimentRunner(output_dir=out_d, seed=args.seed)
    print("Running Experiment Matrix...")
    matrix_results = runner.run_full_matrix(
        source_image=src_img,
        reference_image=ref_img,
        source_gsd=args.source_gsd,
        ref_gsd=args.ref_gsd,
        ground_truth_transform=np.eye(3),
    )

    print("Running Ablation Study...")
    ablation_results = runner.run_ablation_study(
        source_image=src_img,
        reference_image=ref_img,
        source_gsd=args.source_gsd,
        ref_gsd=args.ref_gsd,
        ground_truth_transform=np.eye(3),
    )

    metadata = {
        "experiment_id": f"CLI_POC4_{int(time.time())}",
        "source": {"path": str(src_p.resolve()), "gsd": args.source_gsd},
        "reference": {"path": str(ref_p.resolve()), "gsd": args.ref_gsd},
        "source_gsd": args.source_gsd,
        "reference_gsd": args.ref_gsd,
        "gsd_ratio": gsd_ratio,
        "git_commit": get_git_commit_hash(PROJECT_ROOT),
        "random_seed": args.seed,
    }

    csv_p, json_p, meta_p, fail_p = runner.export_results(matrix_results, ablation_results, metadata)
    print(f"Exported CSV:      {csv_p}")
    print(f"Exported JSON:     {json_p}")

    print("Generating Figures...")
    generate_illumination_comparison_figure(src_img, out_d / "illumination_comparison.png")
    generate_scale_pyramid_figure(src_img, args.source_gsd, out_d / "scale_pyramid.png")
    generate_registration_comparison_figure(src_img, ref_img, out_d / "registration_comparison.png")
    generate_metrics_comparison_figure(matrix_results, out_d / "metrics_comparison.png")
    generate_illumination_scale_heatmap_figure(matrix_results, out_d / "illumination_scale_heatmap.png")
    generate_ablation_results_figure(ablation_results, out_d / "ablation_results.png")

    print(f"All POC-4 outputs generated successfully in {out_d}!")


if __name__ == "__main__":
    import time
    main()
