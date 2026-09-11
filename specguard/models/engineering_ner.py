"""
PyTorch Engineering Named Entity Recognition (NER) Model for SpecGuard.
Sequence-tagging neural architecture for extracting technical parameters, values, and units.
"""

import torch
import torch.nn as nn
from typing import List, Dict, Tuple, Any

NER_LABELS = [
    "O",
    "B-COMPONENT", "I-COMPONENT",
    "B-PARAMETER", "I-PARAMETER",
    "B-VALUE", "I-VALUE",
    "B-UNIT", "I-UNIT",
    "B-TOLERANCE", "I-TOLERANCE",
    "B-PRESSURE", "I-PRESSURE",
    "B-TEMPERATURE", "I-TEMPERATURE",
    "B-VOLTAGE", "I-VOLTAGE",
    "B-CURRENT", "I-CURRENT",
    "B-POWER", "I-POWER",
    "B-FREQUENCY", "I-FREQUENCY",
    "B-CONCENTRATION", "I-CONCENTRATION",
    "B-STANDARD_REF", "I-STANDARD_REF"
]

LABEL2ID = {lbl: idx for idx, lbl in enumerate(NER_LABELS)}
ID2LABEL = {idx: lbl for idx, lbl in enumerate(NER_LABELS)}


class EngineeringNERNet(nn.Module):
    """
    BiLSTM token sequence tagger for engineering document entity recognition.
    """
    def __init__(self, vocab_size: int = 5000, embed_dim: int = 64, hidden_dim: int = 64, num_labels: int = len(NER_LABELS)):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.lstm = nn.LSTM(embed_dim, hidden_dim, batch_first=True, bidirectional=True)
        self.dropout = nn.Dropout(0.3)
        self.classifier = nn.Linear(hidden_dim * 2, num_labels)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch_size, seq_len)
        embedded = self.dropout(self.embedding(x))
        lstm_out, _ = self.lstm(embedded) # (batch_size, seq_len, hidden_dim*2)
        logits = self.classifier(self.dropout(lstm_out)) # (batch_size, seq_len, num_labels)
        return logits
