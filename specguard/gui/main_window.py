"""
Main Desktop Window for SpecGuard.
Implements dark technical CAD layout, left navigation sidebar, and view stack orchestration.
"""

from pathlib import Path
from typing import List

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QPushButton, QLabel, QFrame, QButtonGroup, QStatusBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from specguard.storage.database import DatabaseManager
from specguard.storage.repositories import SessionRepository, DocumentRepository
from specguard.core.models import DocumentModel, Finding
from specguard.gui.theme import DARK_THEME_QSS
from specguard.gui.views.dashboard_view import DashboardView
from specguard.gui.views.upload_view import UploadView
from specguard.gui.views.analysis_view import AnalysisView
from specguard.gui.views.results_view import ResultsView
from specguard.gui.views.standards_view import StandardsView
from specguard.gui.views.models_view import ModelsView
from specguard.gui.views.reports_view import ReportsView
from specguard.gui.views.diagnostics_view import DiagnosticsView
from specguard.gui.views.settings_view import SettingsView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SpecGuard — Offline Engineering Document Intelligence & Standards Compliance")
        self.resize(1280, 840)
        self.setMinimumSize(1024, 700)

        self.db = DatabaseManager()
        self.session_repo = SessionRepository(self.db)
        self.doc_repo = DocumentRepository(self.db)

        self.current_doc: DocumentModel = None
        self.current_findings: List[Finding] = []
        self.current_session_id: str = ""

        self.setup_ui()
        self.setStyleSheet(DARK_THEME_QSS)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Left Sidebar Navigation
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(0, 0, 0, 16)
        sb_layout.setSpacing(4)

        # Branding
        title_lbl = QLabel("SpecGuard")
        title_lbl.setObjectName("app_title")
        sb_layout.addWidget(title_lbl)

        sub_lbl = QLabel("Engineering Quality AI")
        sub_lbl.setObjectName("app_subtitle")
        sb_layout.addWidget(sub_lbl)

        # Offline badge in sidebar
        badge_box = QFrame()
        badge_box.setStyleSheet("background-color: #064e3b; border: 1px solid #059669; border-radius: 4px; margin: 0 12px 12px 12px; padding: 4px 8px;")
        bb_layout = QHBoxLayout(badge_box)
        bb_layout.setContentsMargins(2, 2, 2, 2)
        badge_lbl = QLabel("🔒 100% OFFLINE")
        badge_lbl.setStyleSheet("color: #a7f3d0; font-size: 11px; font-weight: bold;")
        bb_layout.addWidget(badge_lbl)
        sb_layout.addWidget(badge_box)

        # Navigation Buttons
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        self.btn_dashboard = self._create_nav_button("📊 Dashboard", 0)
        self.btn_upload = self._create_nav_button("📄 Documents", 1)
        self.btn_analysis = self._create_nav_button("⚙️ Analysis", 2)
        self.btn_results = self._create_nav_button("🔍 Results & Preview", 3)
        self.btn_standards = self._create_nav_button("📚 Standards Rules", 4)
        self.btn_models = self._create_nav_button("🧠 AI Models", 5)
        self.btn_reports = self._create_nav_button("📤 Export Center", 6)
        self.btn_diag = self._create_nav_button("🛡️ Diagnostics", 7)
        self.btn_settings = self._create_nav_button("⚙️ Settings", 8)

        for btn in [self.btn_dashboard, self.btn_upload, self.btn_analysis, self.btn_results,
                    self.btn_standards, self.btn_models, self.btn_reports, self.btn_diag, self.btn_settings]:
            sb_layout.addWidget(btn)

        sb_layout.addStretch()
        version_lbl = QLabel("v1.0.0 | IEEE & Academic Ready")
        version_lbl.setStyleSheet("color: #64748b; font-size: 10px; padding: 0 16px;")
        sb_layout.addWidget(version_lbl)

        main_layout.addWidget(sidebar)

        # 2. Main Stacked Widget Container
        self.stack = QStackedWidget()

        self.view_dashboard = DashboardView(self.db)
        self.view_upload = UploadView()
        self.view_analysis = AnalysisView()
        self.view_results = ResultsView()
        self.view_standards = StandardsView()
        self.view_models = ModelsView()
        self.view_reports = ReportsView()
        self.view_diagnostics = DiagnosticsView(self.db)
        self.view_settings = SettingsView()

        self.stack.addWidget(self.view_dashboard)    # 0
        self.stack.addWidget(self.view_upload)       # 1
        self.stack.addWidget(self.view_analysis)     # 2
        self.stack.addWidget(self.view_results)      # 3
        self.stack.addWidget(self.view_standards)    # 4
        self.stack.addWidget(self.view_models)       # 5
        self.stack.addWidget(self.view_reports)      # 6
        self.stack.addWidget(self.view_diagnostics)  # 7
        self.stack.addWidget(self.view_settings)     # 8

        main_layout.addWidget(self.stack, 1)

        # Connect Navigation Signals
        self.view_dashboard.open_upload_requested.connect(lambda: self._switch_tab(1))
        self.view_dashboard.open_session_requested.connect(self._load_session_into_results)
        self.view_upload.start_analysis_requested.connect(self._start_analysis_flow)
        self.view_analysis.analysis_finished.connect(self._on_analysis_finished)

        # Status Bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("background-color: #0b1120; color: #94a3b8; border-top: 1px solid #1e293b;")
        self.status_bar.showMessage("Ready | 100% Offline Mode Verified | Local SQLite & PyMuPDF Engine Active")
        self.setStatusBar(self.status_bar)

        self._switch_tab(0)

    def _create_nav_button(self, label: str, index: int) -> QPushButton:
        btn = QPushButton(label)
        btn.setCheckable(True)
        btn.clicked.connect(lambda: self._switch_tab(index))
        self.nav_group.addButton(btn, index)
        return btn

    def _switch_tab(self, index: int):
        self.stack.setCurrentIndex(index)
        btn = self.nav_group.button(index)
        if btn:
            btn.setChecked(True)

        if index == 0:
            self.view_dashboard.refresh_data()
        elif index == 7:
            self.view_diagnostics.refresh_diagnostics()

    def _start_analysis_flow(self, file_path: str, domain: str, standards: list, modules: list):
        self._switch_tab(2)
        self.view_analysis.start_pipeline(file_path, domain, standards, modules)

    def _on_analysis_finished(self, doc: DocumentModel, findings: List[Finding], session_id: str):
        self.current_doc = doc
        self.current_findings = findings
        self.current_session_id = session_id

        # Update Results and Reports views
        self.view_results.display_results(doc, findings, session_id)
        self.view_reports.set_session_data(doc, findings, session_id)

        # Navigate to results view
        self._switch_tab(3)
        self.status_bar.showMessage(f"Analysis Complete: {Path(doc.file_path).name} — {len(findings)} findings recorded.")

    def _load_session_into_results(self, session_id: str):
        findings = self.session_repo.get_findings_for_session(session_id)
        sessions = self.session_repo.get_recent_sessions(limit=50)
        matching_s = next((s for s in sessions if s["session_id"] == session_id), None)
        if not matching_s:
            return

        doc_hash = matching_s["document_hash"]
        doc_info = self.doc_repo.get_document(doc_hash)
        if not doc_info:
            return

        from specguard.core.document_parser import DocumentParser
        try:
            doc = DocumentParser.parse_file(doc_info["file_path"])
            self.current_doc = doc
            self.current_findings = findings
            self.current_session_id = session_id
            self.view_results.display_results(doc, findings, session_id)
            self.view_reports.set_session_data(doc, findings, session_id)
            self._switch_tab(3)
        except Exception as e:
            self.status_bar.showMessage(f"Error reopening document: {e}")
