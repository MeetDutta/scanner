"""
SpecGuard Main Application Window.
Redesigned Minimal User Interface:
Focuses strictly on three primary functions:
1. Upload Document
2. Select Comparison Mode (Mechanical, Chemical, Electrical)
3. Preview Compared Document

Maintains 100% offline local processing, zero cloud dependencies,
and coordinates the existing deep learning, computer vision, and standards pipeline.
"""

from pathlib import Path
from typing import List, Optional
import logging

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QPushButton, QLabel, QFrame, QMessageBox, QStatusBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from specguard.storage.database import DatabaseManager
from specguard.repository.manager import RepositoryManager
from specguard.core.models import DocumentModel, Finding
from specguard.gui.theme import DARK_THEME_QSS
from specguard.gui.views.upload_view import UploadView
from specguard.gui.views.mode_select_view import ModeSelectView
from specguard.gui.views.analysis_view import AnalysisView
from specguard.gui.views.preview_view import PreviewView

logger = logging.getLogger("SpecGuard.MainWindow")


class MainWindow(QMainWindow):
    """
    Focused, three-stage desktop window for SpecGuard:
    Stage 0: Upload Document
    Stage 1: Select Comparison Mode
    Stage 2: Processing Progress
    Stage 3: Compared Document Preview
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SpecGuard — Engineering Document Comparison")
        self.resize(1280, 820)
        self.setMinimumSize(1024, 680)

        # Internal backend managers preserved
        self.db = DatabaseManager()
        self.repo_manager = RepositoryManager(self.db)

        # Workflow State
        self.current_file_path: Optional[str] = None
        self.current_domain: str = "Mechanical"
        self.current_doc: Optional[DocumentModel] = None
        self.current_findings: List[Finding] = []
        self.current_session_id: str = ""

        self.setup_ui()
        self.setStyleSheet(DARK_THEME_QSS)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Top Minimal Header Bar
        top_header = QFrame()
        top_header.setObjectName("top_header")
        header_layout = QHBoxLayout(top_header)
        header_layout.setContentsMargins(20, 10, 20, 10)
        header_layout.setSpacing(16)

        # Brand / Title
        brand_col = QVBoxLayout()
        brand_col.setSpacing(1)
        brand_title = QLabel("SpecGuard")
        brand_title.setObjectName("brand_title")
        brand_sub = QLabel("Engineering Document Comparison")
        brand_sub.setObjectName("brand_subtitle")
        brand_col.addWidget(brand_title)
        brand_col.addWidget(brand_sub)
        header_layout.addLayout(brand_col)

        header_layout.addStretch()

        # Step Breadcrumbs: [1 Upload] → [2 Compare] → [3 Preview]
        steps_layout = QHBoxLayout()
        steps_layout.setSpacing(8)

        self.btn_step_upload = QPushButton("1  Upload")
        self.btn_step_upload.setProperty("class", "step_btn")
        self.btn_step_upload.setCursor(Qt.PointingHandCursor)
        self.btn_step_upload.clicked.connect(self._goto_upload)
        steps_layout.addWidget(self.btn_step_upload)

        arrow_1 = QLabel("→")
        arrow_1.setStyleSheet("color: #475569; font-weight: bold; font-size: 14px;")
        steps_layout.addWidget(arrow_1)

        self.btn_step_mode = QPushButton("2  Mode")
        self.btn_step_mode.setProperty("class", "step_btn")
        self.btn_step_mode.setCursor(Qt.PointingHandCursor)
        self.btn_step_mode.clicked.connect(self._goto_mode)
        self.btn_step_mode.setEnabled(False)
        steps_layout.addWidget(self.btn_step_mode)

        arrow_2 = QLabel("→")
        arrow_2.setStyleSheet("color: #475569; font-weight: bold; font-size: 14px;")
        steps_layout.addWidget(arrow_2)

        self.btn_step_preview = QPushButton("3  Preview")
        self.btn_step_preview.setProperty("class", "step_btn")
        self.btn_step_preview.setCursor(Qt.PointingHandCursor)
        self.btn_step_preview.clicked.connect(self._goto_preview)
        self.btn_step_preview.setEnabled(False)
        steps_layout.addWidget(self.btn_step_preview)

        header_layout.addLayout(steps_layout)
        header_layout.addStretch()

        # Right Action & Status
        right_actions = QHBoxLayout()
        right_actions.setSpacing(10)

        self.btn_top_back = QPushButton("← Back")
        self.btn_top_back.setProperty("class", "secondary")
        self.btn_top_back.setCursor(Qt.PointingHandCursor)
        self.btn_top_back.clicked.connect(self._on_back_clicked)
        self.btn_top_back.setVisible(False)
        right_actions.addWidget(self.btn_top_back)

        self.btn_top_new = QPushButton("New Comparison")
        self.btn_top_new.setProperty("class", "secondary")
        self.btn_top_new.setCursor(Qt.PointingHandCursor)
        self.btn_top_new.clicked.connect(self._reset_to_new_comparison)
        self.btn_top_new.setVisible(False)
        right_actions.addWidget(self.btn_top_new)

        offline_badge = QLabel("🔒 Offline")
        offline_badge.setStyleSheet("""
            color: #10b981;
            font-size: 11px;
            font-weight: 700;
            background-color: #064e3b;
            border: 1px solid #059669;
            border-radius: 4px;
            padding: 4px 8px;
        """)
        right_actions.addWidget(offline_badge)

        header_layout.addLayout(right_actions)
        root_layout.addWidget(top_header)

        # 2. Main Stacked Widget Container
        self.stack = QStackedWidget()

        # Screen 0: Upload
        self.view_upload = UploadView()
        self.view_upload.document_selected.connect(self._on_document_selected)
        self.view_upload.continue_requested.connect(self._on_continue_to_mode)
        self.stack.addWidget(self.view_upload) # Index 0

        # Screen 1: Mode Selection
        self.view_mode = ModeSelectView()
        self.view_mode.back_requested.connect(self._goto_upload)
        self.view_mode.start_comparison_requested.connect(self._start_comparison)
        self.stack.addWidget(self.view_mode) # Index 1

        # Screen 2: Analysis Progress
        self.view_analysis = AnalysisView()
        self.view_analysis.analysis_finished.connect(self._on_analysis_finished)
        self.view_analysis.analysis_failed_signal.connect(self._on_analysis_failed)
        self.stack.addWidget(self.view_analysis) # Index 2

        # Screen 3: Compared Document Preview
        self.view_preview = PreviewView()
        self.view_preview.back_requested.connect(self._goto_mode)
        self.view_preview.new_comparison_requested.connect(self._reset_to_new_comparison)
        self.stack.addWidget(self.view_preview) # Index 3

        root_layout.addWidget(self.stack, 1)

        # 3. Minimal Status Bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("background-color: #090d16; color: #64748b; font-size: 11px; border-top: 1px solid #1e293b; padding: 2px 12px;")
        self.status_bar.showMessage("Ready • 100% Offline Local Processing")
        self.setStatusBar(self.status_bar)

        self._switch_stage(0)

    def _switch_stage(self, index: int):
        self.stack.setCurrentIndex(index)

        # Update Breadcrumb Buttons Styling
        self.btn_step_upload.setProperty("class", "step_btn_active" if index == 0 else ("step_btn_completed" if index > 0 else "step_btn"))
        self.btn_step_mode.setProperty("class", "step_btn_active" if index == 1 else ("step_btn_completed" if index > 1 else "step_btn"))
        self.btn_step_preview.setProperty("class", "step_btn_active" if index == 3 else "step_btn")

        for btn in [self.btn_step_upload, self.btn_step_mode, self.btn_step_preview]:
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Update Top Action Buttons Visibility
        self.btn_top_back.setVisible(index in (1, 3))
        self.btn_top_new.setVisible(index == 3)

        if index == 0:
            self.status_bar.showMessage("Select an engineering document to begin.")
        elif index == 1:
            self.status_bar.showMessage("Choose an engineering domain mode.")
        elif index == 2:
            self.status_bar.showMessage("Analyzing document...")
        elif index == 3:
            doc_name = Path(self.current_doc.file_path).name if self.current_doc else "Document"
            self.status_bar.showMessage(f"Compared {doc_name}: {len(self.current_findings)} findings identified.")

    def _on_document_selected(self, file_path: str):
        self.current_file_path = file_path
        self.btn_step_mode.setEnabled(True)

    def _on_continue_to_mode(self, file_path: str):
        self.current_file_path = file_path
        self.view_mode.set_document(file_path)
        self._switch_stage(1)

    def _goto_upload(self):
        self._switch_stage(0)

    def _goto_mode(self):
        if self.current_file_path:
            self.view_mode.set_document(self.current_file_path)
            self._switch_stage(1)

    def _goto_preview(self):
        if self.current_doc:
            self._switch_stage(3)

    def _on_back_clicked(self):
        curr = self.stack.currentIndex()
        if curr == 3:
            self._switch_stage(1)
        elif curr == 1:
            self._switch_stage(0)

    def _start_comparison(self, file_path: str, domain: str):
        self.current_file_path = file_path
        self.current_domain = domain

        # Switch to Progress Screen
        self._switch_stage(2)

        # Launch offline background pipeline
        self.view_analysis.start_pipeline(file_path, domain)

    def _on_analysis_finished(self, doc: DocumentModel, findings: List[Finding], session_id: str):
        self.current_doc = doc
        self.current_findings = findings
        self.current_session_id = session_id

        # Enable preview step button
        self.btn_step_preview.setEnabled(True)

        # Populate and display Screen 3 (Preview)
        self.view_preview.display_results(doc, findings, self.current_domain)
        self._switch_stage(3)

    def _on_analysis_failed(self, error_msg: str):
        QMessageBox.critical(
            self,
            "Comparison Error",
            "The document comparison could not be completed. Please check that the file is valid and try again."
        )
        self._switch_stage(1)

    def _reset_to_new_comparison(self):
        self.current_file_path = None
        self.current_doc = None
        self.current_findings = []
        self.current_session_id = ""

        self.btn_step_mode.setEnabled(False)
        self.btn_step_preview.setEnabled(False)

        self.view_upload.reset_upload()
        self._switch_stage(0)
