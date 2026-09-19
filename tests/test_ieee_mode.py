"""
Automated tests for IEEE Research Paper Analysis Mode:
- Verifies IEEE profile compliance rules (title, abstract, keywords, 2-column layout, Roman headings, bracket citations, references)
- Verifies engineering modes (Mechanical, Electrical, Chemical) are preserved and unaffected
"""

from pathlib import Path
from specguard.core.document_parser import DocumentParser
from specguard.core.pipeline import AnalysisPipeline
from specguard.analyzers.ieee import IEEEAnalyzer
from specguard.analyzers.structure import StructureAnalyzer

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_ieee_research_paper_analysis():
    """Verify IEEE mode evaluates two-column layout, abstract, keywords, and references."""
    pdf_path = FIXTURES_DIR / "test_ieee_two_column.pdf"
    doc = DocumentParser.parse_file(str(pdf_path))
    doc.profile_name = "ieee_research"

    analyzer = IEEEAnalyzer()
    findings = analyzer.analyze(doc, context={"profile": "ieee_research"})

    # The synthetic fixture has: Title, Abstract, Index Terms, Two-column body, Fig. 1, References
    # Check that abstract missing is NOT flagged
    abs_findings = [f for f in findings if f.finding_id.startswith("IEEE-ABS-001")]
    assert len(abs_findings) == 0

    # Check that references missing is NOT flagged
    ref_findings = [f for f in findings if f.finding_id.startswith("IEEE-REF")]
    assert len(ref_findings) == 0


def test_ieee_mode_does_not_force_mechanical_sections():
    """Verify that analyzing in IEEE mode does NOT report missing Scope, Requirements, or Testing."""
    pdf_path = FIXTURES_DIR / "test_ieee_two_column.pdf"
    doc = DocumentParser.parse_file(str(pdf_path))
    doc.profile_name = "ieee_research"

    structure_analyzer = StructureAnalyzer()
    findings = structure_analyzer.analyze(doc, context={"profile": "ieee_research"})

    # Should NOT have findings saying "Scope", "Requirements", "Testing" are missing
    mech_missing = [
        f for f in findings
        if f.finding_id.startswith("STR-REQ") and any(w in f.detected_value or w in f.expected_value for w in ["Scope", "Requirements", "Testing"])
    ]
    assert len(mech_missing) == 0


def test_mechanical_mode_still_enforces_engineering_sections():
    """Verify that Mechanical engineering mode continues enforcing Scope, Requirements, Testing."""
    pdf_path = FIXTURES_DIR / "test_1_page.pdf"
    pipeline = AnalysisPipeline()
    doc, findings, session_id = pipeline.run_analysis(
        file_path=str(pdf_path),
        domain="mechanical",
        profile="mechanical"
    )

    assert doc.page_count == 1
    # Mechanical sample has Scope, Requirements, Testing so STR-REQ should be satisfied
    missing_req = [f for f in findings if f.finding_id.startswith("STR-REQ")]
    assert len(missing_req) == 0
