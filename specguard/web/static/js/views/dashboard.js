/**
 * SpecGuard Dashboard View
 * Renders real operational metrics, severity distributions, domain stats,
 * and recent verification history from local SQLite storage.
 */

window.DashboardView = {
  async render(container) {
    container.innerHTML = `
      <div class="dashboard-grid">
        <!-- Top Metrics Row -->
        <div class="metrics-row" id="dash-metrics-row">
          <div class="metric-card metric-primary">
            <span class="metric-label">Documents Processed</span>
            <span class="metric-value" id="stat-docs">-</span>
            <span class="metric-sub">Local Repository Archive</span>
          </div>
          <div class="metric-card metric-primary">
            <span class="metric-label">Total Verifications</span>
            <span class="metric-value" id="stat-analyses">-</span>
            <span class="metric-sub">Completed Analyses</span>
          </div>
          <div class="metric-card metric-critical">
            <span class="metric-label">Critical Findings</span>
            <span class="metric-value" id="stat-crit" style="color: var(--sev-critical);">-</span>
            <span class="metric-sub">Immediate Action Required</span>
          </div>
          <div class="metric-card metric-high">
            <span class="metric-label">High Severity</span>
            <span class="metric-value" id="stat-high" style="color: var(--sev-high);">-</span>
            <span class="metric-sub">Engineering Deviations</span>
          </div>
          <div class="metric-card metric-medium">
            <span class="metric-label">Medium Severity</span>
            <span class="metric-value" id="stat-med" style="color: var(--sev-medium);">-</span>
            <span class="metric-sub">Standards Discrepancies</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Total Findings</span>
            <span class="metric-value" id="stat-findings">-</span>
            <span class="metric-sub">Across All Revisions</span>
          </div>
        </div>

        <!-- Domain Breakdown -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">⚙️ Engineering Domain Distribution</div>
            <button class="btn btn-primary btn-sm" onclick="window.router.navigate('new_analysis')">
              + New Analysis
            </button>
          </div>
          <div class="card-body">
            <div class="domain-cards-row" id="dash-domain-row">
              <div class="domain-stat-card mech">
                <span class="domain-stat-title">Mechanical Engineering</span>
                <span class="domain-stat-count" id="domain-mech-count">0 analyses</span>
                <span style="font-size: 11px; color: var(--text-muted);" id="domain-mech-findings">0 findings</span>
              </div>
              <div class="domain-stat-card elec">
                <span class="domain-stat-title">Electrical Engineering</span>
                <span class="domain-stat-count" id="domain-elec-count">0 analyses</span>
                <span style="font-size: 11px; color: var(--text-muted);" id="domain-elec-findings">0 findings</span>
              </div>
              <div class="domain-stat-card chem">
                <span class="domain-stat-title">Chemical Engineering</span>
                <span class="domain-stat-count" id="domain-chem-count">0 analyses</span>
                <span style="font-size: 11px; color: var(--text-muted);" id="domain-chem-findings">0 findings</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Split: Recent Comparisons & Documents -->
        <div class="dashboard-split">
          <!-- Recent Verifications Table -->
          <div class="card">
            <div class="card-header">
              <div class="card-title">🕒 Recent Verifications</div>
              <button class="btn btn-outline btn-sm" onclick="window.router.navigate('history')">View All History →</button>
            </div>
            <div class="card-body" style="padding: 0;">
              <div class="table-wrapper" style="border: none; border-radius: 0;">
                <table class="table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Document</th>
                      <th>Domain</th>
                      <th>Findings</th>
                      <th>Date</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody id="dash-recent-tbody">
                    <tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 24px;">Loading recent comparisons...</td></tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <!-- Quick Launch & Status -->
          <div class="card">
            <div class="card-header">
              <div class="card-title">⚡ Quick Verification</div>
            </div>
            <div class="card-body" style="display: flex; flex-direction: column; gap: 14px;">
              <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.4;">
                Upload an engineering document or choose a local demo sample to perform automated quality and standards verification.
              </p>
              <button class="btn btn-primary" style="width: 100%;" onclick="window.router.navigate('new_analysis')">
                📄 Select Document to Analyze
              </button>
              <div style="border-top: 1px solid var(--border-subtle); padding-top: 14px;">
                <span style="font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">System Integrity</span>
                <div style="display: flex; flex-direction: column; gap: 6px; margin-top: 8px; font-size: 12px;">
                  <div style="display: flex; justify-content: space-between;">
                    <span style="color: var(--text-secondary);">Operating Mode:</span>
                    <span style="font-weight: 700; color: #10b981;">100% Offline (Local)</span>
                  </div>
                  <div style="display: flex; justify-content: space-between;">
                    <span style="color: var(--text-secondary);">Local Database:</span>
                    <span style="font-weight: 600;">specguard.db</span>
                  </div>
                  <div style="display: flex; justify-content: space-between;">
                    <span style="color: var(--text-secondary);">Engines Active:</span>
                    <span style="font-weight: 600;">10 Analyzers</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    await this.loadData();
  },

  async loadData() {
    try {
      const stats = await window.api.dashboard.getStats();
      const recent = await window.api.dashboard.getRecent(7);

      // Populate counters
      document.getElementById("stat-docs").textContent = stats.total_documents;
      document.getElementById("stat-analyses").textContent = stats.total_analyses;
      document.getElementById("stat-findings").textContent = stats.total_findings;
      document.getElementById("stat-crit").textContent = stats.severity_distribution.Critical;
      document.getElementById("stat-high").textContent = stats.severity_distribution.High;
      document.getElementById("stat-med").textContent = stats.severity_distribution.Medium;

      // Domain stats
      const dDist = stats.domain_distribution;
      if (dDist.Mechanical) {
        document.getElementById("domain-mech-count").textContent = `${dDist.Mechanical.comparisons} analyses`;
        document.getElementById("domain-mech-findings").textContent = `${dDist.Mechanical.findings} findings`;
      }
      if (dDist.Electrical) {
        document.getElementById("domain-elec-count").textContent = `${dDist.Electrical.comparisons} analyses`;
        document.getElementById("domain-elec-findings").textContent = `${dDist.Electrical.findings} findings`;
      }
      if (dDist.Chemical) {
        document.getElementById("domain-chem-count").textContent = `${dDist.Chemical.comparisons} analyses`;
        document.getElementById("domain-chem-findings").textContent = `${dDist.Chemical.findings} findings`;
      }

      // Recent comparisons table
      const tbody = document.getElementById("dash-recent-tbody");
      if (recent.recent_comparisons && recent.recent_comparisons.length > 0) {
        tbody.innerHTML = recent.recent_comparisons.map((c) => {
          const dateStr = c.analysis_completed_at ? new Date(c.analysis_completed_at).toLocaleDateString() : "-";
          return `
            <tr>
              <td><strong style="font-family: var(--font-mono); font-size: 12px;">${c.comparison_id}</strong></td>
              <td style="max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${c.document_filename}">
                ${c.document_filename}
              </td>
              <td><span class="badge badge-domain">${c.domain}</span></td>
              <td>
                <span class="badge badge-critical" style="margin-right: 4px;">${c.critical_count}</span>
                <span class="badge badge-high" style="margin-right: 4px;">${c.high_count}</span>
                <span style="font-size: 11px; color: var(--text-muted);">(${c.total_findings})</span>
              </td>
              <td style="color: var(--text-secondary); font-size: 12px;">${dateStr}</td>
              <td>
                <button class="btn btn-secondary btn-sm" onclick="window.DashboardView.openComparison('${c.comparison_id}')">
                  Open
                </button>
              </td>
            </tr>
          `;
        }).join("");
      } else {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 24px;">No historical verifications recorded yet.</td></tr>`;
      }
    } catch (err) {
      console.error("Failed loading dashboard data:", err);
      window.toast.error("Failed loading dashboard metrics.");
    }
  },

  async openComparison(comparisonId) {
    try {
      window.toast.info(`Loading comparison ${comparisonId}...`);
      const detail = await window.api.history.get(comparisonId);
      window.appState.set("activeSessionId", detail.comparison_id);
      window.appState.set("activeDomain", detail.domain.toLowerCase());
      window.appState.set("activeFindings", detail.findings || []);
      window.appState.set("activeDocument", {
        filename: detail.document.filename,
        file_path: detail.document.original_path,
        file_hash: detail.document_sha256,
        file_type: detail.document.file_type,
        page_count: detail.document.page_count
      });
      window.router.navigate("results");
    } catch (err) {
      window.toast.error(`Could not open comparison: ${err.message}`);
    }
  }
};
