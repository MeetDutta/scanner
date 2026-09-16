"""
Reports Generation and Export API for SpecGuard.
Produces publication-quality certified PDF, DOCX, HTML, and JSON audit reports
strictly using the local export engines.
"""

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
from specguard.export.pdf_annotator import PDFAnnotator
from specguard.core.document_parser import DocumentParser

logger = logging.getLogger("SpecGuard.API.Reports")
router = APIRouter(prefix="/reports", tags=["reports"])


class ReportRequest(BaseModel):
    session_id: str
    format: str = "html"  # html, json, pdf, docx


@router.post("/generate")
def generate_report(req: ReportRequest) -> Dict[str, Any]:
    """Generates an audit report in the specified format."""
    repo = RepositoryManager()
    session_id = req.session_id
    fmt = req.format.lower().strip()

    rec = repo.get_comparison_record(session_id)
    findings = repo.get_comparison_findings(session_id)

    if not rec:
        # Fallback to session repository
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM analysis_sessions WHERE session_id = ?", (session_id,))
            s_row = cursor.fetchone()
            if not s_row:
                raise HTTPException(status_code=404, detail=f"Analysis session {session_id} not found.")

        # Get findings from findings table
        from specguard.storage.repositories import SessionRepository
        findings = SessionRepository(db).get_findings_for_session(session_id)

    # Resolve original document
    doc_path = None
    if rec:
        doc_info = repo.get_document(rec.document_id)
        if doc_info and Path(doc_info.original_path).exists():
            doc_path = Path(doc_info.original_path)

    if not doc_path:
        # Check if file exists in demo_samples or uploads
        db = DatabaseManager()
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
        # Look in repository documents
        for p in repo.docs_dir.glob("*.*"):
            doc_path = p
            break

    if not doc_path:
        raise HTTPException(status_code=404, detail="Original document not found for report generation.")

    doc_model = DocumentParser.parse_file(str(doc_path))

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    clean_stem = Path(doc_model.file_path).stem

    if fmt == "html":
        out_filename = f"{clean_stem}_{session_id}_Audit.html"
        out_path = REPORTS_DIR / out_filename
        ReportGenerator.generate_html_report(doc_model, findings, session_id, str(out_path))
    elif fmt == "json":
        out_filename = f"{clean_stem}_{session_id}_Findings.json"
        out_path = REPORTS_DIR / out_filename
        ReportGenerator.generate_json_report(doc_model, findings, session_id, str(out_path))
    elif fmt == "pdf":
        out_filename = f"{clean_stem}_{session_id}_Annotated.pdf"
        out_path = REPORTS_DIR / out_filename
        if Path(doc_model.file_path).suffix.lower() == ".pdf":
            PDFAnnotator.create_annotated_pdf(doc_model.file_path, str(out_path), findings)
        else:
            # Fallback to HTML report if original document is not PDF
            out_filename = f"{clean_stem}_{session_id}_Audit.html"
            out_path = REPORTS_DIR / out_filename
            ReportGenerator.generate_html_report(doc_model, findings, session_id, str(out_path))
    elif fmt == "docx":
        out_filename = f"{clean_stem}_{session_id}_Annotated.docx"
        out_path = REPORTS_DIR / out_filename
        if Path(doc_model.file_path).suffix.lower() == ".docx":
            DOCXAnnotator.create_annotated_docx(doc_model.file_path, str(out_path), findings)
        else:
            # Fallback to HTML report if original is non-DOCX
            out_filename = f"{clean_stem}_{session_id}_Audit.html"
            out_path = REPORTS_DIR / out_filename
            ReportGenerator.generate_html_report(doc_model, findings, session_id, str(out_path))
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format '{fmt}'. Choose html, json, pdf, or docx.")

    return {
        "status": "success",
        "format": fmt,
        "filename": out_filename,
        "file_size": out_path.stat().st_size if out_path.exists() else 0,
        "download_url": f"/api/reports/download/{out_filename}",
        "preview_url": f"/api/reports/preview/{session_id}" if fmt == "html" else None
    }


@router.get("/preview/{session_id}")
def preview_html_report(session_id: str):
    """Renders the HTML compliance report directly in a browser frame."""
    # Check if existing report file exists
    for f in REPORTS_DIR.glob(f"*{session_id}*.html"):
        return HTMLResponse(content=f.read_text(encoding="utf-8"))

    # Generate on the fly
    req = ReportRequest(session_id=session_id, format="html")
    res = generate_report(req)
    report_file = REPORTS_DIR / res["filename"]
    return HTMLResponse(content=report_file.read_text(encoding="utf-8"))


@router.get("/download/{filename}")
def download_report(filename: str):
    """Downloads a generated report."""
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
