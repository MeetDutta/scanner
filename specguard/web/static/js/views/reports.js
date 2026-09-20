/**
 * SpecGuard Reports & Compliance Exports View
 * Generates and downloads certified PDF, DOCX, HTML, and JSON audit documents.
 */

window.ReportsView = {
  async render(container) {
    const sessionId = window.appState.get("activeSessionId");
    const activeDoc = window.appState.get("activeDocument");

    if (!sessionId) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📄</div>
          <div class="empty-state-title">No Active Verification Session Selected</div>
          <div class="empty-state-desc">Select a completed analysis from Document History to export certified audit reports.</div>
          <button class="btn btn-primary" onclick="window.router.navigate('history')">Select from History</button>
        </div>
      `;
      return;
    }

    const docName = activeDoc ? activeDoc.filename : "Specification";

    container.innerHTML = `
      <div style="max-width: 960px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px;">
        <!-- Active Session Banner -->
        <div class="card">
          <div class="card-body" style="display: flex; align-items: center; justify-content: space-between;">
            <div>
              <span style="font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">Selected Verification Session</span>
              <div style="font-size: 16px; font-weight: 800; color: var(--text-primary); margin-top: 2px;">
                ${docName} <span style="font-family: var(--font-mono); font-size: 13px; font-weight: 600; color: var(--accent-primary);">(${sessionId})</span>
              </div>
            </div>
            <button class="btn btn-outline btn-sm" onclick="window.router.navigate('history')">Change Session</button>
          </div>
        </div>

        <!-- 4 Export Cards Grid -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px;">
          <!-- 1. HTML Report -->
          <div class="card">
            <div class="card-header">
              <div class="card-title">🌐 HTML Compliance Report</div>
            </div>
            <div class="card-body" style="display: flex; flex-direction: column; gap: 10px;">
              <p style="font-size: 12.5px; color: var(--text-secondary); line-height: 1.4;">
                Standalone, high-resolution interactive report with executive summaries, statistics grid, and full finding tables.
              </p>
              <div style="margin-top: auto; display: flex; gap: 8px;">
                <button class="btn btn-secondary btn-sm" style="flex: 1;" onclick="window.ReportsView.previewHtml('${sessionId}')">
                  👁️ Preview
                </button>
                <button class="btn btn-primary btn-sm" style="flex: 1;" onclick="window.ReportsView.generateReport('${sessionId}', 'html')">
                  📥 Download
                </button>
              </div>
            </div>
          </div>

          <!-- 2. Certified Annotated PDF -->
          <div class="card">
            <div class="card-header">
              <div class="card-title">📑 Certified Annotated PDF</div>
            </div>
            <div class="card-body" style="display: flex; flex-direction: column; gap: 10px;">
              <p style="font-size: 12.5px; color: var(--text-secondary); line-height: 1.4;">
                Original engineering PDF embedded with vector bounding box highlights, severity color coding, and comment popups.
              </p>
              <div style="margin-top: auto;">
                <button class="btn btn-primary btn-sm" style="width: 100%;" onclick="window.ReportsView.generateReport('${sessionId}', 'pdf')">
                  📥 Export PDF with Highlights
                </button>
              </div>
            </div>
          </div>

          <!-- 3. Annotated Word Document -->
          <div class="card">
            <div class="card-header">
              <div class="card-title">📝 Annotated Word Document</div>
            </div>
            <div class="card-body" style="display: flex; flex-direction: column; gap: 10px;">
              <p style="font-size: 12.5px; color: var(--text-secondary); line-height: 1.4;">
                Microsoft Word format (.docx) with embedded executive audit summary tables and highlighted callouts.
              </p>
              <div style="margin-top: auto;">
                <button class="btn btn-primary btn-sm" style="width: 100%;" onclick="window.ReportsView.generateReport('${sessionId}', 'docx')">
                  📥 Export DOCX Audit
                </button>
              </div>
            </div>
          </div>

          <!-- 4. Findings JSON Data -->
          <div class="card">
            <div class="card-header">
              <div class="card-title">💾 Structured JSON Data</div>
            </div>
            <div class="card-body" style="display: flex; flex-direction: column; gap: 10px;">
              <p style="font-size: 12.5px; color: var(--text-secondary); line-height: 1.4;">
                Machine-readable findings dataset containing exact normalized bounding coordinates, priorities, deviations, and metadata.
              </p>
              <div style="margin-top: auto;">
                <button class="btn btn-secondary btn-sm" style="width: 100%;" onclick="window.ReportsView.generateReport('${sessionId}', 'json')">
                  📥 Download JSON Dataset
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  },

  async generateReport(sessionId, format) {
    try {
      window.toast.info(`Generating ${format.toUpperCase()} report...`);
      const res = await window.api.reports.generate({ session_id: sessionId, format: format });
      window.toast.success(`Report generated: ${res.filename}`);

      // Trigger browser download
      const a = document.createElement("a");
      a.href = res.download_url;
      a.download = res.filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (err) {
      window.toast.error(`Export failed: ${err.message}`);
    }
  },

  previewHtml(sessionId) {
    const previewUrl = window.api.reports.previewUrl(sessionId);
    window.modal.open({
      title: "Executive Compliance Report Preview",
      body: `
        <iframe src="${previewUrl}" style="width: 100%; height: 70vh; border: none; border-radius: var(--radius-md);"></iframe>
      `,
      footerButtons: [
        { label: "Close", class: "btn-secondary" },
        {
          label: "Download HTML",
          class: "btn-primary",
          onClick: () => this.generateReport(sessionId, "html")
        }
      ]
    });
  }
};
