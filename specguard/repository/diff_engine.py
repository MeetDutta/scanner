"""
Version-to-Version Comparison Diff Engine for SpecGuard Repository.
Compares two historical analysis runs to highlight new findings, resolved deviations,
and shifts in model prediction confidence or severity.
"""

from typing import List, Dict, Any, Tuple
from specguard.repository.models import VersionComparisonDiff, FindingDiffItem
from specguard.repository.manager import RepositoryManager
from specguard.core.models import Finding


class VersionDiffEngine:
    """Computes finding differentials across historical comparison checkpoints."""

    def __init__(self, repo_manager: RepositoryManager):
        self.repo_manager = repo_manager

    def compare_sessions(self, comparison_a_id: str, comparison_b_id: str) -> VersionComparisonDiff:
        record_a = self.repo_manager.get_comparison_record(comparison_a_id)
        record_b = self.repo_manager.get_comparison_record(comparison_b_id)

        if not record_a or not record_b:
            raise ValueError(f"One or both comparisons not found ({comparison_a_id}, {comparison_b_id})")

        findings_a = {f.finding_id: f for f in self.repo_manager.get_comparison_findings(comparison_a_id)}
        findings_b = {f.finding_id: f for f in self.repo_manager.get_comparison_findings(comparison_b_id)}

        diff_items: List[FindingDiffItem] = []
        all_ids = sorted(list(set(findings_a.keys()) | set(findings_b.keys())))

        new_count = 0
        resolved_count = 0
        persistent_count = 0

        for f_id in all_ids:
            in_a = f_id in findings_a
            in_b = f_id in findings_b

            if in_b and not in_a:
                # Newly emerged finding in B
                fb = findings_b[f_id]
                new_count += 1
                diff_items.append(FindingDiffItem(
                    finding_id=f_id,
                    category=fb.category,
                    severity=fb.severity,
                    location=fb.location,
                    explanation=fb.explanation,
                    status="NEW",
                    comparison_a_val=None,
                    comparison_b_val=str(fb.detected_value)
                ))
            elif in_a and not in_b:
                # Resolved finding (present in A, clean in B)
                fa = findings_a[f_id]
                resolved_count += 1
                diff_items.append(FindingDiffItem(
                    finding_id=f_id,
                    category=fa.category,
                    severity=fa.severity,
                    location=fa.location,
                    explanation=fa.explanation,
                    status="RESOLVED",
                    comparison_a_val=str(fa.detected_value),
                    comparison_b_val=None
                ))
            else:
                # Persistent in both
                fa = findings_a[f_id]
                fb = findings_b[f_id]
                persistent_count += 1
                diff_status = "MODIFIED" if fa.severity != fb.severity or fa.detected_value != fb.detected_value else "PERSISTENT"
                diff_items.append(FindingDiffItem(
                    finding_id=f_id,
                    category=fb.category,
                    severity=fb.severity,
                    location=fb.location,
                    explanation=fb.explanation,
                    status=diff_status,
                    comparison_a_val=str(fa.detected_value),
                    comparison_b_val=str(fb.detected_value)
                ))

        return VersionComparisonDiff(
            comparison_a_id=comparison_a_id,
            comparison_b_id=comparison_b_id,
            document_filename=record_b.document_filename,
            model_a=record_a.model_version,
            model_b=record_b.model_version,
            new_findings_count=new_count,
            resolved_findings_count=resolved_count,
            persistent_findings_count=persistent_count,
            diff_items=diff_items
        )
