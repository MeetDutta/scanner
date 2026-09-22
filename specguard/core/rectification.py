"""Live document rectification engine.

Keeps an isolated working copy per analysis session, applies user-confirmed
format/text changes to DOCX/PDF documents, and records an append-only change log.
All operations are local/offline.
"""
from __future__ import annotations

import json
import re
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pymupdf
from docx import Document
from docx.shared import Pt

from specguard.core.config import REPO_DIR
from specguard.storage.database import DatabaseManager


class RectificationError(RuntimeError):
    pass


class RectificationManager:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.db = DatabaseManager()
        self.session_dir = REPO_DIR / "comparisons" / session_id / "rectification"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.revisions_dir = self.session_dir / "revisions"
        self.revisions_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.session_dir / "state.json"
        self._ensure_state()

    def _comparison(self) -> Dict[str, Any]:
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT * FROM repo_comparisons WHERE comparison_id = ?", (self.session_id,)).fetchone()
            if row:
                doc = conn.execute("SELECT * FROM repo_documents WHERE document_id = ?", (row["document_id"],)).fetchone()
                if doc and Path(doc["original_path"]).exists():
                    return {"comparison": dict(row), "document": dict(doc), "source": Path(doc["original_path"])}
            # Fallback to analysis_sessions if comparison not found in repo_comparisons
            row_session = conn.execute("SELECT * FROM analysis_sessions WHERE session_id = ?", (self.session_id,)).fetchone()
            if row_session:
                doc_row = conn.execute("SELECT * FROM documents WHERE file_hash = ?", (row_session["document_hash"],)).fetchone()
                if doc_row and Path(doc_row["file_path"]).exists():
                    return {"comparison": dict(row_session), "document": dict(doc_row), "source": Path(doc_row["file_path"])}

        # Check repository directly
        comp_dir = REPO_DIR / "comparisons" / self.session_id
        if (comp_dir / "comparison.json").exists():
            comp_data = json.loads((comp_dir / "comparison.json").read_text(encoding="utf-8"))
            doc_id = comp_data.get("document_id")
            if doc_id:
                doc_path = REPO_DIR / "documents" / doc_id / "original" / comp_data.get("document_filename", "")
                if doc_path.exists():
                    return {"comparison": comp_data, "document": {"document_id": doc_id, "filename": comp_data.get("document_filename")}, "source": doc_path}

        raise RectificationError(f"Analysis session '{self.session_id}' or source document was not found.")

    def _ensure_state(self) -> None:
        if self.state_path.exists():
            return
        info = self._comparison()
        source: Path = info["source"]
        working = self.session_dir / f"working{source.suffix.lower()}"
        shutil.copy2(source, working)
        # Snapshot baseline revision 0
        rev0_backup = self.revisions_dir / f"rev_0{source.suffix.lower()}"
        if not rev0_backup.exists():
            shutil.copy2(source, rev0_backup)
        state = {
            "session_id": self.session_id,
            "source_filename": source.name,
            "source_path": str(source),
            "working_path": str(working),
            "working_format": source.suffix.lower().lstrip("."),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "revision": 0,
            "changes": [],
            "undone_changes": [],
        }
        self._write_state(state)

    def _read_state(self) -> Dict[str, Any]:
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _write_state(self, state: Dict[str, Any]) -> None:
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.state_path)

    def status(self) -> Dict[str, Any]:
        state = self._read_state()
        changes = state.get("changes", [])
        undone = state.get("undone_changes", [])
        return {
            "session_id": self.session_id,
            "source_filename": state["source_filename"],
            "working_filename": Path(state["working_path"]).name,
            "working_format": state["working_format"],
            "revision": state["revision"],
            "updated_at": state["updated_at"],
            "changes": changes,
            "change_count": len(changes),
            "can_undo": len(changes) > 0,
            "can_redo": len(undone) > 0,
        }

    def working_path(self) -> Path:
        state = self._read_state()
        p = Path(state["working_path"])
        if not p.exists():
            raise RectificationError("Working document is missing.")
        return p

    @staticmethod
    def _parse_numeric(value: str) -> Optional[float]:
        m = re.search(r"(-?\d+(?:\.\d+)?)", str(value or ""))
        return float(m.group(1)) if m else None

    @staticmethod
    def _extract_font_name(value: str) -> Optional[str]:
        m = re.search(r"(?:font(?:\s+to)?|typeface)\s*[:=]?\s*['\"]?([^'\".]+?)['\"]?(?:\.|$)", str(value), re.I)
        return m.group(1).strip() if m else None

    def _finding(self, finding_id: str) -> Dict[str, Any]:
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM repo_findings WHERE comparison_id = ? AND finding_id = ?",
                (self.session_id, finding_id),
            ).fetchone()
        if row:
            result = dict(row)
            if result.get("bbox_json"):
                try:
                    result["bbox"] = json.loads(result["bbox_json"])
                except Exception:
                    result["bbox"] = None
            return result

        # Fallback to comparison findings.json
        findings_path = REPO_DIR / "comparisons" / self.session_id / "findings.json"
        if findings_path.exists():
            try:
                items = json.loads(findings_path.read_text(encoding="utf-8"))
                for item in items:
                    if item.get("finding_id") == finding_id:
                        return item
            except Exception:
                pass

        raise RectificationError(f"Finding '{finding_id}' was not found in this session.")

    def _record(self, finding: Dict[str, Any], operation: str, field: str,
                before: Any, after: Any, note: str = "") -> Dict[str, Any]:
        state = self._read_state()
        change = {
            "change_id": f"CHG-{len(state['changes']) + 1:04d}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "finding_id": finding["finding_id"],
            "page": finding.get("page") or finding.get("page_number") or 1,
            "location": finding.get("location", ""),
            "category": finding.get("category", ""),
            "issue_type": finding.get("issue_type", ""),
            "suggested": finding.get("suggested_fix") or finding.get("suggested_correction") or "",
            "operation": operation,
            "field": field,
            "before": before,
            "after": after,
            "status": "APPLIED",
            "note": note,
        }
        state["changes"].append(change)
        state["revision"] += 1
        state["undone_changes"] = []  # Clear redo stack upon new mutation
        state["updated_at"] = change["timestamp"]
        self._write_state(state)
        return change

    def apply(self, finding_id: str, operation: str = "suggested", field: str = "auto",
              value: Any = None, note: str = "") -> Dict[str, Any]:
        finding = self._finding(finding_id)
        state = self._read_state()
        working = Path(state["working_path"])
        ext = working.suffix.lower()
        operation = operation.lower().strip()

        if operation == "suggested":
            suggestion = finding.get("suggested_correction") or finding.get("suggested_fix") or ""
            if re.search(r"font\s+to", suggestion, re.I) or re.search(r"typeface", suggestion, re.I):
                field = "font_name"
                value = self._extract_font_name(suggestion)
            elif re.search(r"size|pt", suggestion, re.I):
                field = "font_size"
                value = self._parse_numeric(suggestion)
            elif re.search(r"replace|change|correct", suggestion, re.I) and finding.get("expected_value"):
                field = "text"
                value = finding.get("expected_value")
            elif finding.get("expected_text") or finding.get("expected_value"):
                field = "text"
                value = finding.get("expected_text") or finding.get("expected_value")
            else:
                field = "text"
                value = suggestion or finding.get("matched_text")
            operation = "format" if field in {"font_name", "font_size", "bold", "italic"} else "text"

        if value is None or (isinstance(value, str) and not value.strip()):
            value = finding.get("expected_value") or finding.get("expected_text") or finding.get("suggested_fix") or "Corrected"

        # Snapshot current working copy before applying mutation
        current_rev = state["revision"]
        snapshot_file = self.revisions_dir / f"rev_{current_rev}{ext}"
        shutil.copy2(working, snapshot_file)

        if ext == ".docx":
            before = self._apply_docx(working, finding, field, value)
        elif ext == ".pdf":
            before = self._apply_pdf(working, finding, field, value)
        else:
            raise RectificationError(f"Live rectification is currently supported for DOCX and PDF, not {ext or 'this file type'}.")

        # Also snapshot new working copy as latest revision
        new_snapshot_file = self.revisions_dir / f"rev_{current_rev + 1}{ext}"
        shutil.copy2(working, new_snapshot_file)

        change = self._record(finding, operation, field, before, value, note)
        return {"status": "saved", "change": change, **self.status()}

    def undo(self) -> Dict[str, Any]:
        """Rolls back the latest applied modification using revision snapshot."""
        state = self._read_state()
        changes = state.get("changes", [])
        if not changes:
            raise RectificationError("No changes available to undo.")

        last_change = changes.pop()
        last_change["status"] = "UNDONE"
        undone = state.get("undone_changes", [])
        undone.append(last_change)

        current_rev = state["revision"]
        prev_rev = max(0, current_rev - 1)
        working = Path(state["working_path"])
        ext = working.suffix.lower()
        backup_file = self.revisions_dir / f"rev_{prev_rev}{ext}"
        if backup_file.exists():
            shutil.copy2(backup_file, working)

        state["revision"] = prev_rev
        state["changes"] = changes
        state["undone_changes"] = undone
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._write_state(state)
        return {"status": "undone", "reverted_change": last_change, **self.status()}

    def redo(self) -> Dict[str, Any]:
        """Reapplies the most recently undone modification."""
        state = self._read_state()
        undone = state.get("undone_changes", [])
        if not undone:
            raise RectificationError("No changes available to redo.")

        redo_change = undone.pop()
        redo_change["status"] = "APPLIED"

        current_rev = state["revision"]
        next_rev = current_rev + 1
        working = Path(state["working_path"])
        ext = working.suffix.lower()
        forward_file = self.revisions_dir / f"rev_{next_rev}{ext}"
        if forward_file.exists():
            shutil.copy2(forward_file, working)

        state["revision"] = next_rev
        state["changes"].append(redo_change)
        state["undone_changes"] = undone
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._write_state(state)
        return {"status": "redone", "reapplied_change": redo_change, **self.status()}

    def _target_text(self, finding: Dict[str, Any]) -> str:
        return str(finding.get("original_content") or finding.get("detected_value") or finding.get("matched_text") or "").strip()

    def _apply_docx(self, path: Path, finding: Dict[str, Any], field: str, value: Any) -> Any:
        doc = Document(str(path))
        target = self._target_text(finding)
        target_short = target.replace("...", "").strip() if target else ""
        matches = []
        if target_short:
            for p in doc.paragraphs:
                if target_short in p.text:
                    matches.append(p)
            if not matches:
                probe = re.sub(r"\s+", " ", target_short)[:45]
                for p in doc.paragraphs:
                    if probe and probe in re.sub(r"\s+", " ", p.text):
                        matches.append(p)

        if not matches and doc.paragraphs:
            matches.append(doc.paragraphs[0])

        if not matches:
            raise RectificationError("Could not locate an editable paragraph in the working DOCX.")

        p = matches[0]
        before = p.text
        if field == "text":
            replacement = str(value)
            if target_short and target_short in p.text:
                for r in p.runs:
                    if target_short in r.text:
                        r.text = r.text.replace(target_short, replacement, 1)
                        break
                else:
                    p.text = p.text.replace(target_short, replacement, 1)
            else:
                p.text = replacement
        elif field == "font_size":
            size = float(value)
            for r in p.runs:
                r.font.size = Pt(size)
        elif field == "font_name":
            name = str(value).strip()
            for r in p.runs:
                r.font.name = name
                r._element.get_or_add_rPr().rFonts.set("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}eastAsia", name)
        elif field in {"bold", "italic"}:
            flag = bool(value)
            for r in p.runs:
                setattr(r.font, field, flag)
        else:
            raise RectificationError(f"Unsupported DOCX field '{field}'.")
        doc.save(str(path))
        return before

    @staticmethod
    def _pdf_font(value: str) -> str:
        v = str(value).lower()
        if "courier" in v or "mono" in v:
            return "cour"
        if "times" in v or "serif" in v:
            return "tiro"
        return "helv"

    def _apply_pdf(self, path: Path, finding: Dict[str, Any], field: str, value: Any) -> Any:
        bbox = finding.get("bbox")
        rect = None
        if bbox and isinstance(bbox, dict) and "x0" in bbox and "y0" in bbox:
            try:
                rect = pymupdf.Rect(float(bbox["x0"]), float(bbox["y0"]), float(bbox["x1"]), float(bbox["y1"]))
            except Exception:
                rect = None

        page_num = int(finding.get("page") or finding.get("page_number") or 1)
        doc = pymupdf.open(str(path))
        try:
            if page_num < 1 or page_num > len(doc):
                page_num = 1
            page = doc[page_num - 1]
            target = self._target_text(finding)

            # If no bbox or empty rect, search the page text for candidate strings
            if not rect or rect.is_empty:
                candidates = [
                    target,
                    finding.get("matched_text"),
                    finding.get("detected_value"),
                    finding.get("expected_value"),
                    finding.get("expected_text")
                ]
                for cand in candidates:
                    if cand and str(cand).strip() and str(cand) not in {"Parameter absent", "N/A"}:
                        clean_cand = str(cand).strip()
                        rects = page.search_for(clean_cand)
                        if not rects and len(clean_cand) > 25:
                            rects = page.search_for(clean_cand[:20])
                        if rects:
                            rect = rects[0]
                            break

            # If still not found, construct a safe fallback annotation region on the page
            if not rect or rect.is_empty:
                rect = pymupdf.Rect(54.0, 72.0, max(200.0, page.rect.width - 54.0), 105.0)

            words = page.get_text("words", clip=rect)
            before = " ".join(str(w[4]) for w in words).strip() or target or "(Original Region)"

            fontsize = float(value) if field == "font_size" else 10.0
            if field == "font_size":
                replacement = before
                fontname = "helv"
            elif field == "font_name":
                replacement = before
                fontsize = max(6.0, rect.height * 0.72)
                fontname = self._pdf_font(str(value))
            elif field == "text":
                replacement = str(value)
                fontsize = max(7.0, min(13.0, rect.height * 0.75))
                fontname = "helv"
            elif field in {"bold", "italic"}:
                replacement = before
                fontsize = max(7.0, min(13.0, rect.height * 0.75))
                fontname = "helv"
            else:
                replacement = str(value)
                fontname = "helv"

            page.add_redact_annot(rect, fill=(1, 1, 1))
            page.apply_redactions()

            # Insert text, adaptively shrinking font size if needed so it always fits
            rc = page.insert_textbox(rect, replacement, fontsize=fontsize, fontname=fontname, color=(0, 0, 0), align=0, overlay=True)
            while rc < 0 and fontsize > 5.0:
                fontsize -= 0.5
                rc = page.insert_textbox(rect, replacement, fontsize=fontsize, fontname=fontname, color=(0, 0, 0), align=0, overlay=True)

            temp = path.with_suffix(path.suffix + ".tmp")
            doc.save(str(temp), garbage=4, deflate=True)
            doc.close()
            temp.replace(path)
            return before
        except Exception:
            doc.close()
            raise

    def preview_pdf_path(self) -> Path:
        working = self.working_path()
        if working.suffix.lower() == ".pdf":
            return working
        if working.suffix.lower() == ".docx":
            import shutil as _shutil
            import subprocess
            soffice = _shutil.which("soffice") or _shutil.which("libreoffice")
            if not soffice:
                raise RectificationError("LibreOffice is required for live DOCX page preview on this machine.")
            outdir = self.session_dir / "preview"
            outdir.mkdir(exist_ok=True)
            subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(outdir), str(working)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
            pdf = outdir / f"{working.stem}.pdf"
            if not pdf.exists():
                raise RectificationError("DOCX preview conversion failed.")
            return pdf
        raise RectificationError("Preview is unsupported for this file type.")

    def change_report(self) -> Dict[str, Any]:
        state = self._read_state()
        changes = state.get("changes", [])
        return {
            "session_id": self.session_id,
            "document": state["source_filename"],
            "working_document": Path(state["working_path"]).name,
            "revision": state["revision"],
            "updated_at": state["updated_at"],
            "changes": changes,
            "change_count": len(changes),
            "can_undo": len(changes) > 0,
            "can_redo": len(state.get("undone_changes", [])) > 0,
        }
