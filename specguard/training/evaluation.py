"""
Research-Grade Model Evaluation and Error Analysis Engine for SpecGuard.
Calculates Accuracy, Precision, Recall, Macro/Weighted F1, Confusion Matrix,
and safety-critical metrics (Critical Finding Recall, False Negative Rate).
"""

from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field
import numpy as np
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support, confusion_matrix
)
import logging

logger = logging.getLogger(__name__)


@dataclass
class DetailedEvaluationResult:
    accuracy: float
    precision_macro: float
    recall_macro: float
    f1_macro: float
    precision_weighted: float
    recall_weighted: float
    f1_weighted: float
    critical_recall: float
    false_negative_rate: float
    confusion_matrix: List[List[int]]
    class_labels: List[str]
    false_positives: List[Dict[str, Any]] = field(default_factory=list)
    false_negatives: List[Dict[str, Any]] = field(default_factory=list)


class ModelEvaluator:
    """Evaluates trained neural models against held-out ground truth test sets."""

    @staticmethod
    def evaluate_classification(
        y_true: List[int],
        y_pred: List[int],
        class_names: List[str],
        sample_metadata: Optional[List[Dict[str, Any]]] = None
    ) -> DetailedEvaluationResult:
        if not y_true or not y_pred:
            return DetailedEvaluationResult(
                0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, [], class_names
            )

        acc = float(accuracy_score(y_true, y_pred))
        p_mac, r_mac, f1_mac, _ = precision_recall_fscore_support(y_true, y_pred, average='macro', zero_division=0)
        p_wgt, r_wgt, f1_wgt, _ = precision_recall_fscore_support(y_true, y_pred, average='weighted', zero_division=0)

        cm = confusion_matrix(y_true, y_pred, labels=list(range(len(class_names)))).tolist()

        # Identify False Positives and False Negatives for error analysis
        fps = []
        fns = []
        if sample_metadata:
            for idx, (yt, yp) in enumerate(zip(y_true, y_pred)):
                if yt != yp:
                    item = sample_metadata[idx] if idx < len(sample_metadata) else {}
                    err_info = {
                        "index": idx,
                        "true_label": class_names[yt] if yt < len(class_names) else str(yt),
                        "predicted_label": class_names[yp] if yp < len(class_names) else str(yp),
                        "text": item.get("text", "")[:80],
                        "document_id": item.get("document_id", "N/A"),
                        "page": item.get("page", 1)
                    }
                    fps.append(err_info)
                    fns.append(err_info)

        # Calculate Critical Finding Recall
        # Assuming index 0 or classes labeled Critical are safety-critical
        crit_true = sum(1 for yt in y_true if yt == 0)
        crit_caught = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0)
        crit_recall = float(crit_caught / crit_true) if crit_true > 0 else 1.0
        fnr = 1.0 - crit_recall

        return DetailedEvaluationResult(
            accuracy=round(acc, 4),
            precision_macro=round(float(p_mac), 4),
            recall_macro=round(float(r_mac), 4),
            f1_macro=round(float(f1_mac), 4),
            precision_weighted=round(float(p_wgt), 4),
            recall_weighted=round(float(r_wgt), 4),
            f1_weighted=round(float(f1_wgt), 4),
            critical_recall=round(crit_recall, 4),
            false_negative_rate=round(fnr, 4),
            confusion_matrix=cm,
            class_labels=class_names,
            false_positives=fps[:10],
            false_negatives=fns[:10]
        )
