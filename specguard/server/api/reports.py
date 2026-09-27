"""
Reports Generation and Export API for SpecGuard.
Produces formal Document Inspection / Publication Readiness Reports (PDF, HTML, JSON, DOCX).
100% offline, local generation with transparent tolerance evaluation and persistent results.
"""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from specguard.core.config import REPORTS_DIR
from specguard.storage.database import DatabaseManager
from specguard.repository.manager import RepositoryManager
from specguard.export.report_generator import ReportGenerator, DOCXAnnotator
from specguard.core.document_parser import DocumentParser
from specguard.core.tolerance import ToleranceResult, ToleranceCalculator, BUILTIN_PROFILES

logger = logging.getLogger("SpecGuard.API.Reports")
router = APIRouter(prefix="/reports", tags=["reports"])


class ReportRequest(BaseModel):
    session_id: str
    format: str = "pdf"  # pdf, html, json, docx
    document_no: Optional[str] = None
    document_title: Optional[str] = None
    revision: Optional[str] = None
    inspection_profile: Optional[str] = None
    max_tolerance: Optional[float] = None


@router.get("/profiles")
def list_inspection_profiles() -> List[Dict[str, Any]]:
    """Lists available inspection profiles with tolerance thresholds and severity policies."""
    return [
        {
            "profile_id": p.profile_id,
            "name": p.name,
            "description": p.description,
            "max_tolerance": p.max_tolerance,
            "max_critical": p.max_critical,
            "max_high": p.max_high
        }
        for p in BUILTIN_PROFILES.values()
    ]


@router.get("/tolerance/{session_id}")
def get_session_tolerance(
    session_id: str,
    profile: Optional[str] = None,
    document_no: Optional[str] = None,
    document_title: Optional[str] = None,
    revision: Optional[str] = None,
    max_tolerance: Optional[float] = None
) -> Dict[str, Any]:
    """Retrieves or calculates the formal tolerance evaluation result for a session."""
    db = DatabaseManager()
    persisted = db.get_tolerance_report(session_id)
    if persisted and not any([profile, document_no, document_title, revision, max_tolerance]):
        return persisted

    # If parameters provided or not yet persisted, calculate
    res = _evaluate_tolerance(
        session_id=session_id,
        profile_identifier=profile,
        custom_meta={
            "document_no": document_no,
            "document_title": document_title,
            "revision": revision
        },
        custom_max_tolerance=max_tolerance
    )
    db.save_tolerance_report(res.to_dict())
    return res.to_dict()


