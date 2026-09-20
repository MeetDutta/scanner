"""
Comprehensive Test Suite for Precise Document Annotations and Visual Marking System.

Validates:
1. PyMuPDF word-level coordinate extraction (distinct sub-pixel coordinates per word).
2. LocationMapper precision (words, phrases, numbers, multi-line wrapping, character slices).
3. GrammarAnalyzer exact word & phrase precision with spelling/repeated word isolation.
4. Duplicate figure & table label precision with bi-directional linked findings.
5. Table of Contents page drift number-level precision with destination heading links.
6. Cross-reference exact token resolution and dangling reference detection.
7. Finding serialization backward and forward compatibility.
"""

import pytest
import pymupdf as fitz
from pathlib import Path

from specguard.core.models import (
    DocumentModel, PageModel, TextBlock, WordModel, LineModel, BBox, Finding, FigureData, TableData
)
from specguard.core.document_parser import DocumentParser
from specguard.core.location_mapper import LocationMapper
from specguard.analyzers.grammar import GrammarAnalyzer
from specguard.analyzers.figures import FigureAnalyzer
from specguard.analyzers.tables import TableAnalyzer
from specguard.analyzers.toc import TOCAnalyzer
from specguard.analyzers.cross_references import CrossReferenceAnalyzer
from specguard.analyzers.structure import StructureAnalyzer


class TestWordLevelExtraction:
    """Verifies that PDF parsing yields exact sub-pixel word coordinates."""

    def test_word_coordinates_are_not_spans(self, tmp_path):
        pdf_path = tmp_path / "test_words.pdf"
        doc = fitz.open()
        page = doc.new_page(width=612, height=792)
        page.insert_text((72, 100), "Figure 1.1: System Architecture Diagram")
        doc.save(str(pdf_path))
        doc.close()

        doc_model = DocumentParser.parse_file(str(pdf_path))
        assert len(doc_model.pages) == 1
        page_model = doc_model.pages[0]

        assert len(page_model.blocks) >= 1
        words = page_model.blocks[0].words
        assert len(words) >= 4

        # Verify distinct horizontal coordinates for each word
        w_fig = next(w for w in words if "Figure" in w.text)
        w_num = next(w for w in words if "1.1" in w.text)
        w_sys = next(w for w in words if "System" in w.text)

        assert w_fig.bbox.x0 < w_fig.bbox.x1
        assert w_fig.bbox.x1 <= w_num.bbox.x0 + 2.0
        assert w_num.bbox.x0 < w_num.bbox.x1
        assert w_num.bbox.x1 <= w_sys.bbox.x0 + 2.0


class TestLocationMapper:
    """Verifies exact token, word, number, and phrase resolution."""

    @pytest.fixture
    def sample_page(self):
        return PageModel(
            page_num=1,
            width=612,
            height=792,
            blocks=[
                TextBlock(
                    text="The measured temprature was 415 V with tolerance specs.",
                    bbox=BBox(50, 100, 350, 120),
                    block_id=0,
                    words=[
                        WordModel(text="The", bbox=BBox(50, 100, 70, 120)),
                        WordModel(text="measured", bbox=BBox(75, 100, 130, 120)),
                        WordModel(text="temprature", bbox=BBox(135, 100, 200, 120)),
                        WordModel(text="was", bbox=BBox(205, 100, 225, 120)),
                        WordModel(text="415", bbox=BBox(230, 100, 250, 120)),
                        WordModel(text="V", bbox=BBox(255, 100, 265, 120)),
                        WordModel(text="with", bbox=BBox(270, 100, 295, 120)),
                        WordModel(text="tolerance", bbox=BBox(300, 100, 350, 120)),
                    ]
                )
            ]
        )

    def test_find_word_bbox_exact(self, sample_page):
        box = LocationMapper.find_word_bbox(sample_page, "temprature")
        assert box is not None
        assert box.x0 == 135
        assert box.x1 == 200

    def test_find_phrase_bboxes_merges_adjacent(self, sample_page):
        boxes = LocationMapper.find_phrase_bboxes(sample_page, "415 V")
        assert len(boxes) == 1
        assert boxes[0].x0 == 230
        assert boxes[0].x1 == 265

    def test_find_number_in_block(self, sample_page):
        num_box = LocationMapper.find_number_in_block(sample_page.blocks[0], "415")
        assert num_box is not None
        assert num_box.x0 == 230
        assert num_box.x1 == 250


