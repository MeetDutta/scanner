"""
SpecGuard Local Web Application Launcher.
Starts the local offline FastAPI backend service, verifies pre-flight diagnostics,
and launches the browser interface on localhost (127.0.0.1:8765).
"""

import sys
import os
import time
import webbrowser
import threading
import logging
from pathlib import Path

# Ensure local specguard package is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import uvicorn
from specguard.core.startup import verify_environment

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("SpecGuard.Launcher")

HOST = "127.0.0.1"
PORT = 8765


def open_browser_delayed(url: str, delay_seconds: float = 1.2):
    """Opens system default web browser after server starts."""
    time.sleep(delay_seconds)
    logger.info("Opening SpecGuard interface at %s", url)
    webbrowser.open(url)


def main():
    logger.info("============================================================")
    logger.info("   SpecGuard — Engineering Document Verification Framework   ")
    logger.info("              100% Offline Local Web Engine                 ")
    logger.info("============================================================")

    # 1. Pre-flight diagnostics
    logger.info("Performing pre-flight environment checks...")
    report = verify_environment()
    if not report.is_ready:
        logger.warning("Diagnostics reported potential issues:\n" + "\n".join(f"• {e}" for e in report.errors))
    else:
        logger.info("Pre-flight check passed: Python %s, All core engines ready.", report.python_version)

    url = f"http://{HOST}:{PORT}"
    logger.info("Binding exclusively to local interface: %s", url)

    # 2. Launch browser in separate daemon thread
    browser_thread = threading.Thread(target=open_browser_delayed, args=(url,), daemon=True)
    browser_thread.start()

    # 3. Start local Uvicorn HTTP server
    try:
        uvicorn.run(
            "specguard.server.app:app",
            host=HOST,
            port=PORT,
            log_level="info",
            access_log=False
        )
    except KeyboardInterrupt:
        logger.info("\nSpecGuard server stopped by user. Clean shutdown complete.")
        sys.exit(0)


if __name__ == "__main__":
    main()
