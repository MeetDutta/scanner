"""
Template Management Engine for SpecGuard.
Loads and indexes fixed domain document templates (Mechanical, Electrical, Chemical).
Provides expected sections, parameters, aliases, vocabulary, and local engineering rules.
"""

import json
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
RULES_DIR = BASE_DIR / "rules"


@dataclass
class ParameterDef:
    parameter_id: str
    parameter: str
    display_name: str
    aliases: List[str] = field(default_factory=list)
    value_type: str = "numeric"  # numeric, text, categorical, range, boolean
    unit: str = ""
    required: bool = False
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[float]] = None
    severity_on_deviation: str = "High"
    rule_reference: str = ""


@dataclass
class SectionDef:
    section_id: str
    number: str
    title: str
    required: bool = True
    order: int = 1
    description: str = ""
    expected_parameters: List[str] = field(default_factory=list)
    subsections: List[Dict[str, Any]] = field(default_factory=list)
    expected_columns: List[str] = field(default_factory=list)


@dataclass
class DomainTemplate:
    template_id: str
    template_version: str
    domain: str
    document_title: str
    description: str
    classification: str = ""
    sections: List[SectionDef] = field(default_factory=list)
    parameters: List[ParameterDef] = field(default_factory=list)
    vocabulary: Dict[str, Any] = field(default_factory=dict)
    rules: List[Dict[str, Any]] = field(default_factory=list)


class TemplateManager:
    """Singleton/Static manager to load and retrieve domain templates."""
    _cache: Dict[str, DomainTemplate] = {}

    @classmethod
    def get_template(cls, domain: str) -> DomainTemplate:
        domain_clean = (domain or "mechanical").lower().strip()
        if domain_clean in cls._cache:
            return cls._cache[domain_clean]

        tmpl_dir = TEMPLATES_DIR / domain_clean
        rules_dir = RULES_DIR / domain_clean

        # 1. Load template.json
        meta: Dict[str, Any] = {}
        tmpl_file = tmpl_dir / "template.json"
        if tmpl_file.exists():
            try:
                with open(tmpl_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            except Exception as e:
                logger.error("Failed loading template file %s: %s", tmpl_file, e)

        # 2. Load sections.json
        sections: List[SectionDef] = []
        sec_file = tmpl_dir / "sections.json"
        if sec_file.exists():
            try:
                with open(sec_file, "r", encoding="utf-8") as f:
                    sec_data = json.load(f)
                    for item in sec_data:
                        sections.append(SectionDef(
                            section_id=item.get("section_id", ""),
                            number=item.get("number", ""),
                            title=item.get("title", ""),
                            required=item.get("required", True),
                            order=item.get("order", 1),
                            description=item.get("description", ""),
                            expected_parameters=item.get("expected_parameters", []),
                            subsections=item.get("subsections", []),
                            expected_columns=item.get("expected_columns", [])
                        ))
            except Exception as e:
                logger.error("Failed loading sections file %s: %s", sec_file, e)

        # 3. Load parameters.json
        parameters: List[ParameterDef] = []
        param_file = tmpl_dir / "parameters.json"
        if param_file.exists():
            try:
                with open(param_file, "r", encoding="utf-8") as f:
                    param_data = json.load(f)
                    for p in param_data:
                        parameters.append(ParameterDef(
                            parameter_id=p.get("parameter_id", ""),
                            parameter=p.get("parameter", ""),
                            display_name=p.get("display_name", ""),
                            aliases=p.get("aliases", []),
                            value_type=p.get("value_type", "numeric"),
                            unit=p.get("unit", ""),
                            required=p.get("required", False),
                            min_value=p.get("min_value"),
                            max_value=p.get("max_value"),
                            allowed_values=p.get("allowed_values"),
                            severity_on_deviation=p.get("severity_on_deviation", "High"),
                            rule_reference=p.get("rule_reference", "")
                        ))
            except Exception as e:
                logger.error("Failed loading parameters file %s: %s", param_file, e)

        # 4. Load vocabulary.json
        vocab: Dict[str, Any] = {}
        vocab_file = tmpl_dir / "vocabulary.json"
        if vocab_file.exists():
            try:
                with open(vocab_file, "r", encoding="utf-8") as f:
                    vocab = json.load(f)
            except Exception as e:
                logger.error("Failed loading vocabulary file %s: %s", vocab_file, e)

        # 5. Load rules.json
        rules: List[Dict[str, Any]] = []
        rule_file = rules_dir / "rules.json"
        if rule_file.exists():
            try:
                with open(rule_file, "r", encoding="utf-8") as f:
                    rules = json.load(f)
            except Exception as e:
                logger.error("Failed loading rules file %s: %s", rule_file, e)

        template = DomainTemplate(
            template_id=meta.get("template_id", f"TMPL-{domain_clean.upper()}-001"),
            template_version=meta.get("template_version", "1.0.0"),
            domain=domain_clean,
            document_title=meta.get("document_title", f"{domain_clean.capitalize()} Engineering Specification"),
            description=meta.get("description", ""),
            classification=meta.get("classification", ""),
            sections=sections,
            parameters=parameters,
            vocabulary=vocab,
            rules=rules
        )

        cls._cache[domain_clean] = template
        return template

    @classmethod
    def match_parameter_alias(cls, domain: str, phrase: str) -> Optional[ParameterDef]:
        """Finds matching parameter definition by exact match or registered alias."""
        tmpl = cls.get_template(domain)
        p_lower = phrase.lower().strip()
        for p in tmpl.parameters:
            if p_lower == p.parameter.lower() or p_lower == p.display_name.lower():
                return p
            for alias in p.aliases:
                if p_lower == alias.lower():
                    return p
        return None

    @classmethod
    def clear_cache(cls):
        cls._cache.clear()
