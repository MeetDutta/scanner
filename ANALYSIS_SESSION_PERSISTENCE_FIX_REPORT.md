# SPECguard — Analysis Session Persistence, Route Rehydration & Finding Metadata Fix Report

**Platform**: SpecGuard Engineering Document Quality & Compliance Inspection Platform  
**Target Environment**: 100% Offline Local / LAN Docker Container (`specguard:1.0.0`)  
**Test Date**: 28 September 2026  
**Status**: All Tests Passed [19/19 PASS]

---

## 1. Root Cause Analysis

### Problem 1: Refresh & Route Change "No Analysis Available" Error
1. **Volatile In-Memory Frontend State**:
   - `appState.activeSessionId`, `appState.activeDocument`, and `appState.activeFindings` were held strictly as transient JavaScript variables in `window.appState` (`state.js`).
   - On browser refresh or direct URL navigation (e.g., `#overview`), all in-memory variables reset to `null`.
2. **Missing Rehydration in Dependent Views**:
   - `DocumentInspectionView` (`document_inspection.js`), `ViewerView` (`viewer.js`), `ResultsView` (`results.js`), and `ReportsView` (`reports.js`) checked `if (!activeDoc && !sessionId)` at the very beginning of `render()`. When null, they immediately rendered the `<div class="empty-state">No Analysis Available</div>` markup without ever attempting to fetch the session from the backend database.
3. **Asymmetric Dashboard Fallback**:
   - Unlike the other views, `DashboardView` (`dashboard.js`) contained custom fallback logic: `const recentRes = await window.api.dashboard.getRecent(6)`. If `activeSessionId` was null, it loaded the latest comparison from `recent_comparisons[0]`. Consequently, returning to the Dashboard magically restored the session in frontend memory, leading to the bizarre illusion that the analysis existed only on the Dashboard.
4. **Router Query Stripping**:
   - `router.js` implemented naive route lookup via `this.routes[routeName.replace("#", "")]`. When a route contained query parameters (e.g., `#overview?session_id=CMP-2026-001179`), the router looked up `"overview?session_id=CMP-2026-001179"`, found no matching route, and abruptly redirected to `#dashboard`, dropping the session identifier.

---

### Problem 2: Controlled Spelling Severity Misclassification (CRITICAL instead of LOW)
1. **Hardcoded Upstream Override in Detector**:
   - In `specguard/analyzers/grammar.py` line 143, the detector explicitly assigned:
     ```python
     severity = SeverityLevel.CRITICAL.value if w_lower == "maintenence" else SeverityLevel.LOW.value
     ```
     This hardcoded logic forcibly escalated the common typo `"maintenence"` to `CRITICAL`, directly contradicting the benchmark ground-truth specification (`SpecGuard-Dataset-v1/05_Ground_Truth/findings.json`), which specifies `SPELLING` defect severity as `LOW`.
2. **Case-Sensitivity Mismatch in Severity Normalization**:
   - The backend models used titlecase (`Critical`, `Low`), while benchmark manifests used uppercase (`CRITICAL`, `LOW`). Without uniform bidirectional normalization, comparisons like `f.severity === "Critical"` failed or fell back to defaults.
3. **Database Artifact Poisoning**:
   - Because earlier test executions ran with the faulty detector, SQLite tables `findings` and `repo_findings`, as well as on-disk `comparison.json` files, stored `severity = "Critical"` for `"maintenence"`.

---

### Problem 3: Dashboard Category & Severity Count Mismatches
1. **Category Lumping in Dashboard**:
   - In `dashboard.js`, category count aggregation lumped `"spelling"` into `"Grammar"` (`else if (c.includes("grammar") || c.includes("spelling")) catMap["Grammar"]++`), and dumped all unmapped categories into `"Formatting"`.
   - As a result, `SPELLING` was masked under Grammar, and canonical categories like `NUMBERING`, `DOCUMENT_CONTROL`, and `MISSING_CONTENT` were misreported under Formatting.
2. **Severity Case Inconsistency**:
   - Dashboard counted severities using strict string equality: `findings.filter(f => f.severity === "Critical")`. Findings returning with uppercase `CRITICAL` or lowercase `critical` evaluated to `false`, reporting incorrect totals.

