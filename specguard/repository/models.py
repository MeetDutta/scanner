"""
Data Models for SpecGuard Local Document Comparison Repository.
Defines immutable representations for documents, comparison sessions, and version diffs.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from datetime import datetime


@dataclass
class RepositoryDocument:
    document_id: str          # Stable ID: DOC-2026-000001
    family_id: str            # Document family grouping revisions
    revision_number: int      # Revision 1, 2, 3...
    filename: str
    original_path: str
    file_type: str
    file_size: int
    sha256: str
    page_count: int
    created_at: str
    stored_locally: bool = True


@dataclass
class ComparisonRecord:
    comparison_id: str        # Stable ID: CMP-2026-000001
    document_id: str
    document_filename: str
    document_sha256: str
    domain: str
    status: str = "COMPLETED"
    analysis_started_at: str = ""
    analysis_completed_at: str = ""
    duration_ms: int = 0
    model_version: str = "Deterministic-v1.0"
    standards_used: List[str] = field(default_factory=list)
    total_findings: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0
    annotated_pdf_path: Optional[str] = None
    annotated_docx_path: Optional[str] = None
    report_html_path: Optional[str] = None
    findings_json_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FindingDiffItem:
    finding_id: str
    category: str
    severity: str
    location: str
    explanation: str
    status: str  # 'NEW', 'RESOLVED', 'PERSISTENT', 'MODIFIED'
    comparison_a_val: Optional[str] = None
    comparison_b_val: Optional[str] = None


@dataclass
class VersionComparisonDiff:
    comparison_a_id: str
    comparison_b_id: str
    document_filename: str
    model_a: str
    model_b: str
    new_findings_count: int
    resolved_findings_count: int
    persistent_findings_count: int
    diff_items: List[FindingDiffItem] = field(default_factory=list)
