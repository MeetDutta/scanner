/**
 * SpecGuard Document Page Inspection Viewer
 * Interactive high-DPI canvas viewer with synchronized finding navigation,
 * visual highlighting, issue classification, and inspection drawer.
 * Strictly 100% READ-ONLY.
 */

window.ViewerView = {
  viewerInstance: null,

  async render(container) {
    let activeDoc = window.appState.get("activeDocument");
    const sessionId = window.appState.get("activeSessionId");
    let findings = window.appState.get("activeFindings") || [];
    const focusedFinding = window.appState.get("focusedFinding");

    // Auto-resolve activeDoc from session if missing
    if (!activeDoc && sessionId) {
      try {
        const hist = await window.api.history.get(sessionId);
        if (hist) {
          activeDoc = {
            filename: hist.document_filename,
            file_hash: hist.document_sha256,
            page_count: hist.page_count || 1
          };
          window.appState.set("activeDocument", activeDoc);
          if (hist.domain) window.appState.set("activeDomain", hist.domain);
        }
      } catch (e) {
        console.warn("Could not resolve document info from session:", e);
      }
    }

    if (!activeDoc) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">👁️</div>
          <div class="empty-state-title">No Analysis Available</div>
          <div class="empty-state-desc">Upload an engineering document and run an inspection to inspect pages and highlights.</div>
          <button class="btn btn-primary" onclick="window.router.navigate('new_analysis')">Start New Analysis</button>
        </div>
      `;
      return;
    }

    if (findings.length === 0 && sessionId) {
      try {
        const res = await window.api.findings.list({ session_id: sessionId, limit: 300 });
        findings = res.findings || [];
        window.appState.set("activeFindings", findings);
      } catch (e) {
        console.error("Error loading findings for viewer:", e);
      }
    }

    container.innerHTML = `
      <div class="viewer-shell" style="display: flex; flex-direction: column; height: 100%; gap: 10px; min-height: 0; flex: 1 1 auto;">
        <!-- Top Viewer Control Bar -->
        <div style="display: flex; align-items: center; justify-content: space-between; background: var(--bg-surface); padding: 8px 16px; border: 1px solid var(--border-default); border-radius: var(--radius-md); flex-shrink: 0;">
          <div style="display: flex; align-items: center; gap: 12px;">
            <button class="btn btn-secondary btn-sm" onclick="window.router.navigate('results')">
              ← Results
            </button>
            <button class="btn btn-secondary btn-sm" onclick="window.router.navigate('overview')">
              📑 Overview
            </button>
            <span style="font-size: 13px; font-weight: 800; color: var(--text-primary);">${escapeHtml(activeDoc.filename)}</span>
            <span class="badge badge-domain" style="text-transform: capitalize;">${escapeHtml(window.appState.get("activeDomain") || "Mechanical")}</span>
            <span class="badge" style="background: rgba(37, 99, 235, 0.1); color: var(--accent-primary); border: 1px solid rgba(37, 99, 235, 0.25);">
              Read-Only Inspection
            </span>
          </div>

          <div style="display: flex; gap: 8px;">
            <button class="btn btn-secondary btn-sm" onclick="window.router.navigate('findings')">
              📋 Document Findings (${findings.length})
            </button>
            <button class="btn btn-primary btn-sm" onclick="window.router.navigate('reports')">
              📄 Export Report
            </button>
          </div>
        </div>

        <!-- Document Viewer Mount Point -->
        <div id="viewer-mount-point" style="flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column;"></div>
      </div>
    `;

    // Instantiate viewer component
    const docId = activeDoc.file_hash || activeDoc.filename;
    this.viewerInstance = new window.DocumentViewerComponent("viewer-mount-point");
    window.currentViewer = this.viewerInstance;
    await this.viewerInstance.loadDocument(docId, activeDoc.page_count || 1, findings);

    const targetPage = window.appState.get("activePage");
    if (targetPage && targetPage !== 1) {
      this.viewerInstance.setPage(targetPage);
    }

    if (focusedFinding) {
      setTimeout(() => {
        this.viewerInstance.focusFinding(focusedFinding);
      }, 200);
    }
  }
};
