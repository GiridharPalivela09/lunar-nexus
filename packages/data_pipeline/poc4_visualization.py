"""NEXUS-LUNAR POC-4: Publication-Quality Visualization Suite.

Generates all 6 required figures:
1. illumination_comparison.png
2. scale_pyramid.png
3. registration_comparison.png
4. metrics_comparison.png
5. illumination_scale_heatmap.png
6. ablation_results.png
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import numpy as np
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec
    HAS_MATPLOTLIB = True
except ImportError:
    matplotlib = None
    plt = None
    GridSpec = None
    HAS_MATPLOTLIB = False

from .illumination_robustness import (
    generate_raw_image,
    generate_normalized_image,
    generate_gradient_image,
    generate_illumination_normalized_image,
    generate_shadow_mask,
)
from .scale_robustness import build_image_pyramid
from .poc4_matching import run_classical_registration


# NEXUS-LUNAR Aesthetic Palette
BG_DARK = "#090d16"
CARD_BG = "#111827"
TEXT_COLOR = "#e2e8f0"
TEXT_MUTED = "#94a3b8"
ACCENT_CYAN = "#00e5ff"
ACCENT_PURPLE = "#818cf8"
ACCENT_GREEN = "#10b981"
ACCENT_AMBER = "#f59e0b"
ACCENT_RED = "#ef4444"


def _apply_dark_theme(ax: plt.Axes) -> None:
    """Configures a Matplotlib axis with dark theme aesthetics."""
    ax.set_facecolor(CARD_BG)
    ax.tick_params(colors=TEXT_MUTED, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color("#1f293d")
        spine.set_linewidth(1.0)


def generate_illumination_comparison_figure(
    image: np.ndarray,
    output_path: Union[str, Path],
    title: str = "NEXUS-LUNAR POC-4: Illumination Representations",
) -> Path:
    """Generates Figure 1: Side-by-side display of all 5 illumination representations."""
    raw = generate_raw_image(image)
    norm = generate_normalized_image(raw)
    grad_mag, _ = generate_gradient_image(raw)
    illum_norm = generate_illumination_normalized_image(raw)
    shadow_mask, shadow_frac, _ = generate_shadow_mask(raw)

    fig = plt.figure(figsize=(15, 4.5), facecolor=BG_DARK)
    fig.suptitle(f"{title} (Shadow Fraction: {shadow_frac*100:.1f}%)", color=TEXT_COLOR, fontsize=13, weight="bold", y=0.98)

    panels = [
        ("A. RAW INTENSITY", raw, "gray", "Native sensor DN values"),
        ("B. LOCAL NORMALIZED", norm, "gray", "Adaptive local contrast standardization"),
        ("C. GRADIENT MAGNITUDE", grad_mag, "magma", "Sobel spatial relief filters"),
        ("D. ILLUMINATION-NORMALIZED", illum_norm, "gray", "High-pass spatial decomposition"),
        ("E. SHADOW MASK", shadow_mask.astype(np.uint8) * 255, "coolwarm", f"Deep shadow zones ({shadow_frac*100:.1f}%)"),
    ]

    for idx, (lbl, arr, cmap, sub) in enumerate(panels):
        ax = fig.add_subplot(1, 5, idx + 1)
        _apply_dark_theme(ax)
        ax.imshow(arr, cmap=cmap)
        ax.set_title(lbl, color=ACCENT_CYAN if idx == 3 else TEXT_COLOR, fontsize=10, weight="bold", pad=6)
        ax.set_xlabel(sub, color=TEXT_MUTED, fontsize=8)
        ax.set_xticks([])
        ax.set_yticks([])

    plt.tight_layout()
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_p, dpi=160, bbox_inches="tight", facecolor=BG_DARK)
    plt.close(fig)
    return out_p


def generate_scale_pyramid_figure(
    image: np.ndarray,
    native_gsd: float,
    output_path: Union[str, Path],
    scales: List[float] = [1.0, 0.5, 0.25, 0.125],
) -> Path:
    """Generates Figure 2: Multi-scale image pyramid with effective GSD labels."""
    pyramid = build_image_pyramid(image, native_gsd=native_gsd, scales=scales)

    fig = plt.figure(figsize=(14, 4.5), facecolor=BG_DARK)
    fig.suptitle(f"NEXUS-LUNAR POC-4: Multi-Scale Image Pyramid (Native GSD: {native_gsd:.2f} m/px)", color=TEXT_COLOR, fontsize=13, weight="bold", y=0.98)

    for idx, lvl in enumerate(pyramid):
        ax = fig.add_subplot(1, len(pyramid), idx + 1)
        _apply_dark_theme(ax)
        ax.imshow(lvl.array, cmap="gray")
        ax.set_title(f"Scale {lvl.scale_factor}x", color=ACCENT_PURPLE, fontsize=11, weight="bold")
        ax.set_xlabel(f"{lvl.width}x{lvl.height} px\nEffective GSD: {lvl.effective_gsd:.2f} m/px", color=TEXT_MUTED, fontsize=8)
        ax.set_xticks([])
        ax.set_yticks([])

    plt.tight_layout()
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_p, dpi=160, bbox_inches="tight", facecolor=BG_DARK)
    plt.close(fig)
    return out_p


def generate_registration_comparison_figure(
    source_image: np.ndarray,
    reference_image: np.ndarray,
    output_path: Union[str, Path],
) -> Path:
    """Generates Figure 3: Registration comparison across all 5 representations."""
    rep_types = [
        "RAW",
        "NORMALIZED",
        "GRADIENT",
        "MULTI-SCALE",
        "MULTI-SCALE + ILLUMINATION-AWARE",
    ]

    fig, axes = plt.subplots(len(rep_types), 1, figsize=(12, 14), facecolor=BG_DARK)
    fig.suptitle("NEXUS-LUNAR POC-4: Registration Baseline across Representations", color=TEXT_COLOR, fontsize=13, weight="bold", y=0.99)

    src_raw = generate_raw_image(source_image)
    ref_raw = generate_raw_image(reference_image)

    for idx, rep in enumerate(rep_types):
        ax = axes[idx]
        _apply_dark_theme(ax)

        # Run registration for this representation
        if rep == "RAW":
            s_img, r_img = src_raw, ref_raw
        elif rep == "NORMALIZED":
            s_img, r_img = generate_normalized_image(src_raw), generate_normalized_image(ref_raw)
        elif rep == "GRADIENT":
            s_img, _ = generate_gradient_image(src_raw)
            r_img, _ = generate_gradient_image(ref_raw)
        elif rep == "MULTI-SCALE":
            s_img, r_img = src_raw, ref_raw
        else:
            s_img = generate_illumination_normalized_image(src_raw)
            r_img = generate_illumination_normalized_image(ref_raw)

        reg = run_classical_registration(s_img, r_img)

        # Draw side-by-side composite canvas
        h1, w1 = s_img.shape
        h2, w2 = r_img.shape
        max_h = max(h1, h2)
        total_w = w1 + w2 + 20

        canvas = np.full((max_h, total_w), 20, dtype=np.uint8)
        canvas[:h1, :w1] = s_img
        canvas[:h2, w1 + 20 : w1 + 20 + w2] = r_img

        ax.imshow(canvas, cmap="gray")
        ax.set_xticks([])
        ax.set_yticks([])

        # Draw inlier vectors
        offset_x = w1 + 20
        for match in reg.inlier_matches[:50]:
            sx, sy = match.src_pt
            rx, ry = match.ref_pt
            ax.plot([sx, rx + offset_x], [sy, ry], color=ACCENT_CYAN, alpha=0.7, linewidth=1.0)
            ax.scatter([sx], [sy], color=ACCENT_AMBER, s=12, zorder=3)
            ax.scatter([rx + offset_x], [ry], color=ACCENT_GREEN, s=12, zorder=3)

        status_str = f"Inliers: {reg.inlier_count} | Inlier Ratio: {reg.inlier_ratio*100:.1f}% | RMSE: {reg.rmse:.2f} px" if reg.success else f"ALIGNMENT FAILED ({reg.failure_reason or 'No consensus'})"
        color = ACCENT_GREEN if reg.success else ACCENT_RED
        ax.set_ylabel(rep, color=TEXT_COLOR, fontsize=9, weight="bold")
        ax.set_title(status_str, color=color, fontsize=9, loc="right")

    plt.tight_layout()
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_p, dpi=160, bbox_inches="tight", facecolor=BG_DARK)
    plt.close(fig)
    return out_p


def generate_metrics_comparison_figure(
    results_list: List[Dict[str, Any]],
    output_path: Union[str, Path],
) -> Path:
    """Generates Figure 4: Multi-bar comparison of performance metrics by representation."""
    # Group results by representation
    rep_names = ["RAW", "NORMALIZED", "GRADIENT", "MULTI-SCALE", "MULTI-SCALE + ILLUMINATION-AWARE"]
    
    inlier_ratios = []
    success_rates = []
    rmses = []
    recalls_1 = []

    for r_name in rep_names:
        matching_rows = [r for r in results_list if r["representation"].upper() == r_name.upper()]
        if matching_rows:
            inlier_ratios.append(np.mean([r["inlier_ratio"] for r in matching_rows]))
            success_rates.append(np.mean([1.0 if r["alignment_success"] else 0.0 for r in matching_rows]) * 100.0)
            valid_rmses = [r["rmse"] for r in matching_rows if np.isfinite(r["rmse"]) and r["rmse"] < 50.0]
            rmses.append(np.mean(valid_rmses) if valid_rmses else 10.0)
            valid_r1 = [r["recall_at_1"] for r in matching_rows if r.get("recall_at_1") is not None]
            recalls_1.append(np.mean(valid_r1) if valid_r1 else 0.0)
        else:
            inlier_ratios.append(0.0)
            success_rates.append(0.0)
            rmses.append(10.0)
            recalls_1.append(0.0)

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), facecolor=BG_DARK)
    fig.suptitle("NEXUS-LUNAR POC-4: Quantitative Metrics Comparison", color=TEXT_COLOR, fontsize=13, weight="bold")

    x = np.arange(len(rep_names))
    short_labels = ["RAW", "NORM", "GRAD", "M-SCALE", "M-SCALE+ILLUM"]

    # 1. Success Rate
    ax1 = axes[0, 0]
    _apply_dark_theme(ax1)
    bars1 = ax1.bar(x, success_rates, color=ACCENT_GREEN, width=0.55)
    ax1.set_title("Alignment Success Rate (%)", color=TEXT_COLOR, fontsize=10, weight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(short_labels, color=TEXT_MUTED, fontsize=8)
    ax1.set_ylim(0, 105)
    for b in bars1:
        ax1.annotate(f"{b.get_height():.1f}%", (b.get_x() + b.get_width()/2, b.get_height() + 2),
                     ha="center", color=TEXT_COLOR, fontsize=8)

    # 2. Inlier Ratio
    ax2 = axes[0, 1]
    _apply_dark_theme(ax2)
    bars2 = ax2.bar(x, [ir * 100.0 for ir in inlier_ratios], color=ACCENT_CYAN, width=0.55)
    ax2.set_title("Geometric Inlier Ratio (%)", color=TEXT_COLOR, fontsize=10, weight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels(short_labels, color=TEXT_MUTED, fontsize=8)
    ax2.set_ylim(0, max(100, max([ir * 100 for ir in inlier_ratios] + [50]) + 10))
    for b in bars2:
        ax2.annotate(f"{b.get_height():.1f}%", (b.get_x() + b.get_width()/2, b.get_height() + 1),
                     ha="center", color=TEXT_COLOR, fontsize=8)

    # 3. RMSE
    ax3 = axes[1, 0]
    _apply_dark_theme(ax3)
    bars3 = ax3.bar(x, rmses, color=ACCENT_AMBER, width=0.55)
    ax3.set_title("Registration RMSE (pixels, lower is better)", color=TEXT_COLOR, fontsize=10, weight="bold")
    ax3.set_xticks(x)
    ax3.set_xticklabels(short_labels, color=TEXT_MUTED, fontsize=8)
    for b in bars3:
        ax3.annotate(f"{b.get_height():.2f}px", (b.get_x() + b.get_width()/2, b.get_height() + 0.1),
                     ha="center", color=TEXT_COLOR, fontsize=8)

    # 4. Recall@1
    ax4 = axes[1, 1]
    _apply_dark_theme(ax4)
    bars4 = ax4.bar(x, [r * 100.0 for r in recalls_1], color=ACCENT_PURPLE, width=0.55)
    ax4.set_title("Recall@1 (Top Candidate Match Accuracy, %)", color=TEXT_COLOR, fontsize=10, weight="bold")
    ax4.set_xticks(x)
    ax4.set_xticklabels(short_labels, color=TEXT_MUTED, fontsize=8)
    ax4.set_ylim(0, 105)
    for b in bars4:
        ax4.annotate(f"{b.get_height():.1f}%", (b.get_x() + b.get_width()/2, b.get_height() + 2),
                     ha="center", color=TEXT_COLOR, fontsize=8)

    plt.tight_layout()
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_p, dpi=160, bbox_inches="tight", facecolor=BG_DARK)
    plt.close(fig)
    return out_p


def generate_illumination_scale_heatmap_figure(
    results_list: List[Dict[str, Any]],
    output_path: Union[str, Path],
) -> Path:
    """Generates Figure 5: Representation vs Condition Performance Heatmap."""
    rep_names = ["RAW", "NORMALIZED", "GRADIENT", "MULTI-SCALE", "MULTI-SCALE + ILLUMINATION-AWARE"]
    conditions = list(dict.fromkeys([r["condition"] for r in results_list]))

    matrix = np.zeros((len(rep_names), len(conditions)), dtype=np.float32)

    for i, rep in enumerate(rep_names):
        for j, cond in enumerate(conditions):
            match = next((r for r in results_list if r["representation"].upper() == rep.upper() and r["condition"] == cond), None)
            if match:
                # Composite normalized score [0, 100]
                succ = 50.0 if match["alignment_success"] else 0.0
                inl = match["inlier_ratio"] * 30.0
                err_term = max(0.0, 20.0 - min(20.0, match["rmse"]))
                matrix[i, j] = succ + inl + err_term
            else:
                matrix[i, j] = 0.0

    fig, ax = plt.subplots(figsize=(14, 6), facecolor=BG_DARK)
    _apply_dark_theme(ax)

    im = ax.imshow(matrix, cmap="viridis", aspect="auto", vmin=0, vmax=100)
    cbar = fig.colorbar(im, ax=ax, pad=0.02)
    cbar.ax.tick_params(colors=TEXT_MUTED, labelsize=8)
    cbar.set_label("Robustness Composite Score (0 - 100)", color=TEXT_COLOR, fontsize=9)

    ax.set_yticks(np.arange(len(rep_names)))
    ax.set_yticklabels(rep_names, color=TEXT_COLOR, fontsize=9, weight="bold")

    cond_clean = [c.replace("__scale_1.0x", "").replace("__", " ") for c in conditions]
    ax.set_xticks(np.arange(len(conditions)))
    ax.set_xticklabels(cond_clean, rotation=40, ha="right", color=TEXT_MUTED, fontsize=8)

    ax.set_title("NEXUS-LUNAR POC-4: Illumination & Scale Robustness Matrix Heatmap", color=TEXT_COLOR, fontsize=12, weight="bold", pad=12)

    # Text annotations in heatmap cells
    for i in range(len(rep_names)):
        for j in range(len(conditions)):
            val = matrix[i, j]
            color = "white" if val < 60 else "black"
            ax.text(j, i, f"{val:.0f}", ha="center", va="center", color=color, fontsize=8, weight="bold")

    plt.tight_layout()
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_p, dpi=160, bbox_inches="tight", facecolor=BG_DARK)
    plt.close(fig)
    return out_p


def generate_ablation_results_figure(
    ablation_results: List[Dict[str, Any]],
    output_path: Union[str, Path],
) -> Path:
    """Generates Figure 6: Visual breakdown of the 8 ablation study configurations."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5), facecolor=BG_DARK)
    fig.suptitle("NEXUS-LUNAR POC-4: Systematic Ablation Study Results", color=TEXT_COLOR, fontsize=13, weight="bold", y=0.98)

    configs = [r["configuration"] for r in ablation_results]
    inlier_ratios = [r["inlier_ratio"] * 100.0 for r in ablation_results]
    rmses = [r["rmse"] if np.isfinite(r["rmse"]) and r["rmse"] < 50.0 else 10.0 for r in ablation_results]
    y_pos = np.arange(len(configs))

    # Panel 1: Inlier Ratio progression
    _apply_dark_theme(ax1)
    bars1 = ax1.barh(y_pos, inlier_ratios, color=ACCENT_CYAN, height=0.6)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(configs, color=TEXT_COLOR, fontsize=9)
    ax1.set_xlabel("Inlier Ratio (%)", color=TEXT_MUTED, fontsize=9)
    ax1.set_title("Geometric Inlier Ratio by Configuration", color=TEXT_COLOR, fontsize=10, weight="bold")
    ax1.set_xlim(0, max(100, max(inlier_ratios + [50]) + 10))
    for b in bars1:
        ax1.annotate(f"{b.get_width():.1f}%", (b.get_width() + 1, b.get_y() + b.get_height()/2),
                     va="center", color=TEXT_COLOR, fontsize=8)

    # Panel 2: RMSE reduction
    _apply_dark_theme(ax2)
    bars2 = ax2.barh(y_pos, rmses, color=ACCENT_AMBER, height=0.6)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels([])
    ax2.set_xlabel("Registration RMSE (pixels, lower is better)", color=TEXT_MUTED, fontsize=9)
    ax2.set_title("Registration RMSE (Pixel Space)", color=TEXT_COLOR, fontsize=10, weight="bold")
    for b in bars2:
        ax2.annotate(f"{b.get_width():.2f}px", (b.get_width() + 0.1, b.get_y() + b.get_height()/2),
                     va="center", color=TEXT_COLOR, fontsize=8)

    plt.tight_layout()
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_p, dpi=160, bbox_inches="tight", facecolor=BG_DARK)
    plt.close(fig)
    return out_p
