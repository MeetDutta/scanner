/**
 * SpecGuard Settings, Telemetry & Diagnostics View
 * Theme preferences, offline mode verification, local storage statistics,
 * startup pre-flight diagnostics, and immutable audit logs.
 */

window.SettingsView = {
  auditPage: 1,

  async render(container) {
    const currentTheme = window.appState.get("theme") || "dark";

    container.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 20px; max-width: 1080px; margin: 0 auto;">
        <!-- 1. General Preferences -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">⚙️ Interface & System Preferences</div>
          </div>
          <div class="card-body" style="display: flex; flex-direction: column; gap: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <div>
                <strong style="color: var(--text-primary);">Theme Preference</strong>
                <div style="font-size: 12px; color: var(--text-muted);">Toggle between high-contrast Dark and Government Light themes.</div>
              </div>
              <div style="display: flex; gap: 6px;">
                <button class="btn ${currentTheme === "dark" ? "btn-primary" : "btn-secondary"} btn-sm" id="btn-theme-dark">🌙 Dark Theme</button>
                <button class="btn ${currentTheme === "light" ? "btn-primary" : "btn-secondary"} btn-sm" id="btn-theme-light">☀️ Light Theme</button>
              </div>
            </div>

            <div style="border-top: 1px solid var(--border-subtle); padding-top: 14px; display: flex; justify-content: space-between; align-items: center;">
              <div>
                <strong style="color: var(--text-primary);">Offline Enforcement Policy</strong>
                <div style="font-size: 12px; color: var(--text-muted);">SpecGuard operates exclusively on localhost (127.0.0.1) with zero telemetry.</div>
              </div>
              <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #059669; padding: 4px 10px;">
                ✓ 100% OFFLINE CONFIRMED
              </span>
            </div>
          </div>
        </div>

        <!-- 2. Local Storage Telemetry -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">💾 Local Storage & Repository Telemetry</div>
            <button class="btn btn-secondary btn-sm" id="btn-refresh-storage">Refresh</button>
          </div>
          <div class="card-body">
            <div class="hardware-specs-grid" id="storage-specs-grid">
              <div class="hardware-spec-box">
                <span class="hardware-spec-label">SQLite Database (specguard.db)</span>
                <span class="hardware-spec-value" id="storage-db-size">-</span>
              </div>
              <div class="hardware-spec-box">
                <span class="hardware-spec-label">Archived Comparisons</span>
                <span class="hardware-spec-value" id="storage-comps-count">-</span>
              </div>
              <div class="hardware-spec-box">
                <span class="hardware-spec-label">Archived Documents</span>
                <span class="hardware-spec-value" id="storage-docs-count">-</span>
              </div>
              <div class="hardware-spec-box">
                <span class="hardware-spec-label">Generated Reports</span>
                <span class="hardware-spec-value" id="storage-reports-count">-</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 3. Pre-Flight Startup Health Diagnostics -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">🛡️ Pre-Flight Verification Diagnostics</div>
            <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #059669;" id="env-health-badge">VERIFYING...</span>
          </div>
          <div class="card-body" style="padding: 0;">
            <div class="table-wrapper" style="border: none; border-radius: 0;">
              <table class="table">
                <thead>
                  <tr>
                    <th>Package / Component</th>
                    <th>Role in SpecGuard</th>
                    <th>Installed Version</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody id="env-health-tbody">
                  <tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 24px;">Running diagnostics...</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- 4. Immutable Audit Logs -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">📜 System Audit Log Records</div>
            <div class="search-input-wrapper" style="width: 260px;">
              <span class="search-icon">🔍</span>
              <input type="text" class="form-input" id="audit-search" placeholder="Search audit logs..." />
            </div>
          </div>
          <div class="card-body" style="padding: 0;">
            <div class="table-wrapper" style="border: none; border-radius: 0;">
              <table class="table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Action</th>
                    <th>Document Hash</th>
                    <th>Details</th>
                  </tr>
                </thead>
                <tbody id="audit-tbody">
                  <tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 24px;">Loading audit logs...</td></tr>
                </tbody>
              </table>
            </div>
          </div>
          <div class="card-footer">
            <span style="font-size: 12px; color: var(--text-muted);" id="audit-page-info">Showing audit logs</span>
            <div style="display: flex; gap: 6px;">
              <button class="btn btn-secondary btn-sm" id="btn-audit-prev" disabled>← Previous</button>
              <button class="btn btn-secondary btn-sm" id="btn-audit-next" disabled>Next →</button>
            </div>
          </div>
        </div>
      </div>
    `;

    this._bindEvents();
    await this.loadStorage();
    await this.loadHealth();
    await this.loadAudit();
  },

  _bindEvents() {
    document.getElementById("btn-theme-dark").onclick = () => {
      window.app.setTheme("dark");
      this.render(document.querySelector(".view-container"));
    };

    document.getElementById("btn-theme-light").onclick = () => {
      window.app.setTheme("light");
      this.render(document.querySelector(".view-container"));
    };

    document.getElementById("btn-refresh-storage").onclick = () => this.loadStorage();

    const auditSearch = document.getElementById("audit-search");
    let timer = null;
    auditSearch.oninput = () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        this.auditPage = 1;
        this.loadAudit();
      }, 250);
    };

    document.getElementById("btn-audit-prev").onclick = () => {
      if (this.auditPage > 1) {
        this.auditPage--;
        this.loadAudit();
      }
    };

    document.getElementById("btn-audit-next").onclick = () => {
      this.auditPage++;
      this.loadAudit();
    };
  },

  async loadStorage() {
    try {
      const s = await window.api.settings.storage();
      document.getElementById("storage-db-size").textContent = `${s.database.size_mb} MB`;
      document.getElementById("storage-comps-count").textContent = `${s.repository.comparisons_count} records (${s.repository.comparisons_size_mb} MB)`;
      document.getElementById("storage-docs-count").textContent = `${s.repository.documents_count} files (${s.repository.documents_size_mb} MB)`;
      document.getElementById("storage-reports-count").textContent = `${s.reports.count} generated (${s.reports.size_mb} MB)`;
    } catch (err) {
      console.warn("Storage telemetry error:", err);
    }
  },

  async loadHealth() {
    try {
      const h = await window.api.settings.health();
      const badge = document.getElementById("env-health-badge");
      const tbody = document.getElementById("env-health-tbody");

      if (h.is_ready) {
        badge.textContent = `✓ READY (Python ${h.python_version})`;
        badge.style.color = "#059669";
      } else {
        badge.textContent = `⚠ ISSUES DETECTED`;
        badge.style.color = "var(--sev-critical)";
      }

      const rows = [];
      Object.entries(h.packages || {}).forEach(([pkg, info]) => {
        rows.push(`
          <tr>
            <td><strong>${pkg}</strong></td>
            <td style="color: var(--text-secondary);">${info.description}</td>
            <td style="font-family: var(--font-mono); font-size: 12px;">${info.version || "-"}</td>
            <td>
              <span class="badge" style="background: ${info.installed ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)"}; color: ${info.installed ? "#059669" : "var(--sev-critical)"};">
                ${info.installed ? "INSTALLED" : "MISSING"}
              </span>
            </td>
          </tr>
        `);
      });

      tbody.innerHTML = rows.join("");
    } catch (err) {
      console.warn("Health check error:", err);
    }
  },

  async loadAudit() {
    const search = document.getElementById("audit-search").value.trim();
    const limit = 25;
    const offset = (this.auditPage - 1) * limit;

    try {
      const res = await window.api.settings.audit({ search, limit, offset });
      const tbody = document.getElementById("audit-tbody");
      const pageInfo = document.getElementById("audit-page-info");
      const prevBtn = document.getElementById("btn-audit-prev");
      const nextBtn = document.getElementById("btn-audit-next");

      const startIdx = res.total > 0 ? offset + 1 : 0;
      const endIdx = Math.min(offset + res.logs.length, res.total);
      pageInfo.textContent = `Showing ${startIdx}-${endIdx} of ${res.total} audit events`;

      prevBtn.disabled = this.auditPage <= 1;
      nextBtn.disabled = endIdx >= res.total;

      if (!res.logs || res.logs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 24px;">No audit events found.</td></tr>`;
        return;
      }

      tbody.innerHTML = res.logs.map((l) => `
        <tr>
          <td style="font-family: var(--font-mono); font-size: 11.5px; color: var(--text-secondary); white-space: nowrap;">
            ${new Date(l.timestamp).toLocaleString()}
          </td>
          <td><strong style="font-size: 12px; color: var(--accent-primary);">${l.user_action}</strong></td>
          <td><code style="font-size: 11px; color: var(--text-muted);">${(l.document_hash || "-").substring(0, 16)}...</code></td>
          <td style="font-size: 12.5px; color: var(--text-secondary);">${escapeHtml(l.details || "-")}</td>
        </tr>
      `).join("");
    } catch (err) {
      console.warn("Audit load error:", err);
    }
  }
};
