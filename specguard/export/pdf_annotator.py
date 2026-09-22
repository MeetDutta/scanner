"""
Native PDF Annotation Engine for SpecGuard.
Embeds color-coded vector highlight bounding boxes, translucent fills, 
search fallbacks, comment popups, and audit callouts into the PDF.
"""

import pymupdf
from pathlib import Path
from typing import List, Dict, Any, Union, Optional
import logging
import re

from specguard.core.models import Finding, SeverityLevel

logger = logging.getLogger(__name__)

SEVERITY_RGB = {
    SeverityLevel.CRITICAL.value: (0.86, 0.12, 0.12),    # Crimson Red
    SeverityLevel.HIGH.value: (0.92, 0.35, 0.05),        # High-visibility Orange
    SeverityLevel.MEDIUM.value: (0.90, 0.65, 0.04),      # Amber/Gold
    SeverityLevel.LOW.value: (0.20, 0.50, 0.92),         # Engineering Blue
    SeverityLevel.INFORMATIONAL.value: (0.42, 0.45, 0.50) # Slate Gray
}

SEVERITY_FILL_RGB = {
    SeverityLevel.CRITICAL.value: (1.0, 0.90, 0.90),
    SeverityLevel.HIGH.value: (1.0, 0.93, 0.86),
    SeverityLevel.MEDIUM.value: (1.0, 0.97, 0.84),
    SeverityLevel.LOW.value: (0.88, 0.93, 1.0),
    SeverityLevel.INFORMATIONAL.value: (0.93, 0.94, 0.95)
}


