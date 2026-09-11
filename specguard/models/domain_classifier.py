"""
PyTorch Domain Classification Model for SpecGuard.
Classifies engineering texts into MECHANICAL, CHEMICAL, ELECTRICAL, or GENERAL.
"""

import torch
import torch.nn as nn
from typing import List, Dict, Tuple, Any


class DomainClassifierNet(nn.Module):
    """
    Lightweight, highly efficient Bidirectional LSTM text classifier for offline domain prediction.
    """
    def __init__(self, vocab_size: int = 5000, embed_dim: int = 64, hidden_dim: int = 64, num_classes: int = 4):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.lstm = nn.LSTM(embed_dim, hidden_dim, batch_first=True, bidirectional=True)
        self.fc = nn.Linear(hidden_dim * 2, num_classes)
        self.dropout = nn.Dropout(0.3)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch_size, seq_len)
        embedded = self.dropout(self.embedding(x))
        lstm_out, (hidden, _) = self.lstm(embedded)
        # Concatenate forward and backward final states
        hidden_cat = torch.cat((hidden[-2], hidden[-1]), dim=1)
        logits = self.fc(self.dropout(hidden_cat))
        return logits


class SimpleTokenizer:
    """Deterministic offline word-level tokenizer with index mapping."""
    def __init__(self, max_vocab: int = 5000):
        self.max_vocab = max_vocab
        self.word2idx: Dict[str, int] = {"<PAD>": 0, "<UNK>": 1}
        self.idx2word: Dict[int, str] = {0: "<PAD>", 1: "<UNK>"}

    def fit(self, texts: List[str]):
        from collections import Counter
        counts = Counter()
        for t in texts:
            words = t.lower().split()
            counts.update(words)
        for w, _ in counts.most_common(self.max_vocab - 2):
            idx = len(self.word2idx)
            self.word2idx[w] = idx
            self.idx2word[idx] = w

    def encode(self, text: str, max_len: int = 64) -> List[int]:
        words = text.lower().split()
        ids = [self.word2idx.get(w, 1) for w in words[:max_len]]
        if len(ids) < max_len:
            ids += [0] * (max_len - len(ids))
        return ids

    def to_dict(self) -> Dict[str, Any]:
        return {"word2idx": self.word2idx}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SimpleTokenizer':
        tok = cls()
        tok.word2idx = data.get("word2idx", {"<PAD>": 0, "<UNK>": 1})
        tok.idx2word = {int(v): k for k, v in tok.word2idx.items()}
        return tok
