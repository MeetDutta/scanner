"""
Analysis Progress View for SpecGuard.
Displays clean, user-friendly progress state without internal technical jargon.
Stages:
1. Extracting document content
2. Understanding document structure
3. Checking engineering requirements
4. Comparing document
5. Preparing preview
"""

from typing import List, Optional
import logging
from pathlib import Path

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
    """Clean user-facing progress view for document comparison."""
    analysis_finished = Signal(object, list, str)
    analysis_failed_signal = Signal(str)

    USER_STAGES = [
        "Extracting document content",
        "Understanding document structure",
        "Checking engineering requirements",
        "Comparing document",
        "Preparing preview"
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

        panel = QFrame()
        panel.setProperty("class", "panel")
        panel.setFixedWidth(600)
        panel.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border: 1px solid #1f2937;
                border-radius: 12px;
                padding: 36px 32px;
            }
        """)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setSpacing(20)

        title = QLabel("Analyzing document...")
        title.setStyleSheet("color: #f8fafc; font-size: 22px; font-weight: 800;")
        title.setAlignment(Qt.AlignCenter)
        panel_layout.addWidget(title)

        self.status_lbl = QLabel("Extracting document content")
        self.status_lbl.setStyleSheet("color: #38bdf8; font-weight: 600; font-size: 14px;")
        self.status_lbl.setAlignment(Qt.AlignCenter)
        panel_layout.addWidget(self.status_lbl)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1e293b;
                border-radius: 4px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #0284c7;
                border-radius: 4px;
            }
        """)
        panel_layout.addWidget(self.progress_bar)

        # 5 Clean User-Facing Stages Box
        stages_box = QFrame()
        stages_box.setStyleSheet("background-color: #0b1120; border: 1px solid #1e293b; border-radius: 8px; padding: 18px 22px;")
        stages_layout = QVBoxLayout(stages_box)
        stages_layout.setSpacing(12)

        self.stage_status_labels = []
        for stage_name in self.USER_STAGES:
            row = QHBoxLayout()
            name_lbl = QLabel(stage_name)
            name_lbl.setStyleSheet("color: #cbd5e1; font-size: 13px; font-weight: 500;")

            status_lbl = QLabel("○ Pending")
            status_lbl.setStyleSheet("color: #64748b; font-weight: 600; font-size: 12px;")

            row.addWidget(name_lbl)
            row.addStretch()
            row.addWidget(status_lbl)
            stages_layout.addLayout(row)
            self.stage_status_labels.append(status_lbl)

        panel_layout.addWidget(stages_box)
        layout.addWidget(panel)

    def start_pipeline(self, file_path: str, domain: str):
        self.progress_bar.setValue(0)
        for lbl in self.stage_status_labels:
            lbl.setText("○ Pending")
            lbl.setStyleSheet("color: #64748b; font-weight: 600; font-size: 12px;")

        self.status_lbl.setText("Extracting document content")
        self.status_lbl.setStyleSheet("color: #38bdf8; font-weight: 600; font-size: 14px;")

        self.worker = AnalysisWorker(file_path, domain)
        self.worker.progress_changed.connect(self._on_progress)
        self.worker.analysis_completed.connect(self._on_completed)
        self.worker.analysis_failed.connect(self._on_failed)
        self.worker.start()

    def _on_progress(self, internal_stage: str, pct: int):
        self.progress_bar.setValue(pct)

        # Map 0-100% to the 5 user-facing stages
        stage_idx = min(len(self.USER_STAGES) - 1, int((pct / 100.0) * len(self.USER_STAGES)))
        self.status_lbl.setText(self.USER_STAGES[stage_idx])

        for i in range(stage_idx):
            self.stage_status_labels[i].setText("✓ Complete")
            self.stage_status_labels[i].setStyleSheet("color: #10b981; font-weight: 700; font-size: 12px;")

        if stage_idx < len(self.USER_STAGES):
            self.stage_status_labels[stage_idx].setText("⟳ In Progress")
            self.stage_status_labels[stage_idx].setStyleSheet("color: #38bdf8; font-weight: 700; font-size: 12px;")

    def _on_completed(self, doc, findings, session_id):
        for lbl in self.stage_status_labels:
            lbl.setText("✓ Complete")
            lbl.setStyleSheet("color: #10b981; font-weight: 700; font-size: 12px;")

        self.progress_bar.setValue(100)
        self.status_lbl.setText("Comparison complete.")
        self.status_lbl.setStyleSheet("color: #10b981; font-weight: 700; font-size: 14px;")
        self.analysis_finished.emit(doc, findings, session_id)

    def _on_failed(self, error_msg: str):
        # Present simplified user-friendly error message
        friendly_error = "The document comparison could not be completed. Please check that the file is valid and try again."
        self.status_lbl.setText(friendly_error)
        self.status_lbl.setStyleSheet("color: #ef4444; font-weight: 700; font-size: 13px;")
        self.analysis_failed_signal.emit(friendly_error)
