"""
Dashboard View for SpecGuard.
Displays high-level KPI cards, issue breakdown, and recent document analysis sessions.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton
)
from PySide6.QtCore import Qt, Signal
from specguard.storage.database import DatabaseManager
from specguard.storage.repositories import SessionRepository


class DashboardView(QWidget):
    open_upload_requested = Signal()
    open_session_requested = Signal(str)

    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.session_repo = SessionRepository(db)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        # Header
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Engineering Quality & Standards Dashboard")
        title.setProperty("class", "heading1")
        subtitle = QLabel("100% Local Compliance Analysis | Mechanical, Chemical, Electrical Domains")
        subtitle.setProperty("class", "meta")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        analyze_btn = QPushButton("+ New Document Analysis")
        analyze_btn.setProperty("class", "primary")
        analyze_btn.clicked.connect(self.open_upload_requested.emit)
        header_layout.addWidget(analyze_btn)
        layout.addLayout(header_layout)

        # KPI Stats Grid
        self.stats_layout = QHBoxLayout()
        self.stats_layout.setSpacing(16)
        layout.addLayout(self.stats_layout)

        # Recent Sessions Section
        recent_label = QLabel("Recent Analysis Sessions")
        recent_label.setProperty("class", "heading2")
        layout.addWidget(recent_label)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Session ID", "Document", "Domain", "Total Findings", "Critical", "High", "Analyzed At"
        ])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.doubleClicked.connect(self._on_row_double_click)
        layout.addWidget(self.table)

        self.refresh_data()

    def _create_card(self, title: str, count: int, color: str) -> QFrame:
        card = QFrame()
        card.setProperty("class", "panel")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 12)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 600;")
        lbl_num = QLabel(str(count))
        lbl_num.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: 700; margin-top: 4px;")

        card_layout.addWidget(lbl_title)
        card_layout.addWidget(lbl_num)
        return card

    def refresh_data(self):
        # Clear stats
        while self.stats_layout.count():
            item = self.stats_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        stats = self.session_repo.get_summary_statistics()
        self.stats_layout.addWidget(self._create_card("Documents Analyzed", stats.get("total_docs", 0), "#38bdf8"))
        self.stats_layout.addWidget(self._create_card("Issues Detected", stats.get("total_findings", 0), "#f8fafc"))
        self.stats_layout.addWidget(self._create_card("Critical Issues", stats.get("total_critical", 0), "#ef4444"))
        self.stats_layout.addWidget(self._create_card("High Deviations", stats.get("total_high", 0), "#f97316"))
        self.stats_layout.addWidget(self._create_card("Medium Issues", stats.get("total_medium", 0), "#eab308"))

        # Populate recent sessions
        sessions = self.session_repo.get_recent_sessions(limit=12)
        self.table.setRowCount(len(sessions))
        for row_idx, s in enumerate(sessions):
            self.table.setItem(row_idx, 0, QTableWidgetItem(s["session_id"]))
            self.table.setItem(row_idx, 1, QTableWidgetItem(s.get("filename", "Document")))
            self.table.setItem(row_idx, 2, QTableWidgetItem(s["domain"].title()))
            self.table.setItem(row_idx, 3, QTableWidgetItem(str(s["findings_count"])))
            self.table.setItem(row_idx, 4, QTableWidgetItem(str(s["critical_count"])))
            self.table.setItem(row_idx, 5, QTableWidgetItem(str(s["high_count"])))
            self.table.setItem(row_idx, 6, QTableWidgetItem(str(s["start_time"])[:19]))

    def _on_row_double_click(self, index):
        row = index.row()
        item = self.table.item(row, 0)
        if item:
            self.open_session_requested.emit(item.text())
