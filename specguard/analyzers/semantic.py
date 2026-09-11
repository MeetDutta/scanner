"""
Semantic Proposition Analysis Engine for SpecGuard.
Extracts structured propositions (Entity, Parameter, Value, Unit, Condition, Location)
and detects semantic ambiguities such as ungrounded specifications and missing operational conditions.
"""

import re
from typing import List, Dict, Optional, Any
import logging

from specguard.analyzers.base import BaseAnalyzer
from specguard.core.models import (
    DocumentModel, Finding, FindingCategory, SeverityLevel, EngineeringParameter, BBox
)

logger = logging.getLogger(__name__)


class SemanticAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Semantic Analyzer"

    @property
    def category(self) -> FindingCategory:
        return FindingCategory.SEMANTIC

    def analyze(self, doc: DocumentModel, context: Dict[str, Any] = None) -> List[Finding]:
        findings: List[Finding] = []
        finding_counter = 1

        # Retrieve extracted parameters from context or extract
        parameters: List[EngineeringParameter] = (context or {}).get("parameters", [])

        for param in parameters:
            # 1. Semantic Check: Pressure without gauge or absolute specification (barg vs bara)
            if param.parameter == "pressure" and param.unit.lower() == "bar":
                if "barg" not in param.source_sentence.lower() and "bara" not in param.source_sentence.lower():
                    findings.append(Finding(
                        finding_id=f"SEM-PRS-{finding_counter:03d}",
                        category=self.category.value,
                        domain="Mechanical",
                        location=f"Page {param.page}",
                        page=param.page,
                        bbox=param.bbox,
                        original_content=param.source_sentence,
                        detected_value=f"{param.raw_value} (ambiguous datum)",
                        expected_value="Explicit gauge (barg) or absolute (bara) datum",
                        deviation="Ambiguous pressure reference datum",
                        severity=SeverityLevel.MEDIUM.value,
                        confidence=0.88,
                        explanation="Engineering specification specifies pressure in 'bar' without designating whether it is gauge pressure (barg) or absolute pressure (bara).",
                        suggested_correction="Clarify pressure datum as 'barg' (gauge) or 'bara' (absolute).",
                        rule_reference="Process Engineering Specification Standard PEP-102",
                        priority_score=4.5
                    ))
                    finding_counter += 1

            # 2. Semantic Check: AC Voltage without Phase indication (e.g. 415 V requires 3-phase, 230 V requires 1-phase)
            elif param.parameter == "voltage" and param.normalized_value >= 100:
                sent_lower = param.source_sentence.lower()
                has_phase = any(kw in sent_lower for kw in ["1-phase", "3-phase", "single-phase", "three-phase", "3ph", "1ph", "dc", "direct current"])
                if not has_phase and param.normalized_value in [230.0, 400.0, 415.0, 690.0]:
                    expected_phase = "3-Phase AC" if param.normalized_value >= 400 else "1-Phase AC"
                    findings.append(Finding(
                        finding_id=f"SEM-PHS-{finding_counter:03d}",
                        category=self.category.value,
                        domain="Electrical",
                        location=f"Page {param.page}",
                        page=param.page,
                        bbox=param.bbox,
                        original_content=param.source_sentence,
                        detected_value=f"{param.raw_value} (Unspecified Phase)",
                        expected_value=f"{param.raw_value}, {expected_phase}",
                        deviation="Missing electrical phase configuration",
                        severity=SeverityLevel.MEDIUM.value,
                        confidence=0.89,
                        explanation=f"Voltage specification '{param.raw_value}' lacks explicit AC phase configuration (e.g., 3-Phase vs Single-Phase).",
                        suggested_correction=f"Specify '{param.raw_value}, {expected_phase}, 50/60 Hz'.",
                        rule_reference="IEC 60038 / IEEE 141 (Electric Power Distribution)",
                        priority_score=4.8
                    ))
                    finding_counter += 1

        return findings
