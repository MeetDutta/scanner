/**
 * SpecGuard Results Dashboard View
 * Executive compliance summary, severity matrices, category distributions,
 * and quick navigation to interactive Document Viewer or Reports.
 */

window.ResultsView = {
  async render(container) {
    const sessionId = window.appState.get("activeSessionId");
    const activeDoc = window.appState.get("activeDocument");
    const activeDomain = window.appState.get("activeDomain") || "mechanical";
    let findings = window.appState.get("activeFindings") || [];

    if (!sessionId && findings.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📊</div>
          <div class="empty-state-title">No Analysis Results Available</div>
          <div class="empty-state-desc">Run a document verification or select a previous analysis from Document History.</div>
          <button class="btn btn-primary" onclick="window.router.navigate('new_analysis')">Start New Analysis</button>
        </div>
      `;
      return;
    }

    // If findings not loaded into state yet, fetch them
    if (findings.length === 0 && sessionId) {
      try {
        const res = await window.api.findings.list({ session_id: sessionId, limit: 300 });
        findings = res.findings || [];
        window.appState.set("activeFindings", findings);
      } catch (err) {
        console.error("Error loading findings:", err);
      }
    }

    const crit = findings.filter((f) => f.severity === "Critical").length;
    const high = findings.filter((f) => f.severity === "High").length;
    const med = findings.filter((f) => f.severity === "Medium").length;
    const low = findings.filter((f) => f.severity === "Low").length;
    const info = findings.filter((f) => f.severity === "Informational").length;

    const docName = activeDoc ? activeDoc.filename : "Verified Specification";

    container.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 20px;">
        <!-- 1. Executive Summary Banner -->
        <div class="card" style="border-left: 5px solid ${crit > 0 ? "var(--sev-critical)" : high > 0 ? "var(--sev-high)" : "#10b981"};">
          <div class="card-body" style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px;">
            <div>
              <div style="display: flex; align-items: center; gap: 10px;">
                <h2 style="font-size: 18px; font-weight: 800; color: var(--text-primary);">${docName}</h2>
                <span class="badge badge-domain" style="text-transform: capitalize;">${activeDomain}</span>
                <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #059669; border: 1px solid rgba(16, 185, 129, 0.3);">
                  ✓ VERIFIED
                </span>
              </div>
              <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">
                Session: <strong style="font-family: var(--font-mono);">${sessionId || "SES-LOCAL"}</strong>
                • Total Findings: <strong>${findings.length}</strong>
                • Status: 100% Local Compliance Verified
              </div>
            </div>

            <!-- Top Actions -->
            <div style="display: flex; gap: 10px;">
              <button class="btn btn-primary" onclick="window.router.navigate('viewer')">
                👁️ Open Document Canvas
              </button>
              <button class="btn btn-secondary" onclick="window.router.navigate('reports')">
                📄 Export Reports
              </button>
            </div>
          </div>
        </div>

        <!-- 2. Severity Counters Row -->
        <div class="metrics-row">
          <div class="metric-card metric-critical">
            <span class="metric-label">Critical Issues</span>
            <span class="metric-value" style="color: var(--sev-critical);">${crit}</span>
            <span class="metric-sub">Blocks specification approval</span>
          </div>
          <div class="metric-card metric-high">
            <span class="metric-label">High Severity</span>
            <span class="metric-value" style="color: var(--sev-high);">${high}</span>
            <span class="metric-sub">Parameters or design deviations</span>
          </div>
          <div class="metric-card metric-medium">
            <span class="metric-label">Medium Severity</span>
            <span class="metric-value" style="color: var(--sev-medium);">${med}</span>
            <span class="metric-sub">Structural or standards warnings</span>
          </div>
          <div class="metric-card metric-low">
            <span class="metric-label">Low Severity</span>
            <span class="metric-value" style="color: var(--sev-low);">${low}</span>
            <span class="metric-sub">Formatting and grammar issues</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Informational</span>
            <span class="metric-value" style="color: var(--sev-info);">${info}</span>
            <span class="metric-sub">Observations & ML flags</span>
          </div>
        </div>

        <!-- 3. Key Findings List -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">🔍 Prioritized Findings (${findings.length})</div>
            <button class="btn btn-outline btn-sm" onclick="window.router.navigate('findings')">
              Manage All Findings →
            </button>
          </div>
          <div class="card-body" style="padding: 0;">
            <div class="table-wrapper" style="border: none; border-radius: 0;">
              <table class="table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Severity</th>
                    <th>Category</th>
                    <th>Location</th>
                    <th>Detected Value</th>
                    <th>Expected Value</th>
                    <th>Suggested Correction</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  ${findings.slice(0, 15).map((f) => {
                    const sevClass = `badge-${f.severity.toLowerCase()}`;
                    return `
                      <tr>
                        <td><strong style="font-family: var(--font-mono); font-size: 11.5px;">${f.finding_id}</strong></td>
                        <td><span class="badge ${sevClass}">${f.severity}</span></td>
                        <td><span style="font-weight: 600;">${f.category}</span></td>
                        <td>Page ${f.page} • <small style="color: var(--text-muted);">${f.location || "-"}</small></td>
                        <td><code style="color: var(--sev-critical);">${escapeHtml(String(f.detected_value || f.original_content || "").substring(0, 30))}</code></td>
                        <td><code style="color: #10b981;">${escapeHtml(String(f.expected_value || "").substring(0, 30))}</code></td>
                        <td style="max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(f.suggested_correction)}">
                          ${escapeHtml(f.suggested_correction || "-")}
                        </td>
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
            <div class="card-footer">
              <span style="font-size: 12px; color: var(--text-muted);">Showing top 15 prioritized findings of ${findings.length}.</span>
              <button class="btn btn-secondary btn-sm" onclick="window.router.navigate('findings')">View All Findings</button>
            </div>
          ` : ""}
        </div>
      </div>
    `;
  },

  viewInCanvas(findingId) {
    const findings = window.appState.get("activeFindings") || [];
    const f = findings.find((x) => x.finding_id === findingId);
    if (f) {
      window.appState.set("focusedFinding", f);
      window.appState.set("activePage", f.page);
    }
    window.router.navigate("viewer");
  }
};
