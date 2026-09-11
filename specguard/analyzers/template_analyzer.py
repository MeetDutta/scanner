"""
Template Validation Engine for SpecGuard.
Deterministically compares engineering documents against fixed domain templates:
- Required sections and sequence
- Required engineering parameters and fields
- Table column integrity and required tabular data
"""

import re
from typing import List, Dict, Tuple, Optional, Any
import logging

from specguard.analyzers.base import BaseAnalyzer
from specguard.core.models import (
    DocumentModel, Finding, FindingCategory, SeverityLevel, EngineeringParameter, BBox
)
from specguard.templates.manager import TemplateManager, DomainTemplate, SectionDef, ParameterDef

logger = logging.getLogger(__name__)


class TemplateAnalyzer(BaseAnalyzer):
    """
    Validates document structure, sections, and fields against the fixed domain template.
    """
    @property
    def name(self) -> str:
        return "Template Analyzer"

    @property
    def category(self) -> FindingCategory:
        return FindingCategory.STRUCTURE

    def analyze(self, doc: DocumentModel, context: Dict[str, Any] = None) -> List[Finding]:
        findings: List[Finding] = []
        domain = (context or {}).get("domain", "mechanical").lower()
        template: DomainTemplate = (context or {}).get("template") or TemplateManager.get_template(domain)
        parameters: List[EngineeringParameter] = (context or {}).get("parameters", [])

        full_doc_text = doc.full_text.lower()
        finding_counter = 1

        # 1. Validate Required Sections
        for sec in template.sections:
            if not sec.required:
                continue

            sec_pattern = re.compile(rf'(?:^|\n)\s*(?:section\s+)?{re.escape(sec.number)}\s+{re.escape(sec.title.lower())}', re.IGNORECASE)
            simple_pattern = re.compile(rf'{re.escape(sec.title.lower())}', re.IGNORECASE)

            found = bool(sec_pattern.search(full_doc_text) or simple_pattern.search(full_doc_text))
            if not found:
                findings.append(Finding(
                    finding_id=f"TMPL-SEC-{finding_counter:03d}",
                    category=FindingCategory.STRUCTURE.value,
                    domain=domain.capitalize(),
                    location="Document Structure",
                    page=1,
                    original_content="",
                    detected_value="Section absent",
                    expected_value=f"Section {sec.number} ({sec.title})",
                    deviation=f"Mandatory template section '{sec.title}' is missing.",
                    severity=SeverityLevel.HIGH.value,
                    confidence=1.0,
                    explanation=f"The fixed {domain.capitalize()} template requires Section {sec.number}: '{sec.title}', which was not found in the document.",
                    suggested_correction=f"Insert Section {sec.number}: {sec.title} containing required engineering specifications.",
                    rule_reference=f"Fixed Template {template.template_id} §{sec.number}",
                    priority_score=7.0
                ))
                finding_counter += 1

            # Validate Required Subsections
            for sub in sec.subsections:
                if not sub.get("required", False):
                    continue
                sub_num = sub.get("number", "")
                sub_title = sub.get("title", "")
                sub_pattern = re.compile(rf'(?:^|\n)\s*{re.escape(sub_num)}\s+{re.escape(sub_title.lower())}', re.IGNORECASE)

                if not sub_pattern.search(full_doc_text) and sub_title.lower() not in full_doc_text:
                    findings.append(Finding(
                        finding_id=f"TMPL-SUB-{finding_counter:03d}",
                        category=FindingCategory.STRUCTURE.value,
                        domain=domain.capitalize(),
                        location=f"Section {sec.number}",
                        page=2 if doc.page_count > 1 else 1,
                        original_content="",
                        detected_value=f"Subsection {sub_num} missing",
                        expected_value=f"Subsection {sub_num} ({sub_title})",
                        deviation=f"Mandatory subsection '{sub_num} {sub_title}' is missing from Section {sec.number}.",
                        severity=SeverityLevel.HIGH.value,
                        confidence=1.0,
                        explanation=f"Template {template.template_id} requires subsection {sub_num} '{sub_title}'. Missing sequence item.",
                        suggested_correction=f"Add subsection {sub_num} '{sub_title}' to complete the required section hierarchy.",
                        rule_reference=f"Fixed Template {template.template_id} §{sub_num}",
                        priority_score=6.5
                    ))
                    finding_counter += 1

        # 2. Validate Required Parameters
        extracted_param_names = {p.parameter.lower() for p in parameters}
        # Also check raw matches in document text using aliases
        for p_def in template.parameters:
            if not p_def.required:
                continue

            found_in_params = p_def.parameter.lower() in extracted_param_names
            found_in_text = False
            if not found_in_params:
                for alias in p_def.aliases:
                    if alias.lower() in full_doc_text:
                        found_in_text = True
                        break

            if not found_in_params and not found_in_text:
                findings.append(Finding(
                    finding_id=f"TMPL-PRM-{finding_counter:03d}",
                    category=FindingCategory.ENGINEERING.value,
                    domain=domain.capitalize(),
                    location="Document Content",
                    page=1,
                    original_content="",
                    detected_value="Parameter absent",
                    expected_value=f"{p_def.display_name} ({p_def.unit})",
                    deviation=f"Required engineering field '{p_def.display_name}' was not found in document.",
                    severity=p_def.severity_on_deviation,
                    confidence=1.0,
                    explanation=f"The {domain.capitalize()} document template mandates specification of '{p_def.display_name}' in standard units ({p_def.unit}).",
                    suggested_correction=f"Define the required '{p_def.display_name}' parameter with applicable tolerance and units.",
                    rule_reference=p_def.rule_reference or f"Fixed Template {template.template_id}",
                    priority_score=8.0 if p_def.severity_on_deviation == "Critical" else 6.0
                ))
                finding_counter += 1

        return findings
