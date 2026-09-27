"""
Tests for SpecGuard Document Tolerance & Publication Readiness Report Engine.
Verifies all 6 acceptance criteria specified in Section 35 of the specification:
1. Analysis with findings (tolerance index, status, metadata)
2. Analysis with zero findings (tolerance index = 0, within tolerance)
3. Analysis with critical findings (critical policy -> NOT ELIGIBLE)
4. Same document run twice produces distinct Session IDs
5. Historical session report uses persisted tolerance result
6. Profile change affects new evaluations without mutating historical reports
7. PDF and HTML exports follow standard naming and do NOT dump detailed error lists
"""

import json
from pathlib import Path
import pytest
import pymupdf

from specguard.core.models import DocumentModel, Finding, BBox
from specguard.core.tolerance import ToleranceProfile, ToleranceResult, ToleranceCalculator, BUILTIN_PROFILES
from specguard.export.report_generator import ReportGenerator
from specguard.storage.database import DatabaseManager
from specguard.repository.manager import RepositoryManager
from specguard.core.pipeline import AnalysisPipeline

DEMO_DIR = Path(__file__).resolve().parent.parent / "demo_samples"


@pytest.fixture
def clean_db(tmp_path):
    db_file = tmp_path / "test_specguard.db"
    db = DatabaseManager(db_path=str(db_file))
    return db


def create_sample_doc(page_count: int = 10, title: str = "Thermal System Specification") -> DocumentModel:
    return DocumentModel(
        file_path=str(DEMO_DIR / "sample.pdf"),
        file_type="PDF",
        file_hash="abc123hash",
        file_size=10240,
        page_count=page_count,
        pages=[],
        metadata={"title": title}
    )


def test_1_analysis_with_findings(clean_db):
    """Test 1: Analysis with findings calculates valid tolerance index, status, and metadata."""
    doc = create_sample_doc(page_count=20, title="Avionics Cooling Architecture")
    findings = [
        Finding(
            finding_id="F-001",
            category="Formatting",
            severity="Medium",
            page=2,
            confidence=0.9,
            message="Non-standard font size",
            explanation="Font size 11.5pt detected",
            suggested_fix="Use 12pt"
        ),
        Finding(
            finding_id="F-002",
            category="Structure",
            severity="High",
            page=3,
            confidence=0.95,
            message="Missing mandatory section",
            explanation="Section 3.2 missing",
            suggested_fix="Add section"
        )
    ]

    custom_meta = {
        "document_no": "ENG-MECH-042",
        "revision": "Rev. 03"
    }

    result = ToleranceCalculator.calculate(
        session_id="SG-20260927-00124",
        doc=doc,
        findings=findings,
        profile_identifier="publication",
        custom_meta=custom_meta,
        custom_max_tolerance=10.0
    )

    # 1. Session ID exists and matches
    assert result.session_id == "SG-20260927-00124"
    # 2. Document No exists
    assert result.document_no == "ENG-MECH-042"
    assert result.document_title == "Avionics Cooling Architecture"
    assert result.revision == "Rev. 03"
    # 3. Tolerance Index calculated (lower is better, > 0)
    assert result.tolerance_index > 0.0
    # 4. Maximum tolerance shown
    assert result.maximum_acceptable_tolerance == 10.0
    # 5. Status calculated
    assert result.acceptance_status == "WITHIN ACCEPTABLE TOLERANCE"
    assert result.tolerance_utilization > 0.0
    assert result.total_findings == 2
    assert result.medium_count == 1
    assert result.high_count == 1
    assert result.critical_count == 0


def test_2_analysis_with_zero_findings(clean_db):
    """Test 2: Analysis with zero findings yields 0.0 tolerance index and acceptable status."""
    doc = create_sample_doc(page_count=15, title="Clean Engineering Specification")
    findings = []

    result = ToleranceCalculator.calculate(
        session_id="SG-20260927-00001",
        doc=doc,
        findings=findings,
        profile_identifier="publication",
        custom_meta={"document_no": "SPEC-001"}
    )

    assert result.tolerance_index == 0.0
    assert result.maximum_acceptable_tolerance == 10.0
    assert result.tolerance_utilization == 0.0
    assert result.acceptance_status == "WITHIN ACCEPTABLE TOLERANCE"
    assert result.total_findings == 0


