"""
Findings Management and Search API for SpecGuard.
Provides multi-criteria filtering, search, pagination, and detailed remediation guidance
strictly from the verified local SQLite findings repository.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional, List
import re
import json
import logging

from specguard.storage.database import DatabaseManager
from specguard.core.models import Finding, BBox
from specguard.repository.manager import RepositoryManager

logger = logging.getLogger("SpecGuard.API.Findings")
router = APIRouter(prefix="/findings", tags=["findings"])


def _enrich_finding_location_metadata(finding_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts structured location breakdown (section, paragraph, object_type, coordinates, multi-locations)
    from location and bounding box metadata with zero fabricated coordinates.
    """
    loc_str = str(finding_dict.get("location") or "")
    cat = str(finding_dict.get("category") or "")
    bbox = finding_dict.get("bbox")

    # Section extraction
    section = None
    sec_match = re.search(r"(?:Section|Sec\.?)\s*([0-9A-Z\.]+)", loc_str, re.IGNORECASE)
    if sec_match:
        section = sec_match.group(1).strip()
    elif "TOC" in cat or "TOC" in loc_str:
        section = "Table of Contents"
    elif "Abstract" in loc_str:
        section = "Abstract"
    finding_dict["section"] = section

    # Paragraph / Line / Block extraction
    paragraph = None
    para_match = re.search(r"(?:Paragraph|Para\.?|Block|Line)\s*([0-9]+)", loc_str, re.IGNORECASE)
    if para_match:
        paragraph = para_match.group(1).strip()
    finding_dict["paragraph"] = paragraph

    # Object Type extraction
    obj_type = None
    if "Table of Contents" in cat or "TOC" in cat or "TOC" in loc_str:
        obj_type = "TOC Entry"
    elif "Table" in cat or "Table" in loc_str:
        obj_type = "Table"
    elif "Figure" in cat or "Figure" in loc_str:
        obj_type = "Figure"
    elif "Equation" in cat or "Equation" in loc_str:
        obj_type = "Equation"
    elif "Heading" in loc_str or "Outline" in loc_str or "Structure" in cat:
        obj_type = "Heading"
    elif "Grammar" in cat or "Spelling" in cat or "Semantic" in cat:
        obj_type = "Text Span"
    elif "Cross-Reference" in cat:
        obj_type = "Cross Reference"
    elif "Formatting" in cat:
        obj_type = "Formatted Text Block"
    elif "Standards" in cat:
        obj_type = "Specification Text"
    elif "Logical" in cat:
        obj_type = "Specification Value"
    finding_dict["object_type"] = obj_type

    # Format region coordinates
    if bbox and isinstance(bbox, dict) and "x0" in bbox and "y0" in bbox and "x1" in bbox and "y1" in bbox:
        w = max(0.0, float(bbox["x1"]) - float(bbox["x0"]))
        h = max(0.0, float(bbox["y1"]) - float(bbox["y0"]))
        finding_dict["region_formatted"] = f"x={float(bbox['x0']):.1f}, y={float(bbox['y0']):.1f}, width={w:.1f}, height={h:.1f}"
    else:
        finding_dict["region_formatted"] = None

    # Multiple locations extraction (e.g. Page X vs Page Y, or cross-ref mentions)
    locations = []
    vs_pages = re.findall(r"Page\s*([0-9]+)", loc_str, re.IGNORECASE)
    if len(vs_pages) > 1:
        for idx, p in enumerate(vs_pages):
            locations.append({
                "label": f"Location {idx + 1} (Page {p})",
                "page": int(p),
                "type": "Occurrence"
            })
    elif finding_dict.get("page"):
        primary_p = finding_dict["page"]
        locations.append({
            "label": f"Primary Location (Page {primary_p})",
            "page": int(primary_p),
            "type": obj_type or "Defect"
        })

    finding_dict["locations"] = locations
    return finding_dict


