"""
Local Standards & Engineering Knowledge Base View for SpecGuard.
Allows viewing, inspecting, and managing machine-readable rules across domains.
"""

from typing import List, Dict, Any
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QTextEdit
)
from specguard.core.config import STANDARDS_DIR
from specguard.analyzers.standards import StandardsKnowledgeBase


class StandardsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_rules: List[Dict[str, Any]] = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        # Header
        title = QLabel("Local Engineering Standards & Rules Knowledge Base")
        title.setProperty("class", "heading1")
        subtitle = QLabel("Machine-readable JSON/YAML standards evaluated 100% offline. Scope restricted to installed rules.")
        subtitle.setProperty("class", "meta")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        # Domain selector
        sel_layout = QHBoxLayout()
        lbl = QLabel("Filter by Domain:")
        lbl.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        sel_layout.addWidget(lbl)

        self.domain_combo = QComboBox()
        self.domain_combo.addItems(["Mechanical", "Electrical", "Chemical"])
        self.domain_combo.currentTextChanged.connect(self._load_rules)
        sel_layout.addWidget(self.domain_combo)
        sel_layout.addStretch()
        layout.addLayout(sel_layout)

        # Table of rules
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Rule ID", "Severity", "Parameter", "Operator", "Target Value / Set", "Reference Standard"
        ])
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_rule_selected)
        layout.addWidget(self.table, 3)

        # Rule detail
        detail_frame = QFrame()
        detail_frame.setProperty("class", "panel")
        df_layout = QVBoxLayout(detail_frame)
        self.rule_detail_lbl = QLabel("Select a rule above to inspect its engineering constraints.")
        self.rule_detail_lbl.setWordWrap(True)
        self.rule_detail_lbl.setStyleSheet("color: #cbd5e1; font-size: 13px;")
        df_layout.addWidget(self.rule_detail_lbl)
        layout.addWidget(detail_frame, 1)

        self._load_rules("Mechanical")

    def _load_rules(self, domain_name: str):
        rules = StandardsKnowledgeBase.load_rules_for_domain(domain_name.lower())
        self.current_rules = rules
        self.table.setRowCount(len(rules))

        for row_idx, r in enumerate(rules):
            self.table.setItem(row_idx, 0, QTableWidgetItem(r.get("rule_id", "-")))
            self.table.setItem(row_idx, 1, QTableWidgetItem(r.get("severity", "Medium")))
            self.table.setItem(row_idx, 2, QTableWidgetItem(r.get("parameter", "-")))
            self.table.setItem(row_idx, 3, QTableWidgetItem(r.get("operator", "-")))
            val_str = str(r.get("allowed_values") or r.get("max_value") or r.get("expected_value") or r.get("allowed_range") or "")
            unit = r.get("unit", "")
            self.table.setItem(row_idx, 4, QTableWidgetItem(f"{val_str} {unit}".strip()))
            self.table.setItem(row_idx, 5, QTableWidgetItem(r.get("reference", r.get("_standard_name", "-"))))

    def _on_rule_selected(self):
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            return
        row = sel[0].row()
        if 0 <= row < len(self.current_rules):
            r = self.current_rules[row]
            self.rule_detail_lbl.setText(
                f"Rule [{r.get('rule_id')}]: {r.get('description')}\n\n"
                f"Standard Source: {r.get('reference', r.get('_standard_name', '-'))}\n"
                f"Evaluation: Parameter '{r.get('parameter')}' must satisfy operator '{r.get('operator')}'."
            )
