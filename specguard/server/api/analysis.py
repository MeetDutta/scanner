"""
Analysis Execution and Progress Tracking API for SpecGuard.
Coordinates document upload, domain selection, pipeline execution,
and fine-grained stage progress events without internet dependencies.
"""

import os
import time
import uuid
import shutil
import hashlib
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from specguard.core.config import DATA_DIR, DEMO_SAMPLES_DIR
from specguard.core.models import DocumentModel, Finding
from specguard.core.document_parser import DocumentParser
from specguard.core.pipeline import AnalysisPipeline
from specguard.templates.manager import TemplateManager
from specguard.storage.database import DatabaseManager
from specguard.repository.manager import RepositoryManager

logger = logging.getLogger("SpecGuard.API.Analysis")
router = APIRouter(prefix="/analysis", tags=["analysis"])

UPLOADS_DIR = DATA_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".xlsx", ".xls", ".txt",
    ".png", ".jpg", ".jpeg", ".tiff", ".tif"
}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

# In-memory thread-safe job state tracker
ANALYSIS_JOBS: Dict[str, Dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()


class CancellationToken:
    def __init__(self):
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True


class AnalysisRequest(BaseModel):
    file_path: Optional[str] = None
    file_hash: Optional[str] = None
    domain: str = "mechanical"
    profile: Optional[str] = None
    selected_standards: List[str] = []
    enabled_modules: Optional[List[str]] = None


def sanitize_filename(filename: str) -> str:
    """Safe alphanumeric filename preservation, preventing directory traversal."""
    base = Path(filename).name
    clean = "".join(c for c in base if c.isalnum() or c in "._- ")
    clean = clean.lstrip(".")
    return clean or "document"


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Uploads and validates a document for analysis with path containment verification."""
    filename = sanitize_filename(file.filename or "uploaded_doc")
    ext = Path(filename).suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    # Secure target destination with UUID prefix and directory containment check
    unique_prefix = uuid.uuid4().hex[:8]
    temp_target = (UPLOADS_DIR / f"{unique_prefix}_{filename}").resolve()
    if not str(temp_target).startswith(str(UPLOADS_DIR.resolve())):
        raise HTTPException(status_code=400, detail="Invalid file destination path.")

    sha256 = hashlib.sha256()
    size = 0

    try:
        with open(temp_target, "wb") as f:
            while chunk := await file.read(65536):
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    raise HTTPException(status_code=413, detail="File exceeds 100 MB limit.")
                sha256.update(chunk)
                f.write(chunk)
    except Exception as e:
        if temp_target.exists():
            temp_target.unlink()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")

    file_hash = sha256.hexdigest()

    # Pre-parse metadata
    try:
        doc = DocumentParser.parse_file(str(temp_target))
        page_count = doc.page_count
        file_type = doc.file_type
    except Exception as e:
        logger.warning("Fast inspection failed; basic metadata will be used: %s", e)
        page_count = 1
        file_type = ext.replace(".", "").upper()

    return {
        "filename": filename,
        "file_path": str(temp_target),
        "file_hash": file_hash,
        "file_size": size,
        "page_count": page_count,
        "file_type": file_type,
        "status": "ready"
    }


@router.get("/samples")
def list_demo_samples() -> List[Dict[str, Any]]:
    """Lists available local sample documents for immediate evaluation."""
    return []


def _run_pipeline_worker(
    job_id: str,
    file_path: str,
    domain: str,
    profile: Optional[str],
    selected_standards: List[str],
    cancel_token: CancellationToken
):
    """Background worker executing the real SpecGuard analysis pipeline."""
    with JOBS_LOCK:
        job = ANALYSIS_JOBS.get(job_id)
        if not job:
            return
        job["status"] = "running"
        job["stage"] = "Initializing analysis pipeline..."
        job["percent"] = 5
        job["start_time"] = time.time()

    def progress_cb(stage_name: str, pct: int):
        with JOBS_LOCK:
            if job_id in ANALYSIS_JOBS:
                if cancel_token.is_cancelled:
                    raise InterruptedError("Analysis cancelled by user.")
                ANALYSIS_JOBS[job_id]["stage"] = stage_name
                ANALYSIS_JOBS[job_id]["percent"] = pct
                ANALYSIS_JOBS[job_id]["stages_log"].append({
                    "stage": stage_name,
                    "percent": pct,
                    "time": round(time.time() - job["start_time"], 2)
                })

    try:
        pipeline = AnalysisPipeline()
        doc, findings, session_id = pipeline.run_analysis(
            file_path=file_path,
            domain=domain,
            profile=profile,
            selected_standards=selected_standards,
            progress_callback=progress_cb,
            cancellation_token=cancel_token
        )

        with JOBS_LOCK:
            if job_id in ANALYSIS_JOBS:
                duration_ms = int((time.time() - job["start_time"]) * 1000)
                ANALYSIS_JOBS[job_id].update({
                    "status": "completed",
                    "stage": "Analysis complete.",
                    "percent": 100,
                    "session_id": session_id,
                    "duration_ms": duration_ms,
                    "total_findings": len(findings),
                    "doc_hash": doc.file_hash,
                    "page_count": doc.page_count,
                    "filename": Path(doc.file_path).name,
                    "file_path": doc.file_path,
                    "domain": domain,
                    "profile": profile or domain
                })
                logger.info("Job %s completed successfully in %d ms.", job_id, duration_ms)
    except InterruptedError as ie:
        logger.info("Job %s was cleanly cancelled: %s", job_id, ie)
        with JOBS_LOCK:
            if job_id in ANALYSIS_JOBS:
                ANALYSIS_JOBS[job_id].update({
                    "status": "cancelled",
                    "stage": "Analysis cancelled.",
                    "percent": 0
                })
    except Exception as e:
        logger.error("Job %s failed: %s", job_id, e, exc_info=True)
        with JOBS_LOCK:
            if job_id in ANALYSIS_JOBS:
                ANALYSIS_JOBS[job_id].update({
                    "status": "failed",
                    "stage": f"Error: {str(e)}",
                    "error": str(e),
                    "percent": 0
                })


@router.post("/start")
def start_analysis(req: AnalysisRequest, bg_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Starts asynchronous document analysis."""
    file_path = req.file_path
    if not file_path:
        raise HTTPException(status_code=400, detail="Target document path is required.")

    target = Path(file_path).resolve()
    # Path traversal protection: Ensure target is within legitimate data or resource directories
    allowed_roots = [
        UPLOADS_DIR.resolve(),
        DEMO_SAMPLES_DIR.resolve(),
        DATA_DIR.resolve(),
    ]
    if not any(root == target or root in target.parents for root in allowed_roots) or not target.exists():
        raise HTTPException(status_code=400, detail="Target document path is invalid or does not exist.")

    file_path = str(target)

    job_id = f"JOB-{uuid.uuid4().hex[:8].upper()}"
    cancel_token = CancellationToken()

    with JOBS_LOCK:
        ANALYSIS_JOBS[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "stage": "Queued for processing...",
            "percent": 0,
            "file_path": file_path,
            "filename": Path(file_path).name,
            "domain": req.domain.lower(),
            "profile": req.profile or req.domain.lower(),
            "selected_standards": req.selected_standards,
            "stages_log": [],
            "start_time": time.time(),
            "cancel_token": cancel_token,
            "cancel_requested": False,
            "error": None
        }

    bg_tasks.add_task(
        _run_pipeline_worker,
        job_id=job_id,
        file_path=file_path,
        domain=req.domain.lower(),
        profile=req.profile,
        selected_standards=req.selected_standards,
        cancel_token=cancel_token
    )

    return {"job_id": job_id, "status": "queued"}


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str) -> Dict[str, Any]:
    """Polls real-time stage progress for an analysis job."""
    with JOBS_LOCK:
        job = ANALYSIS_JOBS.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Analysis job not found.")
        # Return shallow copy without unpicklable token
        res = {k: v for k, v in job.items() if k != "cancel_token"}
        return res


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str) -> Dict[str, Any]:
    """Requests safe cancellation of a running analysis."""
    with JOBS_LOCK:
        job = ANALYSIS_JOBS.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Analysis job not found.")
        if job["status"] in ["completed", "failed", "cancelled"]:
            return {"status": job["status"], "message": "Job already finished."}
        job["cancel_requested"] = True
        if "cancel_token" in job:
            job["cancel_token"].cancel()
        job["status"] = "cancelling"
    return {"status": "cancelling", "message": "Cancellation signal sent."}


