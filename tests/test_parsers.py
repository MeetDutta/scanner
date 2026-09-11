"""
Tests for SpecGuard Multi-Format Document Parsers (PDF, DOCX, TXT, XLSX, Image).
"""

import pytest
from pathlib import Path
from specguard.core.document_parser import DocumentParser
from specguard.core.models import DocumentModel

DEMO_DIR = Path(__file__).resolve().parent.parent / "demo_samples"


def test_pdf_parsing():
    pdf_path = DEMO_DIR / "mechanical_sample_with_errors.pdf"
    assert pdf_path.exists()

    doc = DocumentParser.parse_file(str(pdf_path))
    assert isinstance(doc, DocumentModel)
    assert doc.file_type == "PDF"
    assert doc.page_count == 2
    assert len(doc.pages) == 2
    assert len(doc.pages[0].blocks) > 0
    # Verify bounding boxes are preserved
    for b in doc.pages[0].blocks:
        assert b.bbox is not None
        assert b.bbox.width >= 0
        assert b.bbox.height >= 0


def test_docx_parsing():
    docx_path = DEMO_DIR / "chemical_sample_with_errors.docx"
    assert docx_path.exists()

    doc = DocumentParser.parse_file(str(docx_path))
    assert doc.file_type == "DOCX"
    assert len(doc.pages) == 1
    assert "concentration" in doc.full_text.lower()


def test_txt_parsing(tmp_path):
    txt_file = tmp_path / "test_spec.txt"
    txt_file.write_text("1 Scope\nPrecision drive system.\n2 Voltage: 415 V\n")

    doc = DocumentParser.parse_file(str(txt_file))
    assert doc.file_type == "TXT"
    assert len(doc.pages) == 1
    assert "415 V" in doc.full_text
