"""POC-5 Multimodal AI Correspondence Visualization Module.

Generates publication-quality figures:
1. two_tower_architecture.png: Visual schematic of Two-Tower vision + metadata encoder.
2. retrieval_ranking_grid.png: Query OHRC patch next to Top-5 retrieved LROC candidate patches with ground-truth markers.
3. embedding_clusters.png: 2D PCA/t-SNE projection of L2-normalized patch embeddings across sensors.
4. recall_at_k_curve.png: Recall@K benchmark curve comparing learned embeddings against baseline.
5. similarity_distribution.png: Cosine similarity histograms comparing positive vs hard-negative pairs.
"""

import os
from typing import Dict, List, Any, Optional
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches


def plot_architecture_diagram(output_path: str) -> str:
    """Generates a clear schematic diagram of the Two-Tower Architecture."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis('off')

    # Color palette
    c_tower_a = "#2b5c8f"  # Blue for Tower A (Query / OHRC)
    c_tower_b = "#9c413e"  # Red/Auburn for Tower B (Reference / LROC)
    c_meta = "#3c763d"     # Green for metadata
    c_emb = "#5a3791"      # Purple for embedding space

    # Tower A (OHRC/TMC-2 Query)
    ax.add_patch(patches.FancyBboxPatch((0.5, 3.5), 2.2, 1.8, boxstyle="round,pad=0.1", fc="#e8f0fe", ec=c_tower_a, lw=2))
    ax.text(1.6, 4.8, "Query Tower (A)\nChandrayaan-2 OHRC / TMC-2", ha="center", va="center", fontsize=9, fontweight="bold", color=c_tower_a)
    ax.text(1.6, 4.0, "Patch: 128×128 px\nConvNet Backbone (3 Blocks)\nAdaptive Pooling → 64-D", ha="center", va="center", fontsize=8)

    # Tower B (LROC NAC Reference)
    ax.add_patch(patches.FancyBboxPatch((0.5, 0.7), 2.2, 1.8, boxstyle="round,pad=0.1", fc="#fce8e6", ec=c_tower_b, lw=2))
    ax.text(1.6, 2.0, "Reference Tower (B)\nNASA LROC NAC", ha="center", va="center", fontsize=9, fontweight="bold", color=c_tower_b)
    ax.text(1.6, 1.2, "Patch: 128×128 px\nConvNet Backbone (3 Blocks)\nAdaptive Pooling → 64-D", ha="center", va="center", fontsize=8)

    # Metadata Encoders
    ax.add_patch(patches.FancyBboxPatch((3.2, 3.7), 1.8, 1.4, boxstyle="round,pad=0.08", fc="#e6f4ea", ec=c_meta, lw=1.5))
    ax.text(4.1, 4.4, "Metadata MLP A", ha="center", va="center", fontsize=9, fontweight="bold", color=c_meta)
    ax.text(4.1, 4.0, "Incidence, Emission,\nPhase, Resolution → 32-D", ha="center", va="center", fontsize=7.5)

    ax.add_patch(patches.FancyBboxPatch((3.2, 0.9), 1.8, 1.4, boxstyle="round,pad=0.08", fc="#e6f4ea", ec=c_meta, lw=1.5))
    ax.text(4.1, 1.6, "Metadata MLP B", ha="center", va="center", fontsize=9, fontweight="bold", color=c_meta)
    ax.text(4.1, 1.2, "Incidence, Emission,\nPhase, Resolution → 32-D", ha="center", va="center", fontsize=7.5)

    # Shared Joint Projection Head
    ax.add_patch(patches.FancyBboxPatch((5.5, 2.0), 1.8, 2.0, boxstyle="round,pad=0.1", fc="#f3e8fd", ec=c_emb, lw=2))
    ax.text(6.4, 3.3, "Joint Projection Head\n(Linear 96 → 128)", ha="center", va="center", fontsize=9, fontweight="bold", color=c_emb)
    ax.text(6.4, 2.5, "L2 Normalization\n||z||_2 = 1.0\n128-D Unit Sphere", ha="center", va="center", fontsize=8)

    # Metric Objective / Contrastive Loss
    ax.add_patch(patches.FancyBboxPatch((7.8, 2.0), 1.8, 2.0, boxstyle="round,pad=0.1", fc="#fff2cc", ec="#d6b656", lw=2))
    ax.text(8.7, 3.3, "Metric Objective", ha="center", va="center", fontsize=9, fontweight="bold", color="#7f6000")
    ax.text(8.7, 2.5, "Cosine Similarity Loss\nHard Negative Mining\nMargin m = 0.35\nRecall@K Evaluation", ha="center", va="center", fontsize=8)

    # Connecting Arrows
    arrow_props = dict(arrowstyle="->", lw=1.5, color="#333333")
    ax.annotate("", xy=(3.2, 4.4), xytext=(2.7, 4.4), arrowprops=arrow_props)
    ax.annotate("", xy=(3.2, 1.6), xytext=(2.7, 1.6), arrowprops=arrow_props)
    ax.annotate("", xy=(5.5, 3.2), xytext=(5.0, 4.4), arrowprops=arrow_props)
    ax.annotate("", xy=(5.5, 2.8), xytext=(5.0, 1.6), arrowprops=arrow_props)
    ax.annotate("", xy=(7.8, 3.0), xytext=(7.3, 3.0), arrowprops=arrow_props)

    plt.title("NEXUS-LUNAR: POC-5 Multimodal Two-Tower Vision-Metadata Metric Learning Architecture",
              fontsize=11, fontweight="bold", pad=15)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    return output_path


def plot_retrieval_ranking_grid(
    query_patch: np.ndarray,
    query_info: Dict[str, Any],
    top_k_results: List[Dict[str, Any]],
    candidate_patches_dict: Dict[str, np.ndarray],
    output_path: str
) -> str:
    """Renders a grid showing the Query patch alongside the Top-K retrieved candidate patches."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    k = len(top_k_results)
    fig, axes = plt.subplots(1, k + 1, figsize=(3 * (k + 1), 3.5), dpi=300)

    # Query Patch (Leftmost)
    ax_q = axes[0]
    ax_q.imshow(query_patch, cmap='gray')
    ax_q.set_title(f"QUERY: {query_info.get('sensor', 'OHRC')}\n{query_info.get('patch_id', 'Q0')}\nLat: {query_info.get('lat', 0):.3f}° Lon: {query_info.get('lon', 0):.3f}°",
                   fontsize=8, fontweight="bold", color="#1a73e8")
    ax_q.axis('off')
    rect = patches.Rectangle((0, 0), query_patch.shape[1]-1, query_patch.shape[0]-1,
                             linewidth=2.5, edgecolor='#1a73e8', facecolor='none')
    ax_q.add_patch(rect)

    # Candidate Patches (Rank 1 to K)
    for rank_idx, cand_info in enumerate(top_k_results):
        ax_c = axes[rank_idx + 1]
        cid = cand_info['candidate_patch_id']
        c_patch = candidate_patches_dict.get(cid, np.zeros((128, 128), dtype=np.uint8))

        ax_c.imshow(c_patch, cmap='gray')
        is_hit = cand_info.get('is_true_match', False)
        border_color = "#34a853" if is_hit else "#ea4335"
        label_text = "MATCH (TRUE)" if is_hit else "DISTRACTOR"

        ax_c.set_title(
            f"Rank #{cand_info.get('rank', rank_idx+1)}: {cid}\n"
            f"Sim: {cand_info.get('similarity', 0):.3f} | Dist: {cand_info.get('distance_km', 0):.2f}km\n"
            f"[{label_text}]",
            fontsize=8, fontweight="bold", color=border_color
        )
        ax_c.axis('off')
        rect = patches.Rectangle((0, 0), c_patch.shape[1]-1, c_patch.shape[0]-1,
                                 linewidth=2.5, edgecolor=border_color, facecolor='none')
        ax_c.add_patch(rect)

    plt.suptitle("POC-5 Cross-Sensor Patch Retrieval (Query vs Top-K Candidates)", fontsize=11, fontweight="bold", y=0.98)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    return output_path


