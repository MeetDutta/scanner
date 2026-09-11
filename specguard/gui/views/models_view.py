"""
Local AI Model Management View for SpecGuard.
Dynamically displays registered ML model checkpoints, ONNX graphs, versioning,
cryptographic SHA-256 integrity, and activation controls.
Strictly offline: Zero automatic internet downloads.
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QMessageBox, QDialog,
    QTextEdit, QAbstractItemView
)
from PySide6.QtCore import Qt
from specguard.models.registry import ModelRegistry
from specguard.core.config import MODELS_DIR


class ModelDetailsDialog(QDialog):
    """Inspects detailed metadata for a registered model."""
    def __init__(self, model_data: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Model Inspection: {model_data.get('model_id', 'Unknown')}")
        self.resize(700, 520)
        layout = QVBoxLayout(self)

        info_box = QTextEdit()
        info_box.setReadOnly(True)
        info_box.setProperty("class", "code-view")

        import json
        info_box.setText(json.dumps(model_data, indent=2))
        layout.addWidget(info_box)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_box.addWidget(close_btn)
        layout.addLayout(btn_box)


class ModelsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.registry = ModelRegistry()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)

        # Header
        title = QLabel("Local AI Models & Service Management")
        title.setProperty("class", "heading1")
        subtitle = QLabel("Dynamic Offline Model Registry: PyTorch checkpoints, ONNX graphs, cryptographic hashes, and lifecycle state.")
        subtitle.setProperty("class", "meta")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        # Action bar
        action_bar = QHBoxLayout()
        self.activate_btn = QPushButton("Activate Selected")
        self.activate_btn.setProperty("class", "primary")
        self.activate_btn.clicked.connect(self.activate_selected)

        self.deactivate_btn = QPushButton("Deactivate Selected")
        self.deactivate_btn.clicked.connect(self.deactivate_selected)

        self.verify_hash_btn = QPushButton("Verify SHA-256 Hash")
        self.verify_hash_btn.clicked.connect(self.verify_selected_hash)

        self.inspect_btn = QPushButton("Inspect Details")
        self.inspect_btn.clicked.connect(self.inspect_selected)

        self.refresh_btn = QPushButton("Scan & Refresh")
        self.refresh_btn.clicked.connect(self.refresh_table)

        action_bar.addWidget(self.activate_btn)
        action_bar.addWidget(self.deactivate_btn)
        action_bar.addWidget(self.verify_hash_btn)
        action_bar.addWidget(self.inspect_btn)
        action_bar.addWidget(self.refresh_btn)
        action_bar.addStretch()
        layout.addLayout(action_bar)

        # Models Table
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "Model ID", "Task", "Domain", "Version", "Dataset",
            "Training Run", "Framework", "Architecture", "Status",
            "SHA-256 Integrity", "ONNX Parity"
        ])
        for col in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        # Security Notice Panel
        info_panel = QFrame()
        info_panel.setProperty("class", "panel")
        ip_layout = QVBoxLayout(info_panel)
        ip_lbl = QLabel(
            "Security & Model Integrity Notice:\n"
            "SpecGuard operates 100% offline with zero cloud API dependencies. "
            "All model checkpoints are cryptographically hashed using SHA-256. "
            "Corrupted or modified model weights are blocked from activation automatically. "
            "When deep learning weights are inactive or unavailable, deterministic engineering rules execute as verified local fallbacks."
        )
        ip_lbl.setWordWrap(True)
        ip_lbl.setStyleSheet("color: #94a3b8; font-size: 12px; line-height: 1.4;")
        ip_layout.addWidget(ip_lbl)
        layout.addWidget(info_panel)

        self.refresh_table()

    def _get_selected_model_id(self) -> str:
        row = self.table.currentRow()
        if row >= 0:
            item = self.table.item(row, 0)
            if item:
                return item.text()
        return ""

    def refresh_table(self):
        self.registry.scan_and_sync_artifacts()
        models = self.registry.list_models()

        self.table.setRowCount(len(models))
        for r_idx, m in enumerate(models):
            self.table.setItem(r_idx, 0, QTableWidgetItem(m.get("model_id", "")))
            self.table.setItem(r_idx, 1, QTableWidgetItem(m.get("task", "")))
            self.table.setItem(r_idx, 2, QTableWidgetItem(m.get("domain", "")))
            self.table.setItem(r_idx, 3, QTableWidgetItem(m.get("version", "")))
            self.table.setItem(r_idx, 4, QTableWidgetItem(m.get("dataset_version", "")))
            self.table.setItem(r_idx, 5, QTableWidgetItem(m.get("training_run_id", "")))
            self.table.setItem(r_idx, 6, QTableWidgetItem(m.get("framework", "")))
            self.table.setItem(r_idx, 7, QTableWidgetItem(m.get("architecture", "")))

            # Status
            status = m.get("status", "INACTIVE")
            status_item = QTableWidgetItem(status)
            status_item.setForeground(Qt.green if status == "ACTIVE" else Qt.gray)
            status_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r_idx, 8, status_item)

            # Integrity
            sha = m.get("sha256", "")
            sha_disp = f"✓ {sha[:8]}..." if sha and sha != "NOT_STORED" else "None"
            sha_item = QTableWidgetItem(sha_disp)
            sha_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r_idx, 9, sha_item)

            # ONNX Parity
            parity = m.get("parity_verified")
            if parity is True:
                diff = m.get("parity_max_diff", 0.0)
                p_text = f"PASS (Δ {diff:.1e})" if diff is not None else "PASS"
                p_item = QTableWidgetItem(p_text)
                p_item.setForeground(Qt.green)
            elif parity is False and m.get("onnx_path"):
                p_item = QTableWidgetItem("FAIL")
                p_item.setForeground(Qt.red)
            else:
                p_item = QTableWidgetItem("N/A")
                p_item.setForeground(Qt.gray)
            p_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r_idx, 10, p_item)

    def activate_selected(self):
        m_id = self._get_selected_model_id()
        if not m_id:
            QMessageBox.information(self, "Select Model", "Please select a model row to activate.")
            return
        success = self.registry.activate_model(m_id)
        if success:
            QMessageBox.information(self, "Activated", f"Model {m_id} is now ACTIVE.")
            self.refresh_table()
        else:
            QMessageBox.critical(self, "Activation Failed", f"Could not activate {m_id}. Integrity check failed or file missing.")

    def deactivate_selected(self):
        m_id = self._get_selected_model_id()
        if not m_id:
            QMessageBox.information(self, "Select Model", "Please select a model row to deactivate.")
            return
        self.registry.deactivate_model(m_id)
        QMessageBox.information(self, "Deactivated", f"Model {m_id} deactivated.")
        self.refresh_table()

    def verify_selected_hash(self):
        m_id = self._get_selected_model_id()
        if not m_id:
            QMessageBox.information(self, "Select Model", "Please select a model row to verify.")
            return
        res = self.registry.verify_model_hash(m_id)
        if res.get("valid"):
            QMessageBox.information(
                self, "SHA-256 Validated",
                f"Model: {m_id}\n\n"
                f"File: {res.get('file_path')}\n"
                f"SHA-256: {res.get('calculated_sha256')}\n\n"
                f"Cryptographic integrity verified."
            )
        else:
            QMessageBox.warning(
                self, "Integrity Check Failed",
                f"Model: {m_id}\n\n"
                f"Reason: {res.get('reason')}\n"
                f"Expected: {res.get('expected_sha256')}\n"
                f"Found: {res.get('calculated_sha256')}"
            )

    def inspect_selected(self):
        m_id = self._get_selected_model_id()
        if not m_id:
            QMessageBox.information(self, "Select Model", "Please select a model row to inspect.")
            return
        model_data = self.registry.get_model(m_id)
        if model_data:
            dlg = ModelDetailsDialog(model_data, self)
            dlg.exec()