@router.get("/jobs/{job_id}/stream")
def stream_job_progress(job_id: str):
    """Server-Sent Events stream for live analysis stage updates."""
    with JOBS_LOCK:
        if job_id not in ANALYSIS_JOBS:
            raise HTTPException(status_code=404, detail="Analysis job not found.")

    def event_generator():
        import json
        last_percent = -1
        last_stage = ""

        while True:
            with JOBS_LOCK:
                job = ANALYSIS_JOBS.get(job_id)
                if not job:
                    break
                current_percent = job.get("percent", 0)
                current_stage = job.get("stage", "")
                status = job.get("status", "unknown")
                session_id = job.get("session_id")
                error = job.get("error")

            if current_percent != last_percent or current_stage != last_stage or status in ["completed", "failed"]:
                payload = {
                    "job_id": job_id,
                    "status": status,
                    "stage": current_stage,
                    "percent": current_percent,
                    "session_id": session_id,
                    "error": error
                }
                yield f"data: {json.dumps(payload)}\n\n"
                last_percent = current_percent
                last_stage = current_stage

            if status in ["completed", "failed"]:
                break

            time.sleep(0.15)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/session/{session_id}")
def get_analysis_session(session_id: str) -> Dict[str, Any]:
    """
    Retrieves the canonical persisted analysis session record, document metadata,
    and summary counts. Supports 'latest' to fetch the most recent completed analysis.
    """
    db = DatabaseManager()
    repo = RepositoryManager(db=db)

    target_id = session_id.strip()
    if target_id.lower() == "latest":
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT comparison_id FROM repo_comparisons ORDER BY rowid DESC LIMIT 1")
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="No analysis session found.")
            target_id = row["comparison_id"]

    rec = repo.get_comparison_record(target_id)
    if not rec:
        # Check analysis_sessions fallback
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM analysis_sessions WHERE session_id = ?", (target_id,))
            s_row = cursor.fetchone()
            if not s_row:
                raise HTTPException(status_code=404, detail=f"Analysis session '{session_id}' not found.")
            findings = repo.get_comparison_findings(target_id)
            return {
                "session_id": s_row["session_id"],
                "comparison_id": s_row["session_id"],
                "status": "COMPLETED",
                "domain": s_row["domain"],
                "total_findings": s_row["findings_count"],
                "critical_count": s_row["critical_count"],
                "high_count": s_row["high_count"],
                "medium_count": s_row["medium_count"],
                "low_count": s_row["low_count"],
                "info_count": s_row["info_count"],
                "findings_count": len(findings),
                "document": {
                    "filename": "Engineering Document",
                    "file_hash": s_row["document_hash"],
                    "page_count": 1
                },
                "findings": [f.to_dict() for f in findings]
            }

    doc_info = repo.get_document(rec.document_id)
    findings = repo.get_comparison_findings(target_id)

    # Check for tolerance report
    tol_record = None
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM document_tolerance_reports WHERE session_id = ?", (target_id,))
        t_row = cursor.fetchone()
        if t_row:
            tol_record = dict(t_row)

    crit_count = sum(1 for f in findings if (f.severity or "").upper() == "CRITICAL")
    high_count = sum(1 for f in findings if (f.severity or "").upper() == "HIGH")
    med_count = sum(1 for f in findings if (f.severity or "").upper() == "MEDIUM")
    low_count = sum(1 for f in findings if (f.severity or "").upper() == "LOW")
    info_count = sum(1 for f in findings if (f.severity or "").upper() in ("INFORMATIONAL", "INFO"))

    return {
        "session_id": rec.comparison_id,
        "comparison_id": rec.comparison_id,
        "document_id": rec.document_id,
        "document_filename": rec.document_filename,
        "document_sha256": rec.document_sha256,
        "domain": rec.domain,
        "status": rec.status or "COMPLETED",
        "analysis_started_at": rec.analysis_started_at,
        "analysis_completed_at": rec.analysis_completed_at,
        "duration_ms": rec.duration_ms,
        "model_version": rec.model_version,
        "total_findings": len(findings),
        "critical_count": crit_count,
        "high_count": high_count,
        "medium_count": med_count,
        "low_count": low_count,
        "info_count": info_count,
        "findings_count": len(findings),
        "document": {
            "filename": doc_info.filename if doc_info else rec.document_filename,
            "file_type": doc_info.file_type if doc_info else "PDF",
            "file_size": doc_info.file_size if doc_info else 0,
            "page_count": doc_info.page_count if doc_info else 1,
            "original_path": doc_info.original_path if doc_info else "",
            "file_hash": rec.document_sha256
        },
        "tolerance": tol_record,
        "findings": [f.to_dict() for f in findings]
    }


