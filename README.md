# SpecGuard

**Academic Title:**
*SpecGuard: An Offline Hybrid Deep Learning and Computer Vision Framework for Intelligent Engineering Document Quality and Standards Compliance Analysis*

---

## 1. Overview & Research Contribution

**SpecGuard** is a 100% offline, production-grade engineering document intelligence and compliance analysis desktop application built with Python, PySide6, OpenCV, PyMuPDF, python-docx, openpyxl, and SQLite.

The framework implements a hybrid multi-layer architecture:
- **Computer Vision & OCR** extracts page geometry, line morphology, table grids, diagrams, margins, and bounding-box coordinates.
- **NLP & Deep Learning** extracts engineering propositions `(Entity, Parameter, Value, Unit, Condition, Location)` using a technical vocabulary whitelist.
- **Engineering Analysis** normalizes SI and imperial units (e.g. $1000\text{ V} = 1\text{ kV}$, $1\text{ MPa} = 10\text{ bar}$, $1000\text{ mm} = 1\text{ m}$).
- **Local Standards Knowledge Base** evaluates machine-readable rules (JSON/YAML) across **Mechanical**, **Electrical**, and **Chemical** engineering domains.
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

## 3. Analysis Engines (10 Independent Modules)

1. `FormattingAnalyzer`: Evaluates font consistency, font-size outliers, heading typefaces, margins, and line spacing.
2. `StructureAnalyzer`: Parses document outline hierarchy trees; detects broken numbering sequences (e.g. 3.1 $\to$ 3.3, missing 3.2), depth jumps, duplicate headers, and missing mandatory sections.
3. `TOCAnalyzer`: Cross-validates Table of Contents against actual parsed document headings and page indices, identifying page number drift and missing/extra entries.
4. `TableAnalyzer`: Inspects data tables for empty required specification cells, jagged rows, duplicate entries, and unit column consistency.
5. `GrammarAnalyzer`: Performs technical grammar and spelling validation with an engineering whitelist (500+ terms) to prevent false positives on legitimate technical terminology.
6. `SemanticAnalyzer`: Extracts structured propositions with bounding-box coordinate tracking; flags ambiguous datums (e.g., pressure without gauge/absolute reference) and missing phase configurations.
7. `LogicalAnalyzer`: Maintains a document-wide parameter registry; detects cross-page contradictory values and $\text{Minimum} > \text{Maximum}$ boundary inversions.
8. `EngineeringAnalyzer`: Domain-specific parameter parsers for Mechanical (tolerances, fits, surface roughness Ra, pressure), Chemical (concentrations, flash points, runaway temperatures), and Electrical (voltages, feeder currents, frequencies, power).
9. `StandardsAnalyzer`: Evaluates extracted parameters against local JSON/YAML standard rules.
10. `SeverityEngine`: Computes multi-factor priority scores:
    $$\text{Priority Score} = w_{\text{sev}}\cdot\text{Severity} + w_{\text{safety}}\cdot\text{SafetyImpact} + w_{\text{dev}}\cdot|\text{Deviation}| + w_{\text{std}}\cdot\text{StandardCriticality} + w_{\text{conf}}\cdot\text{Confidence} + w_{\text{cross}}\cdot\text{CrossImpact}$$

---

## 4. Installation & Quickstart

### Prerequisites
- Python 3.9+ (Python 3.11 recommended)
- macOS, Linux, or Windows

### Running SpecGuard

#### 1. Modern Web Application (Recommended)
```bash
# Launch the modern local web interface (opens default browser automatically)
./.venv/bin/python run_web.py

# Or run via main entry point:
./.venv/bin/python app.py
```
The application starts the local backend at `http://127.0.0.1:8765` and launches the user interface in your default browser.

#### 2. Legacy PySide6 Desktop GUI (Rollback Fallback)
```bash
./.venv/bin/python app.py --gui
```

### Running Automated Test Suite

```bash
./.venv/bin/pytest -v
```
All 68 tests (core analyzers, parsers, training pipelines, and web REST API endpoints) execute 100% offline.

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
