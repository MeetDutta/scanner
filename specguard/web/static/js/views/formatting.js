/**
 * SpecGuard Dedicated Formatting Inspection View
 * Classifies all formatting findings into Typography, Paragraph, Layout,
 * Headings, Tables, Figures, and Equations.
 * Strictly READ-ONLY: Shows Detected vs Expected and Suggested Action as information only.
 */

window.FormattingView = {
  activeTab: "all",

  async render(container) {
    const sessionId = window.appState.get("activeSessionId");
    let findings = window.appState.get("activeFindings") || [];

    const activeDoc = window.appState.get("activeDocument");

    if (!sessionId && !activeDoc) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">🎨</div>
          <div class="empty-state-title">No Analysis Available</div>
          <div class="empty-state-desc">Upload an engineering document and run an inspection to analyze formatting and typography.</div>
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

    // Filter formatting-related findings
    const formattingFindings = findings.filter((f) => {
      const cat = (f.category || "").toLowerCase();
      const loc = (f.location || "").toLowerCase();
      const exp = (f.explanation || "").toLowerCase();
      const it = (f.issue_type || "").toLowerCase();
      return (
        cat.includes("format") ||
        cat.includes("layout") ||
        cat.includes("table") ||
        cat.includes("figure") ||
        cat.includes("equation") ||
        cat.includes("structure") ||
        it.includes("font") ||
        it.includes("margin") ||
        exp.includes("font") ||
        exp.includes("pt ") ||
        exp.includes("spacing") ||
        exp.includes("margin") ||
        exp.includes("caption") ||
        exp.includes("heading") ||
        loc.includes("heading") ||
        loc.includes("table") ||
        loc.includes("figure")
      );
    });

    // Grouping by Subcategory
    const groups = {
      typography: formattingFindings.filter((f) => {
        const text = `${f.category} ${f.explanation} ${f.detected_value} ${f.issue_type}`.toLowerCase();
        return text.includes("font") || text.includes("pt") || text.includes("bold") || text.includes("italic") || text.includes("underline") || text.includes("style");
      }),
      paragraph: formattingFindings.filter((f) => {
        const text = `${f.category} ${f.explanation} ${f.detected_value} ${f.location}`.toLowerCase();
        return text.includes("paragraph") || text.includes("align") || text.includes("indent") || text.includes("line spacing") || text.includes("spacing");
      }),
      layout: formattingFindings.filter((f) => {
        const text = `${f.category} ${f.explanation} ${f.detected_value} ${f.location}`.toLowerCase();
        return text.includes("margin") || text.includes("header") || text.includes("footer") || text.includes("page size") || text.includes("page number");
      }),
      headings: formattingFindings.filter((f) => {
        const text = `${f.category} ${f.explanation} ${f.detected_value} ${f.location}`.toLowerCase();
        return text.includes("heading") || text.includes("section header") || text.includes("title");
      }),
      tables: formattingFindings.filter((f) => {
        const text = `${f.category} ${f.explanation} ${f.location}`.toLowerCase();
        return text.includes("table");
      }),
      figures: formattingFindings.filter((f) => {
        const text = `${f.category} ${f.explanation} ${f.location}`.toLowerCase();
        return text.includes("figure") || text.includes("drawing") || text.includes("caption");
      }),
      equations: formattingFindings.filter((f) => {
        const text = `${f.category} ${f.explanation} ${f.location}`.toLowerCase();
        return text.includes("equation") || text.includes("formula");
      })
    };

    let displayList = formattingFindings;
    if (this.activeTab !== "all" && groups[this.activeTab]) {
      displayList = groups[this.activeTab];
    }

    container.innerHTML = `
      <div class="findings-container">
        <!-- Formatting Header Card -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">🎨 Formatting Quality & Style Consistency</div>
            <span class="badge badge-info">${formattingFindings.length} Total Formatting Issues</span>
          </div>
          <div class="card-body">
            <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 12px; line-height: 1.45;">
              Automated inspection of document typography, paragraph styling, page margins, heading hierarchy,
              table formats, and figure caption compliance against engineering publishing standards.
            </p>

            <!-- Group Tabs -->
            <div class="formatting-groups-tabs">
              <button class="formatting-tab-btn ${this.activeTab === 'all' ? 'active' : ''}" data-tab="all">
                All Issues (${formattingFindings.length})
              </button>
              <button class="formatting-tab-btn ${this.activeTab === 'typography' ? 'active' : ''}" data-tab="typography">
                Typography (${groups.typography.length})
              </button>
              <button class="formatting-tab-btn ${this.activeTab === 'paragraph' ? 'active' : ''}" data-tab="paragraph">
                Paragraph (${groups.paragraph.length})
              </button>
              <button class="formatting-tab-btn ${this.activeTab === 'layout' ? 'active' : ''}" data-tab="layout">
                Layout & Margins (${groups.layout.length})
              </button>
              <button class="formatting-tab-btn ${this.activeTab === 'headings' ? 'active' : ''}" data-tab="headings">
                Headings (${groups.headings.length})
              </button>
              <button class="formatting-tab-btn ${this.activeTab === 'tables' ? 'active' : ''}" data-tab="tables">
                Tables (${groups.tables.length})
              </button>
              <button class="formatting-tab-btn ${this.activeTab === 'figures' ? 'active' : ''}" data-tab="figures">
                Figures (${groups.figures.length})
              </button>
              <button class="formatting-tab-btn ${this.activeTab === 'equations' ? 'active' : ''}" data-tab="equations">
                Equations (${groups.equations.length})
              </button>
            </div>
          </div>
        </div>

        <!-- Issue Cards List -->
        <div style="display: flex; flex-direction: column; gap: 12px;">
          ${displayList.length === 0 ? `
            <div class="empty-state" style="padding: 32px;">
              <div class="empty-state-icon">✓</div>
              <div class="empty-state-title">No Formatting Issues Found in this Category</div>
              <div class="empty-state-desc">The document complies with all configured style and formatting rules for this section.</div>
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
                      Page ${f.page_number || f.page} • ${escapeHtml(f.location || "Document Region")}
                    </span>
                    <button class="btn btn-secondary btn-sm" onclick="window.FormattingView.locate('${f.finding_id}')">
                      👁️ Inspect on Canvas
                    </button>
                  </div>
                </div>

                <!-- Problem Statement -->
                <div class="inspection-explanation-text">
                  <strong>Problem:</strong> ${escapeHtml(f.explanation || "Formatting deviation detected.")}
                </div>

                <!-- Detected vs Expected Comparison Grid -->
                <div class="inspection-comparison-grid">
                  <div class="comparison-box detected">
                    <span class="comparison-label">Detected Formatting</span>
                    <span class="comparison-value">${escapeHtml(String(f.detected_value || f.original_content || "Non-conforming style"))}</span>
                  </div>
                  <div class="comparison-box expected">
                    <span class="comparison-label">Expected Formatting</span>
                    <span class="comparison-value">${escapeHtml(String(f.expected_value || f.expected_text || "Standard profile specification"))}</span>
                  </div>
                </div>

                <!-- Suggested Action (Information Only) -->
                <div class="inspection-remediation-box">
                  <div class="remediation-notice">Suggested Corrective Action (Information Only)</div>
                  <div class="remediation-guidance">
                    💡 ${escapeHtml(f.suggested_correction || f.suggested_fix || "Apply configured style manually in the source document.")}
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
