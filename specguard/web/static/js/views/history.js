/**
 * SpecGuard Document History View
 * Repository archive inspection, comparison records, and revision diff analysis.
 */

window.HistoryView = {
  currentFilter: {
    domain: "",
    search: "",
    page: 1,
    limit: 20
  },

  async render(container) {
    container.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <!-- Filter Toolbar -->
        <div class="card">
          <div class="card-body" style="padding: 14px 18px;">
            <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
              <div class="search-input-wrapper" style="flex: 1; min-width: 260px;">
                <span class="search-icon">🔍</span>
                <input type="text" class="form-input" id="history-search" placeholder="Search by Comparison ID (CMP-XXXX) or filename..." />
              </div>

              <div style="display: flex; align-items: center; gap: 6px;">
                <span class="form-label" style="margin: 0;">Domain:</span>
                <select class="form-select" id="history-domain-select">
                  <option value="">All Domains</option>
                  <option value="mechanical">Mechanical</option>
                  <option value="electrical">Electrical</option>
                  <option value="chemical">Chemical</option>
                </select>
              </div>

              <button class="btn btn-secondary btn-sm" id="history-reset-btn">Reset</button>
            </div>
          </div>
        </div>

        <!-- History Table Card -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">
              📁 Document Comparison History <span id="history-count-badge" class="badge badge-info" style="margin-left: 6px;">0</span>
            </div>
            <button class="btn btn-primary btn-sm" onclick="window.router.navigate('new_analysis')">+ New Analysis</button>
          </div>
          <div class="card-body" style="padding: 0;">
            <div class="table-wrapper" style="border: none; border-radius: 0;">
              <table class="table">
                <thead>
                  <tr>
                    <th>Comparison ID</th>
                    <th>Document</th>
                    <th>Domain</th>
                    <th>Completed At</th>
                    <th>Duration</th>
                    <th>Critical</th>
                    <th>High</th>
                    <th>Total</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody id="history-tbody">
                  <tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 32px;">Loading history...</td></tr>
                </tbody>
              </table>
            </div>
          </div>
          <div class="card-footer">
            <span style="font-size: 12px; color: var(--text-muted);" id="history-page-info">Showing records</span>
            <div style="display: flex; gap: 6px;">
              <button class="btn btn-secondary btn-sm" id="btn-hist-prev" disabled>← Previous</button>
              <button class="btn btn-secondary btn-sm" id="btn-hist-next" disabled>Next →</button>
            </div>
          </div>
        </div>
      </div>
    `;

    this._bindEvents();
    await this.fetchHistory();
  },

  _bindEvents() {
    const searchInput = document.getElementById("history-search");
    const domainSelect = document.getElementById("history-domain-select");
    const resetBtn = document.getElementById("history-reset-btn");
    const prevBtn = document.getElementById("btn-hist-prev");
    const nextBtn = document.getElementById("btn-hist-next");

    let timer = null;
    searchInput.oninput = () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        this.currentFilter.search = searchInput.value.trim();
        this.currentFilter.page = 1;
        this.fetchHistory();
      }, 250);
    };

    domainSelect.onchange = () => {
      this.currentFilter.domain = domainSelect.value;
      this.currentFilter.page = 1;
      this.fetchHistory();
    };

    resetBtn.onclick = () => {
      searchInput.value = "";
      domainSelect.value = "";
      this.currentFilter = { domain: "", search: "", page: 1, limit: 20 };
      this.fetchHistory();
    };

    prevBtn.onclick = () => {
      if (this.currentFilter.page > 1) {
        this.currentFilter.page--;
        this.fetchHistory();
      }
    };

    nextBtn.onclick = () => {
      this.currentFilter.page++;
      this.fetchHistory();
    };
  },

  async fetchHistory() {
    const offset = (this.currentFilter.page - 1) * this.currentFilter.limit;

    try {
      const res = await window.api.history.list({
        domain: this.currentFilter.domain,
        search: this.currentFilter.search,
        limit: this.currentFilter.limit,
        offset: offset
      });

      const tbody = document.getElementById("history-tbody");
      const countBadge = document.getElementById("history-count-badge");
      const pageInfo = document.getElementById("history-page-info");
      const prevBtn = document.getElementById("btn-hist-prev");
      const nextBtn = document.getElementById("btn-hist-next");

      if (countBadge) countBadge.textContent = res.total_count;

      const startIdx = res.total_count > 0 ? offset + 1 : 0;
      const endIdx = Math.min(offset + res.comparisons.length, res.total_count);
      if (pageInfo) pageInfo.textContent = `Showing ${startIdx}-${endIdx} of ${res.total_count} records`;

      if (prevBtn) prevBtn.disabled = this.currentFilter.page <= 1;
      if (nextBtn) nextBtn.disabled = endIdx >= res.total_count;

      if (!res.comparisons || res.comparisons.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="9" style="text-align: center; color: var(--text-muted); padding: 36px;">
              No comparison records found.
            </td>
          </tr>
        `;
        return;
      }

      tbody.innerHTML = res.comparisons.map((c) => {
        const dateStr = c.analysis_completed_at ? new Date(c.analysis_completed_at).toLocaleString() : "-";
        return `
          <tr>
            <td><strong style="font-family: var(--font-mono); font-size: 12px;">${c.comparison_id}</strong></td>
            <td style="max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${c.document_filename}">
              ${c.document_filename}
            </td>
            <td><span class="badge badge-domain">${c.domain}</span></td>
            <td style="color: var(--text-secondary); font-size: 12px;">${dateStr}</td>
            <td style="font-family: var(--font-mono); font-size: 11.5px;">${c.duration_ms || 0}ms</td>
            <td><span class="badge badge-critical">${c.critical_count}</span></td>
            <td><span class="badge badge-high">${c.high_count}</span></td>
            <td><strong>${c.total_findings}</strong></td>
            <td>
              <div style="display: flex; gap: 6px;">
                <button class="btn btn-secondary btn-sm" onclick="window.HistoryView.openComparison('${c.comparison_id}')">
                  Open
                </button>
                <button class="btn btn-outline btn-sm" style="color: var(--sev-critical);" onclick="window.HistoryView.confirmDelete('${c.comparison_id}')">
                  ✕
                </button>
              </div>
            </td>
          </tr>
        `;
      }).join("");
    } catch (err) {
      console.error("Error loading history:", err);
      window.toast.error("Failed loading comparison history.");
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
      window.toast.error(`Error opening record: ${err.message}`);
    }
  },

  confirmDelete(comparisonId) {
    window.modal.confirm({
      title: "Delete Verification Record",
      message: `Are you sure you want to permanently delete archive record <strong>${comparisonId}</strong>? This action cannot be undone.`,
      confirmLabel: "Delete Record",
      isDanger: true,
      onConfirm: async () => {
        try {
          await window.api.history.delete(comparisonId);
          window.toast.success(`Record ${comparisonId} deleted.`);
          this.fetchHistory();
        } catch (err) {
          window.toast.error(`Deletion failed: ${err.message}`);
        }
      }
    });
  }
};