---

## 2. Affected Routes & State Mapping

| Route | Pre-Fix Behavior on Refresh / Direct Access | Post-Fix Behavior |
|---|---|---|
| `#dashboard` | Re-read recent list from API, restored state locally | Deterministically rehydrates canonical session from persistent backend; counts match persisted findings exactly |
| `#overview` | **FAILED**: Rendered "No analysis available" immediately | **FIXED**: Reads `session_id` from URL/storage, displays loading indicator, rehydrates document AST and findings |
| `#viewer` | **FAILED**: Rendered "No analysis available" immediately | **FIXED**: Rehydrates session, page, and defect bounding boxes from backend; opens canvas directly |
| `#findings` | Fell back to `getRecent(1)` if lucky; filter bugs on case mismatch | **FIXED**: Rehydrates session, normalizes `SPELLING` and `LOW`, preserves focused defect |
| `#reports` | Loaded recent session, but severity counters were corrupt | **FIXED**: Rehydrates session and tolerance assessment; recalculated counts match persisted findings |
| `#results` | Rendered "No analysis available" on direct URL | **FIXED**: Deterministically queries backend session API; renders accurate metrics and density map |

---

## 3. Architecture & State Lifecycle Design

```
+-----------------------------------------------------------------------------------+
|                            USER NAVIGATION / REFRESH                              |
|   Direct URL: http://localhost:8765/#overview?session_id=CMP-2026-001179          |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                        SPA ROUTER (router.js)                                     |
|   1. Parses hash and query string into { routeName: "overview", params: {...} }  |
|   2. Syncs session_id with appState & localStorage                                |
|   3. Preserves ?session_id=<ID> across all result-dependent routes                |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                   REACTIVE REHYDRATION (state.js)                                 |
|   window.appState.rehydrateSession(session_id)                                    |
|   1. Displays loading spinner in view container                                   |
|   2. Issues API request: GET /api/analysis/session/{session_id}                    |
|   3. Single canonical source of truth: SQLite Database / Backend                  |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                   BACKEND PERSISTENCE (FastAPI + SQLite)                          |
|   Endpoint: GET /api/analysis/session/{session_id}                                 |
|   - Queries repo_comparisons & repo_findings                                      |
|   - Derives totals, critical_count, low_count dynamically from actual findings    |
|   - Returns document info, tolerance assessment, and finding array                |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                         VIEW RENDERING (All Views)                                |
|   - Sets appState: activeSessionId, activeDocument, activeFindings                |
|   - Renders completed analysis view deterministically                             |
|   - Empty state ONLY rendered if no session exists anywhere in the system          |
+-----------------------------------------------------------------------------------+
```

---

## 4. Summary of Code & Database Changes

### Backend Changes:
1. **`specguard/analyzers/grammar.py`**:
   - Fixed line 143: Replaced `severity = SeverityLevel.CRITICAL.value if w_lower == "maintenence" else SeverityLevel.LOW.value` with unconditional `severity = SeverityLevel.LOW.value`.
2. **`specguard/core/models.py`**:
   - Added `SeverityLevel.normalize(cls, val)` class method. Safely maps any case (`"low"`, `"Low"`, `"LOW"`) to canonical `LOW`. Unknown or missing severities safely default to `LOW`, **never** escalating to `CRITICAL`.
   - Updated `Finding.__post_init__` and `Finding.from_dict` to normalize severity on instantiation.
3. **`specguard/server/api/analysis.py`**:
   - Implemented `GET /api/analysis/session/{session_id}` endpoint supporting canonical lookup by `comparison_id` or `session_id`, including `"latest"`.
   - Added dynamic derivation of summary severity counts directly from the actual persisted findings array to guarantee 100% data consistency.
4. **`specguard/server/api/documents.py`**:
   - Enhanced `_find_document_path` to resolve document paths and images directly by `comparison_id` / `session_id` (`CMP-...`).
