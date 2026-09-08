"""POC 2: Geographic Overlap & Resolution-Aware Patch Extraction Engine for Lunar Observations."""

from __future__ import annotations
import os
import math
import json
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any, Union
import numpy as np
from PIL import Image, ImageOps
from shapely.geometry import box, Polygon

from .models import (
    BoundingBox,
    LunarObservation,
    ResolutionStrategy,
    PixelBox,
    PatchExtractionConfig,
    ExtractedPatchPair,
    PatchManifest,
)

logger = logging.getLogger("nexus.data.patch_extractor")

# Lunar mean radius in meters and kilometers
LUNAR_RADIUS_M = 1_737_400.0
LUNAR_RADIUS_KM = 1_737.4
METERS_PER_DEG_LAT = (2.0 * math.pi * LUNAR_RADIUS_M) / 360.0  # ~30,323.35 m/deg


class GeoPixelTransformer:
    """Handles bidirectional transformation between Lunar geographic coordinates (lat, lon)
    and raster pixel space (x, y) for an observation."""

    def __init__(self, bbox: BoundingBox, image_width: int, image_height: int):
        self.bbox = bbox
        self.width = image_width
        self.height = image_height

        self.lat_span = abs(self.bbox.max_lat - self.bbox.min_lat)
        self.lon_span = abs(self.bbox.max_lon - self.bbox.min_lon)

        if self.lat_span <= 1e-9 or self.lon_span <= 1e-9:
            raise ValueError(f"Invalid BoundingBox spans: lat_span={self.lat_span}, lon_span={self.lon_span}")
        if self.width <= 0 or self.height <= 0:
            raise ValueError(f"Invalid image dimensions: {self.width}x{self.height}")

    def geo_to_pixel(self, lat: float, lon: float) -> Tuple[float, float]:
        """Maps (lat, lon) to continuous pixel coordinate (x, y).
        Standard lunar raster: (0, 0) is top-left (max_lat, min_lon)."""
        x = ((lon - self.bbox.min_lon) / self.lon_span) * self.width
        y = ((self.bbox.max_lat - lat) / self.lat_span) * self.height
        return x, y

    def pixel_to_geo(self, x: float, y: float) -> Tuple[float, float]:
        """Maps continuous pixel coordinate (x, y) back to (lat, lon)."""
        lon = self.bbox.min_lon + (x / self.width) * self.lon_span
        lat = self.bbox.max_lat - (y / self.height) * self.lat_span
        return lat, lon

    def bbox_to_pixel_box(self, sub_bbox: BoundingBox) -> PixelBox:
        """Converts a geographic sub-bounding-box into an integer pixel window clamped to image bounds."""
        # Top-left is (max_lat, min_lon), bottom-right is (min_lat, max_lon)
        x0, y0 = self.geo_to_pixel(sub_bbox.max_lat, sub_bbox.min_lon)
        x1, y1 = self.geo_to_pixel(sub_bbox.min_lat, sub_bbox.max_lon)

        min_px = max(0, min(self.width, int(math.floor(min(x0, x1)))))
        max_px = max(0, min(self.width, int(math.ceil(max(x0, x1)))))
        min_py = max(0, min(self.height, int(math.floor(min(y0, y1)))))
        max_py = max(0, min(self.height, int(math.ceil(max(y0, y1)))))

        w = max(1, max_px - min_px)
        h = max(1, max_py - min_py)

        return PixelBox(x=min_px, y=min_py, width=w, height=h)

    def pixel_box_to_bbox(self, pbox: PixelBox) -> BoundingBox:
        """Converts an integer pixel window into its exact geographic bounding box."""
        lat_top, lon_left = self.pixel_to_geo(pbox.x, pbox.y)
        lat_bottom, lon_right = self.pixel_to_geo(pbox.x + pbox.width, pbox.y + pbox.height)

        return BoundingBox(
            min_lat=min(lat_top, lat_bottom),
            max_lat=max(lat_top, lat_bottom),
            min_lon=min(lon_left, lon_right),
            max_lon=max(lon_left, lon_right),
        )


