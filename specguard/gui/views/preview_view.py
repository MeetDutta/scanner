"""
Compared Document Preview View for SpecGuard.
Screen 3 in the 3-stage minimal workflow:
- Left page navigation panel with issue counts
- Center interactive DocumentViewerWidget with severity-highlighted findings
- Right / Overlay Finding Detail Panel (Category, Problem, Expected, Difference, Severity, Correction)
- Minimal preview toolbar (Previous, Next, Zoom In/Out, Fit Width, Fit Page, Prev/Next Issue)
- Top actions: Back to Comparison, New Comparison
"""

from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QScrollArea, QListWidget, QListWidgetItem, QSplitter
)
from PySide6.QtCore import Qt, Signal

from specguard.core.models import DocumentModel, Finding
from specguard.gui.views.viewer_widget import DocumentViewerWidget


class FindingDetailPanel(QFrame):
    """Clean, focused finding detail inspector."""
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("finding_detail_panel")
        self.setFixedWidth(360)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # Header with severity badge and close button
        header_row = QHBoxLayout()
        self.sev_badge = QLabel("Critical")
        self.sev_badge.setProperty("class", "badge_critical")
        header_row.addWidget(self.sev_badge)

        self.category_lbl = QLabel("Finding Category")
        self.category_lbl.setStyleSheet("color: #f8fafc; font-weight: 700; font-size: 14px; margin-left: 6px;")
        header_row.addWidget(self.category_lbl, 1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #94a3b8;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #f8fafc;
            }
        """)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.closed.emit)
        header_row.addWidget(close_btn)

        layout.addLayout(header_row)

        # Field items container
        fields_box = QFrame()
        fields_box.setStyleSheet("background-color: #0b1120; border: 1px solid #1e293b; border-radius: 8px; padding: 12px;")
        fields_layout = QVBoxLayout(fields_box)
        fields_layout.setSpacing(12)

        # 1. Problem
        self.problem_title = QLabel("Problem Detected")
        self.problem_title.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 700; text-transform: uppercase;")
        self.problem_val = QLabel("")
        self.problem_val.setWordWrap(True)
        self.problem_val.setStyleSheet("color: #e2e8f0; font-size: 13px; line-height: 1.3;")
        fields_layout.addWidget(self.problem_title)
        fields_layout.addWidget(self.problem_val)

        # 2. Expected
        self.expected_title = QLabel("Expected Specification")
        self.expected_title.setStyleSheet("color: #10b981; font-size: 11px; font-weight: 700; text-transform: uppercase;")
        self.expected_val = QLabel("")
        self.expected_val.setWordWrap(True)
        self.expected_val.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        fields_layout.addWidget(self.expected_title)
        fields_layout.addWidget(self.expected_val)

        # 3. Difference
        self.diff_title = QLabel("Deviation / Difference")
        self.diff_title.setStyleSheet("color: #f59e0b; font-size: 11px; font-weight: 700; text-transform: uppercase;")
        self.diff_val = QLabel("")
        self.diff_val.setWordWrap(True)
        self.diff_val.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        fields_layout.addWidget(self.diff_title)
        fields_layout.addWidget(self.diff_val)

        # 4. Suggested Correction
        self.correction_title = QLabel("Suggested Correction")
        self.correction_title.setStyleSheet("color: #a855f7; font-size: 11px; font-weight: 700; text-transform: uppercase;")
        self.correction_val = QLabel("")
        self.correction_val.setWordWrap(True)
        self.correction_val.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        fields_layout.addWidget(self.correction_title)
        fields_layout.addWidget(self.correction_val)

        layout.addWidget(fields_box)
        layout.addStretch()

    def display_finding(self, finding: Finding):
        # Severity Badge
        sev = finding.severity or "Medium"
        self.sev_badge.setText(sev.upper())
        badge_class = f"badge_{sev.lower()}" if sev.lower() in ["critical", "high", "medium", "low", "info"] else "badge_medium"
        self.sev_badge.setProperty("class", badge_class)
        self.sev_badge.style().unpolish(self.sev_badge)
        self.sev_badge.style().polish(self.sev_badge)

        # Category
        self.category_lbl.setText(finding.category or "Engineering Finding")

        # Problem
        problem_text = finding.explanation or finding.original_content or finding.detected_value or "Deviation identified in document text or formatting."
        self.problem_val.setText(str(problem_text))

        # Expected
        expected_text = finding.expected_value or "Standard compliant engineering parameter or formatting requirement."
        self.expected_val.setText(str(expected_text))

        # Difference
        diff_text = finding.deviation or (f"Detected: {finding.detected_value} | Expected: {finding.expected_value}" if finding.detected_value else "Requirement mismatch")
        self.diff_val.setText(str(diff_text))

        # Suggested Correction
        correction_text = finding.suggested_correction or "Verify section against standard engineering specification."
        self.correction_val.setText(str(correction_text))


class PreviewView(QWidget):
    """
    Screen 3 — Compared Document Preview
    Occupies the largest available window area:
    - Page thumbnails on left
    - Visual canvas in center with highlighted findings
    - Finding inspector on right
    - Top toolbar with navigation and zoom
    """
    back_requested = Signal()
    new_comparison_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.doc: Optional[DocumentModel] = None
        self.findings: List[Finding] = []
        self.current_finding_idx: int = -1
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 16)
        main_layout.setSpacing(10)

        # 1. Top Bar (Header + Actions)
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        self.back_btn = QPushButton("← Back to Comparison")
        self.back_btn.setProperty("class", "secondary")
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.clicked.connect(self.back_requested.emit)
        top_bar.addWidget(self.back_btn)

        self.new_btn = QPushButton("New Comparison")
        self.new_btn.setProperty("class", "secondary")
        self.new_btn.setCursor(Qt.PointingHandCursor)
        self.new_btn.clicked.connect(self.new_comparison_requested.emit)
        top_bar.addWidget(self.new_btn)

        # Document & Mode Title
        self.doc_title_lbl = QLabel("Compared Document")
        self.doc_title_lbl.setStyleSheet("color: #f8fafc; font-size: 16px; font-weight: 700; margin-left: 8px;")
        top_bar.addWidget(self.doc_title_lbl)

        self.mode_badge = QLabel("⚙ Mechanical")
        self.mode_badge.setStyleSheet("""
            background-color: #0c1c2e;
            color: #38bdf8;
            border: 1px solid #1e3a5f;
            border-radius: 12px;
            padding: 3px 10px;
            font-size: 11px;
            font-weight: 600;
        """)
        top_bar.addWidget(self.mode_badge)

        self.findings_badge = QLabel("0 Issues")
        self.findings_badge.setStyleSheet("""
            background-color: #271418;
            color: #f87171;
            border: 1px solid #4c1d24;
            border-radius: 12px;
            padding: 3px 10px;
            font-size: 11px;
            font-weight: 700;
        """)
        top_bar.addWidget(self.findings_badge)

        top_bar.addStretch()

        # Issue cycling navigation
        self.prev_issue_btn = QPushButton("▲ Prev Issue")
        self.prev_issue_btn.setProperty("class", "secondary")
        self.prev_issue_btn.setCursor(Qt.PointingHandCursor)
        self.prev_issue_btn.clicked.connect(self._prev_issue)
        top_bar.addWidget(self.prev_issue_btn)

        self.next_issue_btn = QPushButton("▼ Next Issue")
        self.next_issue_btn.setProperty("class", "secondary")
        self.next_issue_btn.setCursor(Qt.PointingHandCursor)
        self.next_issue_btn.clicked.connect(self._next_issue)
        top_bar.addWidget(self.next_issue_btn)

        main_layout.addLayout(top_bar)

        # 2. Main 3-Column Splitter (Pages List | Canvas Viewer | Finding Details)
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setStyleSheet("QSplitter::handle { background-color: #1e293b; width: 3px; }")

        # LEFT: Pages Column
        pages_box = QFrame()
        pages_box.setStyleSheet("background-color: #090d16; border: 1px solid #1e293b; border-radius: 8px;")
        pages_box.setFixedWidth(160)
        pages_layout = QVBoxLayout(pages_box)
        pages_layout.setContentsMargins(8, 12, 8, 8)
        pages_layout.setSpacing(8)

        pages_title = QLabel("Pages")
        pages_title.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 700; text-transform: uppercase; padding-left: 4px;")
        pages_layout.addWidget(pages_title)

        self.pages_list = QListWidget()
        self.pages_list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                background-color: #111827;
                color: #cbd5e1;
                border: 1px solid #1f2937;
                border-radius: 6px;
                padding: 10px 12px;
                margin-bottom: 6px;
                font-weight: 600;
            }
            QListWidget::item:selected {
                background-color: #0369a1;
                color: #f8fafc;
                border-color: #38bdf8;
            }
        """)
        self.pages_list.currentRowChanged.connect(self._on_page_selected)
        pages_layout.addWidget(self.pages_list)

        self.splitter.addWidget(pages_box)

        # CENTER: Document Viewer Canvas
        self.viewer = DocumentViewerWidget()
        self.viewer.finding_selected.connect(self._on_finding_clicked)
        self.splitter.addWidget(self.viewer)

        # RIGHT: Finding Detail Panel
        self.detail_panel = FindingDetailPanel()
        self.detail_panel.closed.connect(self.detail_panel.hide)
        self.splitter.addWidget(self.detail_panel)
        self.detail_panel.hide() # Shown upon clicking an issue

        # Initial splitter sizes
        self.splitter.setSizes([160, 800, 360])
        main_layout.addWidget(self.splitter, 1)

    def display_results(self, doc: DocumentModel, findings: List[Finding], domain: str = "Mechanical"):
        self.doc = doc
        self.findings = findings
        self.current_finding_idx = -1

        # Update Titles & Badges
        filename = Path(doc.file_path).name
        self.doc_title_lbl.setText(filename)

        domain_icons = {"Mechanical": "⚙", "Chemical": "🧪", "Electrical": "⚡"}
        icon = domain_icons.get(domain, "⚙")
        self.mode_badge.setText(f"{icon} {domain}")

        issue_text = f"{len(findings)} Issue{'s' if len(findings) != 1 else ''}"
        self.findings_badge.setText(issue_text)

        # Populate Pages List
        self.pages_list.blockSignals(True)
        self.pages_list.clear()
        total_pages = max(1, doc.page_count)

        for p_idx in range(1, total_pages + 1):
            count_on_page = sum(1 for f in findings if f.page == p_idx)
            item_text = f"Page {p_idx}"
            if count_on_page > 0:
                item_text += f"  ({count_on_page})"
            item = QListWidgetItem(item_text)
            self.pages_list.addItem(item)

        self.pages_list.setCurrentRow(0)
        self.pages_list.blockSignals(False)

        # Load Document into Viewer Canvas
        self.viewer.load_document(doc, findings)

        # If there are findings, highlight the first finding by default
        if findings:
            self._select_finding_by_index(0)
        else:
            self.detail_panel.hide()

    def _on_page_selected(self, row: int):
        if row >= 0:
            target_page = row + 1
            if self.viewer.current_page != target_page:
                self.viewer.current_page = target_page
                self.viewer._render_current_page()

    def _on_finding_clicked(self, finding: Finding):
        if finding in self.findings:
            self.current_finding_idx = self.findings.index(finding)
        self.detail_panel.display_finding(finding)
        self.detail_panel.show()

    def _select_finding_by_index(self, index: int):
        if not self.findings or index < 0 or index >= len(self.findings):
            return
        self.current_finding_idx = index
        f = self.findings[index]

        # Jump viewer to finding
        self.viewer.jump_to_finding(f)

        # Update page list selection
        if 1 <= f.page <= self.pages_list.count():
            self.pages_list.blockSignals(True)
            self.pages_list.setCurrentRow(f.page - 1)
            self.pages_list.blockSignals(False)

        # Display details in inspector panel
        self.detail_panel.display_finding(f)
        self.detail_panel.show()

    def _next_issue(self):
        if not self.findings:
            return
        next_idx = (self.current_finding_idx + 1) % len(self.findings)
        self._select_finding_by_index(next_idx)

    def _prev_issue(self):
        if not self.findings:
            return
        prev_idx = (self.current_finding_idx - 1) % len(self.findings)
        self._select_finding_by_index(prev_idx)
