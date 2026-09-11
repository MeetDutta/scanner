"""
Modern High-Precision Engineering CAD / Verification Portal Theme for SpecGuard.
Balances official authoritative engineering aesthetics with clean, premium modern UI:
- Primary Header: Deep Midnight Slate (#0b1329, #0f172a) with subtle accent border
- Canvas Background: Clean Off-White / Pale Slate (#f8fafc)
- Surface Cards: Crisp White (#ffffff) with refined 1px border (#e2e8f0) and subtle radius (8px)
- Primary Accent: Precision Sky/Ocean Blue (#0284c7, #0369a1)
- Secondary Accent: Industrial Amber / Safety Orange (#f97316)
- Typography: High-legibility system sans (-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", sans-serif)
- Severity Palette: Modern high-contrast pill badges
"""

GOVERNMENT_THEME_QSS = """
/* Base Application & Window */
QMainWindow {
    background-color: #f8fafc;
}

QWidget {
    color: #0f172a;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", Helvetica, Arial, sans-serif;
    font-size: 13px;
}

QLabel {
    background-color: transparent;
    color: #0f172a;
}

/* Formal Top Header Banner */
#gov_header_banner {
    background-color: #0b1329;
    border-bottom: 2px solid #1e293b;
    padding: 12px 28px;
}

#gov_header_banner QLabel {
    background-color: transparent;
    border: none;
}

#gov_brand_title {
    font-size: 20px;
    font-weight: 900;
    color: #ffffff;
    letter-spacing: 1.5px;
    background-color: transparent;
}

#gov_brand_sub {
    font-size: 12px;
    font-weight: 500;
    color: #94a3b8;
    letter-spacing: 0.5px;
    background-color: transparent;
}

/* Segmented Workflow Step Navigator Strip */
#workflow_strip {
    background-color: #ffffff;
    border-bottom: 1px solid #e2e8f0;
    padding: 8px 28px;
}

#workflow_strip QLabel {
    background-color: transparent;
}

#workflow_strip QPushButton,
.stage_step_btn {
    border: 1px solid transparent;
    background-color: transparent;
    padding: 7px 18px;
    border-radius: 6px;
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 0.5px;
    color: #64748b;
}

#workflow_strip QPushButton:hover,
.stage_step_btn:hover {
    background-color: #f1f5f9;
    color: #0f172a;
}

#workflow_strip QPushButton:disabled,
.stage_step_btn:disabled {
    color: #cbd5e1;
    background-color: transparent;
}

#workflow_strip QPushButton[active="true"],
.stage_step_active {
    background-color: #0284c7;
    color: #ffffff;
    font-weight: 800;
    border: 1px solid #0284c7;
}

#workflow_strip QPushButton[active="true"]:hover,
.stage_step_active:hover {
    background-color: #0369a1;
    border-color: #0369a1;
}

#workflow_strip QPushButton[done="true"],
.stage_step_done {
    background-color: #f0f9ff;
    color: #0284c7;
    border: 1px solid #bae6fd;
    font-weight: 700;
}

#workflow_strip QPushButton[done="true"]:hover,
.stage_step_done:hover {
    background-color: #e0f2fe;
    border-color: #7dd3fc;
}

/* Modern Surface Panels & Cards */
QFrame.gov_panel {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 24px;
}

QFrame.gov_box {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
}

/* Headings */
QLabel.gov_h1 {
    font-size: 18px;
    font-weight: 900;
    color: #0f172a;
    letter-spacing: 0.5px;
}

QLabel.gov_h2 {
    font-size: 15px;
    font-weight: 800;
    color: #1e293b;
}

QLabel.gov_meta {
    font-size: 12px;
    color: #64748b;
    line-height: 1.4;
}

/* Modern Industrial Buttons */
QPushButton.gov_btn_primary {
    background-color: #0284c7;
    color: #ffffff;
    border: 1px solid #0284c7;
    border-radius: 6px;
    padding: 9px 20px;
    font-weight: 800;
    font-size: 12px;
    letter-spacing: 0.5px;
}

QPushButton.gov_btn_primary:hover {
    background-color: #0369a1;
    border-color: #0369a1;
}

QPushButton.gov_btn_primary:pressed {
    background-color: #0c4a6e;
    border-color: #0c4a6e;
}

QPushButton.gov_btn_primary:disabled {
    background-color: #cbd5e1;
    color: #94a3b8;
    border-color: #cbd5e1;
}

QPushButton.gov_btn_secondary {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 700;
    font-size: 12px;
}

QPushButton.gov_btn_secondary:hover {
    background-color: #f8fafc;
    border-color: #94a3b8;
    color: #0f172a;
}

QPushButton.gov_btn_secondary:pressed {
    background-color: #f1f5f9;
}

QPushButton.gov_btn_danger {
    background-color: #ffffff;
    color: #b91c1c;
    border: 1px solid #fca5a5;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 700;
    font-size: 12px;
}

QPushButton.gov_btn_danger:hover {
    background-color: #fee2e2;
    border-color: #ef4444;
}

/* Drag & Drop Target Zone */
#gov_drop_zone {
    background-color: #ffffff;
    border: 2px dashed #cbd5e1;
    border-radius: 10px;
}

#gov_drop_zone:hover {
    border-color: #0284c7;
    background-color: #f0f9ff;
}

#gov_drop_zone QLabel {
    background-color: transparent;
    border: none;
}

/* Domain Mode Selection Cards */
QFrame.gov_mode_card {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 20px;
}

QFrame.gov_mode_card:hover {
    border-color: #0284c7;
    background-color: #f8fafc;
}

/* Severity Pill Badges */
QLabel.badge_critical {
    background-color: #fee2e2;
    color: #991b1b;
    border: 1px solid #fca5a5;
    border-radius: 12px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.5px;
}

QLabel.badge_high {
    background-color: #ffedd5;
    color: #9a3412;
    border: 1px solid #fdba74;
    border-radius: 12px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.5px;
}

QLabel.badge_medium {
    background-color: #fef3c7;
    color: #92400e;
    border: 1px solid #fde047;
    border-radius: 12px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.5px;
}

QLabel.badge_low {
    background-color: #dbeafe;
    color: #1e40af;
    border: 1px solid #93c5fd;
    border-radius: 12px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.5px;
}

QLabel.badge_info {
    background-color: #f1f5f9;
    color: #475569;
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.5px;
}

/* Formal Finding Detail Panel */
#gov_detail_panel {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
}

/* Progress Bar */
QProgressBar {
    background-color: #e2e8f0;
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #0284c7;
    border-radius: 4px;
}

/* Custom Clean Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #f8fafc;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #cbd5e1;
    min-height: 24px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
