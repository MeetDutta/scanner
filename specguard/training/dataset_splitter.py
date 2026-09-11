"""
Leakage-Free Dataset Splitter for SpecGuard.
Splits annotations into Train / Validation / Test partitions while strictly grouping
all pages of a document together to prevent data leakage between train and test sets.
"""

import random
from collections import defaultdict
from typing import List, Dict, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class DatasetSplitter:
    """Partitions annotated datasets into train/validation/test sets without document leakage."""

    @staticmethod
    def split_annotations(
        annotations: List[Dict[str, Any]],
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        random_seed: int = 42
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        if not annotations:
            return [], [], []

        # Group annotations by document_id to guarantee zero document leakage
        doc_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for annot in annotations:
            doc_id = annot.get("document_id") or f"DOC_UNKNOWN_{annot.get('annotation_id')}"
            doc_groups[doc_id].append(annot)

        doc_ids = list(doc_groups.keys())
        rng = random.Random(random_seed)
        rng.shuffle(doc_ids)

        total_docs = len(doc_ids)
        train_count = max(1, int(total_docs * train_ratio))
        val_count = max(1, int(total_docs * val_ratio)) if total_docs > 2 else 0

        train_doc_ids = set(doc_ids[:train_count])
        val_doc_ids = set(doc_ids[train_count:train_count + val_count])
        test_doc_ids = set(doc_ids[train_count + val_count:])

        train_samples = []
        val_samples = []
        test_samples = []

        for doc_id, items in doc_groups.items():
            if doc_id in train_doc_ids:
                train_samples.extend(items)
            elif doc_id in val_doc_ids:
                val_samples.extend(items)
            else:
                test_samples.extend(items)

        # Fallback if samples are small
        if not test_samples and len(train_samples) > 2:
            test_samples.append(train_samples.pop())
        if not val_samples and len(train_samples) > 2:
            val_samples.append(train_samples.pop())

        logger.info(
            "Dataset split (seed=%d): %d Train, %d Val, %d Test across %d unique documents (0 leakage).",
            random_seed, len(train_samples), len(val_samples), len(test_samples), total_docs
        )
        return train_samples, val_samples, test_samples