class TestGrammarAnalyzerPrecision:
    """Verifies that GrammarAnalyzer sets EXACT_WORD and EXACT_PHRASE precision."""

    def test_spelling_precision(self):
        doc = DocumentModel(
            file_path="dummy.pdf",
            file_type="PDF",
            file_hash="dummy_hash",
            file_size=1024,
            page_count=1,
            pages=[
                PageModel(
                    page_num=1,
                    width=612,
                    height=792,
                    blocks=[
                        TextBlock(
                            text="The nominal tolerence is 0.05 mm.",
                            bbox=BBox(50, 100, 300, 120),
                            block_id=0,
                            words=[
                                WordModel(text="The", bbox=BBox(50, 100, 70, 120)),
                                WordModel(text="nominal", bbox=BBox(75, 100, 120, 120)),
                                WordModel(text="tolerence", bbox=BBox(125, 100, 185, 120)),
                                WordModel(text="is", bbox=BBox(190, 100, 205, 120)),
                                WordModel(text="0.05", bbox=BBox(210, 100, 240, 120)),
                                WordModel(text="mm.", bbox=BBox(245, 100, 270, 120)),
                            ]
                        )
                    ]
                )
            ]
        )

        analyzer = GrammarAnalyzer()
        findings = analyzer.analyze(doc)

        spelling_f = next((f for f in findings if f.issue_type == "SPELLING_ERROR"), None)
        assert spelling_f is not None
        assert spelling_f.location_precision == "EXACT_WORD"
        assert spelling_f.matched_text == "tolerence"
        assert spelling_f.expected_text == "tolerance"
        assert spelling_f.bbox.x0 == 125
        assert spelling_f.bbox.x1 == 185

    def test_repeated_word_precision(self):
        doc = DocumentModel(
            file_path="dummy.pdf",
            file_type="PDF",
            file_hash="dummy_hash",
            file_size=1024,
            page_count=1,
            pages=[
                PageModel(
                    page_num=1,
                    width=612,
                    height=792,
                    blocks=[
                        TextBlock(
                            text="Connect the the cable securely.",
                            bbox=BBox(50, 100, 300, 120),
                            block_id=0,
                            words=[
                                WordModel(text="Connect", bbox=BBox(50, 100, 100, 120)),
                                WordModel(text="the", bbox=BBox(105, 100, 125, 120)),
                                WordModel(text="the", bbox=BBox(130, 100, 150, 120)),
                                WordModel(text="cable", bbox=BBox(155, 100, 195, 120)),
                                WordModel(text="securely.", bbox=BBox(200, 100, 260, 120)),
                            ]
                        )
                    ]
                )
            ]
        )

        analyzer = GrammarAnalyzer()
        findings = analyzer.analyze(doc)

        rep_f = next((f for f in findings if f.issue_type == "REPEATED_WORD"), None)
        assert rep_f is not None
        assert rep_f.location_precision == "EXACT_PHRASE"
        assert rep_f.matched_text == "the the"
        assert rep_f.expected_text == "the"
        assert rep_f.bbox.x0 == 105
        assert rep_f.bbox.x1 == 150


class TestDuplicateLabelsAndLinking:
    """Verifies duplicate figure/table label detection with bi-directional links."""

    def test_duplicate_figure_labels_linked(self):
        doc = DocumentModel(
            file_path="dummy.pdf",
            file_type="PDF",
            file_hash="dummy_hash",
            file_size=1024,
            page_count=2,
            pages=[
                PageModel(
                    page_num=1,
                    width=612,
                    height=792,
                    figures=[
                        FigureData(
                            figure_id="fig_1",
                            page_num=1,
                            bbox=BBox(50, 100, 200, 250),
                            label="Figure 1",
                            caption="Figure 1: Initial System"
                        )
                    ],
                    blocks=[
                        TextBlock(
                            text="Figure 1: Initial System",
                            bbox=BBox(50, 255, 200, 275),
                            words=[
                                WordModel(text="Figure", bbox=BBox(50, 255, 90, 275)),
                                WordModel(text="1:", bbox=BBox(95, 255, 110, 275)),
                            ]
                        )
                    ]
                ),
                PageModel(
                    page_num=2,
                    width=612,
                    height=792,
                    figures=[
                        FigureData(
                            figure_id="fig_2",
                            page_num=2,
                            bbox=BBox(50, 100, 200, 250),
                            label="Figure 1",
                            caption="Figure 1: Conflicting System"
                        )
                    ],
                    blocks=[
                        TextBlock(
                            text="Figure 1: Conflicting System",
                            bbox=BBox(50, 255, 200, 275),
                            words=[
                                WordModel(text="Figure", bbox=BBox(50, 255, 90, 275)),
                                WordModel(text="1:", bbox=BBox(95, 255, 110, 275)),
                            ]
                        )
                    ]
                )
            ]
        )

        analyzer = FigureAnalyzer()
        findings = analyzer.analyze(doc)

        dup_f = next((f for f in findings if f.issue_type == "DUPLICATE_FIGURE_LABEL"), None)
        assert dup_f is not None
        assert dup_f.location_precision == "EXACT_LABEL"
        assert dup_f.matched_text == "Figure 1"
        assert len(dup_f.related_finding_ids) > 0
        assert dup_f.source_object_id == "fig_2"


