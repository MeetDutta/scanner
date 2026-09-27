/**
 * SpecGuard Dedicated Structural & Hierarchy Issues View
 * Inspects document outline, missing sections, heading hierarchy,
 * Table of Contents drift, and figure/table numbering sequences.
 */

window.StructuralIssuesView = {
  async render(container) {
    const sessionId = window.appState.get("activeSessionId");
    let findings = window.appState.get("activeFindings") || [];

    if (!sessionId && findings.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">🏗️</div>
          <div class="empty-state-title">No Structural Analysis Data</div>
          <div class="empty-state-desc">Run a document verification to inspect section hierarchy, TOC synchronicity, and heading sequences.</div>
          <button class="btn btn-primary" onclick="window.router.navigate('new_analysis')">Start Analysis</button>
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

    const structuralFindings = findings.filter((f) => {
      const cat = (f.category || "").toLowerCase();
      const it = (f.issue_type || "").toLowerCase();
      const exp = (f.explanation || "").toLowerCase();
      return (
        cat.includes("structure") ||
        cat.includes("table of contents") ||
        cat.includes("toc") ||
        cat.includes("cross-ref") ||
        cat.includes("hierarchy") ||
        it.includes("toc") ||
        it.includes("duplicate") ||
        it.includes("missing_section") ||
        exp.includes("hierarchy") ||
        exp.includes("section") ||
        exp.includes("table of contents") ||
        exp.includes("numbering") ||
        exp.includes("drift")
      );
    });

    container.innerHTML = `
      <div class="findings-container">
        <!-- Structural Issues Header Card -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">🏗️ Structural Integrity & Hierarchy Compliance</div>
            <span class="badge badge-info">${structuralFindings.length} Structural Issues</span>
          </div>
          <div class="card-body">
            <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.45;">
              Identifies missing required headings, incorrect section numbering hierarchies, duplicate sections,
              orphan figures, cross-reference breaks, and Table of Contents page drift.
            </p>
          </div>
        </div>

        <!-- Issue Cards List -->
        <div style="display: flex; flex-direction: column; gap: 12px;">
          ${structuralFindings.length === 0 ? `
            <div class="empty-state" style="padding: 32px;">
              <div class="empty-state-icon">✓</div>
              <div class="empty-state-title">No Structural Issues Detected</div>
              <div class="empty-state-desc">The document maintains perfect section hierarchy, numbering order, and Table of Contents synchronicity.</div>
            </div>
          ` : structuralFindings.map((f) => {
            const sevClass = `badge-${f.severity.toLowerCase()}`;
            return `
              <div class="issue-card">
                <div class="issue-card-header">
                  <div style="display: flex; align-items: center; gap: 10px;">
                    <span class="finding-code-id">${escapeHtml(f.finding_id)}</span>
                    <span class="badge ${sevClass}">${f.severity}</span>
                    <span style="font-size: 13px; font-weight: 700; color: var(--text-primary);">${escapeHtml(f.category)}</span>
                  </div>
                  <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 11.5px; color: var(--text-muted);">
                      Page ${f.page_number || f.page} • ${escapeHtml(f.location || "Outline")}
                    </span>
                    <button class="btn btn-secondary btn-sm" onclick="window.StructuralIssuesView.locate('${f.finding_id}')">
                      👁️ Inspect on Canvas
                    </button>
                  </div>
                </div>

                <!-- Problem Statement -->
                <div class="inspection-explanation-text">
                  <strong>Structural Problem:</strong> ${escapeHtml(f.explanation || "Section structural discrepancy.")}
                </div>

                <!-- Detected vs Expected Comparison Grid -->
                <div class="inspection-comparison-grid">
                  <div class="comparison-box detected">
                    <span class="comparison-label">Detected in Document</span>
                    <span class="comparison-value">${escapeHtml(String(f.detected_value || f.original_content || "Discrepant structure"))}</span>
                  </div>
                  <div class="comparison-box expected">
                    <span class="comparison-label">Expected Structure / Outline</span>
                    <span class="comparison-value">${escapeHtml(String(f.expected_value || f.expected_text || "Conforming numbering & hierarchy"))}</span>
                  </div>
                </div>

                <!-- Suggested Action (Information Only) -->
                <div class="inspection-remediation-box">
                  <div class="remediation-notice">Suggested Corrective Action (Information Only)</div>
                  <div class="remediation-guidance">
                    💡 ${escapeHtml(f.suggested_correction || f.suggested_fix || "Align section hierarchy manually in the source document.")}
                  </div>
                </div>
              </div>
            `;
          }).join("")}
        </div>
      </div>
    `;
  },

  locate(findingId) {
    const findings = window.appState.get("activeFindings") || [];
    const f = findings.find((x) => x.finding_id === findingId);
    if (f) {
      window.appState.set("focusedFinding", f);
      window.appState.set("activePage", f.page_number || f.page || 1);
    }
    window.router.navigate("findings");
  }
};