def test_3_analysis_with_critical_findings(clean_db):
    """Test 3: Analysis with critical findings triggers NOT ELIGIBLE when max_critical=0."""
    doc = create_sample_doc(page_count=50, title="Critical Safety System")
    # Even if total numerical index is low, critical issues should make it NOT ELIGIBLE
    findings = [
        Finding(
            finding_id="CRIT-001",
            category="Standards Deviation",
            severity="Critical",
            page=5,
            confidence=0.99,
            message="Grounding circuit safety violation",
            explanation="Exceeds allowable leakage",
            suggested_fix="Modify circuit"
        )
    ]

    result = ToleranceCalculator.calculate(
        session_id="SG-20260927-00666",
        doc=doc,
        findings=findings,
        profile_identifier="publication"  # max_critical=0
    )

    assert result.critical_count == 1
    assert result.acceptance_status == "NOT ELIGIBLE"
    assert "critical" in result.status_reason.lower()


def test_4_same_document_run_twice_distinct_session_ids(tmp_path):
    """Test 4: Running the same document twice generates distinct session IDs."""
    pdf_in = DEMO_DIR / "mechanical_sample_with_errors.pdf"
    if not pdf_in.exists():
        pytest.skip("Demo sample not found")

    db = DatabaseManager(db_path=str(tmp_path / "test_pipeline.db"))
    pipeline = AnalysisPipeline(db=db)

    doc1, findings1, session_id1 = pipeline.run_analysis(str(pdf_in), domain="mechanical")
    doc2, findings2, session_id2 = pipeline.run_analysis(str(pdf_in), domain="mechanical")

    assert session_id1 != session_id2
    assert session_id1 is not None and len(session_id1) > 0
    assert session_id2 is not None and len(session_id2) > 0


def test_5_historical_session_persisted_result(clean_db):
    """Test 5: Generating report from historical session uses persisted tolerance result."""
    session_id = "SG-20260927-HIST01"
    doc = create_sample_doc(page_count=10, title="Historical Archival Spec")
    findings = [
        Finding(
            finding_id="F-HIST",
            category="Formatting",
            severity="Low",
            page=1,
            confidence=0.9,
            message="Margin drift",
            explanation="Left margin 22mm",
            suggested_fix="Set 25mm"
        )
    ]

    initial_result = ToleranceCalculator.calculate(
        session_id=session_id,
        doc=doc,
        findings=findings,
        profile_identifier="publication",
        custom_meta={"document_no": "ENG-HIST-01"}
    )

    clean_db.save_tolerance_report(initial_result.to_dict())

    # Retrieve from DB as a historical lookup
    retrieved = clean_db.get_tolerance_report(session_id)
    assert retrieved is not None
    assert retrieved["session_id"] == session_id
    assert retrieved["document_no"] == "ENG-HIST-01"
    assert retrieved["tolerance_index"] == initial_result.tolerance_index
    assert retrieved["acceptance_status"] == initial_result.acceptance_status


