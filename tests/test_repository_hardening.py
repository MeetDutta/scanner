"""
Hardening and Security Tests for SpecGuard Repository and Backup Engine.
Verifies:
1. Real analysis start and completion timestamps with duration calculation.
2. Per-artifact SHA-256 calculation and verification on disk.
3. Historical reopen without inference execution.
4. Warning logged on missing historical artifacts without re-triggering analysis.
5. Document revision comparison (new, resolved, changed, unchanged, severity changes).
6. Backup manifest verification (per-file path, size, sha256).
7. Restore corruption detection (detects tampered files inside archive).
8. Path traversal attack rejection during archive restoration.
"""

import pytest
import tempfile
import zipfile
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

from specguard.storage.database import DatabaseManager
from specguard.repository.manager import RepositoryManager
from specguard.repository.backup import RepositoryBackupEngine
from specguard.core.models import DocumentModel, Finding


@pytest.fixture
def hardened_repo():
    with tempfile.TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        db = DatabaseManager(db_path=base / "test.db")
        mgr = RepositoryManager(repo_dir=base / "repository", db=db)
        yield {"mgr": mgr, "base": base, "db": db}


def test_real_timestamps_and_artifact_hashes(hardened_repo):
    """Verifies distinct started/completed UTC timestamps and artifact hashes."""
    mgr = hardened_repo["mgr"]
    doc = DocumentModel(file_path="pipe_spec.pdf", file_type="pdf", file_size=1200, page_count=2, file_hash="abc123hash")

    t1 = "2026-09-11T12:00:00+00:00"
    t2 = "2026-09-11T12:00:02+00:00"

    findings = [
        Finding(
            finding_id="F-001",
            category="Standards",
            domain="Mechanical",
            location="Page 1",
            page=1,
            original_content="PN16",
            detected_value="PN16",
            expected_value="PN25",
            deviation="Insufficient pressure class",
            severity="High",
            confidence=0.95
        )
    ]

    record = mgr.archive_comparison(
        doc_model=doc,
        findings=findings,
        domain="Mechanical",
        standards=["ASME-B16.5"],
        duration_ms=2000,
        analysis_started_at=t1,
        analysis_completed_at=t2
    )

    assert record.analysis_started_at == t1
    assert record.analysis_completed_at == t2
    assert record.analysis_started_at != record.analysis_completed_at
    assert record.duration_ms == 2000

    # Verify findings.json was hashed
    assert "findings_json" in record.artifact_hashes
    assert len(record.artifact_hashes["findings_json"]) == 64

    # Verify artifact audit function
    audit = mgr.verify_comparison_artifacts(record.comparison_id)
    assert audit["valid"] is True
    assert audit["artifacts"]["findings_json"]["present"] is True
    assert audit["artifacts"]["findings_json"]["match"] is True


def test_zero_inference_historical_reopen_and_missing_warning(hardened_repo, caplog):
    """Historical reopen must load stored findings from disk/db without running inference."""
    mgr = hardened_repo["mgr"]
    doc = DocumentModel(file_path="valve.pdf", file_type="pdf", file_size=800, page_count=1, file_hash="hash_v1")
    f1 = Finding(
        finding_id="F-HIST-01",
        category="Dimension",
        domain="Mechanical",
        location="Page 1",
        page=1,
        original_content="10 mm",
        detected_value="10 mm",
        expected_value="12 mm",
        deviation="Dimension deviation",
        severity="Medium",
        confidence=0.9
    )

    rec = mgr.archive_comparison(doc, [f1], domain="Mechanical", standards=[], duration_ms=500)

    # Reopen from archive
    reopened_findings = mgr.get_comparison_findings(rec.comparison_id)
    assert len(reopened_findings) == 1
    assert reopened_findings[0].finding_id == "F-HIST-01"

    # Remove stored artifact to verify warning is triggered without crashing or rerunning
    findings_json = mgr.comps_dir / rec.comparison_id / "findings.json"
    findings_json.unlink()

    reopened_again = mgr.get_comparison_findings(rec.comparison_id)
    assert len(reopened_again) == 1
    assert "Historical Reopen Warning" in caplog.text


