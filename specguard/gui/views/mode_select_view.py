"""
Comparison Mode Selection View for SpecGuard.
Screen 2 in the 3-stage minimal workflow:
Allows selecting exactly one of three engineering domains (Mechanical, Chemical, Electrical)
and launching the comparison pipeline.
"""

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QButtonGroup, QMessageBox
)
from PySide6.QtCore import Qt, Signal


class ModeCard(QFrame):
    """Large interactive card representing an engineering domain."""
    clicked = Signal(str)

    def __init__(self, domain_key: str, icon: str, title: str, description: str, parent=None):
        super().__init__(parent)
        self.domain_key = domain_key
        self.is_selected = False
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("class", "mode_card")
        self.setup_ui(icon, title, description)

    def setup_ui(self, icon: str, title: str, description: str):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(20, 24, 20, 24)
        layout.setSpacing(12)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 42px; margin-bottom: 4px;")
        icon_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #f8fafc; font-size: 17px; font-weight: 700;")
        title_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_lbl)

        desc_lbl = QLabel(description)
        desc_lbl.setStyleSheet("color: #94a3b8; font-size: 12px; line-height: 1.4;")
        desc_lbl.setWordWrap(True)
        desc_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc_lbl)

        self.check_badge = QLabel("✓ Selected")
        self.check_badge.setStyleSheet("color: #38bdf8; font-weight: 700; font-size: 11px; margin-top: 6px;")
        self.check_badge.setAlignment(Qt.AlignCenter)
        self.check_badge.setVisible(False)
        layout.addWidget(self.check_badge)

        self._update_style()

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.check_badge.setVisible(selected)
        self._update_style()

    def _update_style(self):
        if self.is_selected:
            self.setStyleSheet("""
                QFrame {
                    background-color: #0c1c2e;
                    border: 2px solid #38bdf8;
                    border-radius: 12px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #111827;
                    border: 2px solid #1f2937;
                    border-radius: 12px;
                }
                QFrame:hover {
                    border-color: #475569;
                    background-color: #162032;
                }
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.domain_key)
        super().mousePressEvent(event)


class ModeSelectView(QWidget):
    """
    Screen 2 — Select Comparison Mode
    Three large selectable cards:
      ⚙ Mechanical
      🧪 Chemical
      ⚡ Electrical
    """
    start_comparison_requested = Signal(str, str) # (file_path, domain)
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path: Optional[str] = None
        self.selected_domain: Optional[str] = None
        self.cards: dict[str, ModeCard] = {}
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 28, 32, 32)
        main_layout.setSpacing(24)

        # 1. Top navigation row with back button
        top_row = QHBoxLayout()
        self.back_btn = QPushButton("← Back to Upload")
        self.back_btn.setProperty("class", "secondary")
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.clicked.connect(self.back_requested.emit)
        top_row.addWidget(self.back_btn)
        top_row.addStretch()

        # Selected document chip
        self.doc_chip = QLabel("📄 No document loaded")
        self.doc_chip.setStyleSheet("""
            background-color: #111827;
            border: 1px solid #1f2937;
            border-radius: 16px;
            padding: 6px 14px;
            color: #cbd5e1;
            font-size: 12px;
            font-weight: 600;
        """)
        top_row.addWidget(self.doc_chip)
        main_layout.addLayout(top_row)

        # 2. Centered mode selection container
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setAlignment(Qt.AlignCenter)
        center_layout.setContentsMargins(0, 10, 0, 10)
        center_layout.setSpacing(24)

        title_col = QVBoxLayout()
        title_col.setSpacing(6)
        title = QLabel("Select Comparison Mode")
        title.setStyleSheet("color: #f8fafc; font-size: 24px; font-weight: 800;")
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("Choose the engineering domain for standards and specification checks")
        subtitle.setStyleSheet("color: #94a3b8; font-size: 14px;")
        subtitle.setAlignment(Qt.AlignCenter)
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        center_layout.addLayout(title_col)

        # Three cards row
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)

        # Mechanical
        card_mech = ModeCard(
            domain_key="Mechanical",
            icon="⚙",
            title="Mechanical",
            description="For mechanical engineering specifications, ASME/ISO tolerances, pressure ratings, and material limits."
        )
        card_mech.setFixedWidth(240)
        card_mech.clicked.connect(self._select_domain)
        self.cards["Mechanical"] = card_mech
        cards_layout.addWidget(card_mech)

        # Chemical
        card_chem = ModeCard(
            domain_key="Chemical",
            icon="🧪",
            title="Chemical",
            description="For chemical process documents, concentrations, temperatures, flow rates, and safety standards."
        )
        card_chem.setFixedWidth(240)
        card_chem.clicked.connect(self._select_domain)
        self.cards["Chemical"] = card_chem
        cards_layout.addWidget(card_chem)

        # Electrical
        card_elec = ModeCard(
            domain_key="Electrical",
            icon="⚡",
            title="Electrical",
            description="For electrical diagrams and specs, IEEE/IEC voltages, currents, frequencies, and wiring codes."
        )
        card_elec.setFixedWidth(240)
        card_elec.clicked.connect(self._select_domain)
        self.cards["Electrical"] = card_elec
        cards_layout.addWidget(card_elec)

        center_layout.addLayout(cards_layout)

        # Compare Button
        action_col = QVBoxLayout()
        action_col.setAlignment(Qt.AlignCenter)
        action_col.setContentsMargins(0, 12, 0, 0)

        self.compare_btn = QPushButton("Compare Document")
        self.compare_btn.setProperty("class", "primary")
        self.compare_btn.setCursor(Qt.PointingHandCursor)
        self.compare_btn.setFixedWidth(260)
        self.compare_btn.setStyleSheet("""
            QPushButton {
                font-size: 15px;
                font-weight: 700;
                padding: 13px 28px;
                border-radius: 8px;
            }
            QPushButton:disabled {
                background-color: #1e293b;
                color: #475569;
                border: 1px solid #334155;
            }
        """)
        self.compare_btn.setEnabled(False)
        self.compare_btn.clicked.connect(self._on_start_compare)
        action_col.addWidget(self.compare_btn, alignment=Qt.AlignCenter)

        center_layout.addLayout(action_col)

        main_layout.addWidget(center_widget, 1)

    def set_document(self, file_path: str):
        self.file_path = file_path
        path = Path(file_path)
        self.doc_chip.setText(f"📄 {path.name}")
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
