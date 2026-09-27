/**
 * SpecGuard Dedicated Content & Engineering Issues View
 * Inspects spelling, grammar, terminology, engineering parameters,
 * logical contradictions, and standards deviations.
 */

window.ContentIssuesView = {
  activeTab: "all",

  async render(container) {
    const sessionId = window.appState.get("activeSessionId");
    let findings = window.appState.get("activeFindings") || [];

    const activeDoc = window.appState.get("activeDocument");

    if (!sessionId && !activeDoc) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📝</div>
          <div class="empty-state-title">No Analysis Available</div>
          <div class="empty-state-desc">Upload an engineering document and run an inspection to check grammar, content, and engineering rules.</div>
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
        console.error("Error loading findings:", e);
      }
    }

    const contentFindings = findings.filter((f) => {
      const cat = (f.category || "").toLowerCase();
      const exp = (f.explanation || "").toLowerCase();
      return (
        cat.includes("grammar") ||
        cat.includes("spelling") ||
        cat.includes("parameter") ||
        cat.includes("engineering") ||
        cat.includes("logical") ||
        cat.includes("semantic") ||
        cat.includes("standard") ||
        exp.includes("spelling") ||
        exp.includes("contradiction") ||
        exp.includes("parameter") ||
        exp.includes("tolerance")
      );
    });

    const groups = {
      grammar: contentFindings.filter((f) => {
        const text = `${f.category} ${f.explanation} ${f.issue_type}`.toLowerCase();
        return text.includes("grammar") || text.includes("spelling") || text.includes("typo") || text.includes("punctuation") || text.includes("repeated");
      }),
      parameters: contentFindings.filter((f) => {
        const text = `${f.category} ${f.explanation}`.toLowerCase();
        return text.includes("parameter") || text.includes("engineering") || text.includes("tolerance") || text.includes("unit");
      }),
      logic: contentFindings.filter((f) => {
        const text = `${f.category} ${f.explanation}`.toLowerCase();
        return text.includes("logical") || text.includes("contradiction") || text.includes("semantic");
      }),
      standards: contentFindings.filter((f) => {
        const text = `${f.category} ${f.explanation} ${f.rule_reference}`.toLowerCase();
        return text.includes("standard") || text.includes("ieee") || text.includes("iso") || text.includes("deviation");
      })
    };

    let displayList = contentFindings;
    if (this.activeTab !== "all" && groups[this.activeTab]) {
      displayList = groups[this.activeTab];
    }

    container.innerHTML = `
      <div class="findings-container">
        <!-- Content Header Card -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">📝 Content, Terminology & Engineering Verification</div>
            <span class="badge badge-info">${contentFindings.length} Total Content Issues</span>
          </div>
          <div class="card-body">
            <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 12px; line-height: 1.45;">
              Validates technical spelling, sentence structure, repeated tokens, engineering parameter tolerances,
              cross-document value contradictions, and domain standards compliance.
            </p>

            <!-- Group Tabs -->
            <div class="formatting-groups-tabs">
              <button class="formatting-tab-btn ${this.activeTab === 'all' ? 'active' : ''}" data-tab="all">
                All Issues (${contentFindings.length})
              </button>
              <button class="formatting-tab-btn ${this.activeTab === 'grammar' ? 'active' : ''}" data-tab="grammar">
                Grammar & Terminology (${groups.grammar.length})
              </button>
              <button class="formatting-tab-btn ${this.activeTab === 'parameters' ? 'active' : ''}" data-tab="parameters">
                Engineering Parameters (${groups.parameters.length})
              </button>
              <button class="formatting-tab-btn ${this.activeTab === 'logic' ? 'active' : ''}" data-tab="logic">
                Logical Contradictions (${groups.logic.length})
              </button>
              <button class="formatting-tab-btn ${this.activeTab === 'standards' ? 'active' : ''}" data-tab="standards">
                Standards Deviations (${groups.standards.length})
              </button>
            </div>
          </div>
        </div>

        <!-- Issue Cards List -->
        <div style="display: flex; flex-direction: column; gap: 12px;">
          ${displayList.length === 0 ? `
            <div class="empty-state" style="padding: 32px;">
              <div class="empty-state-icon">✓</div>
              <div class="empty-state-title">No Content Issues Found in this Category</div>
              <div class="empty-state-desc">All technical parameters, terminology, and logical assertions adhere to requirements.</div>
            </div>
          ` : displayList.map((f) => {
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
                      Page ${f.page_number || f.page} • ${escapeHtml(f.location || "Content")}
                    </span>
                    <button class="btn btn-secondary btn-sm" onclick="window.ContentIssuesView.locate('${f.finding_id}')">
                      👁️ Inspect on Canvas
                    </button>
                  </div>
                </div>

                <!-- Problem Statement -->
                <div class="inspection-explanation-text">
                  <strong>Issue Description:</strong> ${escapeHtml(f.explanation || "Content discrepancy detected.")}
                </div>

                <!-- Detected vs Expected Comparison Grid -->
                <div class="inspection-comparison-grid">
                  <div class="comparison-box detected">
                    <span class="comparison-label">Detected Content</span>
                    <span class="comparison-value">${escapeHtml(String(f.detected_value || f.original_content || "Discrepant text"))}</span>
                  </div>
                  <div class="comparison-box expected">
                    <span class="comparison-label">Expected Value / Standard</span>
                    <span class="comparison-value">${escapeHtml(String(f.expected_value || f.expected_text || "Conforming engineering value"))}</span>
                  </div>
                </div>

                <!-- Suggested Action (Information Only) -->
                <div class="inspection-remediation-box">
                  <div class="remediation-notice">Suggested Corrective Action (Information Only)</div>
                  <div class="remediation-guidance">
                    💡 ${escapeHtml(f.suggested_correction || f.suggested_fix || "Verify and update in source document.")}
                  </div>
                </div>
              </div>
            `;
          }).join("")}
        </div>
      </div>
    `;

    // Bind tab clicks
    container.querySelectorAll(".formatting-tab-btn").forEach((btn) => {
      btn.onclick = () => {
        this.activeTab = btn.getAttribute("data-tab");
        this.render(container);
      };
    });
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
