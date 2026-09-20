"""
Automated tests for the Table of Contents (TOC) Analysis Engine:
- Detects genuine TOC and entry hierarchy
- Detects page number drift between TOC declared pages and actual headings
- Respects profile rules: does not penalize IEEE papers for absent TOC
"""

from pathlib import Path
from specguard.core.document_parser import DocumentParser
from specguard.analyzers.toc import TOCAnalyzer

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_toc_page_drift_detection():
    """Verify that TOC page drift is identified with exact evidence."""
    pdf_path = FIXTURES_DIR / "test_toc_drift.pdf"
    doc = DocumentParser.parse_file(str(pdf_path))

    analyzer = TOCAnalyzer()
    findings = analyzer.analyze(doc, context={"profile": "mechanical"})

    assert doc.toc is not None
    assert doc.toc.exists is True
    assert len(doc.toc.items) == 3

    # Finding for Section 2 drift (TOC says 5, actual is 4)
    drift_findings = [f for f in findings if f.finding_id.startswith("TOC-PAG")]
    assert len(drift_findings) >= 1
    f_drift = drift_findings[0]
    assert "drift" in f_drift.deviation.lower()
    assert f_drift.page == 2
    assert "Requirements" in f_drift.explanation


def test_ieee_paper_no_toc_does_not_fail():
    """Verify that IEEE paper without a Table of Contents is NOT flagged with a failure."""
    pdf_path = FIXTURES_DIR / "test_ieee_two_column.pdf"
    doc = DocumentParser.parse_file(str(pdf_path))

    analyzer = TOCAnalyzer()
    findings = analyzer.analyze(doc, context={"profile": "ieee_research"})

    # IEEE profile specifies requires_toc=False, so no TOC-REQ finding should be produced
    req_findings = [f for f in findings if f.finding_id.startswith("TOC-REQ")]
    assert len(req_findings) == 0
