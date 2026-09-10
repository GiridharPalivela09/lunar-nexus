"""NEXUS-LUNAR POC-7: Spatial Intelligence Visualizations.

Generates 8 high-fidelity diagnostic publication figures:
1. knowledge_graph_overview.png: Force-directed / circular graph layout showing entities & relations
2. terrain_intelligence_map.png: Elevation surface map across patch regions
3. slope_analysis_map.png: Slope gradients with operational category boundaries
4. illumination_shadow_map.png: Multi-patch illumination and shadow fraction overlay
5. hazard_intelligence_map.png: Spatial distribution of terrain, slope, and shadow hazards
6. resource_indicator_map.png: IIRS mineralogical/volatile spectral indicator heatmap
7. candidate_site_suitability_map.png: Composite suitability ranking of candidate sites
8. candidate_site_explanation.png: Multi-factor radar scorecard and rationale checklist
"""

from __future__ import annotations
import math
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive headless backend
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    HAS_MATPLOTLIB = True
except ImportError:
    matplotlib = None
    plt = None
    mpatches = None
    HAS_MATPLOTLIB = False

from packages.data_pipeline.poc7_knowledge_graph import SpatialKnowledgeGraph
from packages.data_pipeline.poc7_models import (
    NodeType,
    RelationType,
    CandidateSite,
    TerrainMetrics,
    IlluminationMetrics,
    ResourceIndicator,
    HazardIndicator,
)


