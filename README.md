# DocReady

## Official Project Title
**DocReady — An Offline Intranet Platform for Template-Aware Document Formatting Analysis and Readiness Verification**

---

## 1. Overview & Architectural Capabilities

**DocReady** (formerly SpecGuard) is a 100% offline, intranet-accessible document intelligence platform that analyzes engineering and structured documents for:

- Formatting consistency & page layout correctness
- Typography consistency (fonts, sizes, weights, hierarchy)
- Document structure & heading hierarchy (H1–H4)
- Tables, figures, equations, captions, and numbering
- Margins, spacing, and column layouts
- Template conformity & template drift detection
- Overall document readiness for downstream processing

The framework implements a hybrid multi-layer architecture:
- **Computer Vision & OCR** extracts page geometry, line morphology, table grids, diagrams, margins, and bounding-box coordinates.
- **NLP & Deep Learning** extracts engineering propositions `(Entity, Parameter, Value, Unit, Condition, Location)` using a technical vocabulary whitelist.
- **Engineering Analysis** normalizes SI and imperial units (e.g. $1000\text{ V} = 1\text{ kV}$, $1\text{ MPa} = 10\text{ bar}$, $1000\text{ mm} = 1\text{ m}$).
- **Local Standards Knowledge Base** evaluates machine-readable rules (JSON/YAML) across **Mechanical**, **Electrical**, and **Chemical** engineering domains.
- **Custom Template Management** enables statistical profile learning, human gated review, region annotations, and local supervised ML training.
- **Logical Consistency Engine** identifies cross-document contradictions (e.g. $80^\circ\text{C}$ on Page 1 vs $60^\circ\text{C}$ on Page 2) and impossible physical bounds ($\text{Min} > \text{Max}$).
- **Severity & Prioritization Engine** mathematically ranks findings to surface safety-critical engineering deviations before cosmetic formatting errors.
- **Visual Localization & Interactive Document Viewer** displays high-DPI original document pages with color-coded bounding-box overlays and click-to-jump navigation.
- **Reporting & Export Center** generates annotated PDFs (with vector highlights and popup comments), annotated DOCX files, and certified standalone HTML/JSON compliance audit reports.

---

## 2. Strict 100% Offline Guarantee

SpecGuard operates with **ZERO external network calls**:
- No OpenAI, Gemini, Claude, or cloud AI endpoints
- No cloud OCR services
- No remote databases
- No external telemetry or analytics
- Zero CDN dependencies

A permanent **100% OFFLINE** verification badge and diagnostic screen continuously monitor that all subsystems remain strictly local and air-gapped.

---

## 3. Analysis Engines & Intelligence Modules (14 Independent Engines)

1. `FormattingAnalyzer`: Evaluates font consistency, font-size outliers, heading typefaces, margins, and line spacing.
2. `StructureAnalyzer`: Parses multi-level document outline hierarchy trees supporting numeric (`1.`, `1.1`), Roman numeral (`I.`, `II.`), and letter (`A.`, `B.`) headings; detects broken numbering sequences, depth jumps, duplicate headers, and missing mandatory sections per profile.
3. `TOCAnalyzer`: Multi-level TOC parsing and cross-validation against actual document headings and page indices, identifying page drift, page numbering gaps, and distinguishing lists vs genuine TOC tables with profile-aware suppression.
4. `TableAnalyzer`: Inspects data tables for empty required specification cells, jagged rows, duplicate entries, unit column consistency, caption placement, and multi-page split table continuity.
5. `FigureAnalyzer`: Detects figure captions (`Fig. X`, `Figure Y`), validates numbering continuity, flags duplicate labels, uncaptioned graphical figures, and invalid placement.
6. `EquationAnalyzer`: Scans for numbered display equations (`(1)`, `(2.1)`), verifies sequence order, detects duplicate labels, and extracts mathematical expressions.
7. `CrossReferenceAnalyzer`: Builds a document-wide citation and cross-reference graph linking in-text mentions (`Fig. X`, `Table Y`, `Eq. (Z)`, `[N]`) to targets, identifying dangling references and unreferenced assets.
8. `IEEEAnalyzer`: Dedicated academic and conference compliance engine validating prominent title, abstract, keywords, two-column layouts, Roman numeral table styling, and IEEE citation standards.
9. `DocumentComparator`: Deep structural and semantic revision comparison across multi-page documents (page count deltas, section moves/additions/deletions, table/figure modifications, and text diffs).
10. `GrammarAnalyzer`: Performs technical grammar and spelling validation with an engineering whitelist (500+ terms) to prevent false positives on legitimate technical terminology.
11. `SemanticAnalyzer`: Extracts structured propositions with bounding-box coordinate tracking; flags ambiguous datums (e.g., pressure without gauge/absolute reference) and missing phase configurations.
12. `LogicalAnalyzer`: Maintains a document-wide parameter registry; detects cross-page contradictory values and $\text{Minimum} > \text{Maximum}$ boundary inversions.
13. `EngineeringAnalyzer`: Domain-specific parameter parsers for Mechanical (tolerances, fits, surface roughness Ra, pressure), Chemical (concentrations, flash points, runaway temperatures), and Electrical (voltages, feeder currents, frequencies, power).
14. `StandardsAnalyzer`: Evaluates extracted parameters against local JSON/YAML standard rules.
15. `SeverityEngine`: Computes multi-factor priority scores:
    $$\text{Priority Score} = w_{\text{sev}}\cdot\text{Severity} + w_{\text{safety}}\cdot\text{SafetyImpact} + w_{\text{dev}}\cdot|\text{Deviation}| + w_{\text{std}}\cdot\text{StandardCriticality} + w_{\text{conf}}\cdot\text{Confidence} + w_{\text{cross}}\cdot\text{CrossImpact}$$

