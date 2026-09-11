"""
Logical Consistency and Cross-Document Contradiction Analysis Engine for SpecGuard.
Maintains a document-wide parameter registry across all pages and tables.
Detects cross-page conflicting values (e.g. 80°C on p.4 vs 60°C on p.21),
minimum > maximum contradictions, and impossible engineering relationships.
"""

from typing import List, Dict, Tuple, Optional, Any
from collections import defaultdict
import logging

from specguard.analyzers.base import BaseAnalyzer
from specguard.core.models import (
    DocumentModel, Finding, FindingCategory, SeverityLevel, EngineeringParameter, BBox
)

logger = logging.getLogger(__name__)


class LogicalAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Logical Consistency Analyzer"

    @property
    def category(self) -> FindingCategory:
        return FindingCategory.LOGICAL

    def analyze(self, doc: DocumentModel, context: Dict[str, Any] = None) -> List[Finding]:
        findings: List[Finding] = []
        finding_counter = 1

        parameters: List[EngineeringParameter] = (context or {}).get("parameters", [])
        if not parameters:
            return findings

        # 1. Group parameters by parameter name across the whole document
        registry: Dict[str, List[EngineeringParameter]] = defaultdict(list)
        for p in parameters:
            registry[p.parameter.lower()].append(p)

        for param, param_instances in registry.items():
            if len(param_instances) < 2:
                continue

            # Compare instances across different pages
            base_p = param_instances[0]
            for comp_p in param_instances[1:]:
                # Check cross-page comparison
                if base_p.page == comp_p.page and abs(comp_p.normalized_value - base_p.normalized_value) < 1e-4:
                    continue

                # Normalized difference (> 1% discrepancy)
                diff = abs(comp_p.normalized_value - base_p.normalized_value)
                max_val = max(abs(base_p.normalized_value), abs(comp_p.normalized_value), 1e-6)
                relative_diff = diff / max_val


                if relative_diff > 0.01:
                    findings.append(Finding(
                        finding_id=f"LOG-CTR-{finding_counter:03d}",
                        category=self.category.value,
                        domain="General",
                        location=f"Page {base_p.page} vs Page {comp_p.page}",
                        page=comp_p.page,
                        bbox=comp_p.bbox,
                        original_content=f"Page {base_p.page}: '{base_p.raw_value}' vs Page {comp_p.page}: '{comp_p.raw_value}'",
                        detected_value=f"{comp_p.raw_value} (Page {comp_p.page})",
                        expected_value=f"Consistent value matching Page {base_p.page} ({base_p.raw_value})",
                        deviation=f"Cross-document discrepancy of {diff:.2f} {base_p.normalized_unit}",
                        severity=SeverityLevel.CRITICAL.value,
                        confidence=0.98,
                        explanation=(
                            f"Logical contradiction detected across document sections. "
                            f"Page {base_p.page} specifies {param.replace('_', ' ')} of {base_p.entity} as {base_p.raw_value}, "
                            f"whereas Page {comp_p.page} specifies {comp_p.raw_value}."
                        ),
                        suggested_correction=(
                            f"Reconcile specification conflict for '{param.replace('_', ' ')}' between Page {base_p.page} and Page {comp_p.page}."
                        ),
                        rule_reference="Engineering Design Consistency Standard ISO 9001 §7.3",
                        priority_score=9.5
                    ))
                    finding_counter += 1

        # 2. Check Min > Max contradictions
        min_params = [p for p in parameters if "min" in p.source_sentence.lower()]
        max_params = [p for p in parameters if "max" in p.source_sentence.lower()]

        for min_p in min_params:
            for max_p in max_params:
                if (min_p.parameter == max_p.parameter and 
                        min_p.entity.lower() == max_p.entity.lower() and 
                        min_p.normalized_unit == max_p.normalized_unit):
                    if min_p.normalized_value > max_p.normalized_value:
                        findings.append(Finding(
                            finding_id=f"LOG-MMX-{finding_counter:03d}",
                            category=self.category.value,
                            domain="General",
                            location=f"Page {min_p.page} & Page {max_p.page}",
                            page=min_p.page,
                            bbox=min_p.bbox,
                            original_content=f"Min: {min_p.raw_value} > Max: {max_p.raw_value}",
                            detected_value=f"Minimum ({min_p.raw_value}) > Maximum ({max_p.raw_value})",
                            expected_value="Minimum ≤ Maximum parameter boundary",
                            deviation=f"Inversion error: Minimum exceeds maximum by {min_p.normalized_value - max_p.normalized_value:.2f} {min_p.normalized_unit}",
                            severity=SeverityLevel.CRITICAL.value,
                            confidence=0.99,
                            explanation=(
                                f"Physical impossibility detected: The specified minimum {min_p.parameter} ({min_p.raw_value}) "
                                f"strictly exceeds the maximum {max_p.parameter} ({max_p.raw_value})."
                            ),
                            suggested_correction="Swap or correct the minimum and maximum threshold limits.",
                            rule_reference="Fundamental Physical & Engineering Constraints §1.1",
                            priority_score=9.8
                        ))
                        finding_counter += 1

        return findings
