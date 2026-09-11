"""
Interactive Document Page Viewer Widget for SpecGuard.
Renders high-DPI document pages via PyMuPDF with real bounding-box severity overlays,
zoom controls, page navigation, and click-to-jump targeting.
"""

from typing import List, Optional, Tuple
from pathlib import Path
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QSpinBox, QSlider, QFrame
)
from PySide6.QtCore import Qt, QRectF, Signal, QPoint
from PySide6.QtGui import QPainter, QPixmap, QImage, QColor, QPen, QBrush
import pymupdf

from specguard.core.models import Finding, BBox, DocumentModel

logger = logging.getLogger(__name__)

SEVERITY_COLORS = {
    "Critical": QColor(185, 28, 28, 110),
    "High": QColor(194, 65, 12, 110),
    "Medium": QColor(180, 83, 9, 100),
    "Low": QColor(30, 64, 175, 90),
    "Informational": QColor(71, 85, 105, 80)
}

BORDER_COLORS = {
    "Critical": QColor(185, 28, 28, 255),
    "High": QColor(194, 65, 12, 255),
    "Medium": QColor(180, 83, 9, 255),
    "Low": QColor(30, 64, 175, 255),
    "Informational": QColor(71, 85, 105, 240)
}



class PageCanvas(QWidget):
    """Draws the rendered page pixmap and overlays bounding-box findings."""
    finding_clicked = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap: Optional[QPixmap] = None
        self.findings: List[Finding] = []
        self.scale_factor: float = 1.0
        self.page_width: float = 612.0
        self.page_height: float = 792.0
        self.focused_bbox: Optional[BBox] = None
        self.setMouseTracking(True)

    def set_page_data(self, pixmap: QPixmap, findings: List[Finding], page_w: float, page_h: float, scale: float):
        self.pixmap = pixmap
        self.findings = findings
        self.page_width = page_w
        self.page_height = page_h
        self.scale_factor = scale
        self.setFixedSize(int(pixmap.width()), int(pixmap.height()))
        self.update()

    def set_focused_bbox(self, bbox: Optional[BBox]):
        self.focused_bbox = bbox
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw page image background
        if self.pixmap:
            painter.drawPixmap(0, 0, self.pixmap)

        if not self.pixmap or self.page_width <= 0:
            return

        # Ratio between canvas size and native PDF points
        rx = self.pixmap.width() / self.page_width
        ry = self.pixmap.height() / self.page_height

        # Draw highlights for findings on this page
        for f in self.findings:
            if not f.bbox:
                continue

            rect = QRectF(
                f.bbox.x0 * rx,
                f.bbox.y0 * ry,
                f.bbox.width * rx,
                f.bbox.height * ry
            )

            fill_col = SEVERITY_COLORS.get(f.severity, QColor(100, 116, 139, 80))
            border_col = BORDER_COLORS.get(f.severity, QColor(100, 116, 139, 200))

            painter.setBrush(QBrush(fill_col))
            painter.setPen(QPen(border_col, 2.0, Qt.SolidLine))
            painter.drawRoundedRect(rect, 3, 3)

        # Draw focused highlight with pulsing thicker border if active
        if self.focused_bbox:
            f_rect = QRectF(
                self.focused_bbox.x0 * rx - 3,
                self.focused_bbox.y0 * ry - 3,
                self.focused_bbox.width * rx + 6,
                self.focused_bbox.height * ry + 6
            )
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(56, 189, 248, 255), 3.5, Qt.SolidLine))
            painter.drawRoundedRect(f_rect, 5, 5)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.position() if hasattr(event, "position") else event.pos()
            x = pos.x()
            y = pos.y()
            if self.pixmap and self.page_width > 0 and self.page_height > 0:
                rx = self.pixmap.width() / self.page_width
                ry = self.pixmap.height() / self.page_height
                for f in self.findings:
                    if not f.bbox:
                        continue
                    bx0 = f.bbox.x0 * rx - 4
                    by0 = f.bbox.y0 * ry - 4
                    bx1 = f.bbox.x1 * rx + 4
                    by1 = f.bbox.y1 * ry + 4
                    if bx0 <= x <= bx1 and by0 <= y <= by1:
                        self.focused_bbox = f.bbox
                        self.update()
                        self.finding_clicked.emit(f)
                        return
        super().mousePressEvent(event)


