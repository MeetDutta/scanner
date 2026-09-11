"""
Research-Grade Model Evaluation and Error Analysis Engine for SpecGuard.
Calculates Accuracy, Precision, Recall, Macro/Weighted F1, Confusion Matrix,
multiclass TP/FP/FN/TN, safety-critical finding metrics (Critical Recall, High Recall, FNR, FPR),
and finding-level deviation detection evaluation.
"""

from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field, asdict
import numpy as np
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support, confusion_matrix
)
import logging

from specguard.core.models import Finding

logger = logging.getLogger(__name__)


@dataclass
class ClassMetrics:
    tp: int
    fp: int
    fn: int
    tn: int
    precision: float
    recall: float
    f1: float
    fpr: float
    fnr: float


@dataclass
class DetailedEvaluationResult:
    accuracy: float
    precision_macro: float
    recall_macro: float
    f1_macro: float
    precision_weighted: float
    recall_weighted: float
    f1_weighted: float
    confusion_matrix: List[List[int]]
    class_labels: List[str]
    per_class: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    critical_recall: float = 0.0
    high_recall: float = 0.0
    critical_high_recall: float = 0.0
    critical_precision: float = 0.0
    high_precision: float = 0.0
    critical_f1: float = 0.0
    high_f1: float = 0.0
    false_negative_rate: float = 0.0
    false_positive_rate: float = 0.0
    false_positives: List[Dict[str, Any]] = field(default_factory=list)
    false_negatives: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ModelEvaluator:
    """Evaluates trained neural models against held-out ground truth test sets."""

    @staticmethod
    def evaluate_classification(
        y_true: List[int],
        y_pred: List[int],
        class_names: List[str],
        sample_metadata: Optional[List[Dict[str, Any]]] = None,
        critical_class: Optional[str] = None,
        high_class: Optional[str] = None
    ) -> DetailedEvaluationResult:
        if not y_true or not y_pred:
            return DetailedEvaluationResult(
                accuracy=0.0,
                precision_macro=0.0,
                recall_macro=0.0,
                f1_macro=0.0,
                precision_weighted=0.0,
                recall_weighted=0.0,
                f1_weighted=0.0,
                confusion_matrix=[],
                class_labels=class_names
            )

        num_classes = len(class_names)
        acc = float(accuracy_score(y_true, y_pred))
        p_mac, r_mac, f1_mac, _ = precision_recall_fscore_support(
            y_true, y_pred, average="macro", zero_division=0
        )
        p_wgt, r_wgt, f1_wgt, _ = precision_recall_fscore_support(
            y_true, y_pred, average="weighted", zero_division=0
        )

        cm = confusion_matrix(y_true, y_pred, labels=list(range(num_classes))).tolist()

        # Rigorous per-class TP, FP, FN, TN calculation
        per_class: Dict[str, Dict[str, Any]] = {}
        fps: List[Dict[str, Any]] = []
        fns: List[Dict[str, Any]] = []

        total_samples = len(y_true)

        for c_idx, c_name in enumerate(class_names):
            tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == c_idx and yp == c_idx)
            fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt != c_idx and yp == c_idx)
            fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == c_idx and yp != c_idx)
            tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt != c_idx and yp != c_idx)

            prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
            rec = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
            f1 = float(2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
            fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
            fnr = float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0

            per_class[c_name] = {
                "tp": tp, "fp": fp, "fn": fn, "tn": tn,
                "TP": tp, "FP": fp, "FN": fn, "TN": tn,
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1": round(f1, 4),
                "fpr": round(fpr, 4),
                "fnr": round(fnr, 4)
            }

        # Mathematical error categorization
        if sample_metadata:
            for idx, (yt, yp) in enumerate(zip(y_true, y_pred)):
                if yt != yp:
                    meta = sample_metadata[idx] if idx < len(sample_metadata) else {}
                    base_info = {
                        "index": idx,
                        "true_class": class_names[yt] if yt < num_classes else str(yt),
                        "predicted_class": class_names[yp] if yp < num_classes else str(yp),
                        "text": meta.get("text", "")[:100],
                        "document_id": meta.get("document_id", "N/A"),
                        "page": meta.get("page", 1)
                    }
                    # Distinct FP and FN entries based on true/pred classes
                    fps.append({**base_info, "error_type": f"FP_{class_names[yp]}"})
                    fns.append({**base_info, "error_type": f"FN_{class_names[yt]}"})

        # Explicit safety-critical finding metrics
        crit_rec, high_rec, crit_high_rec = 0.0, 0.0, 0.0
        crit_prec, high_prec = 0.0, 0.0
        crit_f1, high_f1 = 0.0, 0.0

        # Auto-detect Critical and High class names if not passed
        crit_label = critical_class
        high_label = high_class

        if not crit_label:
            for name in class_names:
                if "critical" in name.lower() or "contradict" in name.lower():
                    crit_label = name
                    break
        if not high_label:
            for name in class_names:
                if "high" in name.lower():
                    high_label = name
                    break

        if crit_label and crit_label in per_class:
            c_data = per_class[crit_label]
            crit_rec = c_data["recall"]
            crit_prec = c_data["precision"]
            crit_f1 = c_data["f1"]

        if high_label and high_label in per_class:
            h_data = per_class[high_label]
            high_rec = h_data["recall"]
            high_prec = h_data["precision"]
            high_f1 = h_data["f1"]

        # Combined Critical + High recall
        if crit_label and high_label and crit_label in per_class and high_label in per_class:
            tp_both = per_class[crit_label]["tp"] + per_class[high_label]["tp"]
            actual_both = (per_class[crit_label]["tp"] + per_class[crit_label]["fn"] +
                           per_class[high_label]["tp"] + per_class[high_label]["fn"])
            crit_high_rec = float(tp_both / actual_both) if actual_both > 0 else 0.0
        elif crit_label and crit_label in per_class:
            crit_high_rec = crit_rec

        fnr = round(1.0 - crit_rec, 4) if crit_rec > 0 else 1.0
        fpr = per_class.get(crit_label, {}).get("fpr", 0.0) if crit_label else 0.0

        return DetailedEvaluationResult(
            accuracy=round(acc, 4),
            precision_macro=round(float(p_mac), 4),
            recall_macro=round(float(r_mac), 4),
            f1_macro=round(float(f1_mac), 4),
            precision_weighted=round(float(p_wgt), 4),
            recall_weighted=round(float(r_wgt), 4),
            f1_weighted=round(float(f1_wgt), 4),
            confusion_matrix=cm,
            class_labels=class_names,
            per_class=per_class,
            critical_recall=round(crit_rec, 4),
            high_recall=round(high_rec, 4),
            critical_high_recall=round(crit_high_rec, 4),
            critical_precision=round(crit_prec, 4),
            high_precision=round(high_prec, 4),
            critical_f1=round(crit_f1, 4),
            high_f1=round(high_f1, 4),
            false_negative_rate=fnr,
            false_positive_rate=fpr,
            false_positives=fps[:25],
            false_negatives=fns[:25]
        )

    # Alias for explicit multiclass evaluation
    evaluate_multiclass = evaluate_classification


@dataclass
class FindingEvaluationResult:
    """Evaluation result for end-to-end engineering deviation detection."""
    deviation_precision: float
    deviation_recall: float
    deviation_f1: float
    critical_recall: float
    high_recall: float
    critical_high_recall: float
    false_positive_rate: float
    false_negative_rate: float
    total_ground_truth: int
    total_predictions: int
    true_positives: int
    false_positives: int
    false_negatives: int

    @property
    def precision(self) -> float:
        return self.deviation_precision

    @property
    def recall(self) -> float:
        return self.deviation_recall

    @property
    def f1(self) -> float:
        return self.deviation_f1

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FindingEvaluator:
    """Dedicated finding-level evaluation layer for engineering deviations and compliance."""

    @staticmethod
    def evaluate_findings(
        predictions: List[Finding],
        ground_truth: List[Finding]
    ) -> FindingEvaluationResult:
        if not ground_truth and not predictions:
            return FindingEvaluationResult(1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0, 0, 0, 0, 0)

        matched_gt = set()
        matched_preds = set()

        for p_idx, pred in enumerate(predictions):
            for g_idx, gt in enumerate(ground_truth):
                if g_idx in matched_gt:
                    continue

                # Match by category, domain, and location/content
                same_domain = pred.domain.lower() == gt.domain.lower()
                same_cat = pred.category.lower() == gt.category.lower()
                same_page = pred.page == gt.page

                # Check if detected content or rule matches
                content_overlap = (
                    pred.rule_reference == gt.rule_reference or
                    str(pred.detected_value).strip().lower() == str(gt.detected_value).strip().lower() or
                    (pred.explanation and gt.explanation and pred.explanation.lower()[:30] == gt.explanation.lower()[:30])
                )

                if same_domain and same_page and (same_cat or content_overlap):
                    matched_gt.add(g_idx)
                    matched_preds.add(p_idx)
                    break

        tp = len(matched_preds)
        fp = len(predictions) - tp
        fn = len(ground_truth) - len(matched_gt)

        prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        rec = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = float(2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

        # Critical and High Recall
        crit_gt = [gt for gt in ground_truth if gt.severity == "Critical"]
        crit_tp = [predictions[p] for p in matched_preds if predictions[p].severity == "Critical"]
        crit_rec = float(len(crit_tp) / len(crit_gt)) if crit_gt else 1.0

        high_gt = [gt for gt in ground_truth if gt.severity == "High"]
        high_tp = [predictions[p] for p in matched_preds if predictions[p].severity == "High"]
        high_rec = float(len(high_tp) / len(high_gt)) if high_gt else 1.0

        crit_high_gt = crit_gt + high_gt
        crit_high_tp = crit_tp + high_tp
        crit_high_rec = float(len(crit_high_tp) / len(crit_high_gt)) if crit_high_gt else 1.0

        fnr = 1.0 - rec
        fpr = float(fp / (fp + tp)) if (fp + tp) > 0 else 0.0

        return FindingEvaluationResult(
            deviation_precision=round(prec, 4),
            deviation_recall=round(rec, 4),
            deviation_f1=round(f1, 4),
            critical_recall=round(crit_rec, 4),
            high_recall=round(high_rec, 4),
            critical_high_recall=round(crit_high_rec, 4),
            false_positive_rate=round(fpr, 4),
            false_negative_rate=round(fnr, 4),
            total_ground_truth=len(ground_truth),
            total_predictions=len(predictions),
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn
        )

    evaluate = evaluate_findings
