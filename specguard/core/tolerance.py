"""
SpecGuard Document Tolerance & Publication Readiness Engine.
Calculates transparent, normalized tolerance index, evaluates publication readiness
against configurable profiles, and persists reproducible tolerance decisions.
"""

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from pathlib import Path
import logging

from specguard.core.models import DocumentModel, Finding

logger = logging.getLogger(__name__)


@dataclass
class ToleranceProfile:
    """Configurable document inspection profile defining tolerance thresholds and weightings."""
    profile_id: str
    name: str
    description: str
    max_tolerance: float = 10.0
    max_critical: int = 0
    max_high: int = 2
    severity_weights: Dict[str, float] = field(default_factory=lambda: {
        "Critical": 10.0,
        "High": 5.0,
        "Medium": 2.0,
        "Low": 0.5,
        "Informational": 0.0
    })
    category_weights: Dict[str, float] = field(default_factory=lambda: {
        "Formatting": 1.0,
        "Structure": 1.2,
        "Grammar & Spelling": 0.8,
        "Table of Contents": 1.0,
        "Table": 1.0,
        "Figure": 1.0,
        "Equation": 1.0,
        "Cross-Reference": 1.0,
        "Engineering Parameter": 1.5,
        "Standards Deviation": 1.5,
        "Logical Contradiction": 1.5,
        "Semantic Inconsistency": 1.2,
        "IEEE Compliance": 1.5
    })

    def get_category_weight(self, category: str) -> float:
        cat_lower = (category or "").lower()
        for k, v in self.category_weights.items():
            if k.lower() in cat_lower or cat_lower in k.lower():
                return v
        return 1.0


# Standard built-in publication inspection profiles
BUILTIN_PROFILES: Dict[str, ToleranceProfile] = {
    "publication": ToleranceProfile(
        profile_id="publication",
        name="Publication / Submission",
        description="Formal pre-publication quality tolerance review for external release or submission.",
        max_tolerance=10.0,
        max_critical=0,
        max_high=2,
        severity_weights={"Critical": 10.0, "High": 5.0, "Medium": 2.0, "Low": 0.5, "Informational": 0.0},
        category_weights={
            "Formatting": 1.0, "Structure": 1.2, "Grammar & Spelling": 0.8,
            "Table of Contents": 1.0, "Table": 1.0, "Figure": 1.0, "Equation": 1.0,
            "Cross-Reference": 1.0, "Engineering Parameter": 1.5, "Standards Deviation": 1.5,
            "Logical Contradiction": 1.5, "Semantic Inconsistency": 1.2, "IEEE Compliance": 1.5
        }
    ),
    "strict_compliance": ToleranceProfile(
        profile_id="strict_compliance",
        name="Strict Compliance",
        description="Zero-defect critical tolerance policy for safety-critical and regulatory specifications.",
        max_tolerance=5.0,
        max_critical=0,
        max_high=0,
        severity_weights={"Critical": 15.0, "High": 8.0, "Medium": 3.0, "Low": 1.0, "Informational": 0.0}
    ),
    "internal_review": ToleranceProfile(
        profile_id="internal_review",
        name="Engineering Internal Review",
        description="Permissive draft tolerance profile for inter-departmental peer reviews.",
        max_tolerance=15.0,
        max_critical=0,
        max_high=5,
        severity_weights={"Critical": 10.0, "High": 5.0, "Medium": 2.0, "Low": 0.5, "Informational": 0.0}
    ),
    "academic": ToleranceProfile(
        profile_id="academic",
        name="Academic Submission",
        description="Scholarly publication tolerance focused on structure, formatting, and cross-citations.",
        max_tolerance=8.0,
        max_critical=0,
        max_high=2,
        severity_weights={"Critical": 10.0, "High": 5.0, "Medium": 2.0, "Low": 0.5, "Informational": 0.0}
    ),
    "client": ToleranceProfile(
        profile_id="client",
        name="Client Submission",
        description="Client-facing presentation and deliverable quality tolerance profile.",
        max_tolerance=7.0,
        max_critical=0,
        max_high=1,
        severity_weights={"Critical": 12.0, "High": 6.0, "Medium": 2.0, "Low": 0.5, "Informational": 0.0}
    )
}


