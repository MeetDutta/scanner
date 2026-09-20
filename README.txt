================================================================================
   SpecGuard — Engineering Document Quality & Standards Compliance Framework
                           Windows Portable Edition
================================================================================
Version: 1.0.0
Architecture: x86_64 (64-bit Windows 10 / 11 / Server 2019+)
Network Mode: 100% Offline (Localhost 127.0.0.1 Only)
Zero Cloud Dependencies | Zero Telemetry | Zero Manual Installation Required
================================================================================

1. QUICK START INSTRUCTIONS
--------------------------------------------------------------------------------
1. Extract the entire ZIP archive to any folder on your computer
   (e.g., C:\SpecGuard, D:\Tools\SpecGuard, or your Desktop).
2. Double-click "SpecGuard.exe" or "Launch_SpecGuard.bat".
3. The local offline backend starts automatically.
4. Your default web browser opens immediately to:
   http://127.0.0.1:8765
5. Begin analyzing documents, verifying standards, and generating reports!

To stop SpecGuard:
Press Ctrl+C in the console window, or simply close the console window.


2. SYSTEM REQUIREMENTS
--------------------------------------------------------------------------------
- Operating System: Microsoft Windows 10 (64-bit), Windows 11, or Windows Server
- RAM: 4 GB minimum (8 GB recommended for large drawings and complex models)
- Storage: 1.5 GB free disk space
- Dependencies: NONE.
  SpecGuard is fully self-contained. It does NOT require Python, Node.js,
  pip, Git, or administrative privileges.


3. DIRECTORY STRUCTURE
--------------------------------------------------------------------------------
SpecGuard/
├── SpecGuard.exe              # Primary portable application executable
├── Launch_SpecGuard.bat       # Double-click launcher & diagnostic wrapper
├── README.txt                 # This quick-start guide
├── LICENSE.txt                # License terms
├── PORTABLE_DEPLOYMENT.md     # Deployment, IT security & configuration guide
├── TROUBLESHOOTING.md         # Solutions for common issues
│
├── _internal/                 # Bundled Python runtime, DLLs and native modules
├── resources/                 # Read-only bundled models, standards, templates
├── data/                      # Persistent user-generated data (Database, Uploads, Reports)
│   ├── database/specguard.db  # SQLite database
│   ├── uploads/               # Uploaded engineering documents
│   ├── reports/               # Exported PDF, HTML, JSON verification reports
│   └── logs/specguard.log     # Detailed diagnostic log file
└── uninstall/
    └── Remove_UserData.bat    # Optional script to reset user data


4. ADVANCED COMMAND-LINE OPTIONS
--------------------------------------------------------------------------------
SpecGuard can also be launched via PowerShell or Command Prompt with custom flags:

  SpecGuard.exe --help
      Displays all available command-line flags.

  SpecGuard.exe --port 9000
      Forces the local server to bind to port 9000 instead of 8765.

  SpecGuard.exe --no-browser
      Starts the local service in headless mode without automatically launching
      the web browser. Useful for server or kiosk environments.

  SpecGuard.exe --gui
      Launches the legacy PySide6 desktop window (if PySide6 is active).

  SpecGuard.exe --version
      Prints version information and exits.


5. DATA BACKUP & PORTABILITY
--------------------------------------------------------------------------------
All your inspection findings, document uploads, comparisons, and settings are
stored in the "data\" directory.
To back up your work or migrate to another machine:
1. Copy the "data\" folder to a backup location or USB drive.
2. Replace the "data\" folder on the destination machine.


6. PRIVACY & SECURITY POSTURE
--------------------------------------------------------------------------------
- SpecGuard operates 100% locally on your machine.
- The web service binds EXCLUSIVELY to the loopback interface (127.0.0.1).
- No data is sent over the local network or the internet.
- SpecGuard contains zero analytics, zero telemetry, and zero remote tracking.


7. SUPPORT & TROUBLESHOOTING
--------------------------------------------------------------------------------
If you encounter any issues starting or using SpecGuard:
1. Inspect the log file at: data\logs\specguard.log
2. Refer to TROUBLESHOOTING.md for solutions to common port or permission issues.
3. For enterprise deployment assistance, contact your system administrator.

================================================================================
(C) SpecGuard Engineering Framework Team. All rights reserved.
================================================================================
