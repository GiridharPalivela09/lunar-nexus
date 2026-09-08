"""Lunar Data Catalog and Spatial Index for managing and querying observations and overlapping pairs."""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Union, Tuple
from shapely.geometry import Polygon, box

from .models import (
    SensorType,
    MissionType,
    BoundingBox,
    LunarObservation,
    CatalogQuery,
)

logger = logging.getLogger("nexus.data.catalog")


class LunarDataCatalog:
    """Persistent catalog managing indexed lunar observations and spatial overlap searches."""

    def __init__(self, catalog_file: Union[str, Path] = "data/catalog.json"):
        self.catalog_file = Path(catalog_file)
        self.catalog_file.parent.mkdir(parents=True, exist_ok=True)
        self._observations: Dict[str, LunarObservation] = {}
        self.load()

    def load(self):
        """Loads observations from the catalog file."""
        if not self.catalog_file.exists():
            self._observations = {}
            return

        try:
            with open(self.catalog_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._observations = {
                    pid: LunarObservation(**item) for pid, item in data.items()
                }
            logger.info(f"Loaded {len(self._observations)} items from catalog {self.catalog_file}")
        except Exception as e:
            logger.warning(f"Failed to load catalog {self.catalog_file}: {e}")
            self._observations = {}

    def save(self):
        """Persists observations to the catalog file."""
        data = {
            pid: json.loads(obs.model_dump_json())
            for pid, obs in self._observations.items()
        }
        with open(self.catalog_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved {len(self._observations)} observations to {self.catalog_file}")

    def add_observation(self, obs: LunarObservation, save_now: bool = True):
        """Adds or updates an observation in the catalog."""
        self._observations[obs.product_id] = obs
        if save_now:
            self.save()

    def add_observations(self, obs_list: List[LunarObservation]):
        """Adds multiple observations and saves once."""
        for obs in obs_list:
            self._observations[obs.product_id] = obs
        self.save()

    def get_by_id(self, product_id: str) -> Optional[LunarObservation]:
        """Retrieves an observation by its product ID."""
        return self._observations.get(product_id)

    def list_observations(self) -> List[LunarObservation]:
        """Returns all cataloged observations."""
        return list(self._observations.values())

    def query(self, query: CatalogQuery) -> List[LunarObservation]:
        """Queries observations matching spatial, temporal, and sensor filters."""
        results: List[LunarObservation] = []
        
        query_poly = None
        if query.bbox:
            query_poly = box(
                query.bbox.min_lon, query.bbox.min_lat, query.bbox.max_lon, query.bbox.max_lat
            )

        for obs in self._observations.values():
            # Sensor filter
            if query.sensors and obs.sensor not in query.sensors:
                continue

            # Resolution filter
            if query.min_resolution_m and (not obs.spatial_resolution_m or obs.spatial_resolution_m < query.min_resolution_m):
                continue
            if query.max_resolution_m and (not obs.spatial_resolution_m or obs.spatial_resolution_m > query.max_resolution_m):
                continue

            # Spatial intersection filter
            if query_poly:
                obs_poly = box(
                    obs.bbox.min_lon, obs.bbox.min_lat, obs.bbox.max_lon, obs.bbox.max_lat
                )
                if not query_poly.intersects(obs_poly):
                    continue

            # Time filter
            if query.start_time and obs.acquisition_time and obs.acquisition_time < query.start_time:
                continue
            if query.end_time and obs.acquisition_time and obs.acquisition_time > query.end_time:
                continue

            results.append(obs)
            if len(results) >= query.limit:
                break

        return results

    def find_overlapping_pairs(
        self,
        source_sensor: SensorType = SensorType.OHRC,
        reference_sensor: SensorType = SensorType.LRO_NAC,
        min_overlap_pct: float = 5.0,
    ) -> List[Dict[str, Any]]:
        """Finds pairs of observations between source and reference sensors that physically overlap.
        
        Returns a list of match candidate dictionaries containing overlap geometry & percentages.
        """
        sources = [obs for obs in self._observations.values() if obs.sensor == source_sensor]
        references = [obs for obs in self._observations.values() if obs.sensor == reference_sensor]

        pairs: List[Dict[str, Any]] = []

        for src in sources:
            src_poly = box(src.bbox.min_lon, src.bbox.min_lat, src.bbox.max_lon, src.bbox.max_lat)
            src_area = src_poly.area
            if src_area <= 0:
                continue

            for ref in references:
                ref_poly = box(ref.bbox.min_lon, ref.bbox.min_lat, ref.bbox.max_lon, ref.bbox.max_lat)
                if not src_poly.intersects(ref_poly):
                    continue

                intersection = src_poly.intersection(ref_poly)
                overlap_area = intersection.area
                overlap_pct_src = (overlap_area / src_area) * 100.0
                overlap_pct_ref = (overlap_area / ref_poly.area) * 100.0

                if overlap_pct_src >= min_overlap_pct or overlap_pct_ref >= min_overlap_pct:
                    min_x, min_y, max_x, max_y = intersection.bounds
                    
                    # Calculate ground area in km^2 on Moon (radius 1737.4 km)
                    import math
                    lat_dist_km = abs(max_y - min_y) * (1737400.0 * 2.0 * math.pi / 360.0 / 1000.0)
                    center_lat_rad = math.radians((min_y + max_y) / 2.0)
                    lon_dist_km = abs(max_x - min_x) * (1737400.0 * 2.0 * math.pi / 360.0 / 1000.0) * max(0.01, math.cos(center_lat_rad))
                    area_km2 = round(lat_dist_km * lon_dist_km, 4)

                    pairs.append({
                        "source_product_id": src.product_id,
                        "source_sensor": src.sensor.value,
                        "reference_product_id": ref.product_id,
                        "reference_sensor": ref.sensor.value,
                        "overlap_percent_of_source": round(overlap_pct_src, 2),
                        "overlap_percent_of_reference": round(overlap_pct_ref, 2),
                        "overlap_area_km2": area_km2,
                        "intersection_bbox": {
                            "min_lat": min_y,
                            "max_lat": max_y,
                            "min_lon": min_x,
                            "max_lon": max_x,
                        },
                        "source_resolution_m": src.spatial_resolution_m,
                        "reference_resolution_m": ref.spatial_resolution_m,
                        "solar_incidence_diff_deg": abs(
                            (src.geometry.incidence_angle_deg or 0) - (ref.geometry.incidence_angle_deg or 0)
                        ),
                    })

        # Sort by highest overlap percentage
        pairs.sort(key=lambda p: p["overlap_percent_of_source"], reverse=True)
        return pairs

    def extract_patches_for_pairs(
        self,
        source_sensor: SensorType = SensorType.OHRC,
        reference_sensor: SensorType = SensorType.LRO_NAC,
        min_overlap_pct: float = 5.0,
        patch_size: int = 512,
        stride: Optional[int] = None,
        output_dir: Union[str, Path] = "data/processed/patches",
    ) -> List[Dict[str, Any]]:
        """Finds overlapping pairs and extracts resolution-harmonized patches for each pair."""
        from .patch_extractor import OverlapPatchExtractor
        from .models import PatchExtractionConfig

        config = PatchExtractionConfig(
            patch_size=patch_size,
            stride=stride,
            min_overlap_pct=min_overlap_pct,
        )
        extractor = OverlapPatchExtractor(config=config)
        pairs = self.find_overlapping_pairs(
            source_sensor=source_sensor,
            reference_sensor=reference_sensor,
            min_overlap_pct=min_overlap_pct,
        )

        manifests = []
        for pair_info in pairs:
            src_obs = self.get_by_id(pair_info["source_product_id"])
            ref_obs = self.get_by_id(pair_info["reference_product_id"])
            if src_obs and ref_obs:
                try:
                    manifest = extractor.extract_patch_pairs(
                        source_obs=src_obs,
                        reference_obs=ref_obs,
                        output_dir=output_dir,
                    )
                    manifests.append(json.loads(manifest.model_dump_json()))
                except Exception as e:
                    logger.warning(
                        f"Failed to extract patches for pair {src_obs.product_id} & {ref_obs.product_id}: {e}"
                    )

        return manifests

