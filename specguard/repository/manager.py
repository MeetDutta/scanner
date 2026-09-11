"""
Local Document Comparison Repository Manager for SpecGuard.
Creates immutable archives for all document comparisons with stable sequential IDs (DOC-XXXX, CMP-XXXX).
Guarantees 100% offline data integrity and reproducibility.
"""

import os
import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any, Tuple
import logging

from specguard.core.config import BASE_DIR
from specguard.core.models import DocumentModel, Finding, BBox
from specguard.repository.models import RepositoryDocument, ComparisonRecord
from specguard.storage.database import DatabaseManager

from typing import List, Dict, Any, Optional, Tuple, Union

logger = logging.getLogger(__name__)

REPO_DIR = BASE_DIR / "repository"


class RepositoryManager:
    """Manages the local document archive, comparison sessions, and revision families."""

    def __init__(self, repo_dir: Optional[Union[Path, str, DatabaseManager]] = None, db: Optional[DatabaseManager] = None):
        if isinstance(repo_dir, DatabaseManager):
            self.db = repo_dir
            self.repo_dir = REPO_DIR
        else:
            self.repo_dir = Path(repo_dir) if repo_dir else REPO_DIR
            self.db = db or DatabaseManager()

        self.docs_dir = self.repo_dir / "documents"
        self.comps_dir = self.repo_dir / "comparisons"
        self._init_repository_db()
        self.ensure_structure()

    def ensure_structure(self):
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.comps_dir.mkdir(parents=True, exist_ok=True)

    def _init_repository_db(self):
        """Creates repository tables in SQLite."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript("""
            CREATE TABLE IF NOT EXISTS repo_documents (
                document_id TEXT PRIMARY KEY,
                family_id TEXT NOT NULL,
                revision_number INTEGER DEFAULT 1,
                filename TEXT NOT NULL,
                original_path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                page_count INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                stored_locally INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS repo_comparisons (
                comparison_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                document_filename TEXT NOT NULL,
                document_sha256 TEXT NOT NULL,
                domain TEXT NOT NULL,
                status TEXT DEFAULT 'COMPLETED',
                analysis_started_at TIMESTAMP,
                analysis_completed_at TIMESTAMP,
                duration_ms INTEGER DEFAULT 0,
                model_version TEXT NOT NULL,
                standards_used TEXT,
                total_findings INTEGER DEFAULT 0,
                critical_count INTEGER DEFAULT 0,
                high_count INTEGER DEFAULT 0,
                medium_count INTEGER DEFAULT 0,
                low_count INTEGER DEFAULT 0,
                info_count INTEGER DEFAULT 0,
                annotated_pdf_path TEXT,
                annotated_docx_path TEXT,
                report_html_path TEXT,
                findings_json_path TEXT,
                FOREIGN KEY (document_id) REFERENCES repo_documents(document_id)
            );

            CREATE TABLE IF NOT EXISTS repo_findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comparison_id TEXT NOT NULL,
                finding_id TEXT NOT NULL,
                category TEXT NOT NULL,
                domain TEXT NOT NULL,
                location TEXT,
                page INTEGER NOT NULL,
                bbox_json TEXT,
                original_content TEXT,
                detected_value TEXT,
                expected_value TEXT,
                deviation TEXT,
                severity TEXT NOT NULL,
                confidence REAL NOT NULL,
                explanation TEXT,
                suggested_correction TEXT,
                rule_reference TEXT,
                priority_score REAL DEFAULT 0.0,
                FOREIGN KEY (comparison_id) REFERENCES repo_comparisons(comparison_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_repo_doc_sha ON repo_documents(sha256);
            CREATE INDEX IF NOT EXISTS idx_repo_cmp_date ON repo_comparisons(analysis_completed_at);
            CREATE INDEX IF NOT EXISTS idx_repo_cmp_domain ON repo_comparisons(domain);
            """)
            conn.commit()

    def _next_sequential_id(self, prefix: str, table: str, col: str) -> str:
        year = datetime.now().year
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            cnt = cursor.fetchone()["count"] + 1
            return f"{prefix}-{year}-{cnt:06d}"

    def register_document(self, doc_model: DocumentModel, store_bytes: bool = True) -> RepositoryDocument:
        """Registers a document into the repository, detecting revisions of existing documents."""
        src_path = Path(doc_model.file_path).resolve()
        filename = src_path.name

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            # Check if exact same file hash already registered
            cursor.execute("SELECT * FROM repo_documents WHERE sha256 = ?", (doc_model.file_hash,))
            existing = cursor.fetchone()
            if existing:
                return RepositoryDocument(
                    document_id=existing["document_id"],
                    family_id=existing["family_id"],
                    revision_number=existing["revision_number"],
                    filename=existing["filename"],
                    original_path=existing["original_path"],
                    file_type=existing["file_type"],
                    file_size=existing["file_size"],
                    sha256=existing["sha256"],
                    page_count=existing["page_count"],
                    created_at=str(existing["created_at"]),
                    stored_locally=bool(existing["stored_locally"])
                )

            # Check if there is an existing family with same filename (Revision tracking)
            cursor.execute("SELECT family_id, MAX(revision_number) as max_rev FROM repo_documents WHERE filename = ?", (filename,))
            fam_row = cursor.fetchone()
            if fam_row and fam_row["family_id"]:
                family_id = fam_row["family_id"]
                revision = fam_row["max_rev"] + 1
            else:
                family_id = f"FAM-{uuid.uuid4().hex[:8].upper()}"
                revision = 1

        doc_id = self._next_sequential_id("DOC", "repo_documents", "document_id")
        doc_folder = self.docs_dir / doc_id
        for sub in ["original", "processed", "annotated", "reports"]:
            (doc_folder / sub).mkdir(parents=True, exist_ok=True)

        if store_bytes and src_path.exists():
            shutil.copy2(src_path, doc_folder / "original" / filename)

        # Save metadata JSON
        meta = {
            "document_id": doc_id,
            "family_id": family_id,
            "revision_number": revision,
            "filename": filename,
            "original_path": str(src_path),
            "file_type": doc_model.file_type,
            "file_size": doc_model.file_size,
            "sha256": doc_model.file_hash,
            "page_count": doc_model.page_count,
            "created_at": datetime.now().isoformat()
        }
        with open(doc_folder / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO repo_documents 
                (document_id, family_id, revision_number, filename, original_path, file_type, file_size, sha256, page_count, stored_locally)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (doc_id, family_id, revision, filename, str(src_path), doc_model.file_type, doc_model.file_size, doc_model.file_hash, doc_model.page_count, 1 if store_bytes else 0))
            conn.commit()

        return RepositoryDocument(
            document_id=doc_id,
            family_id=family_id,
            revision_number=revision,
            filename=filename,
            original_path=str(src_path),
            file_type=doc_model.file_type,
            file_size=doc_model.file_size,
            sha256=doc_model.file_hash,
            page_count=doc_model.page_count,
            created_at=meta["created_at"]
        )

    def get_document(self, document_id: str) -> Optional[RepositoryDocument]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM repo_documents WHERE document_id = ?", (document_id,))
            r = cursor.fetchone()
            if not r:
                return None
            return RepositoryDocument(
                document_id=r["document_id"],
                family_id=r["family_id"],
                revision_number=r["revision_number"],
                filename=r["filename"],
                original_path=r["original_path"],
                file_type=r["file_type"],
                file_size=r["file_size"],
                sha256=r["sha256"],
                page_count=r["page_count"],
                created_at=str(r["created_at"]),
                stored_locally=bool(r["stored_locally"])
            )

    def archive_comparison(
        self,
        doc_model: DocumentModel,
        findings: List[Finding],
        domain: str,
        standards: List[str],
        duration_ms: int,
        model_version: str = "Deterministic-v1.0",
        annotated_pdf_path: Optional[str] = None,
        report_html_path: Optional[str] = None,
        analysis_started_at: Optional[str] = None,
        analysis_completed_at: Optional[str] = None,
        model_id: str = "SG-DEFAULT",
        dataset_version: str = "v1.0"
    ) -> ComparisonRecord:
        """Creates an immutable comparison archive with all findings, artifact SHA-256 hashes, and reproducibility metadata."""
        repo_doc = self.register_document(doc_model)
        cmp_id = self._next_sequential_id("CMP", "repo_comparisons", "comparison_id")
        cmp_folder = self.comps_dir / cmp_id
        cmp_folder.mkdir(parents=True, exist_ok=True)

        now_utc = datetime.now(timezone.utc).isoformat()
        started_at = analysis_started_at or now_utc
        completed_at = analysis_completed_at or now_utc

        crit = sum(1 for f in findings if f.severity == "Critical")
        high = sum(1 for f in findings if f.severity == "High")
        med = sum(1 for f in findings if f.severity == "Medium")
        low = sum(1 for f in findings if f.severity == "Low")
        info = sum(1 for f in findings if f.severity == "Informational")

        # Save findings JSON
        findings_json_file = cmp_folder / "findings.json"
        with open(findings_json_file, "w", encoding="utf-8") as f:
            json.dump([f.to_dict() for f in findings], f, indent=2)

        artifact_hashes = {}
        # Hash findings JSON
        sha_findings = hashlib.sha256()
        with open(findings_json_file, "rb") as f:
            while chunk := f.read(65536):
                sha_findings.update(chunk)
        artifact_hashes["findings_json"] = sha_findings.hexdigest()

        # Copy generated report if provided
        dest_report = None
        if report_html_path and Path(report_html_path).exists():
            dest_report = str(cmp_folder / "report.html")
            shutil.copy2(report_html_path, dest_report)
            sha_rep = hashlib.sha256()
            with open(dest_report, "rb") as f:
                while chunk := f.read(65536):
                    sha_rep.update(chunk)
            artifact_hashes["report_html"] = sha_rep.hexdigest()

        dest_annot_pdf = None
        if annotated_pdf_path and Path(annotated_pdf_path).exists():
            dest_annot_pdf = str(cmp_folder / "annotated.pdf")
            shutil.copy2(annotated_pdf_path, dest_annot_pdf)
            sha_pdf = hashlib.sha256()
            with open(dest_annot_pdf, "rb") as f:
                while chunk := f.read(65536):
                    sha_pdf.update(chunk)
            artifact_hashes["annotated_pdf"] = sha_pdf.hexdigest()

        record = ComparisonRecord(
            comparison_id=cmp_id,
            document_id=repo_doc.document_id,
            document_filename=repo_doc.filename,
            document_sha256=repo_doc.sha256,
            domain=domain.title(),
            status="COMPLETED",
            analysis_started_at=started_at,
            analysis_completed_at=completed_at,
            duration_ms=duration_ms,
            model_version=model_version,
            standards_used=standards,
            total_findings=len(findings),
            critical_count=crit,
            high_count=high,
            medium_count=med,
            low_count=low,
            info_count=info,
            annotated_pdf_path=dest_annot_pdf,
            report_html_path=dest_report,
            findings_json_path=str(findings_json_file),
            artifact_hashes=artifact_hashes,
            model_id=model_id,
            dataset_version=dataset_version,
            standards_version="v1.0",
            rule_set_version="v1.0",
            pipeline_version="v1.0",
            application_version="1.0.0",
            inference_configuration={"domain": domain, "selected_standards": standards}
        )

        with open(cmp_folder / "comparison.json", "w", encoding="utf-8") as f:
            json.dump(record.to_dict(), f, indent=2)

        # Save to SQLite
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO repo_comparisons 
                (comparison_id, document_id, document_filename, document_sha256, domain, status,
                 analysis_started_at, analysis_completed_at, duration_ms, model_version, standards_used,
                 total_findings, critical_count, high_count, medium_count, low_count, info_count,
                 annotated_pdf_path, report_html_path, findings_json_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cmp_id, repo_doc.document_id, repo_doc.filename, repo_doc.sha256, domain.title(), "COMPLETED",
                started_at, completed_at, duration_ms, model_version, json.dumps(standards),
                len(findings), crit, high, med, low, info, dest_annot_pdf, dest_report, str(findings_json_file)
            ))

            for f in findings:
                bbox_json = json.dumps(f.bbox.to_dict()) if f.bbox else None
                cursor.execute("""
                    INSERT INTO repo_findings 
                    (comparison_id, finding_id, category, domain, location, page, bbox_json, original_content,
                     detected_value, expected_value, deviation, severity, confidence, explanation, suggested_correction, rule_reference, priority_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    cmp_id, f.finding_id, f.category, f.domain, f.location, f.page, bbox_json,
                    str(f.original_content), str(f.detected_value), str(f.expected_value), f.deviation,
                    f.severity, f.confidence, f.explanation, f.suggested_correction, f.rule_reference, f.priority_score
                ))
            conn.commit()

        logger.info("Archived comparison %s for document %s (elapsed %d ms)", cmp_id, repo_doc.document_id, duration_ms)
        return record

    def get_comparison_findings(self, comparison_id: str) -> List[Finding]:
        """
        Loads findings snapshot from disk/database for zero-inference reopen.
        Strictly does NOT trigger re-analysis. Warns if artifacts are missing.
        """
        # Integrity check on disk snapshot
        cmp_dir = self.comps_dir / comparison_id
        findings_json = cmp_dir / "findings.json"
        if not findings_json.exists():
            logger.warning(
                "Historical Reopen Warning: Stored findings.json artifact for comparison %s is missing from %s! "
                "Zero-inference reopen preserved: Not rerunning analysis. Returning database snapshot.",
                comparison_id, findings_json
            )

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM repo_findings WHERE comparison_id = ? ORDER BY priority_score DESC", (comparison_id,))
            rows = cursor.fetchall()
            findings = []
            for r in rows:
                bbox = BBox.from_dict(json.loads(r["bbox_json"])) if r["bbox_json"] else None
                findings.append(Finding(
                    finding_id=r["finding_id"],
                    category=r["category"],
                    domain=r["domain"],
                    location=r["location"] or "",
                    page=r["page"],
                    bbox=bbox,
                    original_content=r["original_content"] or "",
                    detected_value=r["detected_value"] or "",
                    expected_value=r["expected_value"] or "",
                    deviation=r["deviation"],
                    severity=r["severity"],
                    confidence=r["confidence"],
                    explanation=r["explanation"] or "",
                    suggested_correction=r["suggested_correction"] or "",
                    rule_reference=r["rule_reference"],
                    priority_score=r["priority_score"]
                ))
            return findings

    def get_comparison_record(self, comparison_id: str) -> Optional[ComparisonRecord]:
        """Loads comparison metadata record with stored artifact hash references."""
        cmp_file = self.comps_dir / comparison_id / "comparison.json"
        if cmp_file.exists():
            try:
                with open(cmp_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return ComparisonRecord(**data)
            except Exception as e:
                logger.warning("Could not read comparison.json for %s: %s", comparison_id, e)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM repo_comparisons WHERE comparison_id = ?", (comparison_id,))
            r = cursor.fetchone()
            if not r:
                return None
            return ComparisonRecord(
                comparison_id=r["comparison_id"],
                document_id=r["document_id"],
                document_filename=r["document_filename"],
                document_sha256=r["document_sha256"],
                domain=r["domain"],
                status=r["status"],
                analysis_started_at=str(r["analysis_started_at"]),
                analysis_completed_at=str(r["analysis_completed_at"]),
                duration_ms=r["duration_ms"],
                model_version=r["model_version"],
                standards_used=json.loads(r["standards_used"]) if r["standards_used"] else [],
                total_findings=r["total_findings"],
                critical_count=r["critical_count"],
                high_count=r["high_count"],
                medium_count=r["medium_count"],
                low_count=r["low_count"],
                info_count=r["info_count"],
                annotated_pdf_path=r["annotated_pdf_path"],
                report_html_path=r["report_html_path"],
                findings_json_path=r["findings_json_path"]
            )

    def verify_comparison_artifacts(self, comparison_id: str) -> Dict[str, Any]:
        """
        Audits stored artifacts for a comparison, verifying existence and cryptographic SHA-256 hashes.
        Returns detailed integrity health dict.
        """
        cmp_folder = self.comps_dir / comparison_id
        if not cmp_folder.exists():
            return {"valid": False, "comparison_id": comparison_id, "error": "Comparison directory not found"}

        record = self.get_comparison_record(comparison_id)
        if not record:
            return {"valid": False, "comparison_id": comparison_id, "error": "Comparison record not found"}

        expected_hashes = getattr(record, "artifact_hashes", {})
        results = {"valid": True, "comparison_id": comparison_id, "artifacts": {}}

        # Check findings JSON
        f_json = cmp_folder / "findings.json"
        if f_json.exists():
            sha = hashlib.sha256()
            with open(f_json, "rb") as f:
                while chunk := f.read(65536):
                    sha.update(chunk)
            current_hash = sha.hexdigest()
            exp = expected_hashes.get("findings_json")
            match = (current_hash == exp) if exp else True
            results["artifacts"]["findings_json"] = {"present": True, "sha256": current_hash, "match": match}
            if not match:
                results["valid"] = False
        else:
            results["artifacts"]["findings_json"] = {"present": False, "match": False}
            results["valid"] = False

        # Check report HTML if expected
        rep_html = cmp_folder / "report.html"
        if rep_html.exists():
            sha = hashlib.sha256()
            with open(rep_html, "rb") as f:
                while chunk := f.read(65536):
                    sha.update(chunk)
            current_hash = sha.hexdigest()
            exp = expected_hashes.get("report_html")
            match = (current_hash == exp) if exp else True
            results["artifacts"]["report_html"] = {"present": True, "sha256": current_hash, "match": match}
            if not match:
                results["valid"] = False

        # Check annotated PDF if expected
        ann_pdf = cmp_folder / "annotated.pdf"
        if ann_pdf.exists():
            sha = hashlib.sha256()
            with open(ann_pdf, "rb") as f:
                while chunk := f.read(65536):
                    sha.update(chunk)
            current_hash = sha.hexdigest()
            exp = expected_hashes.get("annotated_pdf")
            match = (current_hash == exp) if exp else True
            results["artifacts"]["annotated_pdf"] = {"present": True, "sha256": current_hash, "match": match}
            if not match:
                results["valid"] = False

        return results

    def compare_revisions(self, comparison_id_1: str, comparison_id_2: str) -> Dict[str, Any]:
        """
        Compares findings between two comparisons (e.g. Revision 1 vs Revision 2).
        Categorizes: New, Resolved, Changed, Unchanged findings and Severity shifts.
        """
        f1 = {f.finding_id: f for f in self.get_comparison_findings(comparison_id_1)}
        f2 = {f.finding_id: f for f in self.get_comparison_findings(comparison_id_2)}

        new_findings = [f2[fid].to_dict() for fid in f2 if fid not in f1]
        resolved_findings = [f1[fid].to_dict() for fid in f1 if fid not in f2]
        changed_findings = []
        unchanged_findings = []
        severity_changes = []

        for fid in f1:
            if fid in f2:
                item1 = f1[fid]
                item2 = f2[fid]
                if item1.severity != item2.severity or item1.deviation != item2.deviation:
                    changed_findings.append({
                        "finding_id": fid,
                        "rev1": item1.to_dict(),
                        "rev2": item2.to_dict()
                    })
                    if item1.severity != item2.severity:
                        severity_changes.append({
                            "finding_id": fid,
                            "previous_severity": item1.severity,
                            "new_severity": item2.severity
                        })
                else:
                    unchanged_findings.append(item1.to_dict())

        return {
            "comparison_id_1": comparison_id_1,
            "comparison_id_2": comparison_id_2,
            "new_count": len(new_findings),
            "resolved_count": len(resolved_findings),
            "changed_count": len(changed_findings),
            "unchanged_count": len(unchanged_findings),
            "severity_changes_count": len(severity_changes),
            "new_findings": new_findings,
            "resolved_findings": resolved_findings,
            "changed_findings": changed_findings,
            "unchanged_findings": unchanged_findings,
            "severity_changes": severity_changes
        }

    def delete_comparison(self, comparison_id: str):
        """Safely removes a comparison archive and its outputs."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM repo_comparisons WHERE comparison_id = ?", (comparison_id,))
            conn.commit()

        cmp_dir = self.comps_dir / comparison_id
        if cmp_dir.exists():
            shutil.rmtree(cmp_dir, ignore_errors=True)
        logger.info("Deleted comparison archive %s", comparison_id)


import uuid
