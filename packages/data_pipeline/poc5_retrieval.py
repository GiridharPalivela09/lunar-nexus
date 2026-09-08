"""NEXUS-LUNAR POC-5: 1-to-N Cross-Sensor Patch Retrieval Engine.

Projects query observation patches (Chandrayaan-2 OHRC/TMC-2) into the shared 128-D embedding space,
ranks all candidate reconnaissance patches (NASA LROC NAC) by cosine similarity, and evaluates
spatial correspondence against known ground-truth coordinates.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import torch
import torch.nn.functional as F

from .poc5_dataset import LunarPatchSample, LunarCorrespondenceDataset
from .poc5_model import TwoTowerCorrespondenceModel


@dataclass
class RetrievedCandidate:
    """Represents a single ranked candidate patch retrieved for a query."""
    rank: int
    candidate_patch: LunarPatchSample
    cosine_similarity: float
    is_ground_truth: bool
    ground_distance_m: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": int(self.rank),
            "candidate_patch_id": str(self.candidate_patch.patch_id),
            "sensor": str(self.candidate_patch.sensor),
            "gsd_m": float(self.candidate_patch.gsd_m),
            "cosine_similarity": round(float(self.cosine_similarity), 4),
            "is_ground_truth": bool(self.is_ground_truth),
            "ground_distance_m": round(float(self.ground_distance_m), 1),
            "source_file": str(self.candidate_patch.source_file),
        }


@dataclass
class QueryRetrievalResult:
    """Represents the complete retrieval output for a single query patch."""
    query_patch: LunarPatchSample
    retrieved_candidates: List[RetrievedCandidate]
    true_match_rank: Optional[int]
    recall_at_1: float
    recall_at_5: float
    recall_at_10: float
    reciprocal_rank: float
    processing_time_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_patch_id": str(self.query_patch.patch_id),
            "query_sensor": str(self.query_patch.sensor),
            "query_gsd_m": float(self.query_patch.gsd_m),
            "true_match_rank": int(self.true_match_rank) if self.true_match_rank is not None else None,
            "recall_at_1": float(self.recall_at_1),
            "recall_at_5": float(self.recall_at_5),
            "recall_at_10": float(self.recall_at_10),
            "reciprocal_rank": round(float(self.reciprocal_rank), 4),
            "processing_time_ms": round(float(self.processing_time_ms), 2),
            "candidates": [c.to_dict() for c in self.retrieved_candidates],
        }


class CrossSensorRetrievalEngine:
    """Executes fast nearest-neighbor embedding retrieval across heterogeneous sensor patches."""

    def __init__(
        self,
        model: TwoTowerCorrespondenceModel,
        candidate_pool: List[LunarPatchSample],
        device: Optional[torch.device] = None,
    ):
        self.device = device or (torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu"))
        self.model = model.to(self.device).eval()
        self.candidate_pool = candidate_pool
        self.candidate_embeddings: Optional[torch.Tensor] = None
        self._index_candidates()

    def _index_candidates(self) -> None:
        """Pre-computes and indexes 128-D embeddings for all candidate reference patches."""
        if not self.candidate_pool:
            return

        embeddings_list = []
        with torch.no_grad():
            for ref_patch in self.candidate_pool:
                ref_t = torch.from_numpy(ref_patch.array).unsqueeze(0).unsqueeze(0).float().to(self.device)
                
                # Symmetrical Conditioning vector matching training: [meta(4), meta(4), ratio(1)]
                r_meta = ref_patch.to_metadata_vector()
                meta_vec = np.concatenate([r_meta, r_meta, np.array([4.0 / 5.0], dtype=np.float32)])
                meta_t = torch.from_numpy(meta_vec).unsqueeze(0).float().to(self.device)

                emb = self.model.encode_reference(ref_t, meta_t)
                embeddings_list.append(emb)

        self.candidate_embeddings = torch.cat(embeddings_list, dim=0)  # (N_candidates, 128)

    def retrieve(
        self,
        query_patch: LunarPatchSample,
        top_k: int = 5,
        target_ground_distance_thresh_m: float = 350.0,
    ) -> QueryRetrievalResult:
        """Retrieves top-K candidate matches for a source query patch."""
        import time
        start = time.perf_counter()

        with torch.no_grad():
            src_t = torch.from_numpy(query_patch.array).unsqueeze(0).unsqueeze(0).float().to(self.device)
            s_meta = query_patch.to_metadata_vector()
            meta_vec = np.concatenate([s_meta, s_meta, np.array([4.0 / 5.0], dtype=np.float32)])
            meta_t = torch.from_numpy(meta_vec).unsqueeze(0).float().to(self.device)

            query_emb = self.model.encode_source(src_t, meta_t)  # (1, 128)

            # Cosine similarity against all candidate embeddings: (1, 128) @ (N, 128)^T -> (N,)
            sims = torch.matmul(query_emb, self.candidate_embeddings.T).squeeze(0).cpu().numpy()

        # Sort descending
        sorted_indices = np.argsort(-sims)
        retrieved: List[RetrievedCandidate] = []
        true_match_rank: Optional[int] = None

        for rank_idx, cand_idx in enumerate(sorted_indices):
            cand = self.candidate_pool[cand_idx]
            sim_score = float(sims[cand_idx])

            # Ground truth verification based on geographic physical distance
            d_lat = (query_patch.center_lat - cand.center_lat) * 30300.0
            d_lon = (query_patch.center_lon - cand.center_lon) * 30300.0 * np.cos(np.radians(query_patch.center_lat))
            dist_m = float(np.sqrt(d_lat ** 2 + d_lon ** 2))
            is_gt = dist_m <= target_ground_distance_thresh_m

            if is_gt and true_match_rank is None:
                true_match_rank = rank_idx + 1

            if rank_idx < top_k:
                retrieved.append(
                    RetrievedCandidate(
                        rank=rank_idx + 1,
                        candidate_patch=cand,
                        cosine_similarity=sim_score,
                        is_ground_truth=is_gt,
                        ground_distance_m=dist_m,
                    )
                )

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        
        # Metrics
        r1 = 1.0 if (true_match_rank is not None and true_match_rank <= 1) else 0.0
        r5 = 1.0 if (true_match_rank is not None and true_match_rank <= 5) else 0.0
        r10 = 1.0 if (true_match_rank is not None and true_match_rank <= 10) else 0.0
        mrr = (1.0 / float(true_match_rank)) if true_match_rank is not None else 0.0

        return QueryRetrievalResult(
            query_patch=query_patch,
            retrieved_candidates=retrieved,
            true_match_rank=true_match_rank,
            recall_at_1=r1,
            recall_at_5=r5,
            recall_at_10=r10,
            reciprocal_rank=mrr,
            processing_time_ms=elapsed_ms,
        )
