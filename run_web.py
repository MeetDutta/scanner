"""
SpecGuard Local Web Application Launcher.
Delegates to portable_launcher for unified dynamic port discovery,
logging, environment verification, and clean shutdown.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import portable_launcher


def main():
    portable_launcher.main()


if __name__ == "__main__":
    main()

