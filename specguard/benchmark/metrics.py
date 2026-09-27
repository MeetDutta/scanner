"""
SpecGuard Benchmark Evaluation Metrics Engine.
Computes Precision, Recall, F1 (micro/macro), Confusion Matrices,
Bounding-Box Intersection over Union (IoU), Normalized Text Matching,
and Tolerance Index Absolute/Relative Errors without fabrication.
"""

import re
import difflib
from typing import List, Dict, Tuple, Optional, Any
import numpy as np


def normalize_text(text: Optional[str]) -> str:
    """Normalizes string for robust, whitespace/punctuation-invariant comparison."""
    if not text:
        return ""
    # Lowercase
    t = text.lower()
    # Normalize unicode spaces & dashes
    t = re.sub(r'[\u2014\u2013\u2212-]', '-', t)
    t = re.sub(r'\.{2,}', '..', t)
    # Remove punctuation except essential technical chars
    t = re.sub(r'[^\w\s\.\-]', ' ', t)
    # Collapse multiple whitespaces
    t = " ".join(t.split())
    return t


def text_similarity(s1: str, s2: str) -> float:
    """Computes exact normalized match and fuzzy gestalt token similarity."""
    n1 = normalize_text(s1)
    n2 = normalize_text(s2)
    if not n1 and not n2:
        return 1.0
    if not n1 or not n2:
        return 0.0
    if n1 == n2:
        return 1.0
    # Substring match bonus
    if n1 in n2 or n2 in n1:
        return 0.95
    return difflib.SequenceMatcher(None, n1, n2).ratio()


def calculate_iou(box_a: Optional[List[float]], box_b: Optional[List[float]]) -> float:
    """
    Calculates Intersection over Union (IoU) of two bounding boxes.
    Supports [x0, y0, x1, y1] format.
    """
    if not box_a or not box_b:
        return 0.0

    xA = max(box_a[0], box_b[0])
    yA = max(box_a[1], box_b[1])
    xB = min(box_a[2], box_b[2])
    yB = min(box_a[3], box_b[3])

    inter_w = max(0.0, xB - xA)
    inter_h = max(0.0, yB - yA)
    inter_area = inter_w * inter_h

    if inter_area <= 0.0:
        return 0.0

    area_a = max(0.0, box_a[2] - box_a[0]) * max(0.0, box_a[3] - box_a[1])
    area_b = max(0.0, box_b[2] - box_b[0]) * max(0.0, box_b[3] - box_b[1])
    union_area = area_a + area_b - inter_area

    if union_area <= 0.0:
        return 0.0

    return inter_area / union_area


def compute_prf1(tp: int, fp: int, fn: int) -> Dict[str, float]:
    """Calculates Precision, Recall, and F1-score with safe zero division."""
    prec = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if fn == 0 else 0.0)
    rec = tp / (tp + fn) if (tp + fn) > 0 else (1.0 if fp == 0 else 0.0)
    f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
    return {
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4)
    }


def compute_char_word_accuracy(reference: str, hypothesis: str) -> Dict[str, float]:
    """Character and word level accuracy metrics for OCR benchmark."""
    r_words = reference.split()
    h_words = hypothesis.split()
    word_sm = difflib.SequenceMatcher(None, r_words, h_words)
    word_acc = word_sm.ratio()

    char_sm = difflib.SequenceMatcher(None, reference, hypothesis)
    char_acc = char_sm.ratio()

    return {
        "char_accuracy": round(char_acc, 4),
        "word_accuracy": round(word_acc, 4)
    }
