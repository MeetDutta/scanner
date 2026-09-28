/**
 * SpecGuard Executive Quality Dashboard View
 * 
 * Implements 4 distinct, authentic application states:
 * STATE 1 - EMPTY: No document or session analyzed. Clean hero card with "+ New Analysis",
 *                 and "Recent Analyses" ONLY if actual previous analyses exist.
 * STATE 2 - ANALYZING: Analysis running. Shows real document name, domain, progress, and stage.
 * STATE 3 - COMPLETED: Real analysis finished. Shows real document filename, domain, page count,
 *                      total findings, severity distribution, page heatmap from real pages,
 *                      issue categories, and inspection controls ("Open Document Inspection", "Document Overview").
 * STATE 4 - FAILED: Analysis failed. Shows real document name, failure error message, and "Retry / New Analysis".
 */

window.DashboardView = {
  async render(container) {
    // 1. STATE 2 / STATE 4: Check if an active analysis job is tracking
    const activeJobId = window.appState.get("activeJobId");
    if (activeJobId) {
      try {
        const job = await window.api.analysis.getJob(activeJobId);
        if (job) {
          if (job.status === "processing" || job.status === "running") {
            this.renderAnalyzing(container, job, window.appState.get("activeDocument"), window.appState.get("activeDomain"));
            return;
          } else if (job.status === "failed") {
            this.renderFailed(container, job, window.appState.get("activeDocument"));
            return;
          } else if (job.status === "completed") {
            window.appState.set("activeSessionId", job.session_id);
            window.appState.set("activeJobId", null);
          }
        }
      } catch (err) {
        console.warn("Could not check active job status for dashboard:", err);
      }
    }

    // 2. Deterministic session rehydration from persistent backend
    let sessionData = null;
    let rehydrateError = null;
    try {
      sessionData = await window.appState.rehydrateSession();
    } catch (e) {
      rehydrateError = e;
      console.warn("Could not rehydrate session for dashboard:", e);
    }

    const currentStatus = window.appState.get("analysisStatus");

    // Check if session retrieval failed
    if (currentStatus === "DATA_LOAD_FAILED" || rehydrateError) {
      const errMsg = rehydrateError ? rehydrateError.message : "The requested analysis session could not be retrieved from the persistent database.";
      this.renderLoadFailed(container, errMsg);
      return;
    }

    // Check if no analysis exists
    if (currentStatus === "NO_ANALYSIS") {
      let recentComparisons = [];
      try {
        const recentRes = await window.api.dashboard.getRecent(6);
        recentComparisons = (recentRes && recentRes.recent_comparisons) || [];
      } catch (e) {}
      this.renderEmpty(container, recentComparisons);
      return;
    }

    let activeDoc = window.appState.get("activeDocument");
    let sessionId = window.appState.get("activeSessionId");
    let findings = window.appState.get("activeFindings");
    let domain = window.appState.get("activeDomain");

    // 3. Fetch recent comparisons from database to check for session restoration & history table
    let recentComparisons = [];
    try {
      const recentRes = await window.api.dashboard.getRecent(6);
      recentComparisons = (recentRes && recentRes.recent_comparisons) || [];
    } catch (e) {
      console.warn("Could not fetch recent comparisons for dashboard:", e);
    }

    // 4. STATE 1 - EMPTY: If there is still no session or document, render clean empty dashboard
    if (!sessionId && !activeDoc) {
      this.renderEmpty(container, recentComparisons);
      return;
    }

    // 5. Fetch findings for active session if not already loaded into state - NEVER SILENTLY FALL BACK TO []
    if (sessionId && findings === null) {
      try {
        const res = await window.api.findings.list({ session_id: sessionId, limit: 500 });
        if (!res || !Array.isArray(res.findings)) {
          throw new Error("Invalid findings response from API.");
        }
        findings = res.findings;
        window.appState.set("activeFindings", findings);
      } catch (e) {
        console.error("Could not load findings for dashboard:", e);
        this.renderFindingsLoadFailed(container, sessionId, e.message);
        return;
      }
    } else if (findings === null) {
      this.renderFindingsLoadFailed(container, sessionId || "Unknown", "No findings data loaded in application state.");
      return;
    }

    // If page_count is not yet known on activeDoc, resolve from document info API
    if (activeDoc && (!activeDoc.page_count || activeDoc.page_count <= 0)) {
      try {
        const docId = activeDoc.file_hash || activeDoc.filename || sessionId;
        const info = await window.api.documents.getInfo(docId);
        if (info && info.page_count) {
          activeDoc.page_count = info.page_count;
          window.appState.set("activeDocument", activeDoc);
        }
      } catch (e) {
        console.warn("Could not fetch page count for document:", e);
      }
    }

    // Check if explicit verified zero findings:
    // Backend must explicitly confirm COMPLETED and total_findings === 0
    const isExplicitZero = (currentStatus === "ANALYSIS_COMPLETE_ZERO_FINDINGS") ||
      (findings.length === 0 && sessionData && (sessionData.status || "").toUpperCase() === "COMPLETED" && (sessionData.total_findings === 0 || sessionData.findings_count === 0));

    if (isExplicitZero) {
      this.renderZeroFindingsCompleted(container, {
        activeDoc,
        sessionId,
        domain: domain || (activeDoc && activeDoc.domain) || "Engineering",
        recentComparisons
      });
      return;
    }

    // 6. STATE 3 - COMPLETED: Render full analysis dashboard with REAL data
    this.renderCompleted(container, {
      activeDoc,
      sessionId,
      findings,
      domain: domain || (activeDoc && activeDoc.domain) || "Engineering",
      recentComparisons
    });
  },

  /**
   * Renders explicit error state when session retrieval fails.
   * Guarantees that API failures never degrade into "Total Findings: 0".
   */
  renderLoadFailed(container, message) {
    container.innerHTML = `
      <div style="max-width: 760px; margin: 48px auto; padding: 36px; background: var(--bg-surface); border: 1px solid var(--accent-critical); border-radius: var(--radius-lg); text-align: center; box-shadow: var(--shadow-md);">
        <div style="font-size: 44px; margin-bottom: 16px;">⚠️</div>
        <h2 style="font-size: 22px; font-weight: 700; color: var(--accent-critical); margin-bottom: 10px;">
          Unable to load analysis results.
        </h2>
        <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 24px; line-height: 1.6; max-width: 600px; margin-left: auto; margin-right: auto;">
          ${escapeHtml(message || "The requested analysis session could not be retrieved from the persistent database.")}
        </p>
        <div style="display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;">
          <button class="btn btn-primary" onclick="window.router.navigate('new_analysis')">
            + Start New Analysis
          </button>
          <button class="btn btn-secondary" onclick="window.location.hash = '#dashboard'; window.location.reload();">
            View Recent Analyses
          </button>
        </div>
      </div>
    `;
  },

  /**
   * Renders explicit error state when session exists but findings retrieval fails.
   */
  renderFindingsLoadFailed(container, sessionId, message) {
    container.innerHTML = `
      <div style="max-width: 760px; margin: 48px auto; padding: 36px; background: var(--bg-surface); border: 1px solid var(--accent-critical); border-radius: var(--radius-lg); text-align: center; box-shadow: var(--shadow-md);">
        <div style="font-size: 44px; margin-bottom: 16px;">⚠️</div>
        <h2 style="font-size: 22px; font-weight: 700; color: var(--accent-critical); margin-bottom: 10px;">
          Unable to load findings.
        </h2>
        <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 24px; line-height: 1.6; max-width: 600px; margin-left: auto; margin-right: auto;">
          The session <strong style="font-family: var(--font-mono);">${escapeHtml(sessionId)}</strong> exists in the database, but finding records could not be loaded: ${escapeHtml(message || "API query failed")}
        </p>
        <div style="display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;">
          <button class="btn btn-primary" onclick="window.location.reload()">
            🔄 Retry Loading Findings
          </button>
          <button class="btn btn-secondary" onclick="window.router.navigate('new_analysis')">
            Start New Analysis
          </button>
        </div>
      </div>
    `;
  },

  /**
   * STATE: Explicit verified completed analysis with 0 findings (Clean Document).
   * Backend explicitly confirms status = COMPLETED and total_findings = 0.
   */
  renderZeroFindingsCompleted(container, { activeDoc, sessionId, domain, recentComparisons }) {
    const docName = activeDoc ? activeDoc.filename : "Verified Engineering Document";
    const pageCount = (activeDoc && activeDoc.page_count) || 1;

    container.innerHTML = `
      <div class="dashboard-container" style="max-width: 1200px; margin: 0 auto; display: flex; flex-direction: column; gap: 24px;">
        <!-- Header -->
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px; border-bottom: 1px solid var(--border-default); padding-bottom: 16px;">
          <div>
            <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
              <h1 style="font-size: 22px; font-weight: 800; color: var(--text-primary); margin: 0;">
                ${escapeHtml(docName)}
              </h1>
              ${domain ? `<span class="badge badge-domain" style="text-transform: capitalize;">${escapeHtml(domain)}</span>` : ""}
              <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); font-weight: 700;">
                ✓ COMPLIANCE PASSED
              </span>
            </div>
            <div style="display: flex; align-items: center; gap: 16px; font-size: 13px; color: var(--text-muted); margin-top: 6px;">
              <span>Session: <strong style="font-family: var(--font-mono);">${escapeHtml(sessionId || "")}</strong></span>
              <span>•</span>
              <span>Pages: <strong>${pageCount}</strong></span>
              <span>•</span>
              <span>Status: <strong style="color: #10b981;">100% SPECIFICATION COMPLIANT</strong></span>
            </div>
          </div>
          <div style="display: flex; gap: 10px; align-items: center;">
            <button class="btn btn-primary" onclick="window.router.navigate('viewer')">
              👁️ View Document
            </button>
            <button class="btn btn-secondary" onclick="window.router.navigate('new_analysis')">
              + New Analysis
            </button>
          </div>
        </div>

        <!-- Verified Clean Banner -->
        <div class="card" style="border: 1px solid rgba(16, 185, 129, 0.3); background: rgba(16, 185, 129, 0.05); border-radius: var(--radius-lg); padding: 24px;">
          <div style="display: flex; align-items: center; gap: 18px;">
            <div style="font-size: 36px;">🛡️</div>
            <div>
              <div style="font-size: 16px; font-weight: 700; color: #10b981; margin-bottom: 4px;">
                Verified Specification Compliance — Zero Defects Detected
              </div>
              <div style="font-size: 13px; color: var(--text-secondary); line-height: 1.5;">
                The document was completely inspected across typography, section hierarchy, table and figure citations, grammar, and engineering parameters. The backend confirms zero non-conforming items.
              </div>
            </div>
          </div>
        </div>

        <!-- Counters -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px;">
          <div class="stat-card" style="padding: 16px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: var(--radius-md); text-align: center;">
            <div style="font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">Total Findings</div>
            <div style="font-size: 28px; font-weight: 800; color: #10b981; margin-top: 4px;">0</div>
          </div>
          <div class="stat-card" style="padding: 16px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: var(--radius-md); text-align: center;">
            <div style="font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">Critical</div>
            <div style="font-size: 28px; font-weight: 800; color: var(--text-muted); margin-top: 4px;">0</div>
          </div>
          <div class="stat-card" style="padding: 16px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: var(--radius-md); text-align: center;">
            <div style="font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">High</div>
            <div style="font-size: 28px; font-weight: 800; color: var(--text-muted); margin-top: 4px;">0</div>
          </div>
          <div class="stat-card" style="padding: 16px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: var(--radius-md); text-align: center;">
            <div style="font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">Medium</div>
            <div style="font-size: 28px; font-weight: 800; color: var(--text-muted); margin-top: 4px;">0</div>
          </div>
          <div class="stat-card" style="padding: 16px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: var(--radius-md); text-align: center;">
            <div style="font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">Low</div>
            <div style="font-size: 28px; font-weight: 800; color: var(--text-muted); margin-top: 4px;">0</div>
          </div>
        </div>
      </div>
    `;
  },

  /**
   * STATE 1 - EMPTY: No document or session analyzed.
   * Displays clean hero card with "+ New Analysis" and "Recent Analyses" ONLY if real history exists.
   */
  renderEmpty(container, recentComparisons) {
    const hasHistory = recentComparisons && recentComparisons.length > 0;

    container.innerHTML = `
      <div class="dashboard-empty-container" style="max-width: 900px; margin: 0 auto; display: flex; flex-direction: column; gap: 24px;">
        <!-- Header Brand Intro -->
        <div style="text-align: center; margin-top: 16px;">
          <div style="display: inline-flex; align-items: center; gap: 10px; justify-content: center; margin-bottom: 6px;">
            <span style="font-size: 28px;">🛡️</span>
            <h1 style="font-size: 24px; font-weight: 800; color: var(--text-primary); letter-spacing: 0.5px; margin: 0;">
              SPECGUARD
            </h1>
          </div>
          <div style="font-size: 13px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px;">
            Engineering Document Quality & Compliance Inspection
          </div>
        </div>

        <!-- 1. True Empty State Hero Card -->
        <div class="card" style="border: 1px solid var(--border-default); box-shadow: var(--shadow-md); border-radius: var(--radius-lg);">
          <div class="card-body" style="padding: 44px 32px; text-align: center;">
            <div style="width: 64px; height: 64px; margin: 0 auto 18px auto; border-radius: 50%; background: var(--bg-surface-hover); display: flex; align-items: center; justify-content: center; font-size: 30px; border: 1px solid var(--border-subtle);">
              📄
            </div>
            <h2 style="font-size: 20px; font-weight: 800; color: var(--text-primary); margin: 0 0 10px 0;">
              No Analysis Available
            </h2>
            <p style="font-size: 14px; color: var(--text-secondary); max-width: 520px; margin: 0 auto 18px auto; line-height: 1.6;">
              Upload an engineering document to inspect it for:
            </p>

            <div style="display: inline-block; text-align: left; margin: 0 auto 26px auto;">
              <ul style="margin: 0; padding-left: 20px; font-size: 13.5px; color: var(--text-secondary); line-height: 1.9;">
                <li><strong style="color: var(--text-primary);">Formatting inconsistencies</strong></li>
                <li><strong style="color: var(--text-primary);">Structural problems</strong></li>
                <li><strong style="color: var(--text-primary);">TOC errors</strong></li>
                <li><strong style="color: var(--text-primary);">Figure and table issues</strong></li>
                <li><strong style="color: var(--text-primary);">Content issues</strong></li>
                <li><strong style="color: var(--text-primary);">Engineering and standards deviations</strong></li>
              </ul>
            </div>

            <div>
              <button class="btn btn-primary" id="btn-empty-new-analysis" onclick="window.router.navigate('new_analysis')" style="padding: 12px 28px; font-size: 14px; font-weight: 700; border-radius: var(--radius-md); box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35);">
                + New Analysis
              </button>
            </div>
          </div>
        </div>

        <!-- 2. Recent Analyses (ONLY rendered if actual previous analyses exist) -->
        ${hasHistory ? `
          <div class="card" style="border: 1px solid var(--border-default); border-radius: var(--radius-lg);">
            <div class="card-header" style="display: flex; justify-content: space-between; align-items: center; padding: 14px 20px;">
              <div class="card-title" style="font-size: 14px; font-weight: 700;">🕒 Recent Analyses</div>
              <button class="btn btn-outline btn-sm" onclick="window.router.navigate('history')">Full History →</button>
            </div>
            <div class="card-body" style="padding: 0;">
              <div class="table-wrapper" style="border: none; border-radius: 0;">
                <table class="findings-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Document</th>
                      <th>Domain</th>
                      <th>Findings</th>
                      <th>Critical</th>
                      <th>High</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${recentComparisons.map((c) => `
                      <tr onclick="window.DashboardView.openComparison('${c.comparison_id}', '${escapeHtml(c.document_filename)}')">
                        <td><strong class="finding-code-id">${c.comparison_id}</strong></td>
                        <td><strong>${escapeHtml(c.document_filename)}</strong></td>
                        <td><span class="badge badge-domain" style="text-transform: capitalize;">${escapeHtml(c.domain || "Mechanical")}</span></td>
                        <td><strong>${c.total_findings || 0}</strong></td>
                        <td><span style="color: var(--sev-critical); font-weight: 700;">${c.critical_count || 0}</span></td>
                        <td><span style="color: var(--sev-high); font-weight: 700;">${c.high_count || 0}</span></td>
                        <td>
                          <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); window.DashboardView.openComparison('${c.comparison_id}', '${escapeHtml(c.document_filename)}')">
                            Inspect
                          </button>
                        </td>
                      </tr>
                    `).join("")}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        ` : ""}
      </div>
    `;
  },

  /**
   * STATE 2 - ANALYZING: A real analysis is actively executing.
   */
  renderAnalyzing(container, job, activeDoc, domain) {
    const docName = (activeDoc && activeDoc.filename) || (job && job.filename) || "Document";
    const percent = (job && job.progress_percent) || 0;
    const currentStage = (job && job.current_stage) || "Analyzing document...";

    container.innerHTML = `
      <div style="max-width: 800px; margin: 20px auto; display: flex; flex-direction: column; gap: 20px;">
        <div class="card" style="border-left: 5px solid var(--accent-primary); box-shadow: var(--shadow-md);">
          <div class="card-body" style="padding: 28px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 12px;">
              <div>
                <span class="badge badge-info" style="font-weight: 700; margin-bottom: 8px;">⏳ ANALYSIS IN PROGRESS</span>
                <h2 style="font-size: 18px; font-weight: 800; color: var(--text-primary); margin: 4px 0 0 0;">
                  ${escapeHtml(docName)}
                </h2>
                ${domain ? `<span class="badge badge-domain" style="text-transform: capitalize; margin-top: 6px;">${escapeHtml(domain)}</span>` : ""}
              </div>
              <button class="btn btn-primary" onclick="window.router.navigate('progress')">
                View Live Progress →
              </button>
            </div>

            <div style="margin-top: 20px;">
              <div style="display: flex; justify-content: space-between; font-size: 13px; font-weight: 600; margin-bottom: 6px;">
                <span>${escapeHtml(currentStage)}</span>
                <span>${percent}%</span>
              </div>
              <div class="progress-bar-track" style="height: 10px; background: var(--bg-surface-hover); border-radius: 5px; overflow: hidden;">
                <div class="progress-bar-fill" style="width: ${percent}%; height: 100%; background: var(--accent-primary); transition: width 0.3s ease;"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  },

  /**
   * STATE 4 - FAILED: Analysis failed.
   */
  renderFailed(container, job, activeDoc) {
    const docName = (activeDoc && activeDoc.filename) || (job && job.filename) || "Document";
    const errMsg = (job && (job.error || job.message)) || "Analysis pipeline encountered an error.";

    container.innerHTML = `
      <div style="max-width: 800px; margin: 20px auto; display: flex; flex-direction: column; gap: 20px;">
        <div class="card" style="border-left: 5px solid var(--sev-critical); box-shadow: var(--shadow-md);">
          <div class="card-body" style="padding: 28px;">
            <span class="badge" style="background: rgba(239, 68, 68, 0.15); color: var(--sev-critical); border: 1px solid var(--sev-critical); font-weight: 700; margin-bottom: 8px;">
              ❌ ANALYSIS FAILED
            </span>
            <h2 style="font-size: 18px; font-weight: 800; color: var(--text-primary); margin: 8px 0;">
              ${escapeHtml(docName)}
            </h2>
            <div style="font-size: 13.5px; color: var(--text-secondary); background: var(--bg-surface-hover); padding: 12px 16px; border-radius: var(--radius-md); border: 1px solid var(--border-subtle); margin: 16px 0;">
              ${escapeHtml(errMsg)}
            </div>
            <div style="display: flex; gap: 10px;">
              <button class="btn btn-primary" onclick="window.router.navigate('new_analysis')">
                Retry / New Analysis
              </button>
            </div>
          </div>
        </div>
      </div>
    `;
  },

  /**
   * STATE 3 - COMPLETED: Full inspection dashboard populated strictly with REAL analysis data.
   */
  renderCompleted(container, { activeDoc, sessionId, findings, domain, recentComparisons }) {
    const crit = findings.filter((f) => (f.severity || "").toUpperCase() === "CRITICAL").length;
    const high = findings.filter((f) => (f.severity || "").toUpperCase() === "HIGH").length;
    const med = findings.filter((f) => (f.severity || "").toUpperCase() === "MEDIUM").length;
    const low = findings.filter((f) => (f.severity || "").toUpperCase() === "LOW").length;
    const info = findings.filter((f) => {
      const s = (f.severity || "").toUpperCase();
      return s === "INFORMATIONAL" || s === "INFO";
    }).length;

    // Standardized canonical category mapping preserving exact detector categories
    function normalizeCategory(cat) {
      if (!cat) return "FORMATTING";
      const c = String(cat).trim().toUpperCase();
      if (c === "SPELLING" || c.includes("SPELL")) return "SPELLING";
      if (c === "GRAMMAR" || c === "GRAMMAR & SPELLING") return "GRAMMAR";
      if (c === "TOC" || c.includes("TABLE OF CONTENTS")) return "TOC";
      if (c === "FIGURE_REFERENCE" || c === "FIGURE" || c.includes("FIGURE")) return "FIGURE_REFERENCE";
      if (c === "TABLE_VALUE" || c === "TABLE" || c.includes("TABLE")) return "TABLE_VALUE";
      if (c === "DOCUMENT_CONTROL" || c.includes("CONTROL") || c.includes("VERSION")) return "DOCUMENT_CONTROL";
      if (c === "NUMBERING" || c.includes("NUMBER")) return "NUMBERING";
      if (c === "MISSING_CONTENT" || c.includes("MISSING")) return "MISSING_CONTENT";
      if (c === "CONTRADICTION" || c.includes("CONTRADICT") || c.includes("LOGICAL")) return "CONTRADICTION";
      if (c === "FORMATTING" || c.includes("FORMAT") || c.includes("LAYOUT") || c.includes("TYPO")) return "FORMATTING";
      if (c === "MIXED") return "MIXED";
      return c;
    }

    const catMap = {
      "SPELLING": 0,
      "GRAMMAR": 0,
      "FORMATTING": 0,
      "TOC": 0,
      "FIGURE_REFERENCE": 0,
      "TABLE_VALUE": 0,
      "DOCUMENT_CONTROL": 0,
      "NUMBERING": 0,
      "MISSING_CONTENT": 0,
      "CONTRADICTION": 0
    };

    findings.forEach((f) => {
      const cat = normalizeCategory(f.category);
      catMap[cat] = (catMap[cat] || 0) + 1;
    });

    // Real page count from parsed document
    const totalPages = (activeDoc && activeDoc.page_count && activeDoc.page_count > 0) ? activeDoc.page_count : 1;
    const pageCounts = {};
    for (let p = 1; p <= totalPages; p++) {
      pageCounts[p] = 0;
    }
    findings.forEach((f) => {
      const p = f.page_number || f.page;
      if (p && pageCounts[p] !== undefined) {
        pageCounts[p]++;
      }
    });
    const maxPageIssues = Math.max(1, ...Object.values(pageCounts));

    container.innerHTML = `
      <div class="findings-container">
        <!-- 1. Active Document Quality Header -->
        <div class="card" style="border-left: 5px solid ${crit > 0 ? 'var(--sev-critical)' : high > 0 ? 'var(--sev-high)' : '#10b981'};">
          <div class="card-body" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
            <div>
              <div style="display: flex; align-items: center; gap: 10px;">
                <h2 style="font-size: 18px; font-weight: 800; color: var(--text-primary); margin: 0;">
                  ${escapeHtml(activeDoc ? activeDoc.filename : "Analyzed Document")}
                </h2>
                ${domain ? `<span class="badge badge-domain" style="text-transform: capitalize;">${escapeHtml(domain)}</span>` : ""}
                <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #059669; border: 1px solid rgba(16, 185, 129, 0.3);">
                  ✓ INSPECTION READY
                </span>
              </div>
              <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">
                Session: <strong style="font-family: var(--font-mono);">${escapeHtml(sessionId || "")}</strong>
                • Pages: <strong>${totalPages}</strong>
                • Total Findings: <strong>${findings.length}</strong>
                • Inspection Mode: Local / LAN Mode
              </div>
            </div>

            <div style="display: flex; gap: 8px;">
              <button class="btn btn-secondary btn-sm" onclick="window.router.navigate('overview')">
                📑 Document Overview
              </button>
              <button class="btn btn-primary btn-sm" onclick="window.router.navigate('viewer')">
                👁️ Open Document Inspection
              </button>
              <button class="btn btn-outline btn-sm" onclick="window.router.navigate('reports')">
                📑 Reports
              </button>
              <button class="btn btn-outline btn-sm" onclick="window.router.navigate('new_analysis')">
                + New Analysis
              </button>
            </div>
          </div>
        </div>

        <!-- 2. Finding Severity Summary Row (Actual Counts) -->
        <div class="metrics-row">
          <div class="metric-card metric-primary">
            <span class="metric-label">Total Findings</span>
            <span class="metric-value">${findings.length}</span>
            <span class="metric-sub">Across All Categories</span>
          </div>
          <div class="metric-card metric-critical">
            <span class="metric-label">Critical</span>
            <span class="metric-value" style="color: var(--sev-critical);">${crit}</span>
            <span class="metric-sub">Blocks Compliance</span>
          </div>
          <div class="metric-card metric-high">
            <span class="metric-label">High Severity</span>
            <span class="metric-value" style="color: var(--sev-high);">${high}</span>
            <span class="metric-sub">Engineering Deviations</span>
          </div>
          <div class="metric-card metric-medium">
            <span class="metric-label">Medium Severity</span>
            <span class="metric-value" style="color: var(--sev-medium);">${med}</span>
            <span class="metric-sub">Standards Warnings</span>
          </div>
          <div class="metric-card metric-low">
            <span class="metric-label">Low Severity</span>
            <span class="metric-value" style="color: var(--sev-low);">${low}</span>
            <span class="metric-sub">Formatting Inconsistencies</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Informational</span>
            <span class="metric-value" style="color: var(--sev-info);">${info}</span>
            <span class="metric-sub">Observations</span>
          </div>
        </div>

        <!-- 3. Split: Page Issue Heatmap & Category Summary -->
        <div class="dashboard-split" style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
          <!-- Page Issue Heatmap (Only for actual document pages 1 to totalPages) -->
          <div class="card">
            <div class="card-header">
              <div class="card-title">🔥 Page Issue Heatmap</div>
              <span style="font-size: 11px; color: var(--text-muted);">${totalPages} Pages Analyzed</span>
            </div>
            <div class="card-body" style="padding: 12px 16px; max-height: 380px; overflow-y: auto;">
              <div class="page-heatmap-container" style="border: none; padding: 0;">
                ${Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => {
                  const count = pageCounts[p] || 0;
                  const pct = Math.max(count > 0 ? 8 : 0, Math.round((count / maxPageIssues) * 100));
                  let densityClass = "density-low";
                  if (count >= 5) densityClass = "density-critical";
                  else if (count >= 3) densityClass = "density-high";
                  else if (count >= 1) densityClass = "density-medium";

                  return `
                    <div class="heatmap-row" onclick="window.DashboardView.jumpToPage(${p})">
                      <span class="heatmap-page-label">Page ${p}</span>
                      <div class="heatmap-bar-track">
                        <div class="heatmap-bar-fill ${densityClass}" style="width: ${pct}%;"></div>
                      </div>
                      <span class="heatmap-count-badge" style="color: ${count > 0 ? 'var(--text-primary)' : 'var(--text-muted)'};">
                        ${count}
                      </span>
                    </div>
                  `;
                }).join("")}
              </div>
            </div>
          </div>

          <!-- Category Distribution (Real category statistics) -->
          <div class="card">
            <div class="card-header">
              <div class="card-title">📊 Issue Categories</div>
              <button class="btn btn-outline btn-sm" onclick="window.router.navigate('findings')">
                View All Findings →
              </button>
            </div>
            <div class="card-body" style="padding: 12px 16px;">
              <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 8px;">
                ${Object.entries(catMap).map(([cName, count]) => `
                  <div class="category-stat-card" style="padding: 10px;" onclick="window.DashboardView.jumpToCategory('${cName}')">
                    <span style="font-size: 11px; font-weight: 700; color: var(--text-muted);">${cName}</span>
                    <span style="font-size: 18px; font-weight: 800; color: ${count > 0 ? 'var(--text-primary)' : 'var(--text-muted)'};">
                      ${count}
                    </span>
                  </div>
                `).join("")}
              </div>
            </div>
          </div>
        </div>

        <!-- 4. Recent Document Inspections (if comparisons exist) -->
        ${recentComparisons && recentComparisons.length > 0 ? `
          <div class="card">
            <div class="card-header">
              <div class="card-title">🕒 Recent Document Inspections</div>
              <button class="btn btn-outline btn-sm" onclick="window.router.navigate('history')">Full History →</button>
            </div>
            <div class="card-body" style="padding: 0;">
              <div class="table-wrapper" style="border: none; border-radius: 0;">
                <table class="findings-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Document</th>
                      <th>Domain</th>
                      <th>Findings</th>
                      <th>Critical</th>
                      <th>High</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${recentComparisons.map((c) => `
                      <tr onclick="window.DashboardView.openComparison('${c.comparison_id}', '${escapeHtml(c.document_filename)}')">
                        <td><strong class="finding-code-id">${c.comparison_id}</strong></td>
                        <td><strong>${escapeHtml(c.document_filename)}</strong></td>
                        <td><span class="badge badge-domain" style="text-transform: capitalize;">${escapeHtml(c.domain || "Mechanical")}</span></td>
                        <td><strong>${c.total_findings || 0}</strong></td>
                        <td><span style="color: var(--sev-critical); font-weight: 700;">${c.critical_count || 0}</span></td>
                        <td><span style="color: var(--sev-high); font-weight: 700;">${c.high_count || 0}</span></td>
                        <td>
                          <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); window.DashboardView.openComparison('${c.comparison_id}', '${escapeHtml(c.document_filename)}')">
                            Inspect
                          </button>
                        </td>
                      </tr>
                    `).join("")}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        ` : ""}
      </div>
    `;
  },

  async openComparison(cmpId, filename) {
    try {
      const detail = await window.api.history.get(cmpId);
      if (detail && detail.document) {
        window.appState.set("activeSessionId", detail.comparison_id);
        window.appState.set("activeDomain", detail.domain ? detail.domain.toLowerCase() : "mechanical");
        window.appState.set("activeFindings", detail.findings || []);
        window.appState.set("activeDocument", {
          filename: detail.document.filename,
          file_path: detail.document.original_path,
          file_hash: detail.document_sha256,
          file_type: detail.document.file_type,
          page_count: detail.document.page_count
        });
      } else {
        window.appState.set("activeSessionId", cmpId);
        window.appState.set("activeDocument", { filename: filename, file_hash: cmpId, page_count: 1 });
      }
      window.router.navigate("dashboard");
    } catch (e) {
      console.error("Error opening comparison:", e);
      window.appState.set("activeSessionId", cmpId);
      window.appState.set("activeDocument", { filename: filename, file_hash: cmpId, page_count: 1 });
      window.router.navigate("dashboard");
    }
  },

  jumpToPage(pageNum) {
    window.appState.set("activePage", pageNum);
    window.router.navigate("viewer", { page: pageNum });
  },

  jumpToCategory(category) {
    window.router.navigate("findings", { category });
  }
};
