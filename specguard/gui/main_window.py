"""
SpecGuard Main Application Window.
Formal Government / Public-Sector Engineering Portal Architecture:
- Institutional header banner (SPEC GUARD, Engineering Document Verification System)
- Three-stage formal workflow strip:
  01 DOCUMENT UPLOAD → 02 COMPARISON MODE → 03 DOCUMENT PREVIEW
- Strict three-step workflow (Upload, Mode Select, Preview)
- 100% offline local processing
"""

from pathlib import Path
from typing import List, Optional
import logging

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QPushButton, QLabel, QFrame, QMessageBox, QStatusBar
)
from PySide6.QtCore import Qt

from specguard.storage.database import DatabaseManager
from specguard.repository.manager import RepositoryManager
from specguard.core.models import DocumentModel, Finding
from specguard.gui.theme import GOVERNMENT_THEME_QSS
from specguard.gui.views.upload_view import UploadView
from specguard.gui.views.mode_select_view import ModeSelectView
from specguard.gui.views.analysis_view import AnalysisView
from specguard.gui.views.preview_view import PreviewView

logger = logging.getLogger("SpecGuard.MainWindow")


class MainWindow(QMainWindow):
    """
    Formal Government Institutional Window for SpecGuard:
    Stage 0: Document Upload
    Stage 1: Comparison Mode
    Stage 2: Analysis in Progress
    Stage 3: Compared Document Preview
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SPEC GUARD — Engineering Document Verification System")
        self.resize(1300, 840)
        self.setMinimumSize(1040, 700)

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
        self.setStyleSheet(GOVERNMENT_THEME_QSS)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Formal Institutional Top Header Banner
        top_header = QFrame()
        top_header.setObjectName("gov_header_banner")
        header_layout = QHBoxLayout(top_header)
        header_layout.setContentsMargins(24, 12, 24, 12)
        header_layout.setSpacing(18)

        # Neutral Institutional Emblem (Geometric Crest)
        emblem_lbl = QLabel("🏛️")
        emblem_lbl.setStyleSheet("font-size: 32px;")
        header_layout.addWidget(emblem_lbl)

        # Brand / Title Column
        brand_col = QVBoxLayout()
        brand_col.setSpacing(2)
        brand_title = QLabel("SPEC GUARD")
        brand_title.setObjectName("gov_brand_title")
        brand_sub = QLabel("Engineering Document Verification System")
        brand_sub.setObjectName("gov_brand_sub")
        brand_col.addWidget(brand_title)
        brand_col.addWidget(brand_sub)
        header_layout.addLayout(brand_col)

        header_layout.addStretch()

        # Offline Verification Tag
        meta_tag = QLabel("Offline Document Analysis & Standards Comparison")
        meta_tag.setObjectName("gov_header_meta")
        header_layout.addWidget(meta_tag)

        root_layout.addWidget(top_header)

        # 2. Formal Workflow Strip (01 DOCUMENT UPLOAD → 02 COMPARISON MODE → 03 DOCUMENT PREVIEW)
        workflow_strip = QFrame()
        workflow_strip.setObjectName("workflow_strip")
        wf_layout = QHBoxLayout(workflow_strip)
        wf_layout.setContentsMargins(24, 4, 24, 4)
        wf_layout.setSpacing(12)

        self.btn_step_upload = QPushButton("01  DOCUMENT UPLOAD")
        self.btn_step_upload.setProperty("class", "stage_step_btn")
        self.btn_step_upload.setCursor(Qt.PointingHandCursor)
        self.btn_step_upload.clicked.connect(self._goto_upload)
        wf_layout.addWidget(self.btn_step_upload)

        arrow_1 = QLabel("→")
        arrow_1.setStyleSheet("color: #94a3b8; font-weight: bold; font-size: 14px;")
        wf_layout.addWidget(arrow_1)

        self.btn_step_mode = QPushButton("02  COMPARISON MODE")
        self.btn_step_mode.setProperty("class", "stage_step_btn")
        self.btn_step_mode.setCursor(Qt.PointingHandCursor)
        self.btn_step_mode.clicked.connect(self._goto_mode)
        self.btn_step_mode.setEnabled(False)
        wf_layout.addWidget(self.btn_step_mode)

        arrow_2 = QLabel("→")
        arrow_2.setStyleSheet("color: #94a3b8; font-weight: bold; font-size: 14px;")
        wf_layout.addWidget(arrow_2)

        self.btn_step_preview = QPushButton("03  DOCUMENT PREVIEW")
        self.btn_step_preview.setProperty("class", "stage_step_btn")
        self.btn_step_preview.setCursor(Qt.PointingHandCursor)
        self.btn_step_preview.clicked.connect(self._goto_preview)
        self.btn_step_preview.setEnabled(False)
        wf_layout.addWidget(self.btn_step_preview)

        wf_layout.addStretch()

        root_layout.addWidget(workflow_strip)

        # 3. Main Stacked Content Container
        self.stack = QStackedWidget()

        # Screen 0: Document Upload
        self.view_upload = UploadView()
        self.view_upload.document_selected.connect(self._on_document_selected)
        self.view_upload.continue_requested.connect(self._on_continue_to_mode)
        self.stack.addWidget(self.view_upload) # Index 0

        # Screen 1: Comparison Mode
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

        # 4. Formal Institutional Status Bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #ffffff;
                color: #475569;
                font-size: 11px;
                font-weight: 600;
                border-top: 1px solid #cbd5e1;
                padding: 3px 16px;
            }
        """)
        self.status_bar.showMessage("Official Verification System • 100% Offline Local Architecture")
        self.setStatusBar(self.status_bar)

        self._switch_stage(0)

    def _switch_stage(self, index: int):
        self.stack.setCurrentIndex(index)

        # Update Workflow Step Labels & Styling
        self.btn_step_upload.setText("01  ✓ DOCUMENT UPLOAD" if index > 0 else "01  DOCUMENT UPLOAD")
        self.btn_step_mode.setText("02  ✓ COMPARISON MODE" if index > 1 else "02  COMPARISON MODE")
        self.btn_step_preview.setText("03  DOCUMENT PREVIEW")

        self.btn_step_upload.setProperty("class", "stage_step_active" if index == 0 else ("stage_step_done" if index > 0 else "stage_step_btn"))
        self.btn_step_mode.setProperty("class", "stage_step_active" if index == 1 else ("stage_step_done" if index > 1 else "stage_step_btn"))
        self.btn_step_preview.setProperty("class", "stage_step_active" if index == 3 else "stage_step_btn")

        for btn in [self.btn_step_upload, self.btn_step_mode, self.btn_step_preview]:
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if index == 0:
            self.status_bar.showMessage("Select an engineering document to begin verification.")
        elif index == 1:
            self.status_bar.showMessage("Select applicable engineering domain.")
        elif index == 2:
            self.status_bar.showMessage("Document analysis in progress...")
        elif index == 3:
            doc_name = Path(self.current_doc.file_path).name if self.current_doc else "Document"
            self.status_bar.showMessage(f"Verification completed for {doc_name} • {len(self.current_findings)} findings recorded.")

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

    def _start_comparison(self, file_path: str, domain: str):
        self.current_file_path = file_path
        self.current_domain = domain

        self._switch_stage(2)
        self.view_analysis.start_pipeline(file_path, domain)

    def _on_analysis_finished(self, doc: DocumentModel, findings: List[Finding], session_id: str):
        self.current_doc = doc
        self.current_findings = findings
        self.current_session_id = session_id

        self.btn_step_preview.setEnabled(True)
        self.view_preview.display_results(doc, findings, self.current_domain)
        self._switch_stage(3)

    def _on_analysis_failed(self, error_msg: str):
        QMessageBox.critical(
            self,
            "Document Verification Error",
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
