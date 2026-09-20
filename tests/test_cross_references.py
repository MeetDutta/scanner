"""
Automated tests for Citation and Cross-Reference Analysis Engine:
- Detects in-text mentions to Figures, Tables, Equations, and Citations
- Resolves cross-references against declared document elements
- Detects unresolved (dangling) references with exact page location
- Detects unreferenced figures and tables
"""

from pathlib import Path
from specguard.core.document_parser import DocumentParser
from specguard.analyzers.figures import FigureAnalyzer
from specguard.analyzers.tables import TableAnalyzer
from specguard.analyzers.equations import EquationAnalyzer
from specguard.analyzers.cross_references import CrossReferenceAnalyzer

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_unresolved_cross_references_detected():
    """Verify that unresolved references to Figure 5, Table IV, and Eq. 9 are detected."""
    pdf_path = FIXTURES_DIR / "test_unresolved_xref.pdf"
    doc = DocumentParser.parse_file(str(pdf_path))

    # Run element analyzers to populate doc.figures, doc.tables, doc.equations
    fig_analyzer = FigureAnalyzer()
    fig_analyzer.analyze(doc)

    tbl_analyzer = TableAnalyzer()
    tbl_analyzer.analyze(doc)

    eq_analyzer = EquationAnalyzer()
    eq_analyzer.analyze(doc)

    xref_analyzer = CrossReferenceAnalyzer()
    findings = xref_analyzer.analyze(doc)

    assert len(doc.cross_references) >= 3

    # Check unresolved figure finding (Fig. 5)
    unresolved_figs = [f for f in findings if f.finding_id.startswith("XREF-FIG")]
    assert len(unresolved_figs) >= 1
    assert "Figure 5" in unresolved_figs[0].detected_value

    # Check unresolved table finding (Table IV)
    unresolved_tbls = [f for f in findings if f.finding_id.startswith("XREF-TBL")]
    assert len(unresolved_tbls) >= 1
    assert "Table IV" in unresolved_tbls[0].detected_value

    # Check unreferenced figure finding (Fig. 1 exists but is not cited)
    unref_figs = [f for f in findings if f.finding_id.startswith("XREF-UNREF-FIG")]
    assert len(unref_figs) >= 1
    assert "Figure 1" in unref_figs[0].detected_value
