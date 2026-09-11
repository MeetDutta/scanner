"""
Formal Government / Public-Sector Institutional Theme for SpecGuard.
Designed according to official engineering verification portal standards:
- Conservative, functional, accessible, high-contrast palette
- Primary: Deep Navy / Government Blue (#002b49, #0a2540)
- Background: Very Light Gray / Off-White (#f1f5f9, #f8fafc)
- Crisp rectangular borders (#cbd5e1, #94a3b8)
- Clean, readable typography (Arial, Noto Sans, sans-serif)
- Formal severity colors: Critical (Deep Red), High (Dark Orange), Medium (Dark Amber), Low (Government Blue), Info (Slate)
"""

GOVERNMENT_THEME_QSS = """
/* Base Application */
QMainWindow, QWidget {
    background-color: #f1f5f9;
    color: #0f172a;
    font-family: Arial, "Noto Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 13px;
}

/* Formal Header Banner */
#gov_header_banner {
    background-color: #002b49;
    border-bottom: 3px solid #b45309;
    padding: 10px 24px;
}

#gov_brand_title {
    font-size: 20px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: 1px;
}

#gov_brand_sub {
    font-size: 12px;
    font-weight: 500;
    color: #93c5fd;
    letter-spacing: 0.5px;
}

#gov_header_meta {
    font-size: 11px;
    font-weight: 600;
    color: #e2e8f0;
    background-color: #0f3b60;
    border: 1px solid #1e4e79;
    border-radius: 2px;
    padding: 4px 10px;
}

/* Workflow Stage Strip */
#workflow_strip {
    background-color: #ffffff;
    border-bottom: 1px solid #cbd5e1;
    padding: 6px 24px;
}

.stage_step_btn {
    border: none;
    background: transparent;
    padding: 8px 16px;
    border-radius: 0px;
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 0.5px;
    color: #64748b;
}

.stage_step_btn:disabled {
    color: #94a3b8;
}

.stage_step_active {
    background-color: #002b49;
    color: #ffffff;
    border-bottom: 3px solid #b45309;
}

.stage_step_done {
    background-color: #e2e8f0;
    color: #002b49;
}

/* Formal Panels and Frames */
QFrame.gov_panel {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 0px;
    padding: 24px;
}

QFrame.gov_box {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 0px;
}

/* Headings */
QLabel.gov_h1 {
    font-size: 18px;
    font-weight: 800;
    color: #002b49;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

QLabel.gov_instruction {
    font-size: 13px;
    color: #334155;
    margin-bottom: 8px;
}

/* Buttons */
QPushButton.gov_btn_primary {
    background-color: #002b49;
    color: #ffffff;
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 0.5px;
    padding: 10px 24px;
    border-radius: 2px;
    border: 1px solid #001f35;
}

QPushButton.gov_btn_primary:hover {
    background-color: #003e6b;
}

QPushButton.gov_btn_primary:disabled {
    background-color: #cbd5e1;
    color: #64748b;
    border: 1px solid #94a3b8;
}

QPushButton.gov_btn_secondary {
    background-color: #ffffff;
    color: #002b49;
    font-weight: 600;
    font-size: 12px;
    padding: 7px 16px;
    border-radius: 2px;
    border: 1px solid #94a3b8;
}

QPushButton.gov_btn_secondary:hover {
    background-color: #f1f5f9;
    border-color: #002b49;
}

/* Upload Drop Zone */
#gov_drop_zone {
    border: 2px dashed #94a3b8;
    border-radius: 0px;
    background-color: #f8fafc;
    padding: 36px;
}

#gov_drop_zone:hover {
    border-color: #002b49;
    background-color: #f0f7ff;
}

/* Selected Document Card */
#gov_doc_card {
    background-color: #ffffff;
    border: 1px solid #94a3b8;
    border-radius: 0px;
    padding: 16px 20px;
}

/* Mode Selection Cards */
.gov_mode_card {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 0px;
    padding: 20px 16px;
    text-align: center;
}

.gov_mode_card:hover {
    border-color: #002b49;
    background-color: #f8fafc;
}

.gov_mode_card_selected {
    border: 2px solid #002b49;
    background-color: #f0f7ff;
}

/* Severity Indicators (Formal & High Contrast) */
QLabel.badge_critical {
    background-color: #b91c1c;
    color: #ffffff;
    font-weight: 800;
    font-size: 11px;
    letter-spacing: 0.5px;
    padding: 3px 8px;
    border-radius: 2px;
}

QLabel.badge_high {
    background-color: #c2410c;
    color: #ffffff;
    font-weight: 800;
    font-size: 11px;
    letter-spacing: 0.5px;
    padding: 3px 8px;
    border-radius: 2px;
}

QLabel.badge_medium {
    background-color: #b45309;
    color: #ffffff;
    font-weight: 800;
    font-size: 11px;
    letter-spacing: 0.5px;
    padding: 3px 8px;
    border-radius: 2px;
}

QLabel.badge_low {
    background-color: #1e40af;
    color: #ffffff;
    font-weight: 800;
    font-size: 11px;
    letter-spacing: 0.5px;
    padding: 3px 8px;
    border-radius: 2px;
}

QLabel.badge_info {
    background-color: #475569;
    color: #ffffff;
    font-weight: 800;
    font-size: 11px;
    letter-spacing: 0.5px;
    padding: 3px 8px;
    border-radius: 2px;
}

/* Finding Detail Panel */
#gov_detail_panel {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 0px;
    padding: 16px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #e2e8f0;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #94a3b8;
    min-height: 24px;
    border-radius: 0px;
}

QScrollBar::handle:vertical:hover {
    background: #64748b;
}

/* Progress bar */
QProgressBar {
    background-color: #e2e8f0;
    border: 1px solid #cbd5e1;
    border-radius: 0px;
    text-align: center;
    color: #0f172a;
    font-weight: 700;
    font-size: 11px;
    height: 16px;
}

QProgressBar::chunk {
    background-color: #002b49;
}
"""

DARK_THEME_QSS = GOVERNMENT_THEME_QSS
