/**
 * SpecGuard Analysis Results View
 * Prioritizes "What is wrong?" and "Where is it wrong?" rather than editing controls.
 * Communicates total findings, severity distribution, category density, and page density heatmap.
 */

window.ResultsView = {
  async render(container) {
    container.innerHTML = `
      <div class="empty-state" style="padding: 60px 20px;">
        <div class="spinner" style="margin: 0 auto 16px;"></div>
        <div style="font-size: 15px; font-weight: 700; color: var(--text-primary);">Loading Analysis Results...</div>
        <div style="font-size: 13px; color: var(--text-muted); margin-top: 4px;">Retrieving persistent analysis session from backend</div>
      </div>
    `;

    try {
      await window.appState.rehydrateSession();
    } catch (err) {
      console.error("Failed to rehydrate session for ResultsView:", err);
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">⚠️</div>
          <div class="empty-state-title">Analysis Session Not Found</div>
          <div class="empty-state-desc">The requested analysis session could not be retrieved from the persistent database.</div>
          <button class="btn btn-primary" onclick="window.router.navigate('new_analysis')">Start New Analysis</button>
        </div>
      `;
      return;
    }

    const sessionId = window.appState.get("activeSessionId");
    let activeDoc = window.appState.get("activeDocument");
    const activeDomain = window.appState.get("activeDomain") || "Mechanical";
    let findings = window.appState.get("activeFindings") || [];

    if (!sessionId && !activeDoc) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📊</div>
          <div class="empty-state-title">No Analysis Available</div>
          <div class="empty-state-desc">Upload an engineering document and run an inspection to view verification results.</div>
          <button class="btn btn-primary" onclick="window.router.navigate('new_analysis')">Start New Analysis</button>
        </div>
      `;
      return;
    }

    if (findings.length === 0 && sessionId) {
      try {
        const res = await window.api.findings.list({ session_id: sessionId, limit: 500 });
        findings = res.findings || [];
        window.appState.set("activeFindings", findings);
      } catch (err) {
        console.error("Error loading findings:", err);
      }
    }

    const docName = activeDoc ? activeDoc.filename : "Engineering Document";
    const totalPages = (activeDoc && activeDoc.page_count) || 1;

    const crit = findings.filter((f) => (f.severity || "").toUpperCase() === "CRITICAL").length;
    const high = findings.filter((f) => (f.severity || "").toUpperCase() === "HIGH").length;
    const med = findings.filter((f) => (f.severity || "").toUpperCase() === "MEDIUM").length;
    const low = findings.filter((f) => (f.severity || "").toUpperCase() === "LOW").length;
    const info = findings.filter((f) => {
      const s = (f.severity || "").toUpperCase();
      return s === "INFORMATIONAL" || s === "INFO";
    }).length;

    // Issue Categories breakdown (canonical)
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

    // Page Issue Density
    const pageCounts = {};
    for (let p = 1; p <= totalPages; p++) pageCounts[p] = 0;
    findings.forEach((f) => {
      const p = f.page_number || f.page || 1;
      pageCounts[p] = (pageCounts[p] || 0) + 1;
    });

    // Filter pages that actually contain issues for concise density list
    const activePagesWithIssues = Object.entries(pageCounts).filter(([_, count]) => count > 0);
    const maxDensity = Math.max(1, ...Object.values(pageCounts));

    container.innerHTML = `
      <div class="findings-container">
        <!-- 1. Document Overview Banner -->
        <div class="card" style="border-left: 5px solid ${crit > 0 ? "var(--sev-critical)" : high > 0 ? "var(--sev-high)" : "#10b981"};">
          <div class="card-body" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
            <div>
              <div style="display: flex; align-items: center; gap: 10px;">
                <h2 style="font-size: 18px; font-weight: 800; color: var(--text-primary); margin: 0;">${escapeHtml(docName)}</h2>
                <span class="badge badge-domain" style="text-transform: capitalize;">${escapeHtml(activeDomain)}</span>
                <span class="badge badge-success">✓ INSPECTION COMPLETED</span>
              </div>
              <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">
                Session: <strong style="font-family: var(--font-mono);">${sessionId || "SES-LOCAL"}</strong>
                • Total Pages: <strong>${totalPages}</strong>
                • Total Findings: <strong>${findings.length}</strong>
              </div>
            </div>

            <!-- Primary Navigation Actions -->
            <div style="display: flex; gap: 8px;">
              <button class="btn btn-primary" onclick="window.router.navigate('viewer')">
                👁️ Open Document Inspection Canvas
              </button>
              <button class="btn btn-secondary" onclick="window.router.navigate('findings')">
                📋 View Document Findings
              </button>
              <button class="btn btn-outline" onclick="window.router.navigate('reports')">
                📄 Export Report
              </button>
            </div>
          </div>
        </div>

        <!-- 2. Total Findings & Severity Matrix -->
        <div class="metrics-row">
          <div class="metric-card metric-primary">
            <span class="metric-label">Total Findings</span>
            <span class="metric-value">${findings.length}</span>
            <span class="metric-sub">Identified Discrepancies</span>
          </div>
          <div class="metric-card metric-critical">
            <span class="metric-label">Critical</span>
            <span class="metric-value" style="color: var(--sev-critical);">${crit}</span>
            <span class="metric-sub">Blocks Specification Approval</span>
          </div>
          <div class="metric-card metric-high">
            <span class="metric-label">High Severity</span>
            <span class="metric-value" style="color: var(--sev-high);">${high}</span>
            <span class="metric-sub">Parameters & Structural Deviations</span>
          </div>
          <div class="metric-card metric-medium">
            <span class="metric-label">Medium Severity</span>
            <span class="metric-value" style="color: var(--sev-medium);">${med}</span>
            <span class="metric-sub">Standards & Outline Warnings</span>
          </div>
          <div class="metric-card metric-low">
            <span class="metric-label">Low Severity</span>
            <span class="metric-value" style="color: var(--sev-low);">${low}</span>
            <span class="metric-sub">Formatting & Grammar Issues</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Informational</span>
            <span class="metric-value" style="color: var(--sev-info);">${info}</span>
            <span class="metric-sub">Observations</span>
          </div>
        </div>

        <!-- 3. Two-Column Layout: Issue Categories & Page Issue Density -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
          <!-- Issue Categories Grid -->
          <div class="card">
            <div class="card-header">
              <div class="card-title">📊 Issue Categories</div>
              <button class="btn btn-outline btn-sm" onclick="window.router.navigate('findings')">All Findings →</button>
            </div>
            <div class="card-body" style="padding: 14px 18px;">
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                ${Object.entries(catMap).map(([cName, count]) => `
                  <div class="category-stat-card" style="padding: 10px;" onclick="window.ResultsView.jumpToCategory('${cName}')">
                    <span style="font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">${cName}</span>
                    <span style="font-size: 20px; font-weight: 800; color: ${count > 0 ? 'var(--text-primary)' : 'var(--text-muted)'}; margin-top: 2px;">
                      ${count}
                    </span>
                  </div>
                `).join("")}
              </div>
            </div>
          </div>

          <!-- Page Issue Density / Heatmap -->
          <div class="card">
            <div class="card-header">
              <div class="card-title">🔥 Page Issue Density</div>
              <span style="font-size: 11px; color: var(--text-muted);">Click row to inspect page</span>
            </div>
            <div class="card-body" style="padding: 14px 18px; max-height: 380px; overflow-y: auto;">
              <div class="page-heatmap-container" style="border: none; padding: 0;">
                ${(activePagesWithIssues.length > 0 ? activePagesWithIssues : [[1, 0]]).map(([p, count]) => {
                  const pct = Math.max(count > 0 ? 8 : 0, Math.round((count / maxDensity) * 100));
                  let densityClass = "density-low";
                  if (count >= 5) densityClass = "density-critical";
                  else if (count >= 3) densityClass = "density-high";
                  else if (count >= 1) densityClass = "density-medium";

                  return `
                    <div class="heatmap-row" onclick="window.ResultsView.jumpToPage(${p})">
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
        </div>

        <!-- 4. Prioritized Key Findings Table -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">🔍 Prioritized Issues Inspection (${findings.length})</div>
            <button class="btn btn-outline btn-sm" onclick="window.router.navigate('findings')">
              Document Findings Table →
            </button>
          </div>
          <div class="card-body" style="padding: 0;">
            <div class="table-wrapper" style="border: none; border-radius: 0;">
              <table class="findings-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Severity</th>
                    <th>Category</th>
                    <th>Page</th>
                    <th>Location</th>
                    <th>Detected Value</th>
                    <th>Expected Value</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  ${findings.slice(0, 15).map((f) => {
                    const sevClass = `badge-${f.severity.toLowerCase()}`;
                    return `
                      <tr>
                        <td><strong class="finding-code-id">${f.finding_id}</strong></td>
                        <td><span class="badge ${sevClass}">${f.severity}</span></td>
                        <td><span style="font-weight: 600;">${escapeHtml(f.category)}</span></td>
                        <td>Page ${f.page_number || f.page}</td>
                        <td><small style="color: var(--text-muted);">${escapeHtml(f.location || "-")}</small></td>
                        <td><code style="color: var(--sev-critical);">${escapeHtml(String(f.detected_value || f.original_content || "").substring(0, 30))}</code></td>
                        <td><code style="color: #10b981;">${escapeHtml(String(f.expected_value || "").substring(0, 30))}</code></td>
                        <td>
                          <button class="btn btn-secondary btn-sm" onclick="window.ResultsView.viewInCanvas('${f.finding_id}')">
                            Locate
                          </button>
                        </td>
                      </tr>
                    `;
                  }).join("")}
                </tbody>
              </table>
            </div>
          </div>
          ${findings.length > 15 ? `
            <div class="card-footer" style="padding: 10px 16px;">
              <span style="font-size: 12px; color: var(--text-muted);">Showing top 15 prioritized issues of ${findings.length}.</span>
              <button class="btn btn-secondary btn-sm" onclick="window.router.navigate('findings')">View All Findings</button>
            </div>
          ` : ""}
        </div>
      </div>
    `;
  },

  jumpToPage(pageNum) {
    window.appState.set("activePage", Number(pageNum));
    window.router.navigate("viewer");
    setTimeout(() => {
      if (window.currentViewer) {
        window.currentViewer.setPage(Number(pageNum));
      }
    }, 150);
  },

  jumpToCategory(category) {
    if (category.toLowerCase() === "formatting") window.router.navigate("formatting");
    else if (category.toLowerCase() === "structure" || category.toLowerCase() === "toc") window.router.navigate("structural");
    else if (["grammar", "engineering", "standards", "logical", "semantic"].includes(category.toLowerCase())) window.router.navigate("content");
    else window.router.navigate("findings");
  },

  viewInCanvas(findingId) {
    const findings = window.appState.get("activeFindings") || [];
    const f = findings.find((x) => x.finding_id === findingId);
    if (f) {
      window.appState.set("focusedFinding", f);
      window.appState.set("activePage", f.page_number || f.page || 1);
    }
    window.router.navigate("findings");
  }
};
