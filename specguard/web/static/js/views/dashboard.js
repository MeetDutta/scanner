/**
 * SpecGuard Executive Quality Dashboard View
 * Communicates document quality, severity distribution, category density,
 * and page-by-page heatmap to answer "Where are the problems in my document?" in seconds.
 */

window.DashboardView = {
  async render(container) {
    let activeDoc = window.appState.get("activeDocument");
    let sessionId = window.appState.get("activeSessionId");
    let findings = window.appState.get("activeFindings") || [];
    let domain = window.appState.get("activeDomain") || "Mechanical";

    // If no active session in appState, load the latest comparison from SQLite repository
    if (!sessionId) {
      try {
        const recent = await window.api.dashboard.getRecent(1);
        if (recent.recent_comparisons && recent.recent_comparisons.length > 0) {
          const latest = recent.recent_comparisons[0];
          sessionId = latest.comparison_id;
          domain = latest.domain || "Mechanical";
          activeDoc = {
            filename: latest.document_filename,
            file_hash: latest.document_sha256,
            page_count: latest.page_count || 1
          };
          window.appState.set("activeSessionId", sessionId);
          window.appState.set("activeDocument", activeDoc);
          window.appState.set("activeDomain", domain);
        }
      } catch (e) {
        console.warn("Could not fetch latest comparison for dashboard:", e);
      }
    }

    // Fetch findings for active session if not already in state
    if (sessionId && findings.length === 0) {
      try {
        const res = await window.api.findings.list({ session_id: sessionId, limit: 300 });
        findings = res.findings || [];
        window.appState.set("activeFindings", findings);
      } catch (e) {
        console.warn("Could not load findings for dashboard:", e);
      }
    }

    // Calculate severity metrics
    const crit = findings.filter((f) => f.severity === "Critical").length;
    const high = findings.filter((f) => f.severity === "High").length;
    const med = findings.filter((f) => f.severity === "Medium").length;
    const low = findings.filter((f) => f.severity === "Low").length;
    const info = findings.filter((f) => f.severity === "Informational").length;

    // Calculate standardized category counts
    const catMap = {
      "Formatting": 0,
      "Structure": 0,
      "Grammar": 0,
      "Tables": 0,
      "Figures": 0,
      "TOC": 0,
      "References": 0,
      "Engineering": 0,
      "Standards": 0,
      "Logical": 0,
      "Semantic": 0
    };

    findings.forEach((f) => {
      const c = (f.category || "").toLowerCase();
      if (c.includes("format") || c.includes("typography") || c.includes("layout")) catMap["Formatting"]++;
      else if (c.includes("structure") || c.includes("outline")) catMap["Structure"]++;
      else if (c.includes("grammar") || c.includes("spelling")) catMap["Grammar"]++;
      else if (c.includes("table of contents") || c.includes("toc")) catMap["TOC"]++;
      else if (c.includes("table")) catMap["Tables"]++;
      else if (c.includes("figure")) catMap["Figures"]++;
      else if (c.includes("reference") || c.includes("citation") || c.includes("cross")) catMap["References"]++;
      else if (c.includes("parameter") || c.includes("engineering")) catMap["Engineering"]++;
      else if (c.includes("standard") || c.includes("ieee")) catMap["Standards"]++;
      else if (c.includes("logical") || c.includes("contradiction")) catMap["Logical"]++;
      else if (c.includes("semantic")) catMap["Semantic"]++;
      else catMap["Formatting"]++;
    });

    // Calculate Page Heatmap
    const totalPages = (activeDoc && activeDoc.page_count) || 5;
    const pageCounts = {};
    for (let p = 1; p <= totalPages; p++) pageCounts[p] = 0;
    findings.forEach((f) => {
      const p = f.page_number || f.page || 1;
      pageCounts[p] = (pageCounts[p] || 0) + 1;
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
                  ${activeDoc ? escapeHtml(activeDoc.filename) : "Engineering Specification"}
                </h2>
                <span class="badge badge-domain" style="text-transform: capitalize;">${escapeHtml(domain)}</span>
                <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #059669; border: 1px solid rgba(16, 185, 129, 0.3);">
                  ✓ INSPECTION READY
                </span>
              </div>
              <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">
                Session: <strong style="font-family: var(--font-mono);">${sessionId || "No session loaded"}</strong>
                • Pages: <strong>${totalPages}</strong>
                • Total Findings: <strong>${findings.length}</strong>
                • Inspection Mode: 100% Offline (Localhost)
              </div>
            </div>

            <div style="display: flex; gap: 8px;">
              <button class="btn btn-secondary btn-sm" onclick="window.router.navigate('overview')">
                📑 Document Overview
              </button>
              <button class="btn btn-primary btn-sm" onclick="window.router.navigate('viewer')">
                👁️ Open Canvas Inspection
              </button>
              <button class="btn btn-outline btn-sm" onclick="window.router.navigate('new_analysis')">
                + New Analysis
              </button>
            </div>
          </div>
        </div>

        <!-- 2. Finding Severity Summary Row -->
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
          <!-- Page Issue Heatmap (Answers: Where are the problems in my document?) -->
          <div class="card">
            <div class="card-header">
              <div class="card-title">🔥 Page Issue Heatmap</div>
              <span style="font-size: 11px; color: var(--text-muted);">Click page to inspect in canvas</span>
            </div>
            <div class="card-body" style="padding: 12px 16px;">
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

          <!-- Category Distribution -->
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

        <!-- 4. Recent Analyzed Documents & Comparisons -->
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
                <tbody id="dash-recent-tbody">
                  <tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 24px;">Loading recent comparisons...</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    `;

    this.loadRecentTable();
  },

  async loadRecentTable() {
    try {
      const recent = await window.api.dashboard.getRecent(6);
      const tbody = document.getElementById("dash-recent-tbody");
      if (!tbody) return;

      if (!recent.recent_comparisons || recent.recent_comparisons.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 24px;">No previous inspections recorded.</td></tr>`;
        return;
      }

      tbody.innerHTML = recent.recent_comparisons.map((c) => `
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
      `).join("");
    } catch (e) {
      console.warn("Could not load recent table:", e);
    }
  },

  async openComparison(cmpId, filename) {
    window.appState.set("activeSessionId", cmpId);
    window.appState.set("activeDocument", { filename: filename, file_hash: cmpId, page_count: 1 });
    try {
      const res = await window.api.findings.list({ session_id: cmpId, limit: 300 });
      window.appState.set("activeFindings", res.findings || []);
    } catch (e) {
      console.error(e);
    }
    window.router.navigate("results");
  },

  jumpToPage(pageNum) {
    window.appState.set("activePage", pageNum);
    window.router.navigate("viewer");
    setTimeout(() => {
      if (window.currentViewer) {
        window.currentViewer.setPage(pageNum);
      }
    }, 150);
  },

  jumpToCategory(category) {
    if (category.toLowerCase() === "formatting") window.router.navigate("formatting");
    else if (category.toLowerCase() === "structure" || category.toLowerCase() === "toc") window.router.navigate("structural");
    else if (["grammar", "engineering", "standards", "logical", "semantic"].includes(category.toLowerCase())) window.router.navigate("content");
    else window.router.navigate("findings");
  }
};