class ResolutionHarmonizer:
    """Manages ground sampling distance (GSD) alignment between heterogeneous sensors."""

    @staticmethod
    def calculate_effective_gsd(
        source_gsd: float,
        reference_gsd: float,
        strategy: ResolutionStrategy = ResolutionStrategy.MATCH_COARSER,
        explicit_target: Optional[float] = None,
    ) -> float:
        """Determines the target GSD in meters per pixel."""
        if explicit_target and explicit_target > 0:
            return float(explicit_target)

        if strategy == ResolutionStrategy.MATCH_COARSER:
            return max(source_gsd, reference_gsd)
        elif strategy == ResolutionStrategy.MATCH_FINER:
            return min(source_gsd, reference_gsd)
        else:
            return source_gsd

    @staticmethod
    def resample_patch(image: Image.Image, current_gsd: float, target_gsd: float) -> Image.Image:
        """Resamples a PIL image to match the target GSD."""
        if abs(current_gsd - target_gsd) < 1e-4:
            return image

        scale_factor = current_gsd / target_gsd
        new_w = max(1, int(round(image.width * scale_factor)))
        new_h = max(1, int(round(image.height * scale_factor)))

        resample_method = (
            Image.Resampling.LANCZOS if scale_factor < 1.0 else Image.Resampling.BICUBIC
        )
        return image.resize((new_w, new_h), resample=resample_method)


class OverlapQualityScorer:
    """Computes a multi-factor confidence and quality score for overlapping observation pairs."""

    @staticmethod
    def compute_ground_area_km2(sub_bbox: BoundingBox) -> float:
        """Calculates approximate physical ground area in km^2 on the Lunar sphere."""
        lat_dist_km = abs(sub_bbox.max_lat - sub_bbox.min_lat) * (METERS_PER_DEG_LAT / 1000.0)
        center_lat_rad = math.radians((sub_bbox.min_lat + sub_bbox.max_lat) / 2.0)
        lon_dist_km = (
            abs(sub_bbox.max_lon - sub_bbox.min_lon)
            * (METERS_PER_DEG_LAT / 1000.0)
            * max(0.01, math.cos(center_lat_rad))
        )
        return float(lat_dist_km * lon_dist_km)

    @classmethod
    def score(
        cls,
        overlap_pct: float,
        source_gsd: Optional[float],
        reference_gsd: Optional[float],
        sun_incidence_diff_deg: Optional[float],
    ) -> float:
        """Calculates a composite confidence score between 0.0 and 1.0.
        
        Factors:
        - Overlap percentage (40% weight)
        - Resolution compatibility (30% weight)
        - Solar illumination consistency (30% weight)
        """
        # 1. Overlap component (100% overlap -> 1.0, 5% overlap -> ~0.05)
        overlap_score = min(1.0, max(0.0, overlap_pct / 100.0))

        # 2. Resolution ratio component (1.0 = identical GSD, 0.1 = 10x difference)
        res_score = 0.8
        if source_gsd and reference_gsd and source_gsd > 0 and reference_gsd > 0:
            ratio = min(source_gsd, reference_gsd) / max(source_gsd, reference_gsd)
            res_score = min(1.0, max(0.1, ratio))

        # 3. Solar incidence delta component (0 deg diff -> 1.0, >= 60 deg diff -> 0.0)
        sun_score = 0.8
        if sun_incidence_diff_deg is not None:
            sun_score = max(0.0, 1.0 - (abs(sun_incidence_diff_deg) / 60.0))

        composite = (0.40 * overlap_score) + (0.30 * res_score) + (0.30 * sun_score)
        return round(float(composite), 4)


