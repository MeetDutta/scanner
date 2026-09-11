"""
Publication-Grade Architecture & Operation Guide PDF Generator for SpecGuard.
Generates a comprehensive, beautifully styled multi-page PDF document detailing
the entire SpecGuard framework, algorithms, 10 analysis engines, workflow, and user guide.
"""

import os
import sys
from pathlib import Path
import pymupdf

OUTPUT_PDF = Path(__file__).resolve().parent / "SpecGuard_Comprehensive_Architecture_and_Operation_Guide.pdf"


def build_guide_html() -> str:
    return """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page {
    size: letter;
    margin: 40pt 45pt 45pt 45pt;
  }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 9.5pt;
    line-height: 1.5;
    color: #1e293b;
  }
  
  /* Headings */
  h1.doc-title {
    font-size: 24pt;
    font-weight: 900;
    color: #0b192c;
    margin-bottom: 4pt;
    letter-spacing: -0.5pt;
  }
  .doc-subtitle {
    font-size: 11pt;
    font-weight: 600;
    color: #0369a1;
    margin-bottom: 16pt;
    line-height: 1.3;
  }
  .meta-banner {
    background-color: #f1f5f9;
    border-left: 4pt solid #0284c7;
    padding: 8pt 12pt;
    margin-bottom: 18pt;
    font-size: 8.5pt;
    color: #475569;
  }
  
  h1 {
    font-size: 15pt;
    font-weight: 800;
    color: #0b192c;
    border-bottom: 1.5pt solid #cbd5e1;
    padding-bottom: 4pt;
    margin-top: 18pt;
    margin-bottom: 8pt;
  }
  h2 {
    font-size: 11.5pt;
    font-weight: 700;
    color: #0f3b60;
    margin-top: 12pt;
    margin-bottom: 5pt;
  }
  h3 {
    font-size: 10pt;
    font-weight: 700;
    color: #1e293b;
    margin-top: 8pt;
    margin-bottom: 3pt;
  }
  p {
    margin: 4pt 0 6pt 0;
    text-align: justify;
  }
  
  /* Callout box */
  .callout {
    background-color: #f8fafc;
    border: 1pt solid #cbd5e1;
    border-left: 3.5pt solid #f97316;
    padding: 8pt 10pt;
    margin: 8pt 0;
    border-radius: 2pt;
  }
  .callout-title {
    font-weight: 800;
    color: #c2410c;
    font-size: 9pt;
    margin-bottom: 3pt;
    text-transform: uppercase;
    letter-spacing: 0.5pt;
  }
  
  /* Tables */
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 8pt 0 12pt 0;
    font-size: 8.5pt;
  }
  th {
    background-color: #0f2744;
    color: #ffffff;
    font-weight: 700;
    text-align: left;
    padding: 5pt 7pt;
    border: 1pt solid #0f2744;
  }
  td {
    border: 1pt solid #cbd5e1;
    padding: 4.5pt 7pt;
    vertical-align: top;
  }
  tr:nth-child(even) td {
    background-color: #f8fafc;
  }
  
  /* Code and formula */
  code {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 8pt;
    background-color: #e2e8f0;
    padding: 1pt 3pt;
    border-radius: 2pt;
    color: #0f172a;
  }
  .formula-box {
    background-color: #f1f5f9;
    border: 1pt solid #cbd5e1;
    padding: 8pt 12pt;
    margin: 6pt 0;
    text-align: center;
    font-family: "Courier New", monospace;
    font-weight: bold;
    color: #0b192c;
  }
  
  /* Badges */
  .badge-critical { background-color: #fee2e2; color: #991b1b; font-weight: bold; padding: 1pt 4pt; border-radius: 2pt; }
  .badge-high { background-color: #ffedd5; color: #9a3412; font-weight: bold; padding: 1pt 4pt; border-radius: 2pt; }
  .badge-medium { background-color: #fef3c7; color: #92400e; font-weight: bold; padding: 1pt 4pt; border-radius: 2pt; }
  .badge-low { background-color: #dbeafe; color: #1e40af; font-weight: bold; padding: 1pt 4pt; border-radius: 2pt; }
  
  /* Workflow steps */
  .step-box {
    display: flex;
    background-color: #ffffff;
    border: 1pt solid #cbd5e1;
    border-left: 3pt solid #0284c7;
    padding: 6pt 8pt;
    margin-bottom: 6pt;
  }
  .step-num {
    font-weight: 800;
    color: #0284c7;
    margin-right: 6pt;
  }
  
  .page-break {
    page-break-before: always;
  }
</style>
</head>
<body>

<!-- COVER / HEADER BLOCK -->
<h1 class="doc-title">SPECGUARD</h1>
<div class="doc-subtitle">An Offline Hybrid Deep Learning and Computer Vision Framework for Intelligent Engineering Document Quality and Standards Compliance Analysis</div>

<div class="meta-banner">
  <strong>TECHNICAL ARCHITECTURE & OPERATION GUIDE</strong> &nbsp;|&nbsp; 
  <strong>Scope:</strong> Mechanical, Electrical, and Chemical Specifications &nbsp;|&nbsp; 
  <strong>Environment:</strong> 100% Offline Air-Gapped &nbsp;|&nbsp; 
  <strong>Release:</strong> Version 2.0 Production Clean Architecture
</div>

<h1>1. Executive Summary & Problem Domain</h1>
<p>
Engineering specifications and design compliance documents form the legal, operational, and safety backbone of modern infrastructure, manufacturing, aerospace, and process plants. A single overlooked discrepancy—such as an unhardened bearing journal tolerance (&plusmn;0.5 mm instead of &plusmn;0.05 mm), an incompatible electrical feeder voltage (230 V instead of 415 V three-phase), or an unauthorized solvent concentration (15% vs 10% thermal threshold)—can lead to catastrophic mechanical failure, electrical arc flash, chemical runaway, or regulatory shutdown.
</p>
<p>
Traditional document verification relies on exhaustive manual peer-review by senior engineers. This manual approach is notoriously slow, expensive, and susceptible to cognitive fatigue across hundred-page documents. Conversely, commercial cloud-based Large Language Models (LLMs) cannot be deployed in defense, aerospace, or critical infrastructure due to strict <strong>air-gap security policies</strong>, lack of geometric bounding-box localization, and propensity for numerical hallucination.
</p>
<div class="callout">
  <div class="callout-title">The SpecGuard Core Solution</div>
  <strong>SpecGuard</strong> resolves this dilemma by delivering a <strong>strictly 100% offline, local desktop application</strong> that couples local computer vision layout analysis, deterministic engineering rules, fixed domain template schemas, and optical verification to autonomously audit technical documents without cloud access.
</div>

<h1>2. Production Workflow: The 3-Stage Pipeline</h1>
<p>
SpecGuard is engineered around a minimal, distraction-free three-stage workflow tailored for industrial and government verification portals:
</p>

<div class="step-box">
  <span class="step-num">STAGE 01:</span>
  <div><strong>DOCUMENT UPLOAD</strong> — Ingests multi-format specifications (PDF, DOCX, XLSX, TXT, scanned images). Computes cryptographic SHA-256 hash, parses page geometry, and displays file metadata with one-click quick demo selectors.</div>
</div>

<div class="step-box">
  <span class="step-num">STAGE 02:</span>
  <div><strong>COMPARISON MODE SELECTION</strong> — The engineer explicitly selects the authoritative domain: <strong>Mechanical Engineering</strong> (ASME Y14.5 / ISO 2768), <strong>Electrical Engineering</strong> (IEC 60364 / IEEE 141), or <strong>Chemical Engineering</strong> (OSHA PSM / Process Safety). Explicit selection directly loads the authoritative template and local rule definitions with zero probabilistic routing.</div>
</div>

<div class="step-box">
  <span class="step-num">STAGE 03:</span>
  <div><strong>DOCUMENT PREVIEW & CERTIFIED EXPORT</strong> — Renders high-DPI document pages with vector bounding-box highlights overlaid on deviations. Provides synchronized page thumbnails, an interactive finding detail inspector, and one-click export for Certified Annotated PDF, standalone HTML audit reports, and structured JSON data.</div>
</div>

<div class="page-break"></div>

<h1>3. Multi-Format Ingestion & Computer Vision Layout Engine</h1>
<p>
Engineering documents arrive in heterogeneous formats ranging from vector digital PDFs to legacy scanned blueprints. SpecGuard implements a unified parsing pipeline:
</p>

<table>
  <tr>
    <th style="width: 22%;">Document Format</th>
    <th style="width: 38%;">Ingestion Mechanism</th>
    <th style="width: 40%;">Extracted Representations</th>
  </tr>
  <tr>
    <td><strong>Vector PDF (.pdf)</strong></td>
    <td>Native PyMuPDF (Fitz) vector dict traversal with sub-pixel resolution</td>
    <td>High-fidelity text blocks, font names, font sizes, bold/italic flags, coordinate bounding boxes (BBox), native vector lines</td>
  </tr>
  <tr>
    <td><strong>Word Document (.docx)</strong></td>
    <td>python-docx Abstract Syntax Tree (AST) paragraph and table parser</td>
    <td>Structural sections, headings, bullet lists, inline run styling, and cellular table grids</td>
  </tr>
  <tr>
    <td><strong>Spreadsheet (.xlsx / .xls)</strong></td>
    <td>openpyxl worksheet cell matrix evaluation</td>
    <td>Tabular data rows, header coordinates, numeric cell formats, formulas, and multi-sheet workbooks</td>
  </tr>
  <tr>
    <td><strong>Plain Text (.txt)</strong></td>
    <td>Universal UTF-8 line buffer parser</td>
    <td>Plain text lines, ASCII indentation trees, regex structural hierarchy</td>
  </tr>
  <tr>
    <td><strong>Scanned Images (.png, .jpg, .tiff)</strong></td>
    <td>OpenCV Computer Vision & Image Enhancement Pipeline</td>
    <td>Denoised, deskewed, contrast-normalized page bitmaps with OCR-detected text bounding boxes</td>
  </tr>
</table>

<h2>3.1 Scanned Image Preprocessing Pipeline</h2>
<p>
When processing scanned documents or rasterized drawings, SpecGuard's <code>ScannedDocumentPipeline</code> executes four deterministic computer vision stages:
</p>
<ol>
  <li><strong>Bilateral Filtering:</strong> Smooths background sensor noise and paper grain while preserving sharp edges of technical letters and dimensional tolerance symbols (d=9, sigmaColor=75, sigmaSpace=75).</li>
  <li><strong>Contrast Limited Adaptive Histogram Equalization (CLAHE):</strong> Equalizes local contrast across uneven lighting and blueprint folds without blowing out thin engineering dimension lines.</li>
  <li><strong>Otsu Adaptive Binarization:</strong> Automatically calculates optimal threshold values to separate dark technical ink from aged parchment or blueprints.</li>
  <li><strong>Skew Detection & Deskewing:</strong> Computes the minimum area bounding rectangle across foreground pixels to calculate the rotation angle &theta; and applies affine transformation to deskew the page prior to OCR.</li>
</ol>

<h1>4. Fixed Domain Template & Local Rules Architecture</h1>
<p>
SpecGuard enforces single authoritative document templates and local deterministic engineering rules per domain:
</p>
<div class="formula-box">
  templates/{domain}/ (template.json, sections.json, parameters.json, vocabulary.json)<br>
  + rules/{domain}/ (rules.json) &nbsp;&rarr;&nbsp; TemplateManager &nbsp;&rarr;&nbsp; Deterministic Analysis
</div>

<table>
  <tr>
    <th>Domain Mode</th>
    <th>Standards Reference</th>
    <th>Enforced Required Sections</th>
    <th>Key Parameter Constraints</th>
  </tr>
  <tr>
    <td><strong>Mechanical Engineering</strong></td>
    <td>ASME Y14.5-2018<br>ISO 2768 (General Tolerances)</td>
    <td>1. Scope<br>2. Operating Conditions<br>3. Manufacturing Tolerances<br>4. Surface Finish & Materials<br>5. Inspection & Quality</td>
    <td>Bearing Journal Tolerance &le; &plusmn;0.05 mm<br>Surface Finish Ra &le; 0.8 &mu;m<br>Maximum Operating Pressure &le; 16 bar<br>Max Operating Temp &le; 80&deg;C</td>
  </tr>
  <tr>
    <td><strong>Electrical Engineering</strong></td>
    <td>IEC 60364-5-52<br>IEEE Std 141 (Red Book)</td>
    <td>1. Scope & System Specs<br>2. Feeder & Distribution<br>3. Protection & Switchgear<br>4. Earthing & Insulation<br>5. Testing & Verification</td>
    <td>Industrial Feeder Voltage = 415 V (3-Phase)<br>Feeder Current Rating &le; 630 A<br>Grid Frequency = 50 Hz &plusmn; 0.5 Hz<br>Insulation Resistance &ge; 1.0 M&Omega;</td>
  </tr>
  <tr>
    <td><strong>Chemical Engineering</strong></td>
    <td>OSHA PSM 1910.119<br>Process Engineering PEP-102</td>
    <td>1. Process Description<br>2. Stream Compositions<br>3. Operating Envelope<br>4. Safety & Relief Limits<br>5. Quality Control</td>
    <td>Additive Concentration &le; 10 wt%<br>Thermal Runaway Temp &le; 120&deg;C<br>Relief Pressure Threshold &le; 25 bar<br>Flash Point &ge; 55&deg;C</td>
  </tr>
</table>

<div class="page-break"></div>

<h1>5. Step-by-Step Breakdown of the 10 Analysis Engines</h1>
<p>
When an engineer triggers analysis, SpecGuard orchestrates 10 independent modular analyzers. Each analyzer executes a discrete verification duty:
</p>

<h3>1. Formatting Analyzer (<code>FormattingAnalyzer</code>)</h3>
<p>
Inspects document typography and page layout consistency. Computes statistical frequency distributions of body fonts, sizes, heading styles, and margins. Detects rogue font substitutions (e.g. Times New Roman mixed into an Arial document) and heading size inversions where lower-level headers exceed higher-level font sizes.
</p>

<h3>2. Structure & Outline Hierarchy Analyzer (<code>StructureAnalyzer</code>)</h3>
<p>
Constructs an Abstract Outline Tree from document headings. Identifies broken numbering sequences (e.g. Section 3.1 &rarr; Section 3.3, flagging the missing Section 3.2), illegal section depth skips (e.g. 1.0 directly jumping to 1.1.1 without a 1.1 parent), duplicate section numbers, and missing mandatory sections defined in the domain template.
</p>

<h3>3. Table of Contents Synchronization Analyzer (<code>TOCAnalyzer</code>)</h3>
<p>
Parses the document's Table of Contents entries and cross-validates each title against the actual heading strings and page locations where those sections appear in the document body. Detects page drift (e.g. TOC states Section 3 is on Page 4, but text is on Page 2) and orphan entries.
</p>

<h3>4. Engineering Table Analyzer (<code>TableAnalyzer</code>)</h3>
<p>
Evaluates tabular structures for compliance with engineering data integrity. Flags jagged rows, missing cell values in mandatory specification columns, empty required tolerance fields, and mixed physical units across a single numeric data column.
</p>

<h3>5. Technical Grammar & Vocabulary Whitelist Engine (<code>GrammarAnalyzer</code>)</h3>
<p>
Executes technical grammar and spelling validation equipped with an engineering vocabulary whitelist containing over 500 domain-specific terms (e.g., <em>martensitic, austenitic, thixotropic, tribological, cavitation, dielectric, switchgear</em>). Prevents false-positive spelling alerts on legitimate technical terms while detecting genuine typos and duplicate consecutive words.
</p>

<h3>6. Engineering Parameter Extraction & Safe Unit Normalizer (<code>EngineeringAnalyzer</code>)</h3>
<p>
Extracts structured numerical parameters using comprehensive domain regex patterns. Pairs extracted values with physical units and executes deterministic unit normalization (e.g. 1 kV &rarr; 1000 V, 1 MPa &rarr; 10 bar, 0.5 mm &rarr; 500 &mu;m). Maps each parameter to its parent sentence and bounding-box coordinates for audit trail tracking.
</p>

<h3>7. Fixed Template Analyzer (<code>TemplateAnalyzer</code>)</h3>
<p>
Directly verifies the parsed document against the active domain template (<code>templates/{domain}/template.json</code>). Flags missing mandatory sections, non-standard section titles, out-of-order section arrangement, and missing critical design parameters.
</p>

<h3>8. Semantic Proposition & Ambiguity Analyzer (<code>SemanticAnalyzer</code>)</h3>
<p>
Scans extracted propositions for engineering ambiguity. Flags ungrounded specifications such as pressure specified simply in "bar" without designating gauge pressure (<code>barg</code>) versus absolute pressure (<code>bara</code>), and high-voltage AC specifications lacking single-phase vs three-phase identification.
</p>

<h3>9. Logical Consistency & Contradiction Engine (<code>LogicalAnalyzer</code>)</h3>
<p>
Maintains a document-wide parameter registry across all pages and tables. Detects cross-page conflicting specifications (e.g., maximum temperature stated as 80&deg;C on Page 1, but listed as 60&deg;C on Page 2), and boundary inversions where a stated minimum limit exceeds the maximum limit (&gt; 1% discrepancy threshold).
</p>

<h3>10. Local Standards Compliance Engine (<code>StandardsAnalyzer</code>)</h3>
<p>
Compares normalized extracted parameters against local deterministic rule tables (<code>rules/{domain}/rules.json</code>). Evaluates exact mathematical bounds (&le;, &ge;, ==, range) and flags safety-critical breaches (e.g. tolerance of &plusmn;0.5 mm exceeding ASME limit of &le; &plusmn;0.05 mm).
</p>

<div class="page-break"></div>

<h1>6. Mathematical Severity Scoring & Multi-Factor Priority Ranking</h1>
<p>
In industrial compliance auditing, thousands of minor formatting or typographical issues can obscure a fatal engineering flaw. SpecGuard implements a deterministic, multi-factor prioritization engine that calculates a <strong>Priority Score</strong> for every finding:
</p>

<div class="formula-box">
  Priority Score = w_sev &middot; S + w_safety &middot; SI + w_dev &middot; |&Delta;| + w_std &middot; C_std + w_conf &middot; Conf + w_cross &middot; CI
</div>

<table>
  <tr>
    <th style="width: 25%;">Variable / Factor</th>
    <th style="width: 15%;">Weight (w)</th>
    <th style="width: 60%;">Description & Metric</th>
  </tr>
  <tr>
    <td><strong>Base Severity (S)</strong></td>
    <td>25.0</td>
    <td>Discrete baseline: Critical = 4.0, High = 3.0, Medium = 2.0, Low = 1.0, Info = 0.5</td>
  </tr>
  <tr>
    <td><strong>Safety Impact (SI)</strong></td>
    <td>20.0</td>
    <td>Flags issues affecting personnel safety, explosion hazard, or electrical arc flash (0.0 to 1.0)</td>
  </tr>
  <tr>
    <td><strong>Normalized Deviation (|&Delta;|)</strong></td>
    <td>15.0</td>
    <td>Relative magnitude of numerical deviation: |Detected - Expected| / Expected</td>
  </tr>
  <tr>
    <td><strong>Standard Criticality (C_std)</strong></td>
    <td>15.0</td>
    <td>Legal/mandatory regulatory requirement vs advisory guideline (0.5 to 1.0)</td>
  </tr>
  <tr>
    <td><strong>Detection Confidence (Conf)</strong></td>
    <td>10.0</td>
    <td>Confidence score of the extractor (0.0 to 1.0)</td>
  </tr>
  <tr>
    <td><strong>Cross-Impact (CI)</strong></td>
    <td>15.0</td>
    <td>Cross-document ripple factor (e.g. parameter is referenced in multiple tables/pages)</td>
  </tr>
</table>

<p>
Findings are sorted in descending order of Priority Score into five discrete tiers:
<span class="badge-critical">CRITICAL</span> Safety or standards breach requiring immediate engineering halt.<br>
<span class="badge-high">HIGH</span> Major deviation likely to cause assembly failure or performance degradation.<br>
<span class="badge-medium">MEDIUM</span> Ambiguity, ungrounded datum, or cross-page discrepancy requiring clarification.<br>
<span class="badge-low">LOW</span> Formatting anomaly, font inconsistency, or minor table alignment imperfection.<br>
</p>

<h1>7. Interactive Visual Localization & Document Canvas</h1>
<p>
SpecGuard's Document Preview screen bridges the gap between text reports and visual engineering inspection:
</p>
<ul>
  <li><strong>Sub-Pixel Coordinate Transformation:</strong> Maps native PDF coordinate bounding boxes (points) to screen pixmap pixel space:
  <code>rx = pixmap.width / page.width</code>, <code>ry = pixmap.height / page.height</code>.</li>
  <li><strong>Color-Coded Vector Overlays:</strong> Renders semi-transparent highlight rectangles on the rendered page (Red for Critical, Orange for High, Amber for Medium, Blue for Low).</li>
  <li><strong>Click-to-Jump Navigation:</strong> Clicking any finding in the summary or finding inspector automatically turns the document canvas to the target page, zooms to the coordinate, and draws a pulsing highlight frame around the deviation.</li>
  <li><strong>Comprehensive Finding Detail Panel:</strong> Displays Finding ID, Category, Severity Badge, Detected Value, Expected Value, Deviation Calculation, Suggested Correction, and Exact Rule Reference.</li>
</ul>

<h1>8. Certified Export System</h1>
<p>
Results can be exported directly from the Document Preview toolbar with zero cloud involvement:
</p>
<ol>
  <li><strong>Certified Vector-Annotated PDF:</strong> Embeds permanent color-coded vector highlight boxes and native PDF comment popups containing finding explanations directly into the original PDF file.</li>
  <li><strong>Executive HTML Compliance Audit Report:</strong> Generates a standalone, CSS-responsive, air-gapped HTML audit dossier complete with executive summary charts, metadata bars, and sortable deviation tables.</li>
  <li><strong>Structured Findings JSON:</strong> Emits complete machine-readable audit data for downstream ERP, PLM, or archival databases.</li>
</ol>

<div class="page-break"></div>

<h1>9. Offline Air-Gap Security & Integrity Architecture</h1>
<p>
SpecGuard enforces strict enterprise security protections while eliminating unnecessary multi-user web authentication:
</p>
<ul>
  <li><strong>Cryptographic File Integrity:</strong> Generates SHA-256 digests of all ingested files to prevent untracked document tampering.</li>
  <li><strong>Path Traversal Defense:</strong> All export, backup, and restore routines rigorously sanitize target file paths against directory traversal attacks (<code>../</code>) and absolute root escapes.</li>
  <li><strong>Zero Network Dependency:</strong> The application contains zero network sockets, external API clients, telemetric pings, or cloud model loaders.</li>
  <li><strong>Local SQLite Database:</strong> Stores audit sessions, comparison runs, and finding archives locally at <code>data/specguard.db</code> without requiring a database server.</li>
</ul>

<h1>10. User & Operational Quickstart Guide</h1>

<h2>10.1 System Requirements & Setup</h2>
<p>
SpecGuard runs on standard hardware (macOS Apple Silicon/Intel, Linux x86_64, Windows 10/11) with Python 3.9+ (Python 3.11 recommended).
</p>
<pre><code># 1. Activate project virtual environment
source .venv/bin/activate

# 2. Launch SpecGuard Desktop Application
python app.py

# 3. Execute Automated Verification Test Suite (60 tests)
pytest -v
</code></pre>

<h2>10.2 Step-by-Step Verification Walkthrough</h2>
<ol>
  <li><strong>Launch Application:</strong> Run <code>python app.py</code>. The preflight diagnostic routine verifies 100% offline environment and loads the institutional header banner.</li>
  <li><strong>Select Document:</strong> On <strong>01 DOCUMENT UPLOAD</strong>, drag and drop any engineering document, browse files, or click one of the <strong>Quick Demo Sample</strong> buttons (e.g. <code>Load Mechanical Sample</code>). Click <strong>CONTINUE TO COMPARISON MODE &rarr;</strong>.</li>
  <li><strong>Choose Domain:</strong> On <strong>02 COMPARISON MODE</strong>, click the applicable domain:
  <strong>Mechanical</strong>, <strong>Electrical</strong>, or <strong>Chemical</strong>. Click <strong>COMPARE DOCUMENT &rarr;</strong>.</li>
  <li><strong>Review Progress:</strong> On <strong>DOCUMENT ANALYSIS IN PROGRESS</strong>, watch the automated checklist complete content extraction, structure analysis, parameter extraction, and standards matching.</li>
  <li><strong>Inspect Findings:</strong> On <strong>03 DOCUMENT PREVIEW</strong>, examine highlighted deviations directly on the document canvas. Use <strong>&blacktriangle; Prev Finding</strong> and <strong>&blacktriangledown; Next Finding</strong> to navigate issues.</li>
  <li><strong>Export Findings:</strong> Click <strong>EXPORT RESULT &blacktriangledown;</strong> to save a Certified Annotated PDF, HTML Audit Report, or JSON specification file.</li>
</ol>

<h2>10.3 Codebase Directory Map</h2>
<pre><code>SpecGuard/
├── app.py                      # Main desktop application entry point
├── pyproject.toml              # Dependencies & packaging metadata
├── templates/                  # Authoritative domain document templates
│   ├── mechanical/             # Mechanical template, sections, parameters, vocabulary
│   ├── electrical/             # Electrical template, sections, parameters, vocabulary
│   └── chemical/               # Chemical template, sections, parameters, vocabulary
├── rules/                      # Local deterministic standards rules
│   ├── mechanical/             # ASME Y14.5 / ISO 2768 rules.json
│   ├── electrical/             # IEC 60364 / IEEE 141 rules.json
│   └── chemical/               # Process Safety / OSHA rules.json
├── specguard/
│   ├── core/                   # DocumentParser, Pipeline, CV Layout, Models, Startup
│   ├── templates/              # TemplateManager (single source of truth)
│   ├── analyzers/              # 10 modular analysis engines + SeverityEngine
│   ├── export/                 # PDFAnnotator, ReportGenerator (HTML / JSON)
│   ├── gui/                    # 3-Stage Government Portal GUI (Upload, Mode, Preview)
│   ├── storage/                # SQLite local session persistence
│   └── repository/             # Immutable comparison archives
└── tests/                      # Full automated test suite (60 passed tests)
</code></pre>

<div class="meta-banner" style="margin-top: 24pt;">
  <strong>SpecGuard Technical Report &copy; 2026</strong> &nbsp;|&nbsp; 
  Autonomous Engineering Document Verification &nbsp;|&nbsp; 
  100% Offline Air-Gapped Architecture
</div>

</body>
</html>
"""


