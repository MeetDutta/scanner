"""
PyTorch Engineering Named Entity Recognition (NER) Model for SpecGuard.
Implements robust offset-aware tokenization, character span alignment,
BIO tagging with distinct PAD/O indices, and attention-mask-supported BiLSTM sequence tagger.
"""

import re
import torch
import torch.nn as nn
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any

DEFAULT_ENTITY_TYPES = [
    "COMPONENT",
    "MATERIAL",
    "PARAMETER",
    "VALUE",
    "UNIT",
    "STANDARD",
    "REQUIREMENT",
    "LIMIT",
    "TEMPERATURE",
    "PRESSURE",
    "VOLTAGE",
    "CURRENT",
    "POWER",
    "FREQUENCY",
    "DIMENSION",
    "TOLERANCE",
    "CONCENTRATION",
]

PAD_LABEL = "[PAD]"
O_LABEL = "O"


def build_ner_labels(entity_types: Optional[List[str]] = None) -> List[str]:
    """Generates ordered BIO labels with PAD at index 0 and O at index 1."""
    types = entity_types or DEFAULT_ENTITY_TYPES
    labels = [PAD_LABEL, O_LABEL]
    for ent in types:
        labels.append(f"B-{ent}")
        labels.append(f"I-{ent}")
    return labels


NER_LABELS = build_ner_labels()
LABEL2ID = {lbl: idx for idx, lbl in enumerate(NER_LABELS)}
ID2LABEL = {idx: lbl for idx, lbl in enumerate(NER_LABELS)}
PAD_ID = LABEL2ID[PAD_LABEL]
O_ID = LABEL2ID[O_LABEL]


@dataclass
class TokenOffset:
    """Represents a single token and its exact character offsets in the original text."""
    token: str
    start_char: int
    end_char: int


class RegexOffsetTokenizer:
    """
    Robust offset-aware tokenizer for technical and engineering text.
    Handles engineering notation, dimensions (M12 × 1.5), units (415 V, 80 °C, 10 bar),
    hyphenated equipment tags (P-101, V-201A), Greek symbols, and mathematical operators.
    """
    # Pattern recognizes:
    # 1. Engineering numbers with decimals, exponents, or tolerances: 15.0, 0.75, 1e-3, ±0.05
    # 2. Words with hyphens, underscores, or multiplication symbols: P-101, M12x1.5, 304L-SS
    # 3. Non-alphanumeric technical symbols and units: °C, %, Ω, µm, ≤, ≥, ±, ×
    # 4. Standard words and punctuation
    TOKEN_REGEX = re.compile(
        r"[±≤≥><=×~]|\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b|[°][CFK]|[\w]+(?:[-_×/][\w]+)*|[^\s\w]",
        re.UNICODE
    )

    @classmethod
    def tokenize_with_offsets(cls, text: str) -> List[TokenOffset]:
        """Returns ordered list of tokens with exact (start_char, end_char) boundaries."""
        tokens: List[TokenOffset] = []
        for match in cls.TOKEN_REGEX.finditer(text):
            tok_text = match.group()
            tokens.append(TokenOffset(
                token=tok_text,
                start_char=match.start(),
                end_char=match.end()
            ))
        return tokens

    @classmethod
    def align_entities_to_bio(
        cls,
        tokens: List[TokenOffset],
        entities: List[Dict[str, Any]],
        label2id: Optional[Dict[str, int]] = None
    ) -> List[int]:
        """
        Maps ground-truth character spans to BIO token label indices.
        Guarantees strict offset alignment without heuristic word splitting.
        """
        l2id = label2id or LABEL2ID
        tags = [O_ID] * len(tokens)

        # Sort entities by start_char
        sorted_ents = sorted(entities, key=lambda e: e.get("start_char", 0))

        for ent in sorted_ents:
            e_label = ent.get("label", "PARAMETER").upper()
            e_start = ent.get("start_char", 0)
            e_end = ent.get("end_char", 0)

            # Find matching token range
            matched_indices = []
            for t_idx, t in enumerate(tokens):
                # Token overlaps entity span if intersection is non-empty
                if max(t.start_char, e_start) < min(t.end_char, e_end):
                    matched_indices.append(t_idx)

            if not matched_indices:
                continue

            # First overlapping token gets B- tag, subsequent get I- tag
            b_tag = f"B-{e_label}"
            i_tag = f"I-{e_label}"

            b_id = l2id.get(b_tag, l2id.get(f"B-PARAMETER", O_ID))
            i_id = l2id.get(i_tag, l2id.get(f"I-PARAMETER", O_ID))

            for rank, t_idx in enumerate(matched_indices):
                if rank == 0:
                    tags[t_idx] = b_id
                else:
                    tags[t_idx] = i_id

        return tags


align_entities_to_bio = RegexOffsetTokenizer.align_entities_to_bio


class EngineeringNERNet(nn.Module):
    """
    BiLSTM token sequence tagger for engineering document entity recognition.
    Supports attention masking to cleanly decouple real 'O' tokens from padding tokens.
    """
    def __init__(
        self,
        vocab_size: int = 5000,
        embed_dim: int = 64,
        hidden_dim: int = 64,
        num_labels: int = len(NER_LABELS),
        dropout: float = 0.3,
        num_classes: Optional[int] = None
    ):
        super().__init__()
        num_labels = num_classes if num_classes is not None else num_labels
        self.num_labels = num_labels
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.lstm = nn.LSTM(
            embed_dim,
            hidden_dim,
            batch_first=True,
            bidirectional=True
        )
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(hidden_dim * 2, num_labels)

    def forward(
        self,
        x: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        # x: (batch_size, seq_len)
        embedded = self.dropout(self.embedding(x))
        lstm_out, _ = self.lstm(embedded)  # (batch_size, seq_len, hidden_dim * 2)
        logits = self.classifier(self.dropout(lstm_out))  # (batch_size, seq_len, num_labels)
        if attention_mask is not None:
            logits = logits * attention_mask.unsqueeze(-1)
        return logits
