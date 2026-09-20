# SpecGuard Portable Deployment & Security Architecture Guide

**Document Version:** 1.0.0  
**Target Environment:** Corporate Engineering Workstations, Air-Gapped Labs, Field Laptops, Industrial Control Networks  
**Security Classification:** 100% Localhost Air-Gapped (`127.0.0.1`), Zero Cloud Connectivity, Zero External Telemetry  

---

## 1. Portable Deployment Architecture

SpecGuard is packaged using an **Onedir Portable Architecture**. Rather than packing the entire application into a monolithic self-extracting executable that unpacks into `%TEMP%` on every run, SpecGuard ships as a pre-extracted, standalone directory tree:

```
SpecGuard/
├── SpecGuard.exe                  # Main portable application executable
├── Launch_SpecGuard.bat           # Shell launcher & diagnostic wrapper
├── README.txt                     # User quick-start guide
├── LICENSE.txt                    # MIT License
├── PORTABLE_DEPLOYMENT.md         # Deployment & security reference
├── TROUBLESHOOTING.md             # Common issues and solutions
│
├── _internal/                     # Bundled Python runtime, DLLs & modules
│   ├── python*.dll
│   ├── fitz/                      # PyMuPDF compiled binaries
│   ├── cv2/                       # OpenCV compiled binaries
│   ├── onnxruntime/               # ONNX Runtime DLLs
│   ├── torch/                     # PyTorch CPU binaries
│   └── ...                        # Supporting wheels and C-extensions
│
├── resources/                     # Bundled read-only application resources
│   ├── models/                    # ONNX model files and registry
│   ├── standards/                 # Domain standards (mechanical, chemical, electrical)
│   ├── rules/                     # Compliance rules
│   ├── templates/                 # Industry specification templates
│   ├── web/                       # Offline HTML5/CSS/JS frontend
│   └── demo_samples/              # Engineering sample documents
│
├── data/                          # Persistent writable user storage
│   ├── database/
│   │   └── specguard.db           # SQLite database
│   ├── uploads/                   # Uploaded documents
│   ├── reports/                   # Exported verification reports
│   ├── logs/
│   │   └── specguard.log          # Runtime log file
│   └── cache/                     # Temporary processing cache
│
└── uninstall/
    └── Remove_UserData.bat        # Script to clean user data if requested
```

### Architectural Benefits:
1. **Instantaneous Execution:** Launch takes < 1.5 seconds because native libraries (`torch_cpu.dll`, `opencv_world.dll`, `fitz.dll`) are loaded directly from disk without decompressing 300MB into `%TEMP%`.
2. **True USB Portability:** The entire `SpecGuard` directory can reside on a USB flash drive or portable drive. All project databases, uploaded blueprints, and exported reports stay together in `data/`.
3. **Graceful Permission Fallback:** If `SpecGuard` is placed in a read-only directory (such as a corporate network share or `C:\Program Files`), `specguard.core.runtime_paths` automatically redirects writable state to `%LOCALAPPDATA%\SpecGuard\data`, preventing permission crashes.

---

## 2. Deployment Scenarios

### 2.1 Scenario A: Local Workstation Extraction (Recommended)
- **Destination:** `C:\SpecGuard`, `D:\Applications\SpecGuard`, or user desktop.
- **Method:** Extract `SpecGuard-v1.0.0-Windows-x64-Portable.zip`.
- **User Action:** Double-click `SpecGuard.exe` or `Launch_SpecGuard.bat`.
- **Privileges:** Standard user (No Administrator / UAC prompt required).

### 2.2 Scenario B: Air-Gapped Field Laptop / USB Drive
- **Destination:** USB Flash Drive (e.g. `E:\SpecGuard`).
- **Method:** Extract ZIP onto the USB drive.
- **User Action:** Plug into air-gapped machine, double-click `Launch_SpecGuard.bat`.
- **Result:** Operates without network connectivity, internet access, or software installation on the host machine.

### 2.3 Scenario C: Corporate Read-Only Network Share
- **Destination:** `\\company-nas\EngineeringTools\SpecGuard`
- **Method:** IT copies the read-only directory to the network share.
- **Behavior:** `SpecGuard` detects that the application directory is not writable. It loads models, standards, and frontend files from the share, and creates local user databases in `%LOCALAPPDATA%\SpecGuard\data`.

---

## 3. IT Security & Governance Analysis

SpecGuard is designed for strictly regulated defense, aerospace, chemical, and nuclear engineering organizations where data leakage is prohibited:

| Security Domain | SpecGuard Guarantee | Audit Verification |
| :--- | :--- | :--- |
| **Network Exposure** | Loopback binding only: `127.0.0.1` | Backend socket binds strictly to `AF_INET, 127.0.0.1`. Never listens on `0.0.0.0`. |
| **Firewall Prompts** | Zero Windows Firewall prompts | Loopback binding does not trigger Windows Defender Firewall alert dialogs. |
| **Outbound Telemetry** | Zero outbound HTTP/HTTPS calls | Tested with network adapters disabled and outbound firewall rules blocking all ports. |
| **External CDNs** | Zero remote scripts or stylesheets | All CSS, JS, SVG icons, and HTML files are bundled locally in `resources/web/`. |
| **Remote Fonts** | Zero external font calls | System UI font stack (`system-ui, -apple-system, Segoe UI, Roboto`) used exclusively. |
| **Data Residency** | 100% On-Premise / On-Device | SQLite database and files reside strictly on local storage in `data/`. |

---

## 4. User Data Backup & Disaster Recovery

### Automatic Backups
Users can trigger transactional backups directly from the Web Interface under **Settings & Health > Backup Data**, or via the API:
```cmd
curl -X POST http://127.0.0.1:8765/api/settings/backup
```

### Manual Backup Procedure
To back up all historical comparisons, findings, and uploaded documents:
1. Close `SpecGuard`.
2. Copy the `SpecGuard\data\` folder to your backup repository or archive.

### Restoration Procedure
1. Extract a clean copy of `SpecGuard`.
2. Paste the preserved `data\` folder into the application root.
3. Launch `SpecGuard.exe`. All previous sessions and findings are instantly restored.

---

## 5. Uninstallation Procedure

Because SpecGuard is fully portable and requires no Windows Registry keys or system drivers:

### Complete Removal:
1. Delete the `SpecGuard` folder.
2. (Optional) If running from a read-only share, delete `%LOCALAPPDATA%\SpecGuard`.

### Reset User Data Only:
Double-click `uninstall\Remove_UserData.bat`. This removes the SQLite database and document cache while preserving application binaries and standards.