class OverlapPatchExtractor:
    """Core POC 2 Engine: Identifies geographic intersections, maps coordinates to pixel windows,
    harmonizes GSD, and extracts co-registered patch pairs with tiling and manifests."""

    def __init__(self, config: Optional[PatchExtractionConfig] = None):
        self.config = config or PatchExtractionConfig()

    @staticmethod
    def _create_polygon(bbox: BoundingBox, footprint_polygon: Optional[List[Tuple[float, float]]] = None) -> Polygon:
        """Constructs a Shapely polygon, preferring true rotated footprint boundary over axis-aligned box."""
        if footprint_polygon and len(footprint_polygon) >= 3:
            try:
                poly = Polygon(footprint_polygon)
                if poly.is_valid and not poly.is_empty and poly.area > 0:
                    return poly
            except Exception:
                pass
        return box(bbox.min_lon, bbox.min_lat, bbox.max_lon, bbox.max_lat)

    def find_geographic_intersection(
        self,
        source_bbox: BoundingBox,
        ref_bbox: BoundingBox,
        source_polygon: Optional[List[Tuple[float, float]]] = None,
        ref_polygon: Optional[List[Tuple[float, float]]] = None,
    ) -> Tuple[Optional[BoundingBox], float, float]:
        """Computes the intersection bounding box and overlap percentages for both footprints.
        Returns: (intersection_bbox, overlap_pct_source, overlap_pct_ref)."""
        src_poly = self._create_polygon(source_bbox, source_polygon)
        ref_poly = self._create_polygon(ref_bbox, ref_polygon)

        if not src_poly.intersects(ref_poly):
            return None, 0.0, 0.0

        inter_geom = src_poly.intersection(ref_poly)
        if inter_geom.is_empty or inter_geom.area <= 0:
            return None, 0.0, 0.0

        min_lon, min_lat, max_lon, max_lat = inter_geom.bounds
        overlap_pct_src = (inter_geom.area / src_poly.area) * 100.0
        overlap_pct_ref = (inter_geom.area / ref_poly.area) * 100.0

        inter_bbox = BoundingBox(
            min_lat=min_lat, max_lat=max_lat, min_lon=min_lon, max_lon=max_lon
        )
        return inter_bbox, round(overlap_pct_src, 2), round(overlap_pct_ref, 2)

    def extract_patch_pairs(
        self,
        source_obs: LunarObservation,
        reference_obs: LunarObservation,
        output_dir: Union[str, Path] = "data/processed/patches",
        source_img: Optional[Image.Image] = None,
        ref_img: Optional[Image.Image] = None,
    ) -> PatchManifest:
        """Performs full resolution-aware patch extraction for an observation pair."""
        pair_key = f"{source_obs.product_id}___{reference_obs.product_id}"
        out_path = Path(output_dir) / pair_key
        out_path.mkdir(parents=True, exist_ok=True)

        # 1. Geographic Intersection (using rotated footprint polygon if present)
        inter_bbox, pct_src, pct_ref = self.find_geographic_intersection(
            source_obs.bbox,
            reference_obs.bbox,
            source_polygon=source_obs.footprint_polygon,
            ref_polygon=reference_obs.footprint_polygon,
        )

        if not inter_bbox or pct_src < self.config.min_overlap_pct:
            logger.warning(
                f"Pair {pair_key} does not meet overlap threshold (src overlap: {pct_src}% < {self.config.min_overlap_pct}%)"
            )
            return PatchManifest(
                source_product_id=source_obs.product_id,
                reference_product_id=reference_obs.product_id,
                total_patches=0,
                intersection_bbox=inter_bbox or source_obs.bbox,
                intersection_area_km2=0.0,
                config=self.config,
                patches=[],
            )

        inter_area_km2 = OverlapQualityScorer.compute_ground_area_km2(inter_bbox)

        # 2. Load images if not provided
        src_image = source_img or self._load_observation_image(source_obs)
        ref_image = ref_img or self._load_observation_image(reference_obs)

        if src_image is None or ref_image is None:
            raise FileNotFoundError(f"Could not load image data for pair {pair_key}")

        # 3. Geo-to-Pixel Mapping
        src_geo_trans = GeoPixelTransformer(source_obs.bbox, src_image.width, src_image.height)
        ref_geo_trans = GeoPixelTransformer(reference_obs.bbox, ref_image.width, ref_image.height)

        src_crop_box = src_geo_trans.bbox_to_pixel_box(inter_bbox)
        ref_crop_box = ref_geo_trans.bbox_to_pixel_box(inter_bbox)

        # 4. Crop common physical region
        src_cropped = src_image.crop(
            (src_crop_box.x, src_crop_box.y, src_crop_box.x + src_crop_box.width, src_crop_box.y + src_crop_box.height)
        )
        ref_cropped = ref_image.crop(
            (ref_crop_box.x, ref_crop_box.y, ref_crop_box.x + ref_crop_box.width, ref_crop_box.y + ref_crop_box.height)
        )

        # 5. GSD & Resolution Harmonization
        src_gsd = source_obs.spatial_resolution_m or 1.0
        ref_gsd = reference_obs.spatial_resolution_m or 1.0

        effective_gsd = ResolutionHarmonizer.calculate_effective_gsd(
            src_gsd, ref_gsd, self.config.resolution_strategy, self.config.target_resolution_m
        )

        if self.config.resolution_strategy != ResolutionStrategy.NATIVE_PHYSICAL:
            src_cropped = ResolutionHarmonizer.resample_patch(src_cropped, src_gsd, effective_gsd)
            ref_cropped = ResolutionHarmonizer.resample_patch(ref_cropped, ref_gsd, effective_gsd)

        # Synchronize raster dimensions between source and reference after GSD resampling
        common_w = min(src_cropped.width, ref_cropped.width)
        common_h = min(src_cropped.height, ref_cropped.height)
        src_cropped = src_cropped.crop((0, 0, common_w, common_h))
        ref_cropped = ref_cropped.crop((0, 0, common_w, common_h))

        # Compute solar difference
        sun_diff = None
        if (
            source_obs.geometry.incidence_angle_deg is not None
            and reference_obs.geometry.incidence_angle_deg is not None
        ):
            sun_diff = abs(
                source_obs.geometry.incidence_angle_deg - reference_obs.geometry.incidence_angle_deg
            )

        quality_score = OverlapQualityScorer.score(pct_src, src_gsd, ref_gsd, sun_diff)

        # 6. Sliding Window Tiling over common overlap area
        patch_size = self.config.patch_size
        stride = self.config.stride or patch_size

        patches: List[ExtractedPatchPair] = []
        fmt = self.config.output_format.lower()
        if fmt not in ["png", "jpg", "tif", "tiff"]:
            fmt = "png"

        # Helper to guarantee exact square patch dimensions for downstream ML models
        def _ensure_patch_size(img: Image.Image, target_size: int) -> Image.Image:
            if img.size == (target_size, target_size):
                return img
            pad_w = max(0, target_size - img.width)
            pad_h = max(0, target_size - img.height)
            if pad_w > 0 or pad_h > 0:
                return ImageOps.expand(img, (0, 0, pad_w, pad_h), fill=0)
            return img.crop((0, 0, target_size, target_size))

        tile_w = src_cropped.width
        tile_h = src_cropped.height

        # If overlap is smaller than requested patch_size, pad to exact patch_size
        if tile_w < patch_size or tile_h < patch_size:
            idx = 1
            src_p_path = out_path / f"patch_{idx:04d}_src.{fmt}"
            ref_p_path = out_path / f"patch_{idx:04d}_ref.{fmt}"

            src_p = _ensure_patch_size(src_cropped, patch_size)
            ref_p = _ensure_patch_size(ref_cropped, patch_size)
            src_p.save(src_p_path)
            ref_p.save(ref_p_path)

            patch_pair = ExtractedPatchPair(
                pair_id=f"{pair_key}_p{idx:04d}",
                patch_index=idx,
                source_product_id=source_obs.product_id,
                reference_product_id=reference_obs.product_id,
                source_patch_path=str(src_p_path),
                reference_patch_path=str(ref_p_path),
                ground_bbox=inter_bbox,
                source_pixel_box=PixelBox(x=0, y=0, width=patch_size, height=patch_size),
                reference_pixel_box=PixelBox(x=0, y=0, width=patch_size, height=patch_size),
                effective_resolution_m=round(effective_gsd, 3),
                overlap_pct=pct_src,
                solar_incidence_diff_deg=sun_diff,
                quality_score=quality_score,
            )
            patches.append(patch_pair)
        else:
            idx = 1
            y_steps = list(range(0, tile_h - patch_size + 1, stride))
            if (tile_h - patch_size) not in y_steps and (tile_h - patch_size) > 0:
                y_steps.append(tile_h - patch_size)

            x_steps = list(range(0, tile_w - patch_size + 1, stride))
            if (tile_w - patch_size) not in x_steps and (tile_w - patch_size) > 0:
                x_steps.append(tile_w - patch_size)

            for py in y_steps:
                for px in x_steps:
                    raw_src = src_cropped.crop((px, py, min(tile_w, px + patch_size), min(tile_h, py + patch_size)))
                    raw_ref = ref_cropped.crop((px, py, min(tile_w, px + patch_size), min(tile_h, py + patch_size)))

                    src_patch = _ensure_patch_size(raw_src, patch_size)
                    ref_patch = _ensure_patch_size(raw_ref, patch_size)

                    src_p_path = out_path / f"patch_{idx:04d}_src.{fmt}"
                    ref_p_path = out_path / f"patch_{idx:04d}_ref.{fmt}"

                    src_patch.save(src_p_path)
                    ref_patch.save(ref_p_path)

                    # Compute geographic bounding box for this individual patch
                    # Interpolate within inter_bbox based on relative position
                    frac_min_x = px / tile_w
                    frac_max_x = (px + patch_size) / tile_w
                    frac_min_y = py / tile_h
                    frac_max_y = (py + patch_size) / tile_h

                    patch_min_lon = inter_bbox.min_lon + frac_min_x * (inter_bbox.max_lon - inter_bbox.min_lon)
                    patch_max_lon = inter_bbox.min_lon + frac_max_x * (inter_bbox.max_lon - inter_bbox.min_lon)
                    patch_max_lat = inter_bbox.max_lat - frac_min_y * (inter_bbox.max_lat - inter_bbox.min_lat)
                    patch_min_lat = inter_bbox.max_lat - frac_max_y * (inter_bbox.max_lat - inter_bbox.min_lat)

                    patch_bbox = BoundingBox(
                        min_lat=min(patch_min_lat, patch_max_lat),
                        max_lat=max(patch_min_lat, patch_max_lat),
                        min_lon=min(patch_min_lon, patch_max_lon),
                        max_lon=max(patch_min_lon, patch_max_lon),
                    )

                    patch_pair = ExtractedPatchPair(
                        pair_id=f"{pair_key}_p{idx:04d}",
                        patch_index=idx,
                        source_product_id=source_obs.product_id,
                        reference_product_id=reference_obs.product_id,
                        source_patch_path=str(src_p_path),
                        reference_patch_path=str(ref_p_path),
                        ground_bbox=patch_bbox,
                        source_pixel_box=PixelBox(x=px, y=py, width=patch_size, height=patch_size),
                        reference_pixel_box=PixelBox(x=px, y=py, width=patch_size, height=patch_size),
                        effective_resolution_m=round(effective_gsd, 3),
                        overlap_pct=pct_src,
                        solar_incidence_diff_deg=sun_diff,
                        quality_score=quality_score,
                    )
                    patches.append(patch_pair)
                    idx += 1

        manifest = PatchManifest(
            source_product_id=source_obs.product_id,
            reference_product_id=reference_obs.product_id,
            total_patches=len(patches),
            intersection_bbox=inter_bbox,
            intersection_polygon=inter_bbox.polygon_coords,
            intersection_area_km2=round(inter_area_km2, 4),
            config=self.config,
            patches=patches,
        )

        manifest_file = out_path / "patch_manifest.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            f.write(manifest.model_dump_json(indent=2))

        # Generate HTML Visual Report
        report_file = out_path / "overlap_report.html"
        self.generate_html_report(manifest, report_file, source_obs, reference_obs)

        logger.info(f"Extracted {len(patches)} patch pairs for {pair_key} to {out_path}")
        return manifest

    def generate_html_report(
        self,
        manifest: PatchManifest,
        output_html: Union[str, Path],
        source_obs: Optional[LunarObservation] = None,
        reference_obs: Optional[LunarObservation] = None,
    ):
        """Generates an interactive HTML visual report for the extracted patch pairs."""
        out_html_path = Path(output_html)
        src_id = manifest.source_product_id
        ref_id = manifest.reference_product_id
        src_sensor = source_obs.sensor.value if source_obs else "Source"
        ref_sensor = reference_obs.sensor.value if reference_obs else "Reference"

        cards_html = []
        for p in manifest.patches:
            src_file_name = Path(p.source_patch_path).name
            ref_file_name = Path(p.reference_patch_path).name
            cards_html.append(f"""
            <div class="patch-card">
              <div class="patch-card-header">
                <span class="patch-badge">Patch #{p.patch_index:04d}</span>
                <span class="quality-badge">Confidence: {p.quality_score:.2f}</span>
              </div>
              <div class="patch-images">
                <div class="img-box">
                  <div class="img-label">{src_sensor} (GSD: {source_obs.spatial_resolution_m if source_obs else 'N/A'}m)</div>
                  <img src="{src_file_name}" alt="Source Patch #{p.patch_index}" loading="lazy" />
                </div>
                <div class="img-box">
                  <div class="img-label">{ref_sensor} (GSD: {reference_obs.spatial_resolution_m if reference_obs else 'N/A'}m)</div>
                  <img src="{ref_file_name}" alt="Reference Patch #{p.patch_index}" loading="lazy" />
                </div>
              </div>
              <div class="patch-meta">
                <span><strong>Lat:</strong> [{p.ground_bbox.min_lat:.3f}°, {p.ground_bbox.max_lat:.3f}°]</span>
                <span><strong>Lon:</strong> [{p.ground_bbox.min_lon:.3f}°, {p.ground_bbox.max_lon:.3f}°]</span>
                <span><strong>Effective GSD:</strong> {p.effective_resolution_m}m</span>
              </div>
            </div>
            """)

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NEXUS-LUNAR | Overlap & Patch Explorer: {src_id} vs {ref_id}</title>
  <style>
    :root {{
      --bg: #090d16;
      --card-bg: #131b2e;
      --border: #23314f;
      --text: #e6edf3;
      --text-muted: #8b949e;
      --accent: #58a6ff;
      --success: #3fb950;
      --purple: #bc8cff;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      padding: 24px;
    }}
    .container {{ max-width: 1400px; margin: 0 auto; }}
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border);
      padding-bottom: 20px;
      margin-bottom: 24px;
    }}
    .title {{ font-size: 1.6rem; font-weight: 700; color: var(--accent); }}
    .subtitle {{ font-size: 0.95rem; color: var(--text-muted); margin-top: 4px; }}
    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-bottom: 28px;
    }}
    .stat-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
    }}
    .stat-label {{ font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }}
    .stat-val {{ font-size: 1.4rem; font-weight: 700; color: #fff; margin-top: 6px; }}
    .stat-sub {{ font-size: 0.8rem; color: var(--accent); margin-top: 4px; }}
    .patches-header {{
      font-size: 1.25rem;
      margin-bottom: 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .patches-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
      gap: 20px;
    }}
    .patch-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      transition: transform 0.2s ease, border-color 0.2s ease;
    }}
    .patch-card:hover {{
      transform: translateY(-2px);
      border-color: var(--accent);
    }}
    .patch-card-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .patch-badge {{
      background: rgba(88, 166, 255, 0.15);
      color: var(--accent);
      padding: 4px 10px;
      border-radius: 20px;
      font-size: 0.85rem;
      font-weight: 600;
    }}
    .quality-badge {{
      background: rgba(63, 185, 80, 0.15);
      color: var(--success);
      padding: 4px 10px;
      border-radius: 20px;
      font-size: 0.85rem;
      font-weight: 600;
    }}
    .patch-images {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }}
    .img-box {{
      display: flex;
      flex-direction: column;
      gap: 6px;
      text-align: center;
    }}
    .img-label {{
      font-size: 0.75rem;
      color: var(--text-muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .img-box img {{
      width: 100%;
      aspect-ratio: 1 / 1;
      object-fit: cover;
      border-radius: 6px;
      border: 1px solid var(--border);
      background: #000;
    }}
    .patch-meta {{
      font-size: 0.8rem;
      color: var(--text-muted);
      border-top: 1px solid var(--border);
      padding-top: 10px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div>
        <div class="title">NEXUS-LUNAR: Geographic Overlap & Patch Explorer</div>
        <div class="subtitle">Proof-of-Concept 2: Resolution-Aware Cross-Sensor Ground Footprint Matching</div>
      </div>
      <div>
        <span class="patch-badge">POC 2 Verified</span>
      </div>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">Source Product</div>
        <div class="stat-val" style="font-size: 1.0rem;">{src_id}</div>
        <div class="stat-sub">{src_sensor} | Res: {source_obs.spatial_resolution_m if source_obs else 'N/A'}m</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Reference Product</div>
        <div class="stat-val" style="font-size: 1.0rem;">{ref_id}</div>
        <div class="stat-sub">{ref_sensor} | Res: {reference_obs.spatial_resolution_m if reference_obs else 'N/A'}m</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Intersection Area</div>
        <div class="stat-val">{manifest.intersection_area_km2:.2f} <span style="font-size: 0.9rem;">km²</span></div>
        <div class="stat-sub">Ground Footprint</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Patches Generated</div>
        <div class="stat-val">{manifest.total_patches} <span style="font-size: 0.9rem;">pairs</span></div>
        <div class="stat-sub">Size: {manifest.config.patch_size}x{manifest.config.patch_size}px</div>
      </div>
    </div>

    <div class="patches-header">
      <div><strong>Co-Registered Physical Patches</strong></div>
      <div style="font-size: 0.85rem; color: var(--text-muted);">Coordinate Bounds: Lat [{manifest.intersection_bbox.min_lat:.2f}°, {manifest.intersection_bbox.max_lat:.2f}°], Lon [{manifest.intersection_bbox.min_lon:.2f}°, {manifest.intersection_bbox.max_lon:.2f}°]</div>
    </div>

    <div class="patches-grid">
      {''.join(cards_html)}
    </div>
  </div>
</body>
</html>
"""
        with open(out_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    def _load_observation_image(self, obs: LunarObservation) -> Optional[Image.Image]:
        """Finds and loads the image for an observation (preview or primary) with scientific dynamic range normalization."""
        candidates = [
            obs.primary_image_path,
            obs.preview_image_path,
        ]
        project_root = Path(__file__).resolve().parent.parent.parent
        for p in candidates:
            if not p:
                continue
            resolved_p = p
            if not os.path.exists(resolved_p):
                clean_p = str(p).replace("\\", "/")
                if os.path.exists(clean_p):
                    resolved_p = clean_p
                else:
                    idx = clean_p.find("data/")
                    if idx != -1:
                        cand = project_root / clean_p[idx:]
                        if cand.exists():
                            resolved_p = str(cand)
                    elif (project_root / clean_p).exists():
                        resolved_p = str(project_root / clean_p)
            if os.path.exists(resolved_p):
                try:
                    img = Image.open(resolved_p)
                    # Convert scientific 16-bit or floating-point rasters using 2%-98% percentile stretching
                    arr = np.array(img)
                    if arr.dtype in [np.uint16, np.int16, np.int32, np.float32, np.float64] or (arr.ndim > 2 and arr.dtype != np.uint8):
                        if arr.ndim == 3 and arr.shape[2] == 1:
                            arr = arr[:, :, 0]
                        valid = np.isfinite(arr) & (arr > 0)
                        if np.any(valid):
                            p2, p98 = np.percentile(arr[valid], (2, 98))
                            if p98 > p2:
                                norm = np.clip((arr - p2) / (p98 - p2), 0.0, 1.0) * 255.0
                            else:
                                norm = np.zeros_like(arr, dtype=np.float32)
                            return Image.fromarray(norm.astype(np.uint8))

                    if img.mode != "L" and img.mode != "RGB":
                        img = img.convert("L")
                    return img
                except Exception as e:
                    logger.warning(f"Error opening image {p}: {e}")
        return None

