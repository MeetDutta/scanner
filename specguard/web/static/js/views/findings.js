/**
 * SpecGuard Findings Management View
 * Advanced search, multi-criteria filtering, pagination, and remediation details.
 */

window.FindingsView = {
  currentFilters: {
    severity: "",
    category: "",
    search: "",
    page: 1,
    limit: 25
  },

  async render(container) {
    const sessionId = window.appState.get("activeSessionId");

    container.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <!-- Header & Search Toolbar -->
        <div class="card">
          <div class="card-body" style="padding: 14px 18px;">
            <div class="findings-filter-bar">
              <!-- Search Box -->
              <div class="search-input-wrapper" style="flex: 1; min-width: 240px;">
                <span class="search-icon">🔍</span>
                <input type="text" class="form-input" id="findings-search" placeholder="Search by finding ID, explanation, rule, or detected value..." />
              </div>

              <!-- Severity Filter -->
              <div style="display: flex; align-items: center; gap: 6px;">
                <span class="form-label" style="margin: 0;">Severity:</span>
                <select class="form-select" id="findings-filter-sev">
                  <option value="">All Severities</option>
                  <option value="Critical">Critical</option>
                  <option value="High">High</option>
                  <option value="Medium">Medium</option>
                  <option value="Low">Low</option>
                  <option value="Informational">Informational</option>
                </select>
              </div>

              <!-- Category Filter -->
              <div style="display: flex; align-items: center; gap: 6px;">
                <span class="form-label" style="margin: 0;">Category:</span>
                <select class="form-select" id="findings-filter-cat">
                  <option value="">All Categories</option>
                  <option value="Formatting">Formatting</option>
                  <option value="Structure">Structure</option>
                  <option value="Table of Contents">Table of Contents</option>
                  <option value="Table">Table</option>
                  <option value="Grammar & Spelling">Grammar & Spelling</option>
                  <option value="Engineering Parameter">Engineering Parameter</option>
                  <option value="Semantic Inconsistency">Semantic Inconsistency</option>
                  <option value="Logical Contradiction">Logical Contradiction</option>
                  <option value="Standards Deviation">Standards Deviation</option>
                </select>
              </div>

              <button class="btn btn-secondary btn-sm" id="findings-reset-btn">Reset</button>
            </div>
          </div>
        </div>

        <!-- Findings Table Card -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">
              📋 Finding Records <span id="findings-count-badge" class="badge badge-info" style="margin-left: 6px;">0</span>
            </div>
            <div style="display: flex; gap: 8px;">
              <button class="btn btn-secondary btn-sm" onclick="window.router.navigate('viewer')">👁️ View in Document Canvas</button>
              <button class="btn btn-primary btn-sm" onclick="window.router.navigate('reports')">📄 Export Findings</button>
            </div>
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
                    <th>Standard / Rule</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody id="findings-tbody">
                  <tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 32px;">Loading findings...</td></tr>
                </tbody>
              </table>
            </div>
          </div>
          <!-- Pagination Footer -->
          <div class="card-footer">
            <span style="font-size: 12px; color: var(--text-muted);" id="findings-page-info">Showing 0 of 0</span>
            <div style="display: flex; gap: 6px;">
              <button class="btn btn-secondary btn-sm" id="btn-prev-page" disabled>← Previous</button>
              <button class="btn btn-secondary btn-sm" id="btn-next-page" disabled>Next →</button>
            </div>
          </div>
        </div>
      </div>
    `;

    this._bindEvents();
    await this.fetchFindings();
  },

  _bindEvents() {
    const searchInput = document.getElementById("findings-search");
    const sevSelect = document.getElementById("findings-filter-sev");
    const catSelect = document.getElementById("findings-filter-cat");
    const resetBtn = document.getElementById("findings-reset-btn");
    const prevBtn = document.getElementById("btn-prev-page");
    const nextBtn = document.getElementById("btn-next-page");

    let debounceTimer = null;
    searchInput.oninput = () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        this.currentFilters.search = searchInput.value.trim();
        this.currentFilters.page = 1;
        this.fetchFindings();
      }, 250);
    };

    sevSelect.onchange = () => {
      this.currentFilters.severity = sevSelect.value;
      this.currentFilters.page = 1;
      this.fetchFindings();
    };

    catSelect.onchange = () => {
      this.currentFilters.category = catSelect.value;
      this.currentFilters.page = 1;
      this.fetchFindings();
    };

    resetBtn.onclick = () => {
      searchInput.value = "";
      sevSelect.value = "";
      catSelect.value = "";
      this.currentFilters = { severity: "", category: "", search: "", page: 1, limit: 25 };
      this.fetchFindings();
    };

    prevBtn.onclick = () => {
      if (this.currentFilters.page > 1) {
        this.currentFilters.page--;
        this.fetchFindings();
      }
    };

    nextBtn.onclick = () => {
      this.currentFilters.page++;
      this.fetchFindings();
    };
  },

  async fetchFindings() {
    const sessionId = window.appState.get("activeSessionId");
    const offset = (this.currentFilters.page - 1) * this.currentFilters.limit;

    try {
      const res = await window.api.findings.list({
        session_id: sessionId,
        severity: this.currentFilters.severity,
        category: this.currentFilters.category,
        search: this.currentFilters.search,
        limit: this.currentFilters.limit,
        offset: offset
      });

      const tbody = document.getElementById("findings-tbody");
      const countBadge = document.getElementById("findings-count-badge");
      const pageInfo = document.getElementById("findings-page-info");
      const prevBtn = document.getElementById("btn-prev-page");
      const nextBtn = document.getElementById("btn-next-page");

      if (countBadge) countBadge.textContent = res.total_count;

      const startIdx = res.total_count > 0 ? offset + 1 : 0;
      const endIdx = Math.min(offset + res.findings.length, res.total_count);
      if (pageInfo) pageInfo.textContent = `Showing ${startIdx}-${endIdx} of ${res.total_count} findings`;

      if (prevBtn) prevBtn.disabled = this.currentFilters.page <= 1;
      if (nextBtn) nextBtn.disabled = endIdx >= res.total_count;

      if (!res.findings || res.findings.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="9" style="text-align: center; color: var(--text-muted); padding: 36px;">
              No findings matched the selected criteria.
            </td>
          </tr>
        `;
        return;
      }

      tbody.innerHTML = res.findings.map((f) => {
        const sevClass = `badge-${f.severity.toLowerCase()}`;
        return `
          <tr>
            <td><strong style="font-family: var(--font-mono); font-size: 11.5px;">${f.finding_id}</strong></td>
            <td><span class="badge ${sevClass}">${f.severity}</span></td>
            <td><span style="font-weight: 600;">${f.category}</span></td>
            <td>Page ${f.page} • <small style="color: var(--text-muted);">${escapeHtml(f.location || "")}</small></td>
            <td><code style="color: var(--sev-critical);">${escapeHtml(String(f.detected_value || f.original_content || "").substring(0, 30))}</code></td>
            <td><code style="color: #10b981;">${escapeHtml(String(f.expected_value || "").substring(0, 30))}</code></td>
            <td style="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(f.suggested_correction)}">
              ${escapeHtml(f.suggested_correction || "-")}
            </td>
            <td style="font-size: 11.5px; color: var(--text-muted); font-family: var(--font-mono);">
              ${escapeHtml(f.rule_reference || "-")}
            </td>
            <td>
              <button class="btn btn-secondary btn-sm" onclick="window.FindingsView.locateInCanvas('${f.finding_id}')">
                Canvas
              </button>
            </td>
          </tr>
        `;
      }).join("");
    } catch (err) {
      console.error("Error loading findings:", err);
      window.toast.error("Failed loading findings table.");
    }
  },

  locateInCanvas(findingId) {
    const findings = window.appState.get("activeFindings") || [];
    const f = findings.find((x) => x.finding_id === findingId);
    if (f) {
      window.appState.set("focusedFinding", f);
      window.appState.set("activePage", f.page);
    }
    window.router.navigate("viewer");
  }
};
