"""
SpecGuard Local Web Application Launcher.
Directly launches the local web server and API platform.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import app


def main():
    app.main()


if __name__ == "__main__":
    main()