---

## 4. Multi-Page Streaming & Document Scale Architecture

- **Zero Page Limits**: Tested and certified on 1, 20, 50, and 100+ page documents with linear memory scaling and stream-based page parsing.
- **Lazy Rendering**: PyMuPDF vector extraction is decoupled from high-DPI rasterization, eliminating memory spikes during bulk analysis.
- **Multi-Column Reading Order**: Geometric column segmentation automatically reconstructs natural reading flow across multi-column academic layouts, mixed spanning figures/tables, and sidebars.
- **DOCX Structural & Headless LibreOffice Integration**: Native XML element-level extraction for headings, tables, breaks, and inline runs, with automatic headless LibreOffice (`soffice`) fallback detection for pixel-perfect PDF conversion and explicit pagination uncertainty reporting.
- **Asynchronous Cancellation & Stage Progress**: Thread-safe cancellation tokens allow immediate, clean cancellation at any pipeline stage.

---

## 5. Installation & Quickstart

### Prerequisites (for Development)
- Python 3.9+ (Python 3.11 recommended)
- macOS, Linux, or Windows

### Running DocReady

#### 1. Windows Portable Zero-Install Package (No Python or Node.js Required)
1. Extract `DocReady-v1.0.0-Windows-x64-Portable.zip`.
2. Double-click `DocReady.exe` or `Launch_DocReady.bat`.
3. The local backend initializes automatically on `127.0.0.1:8765` and opens your default browser.

#### 2. Modern Web Application via Python (Development & Intranet Mode)
```bash
# Launch the modern local web interface (default localhost: 127.0.0.1):
./.venv/bin/python portable_launcher.py

# Launch for private corporate intranet access:
./.venv/bin/python portable_launcher.py --host 0.0.0.0

# Or via convenience launchers:
./.venv/bin/python run_web.py
./.venv/bin/python app.py
```
The application starts the local backend at `http://127.0.0.1:8765` (or the next available port) and opens the user interface in your default browser.

#### 3. Legacy PySide6 Desktop GUI (Rollback Fallback)
```bash
./.venv/bin/python app.py --gui
```

### Building the Windows Portable Distribution
```cmd
# Automated Windows build script (cmd):
build_portable.bat

# Assemble checksummed ZIP distribution:
python package_zip.py
```
See [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md), [PORTABLE_DEPLOYMENT.md](PORTABLE_DEPLOYMENT.md), and [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for full deployment documentation.

### Running Automated Test Suite

```bash
./.venv/bin/pytest -v
```
All 123 tests (DocReady branding & aliases, multi-page streaming, reading order, TOC drift, cross-references, IEEE compliance, custom template learning, region annotations, local layout ML training, offline intranet security, document comparator, stress benchmarks, portable packaging, and web APIs) execute 100% offline.


---

## 5. Demonstration Data

Pre-generated synthetic engineering test documents containing realistic deviations are available in `demo_samples/`:
- `demo_samples/mechanical_sample_with_errors.pdf`:
  - Critical tolerance deviation ($\pm 0.5\text{ mm}$ vs standard limit $\pm 0.05\text{ mm}$)
  - Logical contradiction ($80^\circ\text{C}$ on Page 1 vs $60^\circ\text{C}$ on Page 2)
  - Broken structural numbering (Section 3.1 $\to$ Section 3.3, missing 3.2)
  - TOC page drift (TOC lists Page 4, actual heading is on Page 2)
  - Controlled spelling typos (`maintanence`, `teh`, `recieved`)
  - Table missing cells and mixed column units
- `demo_samples/electrical_sample_with_errors.pdf`:
  - Critical voltage deviation ($230\text{ V}$ detected vs standard $415\text{ V}$ industrial feeder)
  - Feeder current overload ($750\text{ A}$ vs standard $630\text{ A}$ switchgear rating)
- `demo_samples/chemical_sample_with_errors.docx`:
  - Critical concentration deviation ($15\%$ detected vs safety standard limit $10\%$)
  - Thermal runaway threshold violation ($140^\circ\text{C}$ vs safety limit $120^\circ\text{C}$)

---

## 6. Project Structure

```text
├── app.py                      # Main entry point (defaults to web, accepts --gui)
├── run_web.py                  # Local web application launcher (uvicorn + browser)
├── pyproject.toml              # Dependencies & packaging metadata
├── specguard/
│   ├── analyzers/              # 10 pure Python analysis & severity modules
│   ├── core/                   # Pipeline orchestrator, document parsers, models
│   ├── export/                 # PDF annotator, DOCX annotator, HTML/JSON reports
│   ├── models/                 # Dynamic model registry & ML services
│   ├── repository/             # Document archive & revision diff engine
│   ├── security/               # Audit logger & SHA-256 integrity verifier
│   ├── storage/                # SQLite database manager & repositories
│   ├── templates/              # Domain template manager & definitions
│   ├── training/               # Offline training pipelines & hardware manager
│   ├── gui/                    # Legacy PySide6 desktop GUI (preserved for rollback)
│   ├── server/                 # Local FastAPI service & REST API endpoints
│   └── web/                    # Modern offline HTML5/CSS3/JS user interface
│       ├── templates/          # Semantic index.html application shell
│       └── static/             # Pure vanilla CSS design system & JS components
├── demo_samples/               # Ready-to-analyze engineering test files
├── standards/                  # Local machine-readable standards (ASME, IEC, etc.)
├── templates/                  # Fixed domain templates (Mechanical, Electrical, Chemical)
└── tests/                      # Pytest automated test suite (68 passing tests)
```

---

## 7. License & Notice

SpecGuard is an engineering decision-support framework. All findings and suggested corrections must be verified by a qualified engineer prior to design or manufacturing execution.
