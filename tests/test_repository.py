"""
Tests for SpecGuard Local Document Comparison Repository & History Subsystem:
Sequential IDs, Revision Tracking, Immutable Comparison Snapshots, Zero-Inference Reopen,
Search Engine, Version Diffing, and .SGR Backup/Restore.
"""

import pytest
import tempfile
import json
from pathlib import Path

from specguard.storage.database import DatabaseManager
from specguard.core.models import DocumentModel, Finding, BBox
from specguard.repository.manager import RepositoryManager
from specguard.repository.search import RepositorySearchEngine
from specguard.repository.diff_engine import VersionDiffEngine
from specguard.repository.backup import RepositoryBackupEngine


@pytest.fixture
def repo_env():
    with tempfile.TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        db_path = base / "test_specguard.db"
        db = DatabaseManager(db_path=db_path)
        repo_dir = base / "repository"
        repo_mgr = RepositoryManager(repo_dir=repo_dir, db=db)
        yield {
            "db": db,
            "repo_dir": repo_dir,
            "repo_mgr": repo_mgr
        }


def test_sequential_ids_and_registration(repo_env):
    mgr = repo_env["repo_mgr"]

    doc1 = DocumentModel(
        file_path="/path/to/pump_spec.pdf",
        file_type="pdf",
        file_size=2048,
        page_count=4,
        file_hash="hash_rev_1"
    )

    registered1 = mgr.register_document(doc1)
    assert registered1.document_id.startswith("DOC-")
    assert registered1.revision_number == 1
    assert registered1.family_id.startswith("FAM-")

    # Register an updated revision of the same file (same filename, different content hash)
    doc2 = DocumentModel(
        file_path="/updated_path/pump_spec.pdf",
        file_type="pdf",
        file_size=2100,
        page_count=4,
        file_hash="hash_rev_2"
    )
    registered2 = mgr.register_document(doc2)
    assert registered2.document_id != registered1.document_id
    assert registered2.family_id == registered1.family_id
    assert registered2.revision_number == 2


def test_immutable_comparison_snapshot_and_reopen(repo_env):
    mgr = repo_env["repo_mgr"]

    doc = DocumentModel(
        file_path="/specs/vessel_v101.pdf",
        file_type="pdf",
        file_size=5120,
        page_count=2,
        file_hash="vessel_hash_1"
    )

    finding1 = Finding(
        finding_id="FND-001",
        category="Engineering Parameter",
        domain="Mechanical",
        location="Page 1, Para 2",
        page=1,
        bbox=BBox(x0=50, y0=100, x1=200, y1=120),
        original_content="Design pressure is 15 bar.",
        detected_value="15 bar",
        expected_value="<= 10 bar",
        deviation="Over allowable threshold",
        severity="Critical",
        confidence=0.98,
        explanation="Exceeds maximum allowable working pressure per ASME Section VIII.",
        suggested_correction="Reduce design pressure to <= 10 bar.",
        rule_reference="ASME Section VIII Div 1 UG-21",
        priority_score=95.0
    )

    finding2 = Finding(
        finding_id="FND-002",
        category="Grammar / Spelling",
        domain="Mechanical",
        location="Page 2, Para 1",
        page=2,
        bbox=None,
        original_content="The vessel was inspectd.",
        detected_value="inspectd",
        expected_value="inspected",
        deviation="Typo",
        severity="Low",
        confidence=0.92,
        explanation="Spelling error in engineering narrative.",
        suggested_correction="inspected",
        rule_reference="ISO 80000-1 Grammar Spec",
        priority_score=20.0
    )

    cmp_record = mgr.archive_comparison(
        doc_model=doc,
        findings=[finding1, finding2],
        domain="Mechanical",
        standards=["ASME Section VIII Div 1"],
        duration_ms=450
    )

    assert cmp_record.comparison_id.startswith("CMP-")
    assert cmp_record.total_findings == 2
    assert cmp_record.critical_count == 1
    assert cmp_record.low_count == 1

    # Test ZERO-INFERENCE reopen
    loaded_findings = mgr.get_comparison_findings(cmp_record.comparison_id)
    assert len(loaded_findings) == 2
    assert loaded_findings[0].finding_id == "FND-001"
    assert loaded_findings[0].severity == "Critical"
    assert loaded_findings[0].bbox is not None
    assert loaded_findings[0].bbox.x0 == 50

    loaded_rec = mgr.get_comparison_record(cmp_record.comparison_id)
    assert loaded_rec is not None
    assert loaded_rec.document_filename == "vessel_v101.pdf"
    assert loaded_rec.duration_ms == 450