def test_6_profile_change_affects_new_evaluations_without_mutating_old(clean_db):
    """Test 6: Inspection profile change applies to new evaluations without changing persisted records."""
    session_1 = "SG-SESSION-NORM"
    session_2 = "SG-SESSION-STRICT"

    doc = create_sample_doc(page_count=10)
    findings = [
        Finding(
            finding_id="F-1",
            category="Engineering Parameter",
            severity="High",
            page=2,
            confidence=0.9,
            message="Torque out of spec",
            explanation="Value 45Nm",
            suggested_fix="Set 50Nm"
        )
    ]

    # Session 1 evaluated under internal_review (max_tolerance=15.0)
    res_1 = ToleranceCalculator.calculate(session_1, doc, findings, profile_identifier="internal_review")
    clean_db.save_tolerance_report(res_1.to_dict())
    assert res_1.acceptance_status == "WITHIN ACCEPTABLE TOLERANCE"

    # Session 2 evaluated under strict_compliance (max_tolerance=5.0, max_high=0)
    res_2 = ToleranceCalculator.calculate(session_2, doc, findings, profile_identifier="strict_compliance")
    clean_db.save_tolerance_report(res_2.to_dict())
    assert res_2.acceptance_status == "NOT ELIGIBLE"

    # Historical Session 1 remains untouched
    hist_1 = clean_db.get_tolerance_report(session_1)
    assert hist_1["acceptance_status"] == "WITHIN ACCEPTABLE TOLERANCE"
    assert hist_1["maximum_acceptable_tolerance"] == 15.0


def test_7_pdf_and_html_generation_and_naming(tmp_path):
    """Test 7: PDF and HTML generation follow standard naming and contain concise summary without defect dumps."""
    doc = create_sample_doc(page_count=42, title="Thermal System Specification")
    findings = [
        Finding(
            finding_id=f"F-{i:03d}",
            category="Formatting" if i % 2 == 0 else "Structure",
            severity="Medium",
            page=(i % 10) + 1,
            confidence=0.85,
            message=f"Sample issue {i}",
            explanation=f"Detailed error description {i} that should NOT be in the concise report",
            suggested_fix=f"Fix issue {i}"
        )
        for i in range(1, 18)
    ]

    session_id = "SG-20260927-00124"
    custom_meta = {
        "document_no": "ENG-MECH-042",
        "revision": "Rev. 03"
    }

    tol_result = ToleranceCalculator.calculate(
        session_id=session_id,
        doc=doc,
        findings=findings,
        profile_identifier="publication",
        custom_meta=custom_meta,
        custom_max_tolerance=10.0
    )

    # Expected standard filename
    pdf_filename = f"{tol_result.document_no}_{session_id}_Inspection_Report.pdf"
    pdf_path = tmp_path / pdf_filename

    html_filename = f"{tol_result.document_no}_{session_id}_Inspection_Report.html"
    html_path = tmp_path / html_filename

    json_filename = f"{tol_result.document_no}_{session_id}_Inspection_Report.json"
    json_path = tmp_path / json_filename

    # Generate PDF
    ReportGenerator.generate_pdf_report(tol_result, str(pdf_path))
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 2000

    # Verify PDF content via PyMuPDF
    fitz_doc = pymupdf.open(str(pdf_path))
    assert len(fitz_doc) == 1  # Concise 1-page report!
    p1_text = fitz_doc[0].get_text()
    assert "SPECGuard" in p1_text
    assert "DOCUMENT INSPECTION REPORT" in p1_text
    assert "SG-20260927-00124" in p1_text
    assert "ENG-MECH-042" in p1_text
    assert "Final approval, publication, or submission" in p1_text
    assert "responsibility of the authorized reviewer" in p1_text

    # Generate HTML
    ReportGenerator.generate_html_report(tol_result, str(html_path))
    assert html_path.exists()
    html_text = html_path.read_text(encoding="utf-8")
    assert "DOCUMENT INSPECTION REPORT" in html_text
    assert "ENG-MECH-042" in html_text
    assert "WITHIN ACCEPTABLE TOLERANCE" in html_text
    assert "Tolerance Utilization" in html_text
    assert "Detailed Findings and Suggested Corrective Actions are available" in html_text
    assert "Detailed error description 1 that should NOT be in the concise report" not in html_text

    # Generate JSON
    ReportGenerator.generate_json_report(tol_result, str(json_path))
    assert json_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["session_id"] == session_id
    assert data["tolerance_index"] == tol_result.tolerance_index
    assert "category_summary" in data
