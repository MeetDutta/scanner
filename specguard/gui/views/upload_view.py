"""
Upload Document View for SpecGuard.
Screen 1 in the 3-stage minimal workflow:
Drag & drop ingestion, local file browsing, compact document card, and navigation to Comparison Mode.
"""

from pathlib import Path
import os
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".txt", ".png", ".jpg", ".jpeg", ".tiff"}


def format_file_size(num_bytes: int) -> str:
    """Format bytes to human readable string (KB, MB)."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    else:
        return f"{num_bytes / (1024 * 1024):.1f} MB"


class DropZoneWidget(QFrame):
    """Interactive drag-and-drop file target."""
    file_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("drop_zone")
        self.setAcceptDrops(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(40, 48, 40, 48)
        layout.setSpacing(14)

        icon_lbl = QLabel("📄")
        icon_lbl.setStyleSheet("font-size: 52px; margin-bottom: 4px;")
        icon_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_lbl)

        primary_lbl = QLabel("Upload your engineering document")
        primary_lbl.setStyleSheet("color: #f8fafc; font-size: 18px; font-weight: 700;")
        primary_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(primary_lbl)

        sec_lbl = QLabel("Drag & drop your file here or browse from your computer")
        sec_lbl.setStyleSheet("color: #94a3b8; font-size: 13px;")
        sec_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(sec_lbl)

        self.browse_btn = QPushButton("Browse Files")
        self.browse_btn.setProperty("class", "primary")
        self.browse_btn.setStyleSheet("font-size: 13px; font-weight: 600; padding: 10px 24px; border-radius: 6px;")
        self.browse_btn.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.browse_btn, alignment=Qt.AlignCenter)

        format_lbl = QLabel("PDF • DOCX • XLSX • TXT • PNG • JPG • JPEG • TIFF")
        format_lbl.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 600; letter-spacing: 0.5px; margin-top: 8px;")
        format_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(format_lbl)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and Path(urls[0].toLocalFile()).suffix.lower() in SUPPORTED_EXTENSIONS:
                event.acceptProposedAction()
                self.setStyleSheet("border-color: #38bdf8; background-color: #0d1e38;")
                return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")
        event.accept()

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet("")
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if Path(path).suffix.lower() in SUPPORTED_EXTENSIONS:
                event.acceptProposedAction()
                self.file_dropped.emit(path)
                return
        event.ignore()


class UploadView(QWidget):
    """
    Screen 1 — Upload Document
    Allows drag-and-drop or browsing for an engineering document,
    displays a compact document card upon selection, and enables
    progression to Comparison Mode.
    """
    document_selected = Signal(str)
    continue_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_file_path: Optional[str] = None
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 28, 32, 32)
        main_layout.setSpacing(24)

        # 1. Minimal Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        title = QLabel("SpecGuard")
        title.setObjectName("brand_title")
        subtitle = QLabel("Engineering Document Comparison")
        subtitle.setObjectName("brand_subtitle")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addLayout(header_layout)

        # Centered container
        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)
        center_layout.setAlignment(Qt.AlignCenter)
        center_layout.setContentsMargins(0, 20, 0, 20)

        self.content_frame = QFrame()
        self.content_frame.setFixedWidth(640)
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(18)

        # Drop Zone (Empty State)
        self.drop_zone = DropZoneWidget()
        self.drop_zone.file_dropped.connect(self.set_selected_file)
        self.drop_zone.browse_btn.clicked.connect(self._on_browse)
        self.content_layout.addWidget(self.drop_zone)

        # Selected Document Card (Hidden initially)
        self.doc_card = QFrame()
        self.doc_card.setObjectName("doc_card")
        doc_card_layout = QVBoxLayout(self.doc_card)
        doc_card_layout.setSpacing(14)

        card_header = QHBoxLayout()
        card_icon = QLabel("📄")
        card_icon.setStyleSheet("font-size: 32px; padding-right: 8px;")
        card_header.addWidget(card_icon)

        meta_col = QVBoxLayout()
        meta_col.setSpacing(3)
        self.card_filename = QLabel("")
        self.card_filename.setStyleSheet("color: #f8fafc; font-size: 15px; font-weight: 700;")
        self.card_details = QLabel("")
        self.card_details.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 500;")
        meta_col.addWidget(self.card_filename)
        meta_col.addWidget(self.card_details)
        card_header.addLayout(meta_col, 1)

        doc_card_layout.addLayout(card_header)

        # Card Actions
        actions_row = QHBoxLayout()
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setProperty("class", "secondary")
        self.remove_btn.setCursor(Qt.PointingHandCursor)
        self.remove_btn.clicked.connect(self.reset_upload)
        actions_row.addWidget(self.remove_btn)

        self.replace_btn = QPushButton("Replace File")
        self.replace_btn.setProperty("class", "secondary")
        self.replace_btn.setCursor(Qt.PointingHandCursor)
        self.replace_btn.clicked.connect(self._on_browse)
        actions_row.addWidget(self.replace_btn)

        actions_row.addStretch()

        self.continue_btn = QPushButton("Continue to Mode Selection →")
        self.continue_btn.setProperty("class", "primary")
        self.continue_btn.setCursor(Qt.PointingHandCursor)
        self.continue_btn.setStyleSheet("font-weight: 700; padding: 9px 22px; font-size: 13px;")
        self.continue_btn.clicked.connect(self._on_continue)
        actions_row.addWidget(self.continue_btn)

        doc_card_layout.addLayout(actions_row)

        self.content_layout.addWidget(self.doc_card)
        self.doc_card.hide()

        center_layout.addWidget(self.content_frame, alignment=Qt.AlignCenter)
        main_layout.addWidget(center_container, 1)

    def _on_browse(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Engineering Document",
            str(Path.home()),
            "Engineering Documents (*.pdf *.docx *.xlsx *.txt *.png *.jpg *.jpeg *.tiff);;All Files (*)"
        )
        if file_path:
            self.set_selected_file(file_path)

    def set_selected_file(self, file_path: str):
        path = Path(file_path)
        if not path.exists():
            QMessageBox.warning(
                self,
                "Document Error",
                "Unable to read this document. Please check that the file is valid and try again."
            )
            return

        self.selected_file_path = str(path.resolve())
        size_str = format_file_size(path.stat().st_size)
        file_ext = path.suffix.upper().lstrip(".")

        self.card_filename.setText(path.name)
        self.card_details.setText(f"{file_ext} Document • {size_str}")

        self.drop_zone.hide()
        self.doc_card.show()
        self.document_selected.emit(self.selected_file_path)

    def reset_upload(self):
        self.selected_file_path = None
        self.doc_card.hide()
        self.drop_zone.show()

    def _on_continue(self):
        if self.selected_file_path:
            self.continue_requested.emit(self.selected_file_path)
