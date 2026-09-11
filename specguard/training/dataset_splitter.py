"""
Leakage-Free Dataset Splitter for SpecGuard.
Splits annotations into Train / Validation / Test partitions while strictly grouping
all pages of a document together to prevent data leakage between train and test sets.
"""

import re
import random
from collections import defaultdict
from typing import List, Dict, Tuple, Any, Optional
import logging

logger = logging.getLogger(__name__)


class DatasetSplitter:
    """
    Partitions annotated datasets into train/validation/test sets without document leakage.
    Strictly groups all pages and revisions of the same document family together.
    Guarantees:
        TRAIN ∩ VALIDATION = ∅
        TRAIN ∩ TEST = ∅
        VALIDATION ∩ TEST = ∅
    """

    @staticmethod
    def extract_family_id(annot: Dict[str, Any]) -> str:
        """Extracts document family identifier to prevent revision leakage across splits."""
        if annot.get("family_id"):
            return str(annot["family_id"])
        if annot.get("document_family"):
            return str(annot["document_family"])
        doc_id = annot.get("document_id") or annot.get("filename") or f"DOC_UNKNOWN_{annot.get('annotation_id', '0')}"
        # Strip revision suffixes like -REV1, _rev2, .v3, etc.
        clean_id = re.sub(r"[-_](?:rev|revision|v)\d+", "", str(doc_id), flags=re.IGNORECASE)
        # Strip extension if filename
        clean_id = clean_id.rsplit(".", 1)[0]
        return clean_id

    @classmethod
    def split_annotations(
        cls,
        annotations: List[Dict[str, Any]],
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        random_seed: int = 42,
        mode: str = "research"
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        if not annotations:
            return [], [], []

        # Group annotations by document family to guarantee zero cross-page & cross-revision leakage
        fam_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for annot in annotations:
            fam_id = cls.extract_family_id(annot)
            fam_groups[fam_id].append(annot)

        fam_ids = sorted(list(fam_groups.keys()))
        total_fams = len(fam_ids)

        if mode == "research" and total_fams < 3:
            raise ValueError(
                f"Research mode requires at least 3 distinct document families for strict "
                f"Train/Val/Test (70/15/15) leakage-free partitioning. Found only {total_fams} unique document(s): {fam_ids}. "
                f"Cannot perform research-grade evaluation without separate held-out validation and test documents."
            )

        rng = random.Random(random_seed)
        rng.shuffle(fam_ids)

        if total_fams >= 3:
            # Allocate at least 1 document family to Val and Test
            train_count = max(1, int(round(total_fams * train_ratio)))
            val_count = max(1, int(round(total_fams * val_ratio)))
            test_count = max(1, total_fams - train_count - val_count)

            # Ensure sum matches total_fams exactly while keeping each >= 1
            while train_count + val_count + test_count > total_fams and train_count > 1:
                train_count -= 1
            while train_count + val_count + test_count < total_fams:
                train_count += 1

            train_fam_ids = set(fam_ids[:train_count])
            val_fam_ids = set(fam_ids[train_count:train_count + val_count])
            test_fam_ids = set(fam_ids[train_count + val_count:])
        else:
            # Demo/fallback mode for tiny datasets
            train_fam_ids = set(fam_ids[:1])
            val_fam_ids = set(fam_ids[1:2]) if total_fams > 1 else set()
            test_fam_ids = set(fam_ids[2:]) if total_fams > 2 else set()

        # Strict mathematical assertion of disjoint document sets
        assert train_fam_ids.isdisjoint(val_fam_ids), "Train and Validation share document families!"
        assert train_fam_ids.isdisjoint(test_fam_ids), "Train and Test share document families!"
        assert val_fam_ids.isdisjoint(test_fam_ids), "Validation and Test share document families!"

        train_samples = []
        val_samples = []
        test_samples = []

        for fam_id, items in fam_groups.items():
            if fam_id in train_fam_ids:
                train_samples.extend(items)
            elif fam_id in val_fam_ids:
                val_samples.extend(items)
            elif fam_id in test_fam_ids:
                test_samples.extend(items)

        logger.info(
            "Dataset split (seed=%d): %d Train, %d Val, %d Test samples across %d unique document families (0 leakage).",
            random_seed, len(train_samples), len(val_samples), len(test_samples), total_fams
        )
        return train_samples, val_samples, test_samples

