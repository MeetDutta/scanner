"""
Local Engineering Standards and Rule Comparison Engine for SpecGuard.
Compares extracted engineering parameters against machine-readable JSON/YAML standards.
Strictly 100% offline. Adheres to explicit scope: only installed local rules are evaluated.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Any
import logging

from specguard.analyzers.base import BaseAnalyzer
from specguard.core.models import (
    DocumentModel, Finding, FindingCategory, SeverityLevel, EngineeringParameter, BBox
)
from specguard.core.config import STANDARDS_DIR
from specguard.analyzers.engineering import UnitNormalizer

logger = logging.getLogger(__name__)


class StandardsKnowledgeBase:
    """Loads and indexes local engineering standard rule files."""

    @staticmethod
    def load_rules_for_domain(domain: str) -> List[Dict[str, Any]]:
        domain_dir = STANDARDS_DIR / domain.lower()
        if not domain_dir.exists():
            return []

        rules = []
        for file_path in domain_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    file_rules = data.get("rules", [])
                    std_name = data.get("standard_name", file_path.stem)
                    for r in file_rules:
                        r["_standard_name"] = std_name
                        rules.append(r)
            except Exception as e:
                logger.error("Failed loading standards rule file %s: %s", file_path, e)
        return rules


class StandardsAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Standards Compliance Analyzer"

    @property
    def category(self) -> FindingCategory:
        return FindingCategory.STANDARDS

    def analyze(self, doc: DocumentModel, context: Dict[str, Any] = None) -> List[Finding]:
        findings: List[Finding] = []
        finding_counter = 1

        parameters: List[EngineeringParameter] = (context or {}).get("parameters", [])
        active_domain = (context or {}).get("domain", "mechanical").lower()

        # Load installed local standards rules for active domain
        rules = StandardsKnowledgeBase.load_rules_for_domain(active_domain)
        if not rules:
            logger.info("No local standard rules installed for domain '%s'", active_domain)
            return findings

        for param in parameters:
            for rule in rules:
                rule_param = rule.get("parameter", "").lower()
                if rule_param != param.parameter.lower():
                    continue

                # Ensure units are comparable
                rule_unit = rule.get("unit", "")
                norm_rule_val, norm_rule_unit = 0.0, ""
                val_to_check = param.normalized_value

                operator = rule.get("operator", "allowed_values")
                rule_id = rule.get("rule_id", f"STD-{finding_counter:03d}")
                severity = rule.get("severity", "High")
                ref = rule.get("reference", rule.get("_standard_name", "Local Standard"))
                desc = rule.get("description", "Standard requirement deviation")

                deviation_detected = False
                expected_str = ""
                deviation_str = ""

                # 1. Allowed discrete values (e.g. Voltage must be 230 V or 415 V)
                if operator == "allowed_values":
                    allowed = rule.get("allowed_values", [])
                    # Normalize allowed values
                    norm_allowed = [UnitNormalizer.normalize(float(v), rule_unit)[0] for v in allowed]
                    # Check tolerance match
                    if not any(abs(val_to_check - av) < 1e-3 for av in norm_allowed):
                        deviation_detected = True
                        expected_str = f"{', '.join(str(v) for v in allowed)} {rule_unit}"
                        diff = val_to_check - norm_allowed[0] if norm_allowed else 0
                        deviation_str = f"Deviation of {diff:+.1f} {rule_unit} from standard allowed set"

                # 2. Maximum limit (e.g. Tolerance <= 0.05 mm)
                elif operator in ["less_than_or_equal", "max"]:
                    max_allowed = float(rule.get("max_value", rule.get("expected_value", 0.0)))
                    norm_max, _ = UnitNormalizer.normalize(max_allowed, rule_unit)
                    if val_to_check > norm_max + 1e-4:
                        deviation_detected = True
                        expected_str = f"≤ {max_allowed} {rule_unit}"
                        deviation_str = f"Exceeds maximum allowable limit by +{val_to_check - norm_max:.3f} {norm_rule_unit or rule_unit}"

                # 3. Minimum limit (e.g. Insulation Resistance >= 10 MOhm)
                elif operator in ["greater_than_or_equal", "min"]:
                    min_allowed = float(rule.get("min_value", rule.get("expected_value", 0.0)))
                    norm_min, _ = UnitNormalizer.normalize(min_allowed, rule_unit)
                    if val_to_check < norm_min - 1e-4:
                        deviation_detected = True
                        expected_str = f"≥ {min_allowed} {rule_unit}"
                        deviation_str = f"Falls below minimum allowable limit by {val_to_check - norm_min:.3f} {rule_unit}"

                # 4. Range limit (e.g. Concentration 5% - 12%)
                elif operator == "range":
                    rng = rule.get("allowed_range", [0.0, 100.0])
                    norm_min, _ = UnitNormalizer.normalize(float(rng[0]), rule_unit)
                    norm_max, _ = UnitNormalizer.normalize(float(rng[1]), rule_unit)
                    if val_to_check < norm_min - 1e-4 or val_to_check > norm_max + 1e-4:
                        deviation_detected = True
                        expected_str = f"Range [{rng[0]} - {rng[1]}] {rule_unit}"
                        deviation_str = f"Value {val_to_check} falls outside standard range [{rng[0]} - {rng[1]}]"

                if deviation_detected:
                    findings.append(Finding(
                        finding_id=rule_id,
                        category=self.category.value,
                        domain=active_domain.title(),
                        location=f"Page {param.page}",
                        page=param.page,
                        bbox=param.bbox,
                        original_content=param.source_sentence,
                        detected_value=param.raw_value,
                        expected_value=expected_str,
                        deviation=deviation_str,
                        severity=severity,
                        confidence=0.97,
                        explanation=f"Configured rule '{rule_id}' indicates a deviation. {desc}",
                        suggested_correction=f"Verify and update specification to conform with expected {expected_str}.",
                        rule_reference=ref,
                        priority_score=8.0 if severity == "Critical" else 6.5
                    ))
                    finding_counter += 1

        return findings
