"""
Master Deep Learning Training Center View for SpecGuard.
Enables end-to-end dataset ingestion, validation, PyTorch training execution,
evaluation metrics (including Critical Finding Recall), and ONNX export.
"""

from typing import List, Dict, Optional, Any
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, QFrame,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit, QFileDialog,
    QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal

from specguard.training.training_manager import TrainingManager
from specguard.training.hardware import HardwareProfile
from specguard.gui.views.annotation_view import AnnotationStudioWidget


class TrainingWorkerThread(QThread):
    progress_updated = Signal(int, int, float, float, float, float)
    training_finished = Signal(dict)
    training_failed = Signal(str)

    def __init__(self, manager: TrainingManager, task: str, domain: str, epochs: int, batch_size: int, lr: float, device: str, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.task = task
        self.domain = domain
        self.epochs = epochs
        self.batch_size = batch_size
        self.lr = lr
        self.device = device

    def run(self):
        try:
            result = self.manager.run_training_job(
                task_name=self.task,
                domain=self.domain,
                epochs=self.epochs,
                batch_size=self.batch_size,
                learning_rate=self.lr,
                device_str=self.device,
                progress_callback=self._callback
            )
            self.training_finished.emit(result)
        except Exception as e:
            self.training_failed.emit(str(e))

    def _callback(self, ep: int, total_ep: int, tr_loss: float, val_loss: float, acc: float, f1: float):
        self.progress_updated.emit(ep, total_ep, tr_loss, val_loss, acc, f1)


class TrainingView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = TrainingManager()
        self.worker: Optional[TrainingWorkerThread] = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header_box = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Deep Learning Training & Annotation Center")
        title.setProperty("class", "heading1")
        subtitle = QLabel("100% Offline PyTorch Model Training, Hardware Acceleration, and Research Evaluation")
        subtitle.setProperty("class", "meta")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_box.addLayout(title_box)
        header_box.addStretch()

        # Hardware Badge
        hw = self.manager.get_hardware_profile()
        hw_card = QFrame()
        hw_card.setStyleSheet("background-color: #064e3b; border: 1px solid #059669; border-radius: 6px; padding: 8px 12px;")
        hw_layout = QVBoxLayout(hw_card)
        hw_lbl = QLabel(f"⚡ Device: {hw.device.upper()} ({hw.device_name})")
        hw_lbl.setStyleSheet("color: #a7f3d0; font-weight: bold; font-size: 11px;")
        hw_desc = QLabel(f"RAM: {hw.ram_gb} GB | Recommended Batch: {hw.recommended_batch_size}")
        hw_desc.setStyleSheet("color: #d1fae5; font-size: 10px;")
        hw_layout.addWidget(hw_lbl)
        hw_layout.addWidget(hw_desc)
        header_box.addWidget(hw_card)

        layout.addLayout(header_box)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabWidget::pane { border: 1px solid #334155; background-color: #1e293b; border-radius: 8px; }")

        self.tab_dataset = self._create_dataset_tab()
        self.tab_annotation = AnnotationStudioWidget(self.manager.annotation_manager)
        self.tab_validator = self._create_validator_tab()
        self.tab_training = self._create_training_tab()
        self.tab_checkpoints = self._create_checkpoints_tab()

        self.tabs.addTab(self.tab_dataset, "📁 Datasets")
        self.tabs.addTab(self.tab_annotation, "✏️ Annotation Studio")
        self.tabs.addTab(self.tab_validator, "🩺 Health & Validation")
        self.tabs.addTab(self.tab_training, "🚀 Train Model")
        self.tabs.addTab(self.tab_checkpoints, "💾 Model Registry & Checkpoints")

        layout.addWidget(self.tabs)

    # Tab 1: Datasets
    def _create_dataset_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        top_row = QHBoxLayout()
        btn_import = QPushButton("+ Import Raw Engineering Document")
        btn_import.setProperty("class", "primary")
        btn_import.clicked.connect(self._import_document_dialog)
        top_row.addWidget(btn_import)

        self.import_domain_combo = QComboBox()
        self.import_domain_combo.addItems(["Mechanical", "Electrical", "Chemical"])
        top_row.addWidget(QLabel("Target Domain:"))
        top_row.addWidget(self.import_domain_combo)
        top_row.addStretch()

        layout.addLayout(top_row)

        self.doc_table = QTableWidget()
        self.doc_table.setColumnCount(5)
        self.doc_table.setHorizontalHeaderLabels(["Document ID", "Filename", "Domain", "Pages", "SHA-256 Hash"])
        self.doc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.doc_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self.doc_table)

        self._refresh_dataset_table()
        return w

    def _refresh_dataset_table(self):
        docs = self.manager.dataset_manager.list_processed_documents()
        self.doc_table.setRowCount(len(docs))
        for r_idx, d in enumerate(docs):
            self.doc_table.setItem(r_idx, 0, QTableWidgetItem(d.get("document_id", "-")))
            self.doc_table.setItem(r_idx, 1, QTableWidgetItem(d.get("filename", "-")))
            self.doc_table.setItem(r_idx, 2, QTableWidgetItem(d.get("domain", "").title()))
            self.doc_table.setItem(r_idx, 3, QTableWidgetItem(str(d.get("page_count", 1))))
            self.doc_table.setItem(r_idx, 4, QTableWidgetItem(d.get("sha256", "")[:12] + "..."))

    def _import_document_dialog(self):
        filter_str = "Engineering Documents (*.pdf *.docx *.xlsx *.txt *.png *.jpg);;All Files (*.*)"
        path, _ = QFileDialog.getOpenFileName(self, "Select Document to Import into Dataset", "", filter_str)
        if path:
            domain = self.import_domain_combo.currentText().lower()
            try:
                self.manager.dataset_manager.import_document(path, domain)
                QMessageBox.information(self, "Import Successful", f"Document imported and processed into {domain} dataset.")
                self._refresh_dataset_table()
            except Exception as e:
                QMessageBox.critical(self, "Import Error", f"Failed importing document: {e}")

    # Tab 3: Health & Validation
    def _create_validator_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        btn_run_val = QPushButton("🩺 Run Dataset Health & Leakage Check")
        btn_run_val.setProperty("class", "primary")
        btn_run_val.clicked.connect(self._run_health_check)
        layout.addWidget(btn_run_val, alignment=Qt.AlignLeft)

        self.val_report_text = QTextEdit()
        self.val_report_text.setReadOnly(True)
        self.val_report_text.setStyleSheet("background-color: #0f172a; border: 1px solid #334155; font-family: monospace; color: #a7f3d0; padding: 12px;")
        layout.addWidget(self.val_report_text)
        return w

    def _run_health_check(self):
        report = self.manager.validate_dataset()
        self.val_report_text.setText(report.summary_text())

    # Tab 4: Train Model
    def _create_training_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Config row
        cfg_frame = QFrame()
        cfg_frame.setProperty("class", "panel")
        cfg_layout = QHBoxLayout(cfg_frame)

        self.train_task_combo = QComboBox()
        self.train_task_combo.addItems(["Domain Classifier", "Engineering NER", "Logical Contradiction"])
        cfg_layout.addWidget(QLabel("Task:"))
        cfg_layout.addWidget(self.train_task_combo)

        self.train_domain_combo = QComboBox()
        self.train_domain_combo.addItems(["Mechanical", "Electrical", "Chemical"])
        cfg_layout.addWidget(QLabel("Domain:"))
        cfg_layout.addWidget(self.train_domain_combo)

        self.train_epochs = QSpinBox()
        self.train_epochs.setRange(1, 100)
        self.train_epochs.setValue(5)
        cfg_layout.addWidget(QLabel("Epochs:"))
        cfg_layout.addWidget(self.train_epochs)

        self.train_batch = QSpinBox()
        self.train_batch.setRange(1, 64)
        self.train_batch.setValue(4)
        cfg_layout.addWidget(QLabel("Batch Size:"))
        cfg_layout.addWidget(self.train_batch)

        self.train_lr = QDoubleSpinBox()
        self.train_lr.setRange(0.0001, 0.1)
        self.train_lr.setSingleStep(0.0005)
        self.train_lr.setValue(0.001)
        cfg_layout.addWidget(QLabel("Learning Rate:"))
        cfg_layout.addWidget(self.train_lr)

        layout.addWidget(cfg_frame)

        # Progress
        self.train_progress_bar = QProgressBar()
        self.train_progress_bar.setRange(0, 100)
        self.train_progress_bar.setValue(0)
        layout.addWidget(self.train_progress_bar)

        self.train_status_lbl = QLabel("Ready to start offline PyTorch training.")
        self.train_status_lbl.setStyleSheet("color: #38bdf8; font-weight: bold;")
        layout.addWidget(self.train_status_lbl)

        # Real Metrics Log
        self.train_log = QTextEdit()
        self.train_log.setReadOnly(True)
        self.train_log.setStyleSheet("background-color: #0f172a; border: 1px solid #334155; font-family: monospace; color: #cbd5e1; padding: 8px;")
        layout.addWidget(self.train_log)

        self.btn_start_train = QPushButton("🚀 Execute Real PyTorch Training")
        self.btn_start_train.setProperty("class", "primary")
        self.btn_start_train.clicked.connect(self._start_training)
        layout.addWidget(self.btn_start_train, alignment=Qt.AlignRight)

        return w

    def _start_training(self):
        task = self.train_task_combo.currentText().lower().replace(" ", "_")
        domain = self.train_domain_combo.currentText().lower()
        epochs = self.train_epochs.value()
        batch_size = self.train_batch.value()
        lr = self.train_lr.value()

        self.btn_start_train.setEnabled(False)
        self.train_progress_bar.setValue(0)
        self.train_status_lbl.setText("Training model in background (zero cloud connection)...")
        self.train_log.clear()

        self.worker = TrainingWorkerThread(
            manager=self.manager,
            task=task,
            domain=domain,
            epochs=epochs,
            batch_size=batch_size,
            lr=lr,
            device="auto"
        )
        self.worker.progress_updated.connect(self._on_epoch_update)
        self.worker.training_finished.connect(self._on_training_finished)
        self.worker.training_failed.connect(self._on_training_failed)
        self.worker.start()

    def _on_epoch_update(self, ep: int, total_ep: int, tr_loss: float, val_loss: float, acc: float, f1: float):
        pct = int((ep / total_ep) * 100)
        self.train_progress_bar.setValue(pct)
        msg = f"Epoch {ep}/{total_ep} — Train Loss: {tr_loss:.4f} | Val Loss: {val_loss:.4f} | Acc: {acc:.4f} | F1: {f1:.4f}"
        self.train_status_lbl.setText(msg)
        self.train_log.append(msg)

    def _on_training_finished(self, result: dict):
        self.btn_start_train.setEnabled(True)
        self.train_progress_bar.setValue(100)
        self.train_status_lbl.setText("Training completed successfully! Checkpoint saved.")
        self.train_log.append(f"\nFinal Best Metrics: {result.get('best_metrics')}\nSaved to: {result.get('checkpoint_path')}")
        self._refresh_checkpoints_table()

    def _on_training_failed(self, err: str):
        self.btn_start_train.setEnabled(True)
        self.train_status_lbl.setText(f"Training failed: {err}")
        self.train_log.append(f"Error: {err}")

    # Tab 5: Checkpoints & ONNX
    def _create_checkpoints_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        top_row = QHBoxLayout()
        lbl = QLabel("Saved Model Checkpoints & ONNX Artifacts")
        lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #f8fafc;")
        top_row.addWidget(lbl)
        top_row.addStretch()

        btn_refresh = QPushButton("Refresh List")
        btn_refresh.setProperty("class", "secondary")
        btn_refresh.clicked.connect(self._refresh_checkpoints_table)
        top_row.addWidget(btn_refresh)
        layout.addLayout(top_row)

        self.ckpt_table = QTableWidget()
        self.ckpt_table.setColumnCount(6)
        self.ckpt_table.setHorizontalHeaderLabels(["Model ID", "Task", "Domain", "F1 Score", "SHA-256", "Saved Date"])
        self.ckpt_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.ckpt_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.ckpt_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        layout.addWidget(self.ckpt_table)

        self._refresh_checkpoints_table()
        return w

    def _refresh_checkpoints_table(self):
        ckpts = self.manager.checkpoint_manager.list_checkpoints()
        self.ckpt_table.setRowCount(len(ckpts))
        for r_idx, c in enumerate(ckpts):
            self.ckpt_table.setItem(r_idx, 0, QTableWidgetItem(c.get("model_id", "-")))
            self.ckpt_table.setItem(r_idx, 1, QTableWidgetItem(c.get("task", "-").title()))
            self.ckpt_table.setItem(r_idx, 2, QTableWidgetItem(c.get("domain", "-").title()))
            f1_val = c.get("metrics", {}).get("f1_score", 0.0)
            self.ckpt_table.setItem(r_idx, 3, QTableWidgetItem(f"{f1_val:.4f}"))
            self.ckpt_table.setItem(r_idx, 4, QTableWidgetItem(c.get("sha256", "")[:12] + "..."))
            self.ckpt_table.setItem(r_idx, 5, QTableWidgetItem(str(c.get("created_at", ""))[:19]))
