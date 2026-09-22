/**
 * SpecGuard / DocReady Document Viewer View
 * Wraps DocumentViewerComponent with side-by-side canvas, high-DPI pages,
 * finding overlays, zoom controls, and instant finding jump targeting.
 */

window.ViewerView = {
  viewerInstance: null,

  async openChangeReport() {
    const sessionId = window.appState.get("activeSessionId");
    if (!sessionId) {
      window.router.navigate("reports");
      return;
    }
    try {
      window.toast.info("Generating Rectification Change Report...");
      const res = await window.api.reports.generate(sessionId, "changes");
      if (res && res.download_url) {
        window.open(res.download_url, "_blank");
      } else {
        window.router.navigate("reports");
      }
    } catch (e) {
      window.router.navigate("reports");
    }
  },

  downloadEdited() {
    const sessionId = window.appState.get("activeSessionId");
    if (!sessionId) {
      window.toast.error("No active analysis session found.");
      return;
    }
    window.open(window.api.editor.fileUrl(sessionId), "_blank");
  },

  async render(container) {
    const activeDoc = window.appState.get("activeDocument");
    const findings = window.appState.get("activeFindings") || [];
    const focusedFinding = window.appState.get("focusedFinding");

    if (!activeDoc) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📄</div>
          <div class="empty-state-title">No Document Loaded for Viewing</div>
          <div class="empty-state-desc">Select a verified document from History or run a new analysis to inspect pages and highlights.</div>
          <button class="btn btn-primary" onclick="window.router.navigate('history')">Select from History</button>
        </div>
      `;
      return;
    }

    container.classList.add("viewer-container");

    container.innerHTML = `
      <div style="display: flex; flex-direction: column; height: 100%; width: 100%; max-width: 100%; min-width: 0; min-height: 0; gap: 6px; overflow: hidden; box-sizing: border-box;">
        <!-- Top Viewer Control Bar -->
        <div style="display: flex; align-items: center; justify-content: space-between; background: var(--bg-surface); padding: 6px 12px; border: 1px solid var(--border-default); border-radius: var(--radius-md); flex-shrink: 0; width: 100%; max-width: 100%; min-width: 0; box-sizing: border-box; gap: 8px;">
          <div style="display: flex; align-items: center; gap: 8px; min-width: 0; flex: 1;">
            <button class="btn btn-secondary btn-sm" onclick="window.router.navigate('results')" style="flex-shrink: 0;">
              ← Back
            </button>
            <span style="font-size: 13px; font-weight: 800; color: var(--text-primary); letter-spacing: 0.2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 280px;" title="${escapeHtml(activeDoc.filename)}">${escapeHtml(activeDoc.filename)}</span>
            <span class="badge badge-domain" style="text-transform: uppercase; flex-shrink: 0; font-size: 10px;">${window.appState.get("activeDomain") || "Mechanical"}</span>
          </div>

          <div style="display: flex; gap: 6px; align-items: center; flex-shrink: 0;">
            <button class="btn btn-secondary btn-sm" onclick="window.ViewerView.downloadEdited()" title="Download current saved working copy">
              💾 Download
            </button>
            <button class="btn btn-secondary btn-sm" onclick="window.ViewerView.openChangeReport()" title="Generate & View Certified Rectification Change Report">
              📝 Change Report
            </button>
            <button class="btn btn-primary btn-sm" onclick="window.router.navigate('reports')" title="Export certified PDF/HTML audit report">
              📄 Export Audit
            </button>
          </div>
        </div>

        <!-- Document Viewer Mount Point -->
        <div id="viewer-mount-point" style="flex: 1; min-height: 0; min-width: 0; width: 100%; max-width: 100%; position: relative; overflow: hidden; box-sizing: border-box;"></div>
      </div>
    `;

    // Instantiate viewer component
    const docId = activeDoc.file_hash || activeDoc.filename;
    this.viewerInstance = new window.DocumentViewerComponent("viewer-mount-point");
    window.currentViewer = this.viewerInstance;
    this.viewerInstance.loadDocument(docId, activeDoc.page_count || 1, findings);

    if (focusedFinding) {
      setTimeout(() => {
        this.viewerInstance.focusFinding(focusedFinding);
      }, 250);
    }
  }
};