class POC7Visualizer:
    """Renders diagnostic spatial intelligence maps and graph diagrams."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # Apply dark aesthetic theme consistent with NEXUS-LUNAR
        plt.style.use("dark_background")
        self.accent_colors = {
            "cyan": "#00f2fe",
            "purple": "#a29bfe",
            "green": "#00b894",
            "amber": "#fdcb6e",
            "red": "#ff7675",
            "card_bg": "#1e2433",
        }

    def render_knowledge_graph_overview(
        self,
        graph: SpatialKnowledgeGraph,
        filename: str = "knowledge_graph_overview.png",
    ) -> Path:
        """Render circular/clustered layout of nodes and edges in the Spatial Knowledge Graph."""
        fig, ax = plt.subplots(figsize=(12, 10), dpi=150)
        ax.set_facecolor("#0b0e14")
        fig.patch.set_facecolor("#0b0e14")

        # Color mapping for node types
        type_palette = {
            "Lunar Region": "#6c5ce7",
            "Image": "#0984e3",
            "Sensor": "#00cec9",
            "Observation": "#74b9ff",
            "Terrain Patch": "#00f2fe",
            "Crater": "#e17055",
            "Slope Region": "#fdcb6e",
            "Hazard": "#d63031",
            "Illumination State": "#ffeaa7",
            "Spectral Observation": "#fd79a8",
            "Candidate Site": "#00b894",
            "Habitat Component": "#55efc4",
        }

        # Position nodes in clustered rings based on type
        all_nodes = list(graph.nodes.values())
        total_nodes = len(all_nodes)
        coords = {}

        # Center: Lunar Region
        # Inner ring: Images, Sensors, Observations
        # Middle ring: Terrain Patches, Craters, Hazards
        # Outer ring: Illumination, Spectral, Candidate Sites
        for i, node in enumerate(all_nodes):
            nt_str = node.type.value if isinstance(node.type, NodeType) else str(node.type)
            if nt_str == "Lunar Region":
                coords[node.id] = (0.0, 0.0)
            elif nt_str in ("Sensor", "Image", "Observation"):
                angle = 2.0 * math.pi * (i / max(1, total_nodes))
                coords[node.id] = (0.35 * math.cos(angle), 0.35 * math.sin(angle))
            elif nt_str in ("Terrain Patch", "Crater", "Slope Region"):
                angle = 2.0 * math.pi * (i / max(1, total_nodes))
                coords[node.id] = (0.65 * math.cos(angle), 0.65 * math.sin(angle))
            else:
                angle = 2.0 * math.pi * (i / max(1, total_nodes))
                coords[node.id] = (0.90 * math.cos(angle), 0.90 * math.sin(angle))

        # Draw edges
        for edge in graph.edges:
            p1 = coords.get(edge.source)
            p2 = coords.get(edge.target)
            if p1 and p2:
                rel = edge.relationship.value if isinstance(edge.relationship, RelationType) else str(edge.relationship)
                color = "#4facfe" if rel == "CORRESPONDS_TO" else "#2d3436"
                alpha = 0.85 if rel == "CORRESPONDS_TO" else 0.35
                lw = 2.0 if rel == "CORRESPONDS_TO" else 0.7
                ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=color, alpha=alpha, lw=lw, zorder=1)

        # Draw nodes
        for node in all_nodes:
            pt = coords[node.id]
            nt_str = node.type.value if isinstance(node.type, NodeType) else str(node.type)
            col = type_palette.get(nt_str, "#dfe6e9")
            size = 140 if nt_str in ("Lunar Region", "Candidate Site", "Terrain Patch") else 70
            ax.scatter(pt[0], pt[1], s=size, color=col, edgecolors="white", linewidths=1.0, zorder=2)
            # Label prominent nodes
            if nt_str in ("Lunar Region", "Candidate Site") or "PATCH" in node.id:
                ax.text(pt[0] + 0.02, pt[1] + 0.02, node.id, fontsize=7, color="#f1f2f6", zorder=3)

        # Legend
        legend_handles = [
            mpatches.Patch(color=col, label=label)
            for label, col in type_palette.items()
            if any((n.type.value if isinstance(n.type, NodeType) else str(n.type)) == label for n in all_nodes)
        ]
        ax.legend(handles=legend_handles, loc="upper right", fontsize=8, framealpha=0.6, facecolor="#1e2433")

        ax.set_title(
            f"NEXUS-LUNAR Spatial Knowledge Graph ({len(graph.nodes)} Nodes, {len(graph.edges)} Edges)\n"
            f"Cross-Sensor Registered Observations & Provenance Connections",
            fontsize=13, fontweight="bold", color="#f5f6fa", pad=12
        )
        ax.axis("off")
        out_file = self.output_dir / filename
        plt.tight_layout()
        plt.savefig(out_file, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return out_file

    def render_terrain_intelligence_map(
        self,
        terrain_list: List[TerrainMetrics],
        filename: str = "terrain_intelligence_map.png",
    ) -> Path:
        """Render multi-patch elevation and topography map."""
        fig, axes = plt.subplots(1, 2, figsize=(14, 6), dpi=150)
        fig.patch.set_facecolor("#0b0e14")

        # Subplot 1: Elevation Profile Bar Chart
        ax1 = axes[0]
        ax1.set_facecolor("#121620")
        patch_ids = [t.patch_id for t in terrain_list]
        elev_means = [t.elevation_mean_m for t in terrain_list]
        elev_mins = [t.elevation_min_m for t in terrain_list]
        elev_maxs = [t.elevation_max_m for t in terrain_list]
        errs = [[m - mi for m, mi in zip(elev_means, elev_mins)], [ma - m for m, ma in zip(elev_means, elev_maxs)]]

        bars = ax1.bar(patch_ids, elev_means, yerr=errs, capsize=5, color="#00cec9", alpha=0.85, edgecolor="white")
        ax1.set_title("Terrain Elevation Profile (Mean, Min, Max in Meters)", fontsize=11, fontweight="bold", color="#f1f2f6")
        ax1.set_ylabel("Elevation (m)", color="#dfe6e9")
        ax1.tick_params(colors="#b2bec3")
        plt.setp(ax1.get_xticklabels(), rotation=30, ha="right")

        # Subplot 2: Roughness & Topographic Variance
        ax2 = axes[1]
        ax2.set_facecolor("#121620")
        roughness = [t.roughness_score for t in terrain_list]
        slopes = [t.slope_degrees for t in terrain_list]

        scatter = ax2.scatter(slopes, roughness, s=160, c=slopes, cmap="coolwarm", edgecolors="white", linewidths=1.5)
        for i, t in enumerate(terrain_list):
            ax2.annotate(t.patch_id, (slopes[i] + 0.1, roughness[i] + 0.05), fontsize=8, color="#dfe6e9")

        ax2.set_title("Slope vs Local Elevation Roughness (Std Dev)", fontsize=11, fontweight="bold", color="#f1f2f6")
        ax2.set_xlabel("Mean Slope (°)", color="#dfe6e9")
        ax2.set_ylabel("Roughness Score (m std dev)", color="#dfe6e9")
        ax2.tick_params(colors="#b2bec3")
        cbar = plt.colorbar(scatter, ax=ax2)
        cbar.set_label("Slope Intensity", color="#dfe6e9")
        cbar.ax.tick_params(colors="#b2bec3")

        fig.suptitle("NEXUS-LUNAR: Topographic & Terrain Intelligence [DEM Analysis]", fontsize=13, fontweight="bold", color="#00f2fe", y=0.98)
        out_file = self.output_dir / filename
        plt.tight_layout()
        plt.savefig(out_file, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return out_file

    def render_slope_analysis_map(
        self,
        terrain_list: List[TerrainMetrics],
        filename: str = "slope_analysis_map.png",
    ) -> Path:
        """Render slope analysis categorized by operational safety thresholds."""
        fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
        ax.set_facecolor("#121620")
        fig.patch.set_facecolor("#0b0e14")

        patch_ids = [t.patch_id for t in terrain_list]
        slopes = [t.slope_degrees for t in terrain_list]
        cat_colors = {
            "LOW": "#00b894",
            "MODERATE": "#fdcb6e",
            "HIGH": "#e17055",
            "VERY_HIGH": "#d63031",
        }
        bar_colors = [cat_colors.get(t.slope_category.value if hasattr(t.slope_category, "value") else str(t.slope_category), "#00b894") for t in terrain_list]

        bars = ax.barh(patch_ids, slopes, color=bar_colors, edgecolor="white", alpha=0.9, height=0.55)

        # Threshold guideline lines
        ax.axvline(5.0, color="#00b894", linestyle="--", alpha=0.7, label="Low Threshold (< 5°)")
        ax.axvline(12.0, color="#fdcb6e", linestyle="--", alpha=0.7, label="Moderate Threshold (< 12°)")
        ax.axvline(20.0, color="#d63031", linestyle="--", alpha=0.7, label="High / Danger Threshold (> 20°)")

        for bar, slope in zip(bars, slopes):
            ax.text(slope + 0.3, bar.get_y() + bar.get_height() / 2.0, f"{slope:.1f}°", va="center", color="white", fontsize=9, fontweight="bold")

        ax.set_title("NEXUS-LUNAR: Slope Gradient & Operational Mobility Categories", fontsize=12, fontweight="bold", color="#f1f2f6", pad=12)
        ax.set_xlabel("Slope (Degrees)", color="#dfe6e9")
        ax.tick_params(colors="#b2bec3")
        ax.legend(loc="lower right", facecolor="#1e2433", edgecolor="#2d3436", fontsize=9)

        out_file = self.output_dir / filename
        plt.tight_layout()
        plt.savefig(out_file, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return out_file

    def render_illumination_shadow_map(
        self,
        illum_list: List[IlluminationMetrics],
        filename: str = "illumination_shadow_map.png",
    ) -> Path:
        """Render illumination and shadow fraction analysis."""
        fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
        ax.set_facecolor("#121620")
        fig.patch.set_facecolor("#0b0e14")

        x = np.arange(len(illum_list))
        width = 0.35
        patch_ids = [i.patch_id for i in illum_list]
        means = [i.illumination_mean for i in illum_list]
        shadows = [i.shadow_fraction for i in illum_list]

        ax.bar(x - width/2, means, width, label="Mean Illumination Flux", color="#ffeaa7", edgecolor="white", alpha=0.9)
        ax.bar(x + width/2, shadows, width, label="Shadow Fraction (Coverage)", color="#6c5ce7", edgecolor="white", alpha=0.8)

        ax.set_xticks(x)
        ax.set_xticklabels(patch_ids, rotation=25, ha="right", color="#dfe6e9")
        ax.set_ylabel("Fraction (0.0 to 1.0)", color="#dfe6e9")
        ax.tick_params(colors="#b2bec3")
        ax.set_title("NEXUS-LUNAR: Surface Illumination & Shadow Regime Analysis", fontsize=12, fontweight="bold", color="#f1f2f6", pad=12)
        ax.legend(loc="upper right", facecolor="#1e2433", edgecolor="#2d3436")

        out_file = self.output_dir / filename
        plt.tight_layout()
        plt.savefig(out_file, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return out_file

    def render_hazard_map(
        self,
        hazards: List[HazardIndicator],
        filename: str = "hazard_intelligence_map.png",
    ) -> Path:
        """Render spatial hazard severity breakdown."""
        fig, axes = plt.subplots(1, 2, figsize=(13, 5), dpi=150)
        fig.patch.set_facecolor("#0b0e14")

        # Subplot 1: Severity Pie Chart
        ax1 = axes[0]
        ax1.set_facecolor("#121620")
        sev_counts = {"CRITICAL": 0, "HIGH": 0, "MODERATE": 0, "LOW": 0}
        for h in hazards:
            sev_str = h.severity.value if hasattr(h.severity, "value") else str(h.severity)
            sev_counts[sev_str] = sev_counts.get(sev_str, 0) + 1

        active_sevs = {k: v for k, v in sev_counts.items() if v > 0}
        colors = {"CRITICAL": "#d63031", "HIGH": "#e17055", "MODERATE": "#fdcb6e", "LOW": "#00b894"}
        pie_cols = [colors.get(k, "#dfe6e9") for k in active_sevs.keys()]

        if active_sevs:
            ax1.pie(active_sevs.values(), labels=active_sevs.keys(), autopct="%1.1f%%", colors=pie_cols,
                    textprops={"color": "white", "fontsize": 9, "fontweight": "bold"}, startangle=140)
        ax1.set_title("Hazard Severity Distribution", fontsize=11, fontweight="bold", color="#f1f2f6")

        # Subplot 2: Hazard Types Breakdown
        ax2 = axes[1]
        ax2.set_facecolor("#121620")
        type_counts = {}
        for h in hazards:
            t_str = h.hazard_type.value if hasattr(h.hazard_type, "value") else str(h.hazard_type)
            type_counts[t_str] = type_counts.get(t_str, 0) + 1

        if type_counts:
            ax2.barh(list(type_counts.keys()), list(type_counts.values()), color="#ff7675", edgecolor="white")
        ax2.set_title("Detected Hazard Types", fontsize=11, fontweight="bold", color="#f1f2f6")
        ax2.set_xlabel("Count", color="#dfe6e9")
        ax2.tick_params(colors="#b2bec3")

        fig.suptitle("NEXUS-LUNAR: Spatial Hazard Intelligence", fontsize=13, fontweight="bold", color="#ff7675", y=0.98)
        out_file = self.output_dir / filename
        plt.tight_layout()
        plt.savefig(out_file, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return out_file

    def render_resource_indicator_map(
        self,
        resources: List[ResourceIndicator],
        filename: str = "resource_indicator_map.png",
    ) -> Path:
        """Render mineralogical and volatile indicator scores."""
        fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
        ax.set_facecolor("#121620")
        fig.patch.set_facecolor("#0b0e14")

        patch_ids = [r.associated_patch_id for r in resources]
        scores = [r.indicator_score for r in resources]

        bars = ax.bar(patch_ids, scores, color="#fd79a8", edgecolor="white", alpha=0.85, width=0.5)
        for b, s in zip(bars, scores):
            ax.text(b.get_x() + b.get_width()/2.0, s + 0.02, f"{s:.2f}", ha="center", color="white", fontsize=9, fontweight="bold")

        ax.set_ylim(0, 1.0)
        ax.set_ylabel("Spectral Indicator Score (0-1)", color="#dfe6e9")
        ax.tick_params(colors="#b2bec3")
        plt.setp(ax.get_xticklabels(), rotation=25, ha="right")
        ax.set_title("NEXUS-LUNAR: Chandrayaan-2 IIRS Mineralogical & Spectral Indicators\n"
                     "(Notice: Uncalibrated absorption band proxy; NOT confirmed mineable deposits)",
                     fontsize=11, fontweight="bold", color="#fd79a8", pad=12)

        out_file = self.output_dir / filename
        plt.tight_layout()
        plt.savefig(out_file, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return out_file

    def render_candidate_site_suitability_map(
        self,
        sites: List[CandidateSite],
        filename: str = "candidate_site_suitability_map.png",
    ) -> Path:
        """Render ranked candidate site suitability scores."""
        fig, ax = plt.subplots(figsize=(11, 6), dpi=150)
        ax.set_facecolor("#121620")
        fig.patch.set_facecolor("#0b0e14")

        site_ids = [s.site_id for s in sites]
        scores = [s.overall_suitability_score for s in sites]
        colors = ["#00b894" if sc >= 0.70 else "#fdcb6e" if sc >= 0.45 else "#d63031" for sc in scores]

        bars = ax.barh(site_ids, scores, color=colors, edgecolor="white", alpha=0.9, height=0.5)
        for b, sc in zip(bars, scores):
            ax.text(sc + 0.02, b.get_y() + b.get_height()/2.0, f"{sc:.3f}", va="center", color="white", fontsize=10, fontweight="bold")

        ax.axvline(0.70, color="#00b894", linestyle="--", alpha=0.8, label="Favorable Threshold (>= 0.70)")
        ax.axvline(0.45, color="#fdcb6e", linestyle="--", alpha=0.8, label="Marginal Threshold (>= 0.45)")

        ax.set_xlim(0, 1.1)
        ax.set_xlabel("Overall Spatial Suitability Score", color="#dfe6e9")
        ax.set_title("NEXUS-LUNAR: Candidate Site Spatial Suitability Ranking", fontsize=12, fontweight="bold", color="#00f2fe", pad=12)
        ax.tick_params(colors="#b2bec3")
        ax.legend(loc="lower right", facecolor="#1e2433", edgecolor="#2d3436")

        out_file = self.output_dir / filename
        plt.tight_layout()
        plt.savefig(out_file, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return out_file

    def render_candidate_site_explanation(
        self,
        leading_site: CandidateSite,
        filename: str = "candidate_site_explanation.png",
    ) -> Path:
        """Render radar diagram and factor scorecard for the top candidate site."""
        fig = plt.figure(figsize=(12, 6), dpi=150)
        fig.patch.set_facecolor("#0b0e14")

        # Left: Radar Chart
        categories = ["Terrain", "Illumination", "Resource", "Data Quality", "Safety (1 - Hazard)"]
        values = [
            leading_site.terrain_score,
            leading_site.illumination_score,
            leading_site.resource_indicator_score,
            leading_site.spatial_data_quality_score,
            max(0.0, 1.0 - leading_site.hazard_penalty),
        ]
        values += values[:1]  # Complete loop
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        angles += angles[:1]

        ax1 = fig.add_subplot(121, polar=True)
        ax1.set_facecolor("#121620")
        ax1.plot(angles, values, color="#00f2fe", linewidth=2.5, linestyle="solid")
        ax1.fill(angles, values, color="#00f2fe", alpha=0.35)
        ax1.set_xticks(angles[:-1])
        ax1.set_xticklabels(categories, color="#dfe6e9", fontsize=9, fontweight="bold")
        ax1.tick_params(colors="#b2bec3")
        ax1.set_title(f"Multi-Factor Radar: {leading_site.site_id}\nOverall: {leading_site.overall_suitability_score:.3f}",
                      fontsize=11, fontweight="bold", color="#00f2fe", pad=15)

        # Right: Scorecard and Factor Checklist Text
        ax2 = fig.add_subplot(122)
        ax2.set_facecolor("#121620")
        ax2.axis("off")

        expl = leading_site.explanation
        pos_text = "\n".join([f"✓ {p}" for p in (expl.positive_factors if expl else [])])
        neg_text = "\n".join([f"✗ {n}" for n in (expl.negative_factors if expl else [])])

        card_text = (
            f"CANDIDATE SITE EXPLANATION CARD\n"
            f"=========================================\n"
            f"Site ID: {leading_site.site_id} (Patch: {leading_site.patch_id})\n"
            f"Coordinates: Lat {leading_site.coordinates.get('lat', 0):.4f}°, Lon {leading_site.coordinates.get('lon', 0):.4f}°\n"
            f"Suitability Score: {leading_site.overall_suitability_score:.3f} ({leading_site.data_status.value if hasattr(leading_site.data_status, 'value') else leading_site.data_status})\n\n"
            f"POSITIVE FACTORS:\n{pos_text}\n\n"
            f"CONSTRAINING FACTORS / HAZARDS:\n{neg_text if neg_text else 'None'}\n\n"
            f"VERDICT: {expl.summary_verdict if expl else 'EVALUATED'}\n"
        )
        ax2.text(0.05, 0.95, card_text, transform=ax2.transAxes, fontsize=8.5,
                 verticalalignment="top", fontfamily="monospace", color="#f1f2f6")

        out_file = self.output_dir / filename
        plt.tight_layout()
        plt.savefig(out_file, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return out_file
