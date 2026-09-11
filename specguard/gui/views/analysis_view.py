"""
Document Analysis Progress View for SpecGuard.
Government Institutional Processing Screen:
- Heading: DOCUMENT ANALYSIS IN PROGRESS
- Progress indicator
- Processing document checklist:
  ✓ Document content extraction
  ✓ Document structure analysis
  ● Engineering requirement comparison
  ○ Finding identification
  ○ Preparing comparison preview
"""

from typing import List, Optional
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QProgressBar
)
from PySide6.QtCore import Qt, QThread, Signal

from specguard.core.models import DocumentModel, Finding
from specguard.core.pipeline import AnalysisPipeline

logger = logging.getLogger("SpecGuard.AnalysisView")


class AnalysisWorker(QThread):
    progress_changed = Signal(str, int)
    analysis_completed = Signal(object, list, str) # (doc, findings, session_id)
    analysis_failed = Signal(str)

    def __init__(self, file_path: str, domain: str, standards: Optional[list] = None, modules: Optional[list] = None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.domain = domain
        self.standards = standards or []
        self.modules = modules or []

    def run(self):
        try:
            pipeline = AnalysisPipeline()
            doc, findings, session_id = pipeline.run_analysis(
                file_path=self.file_path,
                domain=self.domain,
                selected_standards=self.standards,
                enabled_modules=self.modules,
                progress_callback=self._callback
            )
            self.analysis_completed.emit(doc, findings, session_id)
        except Exception as e:
            logger.error("Analysis failed internally: %s", e, exc_info=True)
            self.analysis_failed.emit(str(e))

    def _callback(self, stage: str, pct: int):
        self.progress_changed.emit(stage, pct)


class AnalysisView(QWidget):
    """
    Formal Government Institutional Document Processing Screen.
    """
    analysis_finished = Signal(object, list, str)
    analysis_failed_signal = Signal(str)

    GOV_STAGES = [
        "Document content extraction",
        "Document structure analysis",
        "Engineering requirement comparison",
        "Finding identification",
        "Preparing comparison preview"
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: Optional[AnalysisWorker] = None
        self.stage_status_labels: List[QLabel] = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignCenter)

        self.panel = QFrame()
        self.panel.setProperty("class", "gov_panel")
        self.panel.setFixedWidth(640)
        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(36, 32, 36, 36)
        panel_layout.setSpacing(18)

        # Formal Heading
        title = QLabel("DOCUMENT ANALYSIS IN PROGRESS")
        title.setProperty("class", "gov_h1")
        title.setAlignment(Qt.AlignCenter)
        panel_layout.addWidget(title)

        self.status_lbl = QLabel("Processing document...")
        self.status_lbl.setStyleSheet("color: #002b49; font-weight: 700; font-size: 13px;")
        self.status_lbl.setAlignment(Qt.AlignCenter)
        panel_layout.addWidget(self.status_lbl)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        panel_layout.addWidget(self.progress_bar)

        # Formal Checklist Box
        checklist_box = QFrame()
        checklist_box.setStyleSheet("background-color: #f8fafc; border: 1px solid #cbd5e1; padding: 18px 24px;")
        box_layout = QVBoxLayout(checklist_box)
        box_layout.setSpacing(12)

        self.stage_status_labels = []
        for stage_name in self.GOV_STAGES:
            row = QHBoxLayout()
            name_lbl = QLabel(stage_name)
            name_lbl.setStyleSheet("color: #1e293b; font-size: 13px; font-weight: 500;")

            status_lbl = QLabel("○")
            status_lbl.setStyleSheet("color: #94a3b8; font-weight: 800; font-size: 14px;")

            row.addWidget(name_lbl)
            row.addStretch()
            row.addWidget(status_lbl)
            box_layout.addLayout(row)
            self.stage_status_labels.append(status_lbl)

        panel_layout.addWidget(checklist_box)
        layout.addWidget(self.panel)

    def start_pipeline(self, file_path: str, domain: str):
        self.progress_bar.setValue(0)
        for lbl in self.stage_status_labels:
            lbl.setText("○")
            lbl.setStyleSheet("color: #94a3b8; font-weight: 800; font-size: 14px;")

        self.status_lbl.setText("Processing document...")
        self.status_lbl.setStyleSheet("color: #002b49; font-weight: 700; font-size: 13px;")

        self.worker = AnalysisWorker(file_path, domain)
        self.worker.progress_changed.connect(self._on_progress)
        self.worker.analysis_completed.connect(self._on_completed)
        self.worker.analysis_failed.connect(self._on_failed)
        self.worker.start()

    def _on_progress(self, internal_stage: str, pct: int):
        self.progress_bar.setValue(pct)

        # Map to the 5 official government stages
        stage_idx = min(len(self.GOV_STAGES) - 1, int((pct / 100.0) * len(self.GOV_STAGES)))
        self.status_lbl.setText(f"Processing: {self.GOV_STAGES[stage_idx]}")

        for i in range(stage_idx):
            self.stage_status_labels[i].setText("✓")
            self.stage_status_labels[i].setStyleSheet("color: #15803d; font-weight: 900; font-size: 14px;")

        if stage_idx < len(self.GOV_STAGES):
            self.stage_status_labels[stage_idx].setText("●")
            self.stage_status_labels[stage_idx].setStyleSheet("color: #002b49; font-weight: 900; font-size: 14px;")

    def _on_completed(self, doc, findings, session_id):
        for lbl in self.stage_status_labels:
            lbl.setText("✓")
            lbl.setStyleSheet("color: #15803d; font-weight: 900; font-size: 14px;")

        self.progress_bar.setValue(100)
        self.status_lbl.setText("Verification complete. Preparing preview...")
        self.status_lbl.setStyleSheet("color: #15803d; font-weight: 700; font-size: 13px;")
        self.analysis_finished.emit(doc, findings, session_id)

    def _on_failed(self, error_msg: str):
        friendly_error = "The document comparison could not be completed. Please check that the file is valid and try again."
        self.status_lbl.setText(friendly_error)
        self.status_lbl.setStyleSheet("color: #b91c1c; font-weight: 700; font-size: 13px;")
        self.analysis_failed_signal.emit(friendly_error)
