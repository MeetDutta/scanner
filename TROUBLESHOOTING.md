# SpecGuard Windows Portable Troubleshooting & Diagnostics Guide

This guide addresses common issues encountered when deploying and executing the portable version of **SpecGuard**.

---

## 1. Quick Diagnostic Checklist

If SpecGuard does not launch or behave as expected:

1. **Check the Log File:**
   Open:
   ```
   SpecGuard\data\logs\specguard.log
   ```
   This file records detailed technical exceptions, environment checks, and startup events.

2. **Run the Diagnostic Batch Launcher:**
   Double-click `Launch_SpecGuard.bat` instead of `SpecGuard.exe`. If a startup error occurs, this script keeps the command window open and displays the exact termination code.

3. **Verify Complete Extraction:**
   Ensure you extracted the ZIP archive completely. Running `SpecGuard.exe` directly from inside Windows Explorer's compressed folder preview (`.zip`) will fail because Windows mounts the archive in a temporary read-only memory space.

---

## 2. Common Issues & Solutions

### Issue 1: "Windows Protected Your PC" (Windows Defender SmartScreen)
- **Symptom:** Windows displays a blue SmartScreen warning dialog stating "Unknown Publisher".
- **Cause:** SpecGuard is an unsigned binary compiled for internal/portable engineering use.
- **Resolution:**
  1. Click **"More info"** on the SmartScreen dialog.
  2. Click the **"Run anyway"** button.
  3. SpecGuard will launch normally. Subsequent launches will not show the dialog.
  - *Enterprise Note:* IT departments can sign `SpecGuard.exe` with their internal corporate code-signing certificate using `signtool.exe`.

---

### Issue 2: Port Conflict (Port 8765 in Use)
- **Symptom:** Another local development server or background application is already using port `8765`.
- **Automatic Behavior:** SpecGuard automatically detects that port `8765` is busy and binds to the next available port (e.g., `8766`, `8767`, etc.). The browser will open to the newly assigned port automatically.
- **Manual Override:** You can force a specific custom port from the command line:
  ```cmd
  SpecGuard.exe --port 9050
  ```

---

### Issue 3: Web Browser Does Not Open Automatically
- **Symptom:** The console reports that the server is running on `http://127.0.0.1:8765`, but your web browser does not pop up.
- **Cause:** Restricted default browser associations or locked down Windows kiosk settings.
- **Resolution:**
  1. Open your preferred browser (Microsoft Edge, Google Chrome, Mozilla Firefox, or Brave).
  2. Navigate to:
     ```
     http://127.0.0.1:8765
     ```
  3. Bookmark the URL for convenient access.

---

### Issue 4: "Access Denied" or Permission Errors
- **Symptom:** Console error indicates permission denied when creating `data\logs` or `data\database`.
- **Cause:** The `SpecGuard` folder was extracted into a system-protected directory (e.g., `C:\Program Files` or a read-only optical disc / corporate share) without write permissions.
- **Automatic Behavior:** SpecGuard will attempt to redirect writable user data to:
  ```
  %LOCALAPPDATA%\SpecGuard\data
  ```
- **Manual Resolution:** Move the `SpecGuard` folder to a writable user directory, such as `C:\SpecGuard`, `D:\Tools\SpecGuard`, or your Desktop.

---

### Issue 5: Antivirus False Positives
- **Symptom:** Antivirus software flags or quarantines `SpecGuard.exe`.
- **Cause:** PyInstaller bootloaders are occasionally flagged as generic heuristics by over-aggressive heuristic antivirus scanners because they unpack executable code in memory.
- **Resolution:**
  1. Add an exclusion rule in your antivirus software for the `SpecGuard` installation directory.
  2. Verify the ZIP file's SHA-256 checksum against the published `.sha256` file to guarantee integrity.

---

### Issue 6: Path Length Limits (MAX_PATH)
- **Symptom:** Files fail to load or write when nested deeply inside enterprise folder hierarchies.
- **Cause:** Windows legacy 260-character path limit.
- **Resolution:**
  1. Extract SpecGuard into a shorter path, such as `C:\SpecGuard`.
  2. Enable Win32 Long Paths in the Windows Registry (`HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\FileSystem\LongPathsEnabled = 1`).

---

### Issue 7: Corrupt SQLite Database or Inconsistent Session State
- **Symptom:** Database error dialog appears during startup or document analysis.
- **Resolution:**
  1. Close SpecGuard.
  2. Double-click `uninstall\Remove_UserData.bat` to reset the database and cache.
  3. Relaunch `SpecGuard.exe`. A fresh database will be initialized automatically.
  - *Tip:* If you created backups, you can restore previous sessions by extracting `data\backups\SpecGuard_Backup_*.zip`.

---

## 3. Contact & Support

For additional technical support:
- Inspect `data\logs\specguard.log` for Python tracebacks.
- Refer to `PORTABLE_DEPLOYMENT.md` for enterprise network and security guidelines.
- Contact your internal engineering systems administrator.
