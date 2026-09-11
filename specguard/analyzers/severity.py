"""
Severity Classification and Finding Prioritization Engine for SpecGuard.
Computes multi-factor priority scores combining severity, safety impact, deviation magnitude,
standard criticality, detection confidence, and cross-document footprint.
"""

from typing import List, Dict, Optional, Any
import logging

from specguard.core.models import Finding, SeverityLevel, FindingCategory
from specguard.core.config import SeverityWeights

logger = logging.getLogger(__name__)


class SeverityEngine:
    """
    Ranks findings mathematically to surface the most critical engineering hazards first.
    Prevents cosmetic issues from eclipsing functional/safety deviations.
    """

    SEVERITY_BASE_SCORES = {
        SeverityLevel.CRITICAL.value: 10.0,
        SeverityLevel.HIGH.value: 7.5,
        SeverityLevel.MEDIUM.value: 5.0,
        SeverityLevel.LOW.value: 2.5,
        SeverityLevel.INFORMATIONAL.value: 1.0
    }

    # Engineering domains with higher inherent safety risk
    SAFETY_IMPACT_CATEGORIES = {
        FindingCategory.STANDARDS.value: 3.5,
        FindingCategory.LOGICAL.value: 3.0,
        FindingCategory.ENGINEERING.value: 2.5,
        FindingCategory.TABLE.value: 1.5,
        FindingCategory.STRUCTURE.value: 1.0,
        FindingCategory.TOC.value: 1.0,
        FindingCategory.SEMANTIC.value: 1.2,
        FindingCategory.FORMATTING.value: 0.2,
        FindingCategory.GRAMMAR.value: 0.1
    }

    def __init__(self, weights: Optional[SeverityWeights] = None):
        self.weights = weights or SeverityWeights()

    def calculate_priority(self, finding: Finding) -> float:
        """Calculates a normalized priority score for a single finding."""
        base_sev = self.SEVERITY_BASE_SCORES.get(finding.severity, 3.0)
        safety = self.SAFETY_IMPACT_CATEGORIES.get(finding.category, 0.5)

        # Deviation magnitude factor: if finding has numerical deviation
        dev_magnitude = 1.0
        if finding.deviation and any(char.isdigit() for char in finding.deviation):
            dev_magnitude = 2.0

        # Standard criticality: if derived from formal standard
        std_crit = 2.0 if finding.rule_reference else 0.5

        # Cross document impact
        cross_impact = 2.5 if finding.category == FindingCategory.LOGICAL.value else 1.0

        score = (
            (self.weights.severity * base_sev) +
            (self.weights.safety_impact * safety) +
            (self.weights.deviation_magnitude * dev_magnitude) +
            (self.weights.standard_criticality * std_crit) +
            (self.weights.confidence * finding.confidence * 2.0) +
            (self.weights.cross_document_impact * cross_impact)
        )
        return round(score, 2)

    def rank_findings(self, findings: List[Finding]) -> List[Finding]:
        """Calculates priority scores and returns findings sorted from most to least urgent."""
        for f in findings:
            f.priority_score = self.calculate_priority(f)

        # Sort descending by priority score, with Critical and High at the top
        ranked = sorted(findings, key=lambda f: f.priority_score, reverse=True)
        return ranked