def _get_val(obj: Any, key: str, default: Any = None) -> Any:
    """Helper to access attributes on dataclasses, Pydantic models, or dicts."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class PDFAnnotator:
    """Generates an annotated PDF document with visual finding overlays."""

    @staticmethod
    def create_annotated_pdf(
        original_pdf_path: str,
        output_path: str,
        findings: List[Union[Finding, Dict[str, Any]]],
        include_header_stamp: bool = True
    ) -> str:
        doc = pymupdf.open(original_pdf_path)
        if len(doc) == 0:
            logger.warning("Empty PDF document provided: %s", original_pdf_path)
            doc.save(str(output_path))
            doc.close()
            return str(output_path)

        callouts_by_page: Dict[int, int] = {}
        annotated_count = 0

        for finding in findings:
            page_num = _get_val(finding, "page", 1)
            try:
                page_num = int(page_num)
            except (ValueError, TypeError):
                page_num = 1

            page_idx = max(0, page_num - 1)
            if page_idx >= len(doc):
                page_idx = min(page_idx, len(doc) - 1)

            page = doc[page_idx]

            # Normalize severity & colors
            sev_raw = str(_get_val(finding, "severity", "Medium")).strip()
            sev_key = sev_raw.title()
            if sev_key not in SEVERITY_RGB:
                sev_key = SeverityLevel.MEDIUM.value
            stroke_color = SEVERITY_RGB[sev_key]
            fill_color = SEVERITY_FILL_RGB.get(sev_key, (1.0, 0.95, 0.85))

            finding_id = str(_get_val(finding, "finding_id", "FINDING"))
            category = str(_get_val(finding, "category", "Compliance Deviation"))
            original_content = str(_get_val(finding, "original_content", "") or "").strip()
            detected_val = str(_get_val(finding, "detected_value", "") or "").strip()
            expected_val = str(_get_val(finding, "expected_value", "") or "").strip()
            deviation = str(_get_val(finding, "deviation", "") or "").strip()
            explanation = str(_get_val(finding, "explanation", "") or "").strip()
            suggested_corr = str(_get_val(finding, "suggested_correction", "") or "").strip()
            rule_ref = str(_get_val(finding, "rule_reference", "") or "").strip()

            annot_title = f"[{sev_key.upper()}] {finding_id}: {category}"
            annot_content = (
                f"Finding ID: {finding_id}\n"
                f"Severity: {sev_key}\n"
                f"Category: {category}\n"
                f"Deviation: {deviation or detected_val or 'Non-compliance detected'}\n"
                f"Expected: {expected_val or 'Compliant specification'}\n"
                f"Explanation: {explanation}\n"
                f"Suggested Correction: {suggested_corr}\n"
                f"Standard Reference: {rule_ref or 'Engineering Standard'}"
            )

            # 1. Coordinate check (bbox)
            rects_to_highlight: List[pymupdf.Rect] = []
            bbox = _get_val(finding, "bbox")
            if bbox:
                x0 = _get_val(bbox, "x0")
                y0 = _get_val(bbox, "y0")
                x1 = _get_val(bbox, "x1")
                y1 = _get_val(bbox, "y1")
                if (
                    x0 is not None and y0 is not None and x1 is not None and y1 is not None
                    and float(x1) > float(x0) and float(y1) > float(y0)
                ):
                    rects_to_highlight.append(pymupdf.Rect(float(x0), float(y0), float(x1), float(y1)))

            # 2. Dynamic text search fallback if no valid bbox
            if not rects_to_highlight:
                generic_terms = {
                    "parameter absent", "section absent", "missing", "absent",
                    "[document structure]", "n/a", "none", "section missing", "null"
                }

                candidates: List[str] = []
                if detected_val and detected_val.lower() not in generic_terms and len(detected_val) >= 3:
                    candidates.append(detected_val)
                if original_content and original_content.lower() not in generic_terms and len(original_content) >= 3:
                    # Clean up quotes or prefixes
                    cleaned_orig = re.sub(r"^(Page \d+:\s*|['\"])", "", original_content).strip()
                    candidates.append(cleaned_orig)

                for cand in candidates:
                    # Search exact candidate or first segment
                    search_str = cand[:60].strip()
                    found = page.search_for(search_str)
                    if not found and len(search_str) > 20:
                        # Try first significant words
                        words = search_str.split()[:4]
                        if words:
                            found = page.search_for(" ".join(words))
                    if found:
                        rects_to_highlight.extend(found[:3])
                        break

            # 3. If target rects were found, apply high-visibility annotations
            if rects_to_highlight:
                for r in rects_to_highlight:
                    # A. Native PDF Text Highlight (permanent translucent tint over text)
                    try:
                        hl = page.add_highlight_annot(r)
                        hl.set_colors(stroke=stroke_color)
                        hl.set_info(title=annot_title, content=annot_content)
                        hl.update()
                    except Exception as e:
                        logger.debug("Failed adding highlight annot: %s", e)

                    # B. Vector Bounding Box with semi-transparent fill
                    try:
                        box = page.add_rect_annot(r)
                        box.set_colors(stroke=stroke_color, fill=fill_color)
                        box.set_opacity(0.35)
                        box.set_border(
                            width=1.5,
                            dashes=[2, 2] if sev_key in ["Low", "Informational"] else None
                        )
                        box.set_info(title=annot_title, content=annot_content)
                        box.update()
                    except Exception as e:
                        logger.debug("Failed adding rect annot: %s", e)

                    # C. Interactive Sticky Note Pin adjacent to the highlight
                    try:
                        pin_x = min(page.rect.width - 24, max(4, r.x1 + 3))
                        pin_y = max(10, min(page.rect.height - 24, r.y0))
                        note = page.add_text_annot(pymupdf.Point(pin_x, pin_y), annot_content, icon="Comment")
                        note.set_colors(stroke=stroke_color)
                        note.set_info(title=annot_title, content=annot_content)
                        note.update()
                    except Exception as e:
                        logger.debug("Failed adding text annot: %s", e)

                annotated_count += 1

            else:
                # 4. Fallback: Structural / Page-level deviation (e.g. Missing parameter or section)
                # Create a prominent visual callout banner in the page margin
                c_idx = callouts_by_page.get(page_idx, 0)
                callouts_by_page[page_idx] = c_idx + 1

                card_h = 34
                margin_bottom = 26 + c_idx * (card_h + 6)
                card_y1 = page.rect.height - margin_bottom
                card_y0 = card_y1 - card_h

                if card_y0 < 40:
                    # Wrap to top margin if bottom is full
                    card_y0 = 36 + (c_idx % 6) * (card_h + 4)
                    card_y1 = card_y0 + card_h

                card_rect = pymupdf.Rect(36, card_y0, page.rect.width - 36, card_y1)

                try:
                    # Paint vector background badge
                    page.draw_rect(card_rect, color=stroke_color, fill=fill_color, width=1.2)
                    summary_line = f"⚠️ [{sev_key.upper()}] {finding_id}: {category} — {deviation or explanation or detected_val}"
                    if suggested_corr:
                        summary_line += f"\n👉 Suggested Correction: {suggested_corr}"

                    page.insert_textbox(
                        pymupdf.Rect(card_rect.x0 + 6, card_rect.y0 + 3, card_rect.x1 - 6, card_rect.y1 - 3),
                        summary_line,
                        fontsize=7.5,
                        color=(0.15, 0.15, 0.15),
                        align=0
                    )

                    # Interactive rect and sticky note annotation
                    box = page.add_rect_annot(card_rect)
                    box.set_colors(stroke=stroke_color)
                    box.set_info(title=annot_title, content=annot_content)
                    box.update()

                    note = page.add_text_annot(
                        pymupdf.Point(card_rect.x0 + 8, card_rect.y0 + 6),
                        annot_content,
                        icon="Help" if "missing" in category.lower() else "Comment"
                    )
                    note.set_colors(stroke=stroke_color)
                    note.set_info(title=annot_title, content=annot_content)
                    note.update()
                    annotated_count += 1
                except Exception as e:
                    logger.debug("Failed drawing callout banner: %s", e)

        # 5. Add certified top audit banner on Page 1
        if include_header_stamp and len(findings) > 0 and len(doc) > 0:
            try:
                p0 = doc[0]
                stamp_rect = pymupdf.Rect(36, 8, p0.rect.width - 36, 26)
                p0.draw_rect(stamp_rect, color=(0.85, 0.18, 0.18), fill=(1.0, 0.96, 0.96), width=1.0)

                crit_n = sum(1 for f in findings if str(_get_val(f, "severity", "")).upper() == "CRITICAL")
                high_n = sum(1 for f in findings if str(_get_val(f, "severity", "")).upper() == "HIGH")
                med_n = sum(1 for f in findings if str(_get_val(f, "severity", "")).upper() in ("MEDIUM", "MODERATE"))
                low_n = sum(1 for f in findings if str(_get_val(f, "severity", "")).upper() in ("LOW", "INFORMATIONAL"))

                stamp_text = (
                    f"🛡️ SpecGuard Certified Compliance Audit: {len(findings)} Findings Highlighted "
                    f"({crit_n} Critical, {high_n} High, {med_n} Med, {low_n} Low)"
                )
                p0.insert_textbox(stamp_rect, stamp_text, fontsize=8, color=(0.65, 0.08, 0.08), align=1)
            except Exception as e:
                logger.debug("Failed inserting header audit stamp: %s", e)

        output_file = Path(output_path).resolve()
        output_file.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_file))
        doc.close()
        logger.info("Saved annotated PDF to %s with %d findings annotated", output_file, annotated_count)
        return str(output_file)

