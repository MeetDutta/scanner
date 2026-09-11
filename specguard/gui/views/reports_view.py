"""
Report and Export Center View for SpecGuard.
Facilitates one-click generation of Annotated PDFs, DOCX files, HTML Compliance Audits, and JSON exports.
"""

from pathlib import Path
from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt

from specguard.core.models import DocumentModel, Finding
from specguard.export.pdf_annotator import PDFAnnotator
from specguard.export.docx_annotator import DOCXAnnotator
from specguard.export.report_generator import ReportGenerator


class ReportsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.doc: Optional[DocumentModel] = None
        self.findings: List[Finding] = []
        self.session_id: str = ""
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        # Header
        title = QLabel("Engineering Compliance Export Center")
        title.setProperty("class", "heading1")
        subtitle = QLabel("Generate certified offline audit reports and visually annotated documents.")
        subtitle.setProperty("class", "meta")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        # Status Panel
        self.status_card = QFrame()
        self.status_card.setProperty("class", "panel")
        sc_layout = QVBoxLayout(self.status_card)
        self.doc_name_lbl = QLabel("No active analysis session loaded.")
        self.doc_name_lbl.setStyleSheet("font-size: 15px; font-weight: 600; color: #38bdf8;")
        self.doc_meta_lbl = QLabel("Run an analysis from the Documents tab to export reports.")
        self.doc_meta_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        sc_layout.addWidget(self.doc_name_lbl)
        sc_layout.addWidget(self.doc_meta_lbl)
        layout.addWidget(self.status_card)

        # Export Grid
        grid_layout = QHBoxLayout()
        grid_layout.setSpacing(16)

        # Card 1: Annotated PDF
        pdf_card = QFrame()
        pdf_card.setProperty("class", "panel")
        pdf_layout = QVBoxLayout(pdf_card)
        pdf_lbl = QLabel("Annotated PDF Document")
        pdf_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #f8fafc;")
        pdf_desc = QLabel("Injects color-coded vector highlight boxes and technical finding popups into original PDF.")
        pdf_desc.setWordWrap(True)
        pdf_desc.setStyleSheet("color: #94a3b8; font-size: 12px; margin: 8px 0;")
        self.btn_pdf = QPushButton("Export Annotated PDF")
        self.btn_pdf.setProperty("class", "primary")
        self.btn_pdf.clicked.connect(self._export_pdf)
        pdf_layout.addWidget(pdf_lbl)
        pdf_layout.addWidget(pdf_desc)
        pdf_layout.addStretch()
        pdf_layout.addWidget(self.btn_pdf)
        grid_layout.addWidget(pdf_card)

        # Card 2: HTML Audit Report
        html_card = QFrame()
        html_card.setProperty("class", "panel")
        html_layout = QVBoxLayout(html_card)
        html_lbl = QLabel("HTML Compliance Report")
        html_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #f8fafc;")
        html_desc = QLabel("Full standalone engineering quality report with summary statistics, deviation logs, and standards.")
        html_desc.setWordWrap(True)
        html_desc.setStyleSheet("color: #94a3b8; font-size: 12px; margin: 8px 0;")
        self.btn_html = QPushButton("Export HTML Report")
        self.btn_html.setProperty("class", "primary")
        self.btn_html.clicked.connect(self._export_html)
        html_layout.addWidget(html_lbl)
        html_layout.addWidget(html_desc)
        html_layout.addStretch()
        html_layout.addWidget(self.btn_html)
        grid_layout.addWidget(html_card)

        # Card 3: JSON Machine-Readable Export
        json_card = QFrame()
        json_card.setProperty("class", "panel")
        json_layout = QVBoxLayout(json_card)
        json_lbl = QLabel("Machine-Readable JSON")
        json_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #f8fafc;")
        json_desc = QLabel("Structured JSON payload containing all bounding boxes, coordinates, normalized values, and severity scores.")
        json_desc.setWordWrap(True)
        json_desc.setStyleSheet("color: #94a3b8; font-size: 12px; margin: 8px 0;")
        self.btn_json = QPushButton("Export JSON Data")
        self.btn_json.setProperty("class", "secondary")
        self.btn_json.clicked.connect(self._export_json)
        json_layout.addWidget(json_lbl)
        json_layout.addWidget(json_desc)
        json_layout.addStretch()
        json_layout.addWidget(self.btn_json)
        grid_layout.addWidget(json_card)

        layout.addLayout(grid_layout)
        layout.addStretch()

    def set_session_data(self, doc: DocumentModel, findings: List[Finding], session_id: str):
        self.doc = doc
        self.findings = findings
        self.session_id = session_id

        crit = sum(1 for f in findings if f.severity == "Critical")
        high = sum(1 for f in findings if f.severity == "High")
        self.doc_name_lbl.setText(f"Active: {Path(doc.file_path).name} (Session {session_id})")
        self.doc_meta_lbl.setText(
            f"Total Findings: {len(findings)} | Critical: {crit} | High: {high} | Document Format: {doc.file_type}"
        )

    def _export_pdf(self):
        if not self.doc or Path(self.doc.file_path).suffix.lower() != ".pdf":
            QMessageBox.warning(self, "PDF Only", "Annotated PDF export requires an original PDF source document.")
            return

        out, _ = QFileDialog.getSaveFileName(self, "Save Annotated PDF", f"annotated_{Path(self.doc.file_path).name}", "PDF (*.pdf)")
        if out:
            try:
                PDFAnnotator.create_annotated_pdf(self.doc.file_path, out, self.findings)
                QMessageBox.information(self, "Success", f"Annotated PDF saved successfully to:\n{out}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed saving PDF: {e}")

    def _export_html(self):
        if not self.doc:
            QMessageBox.warning(self, "No Session", "No active analysis session to export.")
            return

        out, _ = QFileDialog.getSaveFileName(self, "Save Compliance Report", f"report_{Path(self.doc.file_path).stem}.html", "HTML (*.html)")
        if out:
            try:
                ReportGenerator.generate_html_report(self.doc, self.findings, self.session_id, out)
                QMessageBox.information(self, "Success", f"HTML report saved successfully to:\n{out}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed generating HTML report: {e}")

    def _export_json(self):
        if not self.doc:
            QMessageBox.warning(self, "No Session", "No active analysis session to export.")
            return

        out, _ = QFileDialog.getSaveFileName(self, "Save JSON Export", f"findings_{Path(self.doc.file_path).stem}.json", "JSON (*.json)")
        if out:
            try:
                ReportGenerator.generate_json_report(self.doc, self.findings, self.session_id, out)
                QMessageBox.information(self, "Success", f"JSON findings saved successfully to:\n{out}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed generating JSON export: {e}")
