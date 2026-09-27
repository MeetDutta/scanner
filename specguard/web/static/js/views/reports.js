/**
 * SpecGuard Document Inspection & Publication Readiness Report View
 * Formal compliance verification, configurable tolerance evaluation, and certified export.
 * 100% offline, local generation with strict reproducible session tracking.
 */

window.ReportsView = {
  currentTolerance: null,
  profiles: [],
  currentSessionId: null,

  async render(container) {
    let sessionId = window.appState.get("activeSessionId");
    let activeDoc = window.appState.get("activeDocument");

    if (!sessionId) {
      try {
        const recent = await window.api.dashboard.getRecent(1);
        if (recent.recent_comparisons && recent.recent_comparisons.length > 0) {
          const latest = recent.recent_comparisons[0];
          sessionId = latest.comparison_id;
          activeDoc = {
            filename: latest.document_filename,
            file_hash: latest.document_sha256,
            page_count: latest.page_count || 1
          };
          window.appState.set("activeSessionId", sessionId);
          window.appState.set("activeDocument", activeDoc);
        }
      } catch (e) {
        console.warn("Could not fetch recent session for reports:", e);
      }
    }

    if (!sessionId && !activeDoc) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📋</div>
          <div class="empty-state-title">No Analysis Available</div>
          <div class="empty-state-desc">Upload an engineering document and run an inspection to generate a formal Document Inspection & Publication Readiness Report.</div>
          <button class="btn btn-primary" onclick="window.router.navigate('new_analysis')">Start Document Inspection</button>
        </div>
      `;
      return;
    }

    this.currentSessionId = sessionId;

    // Show loading state while fetching tolerance report
    container.innerHTML = `
      <div style="max-width: 980px; margin: 0 auto; padding: 20px 0;">
        <div class="card" style="text-align: center; padding: 40px;">
          <div class="spinner" style="margin: 0 auto 16px;"></div>
          <div style="font-size: 15px; font-weight: 600; color: var(--text-primary);">Loading Document Tolerance Assessment...</div>
          <div style="font-size: 13px; color: var(--text-muted); margin-top: 4px;">Evaluating findings against publication tolerance profile</div>
        </div>
      </div>
    `;

    try {
      // Fetch available profiles and initial tolerance result in parallel
      const [profiles, tolerance] = await Promise.all([
        window.api.reports.getProfiles().catch(() => []),
        window.api.reports.getTolerance(sessionId)
      ]);

      this.profiles = profiles;
      this.currentTolerance = tolerance;

      this.renderReportUI(container);
    } catch (err) {
      container.innerHTML = `
        <div class="card" style="max-width: 800px; margin: 40px auto; padding: 30px; text-align: center;">
          <div style="font-size: 32px; margin-bottom: 12px;">⚠️</div>
          <div style="font-size: 18px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px;">Failed to Load Tolerance Assessment</div>
          <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 20px;">${err.message || "An unexpected error occurred while calculating document tolerance."}</div>
          <button class="btn btn-primary" onclick="window.ReportsView.render(document.getElementById('view-container'))">Retry</button>
        </div>
      `;
    }
  },

  renderReportUI(container) {
    const t = this.currentTolerance;
    const isAcceptable = t.acceptance_status === "WITHIN ACCEPTABLE TOLERANCE";
    const isNotEligible = t.acceptance_status === "NOT ELIGIBLE";

    let statusClass = "status-acceptable";
    let statusIcon = "✓";
    let statusBg = "#ecfdf5";
    let statusBorder = "#10b981";
    let statusText = "#065f46";

    if (isNotEligible) {
      statusClass = "status-not-eligible";
      statusIcon = "⚠️";
      statusBg = "#fef2f2";
      statusBorder = "#ef4444";
      statusText = "#991b1b";
    } else if (!isAcceptable) {
      statusClass = "status-above-tolerance";
      statusIcon = "✕";
      statusBg = "#fff7ed";
      statusBorder = "#f97316";
      statusText = "#9a3412";
    }

    // Gauge calculation: 0 to (max_tolerance * 2)
    const maxScale = Math.max(t.maximum_acceptable_tolerance * 2, t.tolerance_index * 1.25, 20.0);
    const needlePct = Math.min(100, Math.max(0, (t.tolerance_index / maxScale) * 100));
    const thresholdPct = Math.min(100, Math.max(0, (t.maximum_acceptable_tolerance / maxScale) * 100));

    container.innerHTML = `
      <div style="max-width: 980px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; padding-bottom: 60px;">
        
        <!-- Action & Configuration Bar -->
        <div class="card" style="border-top: 4px solid var(--accent-primary);">
          <div class="card-header" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
            <div>
              <div class="card-title" style="font-size: 17px; font-weight: 800; display: flex; align-items: center; gap: 8px;">
                <span>📋</span> Document Inspection & Publication Readiness
              </div>
              <div style="font-size: 12px; color: var(--text-muted); margin-top: 2px;">
                Formal quality compliance review for submission, publication, approval, or release.
              </div>
            </div>
            <div style="display: flex; gap: 8px; align-items: center;">
              <button class="btn btn-secondary btn-sm" onclick="window.ReportsView.toggleConfig()">
                ⚙️ Configure Metadata & Policy
              </button>
              <button class="btn btn-primary btn-sm" onclick="window.ReportsView.exportReport('pdf')">
                📥 Export PDF Report
              </button>
            </div>
          </div>

          <!-- Collapsible Metadata & Policy Config -->
          <div id="report-config-panel" style="display: none; padding: 16px 20px; background: var(--bg-surface-sunken); border-top: 1px solid var(--border-subtle);">
            <div style="font-size: 12px; font-weight: 700; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 12px;">
              Document Identification & Inspection Profile Settings
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px;">
              <div>
                <label style="display: block; font-size: 11px; font-weight: 600; color: var(--text-muted); margin-bottom: 4px;">Document Number</label>
                <input id="cfg-doc-no" type="text" class="form-input" style="width: 100%; padding: 7px 10px; font-size: 13px;" value="${t.document_no !== 'Not Provided' ? t.document_no : ''}" placeholder="e.g. ENG-MECH-042">
              </div>
              <div>
                <label style="display: block; font-size: 11px; font-weight: 600; color: var(--text-muted); margin-bottom: 4px;">Document Title</label>
                <input id="cfg-doc-title" type="text" class="form-input" style="width: 100%; padding: 7px 10px; font-size: 13px;" value="${t.document_title !== 'Not Provided' ? t.document_title : ''}" placeholder="e.g. Thermal System Specification">
              </div>
              <div>
                <label style="display: block; font-size: 11px; font-weight: 600; color: var(--text-muted); margin-bottom: 4px;">Revision / Version</label>
                <input id="cfg-revision" type="text" class="form-input" style="width: 100%; padding: 7px 10px; font-size: 13px;" value="${t.revision !== 'Not Provided' ? t.revision : ''}" placeholder="e.g. Rev. 03">
              </div>
              <div>
                <label style="display: block; font-size: 11px; font-weight: 600; color: var(--text-muted); margin-bottom: 4px;">Inspection Profile</label>
                <select id="cfg-profile" class="form-select" style="width: 100%; padding: 7px 10px; font-size: 13px;" onchange="window.ReportsView.onProfileChange(this.value)">
                  ${this.profiles.map(p => `
                    <option value="${p.profile_id}" ${p.name.toLowerCase() === t.inspection_profile.toLowerCase() || p.profile_id === t.inspection_profile ? 'selected' : ''}>
                      ${p.name} (Max: ${p.max_tolerance})
                    </option>
                  `).join('')}
                </select>
              </div>
              <div>
                <label style="display: block; font-size: 11px; font-weight: 600; color: var(--text-muted); margin-bottom: 4px;">Maximum Acceptable Tolerance</label>
                <input id="cfg-max-tolerance" type="number" step="0.5" min="1" max="100" class="form-input" style="width: 100%; padding: 7px 10px; font-size: 13px;" value="${t.maximum_acceptable_tolerance}">
              </div>
            </div>
            <div style="margin-top: 14px; display: flex; justify-content: flex-end; gap: 10px;">
              <button class="btn btn-secondary btn-sm" onclick="window.ReportsView.toggleConfig()">Cancel</button>
              <button class="btn btn-primary btn-sm" onclick="window.ReportsView.recalculateTolerance()">Apply & Recalculate Assessment</button>
            </div>
          </div>

          <!-- Quick Format Downloads Bar -->
          <div class="card-body" style="padding: 12px 20px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; background: var(--bg-surface);">
            <div style="display: flex; align-items: center; gap: 10px;">
              <span style="font-size: 12px; font-weight: 600; color: var(--text-muted);">Quick Export Formats:</span>
              <button class="btn btn-outline btn-xs" onclick="window.ReportsView.exportReport('pdf')">📑 PDF</button>
              <button class="btn btn-outline btn-xs" onclick="window.ReportsView.exportReport('html')">🌐 HTML</button>
              <button class="btn btn-outline btn-xs" onclick="window.ReportsView.exportReport('json')">💾 JSON</button>
              <button class="btn btn-outline btn-xs" onclick="window.ReportsView.exportReport('docx')">📝 DOCX</button>
            </div>
            <div style="display: flex; gap: 8px;">
              <button class="btn btn-secondary btn-xs" onclick="window.print()">🖨️ Print Report</button>
              <button class="btn btn-secondary btn-xs" onclick="window.router.navigate('findings')">🔍 Open Finding Details</button>
            </div>
          </div>
        </div>

        <!-- FORMAL DOCUMENT INSPECTION REPORT SHEET (Crisp Publication View) -->
        <div id="report-sheet" class="card" style="background: #ffffff; color: #0f172a; box-shadow: 0 10px 25px rgba(0,0,0,0.08); border-radius: 4px; border: 1px solid #cbd5e1; padding: 48px; max-width: 860px; margin: 0 auto; width: 100%;">
          
          <!-- Report Header -->
          <div style="border-bottom: 3px double #002b49; padding-bottom: 20px; text-align: center;">
            <div style="font-size: 26px; font-weight: 900; letter-spacing: 3px; color: #002b49;">SPECGuard</div>
            <div style="font-size: 11.5px; font-weight: 700; letter-spacing: 2px; color: #475569; margin-top: 4px; text-transform: uppercase;">
              ENGINEERING DOCUMENT QUALITY & COMPLIANCE INSPECTION
            </div>
            <div style="font-size: 17px; font-weight: 800; color: #0284c7; letter-spacing: 1.5px; margin-top: 10px; text-transform: uppercase;">
              DOCUMENT INSPECTION REPORT
            </div>
          </div>

          <!-- Document Identification Block -->
          <div style="margin-top: 24px;">
            <div style="font-size: 11px; font-weight: 800; letter-spacing: 1px; color: #64748b; text-transform: uppercase; margin-bottom: 8px;">
              Document Identification
            </div>
            <table style="width: 100%; border-collapse: collapse; font-size: 12.5px; border: 1px solid #cbd5e1;">
              <tbody>
                <tr style="border-bottom: 1px solid #e2e8f0;">
                  <td style="width: 28%; padding: 8px 12px; font-weight: 700; background: #f8fafc; color: #475569;">SESSION ID</td>
                  <td style="padding: 8px 12px; font-family: var(--font-mono); font-weight: 600; color: #0f172a;">${t.session_id}</td>
                </tr>
                <tr style="border-bottom: 1px solid #e2e8f0;">
                  <td style="padding: 8px 12px; font-weight: 700; background: #f8fafc; color: #475569;">DOCUMENT NO.</td>
                  <td style="padding: 8px 12px; font-weight: 600; color: #0f172a;">${t.document_no}</td>
                </tr>
                <tr style="border-bottom: 1px solid #e2e8f0;">
                  <td style="padding: 8px 12px; font-weight: 700; background: #f8fafc; color: #475569;">DOCUMENT TITLE</td>
                  <td style="padding: 8px 12px; font-weight: 600; color: #0f172a;">${t.document_title}</td>
                </tr>
                <tr style="border-bottom: 1px solid #e2e8f0;">
                  <td style="padding: 8px 12px; font-weight: 700; background: #f8fafc; color: #475569;">REVISION</td>
                  <td style="padding: 8px 12px; font-weight: 600; color: #0f172a;">${t.revision}</td>
                </tr>
                <tr style="border-bottom: 1px solid #e2e8f0;">
                  <td style="padding: 8px 12px; font-weight: 700; background: #f8fafc; color: #475569;">INSPECTION PROFILE</td>
                  <td style="padding: 8px 12px; font-weight: 600; color: #0f172a;">${t.inspection_profile}</td>
                </tr>
                <tr style="border-bottom: 1px solid #e2e8f0;">
                  <td style="padding: 8px 12px; font-weight: 700; background: #f8fafc; color: #475569;">INSPECTION DATE</td>
                  <td style="padding: 8px 12px; font-weight: 600; color: #0f172a;">${t.inspection_date}</td>
                </tr>
                <tr>
                  <td style="padding: 8px 12px; font-weight: 700; background: #f8fafc; color: #475569;">PAGES INSPECTED</td>
                  <td style="padding: 8px 12px; font-weight: 600; color: #0f172a;">${t.pages_inspected} Page${t.pages_inspected === 1 ? '' : 's'}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- PROMINENT TOLERANCE ASSESSMENT BLOCK -->
          <div style="margin-top: 28px; border: 2px solid ${statusBorder}; background: ${statusBg}; border-radius: 6px; padding: 24px; text-align: center;">
            <div style="font-size: 12px; font-weight: 800; letter-spacing: 2px; color: ${statusText}; text-transform: uppercase;">
              TOLERANCE ASSESSMENT
            </div>

            <div style="display: flex; justify-content: center; align-items: baseline; gap: 36px; margin: 16px 0 12px;">
              <div>
                <div style="font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">
                  TOLERANCE INDEX
                </div>
                <div style="font-size: 42px; font-weight: 900; color: ${statusText}; line-height: 1.1; margin-top: 4px;">
                  ${t.tolerance_index.toFixed(1)}
                </div>
                <div style="font-size: 10px; font-weight: 700; color: #64748b;">(LOWER IS BETTER)</div>
              </div>

              <div style="font-size: 28px; color: #94a3b8; font-weight: 300;">/</div>

              <div>
                <div style="font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">
                  MAXIMUM ACCEPTABLE
                </div>
                <div style="font-size: 42px; font-weight: 800; color: #334155; line-height: 1.1; margin-top: 4px;">
                  ${t.maximum_acceptable_tolerance.toFixed(1)}
                </div>
                <div style="font-size: 10px; font-weight: 700; color: #64748b;">(CONFIGURED LIMIT)</div>
              </div>
            </div>

            <!-- Tolerance Visual Meter / Gauge -->
            <div style="max-width: 440px; margin: 14px auto 10px; text-align: left;">
              <div style="display: flex; justify-content: space-between; font-size: 10px; font-weight: 700; color: #64748b; margin-bottom: 4px;">
                <span>0.0 (Zero Defects)</span>
                <span>Limit: ${t.maximum_acceptable_tolerance.toFixed(1)}</span>
                <span>${maxScale.toFixed(0)}+</span>
              </div>
              <div style="position: relative; height: 12px; background: #e2e8f0; border-radius: 6px; overflow: visible;">
                <!-- Threshold marker -->
                <div style="position: absolute; left: ${thresholdPct}%; top: -3px; bottom: -3px; width: 3px; background: #0f172a; z-index: 2;" title="Maximum Acceptable Tolerance: ${t.maximum_acceptable_tolerance}"></div>
                <!-- Needle bar -->
                <div style="position: absolute; left: 0; top: 0; bottom: 0; width: ${needlePct}%; background: ${isAcceptable ? '#10b981' : '#ef4444'}; border-radius: 6px 0 0 6px; z-index: 1;"></div>
              </div>
              <div style="display: flex; justify-content: space-between; font-size: 10px; color: #64748b; margin-top: 3px;">
                <span>Current: ${t.tolerance_index.toFixed(1)}</span>
                <span>Tolerance Utilization: ${t.tolerance_utilization.toFixed(0)}%</span>
              </div>
            </div>

            <!-- Acceptance Status Banner -->
            <div style="display: inline-block; margin-top: 14px; padding: 8px 24px; border-radius: 20px; font-size: 15px; font-weight: 800; letter-spacing: 1px; text-transform: uppercase; background: #ffffff; color: ${statusText}; border: 1.5px solid ${statusBorder}; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
              ${statusIcon} ${t.acceptance_status}
            </div>

            ${t.status_reason ? `
              <div style="font-size: 12px; font-weight: 600; color: ${statusText}; margin-top: 8px;">
                ${t.status_reason}
              </div>
            ` : ''}

            <div style="font-size: 12px; color: #475569; margin-top: 8px;">
              Tolerance Utilization: <strong>${t.tolerance_utilization.toFixed(0)}%</strong> of configured threshold
            </div>
          </div>

          <!-- Inspection Summary & Severity Distribution -->
          <div style="margin-top: 28px;">
            <div style="font-size: 11px; font-weight: 800; letter-spacing: 1px; color: #64748b; text-transform: uppercase; margin-bottom: 8px;">
              Inspection Summary
            </div>
            <div style="display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px; text-align: center;">
              <div style="border: 1px solid #cbd5e1; border-radius: 4px; padding: 10px 4px; background: #f8fafc;">
                <div style="font-size: 10px; font-weight: 700; color: #64748b; text-transform: uppercase;">Total</div>
                <div style="font-size: 20px; font-weight: 800; color: #0f172a; margin-top: 2px;">${t.total_findings}</div>
              </div>
              <div style="border: 1px solid ${t.critical_count > 0 ? '#ef4444' : '#cbd5e1'}; border-radius: 4px; padding: 10px 4px; background: ${t.critical_count > 0 ? '#fef2f2' : '#f8fafc'};">
                <div style="font-size: 10px; font-weight: 700; color: #dc2626; text-transform: uppercase;">Critical</div>
                <div style="font-size: 20px; font-weight: 800; color: #dc2626; margin-top: 2px;">${t.critical_count}</div>
              </div>
              <div style="border: 1px solid #cbd5e1; border-radius: 4px; padding: 10px 4px; background: #f8fafc;">
                <div style="font-size: 10px; font-weight: 700; color: #ea580c; text-transform: uppercase;">High</div>
                <div style="font-size: 20px; font-weight: 800; color: #ea580c; margin-top: 2px;">${t.high_count}</div>
              </div>
              <div style="border: 1px solid #cbd5e1; border-radius: 4px; padding: 10px 4px; background: #f8fafc;">
                <div style="font-size: 10px; font-weight: 700; color: #d97706; text-transform: uppercase;">Medium</div>
                <div style="font-size: 20px; font-weight: 800; color: #d97706; margin-top: 2px;">${t.medium_count}</div>
              </div>
              <div style="border: 1px solid #cbd5e1; border-radius: 4px; padding: 10px 4px; background: #f8fafc;">
                <div style="font-size: 10px; font-weight: 700; color: #0284c7; text-transform: uppercase;">Low</div>
                <div style="font-size: 20px; font-weight: 800; color: #0284c7; margin-top: 2px;">${t.low_count}</div>
              </div>
              <div style="border: 1px solid #cbd5e1; border-radius: 4px; padding: 10px 4px; background: #f8fafc;">
                <div style="font-size: 10px; font-weight: 700; color: #64748b; text-transform: uppercase;">Info</div>
                <div style="font-size: 20px; font-weight: 800; color: #64748b; margin-top: 2px;">${t.info_count}</div>
              </div>
            </div>
          </div>

          <!-- Compact Category Summary Table -->
          <div style="margin-top: 28px;">
            <div style="font-size: 11px; font-weight: 800; letter-spacing: 1px; color: #64748b; text-transform: uppercase; margin-bottom: 8px;">
              Category Summary
            </div>
            <table style="width: 100%; border-collapse: collapse; font-size: 12.5px; border: 1px solid #cbd5e1;">
              <thead>
                <tr style="background: #f1f5f9; border-bottom: 2px solid #cbd5e1;">
                  <th style="padding: 7px 12px; text-align: left; font-weight: 700; color: #334155;">Category</th>
                  <th style="padding: 7px 12px; text-align: right; font-weight: 700; color: #334155;">Findings</th>
                </tr>
              </thead>
              <tbody>
                ${Object.entries(t.category_summary || {}).map(([cat, count], idx) => `
                  <tr style="border-bottom: 1px solid #e2e8f0; background: ${idx % 2 === 0 ? '#ffffff' : '#f8fafc'};">
                    <td style="padding: 7px 12px; color: #334155;">${cat}</td>
                    <td style="padding: 7px 12px; text-align: right; font-weight: 700; color: ${count > 0 ? '#0f172a' : '#94a3b8'};">${count}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>

          <!-- Inspection Result Summary & Reference Note -->
          <div style="margin-top: 28px; padding: 16px 20px; background: #f8fafc; border-left: 4px solid #0284c7; border-radius: 0 4px 4px 0;">
            <div style="font-size: 12px; font-weight: 800; text-transform: uppercase; color: #0284c7; margin-bottom: 6px;">
              Inspection Result
            </div>
            <p style="font-size: 13px; color: #334155; line-height: 1.5; margin: 0 0 10px;">
              The analyzed document has a calculated Tolerance Index of <strong>${t.tolerance_index.toFixed(1)}</strong> against a configured maximum acceptable tolerance of <strong>${t.maximum_acceptable_tolerance.toFixed(1)}</strong> under the <em>${t.inspection_profile}</em> inspection profile. 
              The document is <strong>${isAcceptable ? 'within the configured inspection tolerance' : 'above the acceptable inspection tolerance'}</strong>.
            </p>
            <p style="font-size: 12px; color: #64748b; line-height: 1.4; margin: 0;">
              ℹ️ Detailed findings and their exact document locations are available in the SpecGuard inspection interface using Session ID: 
              <span style="font-family: var(--font-mono); font-weight: 600; color: #0284c7;">${t.session_id}</span>.
            </p>
          </div>

          <!-- Human Decision Disclaimer -->
          <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid #e2e8f0; text-align: center;">
            <p style="font-size: 11px; color: #64748b; line-height: 1.4; margin: 0 auto; max-width: 650px;">
              ${t.human_disclaimer}
            </p>
            <div style="margin-top: 8px; font-size: 10.5px; font-weight: 700; color: #94a3b8; letter-spacing: 0.5px;">
              SpecGuard Engineering Quality Framework • Engine Version ${t.engine_version}
            </div>
          </div>

        </div>

      </div>
    `;
  },

  toggleConfig() {
    const p = document.getElementById("report-config-panel");
    if (p) {
      p.style.display = p.style.display === "none" ? "block" : "none";
    }
  },

  onProfileChange(profileId) {
    const p = this.profiles.find(x => x.profile_id === profileId);
    if (p) {
      const maxInput = document.getElementById("cfg-max-tolerance");
      if (maxInput) {
        maxInput.value = p.max_tolerance;
      }
    }
  },

  async recalculateTolerance() {
    const docNo = document.getElementById("cfg-doc-no")?.value?.trim() || "";
    const docTitle = document.getElementById("cfg-doc-title")?.value?.trim() || "";
    const rev = document.getElementById("cfg-revision")?.value?.trim() || "";
    const profile = document.getElementById("cfg-profile")?.value || "";
    const maxTolVal = parseFloat(document.getElementById("cfg-max-tolerance")?.value);

    try {
      window.toast.info("Recalculating document tolerance...");
      const updated = await window.api.reports.getTolerance(this.currentSessionId, {
        document_no: docNo,
        document_title: docTitle,
        revision: rev,
        profile: profile,
        max_tolerance: isNaN(maxTolVal) ? undefined : maxTolVal
      });

      this.currentTolerance = updated;
      this.renderReportUI(document.getElementById("view-container"));
      window.toast.success("Tolerance assessment recalculated!");
    } catch (err) {
      window.toast.error(`Recalculation failed: ${err.message}`);
    }
  },

  async exportReport(format) {
    if (!this.currentTolerance) return;

    const docNo = document.getElementById("cfg-doc-no")?.value?.trim() || this.currentTolerance.document_no;
    const docTitle = document.getElementById("cfg-doc-title")?.value?.trim() || this.currentTolerance.document_title;
    const rev = document.getElementById("cfg-revision")?.value?.trim() || this.currentTolerance.revision;
    const profile = document.getElementById("cfg-profile")?.value || this.currentTolerance.inspection_profile;
    const maxTolVal = parseFloat(document.getElementById("cfg-max-tolerance")?.value) || this.currentTolerance.maximum_acceptable_tolerance;

    try {
      window.toast.info(`Generating formal ${format.toUpperCase()} report...`);
      const res = await window.api.reports.generate({
        session_id: this.currentSessionId,
        format: format,
        document_no: docNo !== "Not Provided" ? docNo : null,
        document_title: docTitle !== "Not Provided" ? docTitle : null,
        revision: rev !== "Not Provided" ? rev : null,
        inspection_profile: profile,
        max_tolerance: maxTolVal
      });

      window.toast.success(`Report ready: ${res.filename}`);

      // Browser download
      const a = document.createElement("a");
      a.href = res.download_url;
      a.download = res.filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (err) {
      window.toast.error(`Export failed: ${err.message}`);
    }
  }
};
