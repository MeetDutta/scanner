"""
Local AI Model Management View for SpecGuard.
Inspects local ML model versions, integrity hashes, and deterministic fallback statuses.
Strictly offline: Zero automatic internet downloads.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QMessageBox
)
from specguard.models.registry import ModelRegistry
from specguard.core.config import MODELS_DIR


class ModelsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.registry = ModelRegistry()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)

        # Header
        title = QLabel("Local AI Models & Service Management")
        title.setProperty("class", "heading1")
        subtitle = QLabel("Offline Model Architecture: Modular PyTorch/ONNX models with verified deterministic local fallbacks.")
        subtitle.setProperty("class", "meta")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        # Models Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Service / Model Name", "Domain", "Local Status", "Fallback Strategy"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        # Info Box
        info_panel = QFrame()
        info_panel.setProperty("class", "panel")
        ip_layout = QVBoxLayout(info_panel)
        ip_lbl = QLabel(
            "Security & Model Integrity Notice:\n"
            "SpecGuard never executes remote cloud inference (no OpenAI, no Gemini, no Claude, no cloud OCR). "
            "When heavy Deep Learning weights are absent from the local models/ directory, SpecGuard activates "
            "verified deterministic rule-based algorithms to guarantee uninterrupted offline compliance analysis."
        )
        ip_lbl.setWordWrap(True)
        ip_lbl.setStyleSheet("color: #94a3b8; font-size: 12px; line-height: 1.4;")
        ip_layout.addWidget(ip_lbl)
        layout.addWidget(info_panel)

        self.refresh_table()

    def refresh_table(self):
        statuses = self.registry.get_all_statuses()
        rows = [
            ("NLP Entity Recognizer", "Cross-Domain", statuses.get("NLP Entity Model", "-"), "Rule-based technical vocabulary & token parsing"),
            ("Engineering Relation Extractor", "Mechanical/Electrical", statuses.get("Engineering Extraction Model", "-"), "Deterministic physical quantity & unit normalizer"),
            ("Layout & CV Visual Analyzer", "Document Layout", "Active (Local OpenCV Engine)", "Morphological line & contour structure analysis"),
            ("Logical Consistency Engine", "Cross-Document", "Active (Local Parameter Registry)", "Deterministic bounds and cross-page contradiction tracking")
        ]

        self.table.setRowCount(len(rows))
        for r_idx, (name, domain, status, fallback) in enumerate(rows):
            self.table.setItem(r_idx, 0, QTableWidgetItem(name))
            self.table.setItem(r_idx, 1, QTableWidgetItem(domain))
            self.table.setItem(r_idx, 2, QTableWidgetItem(status))
            self.table.setItem(r_idx, 3, QTableWidgetItem(fallback))
