"""
Analysis Progress View for SpecGuard.
Runs AnalysisPipeline on a background QThread to keep UI completely responsive.
Displays live stage-by-stage checklist and progress status.
"""

from typing import List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QProgressBar, QPushButton
)
from PySide6.QtCore import Qt, QThread, Signal
from specguard.core.models import DocumentModel, Finding
from specguard.core.pipeline import AnalysisPipeline


class AnalysisWorker(QThread):
    progress_changed = Signal(str, int)
    analysis_completed = Signal(object, list, str) # (doc, findings, session_id)
    analysis_failed = Signal(str)

    def __init__(self, file_path: str, domain: str, standards: list, modules: list, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.domain = domain
        self.standards = standards
        self.modules = modules

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
            self.analysis_failed.emit(str(e))

    def _callback(self, stage: str, pct: int):
        self.progress_changed.emit(stage, pct)


class AnalysisView(QWidget):
    analysis_finished = Signal(object, list, str)

    STAGES = [
        "Document Ingestion & Preprocessing",
        "Document Layout & Computer Vision",
        "Structure & Heading Hierarchy Analysis",
        "Table of Contents Cross-Validation",
        "Engineering Tables & Cell Integrity",
        "Grammar & Engineering Whitelist Validation",
        "Domain Parameter Extraction & Normalization",
        "Semantic Propositions & Logical Consistency",
        "Local Standards Knowledge Base Evaluation",
        "Severity Classification & Finding Prioritization"
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: AnalysisWorker = None
        self.stage_labels: List[QLabel] = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignCenter)

        panel = QFrame()
        panel.setProperty("class", "panel")
        panel.setFixedWidth(680)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(32, 32, 32, 32)
        panel_layout.setSpacing(18)

        title = QLabel("Analyzing Document Quality & Standards Compliance")
        title.setProperty("class", "heading1")
        title.setAlignment(Qt.AlignCenter)
        panel_layout.addWidget(title)

        self.status_lbl = QLabel("Initializing offline analysis pipeline...")
        self.status_lbl.setStyleSheet("color: #38bdf8; font-weight: 600; font-size: 14px;")
        self.status_lbl.setAlignment(Qt.AlignCenter)
        panel_layout.addWidget(self.status_lbl)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        panel_layout.addWidget(self.progress_bar)

        # Stage Checklist Container
        stages_box = QFrame()
        stages_box.setStyleSheet("background-color: #0f172a; border-radius: 6px; padding: 14px;")
        stages_layout = QVBoxLayout(stages_box)
        stages_layout.setSpacing(8)

        self.stage_labels = []
        for stage_name in self.STAGES:
            row = QHBoxLayout()
            name_lbl = QLabel(stage_name)
            name_lbl.setStyleSheet("color: #94a3b8; font-size: 13px;")
            icon_lbl = QLabel("○ Pending")
            icon_lbl.setStyleSheet("color: #64748b; font-weight: bold; font-size: 12px;")
            row.addWidget(name_lbl)
            row.addStretch()
            row.addWidget(icon_lbl)
            stages_layout.addLayout(row)
            self.stage_labels.append(icon_lbl)

        panel_layout.addWidget(stages_box)

        layout.addWidget(panel)

    def start_pipeline(self, file_path: str, domain: str, standards: list, modules: list):
        self.progress_bar.setValue(0)
        for lbl in self.stage_labels:
            lbl.setText("○ Pending")
            lbl.setStyleSheet("color: #64748b; font-weight: bold; font-size: 12px;")

        self.worker = AnalysisWorker(file_path, domain, standards, modules)
        self.worker.progress_changed.connect(self._on_progress)
        self.worker.analysis_completed.connect(self._on_completed)
        self.worker.analysis_failed.connect(self._on_failed)
        self.worker.start()

    def _on_progress(self, stage: str, pct: int):
        self.status_lbl.setText(stage)
        self.progress_bar.setValue(pct)

        # Update checklist icons based on progress
        stage_idx = min(len(self.STAGES) - 1, int((pct / 100.0) * len(self.STAGES)))
        for i in range(stage_idx):
            self.stage_labels[i].setText("✓ Complete")
            self.stage_labels[i].setStyleSheet("color: #10b981; font-weight: bold; font-size: 12px;")
        if stage_idx < len(self.STAGES):
            self.stage_labels[stage_idx].setText("⟳ In Progress")
            self.stage_labels[stage_idx].setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 12px;")

    def _on_completed(self, doc, findings, session_id):
        for lbl in self.stage_labels:
            lbl.setText("✓ Complete")
            lbl.setStyleSheet("color: #10b981; font-weight: bold; font-size: 12px;")
        self.progress_bar.setValue(100)
        self.status_lbl.setText("Analysis finished successfully.")
        self.analysis_finished.emit(doc, findings, session_id)

    def _on_failed(self, error_msg: str):
        self.status_lbl.setText(f"Analysis failed: {error_msg}")
        self.status_lbl.setStyleSheet("color: #ef4444; font-weight: bold;")
