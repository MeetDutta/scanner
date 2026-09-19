"""
DOCX Structural Extractor and Pagination Handler.

Extracts logical structure, styles, headings, tables, and section/page breaks from DOCX files.
Checks for local headless LibreOffice (soffice) to perform pixel-verified pagination.
If headless LibreOffice is not available, uses structural logical pagination and explicitly
reports pagination uncertainty without inventing fake page counts.
"""

import os
import shutil
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

import docx
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn

from specguard.core.models import (
    PageModel, TextBlock, TableData, FigureData, BBox, DocumentModel,
    WordModel, LineModel, SectionNode
)

logger = logging.getLogger(__name__)


def find_libreoffice_executable() -> Optional[str]:
    """
    Detects whether LibreOffice / soffice is available locally in PATH
    or standard installation directories across macOS, Windows, and Linux.
    Strictly offline check.
    """
    # Check PATH first
    for cmd in ["soffice", "libreoffice"]:
        found = shutil.which(cmd)
        if found:
            return found

    # macOS standard application paths
    mac_paths = [
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        Path.home() / "Applications/LibreOffice.app/Contents/MacOS/soffice",
    ]
    for p in mac_paths:
        if os.path.exists(p) and os.access(p, os.X_OK):
            return str(p)

    # Windows standard paths
    win_paths = [
        os.path.expandvars(r"%ProgramFiles%\LibreOffice\program\soffice.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\LibreOffice\program\soffice.exe"),
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    for p in win_paths:
        if os.path.exists(p):
            return str(p)

    # Linux standard paths
    linux_paths = [
        "/usr/bin/libreoffice",
        "/usr/bin/soffice",
        "/usr/local/bin/soffice",
    ]
    for p in linux_paths:
        if os.path.exists(p) and os.access(p, os.X_OK):
            return str(p)

    return None


class DocxExtractor:
    """
    Extracts structural elements and page partitions from DOCX documents.
    """

    @classmethod
    def extract(
        cls,
        file_path: Path,
        file_hash: str,
        file_size: int,
        attempt_pdf_render: bool = True
    ) -> DocumentModel:
        """
        Extracts multi-page DocumentModel from DOCX.
        If headless LibreOffice is available, renders reference PDF for verified coordinates.
        Otherwise, performs structural multi-page extraction and marks pagination_verified=False.
        """
        soffice_bin = find_libreoffice_executable() if attempt_pdf_render else None

        if soffice_bin:
            try:
                doc_model = cls._render_and_extract_via_pdf(file_path, file_hash, file_size, soffice_bin)
                if doc_model:
                    return doc_model
            except Exception as e:
                logger.warning("LibreOffice DOCX conversion failed, falling back to structural extraction: %s", e)

        # Fallback to direct structural extraction
        return cls._extract_structural(file_path, file_hash, file_size, soffice_available=bool(soffice_bin))

    @classmethod
    def _render_and_extract_via_pdf(
        cls,
        file_path: Path,
        file_hash: str,
        file_size: int,
        soffice_bin: str
    ) -> Optional[DocumentModel]:
        """
        Converts DOCX to temporary PDF via headless LibreOffice and parses it with PyMuPDF.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            cmd = [
                soffice_bin,
                "--headless",
                "--convert-to", "pdf",
                "--outdir", tmp_dir,
                str(file_path)
            ]
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=45,
                check=False
            )
            if proc.returncode != 0:
                logger.debug("soffice returned %d: %s", proc.returncode, proc.stderr.decode("utf-8", errors="replace"))
                return None

            pdf_candidate = Path(tmp_dir) / f"{file_path.stem}.pdf"
            if not pdf_candidate.exists():
                return None

            # Parse with PyMuPDF
            from specguard.core.document_parser import DocumentParser
            doc_model = DocumentParser._parse_pdf(pdf_candidate, file_hash, file_size)
            doc_model.file_path = str(file_path)
            doc_model.file_type = "DOCX"
            doc_model.metadata["parser"] = "DOCX-HeadlessLibreOffice-Verified"
            doc_model.metadata["pagination_verified"] = True
            return doc_model

    @classmethod
    def _extract_structural(
        cls,
        file_path: Path,
        file_hash: str,
        file_size: int,
        soffice_available: bool
    ) -> DocumentModel:
        """
        Extracts paragraphs, runs, headings, tables, page breaks, and section breaks directly
        from the DOCX OpenXML structure, partitioning into logical pages.
        """
        doc = docx.Document(str(file_path))

        warnings: List[str] = []
        if not soffice_available:
            warnings.append(
                "Not evaluated: exact DOCX pagination unavailable because no local rendering engine "
                "(LibreOffice) was detected. Document analyzed using structural logical pagination."
            )

        pages: List[PageModel] = []
        current_page_blocks: List[TextBlock] = []
        current_page_tables: List[TableData] = []
        current_page_figures: List[FigureData] = []
        current_page_text: List[str] = []
        sections_list: List[SectionNode] = []

        page_num = 1
        y_cursor = 54.0
        block_id = 0
        section_counter = 0

        # Page dimension defaults (standard Letter)
        page_width = 612.0
        page_height = 792.0
        top_margin = 54.0
        bottom_margin = 738.0
        left_margin = 54.0
        right_margin = 558.0

        # Check section margins if available
        if doc.sections:
            sec = doc.sections[0]
            try:
                page_width = float(sec.page_width.pt)
                page_height = float(sec.page_height.pt)
                top_margin = float(sec.top_margin.pt)
                bottom_margin = page_height - float(sec.bottom_margin.pt)
                left_margin = float(sec.left_margin.pt)
                right_margin = page_width - float(sec.right_margin.pt)
                y_cursor = top_margin
            except Exception:
                pass

        def flush_page():
            nonlocal page_num, current_page_blocks, current_page_tables, current_page_figures, current_page_text, y_cursor
            pages.append(PageModel(
                page_num=page_num,
                width=page_width,
                height=page_height,
                blocks=current_page_blocks,
                tables=current_page_tables,
                figures=current_page_figures,
                text="\n".join(current_page_text),
                layout_type="single_column"
            ))
            page_num += 1
            current_page_blocks = []
            current_page_tables = []
            current_page_figures = []
            current_page_text = []
            y_cursor = top_margin

        # Iterate over body elements (paragraphs and tables in document order)
        body_elements = []
        for child in doc.element.body:
            tag = child.tag
            if tag.endswith("p"):
                body_elements.append(("p", child))
            elif tag.endswith("tbl"):
                body_elements.append(("tbl", child))

        # Map XML element to python-docx objects
        p_map = {p._element: p for p in doc.paragraphs}
        t_map = {t._element: t for t in doc.tables}

        for elem_type, xml_elem in body_elements:
            if elem_type == "p":
                p = p_map.get(xml_elem)
                if not p:
                    continue

                # Check for explicit page break in runs or paragraph properties
                has_page_break = False
                for r in p.runs:
                    # Check for w:br type="page" or lastRenderedPageBreak
                    r_xml = r._element.xml
                    if 'w:type="page"' in r_xml or 'lastRenderedPageBreak' in r_xml:
                        has_page_break = True
                        break

                # Also check paragraph-level pageBreakBefore
                if p.paragraph_format.page_break_before:
                    has_page_break = True

                if has_page_break and (current_page_blocks or current_page_tables):
                    flush_page()

                text = p.text.strip()
                if not text:
                    y_cursor += 12.0
                    continue

                # Typography detection
                font_size = 11.0
                is_bold = False
                is_italic = False
                font_name = "Calibri"

                style_name = p.style.name if p.style else ""
                is_heading = style_name.startswith("Heading") or style_name.lower().startswith("title")
                if is_heading:
                    is_bold = True
                    if "1" in style_name:
                        font_size = 14.0
                    elif "2" in style_name:
                        font_size = 12.5
                    elif "3" in style_name:
                        font_size = 11.5
                    else:
                        font_size = 12.0

                for r in p.runs:
                    if r.bold:
                        is_bold = True
                    if r.italic:
                        is_italic = True
                    if r.font.size:
                        font_size = r.font.size.pt
                    if r.font.name:
                        font_name = r.font.name

                line_height = font_size * 1.3
                # Approximate number of wrapped lines
                chars_per_line = max(40, int((right_margin - left_margin) / (font_size * 0.5)))
                num_lines = max(1, len(text) // chars_per_line + (1 if len(text) % chars_per_line else 0))
                block_height = line_height * num_lines

                # Check if block exceeds available page height (logical overflow)
                if y_cursor + block_height > bottom_margin and (current_page_blocks or current_page_tables):
                    flush_page()

                block_bbox = BBox(
                    x0=left_margin,
                    y0=y_cursor,
                    x1=right_margin,
                    y1=y_cursor + block_height
                )

                # Build word models
                words = []
                w_offset = left_margin
                for w in text.split():
                    w_len = len(w) * (font_size * 0.5)
                    words.append(WordModel(
                        text=w,
                        bbox=BBox(x0=w_offset, y0=y_cursor, x1=w_offset + w_len, y1=y_cursor + line_height),
                        font_name=font_name,
                        font_size=round(font_size, 1),
                        is_bold=is_bold,
                        is_italic=is_italic
                    ))
                    w_offset += w_len + 4.0

                tb = TextBlock(
                    text=text,
                    bbox=block_bbox,
                    font_name=font_name,
                    font_size=round(font_size, 1),
                    is_bold=is_bold,
                    is_italic=is_italic,
                    line_spacing=1.15,
                    block_id=block_id,
                    words=words
                )
                current_page_blocks.append(tb)
                current_page_text.append(text)
                block_id += 1

                # Track headings into sections
                if is_heading:
                    section_counter += 1
                    level = 1
                    for digit in ["1", "2", "3", "4"]:
                        if digit in style_name:
                            level = int(digit)
                            break
                    sections_list.append(SectionNode(
                        section_id=f"sec_{section_counter}",
                        title=text,
                        level=level,
                        page_num=page_num,
                        bbox=block_bbox
                    ))

                # Check for inline drawings/images inside paragraph runs
                if "w:drawing" in xml_elem.xml or "w:pict" in xml_elem.xml:
                    current_page_figures.append(FigureData(
                        bbox=BBox(x0=left_margin, y0=y_cursor, x1=right_margin, y1=y_cursor + 120.0),
                        page_num=page_num,
                        figure_type="raster",
                        figure_id=f"fig_{len(current_page_figures) + 1}",
                        caption="",
                        confidence=0.85
                    ))
                    y_cursor += 125.0

                y_cursor += block_height + 6.0

            elif elem_type == "tbl":
                t = t_map.get(xml_elem)
                if not t:
                    continue

                tab_rows: List[List[str]] = []
                for row in t.rows:
                    tab_rows.append([cell.text.strip() for cell in row.cells])

                if tab_rows:
                    headers = tab_rows[0]
                    rows = tab_rows[1:] if len(tab_rows) > 1 else []
                    est_tbl_height = min(280.0, max(50.0, len(tab_rows) * 22.0))

                    if y_cursor + est_tbl_height > bottom_margin and (current_page_blocks or current_page_tables):
                        flush_page()

                    tbl_bbox = BBox(x0=left_margin, y0=y_cursor, x1=right_margin, y1=y_cursor + est_tbl_height)
                    current_page_tables.append(TableData(
                        rows=rows,
                        headers=headers,
                        bbox=tbl_bbox,
                        page_num=page_num,
                        table_id=f"tbl_{len(current_page_tables) + 1}"
                    ))
                    y_cursor += est_tbl_height + 15.0

        # Flush final page
        if current_page_blocks or current_page_tables or not pages:
            flush_page()

        # Build DocumentModel
        return DocumentModel(
            file_path=str(file_path),
            file_type="DOCX",
            file_hash=file_hash,
            file_size=file_size,
            page_count=len(pages),
            pages=pages,
            sections=sections_list,
            warnings=warnings,
            metadata={
                "parser": "python-docx-structural",
                "pagination_verified": False,
                "renderer_available": soffice_available,
                "sections_extracted": len(sections_list)
            }
        )
