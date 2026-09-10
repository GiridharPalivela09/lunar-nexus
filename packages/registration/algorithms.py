"""Classical Feature Detection and Descriptor Extraction (SIFT, RootSIFT, ORB, AKAZE)."""

from __future__ import annotations
from enum import Enum
from typing import Tuple, List, Optional
import numpy as np
import cv2


class FeatureMethod(str, Enum):
    SIFT = "SIFT"
    ROOT_SIFT = "RootSIFT"
    ORB = "ORB"
    AKAZE = "AKAZE"
    PHASE_CORRELATION = "PhaseCorrelation"


def apply_rootsift_normalization(descriptors: np.ndarray, eps: float = 1e-7) -> np.ndarray:
    """Applies L1 square-root normalization (Hellinger kernel) to SIFT descriptors.
    
    Arandjelović and Zisserman (CVPR 2012):
    Using Euclidean distance on RootSIFT corresponds to Hellinger distance on SIFT,
    significantly improving correspondence accuracy on planetary surface textures.
    """
    if descriptors is None or len(descriptors) == 0:
        return descriptors
    
    # 1. L1 normalization per descriptor row
    l1_norm = np.sum(np.abs(descriptors), axis=1, keepdims=True)
    descriptors_l1 = descriptors / (l1_norm + eps)
    
    # 2. Element-wise square root
    root_descriptors = np.sqrt(np.maximum(descriptors_l1, 0.0))
    
    # 3. L2 re-normalization for unit sphere distance
    l2_norm = np.linalg.norm(root_descriptors, axis=1, keepdims=True)
    return root_descriptors / (l2_norm + eps)


def extract_features(
    image: np.ndarray,
    method: FeatureMethod = FeatureMethod.SIFT,
    max_keypoints: int = 5000,
    max_features: Optional[int] = None,
) -> Tuple[List[cv2.KeyPoint], Optional[np.ndarray]]:
    """Extracts keypoints and descriptors from a grayscale or RGB image.
    
    Returns:
        (keypoints, descriptors)
    """
    if max_features is not None:
        max_keypoints = max_features
    if image is None:
        raise ValueError("Image array cannot be None")
        
    # Convert to single-channel 8-bit grayscale if color
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY if image.shape[2] == 3 else cv2.COLOR_BGRA2GRAY)
    else:
        gray = image.copy()
        
    if gray.dtype != np.uint8:
        # Normalize to 0..255 uint8
        norm = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
        gray = norm.astype(np.uint8)

    if method == FeatureMethod.SIFT or method == FeatureMethod.ROOT_SIFT:
        sift = cv2.SIFT_create(nfeatures=max_keypoints, contrastThreshold=0.01, edgeThreshold=10)
        keypoints, descriptors = sift.detectAndCompute(gray, None)
        if keypoints is None or len(keypoints) < 15:
            sift_fallback = cv2.SIFT_create(nfeatures=max_keypoints, contrastThreshold=0.005, edgeThreshold=10)
            keypoints, descriptors = sift_fallback.detectAndCompute(gray, None)
        if method == FeatureMethod.ROOT_SIFT and descriptors is not None:
            descriptors = apply_rootsift_normalization(descriptors)
        return keypoints, descriptors

    elif method == FeatureMethod.ORB:
        orb = cv2.ORB_create(
            nfeatures=max_keypoints,
            scaleFactor=1.2,
            nlevels=8,
            edgeThreshold=15,
            fastThreshold=12,
        )
        keypoints, descriptors = orb.detectAndCompute(gray, None)
        return keypoints, descriptors

    elif method == FeatureMethod.AKAZE:
        if hasattr(cv2, "AKAZE_create") or (hasattr(cv2, "AKAZE") and hasattr(cv2.AKAZE, "create")):
            create_fn = cv2.AKAZE_create if hasattr(cv2, "AKAZE_create") else cv2.AKAZE.create
            # Try initial threshold suited for subtle lunar surface texture
            akaze = create_fn(threshold=0.0002)
            keypoints, descriptors = akaze.detectAndCompute(gray, None)
            if not keypoints or len(keypoints) < 50:
                akaze = create_fn(threshold=0.00005)
                keypoints, descriptors = akaze.detectAndCompute(gray, None)
        else:
            # Fallback for OpenCV builds without AKAZE: GFTT + SIFT descriptor
            gftt = cv2.GFTTDetector_create(maxCorners=max_keypoints, qualityLevel=0.01, minDistance=3)
            keypoints = gftt.detect(gray, None)
            sift = cv2.SIFT_create()
            keypoints, descriptors = sift.compute(gray, keypoints)
        return keypoints, descriptors

    elif method == FeatureMethod.PHASE_CORRELATION:
        # Phase correlation does not extract local sparse keypoints
        return [], None

    else:
        raise ValueError(f"Unsupported feature extraction method: {method}")
