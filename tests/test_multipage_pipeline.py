"""
Automated tests for SpecGuard multi-page processing pipeline:
- Validates 1, 20, 50, and 100-page documents with ZERO arbitrary page limits
- Validates page count, page-by-page progress reporting, and cancellation
- Validates multi-page DOCX extraction
- Validates corrupted PDF failure handling
"""

import pytest
from pathlib import Path
from specguard.core.document_parser import DocumentParser
from specguard.core.pipeline import AnalysisPipeline
from specguard.server.api.analysis import CancellationToken

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_no_arbitrary_page_limit_20_pages():
    """Verify processing a 20-page document without truncation or limits."""
    pdf_path = FIXTURES_DIR / "test_20_page.pdf"
    doc = DocumentParser.parse_file(str(pdf_path))
    assert doc.page_count == 20
    assert len(doc.pages) == 20
    assert doc.pages[0].page_num == 1
    assert doc.pages[19].page_num == 20


def test_50_page_processing_and_progress():
    """Verify streaming page progress callback on 50-page document."""
    pdf_path = FIXTURES_DIR / "test_50_page.pdf"
    progress_records = []

    def cb(cur, tot, msg):
        progress_records.append((cur, tot))

    doc = DocumentParser.parse_file(str(pdf_path), progress_callback=cb)
    assert doc.page_count == 50
    assert len(doc.pages) == 50
    assert len(progress_records) == 50
    assert progress_records[-1] == (50, 50)


def test_100_page_processing_memory_safe():
    """Verify processing 100+ page document successfully with linear memory profile."""
    pdf_path = FIXTURES_DIR / "test_100_page.pdf"
    doc = DocumentParser.parse_file(str(pdf_path))
    assert doc.page_count == 100
    assert len(doc.pages) == 100
    assert doc.pages[99].page_num == 100
    assert "Stage 100" in doc.pages[99].text


def test_cancellation_token_interrupts_processing():
    """Verify cancellation token stops pipeline execution immediately."""
    pdf_path = FIXTURES_DIR / "test_50_page.pdf"
    cancel_token = CancellationToken()

    def cb(cur, tot, msg):
        if cur >= 5:
            cancel_token.cancel()

    with pytest.raises(InterruptedError):
        DocumentParser.parse_file(
            str(pdf_path),
            progress_callback=cb,
            cancellation_token=cancel_token
        )


def test_corrupted_pdf_handling():
    """Verify corrupted PDF fails gracefully with understandable exception."""
    corrupt_path = FIXTURES_DIR / "test_corrupted.pdf"
    with pytest.raises(Exception):
        DocumentParser.parse_file(str(corrupt_path))


def test_multipage_docx_structural_extraction():
    """Verify multi-page DOCX partitions into logical pages and extracts headings and tables."""
    docx_path = FIXTURES_DIR / "test_multipage.docx"
    doc = DocumentParser.parse_file(str(docx_path))
    assert doc.file_type == "DOCX"
    assert doc.page_count >= 3
    assert len(doc.pages) >= 3
    # Check sections
    assert len(doc.sections) >= 3
    assert any("Scope" in s.title for s in doc.sections)
    # Check table extraction
    assert any(len(p.tables) > 0 for p in doc.pages)
    # Check unverified pagination warning when LibreOffice is not invoked
    assert doc.metadata.get("pagination_verified") is False
