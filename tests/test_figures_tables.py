"""
Automated tests for Figure and Table intelligence engines:
- Duplicate figure label detection
- Figure sequence continuity
- Multi-page table continuity
- Table unit consistency and jagged row checks
"""

from pathlib import Path
from specguard.core.document_parser import DocumentParser
from specguard.analyzers.figures import FigureAnalyzer
from specguard.analyzers.tables import TableAnalyzer
from specguard.core.models import TableData, PageModel, DocumentModel, BBox

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_duplicate_figure_labels_detected():
    """Verify that duplicate Figure 1 labels on different pages are flagged."""
    pdf_path = FIXTURES_DIR / "test_duplicate_figures.pdf"
    doc = DocumentParser.parse_file(str(pdf_path))

    analyzer = FigureAnalyzer()
    findings = analyzer.analyze(doc)

    dup_findings = [f for f in findings if f.finding_id.startswith("FIG-DUP")]
    assert len(dup_findings) >= 1
    assert "Duplicate Figure 1" in dup_findings[0].detected_value
    assert dup_findings[0].page == 2


def test_multipage_table_continuity():
    """Verify that split tables across pages are linked and labeled as continuous."""
    tbl1 = TableData(
        rows=[["A1", "B1"], ["A2", "B2"]],
        headers=["Col A", "Col B"],
        page_num=1,
        caption="Table 1: Material Properties",
        label="Table 1",
        bbox=BBox(54, 500, 558, 700)
    )
    tbl2 = TableData(
        rows=[["A3", "B3"], ["A4", "B4"]],
        headers=["Col A", "Col B"],
        page_num=2,
        caption="Table 1 (Continued)",
        bbox=BBox(54, 80, 558, 250)
    )

    doc = DocumentModel(
        file_path="mock.pdf",
        file_type="PDF",
        file_hash="mockhash",
        file_size=1000,
        page_count=2,
        pages=[
            PageModel(page_num=1, tables=[tbl1]),
            PageModel(page_num=2, tables=[tbl2])
        ]
    )

    analyzer = TableAnalyzer()
    analyzer.analyze(doc)

    assert tbl1.is_split is True
    assert tbl1.page_end == 2
    assert tbl2.is_split is True
    assert "Cont." in tbl2.label or "Continued" in tbl2.label
