"""
Document Acquisition and Configuration View for SpecGuard.
Drag-and-drop ingestion, domain selector, standards configurator, and file inspector.
"""

from pathlib import Path
from typing import List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QFileDialog, QComboBox, QListWidget, QListWidgetItem, QCheckBox,
    QMessageBox
)
from PySide6.QtCore import Qt, Signal
from specguard.core.config import STANDARDS_DIR


class UploadView(QWidget):
    start_analysis_requested = Signal(str, str, list, list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_file_path: str = ""
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        # Header
        title = QLabel("Acquire & Configure Engineering Document")
        title.setProperty("class", "heading1")
        subtitle = QLabel("Supported formats: PDF, DOCX, XLSX, TXT, PNG, JPG, TIFF | 100% Local Ingestion")
        subtitle.setProperty("class", "meta")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        # Main split: Left (Upload / Drop area), Right (Domain & Standards config)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # Left: File Drop Zone
        left_panel = QFrame()
        left_panel.setProperty("class", "panel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(16)

        drop_zone = QFrame()
        drop_zone.setStyleSheet("""
            QFrame {
                border: 2px dashed #334155;
                border-radius: 10px;
                background-color: #0b1120;
                padding: 40px;
            }
            QFrame:hover {
                border-color: #38bdf8;
            }
        """)
        drop_layout = QVBoxLayout(drop_zone)
        drop_layout.setAlignment(Qt.AlignCenter)

        icon_lbl = QLabel("📄")
        icon_lbl.setStyleSheet("font-size: 48px; margin-bottom: 8px;")
        icon_lbl.setAlignment(Qt.AlignCenter)
        drop_layout.addWidget(icon_lbl)

        self.drop_label = QLabel("Click to Browse or Drag & Drop Document Here")
        self.drop_label.setStyleSheet("color: #cbd5e1; font-weight: 600; font-size: 15px;")
        self.drop_label.setAlignment(Qt.AlignCenter)
        drop_layout.addWidget(self.drop_label)

        browse_btn = QPushButton("Browse Local File")
        browse_btn.setProperty("class", "secondary")
        browse_btn.clicked.connect(self._on_browse)
        drop_layout.addWidget(browse_btn, alignment=Qt.AlignCenter)

        left_layout.addWidget(drop_zone)

        # File Inspector Box
        self.info_frame = QFrame()
        self.info_frame.setStyleSheet("background-color: #0f172a; border-radius: 6px; padding: 12px;")
        info_layout = QVBoxLayout(self.info_frame)
        self.file_name_lbl = QLabel("No document selected")
        self.file_name_lbl.setStyleSheet("font-weight: 600; color: #f8fafc;")
        self.file_details_lbl = QLabel("Select a file to inspect metadata.")
        self.file_details_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        info_layout.addWidget(self.file_name_lbl)
        info_layout.addWidget(self.file_details_lbl)
        left_layout.addWidget(self.info_frame)

        content_layout.addWidget(left_panel, 3)

        # Right: Configuration Panel
        right_panel = QFrame()
        right_panel.setProperty("class", "panel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(14)

        domain_lbl = QLabel("Engineering Domain")
        domain_lbl.setProperty("class", "heading2")
        right_layout.addWidget(domain_lbl)

        self.domain_combo = QComboBox()
        self.domain_combo.addItems(["Mechanical", "Electrical", "Chemical"])
        self.domain_combo.currentTextChanged.connect(self._on_domain_changed)
        right_layout.addWidget(self.domain_combo)

        standards_lbl = QLabel("Installed Standards & Rules")
        standards_lbl.setProperty("class", "heading2")
        right_layout.addWidget(standards_lbl)

        self.standards_list = QListWidget()
        self.standards_list.setStyleSheet("background-color: #0f172a; border: 1px solid #334155; border-radius: 6px;")
        right_layout.addWidget(self.standards_list)

        modules_lbl = QLabel("Analysis Engines")
        modules_lbl.setProperty("class", "heading2")
        right_layout.addWidget(modules_lbl)

        self.cb_formatting = QCheckBox("Formatting & Layout (Fonts, Margins, Spacing)")
        self.cb_formatting.setChecked(True)
        self.cb_structure = QCheckBox("Structure & Outline Hierarchy (Missing Sections, 3.1 -> 3.3)")
        self.cb_structure.setChecked(True)
        self.cb_toc = QCheckBox("Table of Contents Validation")
        self.cb_toc.setChecked(True)
        self.cb_tables = QCheckBox("Engineering Tables & Missing Cells")
        self.cb_tables.setChecked(True)
        self.cb_grammar = QCheckBox("Grammar & Engineering Whitelist")
        self.cb_grammar.setChecked(True)
        self.cb_engineering = QCheckBox("Engineering Parameters & Unit Normalization")
        self.cb_engineering.setChecked(True)
        self.cb_logical = QCheckBox("Logical Contradictions (e.g. 80°C vs 60°C)")
        self.cb_logical.setChecked(True)
        self.cb_standards = QCheckBox("Local Standards Compliance Rules")
        self.cb_standards.setChecked(True)

        for cb in [self.cb_formatting, self.cb_structure, self.cb_toc, self.cb_tables,
                   self.cb_grammar, self.cb_engineering, self.cb_logical, self.cb_standards]:
            right_layout.addWidget(cb)

        right_layout.addStretch()

        self.run_btn = QPushButton("🚀 Start Intelligent Analysis")
        self.run_btn.setProperty("class", "primary")
        self.run_btn.setStyleSheet("font-size: 14px; padding: 12px;")
        self.run_btn.clicked.connect(self._on_start_analysis)
        right_layout.addWidget(self.run_btn)

        content_layout.addWidget(right_panel, 2)
        layout.addLayout(content_layout)

        # Enable drag and drop on this widget
        self.setAcceptDrops(True)
        self._on_domain_changed("Mechanical")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self._set_selected_file(path)

    def _on_browse(self):
        file_filter = "Engineering Documents (*.pdf *.docx *.xlsx *.txt *.png *.jpg *.jpeg *.tiff);;All Files (*.*)"
        path, _ = QFileDialog.getOpenFileName(self, "Select Engineering Document", "", file_filter)
        if path:
            self._set_selected_file(path)

    def _set_selected_file(self, path: str):
        p = Path(path)
        if not p.exists():
            return
        self.selected_file_path = str(p.resolve())
        size_kb = p.stat().st_size / 1024.0
        size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024.0:.2f} MB"
        self.file_name_lbl.setText(p.name)
        self.file_details_lbl.setText(f"Format: {p.suffix.upper()[1:]} | Size: {size_str} | Path: {self.selected_file_path}")
        self.drop_label.setText(f"Loaded: {p.name}")

    def _on_domain_changed(self, domain_name: str):
        self.standards_list.clear()
        domain_dir = STANDARDS_DIR / domain_name.lower()
        if domain_dir.exists():
            for std_file in domain_dir.glob("*.json"):
                item = QListWidgetItem(f"✓ {std_file.stem.replace('_', ' ').title()}")
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
                item.setData(Qt.UserRole, str(std_file))
                self.standards_list.addItem(item)
        if self.standards_list.count() == 0:
            item = QListWidgetItem("(No local standard rules installed)")
            self.standards_list.addItem(item)

    def _on_start_analysis(self):
        if not self.selected_file_path:
            QMessageBox.warning(self, "No Document Selected", "Please select or drop an engineering document first.")
            return

        domain = self.domain_combo.currentText().lower()
        selected_stds = []
        for i in range(self.standards_list.count()):
            item = self.standards_list.item(i)
            if item.checkState() == Qt.Checked and item.data(Qt.UserRole):
                selected_stds.append(item.data(Qt.UserRole))

        enabled_modules = []
        if self.cb_formatting.isChecked(): enabled_modules.append("formatting")
        if self.cb_structure.isChecked(): enabled_modules.append("structure")
        if self.cb_toc.isChecked(): enabled_modules.append("toc")
        if self.cb_tables.isChecked(): enabled_modules.append("tables")
        if self.cb_grammar.isChecked(): enabled_modules.append("grammar")
        if self.cb_engineering.isChecked(): enabled_modules.append("engineering")
        if self.cb_logical.isChecked(): enabled_modules.append("logical")
        if self.cb_standards.isChecked(): enabled_modules.append("standards")

        self.start_analysis_requested.emit(self.selected_file_path, domain, selected_stds, enabled_modules)
