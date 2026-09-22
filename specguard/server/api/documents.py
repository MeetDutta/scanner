"""
Document Inspection and Page Rendering API for SpecGuard.
Renders high-DPI document pages locally using PyMuPDF and delivers image bytes
directly to the browser canvas viewer with zero external dependencies.
"""

import io
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse, Response
import pymupdf

from specguard.storage.database import DatabaseManager
from specguard.core.models import DocumentModel
from specguard.core.document_parser import DocumentParser
from specguard.repository.manager import RepositoryManager
from specguard.core.config import DEMO_SAMPLES_DIR, DATA_DIR
from specguard.core.rectification import RectificationManager, RectificationError
from specguard.export.pdf_annotator import PDFAnnotator
from specguard.export.docx_annotator import DOCXAnnotator

logger = logging.getLogger("SpecGuard.API.Documents")
router = APIRouter(prefix="/documents", tags=["documents"])


def _find_document_path(doc_identifier: str) -> Optional[Path]:
    """Finds document file path by document_id (DOC-XXXX), SHA-256 hash, or filename."""
    # Direct path check
    direct_p = Path(doc_identifier)
    if direct_p.exists() and direct_p.is_file():
        return direct_p

    # Check demo_samples directory
    demo_p = DEMO_SAMPLES_DIR / doc_identifier
    if demo_p.exists():
        return demo_p

    # Check uploads directory
    uploads_p = DATA_DIR / "uploads" / doc_identifier
    if uploads_p.exists():
        return uploads_p

    db = DatabaseManager()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        # Try repo_documents first
        cursor.execute(
            "SELECT original_path, filename FROM repo_documents WHERE document_id = ? OR sha256 = ? OR filename = ?",
            (doc_identifier, doc_identifier, doc_identifier)
        )
        row = cursor.fetchone()
        if row and Path(row["original_path"]).exists():
            return Path(row["original_path"])

        # Try documents table
        cursor.execute(
            "SELECT file_path, filename FROM documents WHERE file_hash = ? OR filename = ?",
            (doc_identifier, doc_identifier)
        )
        row = cursor.fetchone()
        if row and Path(row["file_path"]).exists():
            return Path(row["file_path"])

    # Check repository archive directly
    repo = RepositoryManager(db=db)
    archived_file = repo.docs_dir / doc_identifier
    if archived_file.exists():
        return archived_file

    # Scan uploads directory by content sha256 hash or filename prefix
    uploads_dir = DATA_DIR / "uploads"
    if uploads_dir.exists():
        for p in uploads_dir.iterdir():
            if p.is_file() and not p.name.startswith("."):
                if doc_identifier in p.name:
                    return p
                if len(doc_identifier) == 64:
                    import hashlib
                    try:
                        h = hashlib.sha256(p.read_bytes()).hexdigest()
                        if h == doc_identifier:
                            return p
                    except Exception:
                        pass

    return None



class RectificationRequest(BaseModel):
    finding_id: str
    operation: str = "suggested"
    field: str = "auto"
    value: Any = None
    note: str = ""


@router.get("/editor/{session_id}")
def rectification_status(session_id: str) -> Dict[str, Any]:
    """Return the session-scoped live editing state and change log."""
    try:
        return RectificationManager(session_id).status()
    except RectificationError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/editor/{session_id}/apply")
def apply_rectification(session_id: str, req: RectificationRequest) -> Dict[str, Any]:
    """Apply one live correction and persist it immediately to the session working copy."""
    try:
        return RectificationManager(session_id).apply(
            finding_id=req.finding_id,
            operation=req.operation,
            field=req.field,
            value=req.value,
            note=req.note,
        )
    except RectificationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Live rectification failed")
        raise HTTPException(status_code=500, detail=f"Rectification failed: {e}")


@router.post("/editor/{session_id}/undo")
def undo_rectification(session_id: str) -> Dict[str, Any]:
    """Reverts the latest applied modification from the session working copy."""
    try:
        return RectificationManager(session_id).undo()
    except RectificationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Undo rectification failed")
        raise HTTPException(status_code=500, detail=f"Undo failed: {e}")


@router.post("/editor/{session_id}/redo")
def redo_rectification(session_id: str) -> Dict[str, Any]:
    """Reapplies the most recently undone modification to the session working copy."""
    try:
        return RectificationManager(session_id).redo()
    except RectificationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Redo rectification failed")
        raise HTTPException(status_code=500, detail=f"Redo failed: {e}")