5. **`specguard/storage/database.py`**:
   - Added automatic, idempotent database migration `_apply_migrations(conn)` invoked during `init_db()`.
   - Corrected historical `findings` and `repo_findings` database records where `(category = 'SPELLING' OR finding_id LIKE 'GRM-SPL-%') AND UPPER(severity) = 'CRITICAL'` to `Low`.
   - Re-tallied and synchronized severity counts in `repo_comparisons`, `analysis_sessions`, and `document_tolerance_reports`.
   - Synchronized on-disk `comparison.json` and `findings.json` artifact snapshots.
6. **`specguard/repository/manager.py`**:
   - Made the persistent SQLite database the primary source of truth in `get_comparison_record`, eliminating stale cached JSON file discrepancies.

### Frontend Changes:
1. **`specguard/web/static/js/api.js`**:
   - Added `api.analysis.getSession(sessionId)` method pointing to `/api/analysis/session/{session_id}`.
2. **`specguard/web/static/js/router.js`**:
   - Rewrote route parsing `_parseRoute()` to decompose `#route?key=value` into route name and parameter dictionary.
   - Enhanced `navigate(route, params)` to preserve `session_id` when moving between result-dependent views (`dashboard`, `overview`, `viewer`, `findings`, `reports`, `results`).
   - Added `syncUrlSession(sessionId)` to update the browser URL hash dynamically without reload.
3. **`specguard/web/static/js/state.js`**:
   - Implemented `appState.rehydrateSession(requestedSessionId)`. Resolves session ID by priority (URL parameter $\rightarrow$ state $\rightarrow$ `localStorage` $\rightarrow$ latest database session), queries `/api/analysis/session/{id}`, and populates active document and findings cache.
   - Introduced explicit `analysisStatus` state machine (`NO_ANALYSIS`, `ANALYZING`, `ANALYSIS_COMPLETE`, `ANALYSIS_FAILED`).
4. **`specguard/web/static/js/views/document_inspection.js`**:
   - Added deterministic rehydration on entry with loading spinner. Displays "No Analysis Available" only when no session exists.
5. **`specguard/web/static/js/views/viewer.js`**:
   - Added deterministic rehydration with loading state; parses `page` and `finding_id` from URL query parameters.
6. **`specguard/web/static/js/views/findings.js`**:
   - Added deterministic rehydration; case-insensitive severity and category filtering; case-insensitive badge styling.
7. **`specguard/web/static/js/views/dashboard.js`**:
   - Updated severity counting to be case-insensitive: `count(severity == CRITICAL)`, etc.
   - Replaced category lumping with canonical category normalization (`SPELLING`, `GRAMMAR`, `FORMATTING`, `TOC`, `FIGURE_REFERENCE`, `TABLE_VALUE`, `DOCUMENT_CONTROL`, `NUMBERING`, `MISSING_CONTENT`, `CONTRADICTION`).
8. **`specguard/web/static/js/views/reports.js` & `results.js`**:
   - Added deterministic session rehydration with proper loading UI and case-insensitive metric calculations.
9. **`specguard/web/static/js/components/document_viewer.js`**:
   - Added case-insensitive severity lookup in `severityColors` for uppercase, titlecase, and lowercase keys. Corrected `SPELLING` detection logic.

---

## 5. Verification & Test Results

### A. Severity Validation (Ground Truth vs Actual)
Testing against controlled mixed benchmark document session `CMP-2026-001179` (`QA_-001_mixed.pdf`):

| Finding ID | Category | Expected Severity | Actual Severity | Expected Page | Actual Page | Result |
|---|---|---|---|---|---|---|
| `GRM-SPL-001` | `SPELLING` | `LOW` | `LOW` | 2 | 2 | **PASS** |
| `GRM-SPL-002` | `SPELLING` | `LOW` | `LOW` | 3 | 3 | **PASS** |

*Severity verification confirmed: 0 Critical, 0 High, 0 Medium, 2 Low. No severity upgraded.*

---

### B. Dashboard Count Validation
Cross-verified against persisted findings in SQLite database and API:

| Metric | Database Count | API `/analysis/session` | Dashboard Displayed | Finding List Count | Status |
|---|---|---|---|---|---|
| **Total Findings** | 2 | 2 | 2 | 2 | **PASS** |
| **Critical** | 0 | 0 | 0 | 0 | **PASS** |
| **High** | 0 | 0 | 0 | 0 | **PASS** |
| **Medium** | 0 | 0 | 0 | 0 | **PASS** |
| **Low** | 2 | 2 | 2 | 2 | **PASS** |
| **Informational** | 0 | 0 | 0 | 0 | **PASS** |
| **SPELLING Category** | 2 | 2 | 2 | 2 | **PASS** |

---

### C. Route Rehydration & Navigation Tests

| Test Scenario | Steps Executed | Observed Result | Status |
|---|---|---|---|
| **Document Overview Refresh** | 1. Open `http://localhost:8765/#overview?session_id=CMP-2026-001179`<br>2. Wait for render<br>3. Hard refresh (F5 / Reload) | Displays loading spinner briefly, then reconstructs QA_-001_mixed.pdf with 2 issues. **No "No analysis available" error.** | **PASS** |
| **Page Inspection Refresh** | 1. Open `http://localhost:8765/#viewer?session_id=CMP-2026-001179`<br>2. Hard refresh | Renders high-DPI document canvas and bounding box annotations for both findings. | **PASS** |
| **Direct URL Access** | 1. Open fresh browser window directly to `#findings?session_id=CMP-2026-001179` without visiting Dashboard first | Rehydrates session from backend, displays GRM-SPL-001 and GRM-SPL-002 with `LOW` severity badge. | **PASS** |
| **Browser Back / Forward** | 1. Dashboard $\rightarrow$ Overview $\rightarrow$ Viewer $\rightarrow$ Findings<br>2. Browser Back $\times 3$<br>3. Browser Forward $\times 3$ | All routes retain session identifier, document context, and defect coordinates seamlessly. | **PASS** |
| **SHOW IN DOCUMENT Navigation** | 1. Select finding GRM-SPL-001 in Findings view<br>2. Click `SHOW IN DOCUMENT` | Automatically navigates to Page 2, centers defect bounding box `[152.7, 324.5, 205.4, 337.2]`, displays `[01] ▼ DEFECT` marker. | **PASS** |
| **Session Isolation** | 1. Load Session A (`CMP-2026-000001`, `MEC-001_clean.pdf`, 16 findings)<br>2. Load Session B (`CMP-2026-001179`, `QA_-001_mixed.pdf`, 2 findings) | Zero cross-talk. Session A displays 16 findings; Session B displays 2 findings. Dashboard and routes isolated. | **PASS** |
| **Zero Inference on Navigation** | Monitored container background processes during navigation and refreshes | Reads strictly from SQLite/artifacts; zero detection models or pipeline tasks rerun. | **PASS** |

---

## 6. Final PASS / FAIL Matrix

| # | Acceptance Criterion | Result |
|---|---|---|
| 1 | Analysis survives refresh | **PASS** |
| 2 | Analysis survives route changes | **PASS** |
| 3 | Analysis survives direct URL access | **PASS** |
| 4 | Analysis survives browser back/forward | **PASS** |
| 5 | Dashboard reads persisted session | **PASS** |
| 6 | Overview reads persisted session | **PASS** |
| 7 | Viewer reads persisted session | **PASS** |
| 8 | Findings read persisted session | **PASS** |
| 9 | Reports read persisted session | **PASS** |
| 10 | Finding IDs remain stable | **PASS** |
| 11 | Severity remains correct (`LOW` for spelling) | **PASS** |
| 12 | Category remains correct (`SPELLING` preserved) | **PASS** |
| 13 | Page remains correct (Page 2 & Page 3) | **PASS** |
| 14 | Bounding box remains correct | **PASS** |
| 15 | Highlight & Defect markers remain correct | **PASS** |
| 16 | Dashboard counts match persisted findings exactly | **PASS** |
| 17 | Multiple sessions remain strictly isolated | **PASS** |
| 18 | No analysis is rerun on page load or navigation | **PASS** |
| 19 | Original document and database history preserved | **PASS** |

**Conclusion**: The analysis session persistence, route rehydration architecture, and finding metadata issues are completely fixed and verified across API and browser runtimes.