def test_repository_search_engine(repo_env):
    mgr = repo_env["repo_mgr"]
    search_engine = RepositorySearchEngine(repo_env["db"])

    doc_elec = DocumentModel(
        file_path="/specs/transformer.pdf",
        file_type="pdf",
        file_size=1024,
        page_count=1,
        file_hash="elec_hash"
    )
    fnd_crit = Finding(
        finding_id="ELEC-001",
        category="Engineering Parameter",
        domain="Electrical",
        location="Page 1",
        page=1,
        bbox=None,
        original_content="Short circuit current 65 kA",
        detected_value="65 kA",
        expected_value="50 kA",
        deviation="Exceeds bus rating",
        severity="Critical",
        confidence=0.99,
        explanation="Busbar rating violation per IEEE 141.",
        suggested_correction="Upgrade busbar",
        rule_reference="IEEE 141",
        priority_score=98.0
    )
    cmp_elec = mgr.archive_comparison(doc_elec, [fnd_crit], domain="Electrical", standards=["IEEE 141"], duration_ms=200)

    # Search by keyword
    res = search_engine.search(query="transformer")
    assert len(res) == 1
    assert res[0]["comparison_id"] == cmp_elec.comparison_id

    # Search by domain
    res_dom = search_engine.search(domain="Electrical")
    assert len(res_dom) == 1

    # Search by critical only
    res_crit = search_engine.search(critical_only=True)
    assert len(res_crit) == 1


def test_version_diff_engine(repo_env):
    mgr = repo_env["repo_mgr"]

    doc_v1 = DocumentModel(file_path="pipe.pdf", file_type="pdf", file_size=100, page_count=1, file_hash="p1")
    doc_v2 = DocumentModel(file_path="pipe.pdf", file_type="pdf", file_size=110, page_count=1, file_hash="p2")

    # Comparison 1 has finding A (Pressure) and finding B (Typo)
    fnd_a = Finding(
        finding_id="FND-A", category="Engineering Parameter", domain="Mechanical",
        location="P1", page=1, bbox=None, original_content="P = 15 bar",
        detected_value="15 bar", expected_value="10 bar", deviation="Over",
        severity="Critical", confidence=0.9, explanation="High", suggested_correction="", rule_reference="ASME", priority_score=90
    )
    fnd_b = Finding(
        finding_id="FND-B", category="Grammar / Spelling", domain="Mechanical",
        location="P1", page=1, bbox=None, original_content="flange is missaligned",
        detected_value="missaligned", expected_value="misaligned", deviation="Typo",
        severity="Low", confidence=0.9, explanation="Typo", suggested_correction="", rule_reference="ISO", priority_score=15
    )
    cmp1 = mgr.archive_comparison(doc_v1, [fnd_a, fnd_b], domain="Mechanical", standards=["ASME"], duration_ms=100)

    # Comparison 2 has resolved finding B (typo fixed), persistent finding A, and new finding C (Temperature)
    fnd_c = Finding(
        finding_id="FND-C", category="Engineering Parameter", domain="Mechanical",
        location="P1", page=1, bbox=None, original_content="T = 450 C",
        detected_value="450 C", expected_value="350 C", deviation="Over",
        severity="High", confidence=0.9, explanation="Temp high", suggested_correction="", rule_reference="ASME", priority_score=75
    )
    cmp2 = mgr.archive_comparison(doc_v2, [fnd_a, fnd_c], domain="Mechanical", standards=["ASME"], duration_ms=100)

    diff_engine = VersionDiffEngine(mgr)
    diff = diff_engine.compare_sessions(cmp1.comparison_id, cmp2.comparison_id)

    assert diff.comparison_a_id == cmp1.comparison_id
    assert diff.comparison_b_id == cmp2.comparison_id
    assert diff.persistent_findings_count == 1 # Finding A persisted
    assert diff.resolved_findings_count == 1   # Finding B resolved
    assert diff.new_findings_count == 1        # Finding C is new


def test_repository_backup_and_restore(repo_env):
    mgr = repo_env["repo_mgr"]
    repo_dir = repo_env["repo_dir"]

    doc = DocumentModel(file_path="valve.pdf", file_type="pdf", file_size=100, page_count=1, file_hash="vh")
    mgr.archive_comparison(doc, [], domain="Mechanical", standards=[], duration_ms=50)

    with tempfile.TemporaryDirectory() as tmp_dir:
        backup_file = str(Path(tmp_dir) / "specguard_backup.sgr")

        # Create backup
        out_path, digest, count = RepositoryBackupEngine.create_backup(repo_dir=repo_dir, output_file_path=backup_file)
        assert Path(out_path).exists()
        assert len(digest) == 64
        assert count > 0

        # Restore into clean repository directory
        restore_dir = Path(tmp_dir) / "restored_repo"
        success, msg = RepositoryBackupEngine.restore_backup(backup_file_path=out_path, target_repo_dir=restore_dir)
        assert success is True
        assert (restore_dir / "backup_manifest.json").exists()
