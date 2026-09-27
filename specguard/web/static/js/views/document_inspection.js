/**
 * SpecGuard Document Inspection Overview View
 * High-level quality overview, document AST outline, asset counts,
 * and interactive document-wide page error heatmap.
 */

window.DocumentInspectionView = {
  async render(container) {
    const activeDoc = window.appState.get("activeDocument");
    const sessionId = window.appState.get("activeSessionId");
    let findings = window.appState.get("activeFindings") || [];
    const activeDomain = window.appState.get("activeDomain") || "Mechanical";

    if (!activeDoc && !sessionId) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📑</div>
          <div class="empty-state-title">No Document Loaded for Inspection</div>
          <div class="empty-state-desc">Select an analyzed document from History or start a new verification pipeline.</div>
          <button class="btn btn-primary" onclick="window.router.navigate('history')">Select from History</button>
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
        console.error("Error loading findings:", e);
      }
    }

    const docId = activeDoc ? (activeDoc.file_hash || activeDoc.filename) : (sessionId || "current");
    let docDetails = null;
    try {
      docDetails = await window.api.documents.getInfo(docId);
    } catch (e) {
      console.warn("Could not fetch document AST info:", e);
    }

    const totalPages = (docDetails && docDetails.page_count) || (activeDoc && activeDoc.page_count) || 1;
    const docName = (docDetails && docDetails.filename) || (activeDoc && activeDoc.filename) || "Engineering Document";

    // Build page issue histogram
    const pageCounts = {};
    for (let p = 1; p <= totalPages; p++) {
      pageCounts[p] = 0;
    }
    findings.forEach((f) => {
      const p = f.page_number || f.page || 1;
      pageCounts[p] = (pageCounts[p] || 0) + 1;
    });

    const maxCount = Math.max(1, ...Object.values(pageCounts));

    // Category summary counts
    const catCounts = {};
    findings.forEach((f) => {
      const cat = f.category || "General";
      catCounts[cat] = (catCounts[cat] || 0) + 1;
    });

    container.innerHTML = `
      <div class="findings-container">
        <!-- Document Profile Summary Card -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">📑 Document Inspection Profile: ${escapeHtml(docName)}</div>
            <div style="display: flex; gap: 8px;">
              <button class="btn btn-primary btn-sm" onclick="window.router.navigate('viewer')">
                👁️ Open Page Inspection Canvas
              </button>
              <button class="btn btn-secondary btn-sm" onclick="window.router.navigate('reports')">
                📄 Export Report
              </button>
            </div>
          </div>
          <div class="card-body">
            <div class="inspection-meta-grid">
              <div class="meta-item">
                <span class="meta-item-label">Filename</span>
                <span class="meta-item-val" style="word-break: break-all;">${escapeHtml(docName)}</span>
              </div>
              <div class="meta-item">
                <span class="meta-item-label">Engineering Domain</span>
                <span class="meta-item-val" style="color: var(--accent-primary); text-transform: capitalize;">${escapeHtml(activeDomain)}</span>
              </div>
              <div class="meta-item">
                <span class="meta-item-label">Total Pages</span>
                <span class="meta-item-val">${totalPages} pages</span>
              </div>
              <div class="meta-item">
                <span class="meta-item-label">Inspection Session</span>
                <span class="meta-item-val">${escapeHtml(sessionId || "SES-LOCAL")}</span>
              </div>
              <div class="meta-item">
                <span class="meta-item-label">Detected Headings / Sections</span>
                <span class="meta-item-val">${docDetails && docDetails.sections ? docDetails.sections.length : "N/A"}</span>
              </div>
              <div class="meta-item">
                <span class="meta-item-label">Extracted Tables</span>
                <span class="meta-item-val">${docDetails && docDetails.tables ? docDetails.tables.length : "N/A"}</span>
              </div>
              <div class="meta-item">
                <span class="meta-item-label">Extracted Figures</span>
                <span class="meta-item-val">${docDetails && docDetails.figures ? docDetails.figures.length : "N/A"}</span>
              </div>
              <div class="meta-item">
                <span class="meta-item-label">Total Detected Issues</span>
                <span class="meta-item-val" style="color: var(--sev-high); font-weight: 800;">${findings.length}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Document-Wide Page Error Heatmap -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">🔥 Page Issue Density & Heatmap</div>
            <span style="font-size: 11.5px; color: var(--text-muted);">Click any page row to jump directly into Canvas Inspection</span>
          </div>
          <div class="card-body" style="padding: 10px 16px;">
            <div class="page-heatmap-container" style="border: none; padding: 0;">
              ${Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => {
                const count = pageCounts[p] || 0;
                const pct = Math.max(count > 0 ? 8 : 0, Math.round((count / maxCount) * 100));
                let densityClass = "density-low";
                if (count >= 5) densityClass = "density-critical";
                else if (count >= 3) densityClass = "density-high";
                else if (count >= 1) densityClass = "density-medium";

                return `
                  <div class="heatmap-row" onclick="window.DocumentInspectionView.jumpToPage(${p})">
                    <span class="heatmap-page-label">Page ${p}</span>
                    <div class="heatmap-bar-track">
                      <div class="heatmap-bar-fill ${densityClass}" style="width: ${pct}%;"></div>
                    </div>
                    <span class="heatmap-count-badge" style="color: ${count > 0 ? 'var(--text-primary)' : 'var(--text-muted)'};">
                      ${count} issue${count === 1 ? '' : 's'}
                    </span>
                  </div>
                `;
              }).join("")}
            </div>
          </div>
        </div>

        <!-- Issue Categories Breakdown -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">📊 Issue Category Breakdown</div>
          </div>
          <div class="card-body">
            <div class="categories-breakdown-grid">
              ${Object.entries(catCounts).map(([cat, cnt]) => `
                <div class="category-stat-card" onclick="window.DocumentInspectionView.filterCategory('${escapeHtml(cat)}')">
                  <div class="cat-stat-header">
                    <span class="cat-stat-title">${escapeHtml(cat)}</span>
                    <span class="cat-stat-icon">⚠️</span>
                  </div>
                  <span class="cat-stat-count">${cnt}</span>
                  <span class="cat-stat-sub">Click to inspect category issues →</span>
                </div>
              `).join("")}
            </div>
          </div>
        </div>

        <!-- Document Outline Tree if available -->
        ${docDetails && docDetails.sections && docDetails.sections.length > 0 ? `
          <div class="card">
            <div class="card-header">
              <div class="card-title">🌳 Detected Section Hierarchy Outline</div>
            </div>
            <div class="card-body">
              <div style="display: flex; flex-direction: column; gap: 6px; font-size: 13px;">
                ${docDetails.sections.map((s) => `
                  <div style="display: flex; align-items: center; justify-content: space-between; padding: 6px 10px; background: var(--bg-surface-sunken); border-radius: var(--radius-sm); margin-left: ${(s.level - 1) * 18}px; border-left: 3px solid var(--accent-primary);">
                    <span><strong>${escapeHtml(s.number_str || '')}</strong> ${escapeHtml(s.title || 'Untitled Section')}</span>
                    <span style="font-size: 11px; color: var(--text-muted);">Page ${s.page_num || 1}</span>
                  </div>
                `).join("")}
              </div>
            </div>
          </div>
        ` : ''}
      </div>
    `;
  },

  jumpToPage(pageNum) {
    window.appState.set("activePage", pageNum);
    window.router.navigate("viewer");
    setTimeout(() => {
      if (window.currentViewer) {
        window.currentViewer.setPage(pageNum);
      }
    }, 150);
  },

  filterCategory(category) {
    window.appState.set("selectedCategoryFilter", category);
    if (category.toLowerCase().includes("format")) {
      window.router.navigate("formatting");
    } else if (category.toLowerCase().includes("struct") || category.toLowerCase().includes("toc")) {
      window.router.navigate("structural");
    } else if (category.toLowerCase().includes("gramm") || category.toLowerCase().includes("engin") || category.toLowerCase().includes("logic")) {
      window.router.navigate("content");
    } else {
      window.router.navigate("findings");
    }
  }
};
