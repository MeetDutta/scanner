"""
SpecGuard Portable Application Launcher.
Entry point for packaged Windows portable distribution (SpecGuard.exe) and command-line execution.

Features:
- Dynamic installation path detection (independent of current working directory)
- Automatic port allocation with collision avoidance (defaults to 8765)
- Pre-flight diagnostic verification and file logging (data/logs/specguard.log)
- Resilient health check polling before opening browser
- Native 127.0.0.1 local binding (zero LAN exposure, zero firewall prompts)
- Graceful shutdown handling (SIGINT, SIGTERM)
- Support for paths with spaces and Unicode characters
"""

import sys
import os
import time
import socket
import signal
import logging
import argparse
import threading
import webbrowser
from pathlib import Path
from typing import Tuple, Optional

# Ensure package root is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# PyInstaller frozen bundle support
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
    if str(APP_DIR) not in sys.path:
        sys.path.insert(0, str(APP_DIR))
else:
    APP_DIR = SCRIPT_DIR

from specguard.core.runtime_paths import (
    get_app_dir,
    get_data_dir,
    get_log_file_path,
    get_resource_dir,
    is_frozen,
)
from specguard.core.config import DEFAULT_CONFIG


def setup_portable_logging(log_file: Path) -> logging.Logger:
    """Configures dual logging: formatted console output and persistent file log."""
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("SpecGuard")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 1. Console Stream Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. File Handler
    try:
        file_handler = logging.FileHandler(str(log_file), mode="a", encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not initialize log file at {log_file}: {e}")

    return logger


def is_port_available(host: str, port: int) -> bool:
    """Checks whether a given port is available for binding on host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.bind((host, port))
            return True
        except (OSError, socket.error):
            return False


def find_available_port(host: str, preferred_port: int = 8765, max_attempts: int = 50) -> int:
    """
    Finds an open port starting from preferred_port.
    Falls back to OS ephemeral port if the preferred range is fully occupied.
    """
    if is_port_available(host, preferred_port):
        return preferred_port

    for port in range(preferred_port + 1, preferred_port + max_attempts):
        if is_port_available(host, port):
            return port

    # Fallback to ephemeral port assigned by OS
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


def show_fatal_error_dialog(title: str, message: str, log_path: Path):
    """Displays user-facing fatal error dialog on Windows or prints to console."""
    formatted_msg = (
        f"{message}\n\n"
        f"Installation Path: {get_app_dir()}\n"
        f"Detailed Diagnostic Log: {log_path}\n\n"
        "Please consult TROUBLESHOOTING.md or contact support."
    )
    # Try Windows native message box if running on Windows
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, formatted_msg, title, 0x10)  # MB_ICONERROR
            return
        except Exception:
            pass

    # Fallback console print
    print(f"\n========================================================")
    print(f"FATAL ERROR: {title}")
    print(f"========================================================")
    print(formatted_msg)
    print(f"========================================================\n")


def poll_backend_and_launch_browser(url: str, logger: logging.Logger, timeout: float = 15.0):
    """
    Polls local health endpoint until the server is ready, then launches the browser.
    Ensures user never encounters 'Connection Refused' error page.
    """
    import urllib.request

    health_url = f"{url}/api/health"
    start_time = time.time()
    launched = False

    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(health_url, timeout=0.8) as resp:
                if resp.status == 200:
                    logger.info("Backend service confirmed ready. Launching web interface: %s", url)
                    webbrowser.open(url)
                    launched = True
                    break
        except Exception:
            time.sleep(0.2)

    if not launched:
        logger.warning(
            "Backend health check timed out after %.1fs. Attempting browser launch anyway...", timeout
        )
        try:
            webbrowser.open(url)
        except Exception as e:
            logger.error("Could not launch default browser: %s. Please open %s manually.", e, url)


def main():
    parser = argparse.ArgumentParser(description="SpecGuard Portable Application Launcher")
    parser.add_argument("--port", type=int, default=None, help="Force specific port (default: auto-detect 8765+)")
    parser.add_argument("--no-browser", action="store_true", help="Start backend without launching web browser")
    parser.add_argument("--gui", action="store_true", help="Launch desktop PySide6 GUI instead of web")
    parser.add_argument("--version", action="store_true", help="Show application version and exit")
    args = parser.parse_args()

    if args.version:
        print(f"SpecGuard v{DEFAULT_CONFIG.version} (100% Offline Framework)")
        sys.exit(0)

    # 1. Setup Logging
    log_file = get_log_file_path()
    logger = setup_portable_logging(log_file)

    logger.info("=" * 64)
    logger.info("   SpecGuard — Engineering Document Quality & Standards System  ")
    logger.info("                  100%% Offline Portable Edition                 ")
    logger.info("=" * 64)
    logger.info("Application Root: %s", get_app_dir())
    logger.info("Persistent Data : %s", get_data_dir())
    logger.info("Execution Mode  : %s", "PyInstaller Frozen" if is_frozen() else "Python Development")
    logger.info("Platform        : %s (%s)", sys.platform, os.name)

    # 2. Pre-flight Environment Verification
    from specguard.core.startup import verify_environment
    logger.info("Executing pre-flight diagnostic checks...")
    try:
        report = verify_environment()
        if not report.is_ready:
            err_summary = "\n".join(f"• {e}" for e in report.errors)
            logger.critical("Pre-flight environment verification failed:\n%s", err_summary)
            show_fatal_error_dialog(
                "SpecGuard Initialization Error",
                f"Required system components could not be verified:\n{err_summary}",
                log_file
            )
            sys.exit(1)
        logger.info("Environment verified: Python %s, Hardware: %s", report.python_version, report.hardware.get("device_name"))
        if report.warnings:
            for w in report.warnings:
                logger.warning("Pre-flight notice: %s", w)
    except Exception as e:
        logger.exception("Unexpected error during pre-flight diagnostics: %s", e)
        show_fatal_error_dialog("SpecGuard Diagnostic Error", str(e), log_file)
        sys.exit(1)

    # 3. Handle GUI flag if requested
    if args.gui:
        logger.info("Launching PySide6 desktop interface...")
        try:
            from app import launch_gui
            launch_gui()
            sys.exit(0)
        except Exception as e:
            logger.exception("Failed to launch PySide6 desktop interface: %s", e)
            show_fatal_error_dialog("Desktop GUI Launch Failure", str(e), log_file)
            sys.exit(1)

    # 4. Port Allocation
    host = "127.0.0.1"
    if args.port:
        port = args.port
        if not is_port_available(host, port):
            logger.error("Requested port %d is already in use on %s.", port, host)
            show_fatal_error_dialog("Port Conflict", f"Port {port} is occupied by another application.", log_file)
            sys.exit(1)
    else:
        port = find_available_port(host, preferred_port=8765)
        if port != 8765:
            logger.warning("Default port 8765 is occupied. Dynamically allocated port %d.", port)

    app_url = f"http://{host}:{port}"
    logger.info("Binding exclusively to local interface: %s", app_url)

    # 5. Launch Browser Watcher Thread
    if not args.no_browser:
        watcher_thread = threading.Thread(
            target=poll_backend_and_launch_browser,
            args=(app_url, logger),
            daemon=True
        )
        watcher_thread.start()
    else:
        logger.info("Headless mode requested (--no-browser). Interface accessible at %s", app_url)

    # 6. Start Uvicorn Server
    import uvicorn
    from specguard.server.app import create_app

    app_instance = create_app()

    config = uvicorn.Config(
        app=app_instance,
        host=host,
        port=port,
        log_level="info",
        access_log=False
    )
    server = uvicorn.Server(config)

    # Clean shutdown handling
    def handle_exit(signum, frame):
        logger.info("Shutdown signal received (%s). Stopping SpecGuard...", signum)
        server.should_exit = True

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    try:
        server.run()
    except Exception as e:
        logger.exception("Fatal server runtime error: %s", e)
        show_fatal_error_dialog("SpecGuard Runtime Error", str(e), log_file)
        sys.exit(1)
    finally:
        logger.info("SpecGuard backend stopped cleanly. Log saved to: %s", log_file)


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()

