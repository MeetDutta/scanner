"""
Document Upload View for SpecGuard.
Step 1 in the Formal Government Engineering Verification Workflow:
- Rectangular bordered institutional upload panel
- Formal document drag & drop target
- Compact SELECTED DOCUMENT card with [ Remove ] and progression button
"""

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".txt", ".png", ".jpg", ".jpeg", ".tiff"}


def format_file_size(num_bytes: int) -> str:
    """Format bytes to human readable string (KB, MB)."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    else:
        return f"{num_bytes / (1024 * 1024):.1f} MB"


class GovDropZoneWidget(QFrame):
    """Formal rectangular drag-and-drop document target."""
    file_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("gov_drop_zone")
        self.setAcceptDrops(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(32, 40, 32, 40)
        layout.setSpacing(14)

        icon_lbl = QLabel("📄")
        icon_lbl.setStyleSheet("font-size: 36px; margin-bottom: 2px; background: transparent; border: none;")
        icon_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_lbl)

        prompt_lbl = QLabel("Drag and drop document here")
        prompt_lbl.setStyleSheet("color: #0f172a; font-size: 15px; font-weight: 700; background: transparent; border: none;")
        prompt_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(prompt_lbl)

        or_lbl = QLabel("or")
        or_lbl.setStyleSheet("color: #64748b; font-size: 12px; background: transparent; border: none;")
        or_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(or_lbl)

        self.browse_btn = QPushButton("Browse Files")
        self.browse_btn.setProperty("class", "gov_btn_primary")
        self.browse_btn.setCursor(Qt.PointingHandCursor)
        self.browse_btn.setMinimumWidth(150)
        self.browse_btn.setFixedHeight(36)
        layout.addWidget(self.browse_btn, alignment=Qt.AlignCenter)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and Path(urls[0].toLocalFile()).suffix.lower() in SUPPORTED_EXTENSIONS:
                event.acceptProposedAction()
                self.setStyleSheet("border-color: #002b49; background-color: #f0f7ff;")
                return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")
        event.accept()

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet("")
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if Path(path).suffix.lower() in SUPPORTED_EXTENSIONS:
                event.acceptProposedAction()
                self.file_dropped.emit(path)
                return
        event.ignore()


class UploadView(QWidget):
    """
    Step 1 — Document Upload
    Formal rectangular layout conforming to public-sector document portal standards.
    """
    document_selected = Signal(str)
    continue_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_file_path: Optional[str] = None
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 32, 40, 40)
        main_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        # Center Container
        self.panel = QFrame()
        self.panel.setProperty("class", "gov_panel")
        self.panel.setFixedWidth(680)
        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(32, 28, 32, 32)
        panel_layout.setSpacing(16)

        # Panel Header
        h1 = QLabel("DOCUMENT UPLOAD")
        h1.setProperty("class", "gov_h1")
        panel_layout.addWidget(h1)

        instruction = QLabel("Select an engineering document for comparison.")
        instruction.setProperty("class", "gov_instruction")
        panel_layout.addWidget(instruction)

        # Drop Zone (Upload Area)
        self.drop_zone = GovDropZoneWidget()
        self.drop_zone.file_dropped.connect(self.set_selected_file)
        self.drop_zone.browse_btn.clicked.connect(self._on_browse)
        panel_layout.addWidget(self.drop_zone)

        # Quick Demo Samples Box
        self.demo_box = QFrame()
        self.demo_box.setStyleSheet("""
            QFrame {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 10px 14px;
            }
        """)
        demo_layout = QVBoxLayout(self.demo_box)
        demo_layout.setContentsMargins(6, 6, 6, 6)
        demo_layout.setSpacing(6)
        demo_header = QLabel("⚡ QUICK TEST DEMO SPECIFICATIONS")
        demo_header.setStyleSheet("color: #0369a1; font-size: 11px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")
        demo_layout.addWidget(demo_header)

        demo_btns_row = QHBoxLayout()
        demo_btns_row.setSpacing(8)

        self.btn_load_mech = QPushButton("⚙️ Mechanical PDF")
        self.btn_load_mech.setProperty("class", "gov_btn_secondary")
        self.btn_load_mech.setCursor(Qt.PointingHandCursor)
        self.btn_load_mech.clicked.connect(lambda: self._load_demo_sample("mechanical_sample_with_errors.pdf"))
        demo_btns_row.addWidget(self.btn_load_mech)

        self.btn_load_elec = QPushButton("⚡ Electrical PDF")
        self.btn_load_elec.setProperty("class", "gov_btn_secondary")
        self.btn_load_elec.setCursor(Qt.PointingHandCursor)
        self.btn_load_elec.clicked.connect(lambda: self._load_demo_sample("electrical_sample_with_errors.pdf"))
        demo_btns_row.addWidget(self.btn_load_elec)

        self.btn_load_chem = QPushButton("🧪 Chemical DOCX")
        self.btn_load_chem.setProperty("class", "gov_btn_secondary")
        self.btn_load_chem.setCursor(Qt.PointingHandCursor)
        self.btn_load_chem.clicked.connect(lambda: self._load_demo_sample("chemical_sample_with_errors.docx"))
        demo_btns_row.addWidget(self.btn_load_chem)

        demo_layout.addLayout(demo_btns_row)
        panel_layout.addWidget(self.demo_box)

        # Format Notice
        self.formats_lbl = QLabel("Supported formats: PDF, DOCX, XLSX, TXT, PNG, JPG, TIFF")
        self.formats_lbl.setStyleSheet("color: #64748b; font-size: 11.5px; font-weight: 500; margin-top: 2px; background: transparent;")
        self.formats_lbl.setAlignment(Qt.AlignCenter)
        panel_layout.addWidget(self.formats_lbl)

        # Selected Document Box (Hidden Initially)
        self.selected_box = QFrame()
        self.selected_box.setObjectName("gov_doc_card")
        sel_layout = QVBoxLayout(self.selected_box)
        sel_layout.setContentsMargins(18, 16, 18, 16)
        sel_layout.setSpacing(12)

        box_header = QLabel("SELECTED DOCUMENT")
        box_header.setStyleSheet("color: #002b49; font-size: 12px; font-weight: 800; letter-spacing: 0.5px;")
        sel_layout.addWidget(box_header)

        divider = QFrame()
        divider.setStyleSheet("background-color: #cbd5e1; max-height: 1px;")
        sel_layout.addWidget(divider)

        doc_row = QHBoxLayout()
        icon = QLabel("📄")
        icon.setStyleSheet("font-size: 28px; padding-right: 6px;")
        doc_row.addWidget(icon)

        meta_col = QVBoxLayout()
        meta_col.setSpacing(2)
        self.card_filename = QLabel("")
        self.card_filename.setStyleSheet("color: #0f172a; font-size: 14px; font-weight: 700;")
        self.card_details = QLabel("")
        self.card_details.setStyleSheet("color: #475569; font-size: 12px;")
        meta_col.addWidget(self.card_filename)
        meta_col.addWidget(self.card_details)
        doc_row.addLayout(meta_col, 1)

        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setProperty("class", "gov_btn_secondary")
        self.remove_btn.setCursor(Qt.PointingHandCursor)
        self.remove_btn.clicked.connect(self.reset_upload)
        doc_row.addWidget(self.remove_btn)

        sel_layout.addLayout(doc_row)

        action_row = QHBoxLayout()
        action_row.addStretch()
        self.continue_btn = QPushButton("PROCEED TO COMPARISON MODE →")
        self.continue_btn.setProperty("class", "gov_btn_primary")
        self.continue_btn.setCursor(Qt.PointingHandCursor)
        self.continue_btn.clicked.connect(self._on_continue)
        action_row.addWidget(self.continue_btn)
        sel_layout.addLayout(action_row)

        panel_layout.addWidget(self.selected_box)
        self.selected_box.hide()

        main_layout.addWidget(self.panel)

    def _on_browse(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Engineering Document",
            str(Path.home()),
            "Engineering Documents (*.pdf *.docx *.xlsx *.txt *.png *.jpg *.jpeg *.tiff);;All Files (*)"
        )
        if file_path:
            self.set_selected_file(file_path)

    def set_selected_file(self, file_path: str):
        path = Path(file_path)
        if not path.exists():
            QMessageBox.warning(
                self,
                "Document Error",
                "Unable to read this document. Please check that the file is valid and try again."
            )
            return

        self.selected_file_path = str(path.resolve())
        size_str = format_file_size(path.stat().st_size)
        file_ext = path.suffix.upper().lstrip(".")

        self.card_filename.setText(path.name)
        self.card_details.setText(f"{file_ext} | {size_str}")

        self.drop_zone.hide()
        self.formats_lbl.hide()
        self.demo_box.hide()
        self.selected_box.show()
        self.document_selected.emit(self.selected_file_path)

    def reset_upload(self):
        self.selected_file_path = None
        self.selected_box.hide()
        self.drop_zone.show()
        self.formats_lbl.show()
        self.demo_box.show()

    def _load_demo_sample(self, sample_name: str):
        # Locate demo_samples directory relative to project root
        demo_dir = Path(__file__).resolve().parent.parent.parent / "demo_samples"
        target_path = demo_dir / sample_name
        if target_path.exists():
            self.set_selected_file(str(target_path))
        else:
            QMessageBox.warning(self, "Demo Sample", f"Demo sample '{sample_name}' not found at {target_path}")

    def _on_continue(self):
        if self.selected_file_path:
            self.continue_requested.emit(self.selected_file_path)
