/**
 * SpecGuard Standards & Templates Inspector View
 * Browses domain templates, sections hierarchy, parameters definitions,
 * and machine-readable engineering rule criteria.
 */

window.StandardsView = {
  activeDomain: "mechanical",

  async render(container) {
    container.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 20px;">
        <!-- Domain Tabs Toolbar -->
        <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--border-default); padding-bottom: 8px;">
          <div style="display: flex; gap: 8px;" id="standards-domain-tabs">
            <button class="btn btn-primary btn-sm" data-domain="mechanical">⚙️ Mechanical Engineering</button>
            <button class="btn btn-secondary btn-sm" data-domain="electrical">⚡ Electrical Engineering</button>
            <button class="btn btn-secondary btn-sm" data-domain="chemical">🧪 Chemical Engineering</button>
          </div>
          <span style="font-size: 11.5px; font-weight: 700; color: #10b981;">
            ✓ 100% Local Standards Knowledge Base
          </span>
        </div>

        <!-- Template Overview Card -->
        <div class="card" id="tmpl-overview-card">
          <div class="card-header">
            <div class="card-title" id="tmpl-title">Domain Template</div>
            <span class="badge badge-domain" id="tmpl-badge">TMPL-001</span>
          </div>
          <div class="card-body">
            <p id="tmpl-desc" style="color: var(--text-secondary); font-size: 13px; line-height: 1.4;"></p>
          </div>
        </div>

        <!-- Split: Expected Sections Hierarchy & Engineering Parameters -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
          <!-- Left: Sections -->
          <div class="card">
            <div class="card-header">
              <div class="card-title">📑 Required Document Sections</div>
            </div>
            <div class="card-body" style="padding: 0;">
              <div class="table-wrapper" style="border: none; border-radius: 0;">
                <table class="table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Section Title</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody id="tmpl-sections-tbody">
                    <tr><td colspan="3" style="text-align: center; color: var(--text-muted); padding: 24px;">Loading sections...</td></tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <!-- Right: Parameters Definition -->
          <div class="card">
            <div class="card-header">
              <div class="card-title">📐 Domain Engineering Parameters</div>
            </div>
            <div class="card-body" style="padding: 0;">
              <div class="table-wrapper" style="border: none; border-radius: 0;">
                <table class="table">
                  <thead>
                    <tr>
                      <th>Parameter</th>
                      <th>Unit</th>
                      <th>Allowed Range</th>
                      <th>Severity</th>
                    </tr>
                  </thead>
                  <tbody id="tmpl-params-tbody">
                    <tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 24px;">Loading parameters...</td></tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        <!-- Bottom: Installed Rules -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">⚖️ Installed Local Standards Rules (<span id="tmpl-rules-count">0</span>)</div>
          </div>
          <div class="card-body" style="padding: 0;">
            <div class="table-wrapper" style="border: none; border-radius: 0;">
              <table class="table">
                <thead>
                  <tr>
                    <th>Rule ID</th>
                    <th>Standard Reference</th>
                    <th>Target Parameter</th>
                    <th>Condition / Operator</th>
                    <th>Expected / Range</th>
                    <th>Severity</th>
                  </tr>
                </thead>
                <tbody id="tmpl-rules-tbody">
                  <tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 24px;">Loading rules...</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    `;

    this._bindEvents();
    await this.loadDomain(this.activeDomain);
  },

  _bindEvents() {
    const tabs = document.querySelectorAll("#standards-domain-tabs button");
    tabs.forEach((btn) => {
      btn.onclick = () => {
        tabs.forEach((b) => {
          b.className = "btn btn-secondary btn-sm";
        });
        btn.className = "btn btn-primary btn-sm";
        this.activeDomain = btn.getAttribute("data-domain");
        this.loadDomain(this.activeDomain);
      };
    });
  },

  async loadDomain(domain) {
    try {
      const data = await window.api.standards.getDomain(domain);

      // Populate Overview
      document.getElementById("tmpl-title").textContent = data.document_title;
      document.getElementById("tmpl-badge").textContent = data.template_id;
      document.getElementById("tmpl-desc").textContent = data.description || "Specification guidelines and engineering parameters compliance criteria.";

      // Populate Sections
      const secTbody = document.getElementById("tmpl-sections-tbody");
      secTbody.innerHTML = (data.sections || []).map((s) => `
        <tr>
          <td><strong style="font-family: var(--font-mono);">${s.number}</strong></td>
          <td><strong>${s.title}</strong></td>
          <td>
            ${s.required ? `<span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #059669;">MANDATORY</span>` : `<span class="badge badge-info">OPTIONAL</span>`}
          </td>
        </tr>
      `).join("") || `<tr><td colspan="3" style="text-align: center;">No sections defined.</td></tr>`;

      // Populate Parameters
      const paramTbody = document.getElementById("tmpl-params-tbody");
      paramTbody.innerHTML = (data.parameters || []).map((p) => {
        const rangeStr = (p.min_value !== null || p.max_value !== null)
          ? `${p.min_value ?? "-"} to ${p.max_value ?? "-"}`
          : (p.allowed_values ? p.allowed_values.join(", ") : "Defined in rule");
        const sevClass = `badge-${(p.severity_on_deviation || "Medium").toLowerCase()}`;

        return `
          <tr>
            <td>
              <strong>${p.display_name || p.parameter}</strong>
              ${p.aliases && p.aliases.length > 0 ? `<div style="font-size: 10.5px; color: var(--text-muted);">${p.aliases.join(", ")}</div>` : ""}
            </td>
            <td><code style="color: var(--accent-primary);">${p.unit || "-"}</code></td>
            <td style="font-size: 12px; font-family: var(--font-mono);">${rangeStr}</td>
            <td><span class="badge ${sevClass}">${p.severity_on_deviation || "High"}</span></td>
          </tr>
        `;
      }).join("") || `<tr><td colspan="4" style="text-align: center;">No parameters defined.</td></tr>`;

      // Populate Rules
      const rulesTbody = document.getElementById("tmpl-rules-tbody");
      const rulesCount = document.getElementById("tmpl-rules-count");
      const rules = data.rules || [];
      if (rulesCount) rulesCount.textContent = rules.length;

      rulesTbody.innerHTML = rules.map((r) => {
        const sevClass = `badge-${(r.severity || "Medium").toLowerCase()}`;
        const refStr = r.reference || r._standard_name || "SpecGuard Standard";
        const expectedStr = r.expected_value || (r.allowed_range ? `${r.allowed_range[0]} - ${r.allowed_range[1]}` : (r.allowed_values ? r.allowed_values.join(", ") : "-"));

        return `
          <tr>
            <td><strong style="font-family: var(--font-mono); font-size: 12px;">${r.rule_id || "-"}</strong></td>
            <td style="font-weight: 600; color: var(--text-secondary);">${refStr}</td>
            <td><strong style="color: var(--text-primary);">${r.parameter || "-"}</strong></td>
            <td><code>${r.operator || "allowed_values"}</code></td>
            <td><code style="color: #10b981;">${expectedStr} ${r.unit || ""}</code></td>
            <td><span class="badge ${sevClass}">${r.severity || "High"}</span></td>
          </tr>
        `;
      }).join("") || `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 24px;">No standard rules installed for this domain.</td></tr>`;
    } catch (err) {
      console.error("Error loading standards:", err);
      window.toast.error("Failed loading domain template.");
    }
  }
};