def generate_pdf():
    print(f"Generating SpecGuard Comprehensive Architecture Guide PDF...")
    html_content = build_guide_html()
    
    story = pymupdf.Story(html=html_content)
    writer = pymupdf.DocumentWriter(str(OUTPUT_PDF))
    
    page_rect = pymupdf.Rect(0, 0, 612, 792)  # Letter size
    body_rect = pymupdf.Rect(45, 45, 567, 747) # Margins
    
    page_count = 0
    more = 1
    while more:
        device = writer.begin_page(page_rect)
        more, _ = story.place(body_rect)
        story.draw(device)
        writer.end_page()
        page_count += 1
        
    writer.close()
    
    # Second pass: Open with PyMuPDF to stamp running headers, footers & page numbers
    doc = pymupdf.open(str(OUTPUT_PDF))
    total_pages = len(doc)
    
    for i, page in enumerate(doc):
        # Skip header on page 1 (cover)
        if i > 0:
            # Top running header
            page.insert_text(
                pymupdf.Point(45, 30),
                "SPECGUARD — ENGINEERING DOCUMENT VERIFICATION FRAMEWORK",
                fontsize=7.5,
                fontname="helv",
                color=(0.3, 0.4, 0.5)
            )
            # Top decorative rule
            page.draw_line(pymupdf.Point(45, 35), pymupdf.Point(567, 35), color=(0.8, 0.85, 0.9), width=0.75)
            
        # Running bottom footer
        page.draw_line(pymupdf.Point(45, 760), pymupdf.Point(567, 760), color=(0.8, 0.85, 0.9), width=0.75)
        page.insert_text(
            pymupdf.Point(45, 772),
            "100% Offline Air-Gapped Architecture • Confidential Technical Report",
            fontsize=7.5,
            fontname="helv",
            color=(0.4, 0.5, 0.6)
        )
        page_str = f"Page {i + 1} of {total_pages}"
        page.insert_text(
            pymupdf.Point(515, 772),
            page_str,
            fontsize=7.5,
            fontname="helv",
            color=(0.2, 0.3, 0.4)
        )
        
    doc.save(str(OUTPUT_PDF), incremental=True, encryption=pymupdf.PDF_ENCRYPT_KEEP)
    doc.close()
    
    file_size_kb = OUTPUT_PDF.stat().st_size / 1024
    print(f"Successfully generated: {OUTPUT_PDF}")
    print(f"Pages: {total_pages} | Size: {file_size_kb:.1f} KB")


if __name__ == "__main__":
    generate_pdf()
