"""
Automated tests for Geometric Reading Order Reconstruction Engine:
- Two-column IEEE layout
- Single-column engineering specification
- Full-width spanning elements (title, abstract, figures)
- Non-linear vertical traversal
"""

from pathlib import Path
from specguard.core.document_parser import DocumentParser
from specguard.core.reading_order import ReadingOrderEngine
from specguard.core.models import TextBlock, BBox

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_ieee_two_column_reading_order():
    """Verify that in two-column IEEE papers, column 1 is completely read before column 2."""
    pdf_path = FIXTURES_DIR / "test_ieee_two_column.pdf"
    doc = DocumentParser.parse_file(str(pdf_path))
    assert doc.page_count == 2

    p1 = doc.pages[0]
    assert p1.layout_type in ["two_column", "mixed"]
    assert len(p1.columns) == 2

    # Verify that Section I (Introduction) in Column 1 appears in text before Section II (Related Work) in Column 2
    p1_text = p1.text
    idx_intro = p1_text.find("I. INTRODUCTION")
    idx_related = p1_text.find("II. RELATED WORK")
    assert idx_intro != -1
    assert idx_related != -1
    assert idx_intro < idx_related, "Column 1 text must precede Column 2 text in reading order!"

    # Verify that spanning title appears before Section I
    idx_title = p1_text.find("Deep Document Intelligence")
    assert idx_title != -1
    assert idx_title < idx_intro, "Spanning Title must precede Column 1 in reading order!"


def test_synthetic_two_column_block_ordering():
    """Unit test ReadingOrderEngine on synthetic two-column blocks."""
    engine = ReadingOrderEngine()
    page_w = 612.0
    page_h = 792.0

    # Create blocks:
    # 0: Spanning Title (y: 50-80, x: 54-558)
    # 1: Col 1 top (y: 100-150, x: 54-280)
    # 2: Col 1 bottom (y: 200-250, x: 54-280)
    # 3: Col 2 top (y: 100-150, x: 330-558)
    # 4: Col 2 bottom (y: 200-250, x: 330-558)
    blocks = [
        TextBlock(text="Spanning Header Title", bbox=BBox(54, 50, 558, 80)),
        TextBlock(text="Col 1 Top Paragraph", bbox=BBox(54, 100, 280, 150)),
        TextBlock(text="Col 1 Bottom Paragraph", bbox=BBox(54, 200, 280, 250)),
        TextBlock(text="Col 2 Top Paragraph", bbox=BBox(330, 100, 558, 150)),
        TextBlock(text="Col 2 Bottom Paragraph", bbox=BBox(330, 200, 558, 250)),
    ]

    ordered_blocks, ordered_indices, columns, layout_type = engine.analyze_page_layout(
        blocks=blocks,
        page_width=page_w,
        page_height=page_h
    )

    assert layout_type in ["two_column", "mixed"]
    assert len(columns) == 2
    # Order must be: Title (0) -> Col 1 Top (1) -> Col 1 Bottom (2) -> Col 2 Top (3) -> Col 2 Bottom (4)
    # NOT sorted purely by Y (which would interleave 1 and 3, then 2 and 4)!
    assert ordered_indices == [0, 1, 2, 3, 4]
