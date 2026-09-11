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
    """Formal selection card representing an engineering domain."""
    clicked = Signal(str)

    def __init__(self, domain_key: str, title: str, standards_tag: str, icon: str, details: str, parent=None):
        super().__init__(parent)
        self.domain_key = domain_key
        self.is_selected = False
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("class", "gov_mode_card")
        self.setFixedHeight(198)
        self.setMinimumWidth(185)
        self.setup_ui(title, standards_tag, icon, details)

    def setup_ui(self, title: str, standards_tag: str, icon: str, details: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        # Selection Badge Top Row
        self.badge_lbl = QLabel("SELECT")
        self.badge_lbl.setStyleSheet("""
            background-color: #f1f5f9;
            color: #64748b;
            border: 1px solid #cbd5e1;
            border-radius: 9px;
            padding: 2px 8px;
            font-size: 10px;
            font-weight: 800;
        """)
        self.badge_lbl.setFixedHeight(18)
        layout.addWidget(self.badge_lbl, alignment=Qt.AlignRight)

        # Engineering Icon
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 26px; background: transparent;")
        icon_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_lbl)

        # Domain Title
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #0f172a; font-size: 13px; font-weight: 800; letter-spacing: 0.5px; background: transparent;")
        title_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_lbl)

        # Standards Reference Tag
        std_lbl = QLabel(standards_tag)
        std_lbl.setStyleSheet("color: #0369a1; font-size: 9.5px; font-weight: 700; background-color: #f0f9ff; border: 1px solid #bae6fd; border-radius: 4px; padding: 2px 5px;")
        std_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(std_lbl)

        # Details list
        det_lbl = QLabel(details)
        det_lbl.setStyleSheet("color: #64748b; font-size: 10px; line-height: 1.2; background: transparent;")
        det_lbl.setAlignment(Qt.AlignCenter)
        det_lbl.setWordWrap(True)
        layout.addWidget(det_lbl)

        self._update_style()

    def set_selected(self, selected: bool):
        self.is_selected = selected
        if selected:
            self.badge_lbl.setText("✓ SELECTED")
            self.badge_lbl.setStyleSheet("""
                background-color: #0284c7;
                color: #ffffff;
                border: 1px solid #0284c7;
                border-radius: 10px;
                padding: 2px 8px;
                font-size: 10px;
                font-weight: 800;
            """)
        else:
            self.badge_lbl.setText("SELECT")
            self.badge_lbl.setStyleSheet("""
                background-color: #f1f5f9;
                color: #64748b;
                border: 1px solid #cbd5e1;
                border-radius: 10px;
                padding: 2px 8px;
                font-size: 10px;
                font-weight: 800;
            """)
        self._update_style()

    def _update_style(self):
        if self.is_selected:
            self.setStyleSheet("""
                GovModePanel, QFrame[class="gov_mode_card"] {
                    background-color: #f0f9ff;
                    border: 2px solid #0284c7;
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                GovModePanel, QFrame[class="gov_mode_card"] {
                    background-color: #ffffff;
                    border: 1px solid #cbd5e1;
                    border-radius: 8px;
                }
                GovModePanel:hover, QFrame[class="gov_mode_card"]:hover {
                    border-color: #0284c7;
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
        main_layout.setContentsMargins(32, 10, 32, 16)
        main_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        # Top Control Row
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 2)

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
            padding: 4px 12px;
            color: #002b49;
            font-size: 11.5px;
            font-weight: 700;
        """)
        top_row.addWidget(self.doc_summary_lbl)

        # Wrap in 700px panel
        self.panel = QFrame()
        self.panel.setProperty("class", "gov_panel")
        self.panel.setFixedWidth(700)
        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(28, 16, 28, 18)
        panel_layout.setSpacing(12)

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
            standards_tag="ASME Y14.5 • ISO 2768",
            icon="⚙️",
            details="Tolerances • Surface Finish Ra • Operating Pressure • Temperature"
        )
        panel_mech.clicked.connect(self._select_domain)
        self.cards["Mechanical"] = panel_mech
        modes_row.addWidget(panel_mech)

        # Electrical
        panel_elec = GovModePanel(
            domain_key="Electrical",
            title="ELECTRICAL",
            standards_tag="IEC 60364 • IEEE 141",
            icon="⚡",
            details="Feeder Voltage • Current Ratings • Frequency • Phase Balance"
        )
        panel_elec.clicked.connect(self._select_domain)
        self.cards["Electrical"] = panel_elec
        modes_row.addWidget(panel_elec)

        # Chemical
        panel_chem = GovModePanel(
            domain_key="Chemical",
            title="CHEMICAL",
            standards_tag="OSHA PSM • PEP-102",
            icon="🧪",
            details="Concentration % • Flash Points • Thermal Runaway Thresholds"
        )
        panel_chem.clicked.connect(self._select_domain)
        self.cards["Chemical"] = panel_chem
        modes_row.addWidget(panel_chem)

        panel_layout.addLayout(modes_row)

        # Template Info Box
        self.tmpl_info_box = QFrame()
        self.tmpl_info_box.setStyleSheet("""
            QFrame {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-left: 3px solid #0284c7;
                border-radius: 4px;
                padding: 10px 14px;
            }
        """)
        tmpl_layout = QVBoxLayout(self.tmpl_info_box)
        tmpl_layout.setContentsMargins(4, 4, 4, 4)
        tmpl_layout.setSpacing(3)
        self.tmpl_title = QLabel("DOMAIN TEMPLATE CONFIGURATION")
        self.tmpl_title.setStyleSheet("color: #0369a1; font-size: 11px; font-weight: 800; letter-spacing: 0.5px;")
        self.tmpl_desc = QLabel("Select an engineering domain above to review enforced standard rules.")
        self.tmpl_desc.setStyleSheet("color: #475569; font-size: 12px;")
        self.tmpl_desc.setWordWrap(True)
        tmpl_layout.addWidget(self.tmpl_title)
        tmpl_layout.addWidget(self.tmpl_desc)
        panel_layout.addWidget(self.tmpl_info_box)

        # Compare Button
        action_layout = QVBoxLayout()
        action_layout.setAlignment(Qt.AlignCenter)
        action_layout.setContentsMargins(0, 6, 0, 0)

        self.compare_btn = QPushButton("COMPARE DOCUMENT")
        self.compare_btn.setProperty("class", "gov_btn_primary")
        self.compare_btn.setCursor(Qt.PointingHandCursor)
        self.compare_btn.setFixedWidth(280)
        self.compare_btn.setStyleSheet("""
            QPushButton {
                font-size: 13px;
                font-weight: 800;
                letter-spacing: 0.5px;
                padding: 10px 24px;
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

        if domain == "Mechanical":
            self.tmpl_desc.setText("Active Standard: ASME Y14.5 / ISO 2768 • Enforces Journal Tolerances (≤ ±0.05 mm), Surface Finish Ra (≤ 0.8 μm), Operating Pressure & Temperature bounds.")
        elif domain == "Electrical":
            self.tmpl_desc.setText("Active Standard: IEC 60364 / IEEE Std 141 • Enforces 3-Phase Voltage (415 V), Switchgear Feeder Current (≤ 630 A), Grid Frequency (50 Hz ± 0.5 Hz).")
        elif domain == "Chemical":
            self.tmpl_desc.setText("Active Standard: OSHA PSM 1910.119 / PEP-102 • Enforces Additive Concentration (≤ 10 wt%), Runaway Temperature (≤ 120°C), Relief Pressure Limits.")

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
