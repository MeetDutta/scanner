/**
 * SpecGuard Document Viewer View
 * Wraps DocumentViewerComponent with side-by-side canvas, high-DPI pages,
 * finding overlays, zoom controls, and instant finding jump targeting.
 */

window.ViewerView = {
  viewerInstance: null,

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

    container.innerHTML = `
      <div style="display: flex; flex-direction: column; height: 100%; gap: 10px;">
        <!-- Top Viewer Control Bar -->
        <div style="display: flex; align-items: center; justify-content: space-between; background: var(--bg-surface); padding: 8px 16px; border: 1px solid var(--border-default); border-radius: var(--radius-md);">
          <div style="display: flex; align-items: center; gap: 12px;">
            <button class="btn btn-secondary btn-sm" onclick="window.router.navigate('results')">
              ← Back to Results
            </button>
            <span style="font-size: 13px; font-weight: 800; color: var(--text-primary);">${activeDoc.filename}</span>
            <span class="badge badge-domain">${window.appState.get("activeDomain") || "Mechanical"}</span>
          </div>

          <div style="display: flex; gap: 8px;">
            <button class="btn btn-primary btn-sm" onclick="window.router.navigate('reports')">
              📄 Export Certified PDF
            </button>
          </div>
        </div>

        <!-- Document Viewer Mount Point -->
        <div id="viewer-mount-point" style="flex: 1; min-height: 0;"></div>
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
