"""NEXUS-LUNAR: Geospatial & Patch Visualization Generator.

Generates high-resolution publication-quality PNG figures showing:
1. Geographic Footprint Overlap (Source, Reference, Common Intersection)
2. Resolution-Aware Patch Comparison (Native Source vs Native Reference)
"""

from __future__ import annotations
import math
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union, List

import logging
import numpy as np
from PIL import Image
try:
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MplPolygon
    HAS_MATPLOTLIB = True
except ImportError:
    matplotlib = None
    plt = None
    MplPolygon = None
    HAS_MATPLOTLIB = False
from shapely.geometry import Polygon, MultiPolygon

from .footprint_engine import FootprintResult

logger = logging.getLogger("nexus.data.visualization")


def generate_overlap_visualization(
    source_footprint: FootprintResult,
    reference_footprint: FootprintResult,
    intersection_polygon: Optional[Polygon],
    output_path: Union[str, Path],
    source_title: str = "Source Footprint (OHRC)",
    reference_title: str = "Reference Footprint (LROC NAC)",
    overlap_confidence: float = 0.0,
    intersection_area_km2: float = 0.0,
) -> Path:
    """Generates a geographic footprint map showing source, reference, and intersection."""
    if not HAS_MATPLOTLIB:
        raise ImportError(
            "matplotlib is required to generate overlap visualizations. "
            "Install it using: pip install matplotlib"
        )
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 8), dpi=200)
    fig.patch.set_facecolor("#0b0f19")
    ax.set_facecolor("#111827")

    # Determine plot bounds with 15% margin
    all_polys = [source_footprint.polygon, reference_footprint.polygon]
    if intersection_polygon and not intersection_polygon.is_empty:
        all_polys.append(intersection_polygon)

    min_x = min(p.bounds[0] for p in all_polys)
    min_y = min(p.bounds[1] for p in all_polys)
    max_x = max(p.bounds[2] for p in all_polys)
    max_y = max(p.bounds[3] for p in all_polys)

    span_x = max(1e-4, max_x - min_x)
    span_y = max(1e-4, max_y - min_y)
    margin_x = span_x * 0.15
    margin_y = span_y * 0.15

    ax.set_xlim(min_x - margin_x, max_x + margin_x)
    ax.set_ylim(min_y - margin_y, max_y + margin_y)

    # 1. Plot Reference Footprint (Orange / Gold)
    ref_coords = list(reference_footprint.polygon.exterior.coords)
    ref_patch = MplPolygon(
        ref_coords,
        closed=True,
        facecolor="#f59e0b",
        alpha=0.20,
        edgecolor="#f59e0b",
        linewidth=2.0,
        linestyle="--",
        label=f"{reference_title} ({reference_footprint.area_km2:.1f} km²)",
        zorder=2,
    )
    ax.add_patch(ref_patch)

    # 2. Plot Source Footprint (Cyan / Blue)
    src_coords = list(source_footprint.polygon.exterior.coords)
    src_patch = MplPolygon(
        src_coords,
        closed=True,
        facecolor="#38bdf8",
        alpha=0.25,
        edgecolor="#38bdf8",
        linewidth=2.0,
        label=f"{source_title} ({source_footprint.area_km2:.1f} km²)",
        zorder=3,
    )
    ax.add_patch(src_patch)

    # 3. Plot Intersection Footprint (Emerald Green)
    if intersection_polygon and not intersection_polygon.is_empty:
        if isinstance(intersection_polygon, MultiPolygon):
            polys = list(intersection_polygon.geoms)
        else:
            polys = [intersection_polygon]

        for i, poly in enumerate(polys):
            inter_coords = list(poly.exterior.coords)
            lbl = f"Common Geographic Intersection ({intersection_area_km2:.1f} km²)" if i == 0 else None
            inter_patch = MplPolygon(
                inter_coords,
                closed=True,
                facecolor="#10b981",
                alpha=0.55,
                edgecolor="#10b981",
                linewidth=2.5,
                hatch="//",
                label=lbl,
                zorder=4,
            )
            ax.add_patch(inter_patch)

    # Style axes
    ax.set_title(
        "NEXUS-LUNAR: Lunar Surface Footprint Geographic Intersection",
        color="#f3f4f6",
        fontsize=14,
        fontweight="bold",
        pad=16,
    )
    ax.set_xlabel("Selenographic Longitude (degrees East)", color="#9ca3af", fontsize=11, labelpad=8)
    ax.set_ylabel("Selenographic Latitude (degrees North)", color="#9ca3af", fontsize=11, labelpad=8)
    ax.tick_params(colors="#9ca3af", which="both", labelsize=10)
    ax.grid(color="#374151", linestyle=":", linewidth=0.8, alpha=0.7)

    for spine in ax.spines.values():
        spine.set_edgecolor("#374151")

    # Legend
    legend = ax.legend(
        loc="upper right",
        framealpha=0.9,
        facecolor="#1f2937",
        edgecolor="#4b5563",
        fontsize=10,
    )
    for text in legend.get_texts():
        text.set_color("#f3f4f6")

    # Subtitle / Annotation box
    conf_text = (
        f"Geometric Overlap Confidence: {overlap_confidence:.2f}\n"
        f"Common Area: {intersection_area_km2:.2f} km²\n"
        f"CRS: Lunar Selenographic (Moon IAU 2000)"
    )
    ax.text(
        0.02,
        0.03,
        conf_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="bottom",
        bbox=dict(boxstyle="round,pad=0.6", facecolor="#1f2937", edgecolor="#4b5563", alpha=0.9),
        color="#e5e7eb",
        zorder=10,
    )

    plt.tight_layout()
    plt.savefig(out_p, dpi=200, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Generated footprint overlap visualization: {out_p}")
    return out_p


def generate_patch_comparison_visualization(
    source_patch_path: Union[str, Path],
    reference_patch_path: Union[str, Path],
    metadata: Dict[str, Any],
    output_path: Union[str, Path],
) -> Path:
    """Generates a side-by-side comparison figure showing corresponding native geographic patches."""
    if not HAS_MATPLOTLIB:
        raise ImportError(
            "matplotlib is required to generate patch comparison visualizations. "
            "Install it using: pip install matplotlib"
        )
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    src_p = Path(source_patch_path)
    ref_p = Path(reference_patch_path)

    src_img = Image.open(src_p)
    ref_img = Image.open(ref_p)

    src_res = metadata.get("source", {}).get("resolution_m_per_pixel", 0.25)
    ref_res = metadata.get("reference", {}).get("resolution_m_per_pixel", 1.0)
    bounds = metadata.get("common_ground_footprint", {}).get("bounds", {})
    min_lon = bounds.get("min_lon", "N/A")
    min_lat = bounds.get("min_lat", "N/A")
    max_lon = bounds.get("max_lon", "N/A")
    max_lat = bounds.get("max_lat", "N/A")

    src_id = metadata.get("source", {}).get("id", "Source")
    ref_id = metadata.get("reference", {}).get("id", "Reference")

    src_dims = f"{src_img.width} x {src_img.height} px"
    ref_dims = f"{ref_img.width} x {ref_img.height} px"

    fig, axes = plt.subplots(1, 2, figsize=(14, 7), dpi=200)
    fig.patch.set_facecolor("#0b0f19")

    # Left: Source Patch
    axes[0].set_facecolor("#111827")
    axes[0].imshow(src_img, cmap="gray")
    axes[0].set_title(
        f"SOURCE PATCH: {src_id[:28]}...\nResolution: {src_res} m/pixel | Dimensions: {src_dims}",
        color="#38bdf8",
        fontsize=11,
        fontweight="bold",
        pad=10,
    )
    axes[0].tick_params(colors="#9ca3af", labelsize=8)
    for spine in axes[0].spines.values():
        spine.set_edgecolor("#38bdf8")

    # Right: Reference Patch
    axes[1].set_facecolor("#111827")
    axes[1].imshow(ref_img, cmap="gray")
    axes[1].set_title(
        f"REFERENCE PATCH: {ref_id[:28]}...\nResolution: {ref_res} m/pixel | Dimensions: {ref_dims}",
        color="#f59e0b",
        fontsize=11,
        fontweight="bold",
        pad=10,
    )
    axes[1].tick_params(colors="#9ca3af", labelsize=8)
    for spine in axes[1].spines.values():
        spine.set_edgecolor("#f59e0b")

    # Figure annotations
    coord_str = f"Common Geographic Footprint: Lon [{min_lon}°, {max_lon}°], Lat [{min_lat}°, {max_lat}°]"
    fig.suptitle(
        "NEXUS-LUNAR: Resolution-Aware Geographic Patch Pair\n"
        "(Extracted from Common Physical Lunar Ground Footprint)",
        color="#f3f4f6",
        fontsize=13,
        fontweight="bold",
        y=0.98,
    )
    fig.text(
        0.5,
        0.02,
        f"{coord_str}\nNote: Patches correspond to the identical physical lunar region at sensor-native sampling rates.",
        ha="center",
        fontsize=10,
        color="#9ca3af",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#1f2937", edgecolor="#374151", alpha=0.9),
    )

    plt.tight_layout(rect=[0, 0.05, 1, 0.93])
    plt.savefig(out_p, dpi=200, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Generated patch comparison visualization: {out_p}")
    return out_p
