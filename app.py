"""
SpecGuard Desktop Application Entry Point.
Command: python app.py
100% Offline Hybrid Deep Learning and Computer Vision Engineering Quality Framework.
"""

import sys
import os
import logging
from pathlib import Path

# Ensure local specguard package is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from specguard.gui.main_window import MainWindow
from specguard.core.startup import verify_environment

# Configure clean local logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("SpecGuard")


def launch_gui():
    """Launches legacy PySide6 desktop GUI."""
    from PySide6.QtWidgets import QApplication, QMessageBox
    from PySide6.QtCore import Qt
    from specguard.gui.main_window import MainWindow

    logger.info("Initializing SpecGuard PySide6 Desktop GUI...")
    report = verify_environment()

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("SpecGuard")
    app.setOrganizationName("SpecGuard Research")

    if not report.is_ready:
        err_msg = "SpecGuard Pre-flight Verification Failed:\n\n" + "\n".join(f"• {e}" for e in report.errors)
        logger.critical(err_msg)
        QMessageBox.critical(None, "SpecGuard Startup Error", err_msg)
        sys.exit(1)

    window = MainWindow()
    window.show()

    logger.info("SpecGuard PySide6 window launched successfully.")
    sys.exit(app.exec())


def main():
    if "--gui" in sys.argv or "--pyside" in sys.argv:
        launch_gui()
    else:
        import portable_launcher
        portable_launcher.main()


if __name__ == "__main__":
    main()

