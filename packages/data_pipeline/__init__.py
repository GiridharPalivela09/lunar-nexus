"""NEXUS-LUNAR Data Acquisition and Ingestion Pipeline.

Provides automated downloaders, parsers, and catalog indexing for:
- Chandrayaan-2 (OHRC, TMC-2, IIRS)
- LRO NAC (Lunar Reconnaissance Orbiter Narrow Angle Camera)
- SELENE / Kaguya (TC / MI)
"""

from .models import (
    SensorType,
    MissionType,
    BoundingBox,
    ObservationGeometry,
    LunarObservation,
    CatalogQuery,
    ResolutionStrategy,
    PixelBox,
    PatchExtractionConfig,
    ExtractedPatchPair,
    PatchManifest,
)
from .pds_ode_client import PDSODEClient
from .issdc_client import ISSDCClient
from .metadata_parser import MetadataParser
from .catalog import LunarDataCatalog
from .patch_extractor import (
    GeoPixelTransformer,
    ResolutionHarmonizer,
    OverlapQualityScorer,
    OverlapPatchExtractor,
)
from .footprint_engine import (
    FootprintEngine,
    FootprintResult,
    LUNAR_GEOGRAPHIC_PROJ4,
    LUNAR_SOUTH_POLE_STEREO_PROJ4,
    LUNAR_RADIUS_M,
)
from .overlap_engine import (
    OverlapEngine,
    OverlapAnalysisResult,
    calculate_overlap,
    find_overlapping_reference_tiles,
)
from .visualization import (
    generate_overlap_visualization,
    generate_patch_comparison_visualization,
)
from .illumination_robustness import (
    generate_raw_image,
    generate_normalized_image,
    generate_gradient_image,
    generate_edge_image,
    generate_illumination_normalized_image,
    generate_shadow_mask,
    apply_synthetic_illumination_perturbation,
)
from .scale_robustness import (
    PyramidLevel,
    calculate_gsd_ratio,
    resample_to_gsd,
    build_image_pyramid,
    build_multiscale_representation_dict,
    apply_synthetic_scale_perturbation,
)
from .poc4_matching import (
    Keypoint,
    KeypointMatch,
    RegistrationResult,
    detect_keypoints,
    extract_descriptors,
    match_features,
    estimate_affine_ransac,
    run_classical_registration,
)
from .poc4_metrics import (
    calculate_recall_at_k,
    calculate_inlier_ratio,
    calculate_registration_rmse,
    calculate_alignment_success,
    calculate_improvement_deltas,
    FailureCaseTracker,
)
from .poc4_experiment import (
    POC4ExperimentRunner,
)
from .poc4_visualization import (
    generate_illumination_comparison_figure,
    generate_scale_pyramid_figure,
    generate_registration_comparison_figure,
    generate_metrics_comparison_figure,
    generate_illumination_scale_heatmap_figure,
    generate_ablation_results_figure,
)

from .poc5_dataset import (
    LunarPatchSample,
    PatchPairSample,
    LunarCorrespondenceDataset,
    PyTorchLunarPairDataset,
)
from .poc5_model import (
    TwoTowerCorrespondenceModel,
    VisionTowerEncoder,
    MetadataConditioningMLP,
    ConvBlock,
)
from .poc5_training import (
    ContrastiveCosineLoss,
    POC5TwoTowerTrainer,
)
from .poc5_retrieval import (
    CrossSensorRetrievalEngine,
    RetrievedCandidate,
    QueryRetrievalResult,
)
from .poc5_metrics import (
    evaluate_retrieval_performance,
)
from .poc5_visualization import (
    plot_architecture_diagram,
    plot_retrieval_ranking_grid,
    plot_embedding_clusters,
    plot_recall_at_k_curve,
    plot_similarity_distribution,
)

__all__ = [
    "SensorType",
    "MissionType",
    "BoundingBox",
    "ObservationGeometry",
    "LunarObservation",
    "CatalogQuery",
    "ResolutionStrategy",
    "PixelBox",
    "PatchExtractionConfig",
    "ExtractedPatchPair",
    "PatchManifest",
    "PDSODEClient",
    "ISSDCClient",
    "MetadataParser",
    "LunarDataCatalog",
    "GeoPixelTransformer",
    "ResolutionHarmonizer",
    "OverlapQualityScorer",
    "OverlapPatchExtractor",
    "FootprintEngine",
    "FootprintResult",
    "LUNAR_GEOGRAPHIC_PROJ4",
    "LUNAR_SOUTH_POLE_STEREO_PROJ4",
    "OverlapEngine",
    "OverlapAnalysisResult",
    "calculate_overlap",
    "find_overlapping_reference_tiles",
    "generate_overlap_visualization",
    "generate_patch_comparison_visualization",
    # POC-4 Illumination & Scale Robustness
    "generate_raw_image",
    "generate_normalized_image",
    "generate_gradient_image",
    "generate_edge_image",
    "generate_illumination_normalized_image",
    "generate_shadow_mask",
    "apply_synthetic_illumination_perturbation",
    "PyramidLevel",
    "calculate_gsd_ratio",
    "resample_to_gsd",
    "build_image_pyramid",
    "build_multiscale_representation_dict",
    "apply_synthetic_scale_perturbation",
    "Keypoint",
    "KeypointMatch",
    "RegistrationResult",
    "detect_keypoints",
    "extract_descriptors",
    "match_features",
    "estimate_affine_ransac",
    "run_classical_registration",
    "calculate_recall_at_k",
    "calculate_inlier_ratio",
    "calculate_registration_rmse",
    "calculate_alignment_success",
    "calculate_improvement_deltas",
    "FailureCaseTracker",
    "POC4ExperimentRunner",
    "generate_illumination_comparison_figure",
    "generate_scale_pyramid_figure",
    "generate_registration_comparison_figure",
    "generate_metrics_comparison_figure",
    "generate_illumination_scale_heatmap_figure",
    "generate_ablation_results_figure",
    # POC-5 Multimodal AI Correspondence
    "LunarPatchSample",
    "PatchPairSample",
    "LunarCorrespondenceDataset",
    "PyTorchLunarPairDataset",
    "TwoTowerCorrespondenceModel",
    "VisionTowerEncoder",
    "MetadataConditioningMLP",
    "ConvBlock",
    "ContrastiveCosineLoss",
    "POC5TwoTowerTrainer",
    "CrossSensorRetrievalEngine",
    "RetrievedCandidate",
    "QueryRetrievalResult",
    "evaluate_retrieval_performance",
    "plot_architecture_diagram",
    "plot_retrieval_ranking_grid",
    "plot_embedding_clusters",
    "plot_recall_at_k_curve",
    "plot_similarity_distribution",
]


