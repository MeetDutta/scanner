"""
Automated Offscreen GUI Workflow Test for SpecGuard Government Portal UI.
Verifies the complete 3-stage flow:
1. Document Upload -> compact doc card
2. Comparison Mode -> Mechanical / Chemical / Electrical
3. Verification Progress -> Formal checklist
4. Compared Document Preview -> Canvas, pages list, formal finding inspector
5. New Comparison reset
"""

import os
import sys
from pathlib import Path
import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication

# Ensure app instance exists
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

from specguard.gui.main_window import MainWindow


def test_minimal_gui_3_stage_workflow():
    window = MainWindow()
    window.show()

    # 1. Initial State: Screen 0 (Upload)
    assert window.stack.currentIndex() == 0
    assert window.btn_step_upload.property("class") == "stage_step_active"
    assert not window.btn_step_mode.isEnabled()
    assert not window.btn_step_preview.isEnabled()

    # 2. Select Document on Screen 0
    test_pdf = Path("demo_samples/mechanical_sample_with_errors.pdf").resolve()
    assert test_pdf.exists(), "Sample PDF must exist for GUI test"

    window.view_upload.set_selected_file(str(test_pdf))
    assert window.view_upload.selected_box.isVisible()
    assert not window.view_upload.drop_zone.isVisible()
    assert window.current_file_path == str(test_pdf)
    assert window.btn_step_mode.isEnabled()

    # 3. Transition to Screen 1 (Mode Selection)
    window.view_upload.continue_btn.click()
    assert window.stack.currentIndex() == 1
    assert window.btn_step_mode.property("class") == "stage_step_active"
    assert not window.view_mode.compare_btn.isEnabled()

    # 4. Select Mode: Mechanical
    window.view_mode._select_domain("Mechanical")
    assert window.view_mode.selected_domain == "Mechanical"
    assert window.view_mode.compare_btn.isEnabled()

    # 5. Launch Comparison Pipeline
    window.view_mode.compare_btn.click()
    assert window.stack.currentIndex() == 2 # Screen 2 (Analysis Progress)

    # Wait for the background worker to finish
    if window.view_analysis.worker:
        window.view_analysis.worker.wait(15000) # Wait up to 15s for analysis

    # Allow Qt events to process signals
    QCoreApplication.processEvents()

    # 6. Verify Screen 3 (Preview) automatically opened
    assert window.stack.currentIndex() == 3
    assert window.btn_step_preview.property("class") == "stage_step_active"
    assert len(window.current_findings) > 0

    # 7. Check Preview View Elements
    assert window.view_preview.pages_list.count() >= 1
    assert window.view_preview.viewer.canvas.pixmap is not None
    assert window.view_preview.detail_panel.isVisible()
    assert window.view_preview.detail_panel.detected_val.text() != ""
    assert window.view_preview.detail_panel.expected_val.text() != ""

    # 7.1 Verify Export Button & Actions
    assert window.view_preview.export_btn.isVisible()
    export_menu = window.view_preview.export_btn.menu()
    assert export_menu is not None
    assert len(export_menu.actions()) == 3

    # 8. Test Navigation: Back to Mode
    window.view_preview.back_btn.click()
    assert window.stack.currentIndex() == 1

    # 9. Return to Preview via Breadcrumb
    window.btn_step_preview.click()
    assert window.stack.currentIndex() == 3

    # 10. Test "New Comparison" Reset
    window.view_preview.new_btn.click()
    assert window.stack.currentIndex() == 0
    assert window.current_file_path is None
    assert window.current_doc is None
    assert not window.btn_step_mode.isEnabled()
    assert not window.btn_step_preview.isEnabled()
    assert window.view_upload.drop_zone.isVisible()
    assert not window.view_upload.selected_box.isVisible()

    window.close()