@router.get("/editor/{session_id}/pages/{page_num}/image")
def get_rectified_page_image(
    session_id: str,
    page_num: int,
    zoom: float = Query(1.5, ge=0.5, le=3.0),
):
    """Render the current session working copy, not the immutable original."""
    try:
        manager = RectificationManager(session_id)
        pdf_path = manager.preview_pdf_path()
        pdf_doc = pymupdf.open(str(pdf_path))
        try:
            if page_num < 1 or page_num > len(pdf_doc):
                raise HTTPException(status_code=400, detail=f"Invalid page number {page_num}.")
            page = pdf_doc[page_num - 1]
            pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
            return Response(content=pix.tobytes("png"), media_type="image/png", headers={"Cache-Control": "no-store"})
        finally:
            pdf_doc.close()
    except HTTPException:
        raise
    except RectificationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed rendering rectified page")
        raise HTTPException(status_code=500, detail=f"Rectified preview failed: {e}")


@router.get("/editor/{session_id}/annotated")
def download_annotated_document(session_id: str):
    """Generates and downloads the session document with all error highlights and callouts embedded."""
    try:
        manager = RectificationManager(session_id)
        repo = RepositoryManager()
        findings = repo.get_comparison_findings(session_id)
        if not findings:
            db = DatabaseManager()
            from specguard.storage.repositories import SessionRepository
            findings = SessionRepository(db).get_findings_for_session(session_id)

        working_path = manager.working_path()
        preview_pdf = manager.preview_pdf_path()
        clean_stem = working_path.stem.replace("working", "").strip("_") or "document"

        if working_path.suffix.lower() == ".docx":
            out_path = manager.session_dir / f"{clean_stem}_annotated_errors.docx"
            DOCXAnnotator.create_annotated_docx(str(working_path), str(out_path), findings)
            dl_name = f"{clean_stem}_annotated_errors.docx"
            return FileResponse(
                path=str(out_path),
                filename=dl_name,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={"Content-Disposition": f'attachment; filename="{dl_name}"'}
            )
        else:
            src_pdf = preview_pdf if preview_pdf.exists() else working_path
            out_path = manager.session_dir / f"{clean_stem}_annotated_errors.pdf"
            PDFAnnotator.create_annotated_pdf(str(src_pdf), str(out_path), findings)
            dl_name = f"{clean_stem}_annotated_errors.pdf"
            return FileResponse(
                path=str(out_path),
                filename=dl_name,
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{dl_name}"'}
            )
    except RectificationError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Failed generating annotated document")
        raise HTTPException(status_code=500, detail=f"Annotated export failed: {e}")


@router.get("/editor/{session_id}/file")
def download_rectified_file(
    session_id: str,
    annotated: bool = Query(False, description="Whether to include embedded visual error highlights")
):
    """Download the current session working document, optionally with error highlights."""
    if annotated:
        return download_annotated_document(session_id)

    try:
        manager = RectificationManager(session_id)
        path = manager.working_path()
        clean_stem = path.stem.replace("working", "").strip("_") or "document"
        dl_name = f"{clean_stem}_rectified{path.suffix.lower()}"
        return FileResponse(
            path=str(path),
            filename=dl_name,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{dl_name}"'}
        )
    except RectificationError as e:
        raise HTTPException(status_code=404, detail=str(e))



@router.get("/editor/{session_id}/changes")
def rectification_changes(session_id: str) -> Dict[str, Any]:
    try:
        return RectificationManager(session_id).change_report()
    except RectificationError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{doc_id}")
def get_document_info(doc_id: str) -> Dict[str, Any]:
    """Returns document metadata and page properties."""
    doc_path = _find_document_path(doc_id)
    if not doc_path or not doc_path.exists():
        raise HTTPException(status_code=404, detail="Document not found.")

    try:
        doc_model = DocumentParser.parse_file(str(doc_path))
        from dataclasses import asdict

        pages_summary = []
        for p in doc_model.pages:
            pages_summary.append({
                "page_num": p.page_num,
                "width": p.width,
                "height": p.height,
                "text_length": len(p.text),
                "text_snippet": p.text[:150] if p.text else "",
                "blocks_count": len(p.blocks),
                "tables_count": len(p.tables),
                "figures_count": len(p.figures),
                "layout_type": getattr(p, "layout_type", "single_column"),
                "reading_order_count": len(getattr(p, "reading_order", []))
            })

        toc_dict = asdict(doc_model.toc) if doc_model.toc else None
        sections_dict = [asdict(s) for s in doc_model.sections]
        figures_dict = [asdict(f) for f in doc_model.figures]
        tables_dict = [asdict(t) for t in doc_model.tables]
        equations_dict = [asdict(eq) for eq in doc_model.equations]
        cross_refs_dict = [asdict(xr) for xr in doc_model.cross_references]

        return {
            "filename": doc_path.name,
            "file_path": str(doc_path),
            "file_hash": doc_model.file_hash,
            "file_size": doc_model.file_size,
            "file_type": doc_model.file_type,
            "page_count": doc_model.page_count,
            "pages": pages_summary,
            "sections": sections_dict,
            "toc": toc_dict,
            "figures": figures_dict,
            "tables": tables_dict,
            "equations": equations_dict,
            "cross_references": cross_refs_dict,
            "warnings": doc_model.warnings,
            "metadata": doc_model.metadata
        }
    except Exception as e:
        logger.error("Failed parsing document info for %s: %s", doc_path, e)
        raise HTTPException(status_code=500, detail=f"Failed inspecting document: {e}")


