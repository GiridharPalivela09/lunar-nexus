"""NEXUS-LUNAR: Footprint Engine for Lunar Observations.

Converts lunar raster boundaries and corner coordinates into standardized geographic polygons
under Selenographic coordinate systems (Moon IAU2000 / Moon 2000 sphere R=1737.4 km).
"""

from __future__ import annotations
import math
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

import numpy as np
from shapely.geometry import Polygon, box, mapping
from shapely.validation import make_valid
import pyproj

try:
    import rasterio
    from rasterio.crs import CRS
    from rasterio.transform import Affine
    HAS_RASTERIO = True
except ImportError:
    rasterio = None
    CRS = None
    Affine = None
    HAS_RASTERIO = False

logger = logging.getLogger("nexus.data.footprint_engine")

# Lunar Physical Constants
LUNAR_RADIUS_M = 1_737_400.0
LUNAR_RADIUS_KM = 1_737.4
METERS_PER_DEG_LAT = (2.0 * math.pi * LUNAR_RADIUS_M) / 360.0  # ~30,323.35 m/deg

# Standard Lunar Coordinate Reference Systems
LUNAR_GEOGRAPHIC_PROJ4 = "+proj=longlat +R=1737400 +no_defs"
LUNAR_SOUTH_POLE_STEREO_PROJ4 = "+proj=stere +lat_0=-90 +lon_0=0 +k=1 +x_0=0 +y_0=0 +R=1737400 +units=m +no_defs"


@dataclass
class FootprintResult:
    """Represents a computed geographic footprint on the lunar surface."""
    polygon: Polygon                     # Polygon in lunar selenographic coordinates (lon, lat)
    bounds: Tuple[float, float, float, float]  # (min_lon, min_lat, max_lon, max_lat)
    area_km2: float                      # Physical ground area in square kilometers
    crs_name: str                        # Native CRS description
    native_bounds: Optional[Tuple[float, float, float, float]] = None # (min_x, min_y, max_x, max_y)
    is_valid: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def min_lon(self) -> float:
        return self.bounds[0]

    @property
    def min_lat(self) -> float:
        return self.bounds[1]

    @property
    def max_lon(self) -> float:
        return self.bounds[2]

    @property
    def max_lat(self) -> float:
        return self.bounds[3]

    @property
    def coordinates(self) -> List[Tuple[float, float]]:
        """List of (lon, lat) coordinates around the exterior ring."""
        return list(self.polygon.exterior.coords)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "Polygon",
            "coordinates": [list(c) for c in self.coordinates],
            "bounds": {
                "min_lon": round(self.min_lon, 6),
                "min_lat": round(self.min_lat, 6),
                "max_lon": round(self.max_lon, 6),
                "max_lat": round(self.max_lat, 6),
            },
            "area_km2": round(self.area_km2, 4),
            "crs": self.crs_name,
            "is_valid": self.is_valid,
        }


