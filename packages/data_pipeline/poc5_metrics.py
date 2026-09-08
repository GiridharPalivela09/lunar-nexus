"""NEXUS-LUNAR POC-5: Retrieval Evaluation Metrics & Ground-Truth Verification.

Calculates Recall@1, Recall@5, Recall@10, Mean Reciprocal Rank (MRR),
embedding similarity distributions, and statistical performance summaries across query trials.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
import numpy as np

from .poc5_retrieval import QueryRetrievalResult


def evaluate_retrieval_performance(
    query_results: List[QueryRetrievalResult],
) -> Dict[str, Any]:
    """Calculates comprehensive cross-modal retrieval performance metrics."""
    if not query_results:
        return {
            "total_queries": 0,
            "recall_at_1": 0.0,
            "recall_at_5": 0.0,
            "recall_at_10": 0.0,
            "mean_reciprocal_rank": 0.0,
            "mean_processing_time_ms": 0.0,
            "ranks": [],
        }

    n = len(query_results)
    r1_list = [res.recall_at_1 for res in query_results]
    r5_list = [res.recall_at_5 for res in query_results]
    r10_list = [res.recall_at_10 for res in query_results]
    mrr_list = [res.reciprocal_rank for res in query_results]
    time_list = [res.processing_time_ms for res in query_results]
    ranks = [res.true_match_rank for res in query_results if res.true_match_rank is not None]

    pos_sims = []
    neg_sims = []
    for q in query_results:
        for c in q.retrieved_candidates:
            if c.is_ground_truth:
                pos_sims.append(c.cosine_similarity)
            else:
                neg_sims.append(c.cosine_similarity)

    mean_pos = float(np.mean(pos_sims)) if pos_sims else 0.0
    mean_neg = float(np.mean(neg_sims)) if neg_sims else 0.0

    return {
        "total_queries_evaluated": int(n),
        "recall_at_1": round(float(np.mean(r1_list)), 4),
        "recall_at_5": round(float(np.mean(r5_list)), 4),
        "recall_at_10": round(float(np.mean(r10_list)), 4),
        "mean_reciprocal_rank": round(float(np.mean(mrr_list)), 4),
        "mean_processing_time_ms": round(float(np.mean(time_list)), 2),
        "mean_positive_similarity": round(mean_pos, 4),
        "mean_negative_similarity": round(mean_neg, 4),
        "embedding_separation_margin": round(float(mean_pos - mean_neg), 4),
        "median_rank": float(np.median(ranks)) if ranks else 999.0,
        "ground_truth_discovery_rate": round(float(len(ranks) / n), 4),
    }
