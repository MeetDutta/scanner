"""
Professional Technical CAD/Engineering Dark Theme for SpecGuard PySide6 GUI.
"""

DARK_THEME_QSS = """
QMainWindow, QWidget {
    background-color: #0f172a;
    color: #f8fafc;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

/* Navigation Sidebar */
#sidebar {
    background-color: #090d16;
    border-right: 1px solid #1e293b;
    min-width: 220px;
    max-width: 220px;
}

#sidebar QLabel#app_title {
    font-size: 18px;
    font-weight: 700;
    color: #38bdf8;
    padding: 16px 12px 4px 12px;
}

#sidebar QLabel#app_subtitle {
    font-size: 10px;
    color: #94a3b8;
    padding: 0 12px 16px 12px;
}

#sidebar QPushButton {
    text-align: left;
    padding: 10px 16px;
    margin: 2px 8px;
    border-radius: 6px;
    border: none;
    font-weight: 500;
    color: #cbd5e1;
    background-color: transparent;
}

#sidebar QPushButton:hover {
    background-color: #1e293b;
    color: #38bdf8;
}

#sidebar QPushButton:checked {
    background-color: #1e293b;
    color: #38bdf8;
    font-weight: 700;
    border-left: 3px solid #38bdf8;
}

/* Cards & Panels */
QFrame.panel {
    background-color: #1e293b;
    border-radius: 8px;
    border: 1px solid #334155;
    padding: 16px;
}

/* Headers */
QLabel.heading1 {
    font-size: 20px;
    font-weight: 700;
    color: #f8fafc;
    margin-bottom: 8px;
}

QLabel.heading2 {
    font-size: 15px;
    font-weight: 600;
    color: #cbd5e1;
    margin-top: 12px;
    margin-bottom: 4px;
}

QLabel.meta {
    font-size: 12px;
    color: #94a3b8;
}

/* Buttons */
QPushButton.primary {
    background-color: #0284c7;
    color: white;
    font-weight: 600;
    padding: 9px 20px;
    border-radius: 6px;
    border: none;
}

QPushButton.primary:hover {
    background-color: #0369a1;
}

QPushButton.secondary {
    background-color: #334155;
    color: #f8fafc;
    padding: 8px 16px;
    border-radius: 6px;
    border: 1px solid #475569;
}

QPushButton.secondary:hover {
    background-color: #475569;
}

/* Inputs & Combos */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 7px 10px;
    color: #f8fafc;
}

QLineEdit:focus, QComboBox:focus {
    border: 1px solid #38bdf8;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

/* Tables */
QTableWidget {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    gridline-color: #334155;
    selection-background-color: #0369a1;
    selection-color: white;
}

QHeaderView::section {
    background-color: #0f172a;
    color: #94a3b8;
    padding: 8px 6px;
    border: none;
    border-bottom: 1px solid #334155;
    font-weight: 600;
    font-size: 12px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #0f172a;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #334155;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Progress bar */
QProgressBar {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    text-align: center;
    color: #f8fafc;
    height: 18px;
}

QProgressBar::chunk {
    background-color: #0284c7;
    border-radius: 5px;
}

/* Severity Badges */
QLabel.badge_critical {
    background-color: #ef4444;
    color: white;
    font-weight: bold;
    font-size: 11px;
    padding: 3px 8px;
    border-radius: 4px;
}

QLabel.badge_high {
    background-color: #f97316;
    color: white;
    font-weight: bold;
    font-size: 11px;
    padding: 3px 8px;
    border-radius: 4px;
}

QLabel.badge_medium {
    background-color: #eab308;
    color: black;
    font-weight: bold;
    font-size: 11px;
    padding: 3px 8px;
    border-radius: 4px;
}

QLabel.badge_low {
    background-color: #3b82f6;
    color: white;
    font-weight: bold;
    font-size: 11px;
    padding: 3px 8px;
    border-radius: 4px;
}

QLabel.badge_info {
    background-color: #64748b;
    color: white;
    font-weight: bold;
    font-size: 11px;
    padding: 3px 8px;
    border-radius: 4px;
}

/* Minimal 3-Stage Workflow Styling */
#top_header {
    background-color: #090d16;
    border-bottom: 1px solid #1e293b;
    padding: 12px 24px;
}

#brand_title {
    font-size: 20px;
    font-weight: 800;
    color: #38bdf8;
}

#brand_subtitle {
    font-size: 12px;
    color: #64748b;
    font-weight: 500;
}

/* Breadcrumb Steps */
.step_btn {
    border: none;
    background: transparent;
    padding: 6px 14px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 13px;
    color: #64748b;
}

.step_btn:disabled {
    color: #475569;
}

.step_btn_active {
    background-color: #0369a1;
    color: #f8fafc;
    font-weight: 700;
}

.step_btn_completed {
    background-color: #0f2e3e;
    color: #38bdf8;
}

/* Drop Zone */
#drop_zone {
    border: 2px dashed #334155;
    border-radius: 12px;
    background-color: #0b1120;
    padding: 48px;
}

#drop_zone:hover {
    border-color: #38bdf8;
    background-color: #0d172a;
}

/* Compact Document Card */
#doc_card {
    background-color: #111827;
    border: 1px solid #1f2937;
    border-radius: 10px;
    padding: 18px 24px;
}

/* Mode Selection Cards */
.mode_card {
    background-color: #111827;
    border: 2px solid #1f2937;
    border-radius: 12px;
    padding: 24px 20px;
    text-align: center;
}

.mode_card:hover {
    border-color: #475569;
    background-color: #131d33;
}

.mode_card_selected {
    border: 2px solid #38bdf8;
    background-color: #0c1c2e;
}

/* Finding Detail Panel */
#finding_detail_panel {
    background-color: #0e1526;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 18px;
}
"""

