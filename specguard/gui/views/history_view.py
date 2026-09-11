"""
Document Comparison Repository & History View for SpecGuard.
Enables offline search, zero-inference session reopening, version-to-version comparison diffing,
and local .sgr repository backup and restore.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QFrame,
    QMessageBox, QFileDialog, QDialog, QSplitter, QCheckBox
)
from PySide6.QtCore import Qt, Signal

from specguard.repository.manager import RepositoryManager
from specguard.repository.search import RepositorySearchEngine
from specguard.repository.diff_engine import VersionDiffEngine
from specguard.repository.backup import RepositoryBackupEngine
from specguard.core.models import DocumentModel, Finding
from specguard.core.document_parser import DocumentParser


class VersionDiffDialog(QDialog):
    """Side-by-side version comparison modal showing findings diff (new vs resolved)."""
    def __init__(self, diff, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Version Diff: {diff.comparison_a_id} vs {diff.comparison_b_id}")
        self.resize(800, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header summary
        header = QLabel(
            f"Document: {diff.document_filename}\n"
            f"Model A ({diff.comparison_a_id}): {diff.model_a}  ⟶  Model B ({diff.comparison_b_id}): {diff.model_b}\n"
            f"Differential: +{diff.new_findings_count} New Findings | -{diff.resolved_findings_count} Resolved | {diff.persistent_findings_count} Persistent"
        )
        header.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")
        layout.addWidget(header)

        # Diff Table
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Status", "Finding ID", "Severity", "Location", "Explanation"])
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        table.setRowCount(len(diff.diff_items))

        for r_idx, item in enumerate(diff.diff_items):
            status_item = QTableWidgetItem(item.status)
            if item.status == "NEW":
                status_item.setForeground(Qt.red)
            elif item.status == "RESOLVED":
                status_item.setForeground(Qt.green)
            else:
                status_item.setForeground(Qt.yellow)

            table.setItem(r_idx, 0, status_item)
            table.setItem(r_idx, 1, QTableWidgetItem(item.finding_id))
            table.setItem(r_idx, 2, QTableWidgetItem(item.severity))
            table.setItem(r_idx, 3, QTableWidgetItem(item.location))
            table.setItem(r_idx, 4, QTableWidgetItem(item.explanation))

        layout.addWidget(table)

        btn_close = QPushButton("Close")
        btn_close.setProperty("class", "secondary")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)


class HistoryView(QWidget):
    reopen_comparison_requested = Signal(object, list, str) # (doc, findings, session_id)
    reanalyze_requested = Signal(str, str, list, list)

    def __init__(self, repo_manager: Optional[RepositoryManager] = None, parent=None):
        super().__init__(parent)
        self.repo_manager = repo_manager or RepositoryManager()
        self.search_engine = RepositorySearchEngine(self.repo_manager.db)
        self.diff_engine = VersionDiffEngine(self.repo_manager)
        self.selected_comparison_id: Optional[str] = None
        self.current_comparisons: List[Dict[str, Any]] = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        top_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Document Comparison Repository & Historical Archive")
        title.setProperty("class", "heading1")
        subtitle = QLabel("Immutable historical records of every engineering document comparison | 100% Offline Search")
        subtitle.setProperty("class", "meta")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        top_row.addLayout(title_box)
        top_row.addStretch()

        btn_backup = QPushButton("📦 Backup Repository (.sgr)")
        btn_backup.setProperty("class", "secondary")
        btn_backup.clicked.connect(self._backup_repository)
        top_row.addWidget(btn_backup)

        btn_restore = QPushButton("📥 Restore Backup")
        btn_restore.setProperty("class", "secondary")
        btn_restore.clicked.connect(self._restore_repository)
        top_row.addWidget(btn_restore)

        layout.addLayout(top_row)

        # Search and Filter Toolbar
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search comparisons, document IDs, filenames, parameters...")
        self.search_input.textChanged.connect(self._execute_search)
        filter_bar.addWidget(self.search_input, 3)

        self.domain_filter = QComboBox()
        self.domain_filter.addItems(["All Domains", "Mechanical", "Electrical", "Chemical"])
        self.domain_filter.currentTextChanged.connect(self._execute_search)
        filter_bar.addWidget(self.domain_filter, 1)

        self.cb_critical_only = QCheckBox("Critical Findings Only")
        self.cb_critical_only.stateChanged.connect(self._execute_search)
        filter_bar.addWidget(self.cb_critical_only)

        layout.addLayout(filter_bar)

        # Splitter: Table on top/left, Details on right
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #334155; width: 4px; }")

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Comparison ID", "Document ID", "Filename", "Domain", "Total", "Crit", "High", "Completed At"
        ])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        splitter.addWidget(self.table)

        # Right Detail Pane
        detail_frame = QFrame()
        detail_frame.setProperty("class", "panel")
        detail_layout = QVBoxLayout(detail_frame)
        detail_layout.setSpacing(12)

        self.lbl_detail_title = QLabel("Select a comparison to inspect audit record.")
        self.lbl_detail_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #38bdf8;")
        detail_layout.addWidget(self.lbl_detail_title)

        self.lbl_detail_meta = QLabel("")
        self.lbl_detail_meta.setWordWrap(True)
        self.lbl_detail_meta.setStyleSheet("color: #cbd5e1; font-size: 12px; line-height: 1.4;")
        detail_layout.addWidget(self.lbl_detail_meta)

        detail_layout.addStretch()

        # Action Buttons for Selected Comparison
        self.btn_reopen = QPushButton("📂 Reopen Analysis (Instant / 0 Inference)")
        self.btn_reopen.setProperty("class", "primary")
        self.btn_reopen.setEnabled(False)
        self.btn_reopen.clicked.connect(self._reopen_selected)
        detail_layout.addWidget(self.btn_reopen)

        self.btn_reanalyze = QPushButton("🔄 Re-analyze Document (New CMP-ID)")
        self.btn_reanalyze.setProperty("class", "secondary")
        self.btn_reanalyze.setEnabled(False)
        self.btn_reanalyze.clicked.connect(self._reanalyze_selected)
        detail_layout.addWidget(self.btn_reanalyze)

        self.btn_diff = QPushButton("⚖️ Compare with Another Version")
        self.btn_diff.setProperty("class", "secondary")
        self.btn_diff.setEnabled(False)
        self.btn_diff.clicked.connect(self._compare_versions_dialog)
        detail_layout.addWidget(self.btn_diff)

        self.btn_delete = QPushButton("🗑️ Delete Comparison")
        self.btn_delete.setStyleSheet("background-color: #7f1d1d; color: white; border-radius: 6px; padding: 6px;")
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._delete_selected)
        detail_layout.addWidget(self.btn_delete)

        splitter.addWidget(detail_frame)
        splitter.setSizes([750, 350])
        layout.addWidget(splitter)
        self.refresh_data()

    def refresh_data(self):
        """Refreshes repository comparison records."""
        self._execute_search()

    def _execute_search(self):
        query = self.search_input.text()
        dom = self.domain_filter.currentText()
        crit_only = self.cb_critical_only.isChecked()

        results = self.search_engine.search(
            query=query,
            domain=dom if dom != "All Domains" else None,
            critical_only=crit_only
        )
        self.current_comparisons = results
        self.table.setRowCount(len(results))

        for r_idx, c in enumerate(results):
            self.table.setItem(r_idx, 0, QTableWidgetItem(c["comparison_id"]))
            self.table.setItem(r_idx, 1, QTableWidgetItem(c["document_id"]))
            self.table.setItem(r_idx, 2, QTableWidgetItem(c["document_filename"]))
            self.table.setItem(r_idx, 3, QTableWidgetItem(c["domain"]))
            self.table.setItem(r_idx, 4, QTableWidgetItem(str(c["total_findings"])))
            self.table.setItem(r_idx, 5, QTableWidgetItem(str(c["critical_count"])))
            self.table.setItem(r_idx, 6, QTableWidgetItem(str(c["high_count"])))
            self.table.setItem(r_idx, 7, QTableWidgetItem(str(c["analysis_completed_at"])[:19]))

    def _on_selection_changed(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            self.selected_comparison_id = None
            self.btn_reopen.setEnabled(False)
            self.btn_reanalyze.setEnabled(False)
            self.btn_diff.setEnabled(False)
            self.btn_delete.setEnabled(False)
            return

        row = rows[0].row()
        if 0 <= row < len(self.current_comparisons):
            c = self.current_comparisons[row]
            self.selected_comparison_id = c["comparison_id"]
            self.lbl_detail_title.setText(f"{c['comparison_id']} — {c['document_filename']}")
            self.lbl_detail_meta.setText(
                f"Document ID: {c['document_id']} (Rev {c.get('revision_number', 1)})\n"
                f"Completed: {c['analysis_completed_at'][:19]}\n"
                f"Duration: {c.get('duration_ms', 0)} ms\n"
                f"Domain: {c['domain']}\n"
                f"Model Version: {c.get('model_version', 'Deterministic')}\n"
                f"SHA-256: {c['document_sha256'][:16]}...\n\n"
                f"Findings Breakdown:\n"
                f"  • Critical: {c['critical_count']}\n"
                f"  • High: {c['high_count']}\n"
                f"  • Medium: {c['medium_count']}\n"
                f"  • Low: {c['low_count']}\n"
                f"  • Total: {c['total_findings']}"
            )
            self.btn_reopen.setEnabled(True)
            self.btn_reanalyze.setEnabled(True)
            self.btn_diff.setEnabled(len(self.current_comparisons) > 1)
            self.btn_delete.setEnabled(True)

    def _reopen_selected(self):
        """Zero-inference restore: Re-loads findings and document without running ML inference."""
        if not self.selected_comparison_id:
            return

        findings = self.repo_manager.get_comparison_findings(self.selected_comparison_id)
        record = self.repo_manager.get_comparison_record(self.selected_comparison_id)
        if not record:
            return

        # Find document on disk or in repository
        repo_doc_dir = self.repo_manager.docs_dir / record.document_id / "original"
        doc_path = None
        if repo_doc_dir.exists():
            for f in repo_doc_dir.iterdir():
                doc_path = str(f)
                break

        if not doc_path:
            QMessageBox.warning(self, "Document Not Stored", "Original document was not stored locally. Displaying findings only.")
            return

        doc_model = DocumentParser.parse_file(doc_path)
        self.reopen_comparison_requested.emit(doc_model, findings, record.comparison_id)

    def _reanalyze_selected(self):
        """Runs a new analysis with current models and rules, creating a NEW Comparison ID."""
        if not self.selected_comparison_id:
            return

        record = self.repo_manager.get_comparison_record(self.selected_comparison_id)
        if not record:
            return

        repo_doc_dir = self.repo_manager.docs_dir / record.document_id / "original"
        doc_path = None
        if repo_doc_dir.exists():
            for f in repo_doc_dir.iterdir():
                doc_path = str(f)
                break

        if not doc_path:
            QMessageBox.warning(self, "Document Missing", "Original document file is not found in repository.")
            return

        self.reanalyze_requested.emit(doc_path, record.domain.lower(), record.standards_used, [])

    def _compare_versions_dialog(self):
        """Opens version-to-version diffing against another comparison."""
        if not self.selected_comparison_id:
            return

        # Pick another comparison
        candidates = [c["comparison_id"] for c in self.current_comparisons if c["comparison_id"] != self.selected_comparison_id]
        if not candidates:
            QMessageBox.information(self, "Insufficient Comparisons", "Need at least two comparisons to compute version diff.")
            return

        other_id = candidates[0]
        try:
            diff = self.diff_engine.compare_sessions(self.selected_comparison_id, other_id)
            dlg = VersionDiffDialog(diff, self)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Diff Error", f"Failed comparing versions: {e}")

    def _backup_repository(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Repository Backup Archive", "specguard_backup.sgr", "SpecGuard Archive (*.sgr *.zip)")
        if path:
            try:
                out, sha, count = RepositoryBackupEngine.create_backup(self.repo_manager.repo_dir, path)
                QMessageBox.information(self, "Backup Complete", f"Repository backed up successfully ({count} files):\nSHA-256: {sha[:16]}...")
            except Exception as e:
                QMessageBox.critical(self, "Backup Error", f"Failed creating backup: {e}")

    def _restore_repository(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Repository Backup Archive", "", "SpecGuard Archive (*.sgr *.zip)")
        if path:
            confirm = QMessageBox.question(
                self, "Confirm Restore",
                "Restoring repository will merge or restore archived comparisons. Proceed?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm == QMessageBox.Yes:
                success, msg, _ = RepositoryBackupEngine.restore_backup(path, self.repo_manager.repo_dir)
                if success:
                    QMessageBox.information(self, "Restore Successful", msg)
                    self._execute_search()
                else:
                    QMessageBox.critical(self, "Restore Error", msg)

    def _delete_selected(self):
        if not self.selected_comparison_id:
            return

        confirm = QMessageBox.question(
            self, "Delete Comparison Archive?",
            f"Are you sure you want to permanently delete {self.selected_comparison_id}?\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.repo_manager.delete_comparison(self.selected_comparison_id)
            self._execute_search()
