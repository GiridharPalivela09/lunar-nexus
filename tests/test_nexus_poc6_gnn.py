import sys
from pathlib import Path
import pytest
torch = pytest.importorskip("torch")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.nexus_core.poc1_knowledge_graph import (
    build_boguslawsky_knowledge_graph,
)
from packages.nexus_core.poc6_gnn_reasoner import (
    GNNSpatialReasoner,
    GraphSAGELayer,
    LunarGraphSAGENetwork,
)


def test_graphsage_layer_forward():
    """Verify GraphSAGE forward pass and tensor dimensions."""
    in_dim, out_dim = 8, 16
    layer = GraphSAGELayer(in_dim, out_dim)

    # Batch of 5 nodes
    x = torch.randn(5, in_dim)
    adj = torch.eye(5)
    out = layer(x, adj)

    assert out.shape == (5, out_dim)
    # Output should be non-negative due to ReLU
    assert torch.all(out >= 0.0)


def test_lunar_graphsage_network_output():
    """Verify 2-layer GraphSAGE network produces embeddings and predictions in [0, 1]."""
    net = LunarGraphSAGENetwork(in_dim=8, hidden_dim=16, embedding_dim=16)
    x = torch.rand(10, 8)
    adj = torch.eye(10)

    embeddings, preds = net(x, adj)
    assert embeddings.shape == (10, 16)
    assert preds.shape == (10, 1)
    assert torch.all(preds >= 0.0) and torch.all(preds <= 1.0)


def test_gnn_reasoner_on_boguslawsky_graph():
    """Verify end-to-end GNN feature extraction, training convergence, and site inference."""
    skg = build_boguslawsky_knowledge_graph()
    reasoner = GNNSpatialReasoner(skg, hidden_dim=16, seed=42)

    assert reasoner.x.shape[0] == skg.num_nodes
    assert reasoner.x.shape[1] == 8
    assert reasoner.adj_norm.shape == (skg.num_nodes, skg.num_nodes)

    # Train for 30 epochs
    initial_loss = reasoner.train_inductive_predictor(epochs=5, lr=0.01)
    converged_loss = reasoner.train_inductive_predictor(epochs=30, lr=0.01)
    assert converged_loss <= initial_loss or converged_loss < 0.2

    # Infer predictions for candidate sites
    inferences = reasoner.infer_site_suitabilities()
    assert "site_candidate_01_north_rim" in inferences
    assert "site_candidate_02_floor" in inferences

    site1 = inferences["site_candidate_01_north_rim"]
    site2 = inferences["site_candidate_02_floor"]

    assert 0.0 <= site1["gnn_suitability_score"] <= 100.0
    assert 0.0 <= site2["gnn_suitability_score"] <= 100.0
    assert len(site1["embedding_vector"]) > 0