@router.get("")
def list_findings(
    session_id: Optional[str] = Query(None),
    comparison_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    page: Optional[int] = Query(None),
    domain: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("priority_score"),
    sort_dir: str = Query("desc"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """Retrieves ranked findings with search and multi-criteria filtering."""
    db = DatabaseManager()
    target_id = comparison_id or session_id

    # If no session or comparison ID provided, get the latest comparison ID
    if not target_id:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT comparison_id FROM repo_comparisons ORDER BY rowid DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                target_id = row["comparison_id"]

    if not target_id:
        return {
            "findings": [],
            "total_count": 0,
            "session_id": None,
            "severity_summary": {}
        }

    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Check whether target_id is in repo_findings or findings
        cursor.execute("SELECT COUNT(*) FROM repo_findings WHERE comparison_id = ?", (target_id,))
        is_repo = (cursor.fetchone()[0] > 0)

        table_name = "repo_findings" if is_repo else "findings"
        id_col = "comparison_id" if is_repo else "session_id"

        where_clauses = [f"{id_col} = ?"]
        params: List[Any] = [target_id]

        if severity:
            where_clauses.append("LOWER(severity) = LOWER(?)")
            params.append(severity)
        if category:
            where_clauses.append("LOWER(category) = LOWER(?)")
            params.append(category)
        if page:
            where_clauses.append("page = ?")
            params.append(page)
        if domain:
            where_clauses.append("LOWER(domain) = LOWER(?)")
            params.append(domain)
        if search:
            s_param = f"%{search.lower()}%"
            where_clauses.append(
                "(LOWER(finding_id) LIKE ? OR LOWER(explanation) LIKE ? OR LOWER(detected_value) LIKE ? OR LOWER(location) LIKE ? OR LOWER(rule_reference) LIKE ?)"
            )
            params.extend([s_param, s_param, s_param, s_param, s_param])

        where_sql = " AND ".join(where_clauses)

        # Count total matching
        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {where_sql}", tuple(params))
        total_count = cursor.fetchone()[0]

        # Valid sort columns
        valid_sort_cols = {
            "priority_score": "priority_score",
            "severity": "priority_score",  # higher priority first
            "page": "page",
            "category": "category",
            "finding_id": "finding_id"
        }
        col = valid_sort_cols.get(sort_by, "priority_score")
        direction = "ASC" if sort_dir.lower() == "asc" else "DESC"

        # Fetch page of findings
        query = f"""
            SELECT * FROM {table_name}
            WHERE {where_sql}
            ORDER BY {col} {direction}, id ASC
            LIMIT ? OFFSET ?
        """
        cursor.execute(query, tuple(params + [limit, offset]))
        rows = cursor.fetchall()

        # Attempt to load rich disk snapshot if available
        disk_findings_map = {}
        try:
            repo = RepositoryManager(db=db)
            findings_json_file = repo.comps_dir / target_id / "findings.json"
            if findings_json_file.exists():
                with open(findings_json_file, "r", encoding="utf-8") as f_json:
                    disk_list = json.load(f_json)
                    for item in disk_list:
                        if isinstance(item, dict) and "finding_id" in item:
                            disk_findings_map[item["finding_id"]] = item
        except Exception as e:
            logger.debug("Could not read disk snapshot for %s: %s", target_id, e)

        findings = []
        for r in rows:
            bbox_dict = None
            if r["bbox_json"]:
                try:
                    bbox_dict = json.loads(r["bbox_json"])
                except Exception:
                    bbox_dict = None

            f_id = r["finding_id"]
            finding_dict = {
                "id": r["id"],
                "session_id": target_id,
                "finding_id": f_id,
                "category": r["category"],
                "domain": r["domain"],
                "location": r["location"] or "",
                "page": r["page"],
                "page_number": r["page"],
                "bbox": bbox_dict,
                "bounding_boxes": [bbox_dict] if bbox_dict else [],
                "original_content": r["original_content"] or "",
                "detected_value": r["detected_value"] or "",
                "expected_value": r["expected_value"] or "",
                "deviation": r["deviation"] or "",
                "severity": r["severity"],
                "confidence": r["confidence"],
                "explanation": r["explanation"] or "",
                "suggested_correction": r["suggested_correction"] or "",
                "suggested_fix": r["suggested_correction"] or "",
                "rule_reference": r["rule_reference"] or "",
                "rule_id": r["rule_reference"] or f_id,
                "priority_score": r["priority_score"],
                "evidence": "",
                "source_analyzer": "SpecGuard Inspection Engine",
                "issue_type": "",
                "matched_text": str(r["detected_value"] or r["original_content"] or ""),
                "expected_text": str(r["expected_value"] or ""),
                "location_precision": "BLOCK",
                "related_finding_ids": []
            }

            if disk_findings_map and f_id in disk_findings_map:
                disk_f = disk_findings_map[f_id]
                for k in [
                    "bounding_boxes", "location_precision", "issue_type", "message",
                    "suggested_fix", "matched_text", "expected_text", "evidence",
                    "source_analyzer", "rule_id", "related_finding_ids"
                ]:
                    if k in disk_f and disk_f[k] is not None:
                        finding_dict[k] = disk_f[k]

            findings.append(_enrich_finding_location_metadata(finding_dict))

        # Severity summary for current session
        cursor.execute(f"""
            SELECT severity, COUNT(*) as count 
            FROM {table_name} 
            WHERE {id_col} = ? 
            GROUP BY severity
        """, (target_id,))
        sev_counts = {row["severity"]: row["count"] for row in cursor.fetchall()}

        # Category summary for current session
        cursor.execute(f"""
            SELECT category, COUNT(*) as count 
            FROM {table_name} 
            WHERE {id_col} = ? 
            GROUP BY category
        """, (target_id,))
        cat_counts = {row["category"]: row["count"] for row in cursor.fetchall()}

    return {
        "session_id": target_id,
        "total_count": total_count,
        "offset": offset,
        "limit": limit,
        "findings": findings,
        "severity_summary": sev_counts,
        "category_summary": cat_counts
    }


@router.get("/{finding_id}")
def get_finding_detail(finding_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves full explanation, coordinate bounding box, and remediation for a finding."""
    db = DatabaseManager()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        params: List[Any] = [finding_id]
        sql = "SELECT * FROM repo_findings WHERE finding_id = ?"
        if session_id:
            sql += " AND comparison_id = ?"
            params.append(session_id)
        sql += " ORDER BY id DESC LIMIT 1"

        cursor.execute(sql, tuple(params))
        row = cursor.fetchone()

        if not row:
            # Fallback to findings table
            sql = "SELECT * FROM findings WHERE finding_id = ?"
            params = [finding_id]
            if session_id:
                sql += " AND session_id = ?"
                params.append(session_id)
            sql += " ORDER BY id DESC LIMIT 1"
            cursor.execute(sql, tuple(params))
            row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Finding {finding_id} not found.")

        bbox_dict = None
        if row["bbox_json"]:
            try:
                bbox_dict = json.loads(row["bbox_json"])
            except Exception:
                bbox_dict = None

        target_session = row["comparison_id"] if "comparison_id" in row.keys() else row["session_id"]
        res = {
            "finding_id": row["finding_id"],
            "session_id": target_session,
            "category": row["category"],
            "domain": row["domain"],
            "location": row["location"] or "",
            "page": row["page"],
            "page_number": row["page"],
            "bbox": bbox_dict,
            "bounding_boxes": [bbox_dict] if bbox_dict else [],
            "original_content": row["original_content"] or "",
            "detected_value": row["detected_value"] or "",
            "expected_value": row["expected_value"] or "",
            "deviation": row["deviation"] or "",
            "severity": row["severity"],
            "confidence": row["confidence"],
            "explanation": row["explanation"] or "",
            "suggested_correction": row["suggested_correction"] or "",
            "suggested_fix": row["suggested_correction"] or "",
            "rule_reference": row["rule_reference"] or "",
            "rule_id": row["rule_reference"] or row["finding_id"],
            "priority_score": row["priority_score"],
            "evidence": "",
            "source_analyzer": "SpecGuard Inspection Engine",
            "issue_type": "",
            "matched_text": str(row["detected_value"] or row["original_content"] or ""),
            "expected_text": str(row["expected_value"] or ""),
            "location_precision": "BLOCK",
            "related_finding_ids": []
        }

        # Try enriching from disk snapshot if present
        try:
            repo = RepositoryManager(db=db)
            findings_json_file = repo.comps_dir / target_session / "findings.json"
            if findings_json_file.exists():
                with open(findings_json_file, "r", encoding="utf-8") as f_json:
                    disk_list = json.load(f_json)
                    for item in disk_list:
                        if isinstance(item, dict) and item.get("finding_id") == finding_id:
                            for k in [
                                "bounding_boxes", "location_precision", "issue_type", "message",
                                "suggested_fix", "matched_text", "expected_text", "evidence",
                                "source_analyzer", "rule_id", "related_finding_ids"
                            ]:
                                if k in item and item[k] is not None:
                                    res[k] = item[k]
                            break
        except Exception:
            pass

        return _enrich_finding_location_metadata(res)