def test_revision_comparison(hardened_repo):
    """Verifies diffing two revisions of document comparisons."""
    mgr = hardened_repo["mgr"]
    doc = DocumentModel(file_path="spec_rev1.pdf", file_type="pdf", file_size=1000, page_count=1, file_hash="h1")

    # Comparison 1: Findings A and B
    fA = Finding(finding_id="FA", category="Standards", domain="Mechanical", location="P1", page=1,
                 original_content="c1", detected_value="1", expected_value="2", deviation="d1", severity="Critical", confidence=0.9)
    fB = Finding(finding_id="FB", category="Standards", domain="Mechanical", location="P1", page=1,
                 original_content="c2", detected_value="3", expected_value="4", deviation="d2", severity="Medium", confidence=0.8)
    cmp1 = mgr.archive_comparison(doc, [fA, fB], domain="Mechanical", standards=[], duration_ms=100)

    # Comparison 2: Finding A resolved, Finding B severity upgraded to High, Finding C is new
    fB_upgraded = Finding(finding_id="FB", category="Standards", domain="Mechanical", location="P1", page=1,
                          original_content="c2", detected_value="3", expected_value="4", deviation="d2_worse", severity="High", confidence=0.8)
    fC = Finding(finding_id="FC", category="Material", domain="Mechanical", location="P1", page=1,
                 original_content="c3", detected_value="PVC", expected_value="SS316", deviation="Wrong material", severity="Critical", confidence=0.95)
    cmp2 = mgr.archive_comparison(doc, [fB_upgraded, fC], domain="Mechanical", standards=[], duration_ms=100)

    diff = mgr.compare_revisions(cmp1.comparison_id, cmp2.comparison_id)

    assert diff["resolved_count"] == 1
    assert diff["resolved_findings"][0]["finding_id"] == "FA"

    assert diff["new_count"] == 1
    assert diff["new_findings"][0]["finding_id"] == "FC"

    assert diff["changed_count"] == 1
    assert diff["changed_findings"][0]["finding_id"] == "FB"
    assert diff["severity_changes"][0]["previous_severity"] == "Critical" or diff["severity_changes"][0]["previous_severity"] == "Medium"


def test_backup_manifest_and_tamper_detection():
    """Verifies that backup includes per-file SHA-256 and detects corrupted files on restore."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_dir = Path(tmp_dir) / "repo"
        repo_dir.mkdir()
        (repo_dir / "sample.txt").write_text("Integrity-critical engineering document content", encoding="utf-8")

        backup_file = Path(tmp_dir) / "backup.sgr"
        out_p, digest, count = RepositoryBackupEngine.create_backup(repo_dir, str(backup_file))

        assert backup_file.exists()
        assert len(digest) == 64
        assert count == 1

        # Check manifest contents inside zip
        with zipfile.ZipFile(backup_file, "r") as z:
            manifest = json.loads(z.read("backup_manifest.json").decode("utf-8"))
            assert len(manifest["files"]) == 1
            assert manifest["files"][0]["path"] == "sample.txt"
            assert "sha256" in manifest["files"][0]
            assert "size" in manifest["files"][0]

        # Tamper with the zip content to simulate bitrot/corruption
        corrupt_zip = Path(tmp_dir) / "corrupt_backup.sgr"
        with zipfile.ZipFile(backup_file, "r") as z_in, zipfile.ZipFile(corrupt_zip, "w") as z_out:
            for item in z_in.infolist():
                if item.filename == "sample.txt":
                    z_out.writestr(item, b"MODIFIED TAMPERED CONTENT")
                else:
                    z_out.writestr(item, z_in.read(item.filename))

        # Restore must detect and reject corruption
        restore_dir = Path(tmp_dir) / "restored"
        res = RepositoryBackupEngine.restore_backup(str(corrupt_zip), restore_dir)
        assert res.success is False
        assert "Corrupted file detected" in res.message


def test_backup_rejects_path_traversal():
    """Verifies that backup restore strictly rejects path traversal attempts."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        malicious_zip = Path(tmp_dir) / "malicious.sgr"

        manifest = {
            "app_version": "1.0.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "type": "specguard_repository_backup",
            "files": [{"path": "../../etc/malicious.txt", "size": 4, "sha256": "dummy"}]
        }

        with zipfile.ZipFile(malicious_zip, "w") as z:
            z.writestr("backup_manifest.json", json.dumps(manifest))
            z.writestr("../../etc/malicious.txt", b"evil")

        restore_dir = Path(tmp_dir) / "safe_repo"
        res = RepositoryBackupEngine.restore_backup(str(malicious_zip), restore_dir)
        assert res.success is False
        assert "Path traversal detected" in res.message
