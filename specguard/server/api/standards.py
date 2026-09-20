"""
Engineering Standards, Domain Templates, and Rules API for SpecGuard.
Exposes fixed domain templates (Mechanical, Electrical, Chemical) and
locally installed standards rule specifications without external network calls.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from dataclasses import asdict
import logging

from specguard.templates.manager import TemplateManager
from specguard.analyzers.standards import StandardsKnowledgeBase
from specguard.core.profiles import ProfileRegistry

logger = logging.getLogger("SpecGuard.API.Standards")
router = APIRouter(prefix="/standards", tags=["standards"])

DOMAINS = ["mechanical", "electrical", "chemical"]


@router.get("/profiles")
def list_document_profiles() -> List[Dict[str, Any]]:
    """Returns all supported document compliance profiles (Mechanical, Electrical, Chemical, IEEE, Academic)."""
    return ProfileRegistry.list_profiles()


@router.get("")
def list_standards_and_templates() -> List[Dict[str, Any]]:
    """Returns domain templates and installed standards overview."""
    results = []
    for domain in DOMAINS:
        tmpl = TemplateManager.get_template(domain)
        rules = StandardsKnowledgeBase.load_rules_for_domain(domain)

        results.append({
            "domain": domain.capitalize(),
            "domain_key": domain,
            "template_id": tmpl.template_id,
            "document_title": tmpl.document_title,
            "description": tmpl.description,
            "classification": tmpl.classification,
            "sections_count": len(tmpl.sections),
            "parameters_count": len(tmpl.parameters),
            "rules_count": len(rules) + len(tmpl.rules),
            "standards_installed": [r.get("_standard_name", "Local Rule") for r in rules[:3]]
        })
    return results


@router.get("/{domain}")
def get_domain_template_details(domain: str) -> Dict[str, Any]:
    """Returns comprehensive template details, sections, parameters, and rules for a domain."""
    d_clean = domain.lower().strip()
    if d_clean not in DOMAINS:
        raise HTTPException(status_code=404, detail=f"Domain '{domain}' not found. Supported: {', '.join(DOMAINS)}")

    tmpl = TemplateManager.get_template(d_clean)
    installed_rules = StandardsKnowledgeBase.load_rules_for_domain(d_clean)

    sections_data = [asdict(s) for s in tmpl.sections]
    parameters_data = [asdict(p) for p in tmpl.parameters]

    # Merge template rules and installed standards rules
    all_rules = list(tmpl.rules)
    for ir in installed_rules:
        if not any(r.get("rule_id") == ir.get("rule_id") for r in all_rules):
            all_rules.append(ir)

    return {
        "domain": d_clean.capitalize(),
        "domain_key": d_clean,
        "template_id": tmpl.template_id,
        "template_version": tmpl.template_version,
        "document_title": tmpl.document_title,
        "description": tmpl.description,
        "classification": tmpl.classification,
        "sections": sections_data,
        "parameters": parameters_data,
        "vocabulary_sample": list(tmpl.vocabulary.keys())[:20] if isinstance(tmpl.vocabulary, dict) else [],
        "rules": all_rules
    }
