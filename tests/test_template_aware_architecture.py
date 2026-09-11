"""
Unit and Integration Tests for SpecGuard Template-Aware Architecture.
Verifies:
1. Local template loading for Mechanical, Electrical, Chemical.
2. Deterministic template validation (missing sections, missing parameters).
3. Rule-only fallback operation without ML checkpoints.
4. Data augmentation with strict provenance and held-out real test isolation.
5. Low confidence ML guardrail.
"""

from pathlib import Path
import pytest

from specguard.templates.manager import TemplateManager, DomainTemplate
from specguard.analyzers.template_analyzer import TemplateAnalyzer
from specguard.analyzers.standards import StandardsAnalyzer
from specguard.core.models import DocumentModel, PageModel, TextBlock, BBox, EngineeringParameter, Finding
from specguard.core.pipeline import AnalysisPipeline
from specguard.training.augmentation import EngineeringAugmenter, ProvenanceSample


def test_load_all_domain_templates():
    for domain in ["mechanical", "electrical", "chemical"]:
        tmpl = TemplateManager.get_template(domain)
        assert isinstance(tmpl, DomainTemplate)
        assert tmpl.domain == domain
        assert len(tmpl.sections) >= 2, f"{domain} must have at least 2 sections"
        assert len(tmpl.parameters) >= 2, f"{domain} must have at least 2 parameters"
        assert len(tmpl.rules) >= 2, f"{domain} must have at least 2 rules"
        assert len(tmpl.vocabulary) > 0, f"{domain} must have vocabulary definitions"


def test_template_analyzer_detects_missing_section_and_parameter():
    analyzer = TemplateAnalyzer()

    # Document missing Section 1 ("Scope") and Section 2 ("System Requirements")
    doc = DocumentModel(
        file_path="test_doc.pdf",
        file_type="pdf",
        file_hash="abc123hash",
        file_size=1024,
        page_count=1,
        pages=[
            PageModel(
                page_num=1,
                text="This is an informal memo without standard headers.",
                blocks=[
                    TextBlock(text="This is an informal memo without standard headers.", bbox=BBox(10, 10, 100, 20))
                ]
            )
        ]
    )

    context = {
        "domain": "mechanical",
        "parameters": []
    }

    findings = analyzer.analyze(doc, context)

    # Must detect missing Scope and missing required parameters (operating_temperature, operating_pressure)
    sec_findings = [f for f in findings if f.finding_id.startswith("TMPL-SEC")]
    prm_findings = [f for f in findings if f.finding_id.startswith("TMPL-PRM")]

    assert len(sec_findings) >= 1, "Must detect missing required template section"
    assert len(prm_findings) >= 1, "Must detect missing required engineering parameters"


def test_rule_only_fallback_in_pipeline():
    """Verifies that the analysis pipeline runs deterministically without requiring model checkpoints."""
    pipeline = AnalysisPipeline()

    sample_pdf = Path("demo_samples/mechanical_sample_with_errors.pdf")
    assert sample_pdf.exists()

    doc, findings, session_id = pipeline.run_analysis(
        file_path=str(sample_pdf),
        domain="mechanical"
    )

    assert doc is not None
    assert len(findings) > 0, "Must detect deterministic deviations via template and rules"
    # Verify presence of tolerance deviation
    tol_findings = [f for f in findings if "tolerance" in f.explanation.lower() or "tolerance" in (f.deviation or "").lower()]
    assert len(tol_findings) >= 1, "Deterministic rule must detect tolerance deviation ±0.5 mm vs ±0.05 mm"


def test_data_augmentation_provenance_and_test_isolation():
    augmenter = EngineeringAugmenter(seed=42)

    # 1. Statement variation test
    variants = augmenter.generate_statement_variations(
        param_name="Operating Voltage",
        value=415.0,
        unit="V",
        domain="electrical",
        count=3
    )
    assert len(variants) == 3
    for v in variants:
        assert v.source_type == "augmented"
        assert len(v.entities) >= 2, "Entities must be aligned with offsets"

    # 2. Error generation test
    from specguard.templates.manager import ParameterDef
    p_def = ParameterDef(
        parameter_id="temp",
        parameter="temperature",
        display_name="Operating Temperature",
        unit="°C",
        max_value=80.0
    )
    err_samples = augmenter.generate_error_samples(p_def, domain="mechanical")
    assert len(err_samples) == 3
    for e in err_samples:
        assert e.source_type == "synthetic"
        assert e.deviation_type in ("out_of_range", "wrong_unit", "missing_val")

    # 3. Test set isolation check
    real_samples = [
        ProvenanceSample("REAL-1", "Scope paragraph", [], "real", "mechanical", "DOC-001"),
        ProvenanceSample("REAL-2", "Requirements paragraph", [], "real", "mechanical", "DOC-002"),
        ProvenanceSample("REAL-3", "Tolerances paragraph", [], "real", "mechanical", "DOC-003"),
        ProvenanceSample("REAL-4", "Testing paragraph", [], "real", "mechanical", "DOC-004")
    ]

    train_set, val_set, test_set = augmenter.build_domain_training_corpus(
        domain="mechanical",
        real_doc_samples=real_samples,
        augmentation_multiplier=2
    )

    # Held out real test set must have ONLY real samples
    assert len(test_set) >= 1
    for s in test_set:
        assert s.source_type == "real", "Test set MUST NEVER contain augmented or synthetic samples!"

    # Train set should contain augmented and synthetic samples
    train_types = {s.source_type for s in train_set}
    assert "augmented" in train_types
    assert "synthetic" in train_types


def test_low_confidence_ml_guardrail():
    """Section 20: low confidence predictions must be flagged for review rather than declaring critical violations."""
    analyzer = StandardsAnalyzer()

    low_conf_param = EngineeringParameter(
        entity="Motor",
        parameter="voltage",
        value=230.0,
        raw_value="230 V",
        unit="V",
        normalized_value=230.0,
        normalized_unit="V",
        confidence=0.45 # Low confidence
    )

    doc = DocumentModel("test.pdf", "pdf", "hash1", 100, 1)
    context = {
        "domain": "electrical",
        "parameters": [low_conf_param]
    }

    findings = analyzer.analyze(doc, context)
    assert len(findings) >= 1
    # Check that severity was demoted from Critical to Informational and flagged
    f = findings[0]
    assert f.severity == "Informational"
    assert "low ml confidence" in f.explanation.lower() or "verification needed" in f.explanation.lower()