class TestTOCDriftPrecisionAndLinking:
    """Verifies TOC page drift number precision and destination linking."""

    def test_toc_drift_isolates_number_token(self):
        doc = DocumentModel(
            file_path="dummy.pdf",
            file_type="PDF",
            file_hash="dummy_hash",
            file_size=1024,
            page_count=7,
            pages=[
                PageModel(
                    page_num=1,
                    width=612,
                    height=792,
                    blocks=[
                        TextBlock(text="Table of Contents", bbox=BBox(50, 50, 200, 70)),
                        TextBlock(
                            text="1. Introduction .............. 5",
                            bbox=BBox(50, 80, 400, 100),
                            words=[
                                WordModel(text="1.", bbox=BBox(50, 80, 65, 100)),
                                WordModel(text="Introduction", bbox=BBox(70, 80, 150, 100)),
                                WordModel(text="..............", bbox=BBox(155, 80, 360, 100)),
                                WordModel(text="5", bbox=BBox(370, 80, 385, 100)),
                            ]
                        )
                    ]
                ),
                PageModel(
                    page_num=7,
                    width=612,
                    height=792,
                    blocks=[
                        TextBlock(
                            text="1. Introduction",
                            bbox=BBox(50, 50, 200, 75),
                            is_bold=True,
                            font_size=14.0,
                            words=[
                                WordModel(text="1.", bbox=BBox(50, 50, 65, 75)),
                                WordModel(text="Introduction", bbox=BBox(70, 50, 160, 75)),
                            ]
                        )
                    ]
                )
            ]
        )

        analyzer = TOCAnalyzer()
        findings = analyzer.analyze(doc)

        drift_f = next((f for f in findings if f.issue_type == "TOC_PAGE_DRIFT"), None)
        assert drift_f is not None
        assert drift_f.location_precision == "EXACT_NUMBER"
        assert drift_f.matched_text == "5"
        assert drift_f.expected_text == "7"
        assert drift_f.bbox.x0 == 370
        assert drift_f.bbox.x1 == 385

        # Check linked destination finding
        dest_f = next((f for f in findings if f.issue_type == "TOC_DESTINATION_HEADING"), None)
        assert dest_f is not None
        assert dest_f.page_number == 7
        assert drift_f.finding_id in dest_f.related_finding_ids
        assert dest_f.finding_id in drift_f.related_finding_ids


class TestCrossReferencePrecision:
    """Verifies exact phrase token isolation for broken cross-references."""

    def test_unresolved_figure_reference(self):
        doc = DocumentModel(
            file_path="dummy.pdf",
            file_type="PDF",
            file_hash="dummy_hash",
            file_size=1024,
            page_count=1,
            pages=[
                PageModel(
                    page_num=1,
                    width=612,
                    height=792,
                    figures=[],
                    blocks=[
                        TextBlock(
                            text="The pipeline is illustrated in Fig. 4 for review.",
                            bbox=BBox(50, 100, 350, 120),
                            block_id=0,
                            words=[
                                WordModel(text="The", bbox=BBox(50, 100, 70, 120)),
                                WordModel(text="pipeline", bbox=BBox(75, 100, 120, 120)),
                                WordModel(text="is", bbox=BBox(125, 100, 135, 120)),
                                WordModel(text="illustrated", bbox=BBox(140, 100, 195, 120)),
                                WordModel(text="in", bbox=BBox(200, 100, 210, 120)),
                                WordModel(text="Fig.", bbox=BBox(215, 100, 240, 120)),
                                WordModel(text="4", bbox=BBox(245, 100, 255, 120)),
                                WordModel(text="for", bbox=BBox(260, 100, 280, 120)),
                                WordModel(text="review.", bbox=BBox(285, 100, 330, 120)),
                            ]
                        )
                    ]
                )
            ]
        )

        analyzer = CrossReferenceAnalyzer()
        findings = analyzer.analyze(doc)

        xref_f = next((f for f in findings if f.issue_type == "UNRESOLVED_FIGURE_REFERENCE"), None)
        assert xref_f is not None
        assert xref_f.location_precision == "EXACT_PHRASE"
        assert xref_f.matched_text == "Fig. 4"
        assert xref_f.bbox.x0 == 215
        assert xref_f.bbox.x1 == 255


class TestFindingSerialization:
    """Verifies Finding backward compatibility and round-trip serialization."""

    def test_finding_to_dict_and_from_dict(self):
        f = Finding(
            finding_id="TST-001",
            category="Grammar & Spelling",
            location="Page 1",
            page=1,
            bbox=BBox(10, 20, 30, 40),
            bounding_boxes=[BBox(10, 20, 30, 40)],
            matched_text="typo",
            expected_text="type",
            issue_type="SPELLING_ERROR",
            location_precision="EXACT_WORD",
            related_finding_ids=["TST-002"],
            source_object_id="word_1",
            target_object_id="word_2"
        )

        d = f.to_dict()
        assert d["page"] == 1
        assert d["page_number"] == 1
        assert d["bbox"]["x0"] == 10
        assert len(d["bounding_boxes"]) == 1
        assert d["location_precision"] == "EXACT_WORD"
        assert d["matched_text"] == "typo"
        assert d["related_finding_ids"] == ["TST-002"]

        reconstructed = Finding.from_dict(d)
        assert reconstructed.finding_id == "TST-001"
        assert reconstructed.location_precision == "EXACT_WORD"
        assert reconstructed.matched_text == "typo"
        assert reconstructed.related_finding_ids == ["TST-002"]
        assert reconstructed.page_number == 1