@dataclass
class ToleranceResult:
    """Formal result of the document tolerance evaluation."""
    session_id: str
    document_no: str
    document_title: str
    revision: str
    inspection_profile: str
    inspection_date: str
    pages_inspected: int
    engine_version: str = "SpecGuard 1.0.0"

    raw_tolerance: float = 0.0
    normalization_factor: float = 1.0
    tolerance_index: float = 0.0  # LOWER IS BETTER
    maximum_acceptable_tolerance: float = 10.0
    tolerance_utilization: float = 0.0  # % of maximum acceptable
    acceptance_status: str = "WITHIN ACCEPTABLE TOLERANCE"
    status_reason: str = ""

    total_findings: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0
    category_summary: Dict[str, int] = field(default_factory=dict)

    formula_documentation: str = (
        "Raw Tolerance = Sum(Severity Weight x Category Weight). "
        "Tolerance Index = Raw Tolerance / Normalization Factor, where Normalization Factor = max(1.0, Pages / 10.0). "
        "Tolerance Utilization = (Tolerance Index / Maximum Acceptable Tolerance) x 100%."
    )
    human_disclaimer: str = (
        "This report represents automated inspection results generated from the configured "
        "inspection profile. Final approval, publication, or submission remains the responsibility "
        "of the authorized reviewer."
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToleranceResult':
        filtered = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**filtered)


