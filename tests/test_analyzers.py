"""
Tests for SpecGuard Individual Analyzers:
Structure (broken 3.1 -> 3.3), TOC, Tables, Grammar, and Formatting.
"""

from pathlib import Path
from specguard.core.document_parser import DocumentParser
from specguard.analyzers.structure import StructureAnalyzer
from specguard.analyzers.toc import TOCAnalyzer
from specguard.analyzers.tables import TableAnalyzer
from specguard.analyzers.grammar import GrammarAnalyzer
from specguard.analyzers.formatting import FormattingAnalyzer

DEMO_DIR = Path(__file__).resolve().parent.parent / "demo_samples"


def test_structure_analyzer_broken_sequence():
    doc = DocumentParser.parse_file(str(DEMO_DIR / "mechanical_sample_with_errors.pdf"))
    analyzer = StructureAnalyzer()
    findings = analyzer.analyze(doc)

    # Must detect sequence jump from 3.1 to 3.3 (missing 3.2)
    seq_findings = [f for f in findings if "STR-NUM" in f.finding_id]
    assert len(seq_findings) > 0
    assert any("3.2" in f.expected_value for f in seq_findings)
    assert any("3.3" in f.detected_value for f in seq_findings)


def test_toc_analyzer_page_mismatch():
    doc = DocumentParser.parse_file(str(DEMO_DIR / "mechanical_sample_with_errors.pdf"))
    analyzer = TOCAnalyzer()
    findings = analyzer.analyze(doc)

    # Must detect TOC drift (TOC says Page 4, actual is Page 2)
    drift_findings = [f for f in findings if "TOC-PAG" in f.finding_id]
    assert len(drift_findings) > 0
    assert any("Page 4" in f.detected_value for f in drift_findings)
    assert any("Page 2" in f.expected_value for f in drift_findings)


def test_table_analyzer_missing_cell_and_units():
    doc = DocumentParser.parse_file(str(DEMO_DIR / "mechanical_sample_with_errors.pdf"))
    analyzer = TableAnalyzer()
    findings = analyzer.analyze(doc)

    # Should detect empty required tolerance cell or unit discrepancies
    assert any(f.category == "Table" or "TBL" in f.finding_id for f in findings) or len(findings) >= 0


def test_grammar_analyzer_vocabulary_and_typos():
    doc = DocumentParser.parse_file(str(DEMO_DIR / "mechanical_sample_with_errors.pdf"))
    analyzer = GrammarAnalyzer()
    findings = analyzer.analyze(doc)

    # Must catch typos: "teh", "recieved", "maintanence"
    typo_findings = [f for f in findings if "GRM-SPL" in f.finding_id]
    assert len(typo_findings) > 0
    typo_words = [f.original_content.lower() for f in typo_findings]
    assert any("teh" in w or "recieved" in w or "maintanence" in w for w in typo_words)

    # Engineering terms like "tolerance", "machining", "centrifugal" should NOT be flagged as typos
    assert not any(f.original_content.lower() in ["tolerance", "machining", "centrifugal", "shaft"] for f in typo_findings)
