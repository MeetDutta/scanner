"""
SpecGuard Web Application Server.
Command: python app.py [--host HOST] [--port PORT] [--reload]
Web-only document inspection, error detection, and reporting platform.
"""

import sys
import os
import argparse
import logging
from pathlib import Path
import uvicorn

# Ensure local specguard package is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from specguard.core.config import DEFAULT_CONFIG
from specguard.server.app import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("SpecGuard")


def main():
    parser = argparse.ArgumentParser(
        description="SpecGuard — Engineering Document Quality & Compliance Inspection Web Platform"
    )
    default_host = os.environ.get("SPECGUARD_HOST") or os.environ.get("HOST") or os.environ.get("DOCREADY_HOST", "0.0.0.0")
    default_port = int(os.environ.get("SPECGUARD_PORT") or os.environ.get("PORT", "8765"))

    parser.add_argument("--host", type=str, default=default_host,
                        help="Host address to bind the server to (default: 0.0.0.0 for LAN access)")
    parser.add_argument("--port", type=int, default=default_port,
                        help="Port number to listen on (default: 8765)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--version", action="store_true", help="Display version and exit")

    args = parser.parse_args()

    if args.version:
        print(f"SpecGuard v{DEFAULT_CONFIG.version} (100% Offline LAN/Intranet Platform)")
        sys.exit(0)

    logger.info("Starting SpecGuard 100%% Offline LAN Web Server")
    logger.info("Listening on: http://%s:%d (Localhost: http://127.0.0.1:%d)", args.host, args.port, args.port)
    if args.host == "0.0.0.0":
        logger.info("LAN Access available at http://<YOUR-SERVER-LAN-IP>:%d for intranet clients.", args.port)
    if args.reload:
        uvicorn.run("specguard.server.app:app", host=args.host, port=args.port, reload=True, log_level="info")
    else:
        app = create_app()
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
