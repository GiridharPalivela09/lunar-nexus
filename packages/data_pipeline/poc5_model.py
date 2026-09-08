"""NEXUS-LUNAR POC-5: Two-Tower Deep Vision Encoder & Shared Embedding Model.

Implements Siamese / Two-Tower neural architecture for cross-sensor lunar terrain correspondence.
Maps heterogeneous observation patches (Chandrayaan-2 OHRC/TMC-2 and NASA LROC NAC)
along with physical acquisition metadata into a unified 128-D L2-normalized metric space.
"""

from __future__ import annotations
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, Optional


class ConvBlock(nn.Module):
    """Residual convolutional block with batch normalization and leaky activation."""
    def __init__(self, in_channels: int, out_channels: int, downsample: bool = True):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.relu = nn.LeakyReLU(0.1, inplace=True)
        self.downsample = downsample
        if downsample:
            self.pool = nn.MaxPool2d(2, 2)
        
        if in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, bias=False),
                nn.BatchNorm2d(out_channels)
            )
        else:
            self.shortcut = nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        res = self.shortcut(x)
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out = self.relu(out + res)
        if self.downsample:
            out = self.pool(out)
        return out


class VisionTowerEncoder(nn.Module):
    """Deep visual feature extractor producing dense spatial morphology representations."""
    def __init__(self, in_channels: int = 1, base_dim: int = 32, feature_dim: int = 128):
        super().__init__()
        # Input: (B, 1, 128, 128) -> Layer 1 -> (B, 32, 64, 64)
        self.block1 = ConvBlock(in_channels, base_dim, downsample=True)
        # Layer 2 -> (B, 64, 32, 32)
        self.block2 = ConvBlock(base_dim, base_dim * 2, downsample=True)
        # Layer 3 -> (B, 128, 16, 16)
        self.block3 = ConvBlock(base_dim * 2, base_dim * 4, downsample=True)
        # Layer 4 -> (B, 128, 8, 8)
        self.block4 = ConvBlock(base_dim * 4, feature_dim, downsample=True)
        
        # Spatial Global Average & Max Pooling
        self.gap = nn.AdaptiveAvgPool2d((1, 1))
        self.gmp = nn.AdaptiveMaxPool2d((1, 1))
        self.fc = nn.Linear(feature_dim * 2, feature_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.block1(x)
        h = self.block2(h)
        h = self.block3(h)
        h = self.block4(h)
        
        avg_pool = self.gap(h).flatten(1)
        max_pool = self.gmp(h).flatten(1)
        pooled = torch.cat([avg_pool, max_pool], dim=1)
        features = F.leaky_relu(self.fc(pooled), 0.1)
        return features


class MetadataConditioningMLP(nn.Module):
    """Projects physical telemetry parameters (GSD, incidence angle, sensor ID) into dense conditioning vector."""
    def __init__(self, meta_dim: int = 9, out_dim: int = 32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(meta_dim, 64),
            nn.LeakyReLU(0.1, inplace=True),
            nn.Linear(64, out_dim),
            nn.LeakyReLU(0.1, inplace=True),
        )

    def forward(self, meta: torch.Tensor) -> torch.Tensor:
        return self.net(meta)


class TwoTowerCorrespondenceModel(nn.Module):
    """Complete Two-Tower Cross-Sensor Neural Correspondence Architecture."""

    def __init__(
        self,
        embedding_dim: int = 128,
        meta_dim: int = 9,
        meta_proj_dim: int = 32,
    ):
        super().__init__()
        self.embedding_dim = embedding_dim
        
        # Source Vision Tower (OHRC / TMC-2 targeted instruments)
        self.source_tower = VisionTowerEncoder(in_channels=1, base_dim=32, feature_dim=embedding_dim)
        # Reference Vision Tower (LROC NAC reconnaissance baseline)
        self.reference_tower = VisionTowerEncoder(in_channels=1, base_dim=32, feature_dim=embedding_dim)
        
        # Physical Metadata Conditioning
        self.meta_mlp = MetadataConditioningMLP(meta_dim=meta_dim, out_dim=meta_proj_dim)
        
        # Joint Projection Heads with Batch Normalization to prevent dimensional collapse
        self.source_head = nn.Sequential(
            nn.Linear(embedding_dim + meta_proj_dim, embedding_dim, bias=False),
            nn.BatchNorm1d(embedding_dim),
            nn.LeakyReLU(0.1, inplace=True),
            nn.Linear(embedding_dim, embedding_dim, bias=False),
            nn.BatchNorm1d(embedding_dim)
        )
        self.reference_head = nn.Sequential(
            nn.Linear(embedding_dim + meta_proj_dim, embedding_dim, bias=False),
            nn.BatchNorm1d(embedding_dim),
            nn.LeakyReLU(0.1, inplace=True),
            nn.Linear(embedding_dim, embedding_dim, bias=False),
            nn.BatchNorm1d(embedding_dim)
        )

    def encode_source(self, src_img: torch.Tensor, meta: torch.Tensor) -> torch.Tensor:
        """Projects a source observation patch into L2-normalized shared embedding."""
        vis_feat = self.source_tower(src_img)
        meta_feat = self.meta_mlp(meta)
        combined = torch.cat([vis_feat, meta_feat], dim=1)
        # Handle batch size 1 inference for BatchNorm
        if combined.size(0) == 1 and not self.training:
            emb = self.source_head[3](self.source_head[2](self.source_head[0](combined)))
        else:
            emb = self.source_head(combined)
        return F.normalize(emb, p=2, dim=-1)

    def encode_reference(self, ref_img: torch.Tensor, meta: torch.Tensor) -> torch.Tensor:
        """Projects a reference observation patch into L2-normalized shared embedding."""
        vis_feat = self.reference_tower(ref_img)
        meta_feat = self.meta_mlp(meta)
        combined = torch.cat([vis_feat, meta_feat], dim=1)
        # Handle batch size 1 inference for BatchNorm
        if combined.size(0) == 1 and not self.training:
            emb = self.reference_head[3](self.reference_head[2](self.reference_head[0](combined)))
        else:
            emb = self.reference_head(combined)
        return F.normalize(emb, p=2, dim=-1)

    def compute_similarity(self, src_emb: torch.Tensor, ref_emb: torch.Tensor) -> torch.Tensor:
        """Computes pairwise cosine similarity in [-1.0, 1.0] between normalized embeddings."""
        return torch.sum(src_emb * ref_emb, dim=-1)

    def forward(
        self,
        src_img: torch.Tensor,
        ref_img: torch.Tensor,
        meta: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Runs joint forward pass on pair returning (source_embedding, reference_embedding, cosine_similarity)."""
        src_emb = self.encode_source(src_img, meta)
        ref_emb = self.encode_reference(ref_img, meta)
        sim = self.compute_similarity(src_emb, ref_emb)
        return src_emb, ref_emb, sim
