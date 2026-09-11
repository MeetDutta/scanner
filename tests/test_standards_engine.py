"""
Tests for SpecGuard Logical Consistency & Standards Engines:
1. Cross-document contradictions (80°C vs 60°C)
2. Mechanical standard violation (±0.5 mm vs ±0.05 mm)
3. Electrical standard violation (230 V vs 415 V)
4. Chemical standard violation (15% vs 10%)
5. Severity priority ordering
"""

from pathlib import Path
from specguard.core.document_parser import DocumentParser
from specguard.analyzers.engineering import EngineeringAnalyzer, UnitNormalizer
from specguard.analyzers.logical import LogicalAnalyzer
from specguard.analyzers.standards import StandardsAnalyzer
from specguard.analyzers.severity import SeverityEngine
from specguard.analyzers.grammar import GrammarAnalyzer

DEMO_DIR = Path(__file__).resolve().parent.parent / "demo_samples"


def test_unit_normalization():
    assert UnitNormalizer.normalize(1.0, "kV") == (1000.0, "V")
    assert UnitNormalizer.normalize(1000.0, "V") == (1000.0, "V")
    assert UnitNormalizer.normalize(1.0, "MPa") == (10.0, "bar")
    assert UnitNormalizer.normalize(10.0, "bar") == (10.0, "bar")
    assert UnitNormalizer.normalize(1.0, "m") == (1000.0, "mm")
    assert UnitNormalizer.normalize(50.0, "mm") == (50.0, "mm")


def test_logical_contradiction_detection():
    doc = DocumentParser.parse_file(str(DEMO_DIR / "mechanical_sample_with_errors.pdf"))
    eng_analyzer = EngineeringAnalyzer()
    context = {}
    eng_analyzer.analyze(doc, context)

    # Must extract temperature parameters
    params = context.get("parameters", [])
    temp_params = [p for p in params if p.parameter == "temperature"]
    assert len(temp_params) >= 2

    # Run LogicalAnalyzer
    log_analyzer = LogicalAnalyzer()
    findings = log_analyzer.analyze(doc, context)

    # Must detect contradiction between 80°C (p.1) and 60°C (p.2)
    contra_findings = [f for f in findings if "LOG-CTR" in f.finding_id]
    assert len(contra_findings) > 0
    f = contra_findings[0]
    assert f.severity == "Critical"
    assert "80" in f.original_content and "60" in f.original_content


def test_mechanical_standards_compliance():
    doc = DocumentParser.parse_file(str(DEMO_DIR / "mechanical_sample_with_errors.pdf"))
    eng_analyzer = EngineeringAnalyzer()
    context = {"domain": "mechanical"}
    eng_analyzer.analyze(doc, context)

    std_analyzer = StandardsAnalyzer()
    findings = std_analyzer.analyze(doc, context)

    # Must flag tolerance ±0.5 mm violating ASME/ISO ±0.05 mm standard
    tol_findings = [f for f in findings if f.finding_id == "MECH-001" or "tolerance" in f.explanation.lower()]
    assert len(tol_findings) > 0
    assert tol_findings[0].severity == "Critical"
    assert "0.5" in str(tol_findings[0].detected_value)


def test_electrical_standards_compliance():
    doc = DocumentParser.parse_file(str(DEMO_DIR / "electrical_sample_with_errors.pdf"))
    eng_analyzer = EngineeringAnalyzer()
    context = {"domain": "electrical"}
    eng_analyzer.analyze(doc, context)

    std_analyzer = StandardsAnalyzer()
    findings = std_analyzer.analyze(doc, context)

    # Must flag voltage 230 V violating IEC 415 V industrial feeder standard
    volt_findings = [f for f in findings if f.finding_id == "ELEC-001" or "voltage" in f.explanation.lower()]
    assert len(volt_findings) > 0
    assert volt_findings[0].severity == "Critical"
    assert "230" in str(volt_findings[0].detected_value)


def test_chemical_standards_compliance():
    doc = DocumentParser.parse_file(str(DEMO_DIR / "chemical_sample_with_errors.docx"))
    eng_analyzer = EngineeringAnalyzer()
    context = {"domain": "chemical"}
    eng_analyzer.analyze(doc, context)

    std_analyzer = StandardsAnalyzer()
    findings = std_analyzer.analyze(doc, context)

    # Must flag concentration 15% violating 10% safety standard
    conc_findings = [f for f in findings if f.finding_id == "CHEM-001" or "concentration" in f.explanation.lower()]
    assert len(conc_findings) > 0
    assert conc_findings[0].severity == "Critical"


def test_severity_priority_ranking():
    doc = DocumentParser.parse_file(str(DEMO_DIR / "mechanical_sample_with_errors.pdf"))
    eng_analyzer = EngineeringAnalyzer()
    context = {"domain": "mechanical"}
    eng_analyzer.analyze(doc, context)

    std_findings = StandardsAnalyzer().analyze(doc, context)
    log_findings = LogicalAnalyzer().analyze(doc, context)
    grm_findings = GrammarAnalyzer().analyze(doc, context)

    all_findings = grm_findings + std_findings + log_findings
    engine = SeverityEngine()
    ranked = engine.rank_findings(all_findings)

    # Critical & High findings must strictly outrank Grammar typos
    assert ranked[0].severity in ["Critical", "High"]
    assert ranked[-1].severity in ["Low", "Informational"]
