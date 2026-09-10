"""NEXUS-LUNAR POC-6: Visualization Engine.

Generates 6 publication-ready diagnostic visualizations in outputs/poc6/:
1. geometric_verification_gallery.png (visual verification showing correspondences & ACCEPT/REJECT badges)
2. inlier_ratio_vs_confidence.png (scatter plot of Inlier Ratio vs Verification Confidence)
3. spatial_distribution_inliers.png (4x4 spatial grid occupancy and inlier spread)
4. confidence_score_breakdown.png (multi-signal confidence score component breakdown)
5. accepted_vs_rejected_scatter.png (AI similarity vs Verification Confidence showing rejection of false positives)
6. xai_rejection_reasons_breakdown.png (frequency histogram of XAI failure diagnostic codes)
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.lines import Line2D
    HAS_MATPLOTLIB = True
except ImportError:
    matplotlib = None
    plt = None
    patches = None
    Line2D = None
    HAS_MATPLOTLIB = False

from .poc6_verification import VerifiedCandidateMatch


def plot_geometric_verification_gallery(
    results: List[VerifiedCandidateMatch],
    image_registry: Dict[str, np.ndarray],
    output_path: Union[str, Path] = "outputs/poc6/geometric_verification_gallery.png",
    max_pairs: int = 4,
) -> Path:
    """Renders side-by-side patch comparisons with tentative vs inlier match lines and ACCEPT/REJECT badges."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Pick sample accepted and sample rejected matches
    accepted = [r for r in results if r.accepted]
    rejected = [r for r in results if not r.accepted]

    selected: List[VerifiedCandidateMatch] = []
    if accepted:
        selected.extend(accepted[:max(1, max_pairs // 2)])
    if rejected:
        selected.extend(rejected[:max(1, max_pairs - len(selected))])
    if not selected:
        selected = results[:max_pairs]

    n_show = len(selected)
    if n_show == 0:
        return out

    fig, axes = plt.subplots(n_show, 1, figsize=(11, 3.2 * n_show), facecolor="#0e131f")
    if n_show == 1:
        axes = [axes]

    for idx, (ax, r) in enumerate(zip(axes, selected)):
        ax.set_facecolor("#151d2f")
        q_img = image_registry.get(r.query_patch_id, np.zeros((128, 128), dtype=np.float32))
        c_img = image_registry.get(r.candidate_patch_id, np.zeros((128, 128), dtype=np.float32))

        # Composite side-by-side image with gap
        h, w = q_img.shape[:2]
        gap = 40
        composite = np.zeros((h, 2 * w + gap), dtype=np.float32)
        composite[:, :w] = q_img
        composite[:, w + gap:] = c_img

        ax.imshow(composite, cmap="gray", vmin=0.0, vmax=1.0, extent=[0, 2 * w + gap, h, 0])

        # Draw inlier correspondence lines
        for corr in r.inlier_correspondences[:25]:  # Limit to 25 lines for visual clarity
            sx, sy = corr["src_pt"]
            rx, ry = corr["ref_pt"]
            ax.plot([sx, rx + w + gap], [sy, ry], color="#00ffcc", alpha=0.6, linewidth=1.2)
            ax.scatter([sx], [sy], color="#00ffff", s=16, edgecolors="none", zorder=3)
            ax.scatter([rx + w + gap], [ry], color="#ff00ea", s=16, edgecolors="none", zorder=3)

        # Labels
        badge_color = "#00e676" if r.accepted else "#ff1744"
        badge_text = f"✓ {r.decision}" if r.accepted else f"✗ {r.decision}"
        
        info_text = (
            f"Query: {r.query_patch_id} ({r.query_sensor}) | Cand: {r.candidate_patch_id} ({r.candidate_sensor})\n"
            f"AI Sim: {r.ai_similarity_score:.2f} | Inliers: {r.inlier_count}/{r.tentative_match_count} ({r.inlier_ratio*100:.0f}%) | "
            f"RMSE: {r.rmse:.2f} px | Conf: {r.verification_confidence:.2f}"
        )
        if not r.accepted and r.rejection_reasons:
            info_text += f"\nRejection Reason: {r.rejection_reasons[0]['code']} ({r.rejection_reasons[0]['message'][:60]}...)"

        ax.text(
            10, 18, badge_text,
            fontsize=11, fontweight="bold", color="white",
            bbox=dict(boxstyle="round,pad=0.3", facecolor=badge_color, edgecolor="none", alpha=0.9),
        )
        ax.text(
            w // 2, h - 8, f"Query ({r.query_sensor})",
            color="#a0aec0", fontsize=9, ha="center",
            bbox=dict(boxstyle="square,pad=0.2", facecolor="#0e131f", alpha=0.7)
        )
        ax.text(
            w + gap + w // 2, h - 8, f"Candidate ({r.candidate_sensor})",
            color="#a0aec0", fontsize=9, ha="center",
            bbox=dict(boxstyle="square,pad=0.2", facecolor="#0e131f", alpha=0.7)
        )
        ax.set_title(info_text, color="#e2e8f0", fontsize=9, pad=8, loc="left")
        ax.axis("off")

    plt.tight_layout()
    plt.savefig(out, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    return out


def plot_inlier_ratio_vs_confidence(
    results: List[VerifiedCandidateMatch],
    output_path: Union[str, Path] = "outputs/poc6/inlier_ratio_vs_confidence.png",
) -> Path:
    """Scatter plot of Inlier Ratio vs Verification Confidence, colored by decision."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 6), facecolor="#0e131f")
    ax.set_facecolor("#151d2f")

    acc_x = [r.inlier_ratio for r in results if r.accepted]
    acc_y = [r.verification_confidence for r in results if r.accepted]
    rej_x = [r.inlier_ratio for r in results if not r.accepted]
    rej_y = [r.verification_confidence for r in results if not r.accepted]

    if rej_x:
        ax.scatter(rej_x, rej_y, c="#ff3366", s=60, alpha=0.7, edgecolors="white", linewidths=0.5, label=f"REJECTED (n={len(rej_x)})")
    if acc_x:
        ax.scatter(acc_x, acc_y, c="#00ffaa", s=80, alpha=0.9, edgecolors="white", linewidths=0.8, marker="D", label=f"ACCEPTED (n={len(acc_x)})")

    # Guidelines
    ax.axvline(0.35, color="#f59e0b", linestyle="--", linewidth=1.2, alpha=0.8, label="Min Inlier Ratio (0.35)")
    ax.axhline(0.50, color="#60a5fa", linestyle="--", linewidth=1.2, alpha=0.8, label="Min Confidence (0.50)")

    ax.set_xlabel("Geometric Inlier Ratio (Inliers / Tentative Matches)", color="#e2e8f0", fontsize=11)
    ax.set_ylabel("Final Verification Confidence Score", color="#e2e8f0", fontsize=11)
    ax.set_title("POC-6: Inlier Ratio vs Verification Confidence Separation", color="#ffffff", fontsize=13, fontweight="bold", pad=12)
    ax.grid(True, linestyle=":", color="#2d3748", alpha=0.7)
    ax.tick_params(colors="#a0aec0")
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)

    legend = ax.legend(facecolor="#1a202c", edgecolor="#4a5568", fontsize=9, loc="lower right")
    for text in legend.get_texts():
        text.set_color("#e2e8f0")

    plt.tight_layout()
    plt.savefig(out, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    return out


def plot_spatial_distribution_inliers(
    results: List[VerifiedCandidateMatch],
    output_path: Union[str, Path] = "outputs/poc6/spatial_distribution_inliers.png",
) -> Path:
    """Visualizes 4x4 spatial grid occupancy and inlier point spread for sample matches."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(10, 5), facecolor="#0e131f")
    
    # 1. Accepted sample with good spatial spread
    acc_samples = [r for r in results if r.accepted and len(r.inlier_correspondences) >= 6]
    rej_samples = [r for r in results if not r.accepted and len(r.inlier_correspondences) >= 3]

    r_good = acc_samples[0] if acc_samples else results[0]
    r_poor = rej_samples[0] if rej_samples else results[-1]

    for ax, r, title, badge_color in [
        (axes[0], r_good, f"Good Spatial Spread: {r_good.decision}", "#00e676" if r_good.accepted else "#ff1744"),
        (axes[1], r_poor, f"Poor / Clustered Spread: {r_poor.decision}", "#00e676" if r_poor.accepted else "#ff1744"),
    ]:
        ax.set_facecolor("#151d2f")
        ax.set_xlim(0, 128)
        ax.set_ylim(128, 0)

        # Draw 4x4 grid lines
        for g in range(1, 4):
            coord = g * 32
            ax.axvline(coord, color="#2d3748", linestyle="--", linewidth=1.0)
            ax.axhline(coord, color="#2d3748", linestyle="--", linewidth=1.0)

        pts = np.array([c["src_pt"] for c in r.inlier_correspondences]) if r.inlier_correspondences else np.empty((0, 2))
        if len(pts) > 0:
            ax.scatter(pts[:, 0], pts[:, 1], c="#00ffff", s=50, edgecolors="white", linewidths=0.8, zorder=3)
            # Bounding box
            x0, x1 = np.min(pts[:, 0]), np.max(pts[:, 0])
            y0, y1 = np.min(pts[:, 1]), np.max(pts[:, 1])
            rect = patches.Rectangle(
                (x0, y0), x1 - x0, y1 - y0,
                linewidth=1.5, edgecolor="#f59e0b", facecolor="#f59e0b", alpha=0.2, zorder=2
            )
            ax.add_patch(rect)

        ax.set_title(
            f"{title}\nInliers: {r.inlier_count} | Spread Score: {r.spatial_distribution_score:.2f} ({r.spatial_distribution_status})",
            color="#e2e8f0", fontsize=10, pad=8
        )
        ax.set_xlabel("Patch X (px)", color="#a0aec0", fontsize=9)
        ax.set_ylabel("Patch Y (px)", color="#a0aec0", fontsize=9)
        ax.tick_params(colors="#a0aec0")

    plt.suptitle("POC-6: Spatial Distribution & 4x4 Grid Occupancy of Geometric Inliers", color="#ffffff", fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(out, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    return out


def plot_confidence_score_breakdown(
    results: List[VerifiedCandidateMatch],
    output_path: Union[str, Path] = "outputs/poc6/confidence_score_breakdown.png",
) -> Path:
    """Horizontal stacked bar chart showing the multi-signal breakdown across accepted and rejected candidates."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 6), facecolor="#0e131f")
    ax.set_facecolor("#151d2f")

    # Choose up to 8 illustrative candidates
    selected = results[:8]
    labels = [f"#{i+1} {r.query_patch_id[:6]}.. vs {r.candidate_patch_id[:6]}..\n({r.decision})" for i, r in enumerate(selected)]
    y_pos = np.arange(len(selected))

    # Signal components
    s_ai = [r.confidence_breakdown.ai_match_score * 0.10 for r in selected]
    s_inl = [r.confidence_breakdown.inlier_score * 0.20 for r in selected]
    s_ratio = [r.confidence_breakdown.inlier_ratio_score * 0.20 for r in selected]
    s_rmse = [r.confidence_breakdown.rmse_score * 0.15 for r in selected]
    s_geo = [r.confidence_breakdown.geographic_overlap_score * 0.15 for r in selected]
    s_dist = [r.confidence_breakdown.spatial_distribution_score * 0.10 for r in selected]
    s_stab = [r.confidence_breakdown.transformation_stability_score * 0.05 for r in selected]
    s_sensor = [r.confidence_breakdown.sensor_compatibility_score * 0.05 for r in selected]

    colors = ["#3b82f6", "#10b981", "#06b6d4", "#8b5cf6", "#f59e0b", "#ec4899", "#6366f1", "#14b8a6"]
    component_names = [
        "AI Match (10%)",
        "Inlier Count (20%)",
        "Inlier Ratio (20%)",
        "RMSE (15%)",
        "Geo Overlap (15%)",
        "Spatial Dist (10%)",
        "Stability (5%)",
        "Sensor Compat (5%)"
    ]

    bottoms = np.zeros(len(selected))
    for data, color, name in zip([s_ai, s_inl, s_ratio, s_rmse, s_geo, s_dist, s_stab, s_sensor], colors, component_names):
        ax.barh(y_pos, data, left=bottoms, color=color, alpha=0.85, edgecolor="#0e131f", height=0.6, label=name)
        bottoms += np.array(data)

    # Acceptance threshold line
    ax.axvline(0.50, color="#ffffff", linestyle="--", linewidth=1.5, label="Acceptance Threshold (0.50)")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, color="#e2e8f0", fontsize=8)
    ax.set_xlabel("Weighted Verification Confidence Contribution", color="#e2e8f0", fontsize=10)
    ax.set_title("POC-6: Transparent 8-Signal Verification Confidence Breakdown", color="#ffffff", fontsize=12, fontweight="bold", pad=12)
    ax.set_xlim(0.0, 1.05)
    ax.grid(True, linestyle=":", color="#2d3748", alpha=0.5, axis="x")
    ax.tick_params(colors="#a0aec0")
    ax.invert_yaxis()

    legend = ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", facecolor="#1a202c", edgecolor="#4a5568", fontsize=8)
    for text in legend.get_texts():
        text.set_color("#e2e8f0")

    plt.tight_layout()
    plt.savefig(out, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    return out


def plot_accepted_vs_rejected_scatter(
    results: List[VerifiedCandidateMatch],
    output_path: Union[str, Path] = "outputs/poc6/accepted_vs_rejected_scatter.png",
) -> Path:
    """AI Similarity vs Verification Confidence scatter showing rejection of high-AI false positives."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 6), facecolor="#0e131f")
    ax.set_facecolor("#151d2f")

    # Separate candidates
    false_positives = [r for r in results if not r.accepted and r.ai_similarity_score >= 0.70]
    true_positives = [r for r in results if r.accepted]
    true_negatives = [r for r in results if not r.accepted and r.ai_similarity_score < 0.70]

    if true_negatives:
        ax.scatter(
            [r.ai_similarity_score for r in true_negatives],
            [r.verification_confidence for r in true_negatives],
            c="#64748b", s=50, alpha=0.7, edgecolors="white", linewidths=0.5, label=f"Low AI / Rejected (n={len(true_negatives)})"
        )
    if false_positives:
        ax.scatter(
            [r.ai_similarity_score for r in false_positives],
            [r.verification_confidence for r in false_positives],
            c="#ff1744", s=90, alpha=0.9, edgecolors="white", linewidths=1.0, marker="X",
            label=f"High AI False Positives (REJECTED by Geometry) (n={len(false_positives)})"
        )
    if true_positives:
        ax.scatter(
            [r.ai_similarity_score for r in true_positives],
            [r.verification_confidence for r in true_positives],
            c="#00e676", s=90, alpha=0.9, edgecolors="white", linewidths=1.0, marker="o",
            label=f"Geometrically Verified ACCEPTED (n={len(true_positives)})"
        )

    # Shaded quadrant for false positives rejected by POC-6
    ax.axvspan(0.70, 1.0, ymin=0.0, ymax=0.50, color="#ff1744", alpha=0.08)
    ax.text(
        0.85, 0.25, "CRITICAL XAI ZONE:\nHigh AI Similarity,\nZero Physical Geometry\n(Safely Rejected)",
        color="#ff80ab", fontsize=9, ha="center", va="center", style="italic",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#1e1020", edgecolor="#ff1744", alpha=0.8)
    )

    ax.axhline(0.50, color="#00e676", linestyle="--", linewidth=1.2, alpha=0.8, label="Acceptance Confidence Threshold")
    ax.axvline(0.70, color="#f59e0b", linestyle=":", linewidth=1.2, alpha=0.8, label="High AI Similarity Threshold")

    ax.set_xlabel("AI Multimodal Cosine Similarity (POC-5)", color="#e2e8f0", fontsize=11)
    ax.set_ylabel("Geometric Verification Confidence (POC-6)", color="#e2e8f0", fontsize=11)
    ax.set_title("POC-6: AI Similarity vs Geometric Evidence Validation", color="#ffffff", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, linestyle=":", color="#2d3748", alpha=0.7)
    ax.tick_params(colors="#a0aec0")

    legend = ax.legend(facecolor="#1a202c", edgecolor="#4a5568", fontsize=8.5, loc="upper left")
    for text in legend.get_texts():
        text.set_color("#e2e8f0")

    plt.tight_layout()
    plt.savefig(out, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    return out


def plot_xai_rejection_reasons_breakdown(
    results: List[VerifiedCandidateMatch],
    output_path: Union[str, Path] = "outputs/poc6/xai_rejection_reasons_breakdown.png",
) -> Path:
    """Bar chart showing the frequency distribution of Explainable AI rejection codes."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    code_counts: Dict[str, int] = {}
    for r in results:
        if not r.accepted:
            for rej in r.rejection_reasons:
                c = rej["code"]
                code_counts[c] = code_counts.get(c, 0) + 1

    if not code_counts:
        code_counts = {"NO_FAILURES": 0}

    sorted_codes = sorted(code_counts.items(), key=lambda x: x[1], reverse=True)
    labels = [k for k, _ in sorted_codes]
    counts = [v for _, v in sorted_codes]

    fig, ax = plt.subplots(figsize=(9, 5), facecolor="#0e131f")
    ax.set_facecolor("#151d2f")

    bars = ax.bar(labels, counts, color="#ff4081", alpha=0.85, edgecolor="#ffffff", linewidth=0.5, width=0.55)

    for bar in bars:
        h = bar.get_height()
        ax.annotate(
            f"{int(h)}",
            xy=(bar.get_x() + bar.get_width() / 2, h),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center", va="bottom",
            color="#ffffff", fontsize=9, fontweight="bold",
        )

    ax.set_ylabel("Diagnostic Failure Frequency", color="#e2e8f0", fontsize=11)
    ax.set_title("POC-6: Explainable AI (XAI) Diagnostic Rejection Code Distribution", color="#ffffff", fontsize=12, fontweight="bold", pad=12)
    ax.tick_params(colors="#a0aec0", axis="both")
    plt.xticks(rotation=28, ha="right", color="#e2e8f0", fontsize=8.5)
    ax.grid(True, linestyle=":", color="#2d3748", alpha=0.7, axis="y")

    plt.tight_layout()
    plt.savefig(out, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    return out


def generate_all_poc6_visualizations(
    results: List[VerifiedCandidateMatch],
    image_registry: Dict[str, np.ndarray],
    output_dir: Union[str, Path] = "outputs/poc6",
) -> Dict[str, Path]:
    """Generates all 6 required diagnostic visualizations in output_dir."""
    d = Path(output_dir)
    d.mkdir(parents=True, exist_ok=True)

    fig1 = plot_geometric_verification_gallery(results, image_registry, d / "geometric_verification_gallery.png")
    fig2 = plot_inlier_ratio_vs_confidence(results, d / "inlier_ratio_vs_confidence.png")
    fig3 = plot_spatial_distribution_inliers(results, d / "spatial_distribution_inliers.png")
    fig4 = plot_confidence_score_breakdown(results, d / "confidence_score_breakdown.png")
    fig5 = plot_accepted_vs_rejected_scatter(results, d / "accepted_vs_rejected_scatter.png")
    fig6 = plot_xai_rejection_reasons_breakdown(results, d / "xai_rejection_reasons_breakdown.png")

    return {
        "gallery": fig1,
        "inlier_ratio_vs_confidence": fig2,
        "spatial_distribution": fig3,
        "confidence_breakdown": fig4,
        "accepted_vs_rejected_scatter": fig5,
        "xai_rejection_breakdown": fig6,
    }