class DocumentViewerWidget(QWidget):
    """Complete document viewer component with zoom, paging, and jump-to-highlight."""
    finding_selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.doc: Optional[DocumentModel] = None
        self.pdf_doc: Optional[pymupdf.Document] = None
        self.current_page: int = 1
        self.total_pages: int = 1
        self.zoom_level: float = 1.25
        self.all_findings: List[Finding] = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Toolbar
        toolbar = QFrame()
        toolbar.setStyleSheet("background-color: #ffffff; border-bottom: 1px solid #cbd5e1; padding: 4px 8px;")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(4, 4, 4, 4)

        self.prev_btn = QPushButton("← Previous")
        self.prev_btn.setProperty("class", "gov_btn_secondary")
        self.prev_btn.clicked.connect(self._prev_page)
        tb_layout.addWidget(self.prev_btn)

        self.page_lbl = QLabel("Page 1 of 1")
        self.page_lbl.setStyleSheet("color: #002b49; font-weight: 700; padding: 0 8px;")
        tb_layout.addWidget(self.page_lbl)

        self.next_btn = QPushButton("Next →")
        self.next_btn.setProperty("class", "gov_btn_secondary")
        self.next_btn.clicked.connect(self._next_page)
        tb_layout.addWidget(self.next_btn)

        tb_layout.addStretch()

        self.zoom_out_btn = QPushButton("−")
        self.zoom_out_btn.setProperty("class", "gov_btn_secondary")
        self.zoom_out_btn.setFixedWidth(32)
        self.zoom_out_btn.clicked.connect(self._zoom_out)
        tb_layout.addWidget(self.zoom_out_btn)

        self.zoom_lbl = QLabel("125%")
        self.zoom_lbl.setStyleSheet("color: #475569; font-size: 12px; font-weight: 700;")
        tb_layout.addWidget(self.zoom_lbl)

        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setProperty("class", "gov_btn_secondary")
        self.zoom_in_btn.setFixedWidth(32)
        self.zoom_in_btn.clicked.connect(self._zoom_in)
        tb_layout.addWidget(self.zoom_in_btn)

        self.fit_width_btn = QPushButton("Fit Width")
        self.fit_width_btn.setProperty("class", "gov_btn_secondary")
        self.fit_width_btn.clicked.connect(self.fit_to_width)
        tb_layout.addWidget(self.fit_width_btn)

        self.fit_page_btn = QPushButton("Fit Page")
        self.fit_page_btn.setProperty("class", "gov_btn_secondary")
        self.fit_page_btn.clicked.connect(self.fit_to_page)
        tb_layout.addWidget(self.fit_page_btn)

        layout.addWidget(toolbar)

        # Scroll area with canvas
        self.scroll_area = QScrollArea()
        self.scroll_area.setStyleSheet("background-color: #e2e8f0; border: 1px solid #cbd5e1;")
        self.scroll_area.setAlignment(Qt.AlignCenter)

        self.canvas = PageCanvas()
        self.canvas.finding_clicked.connect(self.finding_selected.emit)
        self.scroll_area.setWidget(self.canvas)
        layout.addWidget(self.scroll_area)

    def fit_to_width(self):
        viewport_w = self.scroll_area.viewport().width()
        page_w = self.doc.pages[self.current_page - 1].width if self.doc and self.current_page <= len(self.doc.pages) else 612.0
        if viewport_w > 50 and page_w > 0:
            self.zoom_level = max(0.4, min(3.0, (viewport_w - 40) / page_w))
            self._render_current_page()

    def fit_to_page(self):
        viewport_h = self.scroll_area.viewport().height()
        page_h = self.doc.pages[self.current_page - 1].height if self.doc and self.current_page <= len(self.doc.pages) else 792.0
        if viewport_h > 50 and page_h > 0:
            self.zoom_level = max(0.4, min(3.0, (viewport_h - 40) / page_h))
            self._render_current_page()

    def load_document(self, doc: DocumentModel, findings: List[Finding]):
        self.doc = doc
        self.all_findings = findings
        self.total_pages = max(1, doc.page_count)
        self.current_page = 1

        # Open PDF if file is PDF
        if Path(doc.file_path).suffix.lower() == ".pdf":
            try:
                self.pdf_doc = pymupdf.open(doc.file_path)
            except Exception as e:
                logger.error("Failed opening PDF with PyMuPDF: %s", e)
                self.pdf_doc = None
        else:
            self.pdf_doc = None

        self._render_current_page()

    def jump_to_finding(self, finding: Finding):
        """Switches page and centers on the finding's bounding box."""
        self.current_page = finding.page
        self._render_current_page()
        if finding.bbox:
            self.canvas.set_focused_bbox(finding.bbox)
            # Center scroll view on the finding
            page_h = self.doc.pages[self.current_page - 1].height if self.doc and self.current_page <= len(self.doc.pages) else 792.0
            rx = self.canvas.width() / 612.0
            ry = self.canvas.height() / page_h
            target_y = int(finding.bbox.y0 * ry)
            self.scroll_area.verticalScrollBar().setValue(max(0, target_y - 120))
        else:
            self.canvas.set_focused_bbox(None)

    def _render_current_page(self):
        self.page_lbl.setText(f"Page {self.current_page} of {self.total_pages}")
        self.zoom_lbl.setText(f"{int(self.zoom_level * 100)}%")

        findings_on_page = [f for f in self.all_findings if f.page == self.current_page]

        page_w = 612.0
        page_h = 792.0
        if self.doc and self.current_page <= len(self.doc.pages):
            page_model = self.doc.pages[self.current_page - 1]
            page_w = page_model.width
            page_h = page_model.height

        if self.pdf_doc and 0 <= (self.current_page - 1) < len(self.pdf_doc):
            fitz_page = self.pdf_doc[self.current_page - 1]
            zoom_matrix = pymupdf.Matrix(self.zoom_level, self.zoom_level)
            pix = fitz_page.get_pixmap(matrix=zoom_matrix)
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            qpix = QPixmap.fromImage(img)
            self.canvas.set_page_data(qpix, findings_on_page, page_w, page_h, self.zoom_level)
        else:
            # Synthetic canvas for text / docx / non-pdf files
            cw = int(page_w * self.zoom_level)
            ch = int(page_h * self.zoom_level)
            pix = QPixmap(cw, ch)
            pix.fill(QColor("#1e293b"))
            p = QPainter(pix)
            p.setPen(QPen(QColor("#94a3b8"), 1))
            p.drawRect(0, 0, cw - 1, ch - 1)
            p.setPen(QColor("#f8fafc"))
            p.drawText(20, 40, f"Document: {Path(self.doc.file_path).name if self.doc else 'Page'}")
            p.drawText(20, 70, f"Page {self.current_page} (Text Document View)")
            if self.doc and self.current_page <= len(self.doc.pages):
                lines = self.doc.pages[self.current_page - 1].text.split("\n")[:35]
                for idx, line in enumerate(lines):
                    p.drawText(20, 100 + idx * 18, line[:80])
            p.end()
            self.canvas.set_page_data(pix, findings_on_page, page_w, page_h, self.zoom_level)

    def _prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.canvas.set_focused_bbox(None)
            self._render_current_page()

    def _next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.canvas.set_focused_bbox(None)
            self._render_current_page()

    def _zoom_in(self):
        if self.zoom_level < 3.0:
            self.zoom_level += 0.25
            self._render_current_page()

    def _zoom_out(self):
        if self.zoom_level > 0.5:
            self.zoom_level -= 0.25
            self._render_current_page()
