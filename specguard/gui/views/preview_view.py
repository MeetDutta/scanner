"""
Compared Document Preview View for SpecGuard.
Step 3 in the Formal Government Engineering Verification Workflow:
- Heading: COMPARED DOCUMENT
- Formal summary bar (COMPARISON RESULT, Document, Mode, Status, Counts)
- Left: DOCUMENT PAGES vertical list
- Center: High-contrast document canvas with highlighted findings
- Right: Formal FINDING DETAILS panel (Finding ID, Category, Severity, Detected, Expected, Deviation, Recommendation, Reference)
- Toolbar and Top Actions (NEW COMPARISON, ← BACK TO COMPARISON)
"""

from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QScrollArea, QListWidget, QListWidgetItem, QSplitter, QMenu,
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal

from specguard.core.models import DocumentModel, Finding
from specguard.gui.views.viewer_widget import DocumentViewerWidget
from specguard.export.pdf_annotator import PDFAnnotator
from specguard.export.report_generator import ReportGenerator


class GovFindingDetailPanel(QFrame):
    """Formal government-style finding details panel."""
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("gov_detail_panel")
        self.setFixedWidth(360)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(12)

        # Header Row
        header_row = QHBoxLayout()
        header_lbl = QLabel("FINDING DETAILS")
        header_lbl.setStyleSheet("color: #002b49; font-size: 13px; font-weight: 800; letter-spacing: 0.5px;")
        header_row.addWidget(header_lbl)
        header_row.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(22, 22)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #cbd5e1;
                color: #64748b;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f1f5f9;
                color: #002b49;
            }
        """)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.closed.emit)
        header_row.addWidget(close_btn)
        layout.addLayout(header_row)

        divider = QFrame()
        divider.setStyleSheet("background-color: #cbd5e1; max-height: 1px;")
        layout.addWidget(divider)

        # Fields Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")

        fields_widget = QWidget()
        fields_layout = QVBoxLayout(fields_widget)
        fields_layout.setContentsMargins(0, 0, 4, 0)
        fields_layout.setSpacing(10)

        # 1. Finding ID
        self.id_val = self._add_field(fields_layout, "Finding ID", "CMP-00000")

        # 2. Category
        self.cat_val = self._add_field(fields_layout, "Category", "Engineering Requirement")

        # 3. Severity
        sev_row = QVBoxLayout()
        sev_lbl = QLabel("Severity")
        sev_lbl.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 700; text-transform: uppercase;")
        self.sev_badge = QLabel("CRITICAL")
        self.sev_badge.setProperty("class", "badge_critical")
        self.sev_badge.setFixedWidth(90)
        self.sev_badge.setAlignment(Qt.AlignCenter)
        sev_row.addWidget(sev_lbl)
        sev_row.addWidget(self.sev_badge)
        fields_layout.addLayout(sev_row)

        # 4. Detected
        self.detected_val = self._add_field(fields_layout, "Detected", "—")

        # 5. Expected
        self.expected_val = self._add_field(fields_layout, "Expected", "—")

        # 6. Deviation
        self.deviation_val = self._add_field(fields_layout, "Deviation", "—")

        # 7. Recommendation
        self.recommendation_val = self._add_field(fields_layout, "Recommendation", "—")

        # 8. Reference
        self.reference_val = self._add_field(fields_layout, "Reference", "Local Engineering Standard")

        fields_layout.addStretch()
        scroll.setWidget(fields_widget)
        layout.addWidget(scroll, 1)

    def _add_field(self, parent_layout: QVBoxLayout, label_text: str, default_val: str) -> QLabel:
        col = QVBoxLayout()
        col.setSpacing(2)
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 700; text-transform: uppercase;")
        val = QLabel(default_val)
        val.setWordWrap(True)
        val.setStyleSheet("color: #0f172a; font-size: 12px; font-weight: 600; line-height: 1.3;")
        col.addWidget(lbl)
        col.addWidget(val)
        parent_layout.addLayout(col)
        return val

    def display_finding(self, finding: Finding):
        # ID
        self.id_val.setText(finding.finding_id or "CMP-00001")

        # Category
        self.cat_val.setText(finding.category or "Engineering Finding")

        # Severity
        sev = (finding.severity or "Medium").upper()
        self.sev_badge.setText(sev)
        badge_class = f"badge_{sev.lower()}" if sev.lower() in ["critical", "high", "medium", "low", "info"] else "badge_medium"
        self.sev_badge.setProperty("class", badge_class)
        self.sev_badge.style().unpolish(self.sev_badge)
        self.sev_badge.style().polish(self.sev_badge)

        # Detected
        detected_text = finding.original_content or finding.detected_value or finding.explanation or "Deviation detected in specification text."
        self.detected_val.setText(str(detected_text))

        # Expected
        expected_text = finding.expected_value or "Standard engineering specification requirement."
        self.expected_val.setText(str(expected_text))

        # Deviation
        dev_text = finding.deviation or finding.explanation or "Requirement mismatch detected against standard rule."
        self.deviation_val.setText(str(dev_text))

        # Recommendation
        rec_text = finding.suggested_correction or "Review and align with local engineering standard specifications."
        self.recommendation_val.setText(str(rec_text))

        # Reference
        ref_text = finding.rule_reference or f"Local {finding.domain or 'Engineering'} Standard"
        self.reference_val.setText(str(ref_text))


class PreviewView(QWidget):
    """
    Step 3 — Compared Document Preview
    Formal institutional two-column inspection interface:
    - Top formal result summary
    - Left: Document Pages list
    - Center: Document Preview with visual highlights
    - Right: Finding Details
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
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(10)

        # 1. Top Control Bar (Navigation & New Comparison)
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        self.back_btn = QPushButton("← BACK TO COMPARISON")
        self.back_btn.setProperty("class", "gov_btn_secondary")
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.clicked.connect(self.back_requested.emit)
        top_bar.addWidget(self.back_btn)

        self.new_btn = QPushButton("NEW COMPARISON")
        self.new_btn.setProperty("class", "gov_btn_primary")
        self.new_btn.setCursor(Qt.PointingHandCursor)
        self.new_btn.clicked.connect(self.new_comparison_requested.emit)
        top_bar.addWidget(self.new_btn)

        self.export_btn = QPushButton("EXPORT RESULT ▾")
        self.export_btn.setProperty("class", "gov_btn_secondary")
        self.export_btn.setCursor(Qt.PointingHandCursor)
        self._setup_export_menu()
        top_bar.addWidget(self.export_btn)

        top_bar.addStretch()

        # Findings Navigation
        self.prev_issue_btn = QPushButton("▲ Prev Finding")
        self.prev_issue_btn.setProperty("class", "gov_btn_secondary")
        self.prev_issue_btn.setCursor(Qt.PointingHandCursor)
        self.prev_issue_btn.clicked.connect(self._prev_issue)
        top_bar.addWidget(self.prev_issue_btn)

        self.next_issue_btn = QPushButton("▼ Next Finding")
        self.next_issue_btn.setProperty("class", "gov_btn_secondary")
        self.next_issue_btn.setCursor(Qt.PointingHandCursor)
        self.next_issue_btn.clicked.connect(self._next_issue)
        top_bar.addWidget(self.next_issue_btn)

        main_layout.addLayout(top_bar)

        # 2. Formal Summary Bar (COMPARISON RESULT)
        self.summary_frame = QFrame()
        self.summary_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-left: 4px solid #002b49;
                padding: 10px 16px;
            }
        """)
        sum_layout = QHBoxLayout(self.summary_frame)
        sum_layout.setContentsMargins(8, 6, 8, 6)
        sum_layout.setSpacing(20)

        # Left Info
        info_col = QVBoxLayout()
        info_col.setSpacing(3)
        self.res_title_lbl = QLabel("COMPARISON RESULT")
        self.res_title_lbl.setStyleSheet("color: #002b49; font-size: 13px; font-weight: 800; letter-spacing: 0.5px;")
        self.meta_summary_lbl = QLabel("Document: — | Mode: —")
        self.meta_summary_lbl.setStyleSheet("color: #475569; font-size: 12px; font-weight: 600;")
        info_col.addWidget(self.res_title_lbl)
        info_col.addWidget(self.meta_summary_lbl)
        sum_layout.addLayout(info_col)

        sum_layout.addStretch()

        # Status & Counts
        stat_col = QVBoxLayout()
        stat_col.setSpacing(3)
        self.status_banner_lbl = QLabel("COMPARISON COMPLETED — DEVIATIONS DETECTED")
        self.status_banner_lbl.setStyleSheet("color: #b45309; font-size: 12px; font-weight: 800;")
        self.counts_summary_lbl = QLabel("Critical: 0 | High: 0 | Medium: 0 | Low: 0")
        self.counts_summary_lbl.setStyleSheet("color: #334155; font-size: 12px; font-weight: 700;")
        stat_col.addWidget(self.status_banner_lbl, alignment=Qt.AlignRight)
        stat_col.addWidget(self.counts_summary_lbl, alignment=Qt.AlignRight)
        sum_layout.addLayout(stat_col)

        main_layout.addWidget(self.summary_frame)

        # 3. Main Splitter: Document Pages | Document Preview | Finding Details
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setStyleSheet("QSplitter::handle { background-color: #cbd5e1; width: 2px; }")

        # LEFT: Document Pages List
        pages_box = QFrame()
        pages_box.setStyleSheet("background-color: #ffffff; border: 1px solid #cbd5e1;")
        pages_box.setFixedWidth(160)
        pages_layout = QVBoxLayout(pages_box)
        pages_layout.setContentsMargins(10, 12, 10, 10)
        pages_layout.setSpacing(8)

        pages_title = QLabel("DOCUMENT PAGES")
        pages_title.setStyleSheet("color: #002b49; font-size: 11px; font-weight: 800; letter-spacing: 0.5px;")
        pages_layout.addWidget(pages_title)

        self.pages_list = QListWidget()
        self.pages_list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                background-color: #f8fafc;
                color: #0f172a;
                border: 1px solid #cbd5e1;
                border-radius: 0px;
                padding: 8px 10px;
                margin-bottom: 5px;
                font-weight: 700;
                font-size: 12px;
            }
            QListWidget::item:selected {
                background-color: #002b49;
                color: #ffffff;
                border-color: #002b49;
            }
        """)
        self.pages_list.currentRowChanged.connect(self._on_page_selected)
        pages_layout.addWidget(self.pages_list)

        self.splitter.addWidget(pages_box)

        # CENTER: Document Viewer Canvas
        self.viewer = DocumentViewerWidget()
        self.viewer.finding_selected.connect(self._on_finding_clicked)
        self.splitter.addWidget(self.viewer)

        # RIGHT: Formal Finding Detail Panel
        self.detail_panel = GovFindingDetailPanel()
        self.detail_panel.closed.connect(self.detail_panel.hide)
        self.splitter.addWidget(self.detail_panel)
        self.detail_panel.hide()

        self.splitter.setSizes([160, 800, 360])
        main_layout.addWidget(self.splitter, 1)

    def _setup_export_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                color: #0f172a;
                border: 1px solid #cbd5e1;
                font-weight: 600;
                font-size: 12px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 20px;
            }
            QMenu::item:selected {
                background-color: #002b49;
                color: #ffffff;
            }
        """)
        act_pdf = menu.addAction("Export Certified PDF (with visual highlights)...")
        act_html = menu.addAction("Export Executive Compliance Report (HTML)...")
        act_json = menu.addAction("Export Findings Data (JSON)...")

        act_pdf.triggered.connect(self._export_pdf)
        act_html.triggered.connect(self._export_html)
        act_json.triggered.connect(self._export_json)

        self.export_btn.setMenu(menu)

    def _export_pdf(self):
        if not self.doc or not self.doc.file_path:
            QMessageBox.warning(self, "Export Warning", "No verified document is currently loaded.")
            return

        default_name = f"{Path(self.doc.file_path).stem}_SpecGuard_Annotated.pdf"
        out_path, _ = QFileDialog.getSaveFileName(self, "Export Annotated PDF", default_name, "PDF Files (*.pdf)")
        if not out_path:
            return

        try:
            if Path(self.doc.file_path).suffix.lower() == ".pdf":
                PDFAnnotator.create_annotated_pdf(self.doc.file_path, out_path, self.findings)
            else:
                # If non-PDF (e.g. DOCX or TXT), generate comprehensive HTML or alert
                ReportGenerator.generate_html_report(self.doc, self.findings, getattr(self, "session_id", "SES-EXPORT"), out_path.replace(".pdf", ".html"))
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Original file is non-PDF ({self.doc.file_type}). Generated complete Compliance Audit Report at:\n{out_path.replace('.pdf', '.html')}"
                )
                return

            QMessageBox.information(self, "Export Successful", f"Certified Annotated PDF successfully exported to:\n{out_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed exporting PDF report: {e}")

    def _export_html(self):
        if not self.doc:
            QMessageBox.warning(self, "Export Warning", "No verified document is currently loaded.")
            return

        default_name = f"{Path(self.doc.file_path).stem}_SpecGuard_Audit.html"
        out_path, _ = QFileDialog.getSaveFileName(self, "Export Compliance Report", default_name, "HTML Files (*.html)")
        if not out_path:
            return

        try:
            ReportGenerator.generate_html_report(self.doc, self.findings, getattr(self, "session_id", "SES-EXPORT"), out_path)
            QMessageBox.information(self, "Export Successful", f"Compliance Audit Report successfully exported to:\n{out_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed exporting HTML report: {e}")

    def _export_json(self):
        if not self.doc:
            QMessageBox.warning(self, "Export Warning", "No verified document is currently loaded.")
            return

        default_name = f"{Path(self.doc.file_path).stem}_SpecGuard_Findings.json"
        out_path, _ = QFileDialog.getSaveFileName(self, "Export Findings JSON", default_name, "JSON Files (*.json)")
        if not out_path:
            return

        try:
            ReportGenerator.generate_json_report(self.doc, self.findings, getattr(self, "session_id", "SES-EXPORT"), out_path)
            QMessageBox.information(self, "Export Successful", f"Findings JSON successfully exported to:\n{out_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed exporting JSON: {e}")

    def display_results(self, doc: DocumentModel, findings: List[Finding], domain: str = "Mechanical", session_id: str = ""):
        self.doc = doc
        self.findings = findings
        self.current_domain = domain
        self.session_id = session_id
        self.current_finding_idx = -1

        # Calculate severity counts
        crit_count = sum(1 for f in findings if (f.severity or "").lower() == "critical")
        high_count = sum(1 for f in findings if (f.severity or "").lower() == "high")
        med_count = sum(1 for f in findings if (f.severity or "").lower() == "medium")
        low_count = sum(1 for f in findings if (f.severity or "").lower() in ("low", "informational"))

        # Formal Status Banner Text
        if crit_count > 0:
            self.status_banner_lbl.setText("COMPARISON COMPLETED — CRITICAL FINDINGS REQUIRE REVIEW")
            self.status_banner_lbl.setStyleSheet("color: #b91c1c; font-size: 12px; font-weight: 800;")
        elif (high_count + med_count + low_count) > 0:
            self.status_banner_lbl.setText("COMPARISON COMPLETED — DEVIATIONS DETECTED")
            self.status_banner_lbl.setStyleSheet("color: #b45309; font-size: 12px; font-weight: 800;")
        else:
            self.status_banner_lbl.setText("COMPARISON COMPLETED — NO SIGNIFICANT DEVIATIONS DETECTED")
            self.status_banner_lbl.setStyleSheet("color: #15803d; font-size: 12px; font-weight: 800;")

        # Update Summary Details
        filename = Path(doc.file_path).name
        self.meta_summary_lbl.setText(f"Document: {filename} | Mode: {domain}")
        self.counts_summary_lbl.setText(f"Critical: {crit_count} | High: {high_count} | Medium: {med_count} | Low: {low_count}")

        # Populate Pages List
        self.pages_list.blockSignals(True)
        self.pages_list.clear()
        total_pages = max(1, doc.page_count)

        for p_idx in range(1, total_pages + 1):
            count_on_page = sum(1 for f in findings if f.page == p_idx)
            item_text = f"Page {p_idx:02d}"
            if count_on_page > 0:
                item_text += f"  ({count_on_page})"
            item = QListWidgetItem(item_text)
            self.pages_list.addItem(item)

        self.pages_list.setCurrentRow(0)
        self.pages_list.blockSignals(False)

        # Load Document into Canvas
        self.viewer.load_document(doc, findings)

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

        self.viewer.jump_to_finding(f)

        if 1 <= f.page <= self.pages_list.count():
            self.pages_list.blockSignals(True)
            self.pages_list.setCurrentRow(f.page - 1)
            self.pages_list.blockSignals(False)

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
