"""
Comparison Mode Selection View for SpecGuard.
Step 2 in the Formal Government Engineering Verification Workflow:
- Three rectangular institutional domain selection panels: MECHANICAL, ELECTRICAL, CHEMICAL
- Single selection with strong border, check indicator, and clear selected state
- Formal primary COMPARE DOCUMENT button and back navigation
"""

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QMessageBox
)
from PySide6.QtCore import Qt, Signal


class GovModePanel(QFrame):
    """Formal rectangular selection panel representing an engineering domain."""
    clicked = Signal(str)

    def __init__(self, domain_key: str, title: str, subtitle: str, icon: str, parent=None):
        super().__init__(parent)
        self.domain_key = domain_key
        self.is_selected = False
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("class", "gov_mode_card")
        self.setup_ui(title, subtitle, icon)

    def setup_ui(self, title: str, subtitle: str, icon: str):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(18, 24, 18, 24)
        layout.setSpacing(10)

        # Checkmark indicator row
        self.check_lbl = QLabel(" ")
        self.check_lbl.setStyleSheet("color: #002b49; font-weight: 900; font-size: 14px;")
        self.check_lbl.setAlignment(Qt.AlignLeft)
        layout.addWidget(self.check_lbl)

        # Subtle engineering icon
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 28px; color: #334155; margin-bottom: 2px;")
        icon_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #002b49; font-size: 15px; font-weight: 800; letter-spacing: 0.5px;")
        title_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_lbl)

        sub_lbl = QLabel(subtitle)
        sub_lbl.setStyleSheet("color: #475569; font-size: 12px; font-weight: 500;")
        sub_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(sub_lbl)

        self._update_style()

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.check_lbl.setText("✓" if selected else " ")
        self._update_style()

    def _update_style(self):
        if self.is_selected:
            self.setStyleSheet("""
                QFrame {
                    background-color: #f0f7ff;
                    border: 2px solid #002b49;
                    border-radius: 0px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #ffffff;
                    border: 1px solid #cbd5e1;
                    border-radius: 0px;
                }
                QFrame:hover {
                    border-color: #002b49;
                    background-color: #f8fafc;
                }
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.domain_key)
        super().mousePressEvent(event)


class ModeSelectView(QWidget):
    """
    Step 2 — Comparison Mode
    Three and only three formal selection choices:
    MECHANICAL, ELECTRICAL, CHEMICAL.
    """
    start_comparison_requested = Signal(str, str) # (file_path, domain)
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path: Optional[str] = None
        self.selected_domain: Optional[str] = None
        self.cards: dict[str, GovModePanel] = {}
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 24, 40, 40)
        main_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        # Top Control Row
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 12)

        self.back_btn = QPushButton("← BACK TO UPLOAD")
        self.back_btn.setProperty("class", "gov_btn_secondary")
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.clicked.connect(self.back_requested.emit)
        top_row.addWidget(self.back_btn)

        top_row.addStretch()

        self.doc_summary_lbl = QLabel("DOCUMENT: No document loaded")
        self.doc_summary_lbl.setStyleSheet("""
            background-color: #ffffff;
            border: 1px solid #cbd5e1;
            padding: 5px 12px;
            color: #002b49;
            font-size: 12px;
            font-weight: 700;
        """)
        top_row.addWidget(self.doc_summary_lbl)

        # Wrap in 680px panel
        self.panel = QFrame()
        self.panel.setProperty("class", "gov_panel")
        self.panel.setFixedWidth(700)
        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(32, 28, 32, 32)
        panel_layout.setSpacing(20)

        panel_layout.addLayout(top_row)

        # Headings
        h1 = QLabel("COMPARISON MODE")
        h1.setProperty("class", "gov_h1")
        panel_layout.addWidget(h1)

        instruction = QLabel("Select the applicable engineering domain.")
        instruction.setProperty("class", "gov_instruction")
        panel_layout.addWidget(instruction)

        # Three Formal Selection Panels
        modes_row = QHBoxLayout()
        modes_row.setSpacing(16)

        # Mechanical
        panel_mech = GovModePanel(
            domain_key="Mechanical",
            title="MECHANICAL",
            subtitle="Mechanical\nEngineering",
            icon="⚙"
        )
        panel_mech.clicked.connect(self._select_domain)
        self.cards["Mechanical"] = panel_mech
        modes_row.addWidget(panel_mech)

        # Electrical
        panel_elec = GovModePanel(
            domain_key="Electrical",
            title="ELECTRICAL",
            subtitle="Electrical\nEngineering",
            icon="⚡"
        )
        panel_elec.clicked.connect(self._select_domain)
        self.cards["Electrical"] = panel_elec
        modes_row.addWidget(panel_elec)

        # Chemical
        panel_chem = GovModePanel(
            domain_key="Chemical",
            title="CHEMICAL",
            subtitle="Chemical\nEngineering",
            icon="🧪"
        )
        panel_chem.clicked.connect(self._select_domain)
        self.cards["Chemical"] = panel_chem
        modes_row.addWidget(panel_chem)

        panel_layout.addLayout(modes_row)

        # Compare Button
        action_layout = QVBoxLayout()
        action_layout.setAlignment(Qt.AlignCenter)
        action_layout.setContentsMargins(0, 12, 0, 0)

        self.compare_btn = QPushButton("COMPARE DOCUMENT")
        self.compare_btn.setProperty("class", "gov_btn_primary")
        self.compare_btn.setCursor(Qt.PointingHandCursor)
        self.compare_btn.setFixedWidth(280)
        self.compare_btn.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: 800;
                letter-spacing: 0.5px;
                padding: 12px 24px;
            }
        """)
        self.compare_btn.setEnabled(False)
        self.compare_btn.clicked.connect(self._on_start_compare)
        action_layout.addWidget(self.compare_btn, alignment=Qt.AlignCenter)

        panel_layout.addLayout(action_layout)

        main_layout.addWidget(self.panel)

    def set_document(self, file_path: str):
        self.file_path = file_path
        path = Path(file_path)
        self.doc_summary_lbl.setText(f"DOCUMENT: {path.name}")
        self._update_button_state()

    def _select_domain(self, domain: str):
        self.selected_domain = domain
        for d, card in self.cards.items():
            card.set_selected(d == domain)
        self._update_button_state()

    def _update_button_state(self):
        self.compare_btn.setEnabled(bool(self.file_path and self.selected_domain))

    def _on_start_compare(self):
        if not self.file_path or not Path(self.file_path).exists():
            QMessageBox.warning(
                self,
                "Comparison Error",
                "Unable to read this document. Please check that the file is valid and try again."
            )
            return

        if not self.selected_domain:
            QMessageBox.warning(
                self,
                "Comparison Error",
                "Please select a comparison mode to proceed."
            )
            return

        self.start_comparison_requested.emit(self.file_path, self.selected_domain)
