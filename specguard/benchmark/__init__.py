"""
SpecGuard Benchmark and Model Validation Suite.
"""

from specguard.benchmark.engine import BenchmarkEngine
from specguard.benchmark.metrics import (
    calculate_iou,
    compute_prf1,
    normalize_text,
    text_similarity,
    compute_char_word_accuracy
)

__all__ = [
    "BenchmarkEngine",
    "calculate_iou",
    "compute_prf1",
    "normalize_text",
    "text_similarity",
    "compute_char_word_accuracy"
]
