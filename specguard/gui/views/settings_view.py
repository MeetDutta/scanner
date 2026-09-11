"""
Settings and Configuration View for SpecGuard.
Enables fine-tuning of severity ranking weights, confidence thresholds, and application preferences.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QDoubleSpinBox,
    QComboBox, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt
from specguard.core.config import DEFAULT_CONFIG, SeverityWeights


class SettingsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        title = QLabel("Application Settings & Ranking Weights")
        title.setProperty("class", "heading1")
        subtitle = QLabel("Configure mathematical priority weights and detection thresholds.")
        subtitle.setProperty("class", "meta")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        # Weights Frame
        weights_frame = QFrame()
        weights_frame.setProperty("class", "panel")
        wf_layout = QVBoxLayout(weights_frame)
        wf_layout.setSpacing(12)

        wf_title = QLabel("Severity & Priority Scoring Weights")
        wf_title.setProperty("class", "heading2")
        wf_layout.addWidget(wf_title)

        # Severity weight
        row1, self.sb_sev = self._create_weight_row("Base Severity Multiplier", DEFAULT_CONFIG.weights.severity)
        wf_layout.addLayout(row1)

        # Safety impact
        row2, self.sb_safety = self._create_weight_row("Safety & Compliance Impact Weight", DEFAULT_CONFIG.weights.safety_impact)
        wf_layout.addLayout(row2)

        # Deviation magnitude
        row3, self.sb_dev = self._create_weight_row("Numerical Deviation Magnitude Weight", DEFAULT_CONFIG.weights.deviation_magnitude)
        wf_layout.addLayout(row3)

        # Standard criticality
        row4, self.sb_std = self._create_weight_row("Formal Standard Criticality Weight", DEFAULT_CONFIG.weights.standard_criticality)
        wf_layout.addLayout(row4)

        # Confidence weight
        row5, self.sb_conf = self._create_weight_row("Detection Confidence Weight", DEFAULT_CONFIG.weights.confidence)
        wf_layout.addLayout(row5)

        # Cross document impact
        row6, self.sb_cross = self._create_weight_row("Cross-Document Contradiction Weight", DEFAULT_CONFIG.weights.cross_document_impact)
        wf_layout.addLayout(row6)

        layout.addWidget(weights_frame)

        # General Preferences Frame
        gen_frame = QFrame()
        gen_frame.setProperty("class", "panel")
        gf_layout = QVBoxLayout(gen_frame)
        gf_layout.setSpacing(12)

        gf_title = QLabel("General Engineering Preferences")
        gf_title.setProperty("class", "heading2")
        gf_layout.addWidget(gf_title)

        d_row = QHBoxLayout()
        d_lbl = QLabel("Default Engineering Domain:")
        d_lbl.setStyleSheet("color: #cbd5e1;")
        self.default_domain_combo = QComboBox()
        self.default_domain_combo.addItems(["Mechanical", "Electrical", "Chemical"])
        d_row.addWidget(d_lbl)
        d_row.addStretch()
        d_row.addWidget(self.default_domain_combo)
        gf_layout.addLayout(d_row)

        layout.addWidget(gen_frame)

        # Save Button
        save_btn = QPushButton("Save Preferences")
        save_btn.setProperty("class", "primary")
        save_btn.clicked.connect(self._save_settings)
        layout.addWidget(save_btn, alignment=Qt.AlignLeft)

        layout.addStretch()

    def _create_weight_row(self, label_text: str, default_val: float):
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #cbd5e1;")
        sb = QDoubleSpinBox()
        sb.setRange(0.1, 10.0)
        sb.setSingleStep(0.5)
        sb.setValue(default_val)
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(sb)
        return row, sb

    def _save_settings(self):
        DEFAULT_CONFIG.weights.severity = self.sb_sev.value()
        DEFAULT_CONFIG.weights.safety_impact = self.sb_safety.value()
        DEFAULT_CONFIG.weights.deviation_magnitude = self.sb_dev.value()
        DEFAULT_CONFIG.weights.standard_criticality = self.sb_std.value()
        DEFAULT_CONFIG.weights.confidence = self.sb_conf.value()
        DEFAULT_CONFIG.weights.cross_document_impact = self.sb_cross.value()
        DEFAULT_CONFIG.active_domain = self.default_domain_combo.currentText().lower()

        QMessageBox.information(self, "Settings Saved", "Configuration successfully updated in memory.")
