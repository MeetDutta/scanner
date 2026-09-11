"""
Before / After Suggested Correction Review Dialog for SpecGuard.
Enables side-by-side verification of original engineering text and suggested correction.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton, QFrame
)
from PySide6.QtCore import Qt
from specguard.core.models import Finding


class DiffDialog(QDialog):
    def __init__(self, finding: Finding, parent=None):
        super().__init__(parent)
        self.finding = finding
        self.setWindowTitle(f"Review Correction — {finding.finding_id}")
        self.resize(750, 480)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header Info
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #1e293b; border-radius: 6px; padding: 12px;")
        h_layout = QVBoxLayout(header_frame)

        title = QLabel(f"[{self.finding.severity}] {self.finding.category} — {self.finding.finding_id}")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        h_layout.addWidget(title)

        loc = QLabel(f"Location: {self.finding.location} | Rule: {self.finding.rule_reference or 'Standard Specification'}")
        loc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        h_layout.addWidget(loc)

        layout.addWidget(header_frame)

        # Side-by-Side Comparison
        diff_layout = QHBoxLayout()
        diff_layout.setSpacing(16)

        # Original
        orig_box = QVBoxLayout()
        orig_lbl = QLabel("Original Document Content (Detected)")
        orig_lbl.setStyleSheet("font-weight: 600; color: #ef4444;")
        self.orig_edit = QTextEdit()
        self.orig_edit.setReadOnly(True)
        self.orig_edit.setText(f"{self.finding.original_content}\n\nDetected Value:\n{self.finding.detected_value}")
        self.orig_edit.setStyleSheet("background-color: #1c1917; border: 1px solid #7f1d1d; color: #fca5a5; font-family: monospace;")
        orig_box.addWidget(orig_lbl)
        orig_box.addWidget(self.orig_edit)
        diff_layout.addLayout(orig_box)

        # Suggested Correction
        corr_box = QVBoxLayout()
        corr_lbl = QLabel("Suggested Correction (Compliant)")
        corr_lbl.setStyleSheet("font-weight: 600; color: #10b981;")
        self.corr_edit = QTextEdit()
        self.corr_edit.setReadOnly(True)
        self.corr_edit.setText(f"Expected Standard Value:\n{self.finding.expected_value}\n\nSuggested Action:\n{self.finding.suggested_correction}")
        self.corr_edit.setStyleSheet("background-color: #064e3b; border: 1px solid #047857; color: #a7f3d0; font-family: monospace;")
        corr_box.addWidget(corr_lbl)
        corr_box.addWidget(self.corr_edit)
        diff_layout.addLayout(corr_box)

        layout.addLayout(diff_layout)

        # Explanation Box
        exp_lbl = QLabel(f"Technical Rationale: {self.finding.explanation}")
        exp_lbl.setWordWrap(True)
        exp_lbl.setStyleSheet("color: #cbd5e1; font-size: 12px; padding: 6px; background-color: #1e293b; border-radius: 4px;")
        layout.addWidget(exp_lbl)

        # Bottom Disclaimer and Close Button
        btn_layout = QHBoxLayout()
        disclaimer = QLabel("Notice: Decision-support suggestion only. Verify with domain engineering lead.")
        disclaimer.setStyleSheet("color: #64748b; font-size: 11px;")
        btn_layout.addWidget(disclaimer)
        btn_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setProperty("class", "secondary")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
