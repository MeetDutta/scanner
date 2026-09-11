"""
Academic Evaluation and Detection Metrics Engine for SpecGuard.
Calculates Precision, Recall, F1-Score, Detection Accuracy, and False-Negative Rates for safety-critical deviations.
"""

from typing import List, Dict, Any, Set
from dataclasses import dataclass


@dataclass
class EvaluationReport:
    precision: float
    recall: float
    f1_score: float
    accuracy: float
    critical_recall: float
    false_positives: int
    false_negatives: int
    true_positives: int


class EvaluationMetrics:
    """Evaluates analyzer predictions against ground-truth annotated engineering datasets."""

    @staticmethod
    def evaluate(predicted_finding_ids: Set[str], ground_truth_ids: Set[str], critical_ids: Set[str]) -> EvaluationReport:
        tp = len(predicted_finding_ids & ground_truth_ids)
        fp = len(predicted_finding_ids - ground_truth_ids)
        fn = len(ground_truth_ids - predicted_finding_ids)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        accuracy = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0.0

        # Safety-critical recall
        crit_tp = len(predicted_finding_ids & critical_ids)
        crit_total = len(critical_ids)
        critical_recall = crit_tp / crit_total if crit_total > 0 else 1.0

        return EvaluationReport(
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1_score=round(f1, 4),
            accuracy=round(accuracy, 4),
            critical_recall=round(critical_recall, 4),
            false_positives=fp,
            false_negatives=fn,
            true_positives=tp
        )
