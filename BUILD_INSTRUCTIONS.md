# SpecGuard Windows Portable Build Instructions

**Target Application:** SpecGuard v1.0.0 Windows Portable Edition  
**Supported Build Hosts:** Windows 10 (64-bit), Windows 11, Windows Server 2019+, or Windows CI Runner (`windows-latest`)  
**Target Architecture:** x86_64 (64-bit)  
**Output:** Standalone zero-install directory and verified ZIP archive (`SpecGuard-v1.0.0-Windows-x64-Portable.zip`)

---

## 1. Prerequisites

Before initiating the build process on the Windows build machine, ensure the following software is installed:

1. **Python 3.9+ 64-bit** (Python 3.11 recommended):
   - Download official installer from [python.org](https://www.python.org/downloads/).
   - Ensure the option **"Add Python to PATH"** is checked during installation.
2. **Git for Windows** (optional, for cloning repository).
3. **PowerShell 5.1+** or **Windows Command Prompt (cmd.exe)**.
4. **Internet Connection during build only:** Required only to download Python build wheels and dependencies into the build environment. Once packaged, the resulting application requires zero internet connection.

> [!IMPORTANT]
> **Cross-Compilation Boundary Notice:**  
> PyInstaller does not cross-compile Windows PE binaries (`.exe` and `.dll`) from macOS or Linux. To produce the native Windows executable `SpecGuard.exe` with bundled Windows DLLs, the build scripts (`build_portable.bat` or `build_portable.ps1`) must be executed directly on a 64-bit Windows environment or a Windows CI runner (such as GitHub Actions `windows-latest`).

---

## 2. Quick-Start Automated Build

We provide two one-click automated build scripts that handle the complete pipeline:

### Option A: Using Windows Command Prompt (`.bat`)

Open Command Prompt in the repository root directory and run:

```cmd
build_portable.bat
```

### Option B: Using Windows PowerShell (`.ps1`)

Open PowerShell in the repository root directory and run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\build_portable.ps1
```

Both automated scripts execute the following 7-phase pipeline:
1. **Verifies Python Runtime:** Ensures 64-bit Python 3.9+ is active.
2. **Cleans Stale Artifacts:** Deletes previous `build/` and `dist/` directories.
3. **Installs Packaging Dependencies:** Reads `requirements-build.txt` and installs PyInstaller 6.5+.
4. **Executes Automated Test Suite:** Runs `pytest tests/ -q` (all 83 tests). Aborts immediately if any test fails.
5. **Compiles Application via PyInstaller:** Compiles `SpecGuard.spec` into an `onedir` release.
6. **Assembles Portable Layout:** Populates `resources/`, writable `data/`, batch wrappers, and user documentation.
7. **Generates Checksummed ZIP:** Compresses the complete folder into `dist/SpecGuard-v1.0.0-Windows-x64-Portable.zip` and calculates its SHA-256 digest.

---

## 3. Manual Step-by-Step Build Procedure

If you prefer full control over each phase of the build, follow these manual steps:

### Step 1: Create and Activate Virtual Environment

```cmd
python -m venv .venv
call .venv\Scripts\activate.bat
```

### Step 2: Install Project and Build Dependencies

```cmd
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements-build.txt
python -m pip install -e .[ml,research,dev]
```

### Step 3: Run Automated Verification Tests

Verify all analyzers, parsers, paths, and API endpoints are functional:

```cmd
python -m pytest tests/ -v
```

Ensure all tests pass before proceeding.

### Step 4: Run PyInstaller Compilation

Compile the application using the audited `SpecGuard.spec` configuration:

```cmd
pyinstaller --clean -y SpecGuard.spec
```

Verify that `dist\SpecGuard\SpecGuard.exe` has been generated.

### Step 5: Assemble Portable ZIP and Checksum

Execute the packaging utility:

```cmd
python package_zip.py
```

This will produce:
- `dist\SpecGuard-v1.0.0-Windows-x64-Portable.zip`
- `dist\SpecGuard-v1.0.0-Windows-x64-Portable.zip.sha256`

---

## 4. GitHub Actions Automated CI/CD Workflow

For automated reproducible releases, add this workflow file to `.github/workflows/build_windows.yml`:

```yaml
name: Build SpecGuard Windows Portable

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:

jobs:
  build-windows:
    runs-on: windows-latest

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip setuptools wheel
          python -m pip install -r requirements-build.txt
          python -m pip install -e .[ml,research,dev]

      - name: Run Unit & Packaging Tests
        run: |
          python -m pytest tests/ -v

      - name: Compile Executable with PyInstaller
        run: |
          pyinstaller --clean -y SpecGuard.spec

      - name: Package Portable ZIP & SHA-256
        run: |
          python package_zip.py

      - name: Upload Release Artifacts
        uses: actions/upload-artifact@v4
        with:
          name: SpecGuard-Windows-x64-Portable
          path: |
            dist/*.zip
            dist/*.sha256
```

---

## 5. Verification Checklist

Upon build completion, verify:
- [ ] `SpecGuard.exe` launches without missing DLL errors.
- [ ] Browser launches to `http://127.0.0.1:8765`.
- [ ] `data/logs/specguard.log` is generated and contains clean startup entries.
- [ ] Analysis engine parses demo PDF, Word, and Scanned Image documents.
- [ ] Verification reports are saved to `data/reports/`.
- [ ] Double-clicking `uninstall/Remove_UserData.bat` prompts user before clearing cache.