@router.get("/{doc_id}/pages/{page_num}/image")
def get_page_image(
    doc_id: str,
    page_num: int,
    zoom: float = Query(1.5, ge=0.5, le=3.0)
):
    """
    Renders high-DPI document page directly to PNG bytes using PyMuPDF.
    Allows exact pixel-perfect rendering with zero external services.
    """
    doc_path = _find_document_path(doc_id)
    if not doc_path or not doc_path.exists():
        raise HTTPException(status_code=404, detail="Document not found.")

    ext = doc_path.suffix.lower()

    # Case 1: PDF Document
    if ext == ".pdf":
        try:
            pdf_doc = pymupdf.open(str(doc_path))
            if page_num < 1 or page_num > len(pdf_doc):
                pdf_doc.close()
                raise HTTPException(status_code=400, detail=f"Invalid page number {page_num}.")

            page = pdf_doc[page_num - 1]
            matrix = pymupdf.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            png_bytes = pix.tobytes("png")
            pdf_doc.close()
            return Response(content=png_bytes, media_type="image/png")
        except Exception as e:
            logger.error("Failed rendering PDF page %d: %s", page_num, e)
            raise HTTPException(status_code=500, detail=f"Rendering error: {e}")

    # Case 2: Image formats (PNG, JPG, TIFF)
    elif ext in [".png", ".jpg", ".jpeg", ".tiff", ".tif"]:
        try:
            img_doc = pymupdf.open(str(doc_path))
            page = img_doc[0]
            matrix = pymupdf.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            png_bytes = pix.tobytes("png")
            img_doc.close()
            return Response(content=png_bytes, media_type="image/png")
        except Exception as e:
            logger.error("Failed rendering image page: %s", e)
            raise HTTPException(status_code=500, detail=f"Rendering error: {e}")

    # Case 3: Text / DOCX / Spreadsheet fallback - generate clean SVG/PNG preview
    else:
        try:
            doc_model = DocumentParser.parse_file(str(doc_path))
            page_text = ""
            if 1 <= page_num <= len(doc_model.pages):
                page_text = doc_model.pages[page_num - 1].text

            # Create an in-memory synthetic PDF page and render it to PNG with PyMuPDF
            temp_pdf = pymupdf.open()
            page = temp_pdf.new_page(width=612, height=792)
            page.insert_text(
                (40, 50),
                f"SpecGuard Document Preview — {doc_path.name} (Page {page_num}/{doc_model.page_count})",
                fontsize=13,
                fontname="helv",
                color=(0.1, 0.2, 0.4)
            )
            page.draw_line((40, 65), (572, 65), color=(0.7, 0.8, 0.9), width=1)

            lines = page_text.splitlines()[:42]
            y = 90
            for line in lines:
                if line.strip():
                    page.insert_text((40, y), line[:85], fontsize=9.5, fontname="couri", color=(0.15, 0.2, 0.25))
                    y += 15

            matrix = pymupdf.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            png_bytes = pix.tobytes("png")
            temp_pdf.close()
            return Response(content=png_bytes, media_type="image/png")
        except Exception as e:
            logger.error("Failed rendering fallback text preview: %s", e)
            raise HTTPException(status_code=500, detail=f"Preview error: {e}")


@router.get("/{doc_id}/file")
def download_original_file(doc_id: str):
    """Safely downloads or streams the original document."""
    doc_path = _find_document_path(doc_id)
    if not doc_path or not doc_path.exists():
        raise HTTPException(status_code=404, detail="Document not found.")

    return FileResponse(
        path=str(doc_path),
        filename=doc_path.name,
        media_type="application/octet-stream"
    )
