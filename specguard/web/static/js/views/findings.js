/**
 * SpecGuard Document Findings Inspection View
 * Purely read-only inspection interface with multi-criteria filtering,
 * side inspection drawer, clear Problem / Detected / Expected / Explanation hierarchy,
 * and zero automatic editing or modification controls.
 */

window.FindingsView = {
  currentFilters: {
    severity: "",
    category: "",
    search: "",
    page_num: "",
    confidence_min: "",
    page: 1,
    limit: 25
  },
  selectedFinding: null,

  async render(container) {
    const sessionId = window.appState.get("activeSessionId");

    container.innerHTML = `
      <div class="findings-container">
        <!-- Header & Search Toolbar -->
        <div class="findings-toolbar-card">
          <div class="findings-filter-bar">
            <!-- Search Box -->
            <div class="search-input-wrapper" style="flex: 1; min-width: 240px;">
              <span class="search-icon">🔍</span>
              <input type="text" class="form-input" id="findings-search" placeholder="Search finding ID, description, rule, or detected value..." />
            </div>

            <!-- Severity Filter -->
            <div class="filter-group">
              <span class="filter-label">Severity:</span>
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
            <div class="filter-group">
              <span class="filter-label">Category:</span>
              <select class="form-select" id="findings-filter-cat">
                <option value="">All Categories</option>
                <option value="Formatting">Formatting</option>
                <option value="Structure">Structure</option>
                <option value="Table of Contents">Table of Contents</option>
                <option value="Table">Table</option>
                <option value="Figure">Figure</option>
                <option value="Equation">Equation</option>
                <option value="Grammar & Spelling">Grammar & Spelling</option>
                <option value="Engineering Parameter">Engineering Parameter</option>
                <option value="Semantic Inconsistency">Semantic Inconsistency</option>
                <option value="Logical Contradiction">Logical Contradiction</option>
                <option value="Standards Deviation">Standards Deviation</option>
              </select>
            </div>

            <!-- Page Filter -->
            <div class="filter-group">
              <span class="filter-label">Page:</span>
              <input type="number" class="form-input" id="findings-filter-page" placeholder="All" min="1" style="width: 70px; height: 32px; padding: 4px 8px; font-size: 12px;" />
            </div>

            <button class="btn btn-secondary btn-sm" id="findings-reset-btn">Reset Filters</button>
          </div>
        </div>

        <!-- Main Body: Split between Findings Table & Inspection Drawer -->
        <div style="display: flex; gap: 16px; align-items: flex-start; flex-wrap: wrap;">
          <!-- Findings Table Card -->
          <div class="findings-table-card" style="flex: 3; min-width: 500px;">
            <div class="card-header" style="padding: 12px 16px;">
              <div class="card-title">
                📋 Document Findings <span id="findings-count-badge" class="badge badge-info" style="margin-left: 6px;">0</span>
              </div>
              <div style="display: flex; gap: 8px;">
                <button class="btn btn-secondary btn-sm" onclick="window.router.navigate('viewer')">
                  👁️ View in Canvas
                </button>
                <button class="btn btn-primary btn-sm" onclick="window.router.navigate('reports')">
                  📄 Export Report
                </button>
              </div>
            </div>

            <div class="table-wrapper" style="border: none; border-radius: 0;">
              <table class="findings-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Severity</th>
                    <th>Category</th>
                    <th>Page</th>
                    <th>Location</th>
                    <th>Issue Description</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody id="findings-tbody">
                  <tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 32px;">Loading findings...</td></tr>
                </tbody>
              </table>
            </div>

            <!-- Pagination Footer -->
            <div class="card-footer" style="padding: 10px 16px;">
              <span style="font-size: 12px; color: var(--text-muted);" id="findings-page-info">Showing 0 of 0</span>
              <div style="display: flex; gap: 6px;">
                <button class="btn btn-secondary btn-sm" id="btn-prev-page" disabled>← Previous</button>
                <button class="btn btn-secondary btn-sm" id="btn-next-page" disabled>Next →</button>
              </div>
            </div>
          </div>

          <!-- Detailed Inspection Panel (Opens on finding selection) -->
          <div class="inspection-panel" id="findings-detail-panel" style="flex: 2; min-width: 320px; display: none;">
            <!-- Populated dynamically when a finding is clicked -->
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
    const pageInput = document.getElementById("findings-filter-page");
    const resetBtn = document.getElementById("findings-reset-btn");
    const prevBtn = document.getElementById("btn-prev-page");
    const nextBtn = document.getElementById("btn-next-page");

    let debounceTimer = null;
    if (searchInput) {
      searchInput.oninput = () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
          this.currentFilters.search = searchInput.value.trim();
          this.currentFilters.page = 1;
          this.fetchFindings();
        }, 250);
      };
    }

    if (sevSelect) {
      sevSelect.onchange = () => {
        this.currentFilters.severity = sevSelect.value;
        this.currentFilters.page = 1;
        this.fetchFindings();
      };
    }

    if (catSelect) {
      catSelect.onchange = () => {
        this.currentFilters.category = catSelect.value;
        this.currentFilters.page = 1;
        this.fetchFindings();
      };
    }

    if (pageInput) {
      pageInput.onchange = () => {
        this.currentFilters.page_num = pageInput.value.trim();
        this.currentFilters.page = 1;
        this.fetchFindings();
      };
    }

    if (resetBtn) {
      resetBtn.onclick = () => {
        if (searchInput) searchInput.value = "";
        if (sevSelect) sevSelect.value = "";
        if (catSelect) catSelect.value = "";
        if (pageInput) pageInput.value = "";
        this.currentFilters = { severity: "", category: "", search: "", page_num: "", confidence_min: "", page: 1, limit: 25 };
        this.fetchFindings();
      };
    }

    if (prevBtn) {
      prevBtn.onclick = () => {
        if (this.currentFilters.page > 1) {
          this.currentFilters.page--;
          this.fetchFindings();
        }
      };
    }

    if (nextBtn) {
      nextBtn.onclick = () => {
        this.currentFilters.page++;
        this.fetchFindings();
      };
    }
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
        page: this.currentFilters.page_num || undefined,
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
            <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 36px;">
              No findings matched the selected inspection criteria.
            </td>
          </tr>
        `;
        return;
      }

      tbody.innerHTML = res.findings.map((f) => {
        const sevClass = `badge-${f.severity.toLowerCase()}`;
        const issueSummary = f.explanation || f.original_content || f.detected_value || "Issue detected";
        const isSelected = this.selectedFinding && this.selectedFinding.finding_id === f.finding_id;

        return `
          <tr class="${isSelected ? 'selected' : ''}" onclick="window.FindingsView.selectFinding('${f.finding_id}')">
            <td><strong class="finding-code-id">${f.finding_id}</strong></td>
            <td><span class="badge ${sevClass}">${f.severity}</span></td>
            <td><span style="font-weight: 600;">${escapeHtml(f.category)}</span></td>
            <td>Page ${f.page_number || f.page}</td>
            <td><small style="color: var(--text-muted);">${escapeHtml(f.location || "-")}</small></td>
            <td style="max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(issueSummary)}">
              ${escapeHtml(issueSummary)}
            </td>
            <td>
              <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); window.FindingsView.locateInCanvas('${f.finding_id}')">
                Canvas
              </button>
            </td>
          </tr>
        `;
      }).join("");

      // If a finding is already selected, re-render panel
      if (this.selectedFinding) {
        const updated = res.findings.find((x) => x.finding_id === this.selectedFinding.finding_id);
        if (updated) this.renderDetailPanel(updated);
      } else if (res.findings.length > 0) {
        // Auto-select first finding for inspection convenience
        this.renderDetailPanel(res.findings[0]);
      }
    } catch (err) {
      console.error("Error loading findings:", err);
      window.toast.error("Failed loading findings table.");
    }
  },

  selectFinding(findingId) {
    const findings = window.appState.get("activeFindings") || [];
    let f = findings.find((x) => x.finding_id === findingId);
    if (!f) {
      // Find in current table
      const tbody = document.getElementById("findings-tbody");
      if (tbody) {
        const rows = tbody.querySelectorAll("tr");
        rows.forEach((r) => r.classList.remove("selected"));
      }
    }
    this.selectedFinding = f;

    // Fetch full finding detail from backend API
    window.api.findings.get(findingId).then((fullF) => {
      this.selectedFinding = fullF;
      this.renderDetailPanel(fullF);
    }).catch(() => {
      if (f) this.renderDetailPanel(f);
    });
  },

  renderDetailPanel(f) {
    const panel = document.getElementById("findings-detail-panel");
    if (!panel) return;

    panel.style.display = "flex";
    const sevClass = `badge-${f.severity.toLowerCase()}`;
    const precision = f.location_precision || "APPROXIMATE";

    panel.innerHTML = `
      <div class="inspection-header">
        <div class="inspection-title-group">
          <span class="finding-code-id">${escapeHtml(f.finding_id)}</span>
          <span class="finding-issue-name">${escapeHtml(f.category)} ${f.issue_type ? `• ${escapeHtml(f.issue_type)}` : ''}</span>
          <div class="inspection-location-badge">
            <span>📍 Page ${f.page_number || f.page}</span>
            <span>•</span>
            <span>${escapeHtml(f.location || "General Text")}</span>
          </div>
        </div>
        <div style="display: flex; gap: 6px; align-items: center;">
          <span class="badge ${sevClass}">${f.severity}</span>
        </div>
      </div>

      <!-- Problem Statement -->
      <div class="inspection-section">
        <span class="inspection-section-label">Problem</span>
        <div class="inspection-explanation-text">
          ${escapeHtml(f.explanation || f.message || "Document discrepancy detected.")}
        </div>
      </div>

      <!-- Comparison Grid: Detected vs Expected -->
      <div class="inspection-comparison-grid">
        <div class="comparison-box detected">
          <span class="comparison-label">Detected Content / Style</span>
          <div class="comparison-value">
            ${escapeHtml(String(f.detected_value || f.original_content || f.matched_text || "N/A"))}
          </div>
        </div>
        <div class="comparison-box expected">
          <span class="comparison-label">Expected Formatting / Value</span>
          <div class="comparison-value">
            ${escapeHtml(String(f.expected_value || f.expected_text || "Conforming specification standard"))}
          </div>
        </div>
      </div>

      <!-- Why / Rule Explanation -->
      <div class="inspection-section">
        <span class="inspection-section-label">Why This Failed</span>
        <div class="inspection-explanation-text">
          ${escapeHtml(f.explanation || "Does not conform to the configured engineering standards or template outline.")}
        </div>
      </div>

      <!-- Suggested Action: Information Only (NO APPLY BUTTON) -->
      <div class="inspection-remediation-box">
        <div class="remediation-notice">Suggested Action (Information Only)</div>
        <div class="remediation-guidance">
          💡 ${escapeHtml(f.suggested_correction || f.suggested_fix || "Review the reference and update it in the source document.")}
        </div>
      </div>

      <!-- Technical Metadata & Rule Evidence -->
      <div class="inspection-meta-grid">
        <div class="meta-item">
          <span class="meta-item-label">Rule / Standard</span>
          <span class="meta-item-val">${escapeHtml(f.rule_reference || f.rule_id || "SpecGuard Core Rules")}</span>
        </div>
        <div class="meta-item">
          <span class="meta-item-label">Location Precision</span>
          <span class="meta-item-val">${escapeHtml(precision)}</span>
        </div>
        <div class="meta-item">
          <span class="meta-item-label">Confidence Score</span>
          <span class="meta-item-val">${Math.round((f.confidence || 1.0) * 100)}%</span>
        </div>
        <div class="meta-item">
          <span class="meta-item-label">Detection Analyzer</span>
          <span class="meta-item-val">${escapeHtml(f.source_analyzer || "Deterministic Engine")}</span>
        </div>
      </div>

      <!-- Canvas Inspection Jump -->
      <button class="btn btn-primary" style="width: 100%; margin-top: 6px;" onclick="window.FindingsView.locateInCanvas('${f.finding_id}')">
        👁️ Locate and Highlight on Document Canvas
      </button>
    `;
  },

  locateInCanvas(findingId) {
    const findings = window.appState.get("activeFindings") || [];
    let f = findings.find((x) => x.finding_id === findingId) || this.selectedFinding;
    if (f) {
      window.appState.set("focusedFinding", f);
      window.appState.set("activePage", f.page_number || f.page || 1);
    }
    window.router.navigate("viewer");
  }
};
