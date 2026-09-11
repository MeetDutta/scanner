"""
Unified Multi-Format Document Ingestion Engine for SpecGuard.
Extracts normalized DocumentModel with high-fidelity coordinate, font, and table preservation.
Supports PDF, DOCX, XLSX, TXT, and Images (PNG, JPG, JPEG, TIFF).
"""

import os
import re
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Any
import logging

import pymupdf  # PyMuPDF
import cv2
import numpy as np

from specguard.core.models import (
    DocumentModel, PageModel, TextBlock, TableData, FigureData, BBox
)
from specguard.core.scanned_pipeline import ScannedDocumentPipeline
from specguard.core.cv_layout import LayoutAnalyzerCV

logger = logging.getLogger(__name__)


class DocumentParser:
    """Dispatches document parsing to specialized format handlers."""

    @staticmethod
    def parse_file(file_path: str) -> DocumentModel:
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")

        file_size = path.stat().st_size
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        file_hash = sha256.hexdigest()

        ext = path.suffix.lower()
        if ext == ".pdf":
            return DocumentParser._parse_pdf(path, file_hash, file_size)
        elif ext == ".docx":
            return DocumentParser._parse_docx(path, file_hash, file_size)
        elif ext in [".xlsx", ".xls"]:
            return DocumentParser._parse_xlsx(path, file_hash, file_size)
        elif ext == ".txt":
            return DocumentParser._parse_txt(path, file_hash, file_size)
        elif ext in [".png", ".jpg", ".jpeg", ".tiff", ".tif"]:
            return DocumentParser._parse_image(path, file_hash, file_size)
        else:
            raise ValueError(f"Unsupported document format: {ext}")

    @staticmethod
    def _parse_pdf(path: Path, file_hash: str, file_size: int) -> DocumentModel:
        doc = pymupdf.open(str(path))
        pages: List[PageModel] = []

        for page_idx, fitz_page in enumerate(doc):
            page_num = page_idx + 1
            rect = fitz_page.rect
            page_w = float(rect.width)
            page_h = float(rect.height)

            blocks: List[TextBlock] = []
            tables: List[TableData] = []
            page_text_pieces = []

            # Extract detailed text blocks with font and coordinate data
            page_dict = fitz_page.get_text("dict")
            block_id = 0
            for b in page_dict.get("blocks", []):
                if b.get("type") == 0:  # Text block
                    for line in b.get("lines", []):
                        line_text_parts = []
                        line_bbox = line.get("bbox", (0, 0, 0, 0))
                        font_name = "Helvetica"
                        font_size = 11.0
                        is_bold = False
                        is_italic = False

                        for span in line.get("spans", []):
                            span_text = span.get("text", "")
                            line_text_parts.append(span_text)
                            font_name = span.get("font", font_name)
                            font_size = float(span.get("size", font_size))
                            flags = span.get("flags", 0)
                            if flags & 2:
                                is_italic = True
                            if flags & 16 or "bold" in font_name.lower():
                                is_bold = True

                        full_line_text = "".join(line_text_parts).strip()
                        if full_line_text:
                            blocks.append(TextBlock(
                                text=full_line_text,
                                bbox=BBox(x0=line_bbox[0], y0=line_bbox[1], x1=line_bbox[2], y1=line_bbox[3]),
                                font_name=font_name,
                                font_size=round(font_size, 1),
                                is_bold=is_bold,
                                is_italic=is_italic,
                                block_id=block_id
                            ))
                            page_text_pieces.append(full_line_text)
                    block_id += 1

            # Extract native PDF tables if available via pymupdf
            try:
                tabs = fitz_page.find_tables()
                for tab in tabs:
                    tab_df = tab.extract()
                    if tab_df and len(tab_df) > 0:
                        headers = [str(c or "").strip() for c in tab_df[0]]
                        rows = [[str(c or "").strip() for c in row] for row in tab_df[1:]]
                        tab_rect = tab.bbox
                        tables.append(TableData(
                            rows=rows,
                            headers=headers,
                            bbox=BBox(x0=tab_rect[0], y0=tab_rect[1], x1=tab_rect[2], y1=tab_rect[3]),
                            page_num=page_num
                        ))
            except Exception as e:
                logger.debug("Native PDF table extraction fallback for page %d: %s", page_num, e)

            # Render page pixmap to OpenCV for computer vision layout validation
            figures: List[FigureData] = []
            try:
                pix = fitz_page.get_pixmap(dpi=150)
                img_data = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                if pix.n >= 3:
                    gray = cv2.cvtColor(img_data, cv2.COLOR_BGR2GRAY if pix.n == 3 else cv2.COLOR_RGBA2GRAY)
                    cv_tables_boxes, _ = LayoutAnalyzerCV.detect_lines_and_tables(gray, page_num)
                    # Scale factor between image dpi (150) and PDF points (72)
                    scale_x = page_w / pix.width
                    scale_y = page_h / pix.height
                    scaled_table_boxes = [
                        BBox(x0=b.x0 * scale_x, y0=b.y0 * scale_y, x1=b.x1 * scale_x, y1=b.y1 * scale_y)
                        for b in cv_tables_boxes
                    ]
                    cv_figures = LayoutAnalyzerCV.detect_figures_and_drawings(gray, cv_tables_boxes, page_num)
                    for fig in cv_figures:
                        figures.append(FigureData(
                            bbox=BBox(x0=fig.bbox.x0 * scale_x, y0=fig.bbox.y0 * scale_y,
                                      x1=fig.bbox.x1 * scale_x, y1=fig.bbox.y1 * scale_y),
                            page_num=page_num,
                            figure_type=fig.figure_type
                        ))
            except Exception as cv_err:
                logger.debug("OpenCV layout analysis on page %d skipped: %s", page_num, cv_err)

            pages.append(PageModel(
                page_num=page_num,
                width=page_w,
                height=page_h,
                blocks=blocks,
                tables=tables,
                figures=figures,
                text="\n".join(page_text_pieces)
            ))

        doc.close()
        return DocumentModel(
            file_path=str(path),
            file_type="PDF",
            file_hash=file_hash,
            file_size=file_size,
            page_count=len(pages),
            pages=pages,
            metadata={"parser": "PyMuPDF+OpenCV"}
        )

    @staticmethod
    def _parse_docx(path: Path, file_hash: str, file_size: int) -> DocumentModel:
        import docx
        doc = docx.Document(str(path))
        blocks: List[TextBlock] = []
        tables: List[TableData] = []
        full_text_pieces = []

        y_offset = 50.0  # Synthetic point coordinate calculation
        block_id = 0

        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                y_offset += 14.0
                continue

            # Typography detection from style and runs
            font_size = 11.0
            is_bold = False
            is_italic = False
            font_name = "Calibri"

            if p.style and p.style.name.startswith("Heading"):
                is_bold = True
                font_size = 14.0 if "1" in p.style.name else 12.5

            for r in p.runs:
                if r.bold:
                    is_bold = True
                if r.italic:
                    is_italic = True
                if r.font.size:
                    font_size = r.font.size.pt
                if r.font.name:
                    font_name = r.font.name

            h_est = font_size * 1.3
            bbox = BBox(x0=54.0, y0=y_offset, x1=558.0, y1=y_offset + h_est)
            blocks.append(TextBlock(
                text=text,
                bbox=bbox,
                font_name=font_name,
                font_size=round(font_size, 1),
                is_bold=is_bold,
                is_italic=is_italic,
                block_id=block_id
            ))
            full_text_pieces.append(text)
            y_offset += h_est + 6.0
            block_id += 1

        # Extract docx tables
        for t in doc.tables:
            tab_rows = []
            for row in t.rows:
                tab_rows.append([c.text.strip() for c in row.cells])
            if tab_rows:
                headers = tab_rows[0]
                rows = tab_rows[1:] if len(tab_rows) > 1 else []
                tables.append(TableData(
                    rows=rows,
                    headers=headers,
                    bbox=BBox(x0=54.0, y0=y_offset, x1=558.0, y1=y_offset + 100.0),
                    page_num=1
                ))
                y_offset += 110.0

        # Wrap in page model
        page = PageModel(
            page_num=1,
            width=612.0,
            height=max(792.0, y_offset + 50.0),
            blocks=blocks,
            tables=tables,
            figures=[],
            text="\n".join(full_text_pieces)
        )

        return DocumentModel(
            file_path=str(path),
            file_type="DOCX",
            file_hash=file_hash,
            file_size=file_size,
            page_count=1,
            pages=[page],
            metadata={"parser": "python-docx"}
        )

    @staticmethod
    def _parse_xlsx(path: Path, file_hash: str, file_size: int) -> DocumentModel:
        import openpyxl
        wb = openpyxl.load_workbook(str(path), data_only=True)
        pages: List[PageModel] = []

        for sheet_idx, sheet_name in enumerate(wb.sheetnames):
            ws = wb[sheet_name]
            all_rows = []
            for row in ws.iter_rows(values_only=True):
                # Convert None to ""
                all_rows.append([str(cell or "").strip() for cell in row])

            headers = all_rows[0] if all_rows else []
            data_rows = all_rows[1:] if len(all_rows) > 1 else []

            table = TableData(
                rows=data_rows,
                headers=headers,
                bbox=BBox(x0=50.0, y0=50.0, x1=740.0, y1=550.0),
                page_num=sheet_idx + 1,
                caption=f"Sheet: {sheet_name}"
            )

            # Build text representation
            text_lines = [f"=== Sheet: {sheet_name} ===", " | ".join(headers)]
            for r in data_rows[:100]:
                text_lines.append(" | ".join(r))

            blocks = [
                TextBlock(
                    text=line,
                    bbox=BBox(x0=50.0, y0=50.0 + idx * 16.0, x1=740.0, y1=64.0 + idx * 16.0),
                    font_name="Calibri",
                    font_size=10.0,
                    block_id=idx
                )
                for idx, line in enumerate(text_lines)
            ]

            pages.append(PageModel(
                page_num=sheet_idx + 1,
                width=792.0,
                height=612.0,
                blocks=blocks,
                tables=[table],
                text="\n".join(text_lines)
            ))

        wb.close()
        return DocumentModel(
            file_path=str(path),
            file_type="XLSX",
            file_hash=file_hash,
            file_size=file_size,
            page_count=len(pages),
            pages=pages,
            metadata={"parser": "openpyxl"}
        )

    @staticmethod
    def _parse_txt(path: Path, file_hash: str, file_size: int) -> DocumentModel:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = [l.rstrip("\r\n") for l in f.readlines()]

        blocks = []
        page_lines = []
        pages = []
        page_num = 1
        y_pos = 50.0

        for idx, line in enumerate(lines):
            if idx > 0 and idx % 45 == 0:
                pages.append(PageModel(
                    page_num=page_num,
                    width=612.0,
                    height=792.0,
                    blocks=blocks,
                    tables=[],
                    text="\n".join(page_lines)
                ))
                page_num += 1
                blocks = []
                page_lines = []
                y_pos = 50.0

            if line.strip():
                blocks.append(TextBlock(
                    text=line,
                    bbox=BBox(x0=54.0, y0=y_pos, x1=558.0, y1=y_pos + 14.0),
                    font_name="Courier",
                    font_size=10.0,
                    block_id=idx
                ))
            page_lines.append(line)
            y_pos += 15.0

        if page_lines or not pages:
            pages.append(PageModel(
                page_num=page_num,
                width=612.0,
                height=792.0,
                blocks=blocks,
                tables=[],
                text="\n".join(page_lines)
            ))

        return DocumentModel(
            file_path=str(path),
            file_type="TXT",
            file_hash=file_hash,
            file_size=file_size,
            page_count=len(pages),
            pages=pages,
            metadata={"parser": "plain_text"}
        )

    @staticmethod
    def _parse_image(path: Path, file_hash: str, file_size: int) -> DocumentModel:
        image = cv2.imread(str(path))
        if image is None:
            raise ValueError(f"Could not load image at {path}")

        h, w = image.shape[:2]
        # Preprocess, deskew, and binarize
        enhanced = ScannedDocumentPipeline.preprocess_image(image)
        deskewed, angle = ScannedDocumentPipeline.deskew_image(enhanced)
        binary = ScannedDocumentPipeline.binarize(deskewed)

        # Extract text regions
        text_boxes = ScannedDocumentPipeline.extract_text_regions(binary)
        table_boxes, tables = LayoutAnalyzerCV.detect_lines_and_tables(deskewed, page_num=1)
        figures = LayoutAnalyzerCV.detect_figures_and_drawings(deskewed, table_boxes, page_num=1)

        # Create blocks from text regions
        blocks = [
            TextBlock(
                text=f"[Image Text Region {idx+1}]",
                bbox=bbox,
                font_name="OCR-Detected",
                font_size=11.0,
                block_id=idx
            )
            for idx, bbox in enumerate(text_boxes)
        ]

        page = PageModel(
            page_num=1,
            width=float(w),
            height=float(h),
            blocks=blocks,
            tables=tables,
            figures=figures,
            text=f"[Scanned Image Document: {path.name} | Deskew: {angle:.1f}° | Regions: {len(text_boxes)}]"
        )

        return DocumentModel(
            file_path=str(path),
            file_type="IMAGE",
            file_hash=file_hash,
            file_size=file_size,
            page_count=1,
            pages=[page],
            metadata={"parser": "OpenCV-Scanned", "deskew_angle": angle}
        )