class FootprintEngine:
    """Calculates, standardizes, and reprojects lunar surface footprints."""

    def __init__(self, target_crs: str = LUNAR_GEOGRAPHIC_PROJ4):
        self.target_crs = target_crs
        self._target_pyproj = pyproj.CRS.from_user_input(target_crs)

    @staticmethod
    def compute_spherical_area_km2(polygon: Polygon) -> float:
        """Calculates ground area on the lunar sphere (R=1737.4 km) from (lon, lat) coordinates."""
        if polygon.is_empty or not polygon.is_valid:
            return 0.0

        # Project to local lunar stereographic centered at polygon centroid for accurate metric area
        cent_lon, cent_lat = polygon.centroid.x, polygon.centroid.y
        local_proj_str = f"+proj=stere +lat_0={cent_lat} +lon_0={cent_lon} +k=1 +x_0=0 +y_0=0 +R={LUNAR_RADIUS_M} +units=m +no_defs"
        try:
            transformer = pyproj.Transformer.from_crs(
                LUNAR_GEOGRAPHIC_PROJ4, local_proj_str, always_xy=True
            )
            coords = list(polygon.exterior.coords)
            xs, ys = transformer.transform([c[0] for c in coords], [c[1] for c in coords])
            local_poly = Polygon(zip(xs, ys))
            area_m2 = abs(local_poly.area)
            return float(area_m2 / 1e6)
        except Exception as e:
            logger.debug(f"Fallback spherical area calculation due to: {e}")
            # Fallback approximation using cosine of latitude
            min_lon, min_lat, max_lon, max_lat = polygon.bounds
            d_lat_km = abs(max_lat - min_lat) * (METERS_PER_DEG_LAT / 1000.0)
            avg_lat_rad = math.radians((min_lat + max_lat) / 2.0)
            d_lon_km = abs(max_lon - min_lon) * (METERS_PER_DEG_LAT / 1000.0) * max(0.01, math.cos(avg_lat_rad))
            return float(d_lat_km * d_lon_km)

    def extract_from_raster(self, raster_path: Union[str, Path]) -> FootprintResult:
        """Extracts the true lunar surface footprint directly from a georeferenced raster."""
        if not HAS_RASTERIO:
            raise ImportError(
                "The 'rasterio' package is required to extract footprints directly from georeferenced raster files. "
                "Install it using: pip install rasterio"
            )

        p = Path(raster_path)
        if not p.exists():
            raise FileNotFoundError(f"Raster file not found: {p}")

        with rasterio.open(p) as src:
            width = src.width
            height = src.height
            transform = src.transform
            crs = src.crs

            if crs is None:
                # If CRS is not defined in raster headers, raise validation error as required
                raise ValueError(
                    f"Raster {p.name} does not contain geospatial CRS metadata. "
                    "A valid Lunar CRS (e.g. IAU2000 / Polar Stereographic) is required."
                )

            # Native corners in raster projected space (top-left, top-right, bottom-right, bottom-left)
            # Pixel (0,0), (width, 0), (width, height), (0, height)
            corners_px = [(0, 0), (width, 0), (width, height), (0, height), (0, 0)]
            native_coords = [
                (transform.c + pt[0] * transform.a + pt[1] * transform.b,
                 transform.f + pt[0] * transform.d + pt[1] * transform.e)
                for pt in corners_px
            ]
            native_poly = Polygon(native_coords)
            native_bounds = native_poly.bounds

            # Transform native coordinates to lunar geographic (lon, lat)
            transformer = pyproj.Transformer.from_crs(crs, self._target_pyproj, always_xy=True)
            geo_xs, geo_ys = transformer.transform(
                [c[0] for c in native_coords],
                [c[1] for c in native_coords]
            )
            geo_coords = list(zip(geo_xs, geo_ys))
            geo_poly = Polygon(geo_coords)

            if not geo_poly.is_valid:
                geo_poly = make_valid(geo_poly)
                if geo_poly.geom_type == "MultiPolygon":
                    geo_poly = max(geo_poly.geoms, key=lambda a: a.area)

            area_km2 = self.compute_spherical_area_km2(geo_poly)
            bounds = geo_poly.bounds  # (min_lon, min_lat, max_lon, max_lat)

            return FootprintResult(
                polygon=geo_poly,
                bounds=bounds,
                area_km2=area_km2,
                crs_name=str(crs),
                native_bounds=native_bounds,
                is_valid=geo_poly.is_valid and not geo_poly.is_empty,
                metadata={
                    "width": width,
                    "height": height,
                    "driver": src.driver,
                    "res": src.res,
                    "source_path": str(p.resolve()),
                }
            )

    def extract_from_corners(
        self,
        corners: List[Tuple[float, float]],
        crs_input: Optional[Union[str, pyproj.CRS]] = None,
        is_lon_lat: bool = True,
    ) -> FootprintResult:
        """Constructs a footprint polygon from explicit corner coordinates (e.g. UL, UR, LR, LL).
        
        If `is_lon_lat` is True, corners are interpreted as (lon, lat) in degrees.
        If corners are (lat, lon), set is_lon_lat=False or reorder beforehand.
        """
        if len(corners) < 3:
            raise ValueError(f"At least 3 corners are required to construct a polygon, got {len(corners)}")

        coords = list(corners)
        if coords[0] != coords[-1]:
            coords.append(coords[0])

        if not is_lon_lat:
            # Swap (lat, lon) -> (lon, lat)
            coords = [(pt[1], pt[0]) for pt in coords]

        poly = Polygon(coords)
        if not poly.is_valid:
            poly = make_valid(poly)
            if poly.geom_type == "MultiPolygon":
                poly = max(poly.geoms, key=lambda a: a.area)

        # Reproject if a non-geographic CRS is specified for the coordinates
        if crs_input:
            input_crs_obj = pyproj.CRS.from_user_input(crs_input)
            if input_crs_obj != self._target_pyproj:
                transformer = pyproj.Transformer.from_crs(input_crs_obj, self._target_pyproj, always_xy=True)
                xs, ys = transformer.transform([c[0] for c in coords], [c[1] for c in coords])
                poly = Polygon(zip(xs, ys))
                if not poly.is_valid:
                    poly = make_valid(poly)
                    if poly.geom_type == "MultiPolygon":
                        poly = max(poly.geoms, key=lambda a: a.area)

        area_km2 = self.compute_spherical_area_km2(poly)
        return FootprintResult(
            polygon=poly,
            bounds=poly.bounds,
            area_km2=area_km2,
            crs_name=str(crs_input) if crs_input else "Lunar Selenographic (lon, lat)",
            is_valid=poly.is_valid and not poly.is_empty,
        )

    def extract_from_bounding_box(
        self, min_lat: float, max_lat: float, min_lon: float, max_lon: float
    ) -> FootprintResult:
        """Constructs an axis-aligned geographic footprint polygon."""
        if min_lat >= max_lat or min_lon >= max_lon:
            raise ValueError(f"Invalid bounding box: lat [{min_lat}, {max_lat}], lon [{min_lon}, {max_lon}]")
        poly = box(min_lon, min_lat, max_lon, max_lat)
        area_km2 = self.compute_spherical_area_km2(poly)
        return FootprintResult(
            polygon=poly,
            bounds=poly.bounds,
            area_km2=area_km2,
            crs_name="Lunar Selenographic (lon, lat)",
            is_valid=True,
        )
