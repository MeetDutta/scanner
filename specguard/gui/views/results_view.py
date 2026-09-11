"""
Interactive Results & Visual Inspection View for SpecGuard.
Split layout containing filterable findings table, detailed finding inspector,
and live DocumentViewerWidget with click-to-jump bounding-box highlights.
"""

from typing import List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QComboBox, QPushButton,
    QSplitter, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, Signal

from specguard.core.models import DocumentModel, Finding
from specguard.gui.views.viewer_widget import DocumentViewerWidget
from specguard.gui.views.diff_view import DiffDialog
from specguard.export.pdf_annotator import PDFAnnotator
from specguard.export.report_generator import ReportGenerator


class ResultsView(QWidget):
    request_export_reports = Signal(object, list, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.doc: Optional[DocumentModel] = None
        self.all_findings: List[Finding] = []
        self.filtered_findings: List[Finding] = []
        self.session_id: str = ""
        self.selected_finding: Optional[Finding] = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Top Action Bar
        top_bar = QHBoxLayout()
        self.title_lbl = QLabel("Analysis Results & Visual Localization")
        self.title_lbl.setProperty("class", "heading1")
        top_bar.addWidget(self.title_lbl)
        top_bar.addStretch()

        self.btn_export_pdf = QPushButton("Annotate PDF")
        self.btn_export_pdf.setProperty("class", "secondary")
        self.btn_export_pdf.clicked.connect(self._export_annotated_pdf)
        top_bar.addWidget(self.btn_export_pdf)

        self.btn_export_report = QPushButton("HTML Audit Report")
        self.btn_export_report.setProperty("class", "primary")
        self.btn_export_report.clicked.connect(self._export_html_report)
        top_bar.addWidget(self.btn_export_report)

        layout.addLayout(top_bar)

        # Main Splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #334155; width: 4px; }")

        # LEFT PANE: Filterable Findings Table & Details
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(10)

        # Filter Bar
        filter_box = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search findings or rules...")
        self.search_input.textChanged.connect(self._apply_filters)
        filter_box.addWidget(self.search_input, 2)

        self.sev_filter = QComboBox()
        self.sev_filter.addItems(["All Severities", "Critical", "High", "Medium", "Low", "Informational"])
        self.sev_filter.currentTextChanged.connect(self._apply_filters)
        filter_box.addWidget(self.sev_filter, 1)

        self.cat_filter = QComboBox()
        self.cat_filter.addItems([
            "All Categories", "Formatting", "Structure", "Table of Contents",
            "Table", "Grammar & Spelling", "Semantic Inconsistency",
            "Logical Contradiction", "Engineering Parameter", "Standards Deviation"
        ])
        self.cat_filter.currentTextChanged.connect(self._apply_filters)
        filter_box.addWidget(self.cat_filter, 1)

        left_layout.addLayout(filter_box)

        # Findings Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Sev", "Category", "Location", "Deviation"])
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_finding_selected)
        left_layout.addWidget(self.table, 3)

        # Finding Detail Panel
        self.detail_frame = QFrame()
        self.detail_frame.setProperty("class", "panel")
        detail_layout = QVBoxLayout(self.detail_frame)
        detail_layout.setSpacing(6)

        self.detail_header = QLabel("Select a finding above to inspect details and jump to document.")
        self.detail_header.setStyleSheet("font-weight: bold; color: #38bdf8;")
        detail_layout.addWidget(self.detail_header)

        self.detail_explanation = QLabel("")
        self.detail_explanation.setWordWrap(True)
        self.detail_explanation.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        detail_layout.addWidget(self.detail_explanation)

        self.detail_vals = QLabel("")
        self.detail_vals.setStyleSheet("color: #94a3b8; font-size: 11px;")
        detail_layout.addWidget(self.detail_vals)

        detail_btn_box = QHBoxLayout()
        self.diff_btn = QPushButton("🔍 Review Suggested Correction (Diff)")
        self.diff_btn.setProperty("class", "secondary")
        self.diff_btn.setEnabled(False)
        self.diff_btn.clicked.connect(self._open_diff_dialog)
        detail_btn_box.addWidget(self.diff_btn)
        detail_btn_box.addStretch()

        detail_layout.addLayout(detail_btn_box)
        left_layout.addWidget(self.detail_frame, 2)

        splitter.addWidget(left_widget)

        # RIGHT PANE: Interactive Document Viewer
        self.viewer = DocumentViewerWidget()
        splitter.addWidget(self.viewer)

        splitter.setSizes([520, 680])
        layout.addWidget(splitter)

    def display_results(self, doc: DocumentModel, findings: List[Finding], session_id: str):
        self.doc = doc
        self.all_findings = findings
        self.session_id = session_id
        self.title_lbl.setText(f"Analysis Results: {Path(doc.file_path).name} ({len(findings)} Findings)")
        self.viewer.load_document(doc, findings)
        self._apply_filters()

        if self.filtered_findings:
            self.table.selectRow(0)

    def _apply_filters(self):
        query = self.search_input.text().lower()
        sev = self.sev_filter.currentText()
        cat = self.cat_filter.currentText()

        self.filtered_findings = []
        for f in self.all_findings:
            if sev != "All Severities" and f.severity != sev:
                continue
            if cat != "All Categories" and f.category != cat:
                continue
            if query:
                match_text = f"{f.finding_id} {f.explanation} {f.detected_value} {f.rule_reference or ''}".lower()
                if query not in match_text:
                    continue
            self.filtered_findings.append(f)

        self.table.setRowCount(len(self.filtered_findings))
        for row_idx, f in enumerate(self.filtered_findings):
            self.table.setItem(row_idx, 0, QTableWidgetItem(f.finding_id))
            self.table.setItem(row_idx, 1, QTableWidgetItem(f.severity))
            self.table.setItem(row_idx, 2, QTableWidgetItem(f.category))
            self.table.setItem(row_idx, 3, QTableWidgetItem(f.location))
            self.table.setItem(row_idx, 4, QTableWidgetItem(f.deviation or str(f.detected_value)))

    def _on_finding_selected(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        if 0 <= row < len(self.filtered_findings):
            finding = self.filtered_findings[row]
            self.selected_finding = finding

            # Update detail card
            self.detail_header.setText(f"[{finding.severity}] {finding.category} — {finding.finding_id}")
            self.detail_explanation.setText(finding.explanation)
            self.detail_vals.setText(
                f"Detected: {finding.detected_value}  |  Expected: {finding.expected_value}\n"
                f"Rule: {finding.rule_reference or 'Standard Rule'}  |  Confidence: {int(finding.confidence * 100)}%"
            )
            self.diff_btn.setEnabled(True)

            # Jump document viewer to page and highlight
            self.viewer.jump_to_finding(finding)

    def _open_diff_dialog(self):
        if self.selected_finding:
            dlg = DiffDialog(self.selected_finding, self)
            dlg.exec()

    def _export_annotated_pdf(self):
        if not self.doc or Path(self.doc.file_path).suffix.lower() != ".pdf":
            QMessageBox.information(self, "Export", "PDF annotation is available for PDF documents.")
            return

        out_path, _ = QFileDialog.getSaveFileName(self, "Save Annotated PDF", f"annotated_{Path(self.doc.file_path).name}", "PDF (*.pdf)")
        if out_path:
            try:
                PDFAnnotator.create_annotated_pdf(self.doc.file_path, out_path, self.all_findings)
                QMessageBox.information(self, "Success", f"Annotated PDF saved successfully to:\n{out_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed saving annotated PDF: {e}")

    def _export_html_report(self):
        if not self.doc:
            return

        out_path, _ = QFileDialog.getSaveFileName(self, "Save Compliance Report", f"report_{Path(self.doc.file_path).stem}.html", "HTML (*.html)")
        if out_path:
            try:
                ReportGenerator.generate_html_report(self.doc, self.all_findings, self.session_id, out_path)
                QMessageBox.information(self, "Success", f"Engineering compliance report saved to:\n{out_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed generating report: {e}")
