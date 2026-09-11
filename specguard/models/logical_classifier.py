"""
PyTorch Semantic & Logical Contradiction Model for SpecGuard.
Siamese dual-encoder architecture that compares statement pairs for engineering contradictions.
"""

import torch
import torch.nn as nn
from typing import Tuple


class LogicalRelationNet(nn.Module):
    """
    Siamese neural network that encodes two technical statements, calculates vector distance
    and interaction terms, and predicts whether they are CONSISTENT or CONTRADICTORY.
    """
    def __init__(self, vocab_size: int = 5000, embed_dim: int = 64, hidden_dim: int = 64):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.lstm = nn.LSTM(embed_dim, hidden_dim, batch_first=True, bidirectional=True)
        self.dropout = nn.Dropout(0.3)
        # Input to classifier: [u; v; |u - v|; u * v] = hidden_dim * 2 * 4
        in_features = (hidden_dim * 2) * 4
        self.classifier = nn.Sequential(
            nn.Linear(in_features, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 2)  # 0: CONSISTENT, 1: CONTRADICTORY
        )

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        embedded = self.dropout(self.embedding(x))
        _, (hidden, _) = self.lstm(embedded)
        return torch.cat((hidden[-2], hidden[-1]), dim=1)

    def forward(self, x1: torch.Tensor, x2: torch.Tensor) -> torch.Tensor:
        u = self.encode(x1)
        v = self.encode(x2)
        diff = torch.abs(u - v)
        prod = u * v
        features = torch.cat([u, v, diff, prod], dim=1)
        logits = self.classifier(features)
        return logits
