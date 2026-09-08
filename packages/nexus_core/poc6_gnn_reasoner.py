"""NEXUS POC 6: Graph Neural Network (GNN) Spatial Reasoner.

Implements inductive GraphSAGE (Hamilton et al., 2017) over the Lunar Spatial
Knowledge Graph:
- Neighborhood aggregation of heterogeneous spatial relationships (Craters, Hazards, Observations, Terrain)
- Inductive node embedding extraction
- Multi-objective site suitability prediction head
- Transparent training & evaluation against ground truth engineering heuristics
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from packages.nexus_core.poc1_knowledge_graph import (
    LunarSpatialKnowledgeGraph,
    NodeType,
)

logger = logging.getLogger(__name__)


class GraphSAGELayer(nn.Module):
    """Mean-aggregation GraphSAGE layer for inductive representation learning."""

    def __init__(self, in_features: int, out_features: int, bias: bool = True):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        # Linear layer for concatenated [self_feat || neighbor_mean]
        self.weight = nn.Linear(in_features * 2, out_features, bias=bias)

    def forward(self, x: torch.Tensor, adj_norm: torch.Tensor) -> torch.Tensor:
        """Args:

        x: Node feature tensor (N, in_features).
        adj_norm: Normalized adjacency matrix (N, N) with self-loops.
        """
        # Aggregate neighbor representations: (N, N) x (N, in_features) -> (N, in_features)
        neighbor_agg = torch.matmul(adj_norm, x)

        # Concatenate self features with aggregated neighbor features
        combined = torch.cat([x, neighbor_agg], dim=-1)

        # Apply transformation and ReLU non-linearity
        out = self.weight(combined)
        return F.relu(out)


class LunarGraphSAGENetwork(nn.Module):
    """2-layer GraphSAGE model with inductive suitability predictor head."""

    def __init__(
        self,
        in_dim: int = 8,
        hidden_dim: int = 16,
        embedding_dim: int = 16,
    ):
        super().__init__()
        self.sage1 = GraphSAGELayer(in_dim, hidden_dim)
        self.sage2 = GraphSAGELayer(hidden_dim, embedding_dim)

        # Predictor head: Maps node embedding to site suitability [0.0, 1.0]
        self.predictor = nn.Sequential(
            nn.Linear(embedding_dim, 8),
            nn.ReLU(),
            nn.Linear(8, 1),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor, adj_norm: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """Returns:

        embeddings: (N, embedding_dim)
        predictions: (N, 1)
        """
        h1 = self.sage1(x, adj_norm)
        embeddings = self.sage2(h1, adj_norm)
        predictions = self.predictor(embeddings)
        return embeddings, predictions


class GNNSpatialReasoner:
    """Orchestrates graph feature extraction, inductive GNN training, and site reasoning."""

    FEATURE_DIM = 8

    def __init__(self, skg: LunarSpatialKnowledgeGraph, hidden_dim: int = 16, seed: int = 42):
        torch.manual_seed(seed)
        np.random.seed(seed)
        self.skg = skg
        self.model = LunarGraphSAGENetwork(in_dim=self.FEATURE_DIM, hidden_dim=hidden_dim)
        self.node_ids: List[str] = []
        self.node_id_to_idx: Dict[str, int] = {}
        self._prepare_graph_tensors()

    def _extract_node_feature_vector(self, node_id: str) -> np.ndarray:
        """Extracts normalized 8-element feature vector for a graph entity:

        [0]: Normalized elevation (-3000m to 0m)
        [1]: Mean slope / 45.0
        [2]: Max slope / 45.0
        [3]: Roughness RMS / 5.0
        [4]: Solar availability / 100.0
        [5]: Hydroxyl band depth / 10.0
        [6]: Is hazard flag (1.0 if Hazard, 0.0 otherwise)
        [7]: Registration / observation confidence
        """
        node = self.skg.get_node(node_id)
        if not node:
            return np.zeros(self.FEATURE_DIM, dtype=np.float32)

        elev = (node.elevation_m + 3000.0) / 3000.0
        mean_slope = float(node.properties.get("mean_slope_deg", 0.0)) / 45.0
        max_slope = float(node.properties.get("max_slope_deg", 0.0)) / 45.0
        rough = float(node.properties.get("roughness_rms_m", 0.0)) / 5.0
        solar = float(node.properties.get("solar_availability_pct", 50.0)) / 100.0
        hydroxyl = float(node.properties.get("band_depth_pct", 0.0)) / 10.0
        is_hazard = 1.0 if node.node_type == NodeType.HAZARD else 0.0
        confidence = float(node.properties.get("confidence", 0.85))

        vec = np.array(
            [elev, mean_slope, max_slope, rough, solar, hydroxyl, is_hazard, confidence],
            dtype=np.float32,
        )
        return np.clip(vec, 0.0, 1.0)

    def _prepare_graph_tensors(self) -> None:
        """Converts NetworkX knowledge graph into PyTorch feature matrix and normalized adjacency."""
        self.node_ids = list(self.skg.graph.nodes())
        self.node_id_to_idx = {nid: i for i, nid in enumerate(self.node_ids)}
        num_nodes = len(self.node_ids)

        # Build feature matrix X (N, 8)
        feats = [self._extract_node_feature_vector(nid) for nid in self.node_ids]
        self.x = torch.tensor(np.array(feats), dtype=torch.float32)

        # Build adjacency matrix A with self-loops
        adj = np.zeros((num_nodes, num_nodes), dtype=np.float32)
        np.fill_diagonal(adj, 1.0)

        for u, v in self.skg.graph.edges():
            if u in self.node_id_to_idx and v in self.node_id_to_idx:
                i, j = self.node_id_to_idx[u], self.node_id_to_idx[v]
                adj[i, j] = 1.0
                adj[j, i] = 1.0  # Bidirectional propagation for spatial context

        # Degree normalization: D^-1 * A
        row_sum = adj.sum(axis=1, keepdims=True)
        row_sum = np.maximum(row_sum, 1e-6)
        adj_norm = adj / row_sum
        self.adj_norm = torch.tensor(adj_norm, dtype=torch.float32)

    def train_inductive_predictor(self, epochs: int = 60, lr: float = 0.01) -> float:
        """Trains GraphSAGE predictor using available site labels."""
        self.model.train()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)

        # Find candidate site indices and construct pseudo ground-truth targets from physical constraints
        site_indices = []
        target_values = []

        for nid, idx in self.node_id_to_idx.items():
            node = self.skg.get_node(nid)
            if node and node.node_type == NodeType.CANDIDATE_SITE:
                site_indices.append(idx)
                # Compute objective label: high solar + low slope - hazard
                mean_slope = float(node.properties.get("mean_slope_deg", 5.0))
                solar = float(node.properties.get("solar_availability_pct", 50.0)) / 100.0
                suitability = float(np.clip(solar * 0.6 + (1.0 - mean_slope / 30.0) * 0.4, 0.0, 1.0))
                target_values.append([suitability])

        if not site_indices:
            return 0.0

        idx_tensor = torch.tensor(site_indices, dtype=torch.long)
        targets = torch.tensor(target_values, dtype=torch.float32)

        final_loss = 0.0
        for _ in range(epochs):
            optimizer.zero_grad()
            _, preds = self.model(self.x, self.adj_norm)
            site_preds = preds[idx_tensor]
            loss = F.mse_loss(site_preds, targets)
            loss.backward()
            optimizer.step()
            final_loss = float(loss.item())

        self.model.eval()
        return final_loss

    def infer_site_suitabilities(self) -> Dict[str, Dict[str, Any]]:
        """Infers GNN embeddings and suitability scores for all candidate sites in the graph."""
        self.model.eval()
        with torch.no_grad():
            embeddings, predictions = self.model(self.x, self.adj_norm)

        results = {}
        for nid, idx in self.node_id_to_idx.items():
            node = self.skg.get_node(nid)
            if node and node.node_type == NodeType.CANDIDATE_SITE:
                emb = embeddings[idx].cpu().numpy().tolist()
                pred_score = float(predictions[idx].item()) * 100.0
                results[nid] = {
                    "site_id": nid,
                    "site_name": node.name,
                    "gnn_suitability_score": round(pred_score, 1),
                    "embedding_vector": [round(v, 4) for v in emb[:6]],  # first 6 dims for inspection
                    "embedding_dim": len(emb),
                }
        return results