class ToleranceCalculator:
    """Calculates and determines document publication tolerance indices."""

    @staticmethod
    def get_profile(profile_identifier: Optional[str] = None) -> ToleranceProfile:
        if not profile_identifier:
            return BUILTIN_PROFILES["publication"]

        clean = profile_identifier.lower().strip().replace(" ", "_").replace("/", "_")
        for k, p in BUILTIN_PROFILES.items():
            if k == clean or p.profile_id == clean or p.name.lower() == profile_identifier.lower():
                return p

        # Fallback to publication profile
        return BUILTIN_PROFILES["publication"]

    @staticmethod
    def extract_document_metadata(doc: DocumentModel, custom_meta: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Extracts Document No, Title, and Revision from user input, document AST, or text.
        Never fabricates values: returns 'Not Provided' if absent.
        """
        meta = {
            "document_no": "Not Provided",
            "document_title": "Not Provided",
            "revision": "Not Provided"
        }

        # 1. Custom user-provided metadata takes precedence
        if custom_meta:
            if custom_meta.get("document_no"):
                meta["document_no"] = str(custom_meta["document_no"]).strip()
            if custom_meta.get("document_title"):
                meta["document_title"] = str(custom_meta["document_title"]).strip()
            if custom_meta.get("revision"):
                meta["revision"] = str(custom_meta["revision"]).strip()

        # 2. Extract from document if still 'Not Provided'
        full_text_p1 = ""
        if doc.pages and len(doc.pages) > 0:
            full_text_p1 = doc.pages[0].text or ""

        # Title extraction: PDF metadata -> first big heading -> filename stem
        if meta["document_title"] == "Not Provided":
            pdf_title = (doc.metadata or {}).get("title")
            if pdf_title and len(pdf_title.strip()) > 3 and not pdf_title.lower().endswith(".pdf"):
                meta["document_title"] = pdf_title.strip()
            elif doc.sections and len(doc.sections) > 0:
                meta["document_title"] = doc.sections[0].title.strip()
            elif Path(doc.file_path).stem:
                # Clean filename stem
                clean_name = Path(doc.file_path).stem.replace("_", " ").replace("-", " ")
                # Strip leading numbers/dates
                clean_name = re.sub(r'^[0-9A-Fa-f]{16,64}\b', '', clean_name).strip()
                if clean_name:
                    meta["document_title"] = clean_name.title()

        # Document No extraction: Regex check on Page 1 or header text
        if meta["document_no"] == "Not Provided":
            doc_no_m = re.search(
                r'(?:Document\s*(?:No\.?|Number)|Doc\s*(?:No\.?|#)|Spec\s*(?:No\.?|#))\s*[:\-]?\s*([A-Za-z0-9\-_/]+)',
                full_text_p1, re.IGNORECASE
            )
            if doc_no_m:
                meta["document_no"] = doc_no_m.group(1).strip()
            else:
                # Common engineering code pattern e.g. ENG-MECH-042 or ASME-SEC-VIII
                code_m = re.search(r'\b([A-Z]{2,6}-[A-Z0-9]{2,6}-[0-9]{2,6})\b', full_text_p1)
                if code_m:
                    meta["document_no"] = code_m.group(1).strip()

        # Revision extraction: Regex check on Page 1 or header
        if meta["revision"] == "Not Provided":
            rev_m = re.search(
                r'(?:Revision|Rev\.?|Version|Ver\.?)\s*[:\-]?\s*(Rev\.?\s*[0-9A-Za-z\-_.]+|[0-9A-Za-z\-_.]+)',
                full_text_p1, re.IGNORECASE
            )
            if rev_m:
                val = rev_m.group(1).strip()
                if not val.lower().startswith("rev") and not val.lower().startswith("v"):
                    val = f"Rev. {val}"
                meta["revision"] = val

        return meta

    @classmethod
    def calculate(
        cls,
        session_id: str,
        doc: DocumentModel,
        findings: List[Finding],
        profile_identifier: Optional[str] = None,
        custom_meta: Optional[Dict[str, str]] = None,
        custom_max_tolerance: Optional[float] = None
    ) -> ToleranceResult:
        """Calculates normalized Tolerance Index and evaluates acceptance status."""
        profile = cls.get_profile(profile_identifier)
        max_tol = custom_max_tolerance if custom_max_tolerance is not None and custom_max_tolerance > 0 else profile.max_tolerance

        pages_count = max(1, doc.page_count)
        metadata = cls.extract_document_metadata(doc, custom_meta)

        crit_count = sum(1 for f in findings if f.severity == "Critical")
        high_count = sum(1 for f in findings if f.severity == "High")
        med_count = sum(1 for f in findings if f.severity == "Medium")
        low_count = sum(1 for f in findings if f.severity == "Low")
        info_count = sum(1 for f in findings if f.severity == "Informational")

        # Standardized Category Counts
        category_summary = {
            "Formatting": 0,
            "Structure": 0,
            "Grammar": 0,
            "TOC": 0,
            "Figures": 0,
            "Tables": 0,
            "References": 0,
            "Engineering": 0,
            "Standards": 0
        }

        raw_tolerance = 0.0
        for f in findings:
            sev_w = profile.severity_weights.get(f.severity, 1.0)
            cat_w = profile.get_category_weight(f.category)
            raw_tolerance += (sev_w * cat_w)

            c_lower = (f.category or "").lower()
            if "format" in c_lower or "typography" in c_lower or "layout" in c_lower:
                category_summary["Formatting"] += 1
            elif "structure" in c_lower or "outline" in c_lower:
                category_summary["Structure"] += 1
            elif "grammar" in c_lower or "spelling" in c_lower:
                category_summary["Grammar"] += 1
            elif "toc" in c_lower or "table of contents" in c_lower:
                category_summary["TOC"] += 1
            elif "figure" in c_lower or "drawing" in c_lower:
                category_summary["Figures"] += 1
            elif "table" in c_lower:
                category_summary["Tables"] += 1
            elif "reference" in c_lower or "citation" in c_lower or "cross" in c_lower:
                category_summary["References"] += 1
            elif "engineering" in c_lower or "parameter" in c_lower:
                category_summary["Engineering"] += 1
            elif "standard" in c_lower or "ieee" in c_lower or "iso" in c_lower:
                category_summary["Standards"] += 1
            else:
                category_summary["Formatting"] += 1

        # Transparent Normalization Factor based on document length:
        # Normalization factor = max(1.0, Pages / 10.0)
        norm_factor = max(1.0, round(pages_count / 10.0, 2))
        tolerance_index = round(raw_tolerance / norm_factor, 1)

        # Tolerance Utilization: (Tolerance Index / Maximum Acceptable) * 100
        tolerance_utilization = round((tolerance_index / max(0.1, max_tol)) * 100, 1)

        # Determine Acceptance Status based on configured limits
        if crit_count > profile.max_critical:
            acceptance_status = "NOT ELIGIBLE"
            status_reason = (
                f"Document contains {crit_count} critical finding(s). "
                f"Configured profile requires at most {profile.max_critical} critical findings."
            )
        elif high_count > profile.max_high:
            if profile.max_high == 0:
                acceptance_status = "NOT ELIGIBLE"
                status_reason = (
                    f"Document contains {high_count} high-severity finding(s). "
                    f"Configured profile requires 0 high-severity findings."
                )
            else:
                acceptance_status = "ABOVE ACCEPTABLE TOLERANCE"
                status_reason = (
                    f"Document contains {high_count} high-severity finding(s). "
                    f"Configured profile allows at most {profile.max_high} high-severity findings."
                )
        elif tolerance_index > max_tol:
            acceptance_status = "ABOVE ACCEPTABLE TOLERANCE"
            status_reason = (
                f"Calculated Tolerance Index ({tolerance_index}) exceeds configured maximum "
                f"acceptable tolerance threshold ({max_tol})."
            )
        else:
            acceptance_status = "WITHIN ACCEPTABLE TOLERANCE"
            status_reason = (
                f"Calculated Tolerance Index ({tolerance_index}) is within configured maximum "
                f"acceptable tolerance threshold ({max_tol})."
            )

        # Inspection Date
        inspection_date = datetime.now().strftime("%d %B %Y")

        return ToleranceResult(
            session_id=session_id,
            document_no=metadata["document_no"],
            document_title=metadata["document_title"],
            revision=metadata["revision"],
            inspection_profile=profile.name,
            inspection_date=inspection_date,
            pages_inspected=pages_count,
            raw_tolerance=round(raw_tolerance, 2),
            normalization_factor=norm_factor,
            tolerance_index=tolerance_index,
            maximum_acceptable_tolerance=max_tol,
            tolerance_utilization=tolerance_utilization,
            acceptance_status=acceptance_status,
            status_reason=status_reason,
            total_findings=len(findings),
            critical_count=crit_count,
            high_count=high_count,
            medium_count=med_count,
            low_count=low_count,
            info_count=info_count,
            category_summary=category_summary
        )
