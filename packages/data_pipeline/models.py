"""Data models and schemas for lunar observations, metadata, and queries."""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator, model_validator


class SensorType(str, Enum):
    OHRC = "OHRC"          # Chandrayaan-2 Orbiter High Resolution Camera (~0.25m)
    TMC2 = "TMC2"          # Chandrayaan-2 Terrain Mapping Camera-2 (~5m)
    IIRS = "IIRS"          # Chandrayaan-2 Imaging Infrared Spectrometer (~80m, 256 bands)
    LRO_NAC = "LRO_NAC"    # LRO Narrow Angle Camera (~0.5 - 2m)
    SELENE_TC = "SELENE_TC"# SELENE (Kaguya) Terrain Camera (~10m)
    SELENE_MI = "SELENE_MI"# SELENE Multiband Imager (~20m)


class MissionType(str, Enum):
    CHANDRAYAAN2 = "CHANDRAYAAN-2"
    LRO = "LRO"
    SELENE = "SELENE"


class BoundingBox(BaseModel):
    min_lat: float = Field(..., ge=-90.0, le=90.0, description="Minimum latitude in degrees (-90 to 90)")
    max_lat: float = Field(..., ge=-90.0, le=90.0, description="Maximum latitude in degrees (-90 to 90)")
    min_lon: float = Field(..., ge=-180.0, le=360.0, description="Minimum longitude in degrees (-180 to 180 or 0 to 360)")
    max_lon: float = Field(..., ge=-180.0, le=360.0, description="Maximum longitude in degrees (-180 to 180 or 0 to 360)")

    @model_validator(mode="after")
    def validate_bounds_order(self) -> "BoundingBox":
        if self.min_lat > self.max_lat:
            raise ValueError(f"Inverted latitude bounds: min_lat ({self.min_lat}) > max_lat ({self.max_lat})")
        if self.min_lon > self.max_lon:
            raise ValueError(f"Inverted longitude bounds: min_lon ({self.min_lon}) > max_lon ({self.max_lon})")
        return self

    @property
    def center(self) -> Tuple[float, float]:
        """Returns (center_lat, center_lon)."""
        return ((self.min_lat + self.max_lat) / 2.0, (self.min_lon + self.max_lon) / 2.0)

    @property
    def polygon_coords(self) -> List[Tuple[float, float]]:
        """Returns list of (lon, lat) closed coordinates for polygon construction."""
        return [
            (self.min_lon, self.min_lat),
            (self.max_lon, self.min_lat),
            (self.max_lon, self.max_lat),
            (self.min_lon, self.max_lat),
            (self.min_lon, self.min_lat),
        ]


class ObservationGeometry(BaseModel):
    solar_zenith_deg: Optional[float] = None
    solar_azimuth_deg: Optional[float] = None
    incidence_angle_deg: Optional[float] = None
    emission_angle_deg: Optional[float] = None
    phase_angle_deg: Optional[float] = None
    sub_solar_lat: Optional[float] = None
    sub_solar_lon: Optional[float] = None
    spacecraft_altitude_km: Optional[float] = None


class LunarObservation(BaseModel):
    product_id: str = Field(..., min_length=1, description="Unique product identifier (e.g. ch2_ohr_ncp_..., M1144485705LR)")
    mission: MissionType
    sensor: SensorType
    acquisition_time: Optional[datetime] = None
    spatial_resolution_m: Optional[float] = None
    crs: str = "Moon 2000 (IAU2000:30100)"
    bbox: BoundingBox
    footprint_polygon: Optional[List[Tuple[float, float]]] = Field(
        default=None, description="Detailed (lon, lat) polygon boundary coordinates"
    )
    geometry: ObservationGeometry = Field(default_factory=ObservationGeometry)

    @field_validator("spatial_resolution_m")
    @classmethod
    def validate_positive_resolution(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError(f"Spatial resolution must be positive, got {v}")
        return v

    @field_validator("product_id")
    @classmethod
    def validate_non_empty_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("product_id cannot be empty or whitespace only")
        return v.strip()
    
    # File locations
    primary_image_path: Optional[str] = None
    label_path: Optional[str] = None
    preview_image_path: Optional[str] = None
    auxiliary_files: List[str] = Field(default_factory=list)
    
    # Remote source references
    source_url: Optional[str] = None
    download_urls: Dict[str, str] = Field(default_factory=dict)
    
    # Additional raw metadata
    extra_metadata: Dict[str, Any] = Field(default_factory=dict)
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product_id,
            "mission": self.mission.value,
            "sensor": self.sensor.value,
            "acquisition_time": self.acquisition_time.isoformat() if self.acquisition_time else None,
            "resolution_m": self.spatial_resolution_m,
            "bbox": self.bbox.model_dump(),
            "center": self.bbox.center,
            "primary_image": self.primary_image_path,
            "preview_image": self.preview_image_path,
            "incidence_angle": self.geometry.incidence_angle_deg,
            "solar_azimuth": self.geometry.solar_azimuth_deg,
        }


class CatalogQuery(BaseModel):
    sensors: Optional[List[SensorType]] = None
    bbox: Optional[BoundingBox] = None
    min_resolution_m: Optional[float] = None
    max_resolution_m: Optional[float] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = 50


class ResolutionStrategy(str, Enum):
    MATCH_COARSER = "match_coarser"    # Resample higher-res to match lower-res (recommended for feature stability)
    MATCH_FINER = "match_finer"        # Upsample lower-res to match higher-res
    NATIVE_PHYSICAL = "native_physical"  # Maintain native pixel GSD; patch dimensions in pixels will differ proportionally


class PixelBox(BaseModel):
    x: int = Field(..., description="Top-left X pixel coordinate")
    y: int = Field(..., description="Top-left Y pixel coordinate")
    width: int = Field(..., description="Width in pixels")
    height: int = Field(..., description="Height in pixels")

    @property
    def bounds(self) -> Tuple[int, int, int, int]:
        """Returns (min_x, min_y, max_x, max_y)."""
        return (self.x, self.y, self.x + self.width, self.y + self.height)


class PatchExtractionConfig(BaseModel):
    patch_size: int = Field(512, description="Square patch dimension in pixels (or target size)")
    stride: Optional[int] = Field(None, description="Sliding window stride in pixels (defaults to patch_size)")
    min_overlap_pct: float = Field(5.0, description="Minimum ground overlap percentage required")
    resolution_strategy: ResolutionStrategy = Field(
        ResolutionStrategy.MATCH_COARSER, description="Strategy for handling differing spatial resolutions"
    )
    target_resolution_m: Optional[float] = Field(None, description="Explicit target GSD in meters (overrides strategy)")
    output_format: str = Field("png", description="Image format for extracted patches (png or tif)")


class ExtractedPatchPair(BaseModel):
    pair_id: str
    patch_index: int
    source_product_id: str
    reference_product_id: str
    source_patch_path: str
    reference_patch_path: str
    ground_bbox: BoundingBox
    source_pixel_box: PixelBox
    reference_pixel_box: PixelBox
    effective_resolution_m: float
    overlap_pct: float
    solar_incidence_diff_deg: Optional[float] = None
    quality_score: float = Field(..., description="Composite quality/confidence score (0.0 to 1.0)")


class PatchManifest(BaseModel):
    source_product_id: str
    reference_product_id: str
    total_patches: int
    intersection_bbox: BoundingBox
    intersection_polygon: Optional[List[Tuple[float, float]]] = None
    intersection_area_km2: float
    config: PatchExtractionConfig
    patches: List[ExtractedPatchPair] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