def plot_embedding_clusters(
    query_embeddings: np.ndarray,
    candidate_embeddings: np.ndarray,
    matched_indices: List[int],
    output_path: str
) -> str:
    """Visualizes the 128-D embedding space projected onto 2D using SVD/PCA."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    all_embs = np.vstack([query_embeddings, candidate_embeddings])
    
    # 2-Component PCA via SVD
    centered = all_embs - np.mean(all_embs, axis=0)
    u, s, vt = np.linalg.svd(centered, full_matrices=False)
    coords_2d = np.dot(centered, vt[:2].T)

    n_q = len(query_embeddings)
    coords_q = coords_2d[:n_q]
    coords_c = coords_2d[n_q:]

    fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
    
    # Plot candidate points (LROC NAC)
    ax.scatter(coords_c[:, 0], coords_c[:, 1], c='#5f6368', alpha=0.6, s=35, label="LROC NAC Reference Footprints")
    
    # Plot query points (OHRC)
    ax.scatter(coords_q[:, 0], coords_q[:, 1], c='#1a73e8', marker='^', s=60, edgecolors='black', label="OHRC Queries")

    # Connect matched query-reference pairs with lines
    for q_idx, c_idx in enumerate(matched_indices):
        if c_idx < len(coords_c):
            ax.plot([coords_q[q_idx, 0], coords_c[c_idx, 0]],
                    [coords_q[q_idx, 1], coords_c[c_idx, 1]],
                    'g--', alpha=0.5, lw=1.2)

    ax.set_xlabel("Principal Latent Dimension 1 (PCA)", fontsize=10)
    ax.set_ylabel("Principal Latent Dimension 2 (PCA)", fontsize=10)
    ax.set_title("POC-5 Shared Latent Space Projection (128-D → 2D)\nCo-registered Cross-Sensor Pairs Cluster Closely", fontsize=11, fontweight="bold")
    ax.legend(loc="upper right", frameon=True)
    ax.grid(True, linestyle=":", alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    return output_path


def plot_recall_at_k_curve(metrics: Dict[str, Any], output_path: str) -> str:
    """Plots Recall@1, Recall@5, Recall@10 comparison against baseline."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    ks = [1, 5, 10]
    recalls = [metrics.get('recall_at_1', 0.0) * 100,
               metrics.get('recall_at_5', 0.0) * 100,
               metrics.get('recall_at_10', 0.0) * 100]
    
    # Classical SIFT/ORB baseline from POC-4 benchmarks (~25% R@1, ~48% R@5, ~62% R@10)
    baseline_recalls = [25.0, 48.0, 62.0]

    fig, ax = plt.subplots(figsize=(7, 5), dpi=300)
    ax.plot(ks, recalls, marker='o', lw=2.5, color='#1a73e8', label=f"NEXUS Two-Tower AI (MRR: {metrics.get('mean_reciprocal_rank', 0):.3f})")
    ax.plot(ks, baseline_recalls, marker='s', lw=2.0, linestyle='--', color='#ea4335', label="Classical Keypoint Baseline (SIFT/ORB)")

    for k, r in zip(ks, recalls):
        ax.annotate(f"{r:.1f}%", xy=(k, r), xytext=(k, r + 2.5),
                    ha='center', fontsize=9, fontweight="bold", color='#1a73e8')

    ax.set_xticks(ks)
    ax.set_ylim(0, 105)
    ax.set_xlabel("Top-K Candidates Retained (K)", fontsize=10)
    ax.set_ylabel("Retrieval Accuracy Recall@K (%)", fontsize=10)
    ax.set_title("Cross-Sensor Lunar Patch Retrieval Accuracy (Recall@K)", fontsize=11, fontweight="bold")
    ax.legend(loc="lower right", frameon=True)
    ax.grid(True, linestyle=":", alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    return output_path


def plot_similarity_distribution(
    pos_similarities: List[float],
    neg_similarities: List[float],
    output_path: str
) -> str:
    """Plots cosine similarity histograms of positive vs negative patch pairs."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)

    bins = np.linspace(-0.2, 1.0, 30)
    ax.hist(pos_similarities, bins=bins, alpha=0.7, color='#34a853', label=f"Positive Pairs (N={len(pos_similarities)})", density=True)
    ax.hist(neg_similarities, bins=bins, alpha=0.6, color='#ea4335', label=f"Hard Negative Pairs (N={len(neg_similarities)})", density=True)

    pos_mean = float(np.mean(pos_similarities)) if pos_similarities else 0.0
    neg_mean = float(np.mean(neg_similarities)) if neg_similarities else 0.0
    separation_margin = pos_mean - neg_mean

    ax.axvline(pos_mean, color='#1e8e3e', linestyle='--', lw=2, label=f"Mean Positive: {pos_mean:.3f}")
    ax.axvline(neg_mean, color='#d93025', linestyle='--', lw=2, label=f"Mean Negative: {neg_mean:.3f}")

    ax.set_xlabel("Cosine Similarity", fontsize=10)
    ax.set_ylabel("Probability Density", fontsize=10)
    ax.set_title(f"Learned Latent Space Separation Margin: Δ = {separation_margin:.3f}", fontsize=11, fontweight="bold")
    ax.legend(loc="upper left", frameon=True)
    ax.grid(True, linestyle=":", alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    return output_path
