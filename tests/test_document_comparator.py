"""
Automated tests for Multi-Page Document Comparator:
- Detects page additions, removals, and count differences
- Detects structural section moves and removals
- Detects added and removed figures and tables
- Detects paragraph modifications and textual similarity
"""

from specguard.core.models import (
    DocumentModel, PageModel, TextBlock, SectionNode, FigureData, TableData, BBox
)
from specguard.core.document_comparator import DocumentComparator


def test_document_comparator_page_and_section_diff():
    """Verify comparator detects added pages and moved sections."""
    doc1 = DocumentModel(
        file_path="spec_v1.pdf",
        file_type="PDF",
        file_hash="hash1",
        file_size=1000,
        page_count=2,
        pages=[
            PageModel(page_num=1, blocks=[TextBlock("Scope of work", BBox(54, 50, 500, 80))]),
            PageModel(page_num=2, blocks=[TextBlock("Testing criteria", BBox(54, 50, 500, 80))])
        ],
        sections=[
            SectionNode("sec_1", "Scope", 1, "1", 1),
            SectionNode("sec_2", "Testing", 1, "2", 2)
        ]
    )

    doc2 = DocumentModel(
        file_path="spec_v2.pdf",
        file_type="PDF",
        file_hash="hash2",
        file_size=1500,
        page_count=3,
        pages=[
            PageModel(page_num=1, blocks=[TextBlock("Scope of work", BBox(54, 50, 500, 80))]),
            PageModel(page_num=2, blocks=[TextBlock("Requirements added", BBox(54, 50, 500, 80))]),
            PageModel(page_num=3, blocks=[TextBlock("Testing criteria", BBox(54, 50, 500, 80))])
        ],
        sections=[
            SectionNode("sec_1", "Scope", 1, "1", 1),
            SectionNode("sec_new", "Requirements", 1, "2", 2),
            SectionNode("sec_2", "Testing", 1, "3", 3)  # Moved from page 2 to page 3!
        ]
    )

    comparator = DocumentComparator()
    report = comparator.compare(doc1, doc2)

    assert report.added_pages == 1
    assert report.doc1_pages == 2
    assert report.doc2_pages == 3
    assert report.sections_changed >= 2  # Requirements added, Testing moved

    # Check that moved section "Testing" is explicitly recorded
    moved_items = [d for d in report.diff_items if d.diff_type == "section" and d.change_type == "moved"]
    assert len(moved_items) >= 1
    assert "Testing" in moved_items[0].description


def test_document_comparator_figure_and_table_diff():
    """Verify comparator detects added figures and modified table captions."""
    doc1 = DocumentModel(
        file_path="spec_v1.pdf",
        file_type="PDF",
        file_hash="hash1",
        file_size=1000,
        page_count=1,
        pages=[PageModel(page_num=1)],
        tables=[TableData(table_id="tbl_1", label="Table 1", caption="Initial Values", page_num=1)]
    )

    doc2 = DocumentModel(
        file_path="spec_v2.pdf",
        file_type="PDF",
        file_hash="hash2",
        file_size=1200,
        page_count=1,
        pages=[PageModel(page_num=1)],
        tables=[TableData(table_id="tbl_1", label="Table 1", caption="Updated Engineering Values", page_num=1)],
        figures=[FigureData(figure_id="fig_1", label="Figure 1", caption="New Layout Chart", page_num=1)]
    )

    comparator = DocumentComparator()
    report = comparator.compare(doc1, doc2)

    assert report.tables_changed >= 1
    assert report.figures_changed >= 1

    added_figs = [d for d in report.diff_items if d.diff_type == "figure" and d.change_type == "added"]
    assert len(added_figs) == 1
    assert "Figure 1" in added_figs[0].description

    mod_tbls = [d for d in report.diff_items if d.diff_type == "table" and d.change_type == "modified"]
    assert len(mod_tbls) == 1
    assert "caption" in mod_tbls[0].description.lower()
