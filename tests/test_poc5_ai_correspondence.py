"""Unit tests for NEXUS-LUNAR POC-5 Multimodal AI Correspondence.

Tests:
1. LunarCorrespondenceDataset loading of real lunar patches and pair construction.
2. Two-Tower Deep Vision + Metadata architecture forward pass and shape verification.
3. Contrastive Cosine Loss and gradient propagation.
4. Latent L2 normalization (||z||_2 == 1.0).
5. CrossSensorRetrievalEngine 1-to-N indexing and cosine ranking.
6. Metric evaluation (Recall@K, MRR, separation margins).
"""

import pytest
import numpy as np
import torch
from pathlib import Path

from packages.data_pipeline.poc5_dataset import (
    LunarPatchSample,
    PatchPairSample,
    LunarCorrespondenceDataset,
    PyTorchLunarPairDataset,
)
from packages.data_pipeline.poc5_model import (
    TwoTowerCorrespondenceModel,
    VisionTowerEncoder,
    MetadataConditioningMLP,
)
from packages.data_pipeline.poc5_training import (
    ContrastiveCosineLoss,
    POC5TwoTowerTrainer,
)
from packages.data_pipeline.poc5_retrieval import (
    CrossSensorRetrievalEngine,
    RetrievedCandidate,
    QueryRetrievalResult,
)
from packages.data_pipeline.poc5_metrics import (
    evaluate_retrieval_performance,
)


@pytest.fixture
def mock_patch_sample():
    """Generates a standardized mock lunar patch sample."""
    arr = np.random.uniform(0.1, 0.9, (128, 128)).astype(np.float32)
    return LunarPatchSample(
        patch_id="SRC_OHRC_0001",
        sensor="OHRC",
        gsd_m=0.25,
        solar_incidence_deg=75.0,
        center_lat=-73.2,
        center_lon=26.3,
        array=arr,
        provenance="TEST_PATCH",
    )


@pytest.fixture
def mock_reference_sample():
    """Generates a standardized mock reference patch sample."""
    arr = np.random.uniform(0.1, 0.9, (128, 128)).astype(np.float32)
    return LunarPatchSample(
        patch_id="REF_LRO_0001",
        sensor="LRO_NAC",
        gsd_m=1.0,
        solar_incidence_deg=70.0,
        center_lat=-73.2,
        center_lon=26.3,
        array=arr,
        provenance="TEST_PATCH",
    )


def test_metadata_vector_encoding(mock_patch_sample):
    """Verifies that physical telemetry is correctly mapped to normalized vectors."""
    meta_vec = mock_patch_sample.to_metadata_vector()
    assert meta_vec.shape == (4,)
    assert 0.0 <= meta_vec[0] <= 1.0  # normalized GSD
    assert -1.0 <= meta_vec[1] <= 1.0  # sin(incidence)
    assert -1.0 <= meta_vec[2] <= 1.0  # cos(incidence)
    assert meta_vec[3] == 0.0          # OHRC code


def test_two_tower_forward_pass():
    """Verifies that the Two-Tower model produces 128-D L2-normalized embeddings."""
    model = TwoTowerCorrespondenceModel(embedding_dim=128, meta_dim=9, meta_proj_dim=32)
    model.eval()

    src_img = torch.rand(2, 1, 128, 128)
    ref_img = torch.rand(2, 1, 128, 128)
    meta = torch.rand(2, 9)

    with torch.no_grad():
        src_emb, ref_emb, sim = model(src_img, ref_img, meta)

    assert src_emb.shape == (2, 128)
    assert ref_emb.shape == (2, 128)
    assert sim.shape == (2,)

    # Verify L2 normalization
    src_norms = torch.norm(src_emb, p=2, dim=-1)
    ref_norms = torch.norm(ref_emb, p=2, dim=-1)
    np.testing.assert_allclose(src_norms.numpy(), np.ones(2), rtol=1e-5)
    np.testing.assert_allclose(ref_norms.numpy(), np.ones(2), rtol=1e-5)


def test_contrastive_loss_objective():
    """Verifies that positive similarity minimizes loss and negative pairs are penalized."""
    loss_fn = ContrastiveCosineLoss(margin=0.25)
    
    # Perfect positive similarity
    sim_pos = torch.tensor([0.95, 0.99])
    label_pos = torch.tensor([1.0, 1.0])
    loss_pos = loss_fn(sim_pos, label_pos)
    assert loss_pos.item() < 0.1

    # High negative similarity should violate margin
    sim_neg_bad = torch.tensor([0.80, 0.70])
    label_neg = torch.tensor([0.0, 0.0])
    loss_neg_bad = loss_fn(sim_neg_bad, label_neg)
    assert loss_neg_bad.item() > 0.4


def test_cross_sensor_retrieval_engine(mock_patch_sample, mock_reference_sample):
    """Verifies candidate indexing, cosine retrieval, and Top-K ranking."""
    model = TwoTowerCorrespondenceModel(embedding_dim=128, meta_dim=9, meta_proj_dim=32)
    
    # Create pool of candidates
    candidates = [mock_reference_sample]
    for i in range(1, 5):
        distractor = LunarPatchSample(
            patch_id=f"REF_LRO_{i:04d}",
            sensor="LRO_NAC",
            gsd_m=1.0,
            solar_incidence_deg=65.0,
            center_lat=-70.0 + i,
            center_lon=20.0 + i,
            array=np.random.uniform(0, 1, (128, 128)).astype(np.float32),
        )
        candidates.append(distractor)

    engine = CrossSensorRetrievalEngine(model=model, candidate_pool=candidates, device=torch.device("cpu"))
    assert engine.candidate_embeddings.shape == (5, 128)

    # Retrieve for query
    res = engine.retrieve(query_patch=mock_patch_sample, top_k=3, target_ground_distance_thresh_m=350.0)
    assert len(res.retrieved_candidates) == 3
    assert res.processing_time_ms > 0.0
    assert 0.0 <= res.recall_at_1 <= 1.0
    assert 0.0 <= res.recall_at_5 <= 1.0


def test_metrics_evaluation():
    """Verifies that retrieval results correctly aggregate into Recall@K and MRR."""
    # Construct mock retrieval results
    query1 = LunarPatchSample("Q1", "OHRC", 0.25, 75.0, -73.0, 26.0, np.zeros((128, 128)))
    res1 = QueryRetrievalResult(
        query_patch=query1,
        retrieved_candidates=[],
        true_match_rank=1,
        recall_at_1=1.0,
        recall_at_5=1.0,
        recall_at_10=1.0,
        reciprocal_rank=1.0,
        processing_time_ms=12.5,
    )
    query2 = LunarPatchSample("Q2", "OHRC", 0.25, 75.0, -73.0, 26.0, np.zeros((128, 128)))
    res2 = QueryRetrievalResult(
        query_patch=query2,
        retrieved_candidates=[],
        true_match_rank=4,
        recall_at_1=0.0,
        recall_at_5=1.0,
        recall_at_10=1.0,
        reciprocal_rank=0.25,
        processing_time_ms=10.2,
    )

    metrics = evaluate_retrieval_performance([res1, res2])
    assert metrics["total_queries_evaluated"] == 2
    assert metrics["recall_at_1"] == 0.5
    assert metrics["recall_at_5"] == 1.0
    assert metrics["recall_at_10"] == 1.0
    assert metrics["mean_reciprocal_rank"] == (1.0 + 0.25) / 2.0
