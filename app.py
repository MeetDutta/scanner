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
    parser.add_argument("--host", type=str, default=os.environ.get("DOCREADY_HOST", "127.0.0.1"),
                        help="Host address to bind the server to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8765")),
                        help="Port number to listen on (default: 8765)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--version", action="store_true", help="Display version and exit")

    args = parser.parse_args()

    if args.version:
        print(f"DocReady / SpecGuard v{DEFAULT_CONFIG.version} (Web-Only Platform)")
        sys.exit(0)

    logger.info("Starting SpecGuard Web Server on http://%s:%d", args.host, args.port)
    if args.reload:
        uvicorn.run("specguard.server.app:app", host=args.host, port=args.port, reload=True, log_level="info")
    else:
        app = create_app()
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