def _evaluate_tolerance(
    session_id: str,
    profile_identifier: Optional[str] = None,
    custom_meta: Optional[Dict[str, str]] = None,
    custom_max_tolerance: Optional[float] = None
) -> ToleranceResult:
    """Helper to evaluate tolerance from repo comparison or database session."""
    repo = RepositoryManager()
    db = DatabaseManager()

    rec = repo.get_comparison_record(session_id)
    findings = repo.get_comparison_findings(session_id)

    if not rec:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM analysis_sessions WHERE session_id = ?", (session_id,))
            s_row = cursor.fetchone()
            if not s_row:
                raise HTTPException(status_code=404, detail=f"Analysis session '{session_id}' not found.")

        from specguard.storage.repositories import SessionRepository
        findings = SessionRepository(db).get_findings_for_session(session_id)

    # Locate document file
    doc_path = None
    if rec:
        doc_info = repo.get_document(rec.document_id)
        if doc_info and Path(doc_info.original_path).exists():
            doc_path = Path(doc_info.original_path)

    if not doc_path:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT original_path FROM repo_documents 
                WHERE document_id = (SELECT document_id FROM repo_comparisons WHERE comparison_id = ?)
            """, (session_id,))
            row = cursor.fetchone()
            if row and Path(row["original_path"]).exists():
                doc_path = Path(row["original_path"])

    if not doc_path or not doc_path.exists():
        for p in repo.docs_dir.glob("*.*"):
            doc_path = p
            break

    if not doc_path or not doc_path.exists():
        from specguard.core.config import DEMO_SAMPLES_DIR
        for p in DEMO_SAMPLES_DIR.glob("*.*"):
            doc_path = p
            break

    if not doc_path:
        raise HTTPException(status_code=404, detail="Original document not found for tolerance evaluation.")

    doc_model = DocumentParser.parse_file(str(doc_path))

    return ToleranceCalculator.calculate(
        session_id=session_id,
        doc=doc_model,
        findings=findings,
        profile_identifier=profile_identifier or (rec.domain if rec else "publication"),
        custom_meta=custom_meta,
        custom_max_tolerance=custom_max_tolerance
    )


@router.post("/generate")
def generate_report(req: ReportRequest) -> Dict[str, Any]:
    """Generates a concise formal Document Inspection / Publication Readiness Report."""
    session_id = req.session_id.strip()
    fmt = req.format.lower().strip()
    db = DatabaseManager()

    # Check for existing persisted tolerance report
    custom_provided = any([req.document_no, req.document_title, req.revision, req.inspection_profile, req.max_tolerance])
    persisted = db.get_tolerance_report(session_id)

    if persisted and not custom_provided:
        res = ToleranceResult.from_dict(persisted)
    else:
        res = _evaluate_tolerance(
            session_id=session_id,
            profile_identifier=req.inspection_profile,
            custom_meta={
                "document_no": req.document_no,
                "document_title": req.document_title,
                "revision": req.revision
            },
            custom_max_tolerance=req.max_tolerance
        )
        # Persist so historical reports do not silently change
        db.save_tolerance_report(res.to_dict())

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Standard report file naming per specification:
    # {DOCUMENT_NO}_{SESSION_ID}_Inspection_Report.pdf
    # or {SESSION_ID}_Inspection_Report.pdf if Document No is Not Provided
    clean_doc_no = re.sub(r'[^A-Za-z0-9_-]', '_', res.document_no or "").strip('_')
    clean_sess_id = re.sub(r'[^A-Za-z0-9_-]', '_', res.session_id).strip('_')

    if clean_doc_no and clean_doc_no != "Not_Provided":
        base_name = f"{clean_doc_no}_{clean_sess_id}_Inspection_Report"
    else:
        base_name = f"{clean_sess_id}_Inspection_Report"

    if fmt == "pdf":
        out_filename = f"{base_name}.pdf"
        out_path = REPORTS_DIR / out_filename
        ReportGenerator.generate_pdf_report(res, str(out_path))
    elif fmt == "html":
        out_filename = f"{base_name}.html"
        out_path = REPORTS_DIR / out_filename
        ReportGenerator.generate_html_report(res, str(out_path))
    elif fmt == "json":
        out_filename = f"{base_name}.json"
        out_path = REPORTS_DIR / out_filename
        ReportGenerator.generate_json_report(res, str(out_path))
    elif fmt == "docx":
        out_filename = f"{base_name}.docx"
        out_path = REPORTS_DIR / out_filename
        # DOCX Report
        repo = RepositoryManager()
        findings = repo.get_comparison_findings(session_id)
        # Use dummy empty docx or existing template
        dummy_docx = REPORTS_DIR / f"{clean_sess_id}_temp.docx"
        doc = docx.Document()
        doc.add_paragraph()
        doc.save(str(dummy_docx))
        DOCXAnnotator.create_annotated_docx(str(dummy_docx), str(out_path), findings, res)
        if dummy_docx.exists():
            dummy_docx.unlink()
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format '{fmt}'. Choose pdf, html, json, or docx.")

    return {
        "status": "success",
        "format": fmt,
        "filename": out_filename,
        "file_size": out_path.stat().st_size if out_path.exists() else 0,
        "download_url": f"/api/reports/download/{out_filename}",
        "preview_url": f"/api/reports/preview/{session_id}",
        "tolerance_result": res.to_dict()
    }


@router.get("/preview/{session_id}")
def preview_html_report(session_id: str):
    """Renders the HTML publication inspection report directly in a browser frame."""
    clean_sess_id = re.sub(r'[^A-Za-z0-9_-]', '_', session_id).strip('_')

    # Look for existing generated report
    for f in REPORTS_DIR.glob(f"*{clean_sess_id}*.html"):
        return HTMLResponse(content=f.read_text(encoding="utf-8"))

    # Generate on the fly
    req = ReportRequest(session_id=session_id, format="html")
    res = generate_report(req)
    report_file = REPORTS_DIR / res["filename"]
    return HTMLResponse(content=report_file.read_text(encoding="utf-8"))


@router.get("/download/{filename}")
def download_report(filename: str):
    """Downloads a generated report with proper headers."""
    target = REPORTS_DIR / filename
    if not target.exists():
        raise HTTPException(status_code=404, detail="Report file not found.")

    media_type = "application/octet-stream"
    if filename.endswith(".html"):
        media_type = "text/html"
    elif filename.endswith(".json"):
        media_type = "application/json"
    elif filename.endswith(".pdf"):
        media_type = "application/pdf"
    elif filename.endswith(".docx"):
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    return FileResponse(
        path=str(target),
        filename=filename,
        media_type=media_type
    )
