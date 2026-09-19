/**
 * SpecGuard Model Training, Custom Templates & Profile Learning View
 * Integrates:
 * 1. Hardware Awareness & Local Compute Profile
 * 2. Custom Document Template Management (Creation, Samples, Profile Learning)
 * 3. Human Profile Review & Gated Approval Workflow
 * 4. Region Annotations & Dataset Sufficiency Validation
 * 5. Local Supervised Machine Learning Training & Evaluation
 * 6. Model Registry & Checkpoints
 * Strictly 100% offline.
 */

window.TrainingView = {
  activeTemplateId: null,
  activeSubTab: "samples",

  async render(container) {
    container.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 24px;">
        <!-- 1. Hardware Awareness Card -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">🖥️ Local Computing Hardware & Device Profile</div>
            <span class="badge badge-domain" id="hw-accel-badge">DETECTING...</span>
          </div>
          <div class="card-body">
            <div class="hardware-specs-grid" id="hw-specs-grid">
              <div class="hardware-spec-box">
                <span class="hardware-spec-label">Target Computing Device</span>
                <span class="hardware-spec-value" id="hw-device-val">-</span>
              </div>
              <div class="hardware-spec-box">
                <span class="hardware-spec-label">CPU Cores</span>
                <span class="hardware-spec-value" id="hw-cores-val">-</span>
              </div>
              <div class="hardware-spec-box">
                <span class="hardware-spec-label">System RAM</span>
                <span class="hardware-spec-value" id="hw-ram-val">-</span>
              </div>
              <div class="hardware-spec-box">
                <span class="hardware-spec-label">Recommended Batch Size</span>
                <span class="hardware-spec-value" id="hw-batch-val">-</span>
              </div>
            </div>
            <div style="margin-top: 14px; font-size: 12.5px; color: var(--text-secondary); background: var(--bg-surface-sunken); padding: 10px 14px; border-radius: var(--radius-md); border-left: 3px solid var(--accent-primary);" id="hw-recommendation-box">
              Analyzing hardware capabilities...
            </div>
          </div>
        </div>

        <!-- 2. Custom Templates & Profile Learning Platform -->
        <div class="card">
          <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div class="card-title">📐 Custom Document Templates & Profile Learning</div>
              <div style="font-size: 12px; color: var(--text-muted); margin-top: 2px;">
                Learn layout rules, typography, and section structures from sample documents without cloud AI.
              </div>
            </div>
            <button class="btn btn-primary btn-sm" id="btn-create-template-modal">
              + Create New Template
            </button>
          </div>
          <div class="card-body" style="display: flex; flex-direction: column; gap: 16px;">
            <!-- Template Selector Row -->
            <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
              <label style="font-size: 13px; font-weight: 600; color: var(--text-secondary);">Select Custom Template:</label>
              <select id="custom-template-select" style="padding: 8px 12px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); background: var(--bg-surface-sunken); color: var(--text-primary); min-width: 260px; font-size: 13px;">
                <option value="">Loading templates...</option>
              </select>
              <button class="btn btn-secondary btn-sm" id="btn-refresh-templates">🔄 Refresh</button>
              <button class="btn btn-outline btn-sm" id="btn-delete-template" style="display: none; color: var(--sev-critical); border-color: var(--sev-critical);">🗑️ Delete Template</button>
            </div>

            <!-- Active Template Container -->
            <div id="template-workspace-container" style="display: none;">
              <!-- Template Header Pill -->
              <div style="display: flex; justify-content: space-between; align-items: center; padding: 14px 18px; background: var(--bg-surface-sunken); border-radius: var(--radius-md); border: 1px solid var(--border-subtle); margin-bottom: 16px;">
                <div>
                  <div style="font-size: 16px; font-weight: 700; color: var(--text-primary);" id="tmpl-view-name">Template Name</div>
                  <div style="font-size: 12px; color: var(--text-secondary); margin-top: 3px;" id="tmpl-view-desc">Description</div>
                </div>
                <div style="display: flex; gap: 10px; align-items: center;">
                  <span class="badge" id="tmpl-status-badge">DRAFT</span>
                  <span style="font-family: var(--font-mono); font-size: 12px; color: var(--text-muted);" id="tmpl-version-tag">v1.0.0</span>
                </div>
              </div>

              <!-- Workflow Sub-Tabs -->
              <div style="display: flex; gap: 8px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 8px; margin-bottom: 16px;">
                <button class="btn btn-secondary btn-sm active" id="tab-btn-samples" onclick="window.TrainingView.switchSubTab('samples')">1. Sample Documents</button>
                <button class="btn btn-secondary btn-sm" id="tab-btn-learn" onclick="window.TrainingView.switchSubTab('learn')">2. Profile Learning</button>
                <button class="btn btn-secondary btn-sm" id="tab-btn-review" onclick="window.TrainingView.switchSubTab('review')">3. Review & Approval</button>
                <button class="btn btn-secondary btn-sm" id="tab-btn-annotate" onclick="window.TrainingView.switchSubTab('annotate')">4. Region Annotations</button>
                <button class="btn btn-secondary btn-sm" id="tab-btn-ml" onclick="window.TrainingView.switchSubTab('ml')">5. Local ML Training</button>
                <button class="btn btn-secondary btn-sm" id="tab-btn-versions" onclick="window.TrainingView.switchSubTab('versions')">6. Version History</button>
              </div>

              <!-- Sub-Tab 1: Sample Documents -->
              <div id="subtab-samples" class="template-subtab-pane">
                <div style="display: flex; flex-direction: column; gap: 14px;">
                  <div style="border: 2px dashed var(--border-subtle); border-radius: var(--radius-md); padding: 24px; text-align: center; cursor: pointer; background: var(--bg-surface-sunken);" id="sample-dropzone">
                    <span style="font-size: 32px;">📤</span>
                    <div style="font-weight: 600; margin-top: 6px;">Click or drag PDF/DOCX sample documents here</div>
                    <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">Samples are stored in an isolated local directory with SHA-256 deduplication.</div>
                    <input type="file" id="sample-file-input" style="display: none;" accept=".pdf,.docx" />
                  </div>
                  <div id="sample-conflicts-banner" style="display: none; padding: 10px 14px; background: rgba(239, 68, 68, 0.1); border: 1px solid var(--sev-critical); border-radius: var(--radius-sm); color: var(--sev-critical); font-size: 12.5px;"></div>
                  <div class="table-wrapper" style="border: 1px solid var(--border-subtle); border-radius: var(--radius-md);">
                    <table class="table">
                      <thead>
                        <tr>
                          <th>Sample ID</th>
                          <th>Filename</th>
                          <th>Pages</th>
                          <th>SHA-256 Digest</th>
                          <th>Status</th>
                          <th>Action</th>
                        </tr>
                      </thead>
                      <tbody id="samples-tbody">
                        <tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 20px;">No samples uploaded yet.</td></tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              <!-- Sub-Tab 2: Profile Learning Wizard -->
              <div id="subtab-learn" class="template-subtab-pane" style="display: none;">
                <div style="display: flex; flex-direction: column; gap: 16px;">
                  <div style="display: flex; justify-content: space-between; align-items: center;">
                    <p style="font-size: 13px; color: var(--text-secondary); margin: 0;">
                      Learns layout dimensions, typography, section hierarchies, and table/figure conventions across all uploaded samples.
                    </p>
                    <button class="btn btn-primary btn-sm" id="btn-run-learning">🧠 Learn Profile from Samples</button>
                  </div>
                  <div id="learned-profile-results" style="display: none; display: flex; flex-direction: column; gap: 16px;">
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px;" id="learned-cards-grid"></div>
                  </div>
                </div>
              </div>

              <!-- Sub-Tab 3: Review & Approval -->
              <div id="subtab-review" class="template-subtab-pane" style="display: none;">
                <div style="display: flex; flex-direction: column; gap: 16px;">
                  <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                      <h4 style="margin: 0; font-size: 14px; color: var(--text-primary);">Profile Review & Approval Gate</h4>
                      <div style="font-size: 12px; color: var(--text-muted);">
                        Review automatically learned properties, adjust numerical tolerances, and approve template before activation.
                      </div>
                    </div>
                    <div style="display: flex; gap: 10px;">
                      <button class="btn btn-secondary btn-sm" id="btn-approve-profile">✓ Approve Profile</button>
                      <button class="btn btn-primary btn-sm" id="btn-activate-template">⚡ Activate for Analysis</button>
                    </div>
                  </div>
                  <div id="review-properties-container" style="display: flex; flex-direction: column; gap: 12px;"></div>
                </div>
              </div>

              <!-- Sub-Tab 4: Region Annotations -->
              <div id="subtab-annotate" class="template-subtab-pane" style="display: none;">
                <div style="display: flex; flex-direction: column; gap: 16px;">
                  <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                      <h4 style="margin: 0; font-size: 14px;">Human-in-the-Loop Region Labeling</h4>
                      <div style="font-size: 12px; color: var(--text-muted);">Label regions: Title, Heading, Body, Caption, Table, Figure, Equation, Header, Footer.</div>
                    </div>
                    <div id="annotation-health-badge" class="badge">Checking Readiness...</div>
                  </div>
                  <div class="table-wrapper" style="border: 1px solid var(--border-subtle); border-radius: var(--radius-md);">
                    <table class="table">
                      <thead>
                        <tr>
                          <th>Annotation ID</th>
                          <th>Sample</th>
                          <th>Page</th>
                          <th>Region Label</th>
                          <th>Bounding Box</th>
                          <th>Action</th>
                        </tr>
                      </thead>
                      <tbody id="annotations-tbody">
                        <tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 20px;">No annotations recorded.</td></tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              <!-- Sub-Tab 5: Local ML Training -->
              <div id="subtab-ml" class="template-subtab-pane" style="display: none;">
                <div style="display: flex; flex-direction: column; gap: 16px;">
                  <p style="font-size: 13px; color: var(--text-secondary); margin: 0;">
                    Train an optional local layout region classifier using strictly document-level data partition splitting.
                  </p>
                  <div style="display: flex; gap: 12px; align-items: center;">
                    <button class="btn btn-primary btn-sm" id="btn-train-ml-model">🚀 Start Local Supervised ML Training</button>
                    <span style="font-size: 12px; color: var(--text-muted);">Uses local PyTorch. Zero remote AI calls.</span>
                  </div>
                  <div id="ml-training-results" style="display: none; padding: 16px; background: var(--bg-surface-sunken); border-radius: var(--radius-md); border: 1px solid var(--border-subtle);"></div>
                </div>
              </div>

              <!-- Sub-Tab 6: Version History -->
              <div id="subtab-versions" class="template-subtab-pane" style="display: none;">
                <div class="table-wrapper" style="border: 1px solid var(--border-subtle); border-radius: var(--radius-md);">
                  <table class="table">
                    <thead>
                      <tr>
                        <th>Version Tag</th>
                        <th>Created At</th>
                        <th>Status</th>
                        <th>Note</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody id="versions-tbody">
                      <tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 20px;">No versions available.</td></tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 3. Local Model Registry -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">🤖 Local Model Registry & Checkpoints</div>
            <button class="btn btn-secondary btn-sm" id="btn-refresh-models">Refresh Registry</button>
          </div>
          <div class="card-body" style="padding: 0;">
            <div class="table-wrapper" style="border: none; border-radius: 0;">
              <table class="table">
                <thead>
                  <tr>
                    <th>Model ID</th>
                    <th>Task</th>
                    <th>Domain</th>
                    <th>Version</th>
                    <th>Status</th>
                    <th>Integrity Hash</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody id="models-tbody">
                  <tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 32px;">Loading model registry...</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <!-- Create Template Modal -->
      <div id="modal-create-template" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 9999; align-items: center; justify-content: center;">
        <div style="background: var(--bg-surface); width: 480px; max-width: 90vw; border-radius: var(--radius-lg); border: 1px solid var(--border-subtle); padding: 24px; display: flex; flex-direction: column; gap: 16px; box-shadow: 0 20px 40px rgba(0,0,0,0.4);">
          <div style="font-size: 16px; font-weight: 700; color: var(--text-primary);">Create New Custom Template</div>
          <div style="display: flex; flex-direction: column; gap: 12px;">
            <div>
              <label style="font-size: 12px; font-weight: 600; color: var(--text-secondary);">Template ID (e.g. acme_spec, lab_report)</label>
              <input type="text" id="modal-input-id" class="input" style="width: 100%; margin-top: 4px;" placeholder="acme_spec_2026" />
            </div>
            <div>
              <label style="font-size: 12px; font-weight: 600; color: var(--text-secondary);">Display Name</label>
              <input type="text" id="modal-input-name" class="input" style="width: 100%; margin-top: 4px;" placeholder="Acme Engineering Specification" />
            </div>
            <div>
              <label style="font-size: 12px; font-weight: 600; color: var(--text-secondary);">Category / Domain</label>
              <input type="text" id="modal-input-cat" class="input" style="width: 100%; margin-top: 4px;" placeholder="Engineering Specification" />
            </div>
            <div>
              <label style="font-size: 12px; font-weight: 600; color: var(--text-secondary);">Description</label>
              <textarea id="modal-input-desc" class="input" style="width: 100%; height: 70px; margin-top: 4px;" placeholder="Specification rules for Acme mechanical components..."></textarea>
            </div>
          </div>
          <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 8px;">
            <button class="btn btn-secondary btn-sm" id="btn-cancel-create-tmpl">Cancel</button>
            <button class="btn btn-primary btn-sm" id="btn-confirm-create-tmpl">Create Template</button>
          </div>
        </div>
      </div>
    `;

    this.bindEvents();
    await this.loadHardware();
    await this.loadTemplates();
    await this.loadModels();
  },

  bindEvents() {
    document.getElementById("btn-refresh-models").onclick = () => this.loadModels();
    document.getElementById("btn-refresh-templates").onclick = () => this.loadTemplates();

    // Modal
    const modal = document.getElementById("modal-create-template");
    document.getElementById("btn-create-template-modal").onclick = () => {
      modal.style.display = "flex";
    };
    document.getElementById("btn-cancel-create-tmpl").onclick = () => {
      modal.style.display = "none";
    };
    document.getElementById("btn-confirm-create-tmpl").onclick = () => this.createTemplate();

    // Select change
    document.getElementById("custom-template-select").onchange = (e) => {
      this.selectTemplate(e.target.value);
    };

    // Dropzone
    const dropzone = document.getElementById("sample-dropzone");
    const fileInput = document.getElementById("sample-file-input");
    dropzone.onclick = () => fileInput.click();
    fileInput.onchange = (e) => {
      if (e.target.files.length > 0) {
        this.uploadSample(e.target.files[0]);
      }
    };

    // Learning, Approval, Activation
    document.getElementById("btn-run-learning").onclick = () => this.runLearning();
    document.getElementById("btn-approve-profile").onclick = () => this.approveProfile();
    document.getElementById("btn-activate-template").onclick = () => this.activateTemplate();
    document.getElementById("btn-train-ml-model").onclick = () => this.trainMLModel();
  },

  async loadHardware() {
    try {
      const hw = await window.api.models.hardware();
      document.getElementById("hw-accel-badge").textContent = hw.gpu_available ? "ACCELERATION ACTIVE" : "CPU FALLBACK";
      document.getElementById("hw-device-val").textContent = hw.device_name;
      document.getElementById("hw-cores-val").textContent = `${hw.cpu_cores} Physical Cores`;
      document.getElementById("hw-ram-val").textContent = `${hw.ram_gb} GB`;
      document.getElementById("hw-batch-val").textContent = `${hw.recommended_batch_size} (Optimal)`;
      document.getElementById("hw-recommendation-box").textContent = `💡 ${hw.recommendations}`;
    } catch (err) {
      console.warn("Could not load hardware profile:", err);
    }
  },

  async loadTemplates() {
    try {
      const list = await window.api.templates.list();
      const select = document.getElementById("custom-template-select");
      if (!list || list.length === 0) {
        select.innerHTML = `<option value="">No custom templates created yet</option>`;
        document.getElementById("template-workspace-container").style.display = "none";
        return;
      }
      select.innerHTML = list.map(t => `<option value="${t.template_id}">${t.name} (${t.status})</option>`).join("");
      if (!this.activeTemplateId && list.length > 0) {
        this.selectTemplate(list[0].template_id);
      } else if (this.activeTemplateId) {
        select.value = this.activeTemplateId;
        this.selectTemplate(this.activeTemplateId);
      }
    } catch (err) {
      console.error("Failed loading templates:", err);
    }
  },

  async selectTemplate(templateId) {
    if (!templateId) return;
    this.activeTemplateId = templateId;
    document.getElementById("template-workspace-container").style.display = "block";
    try {
      const data = await window.api.templates.get(templateId);
      const meta = data.metadata;
      document.getElementById("tmpl-view-name").textContent = meta.name;
      document.getElementById("tmpl-view-desc").textContent = meta.description || meta.category;
      document.getElementById("tmpl-status-badge").textContent = meta.status;
      document.getElementById("tmpl-version-tag").textContent = `v${meta.version}`;

      this.switchSubTab(this.activeSubTab);
    } catch (err) {
      window.toast.error(`Error loading template: ${err.message}`);
    }
  },

  switchSubTab(tabName) {
    this.activeSubTab = tabName;
    ["samples", "learn", "review", "annotate", "ml", "versions"].forEach(t => {
      const btn = document.getElementById(`tab-btn-${t}`);
      const pane = document.getElementById(`subtab-${t}`);
      if (btn && pane) {
        if (t === tabName) {
          btn.classList.add("active");
          pane.style.display = "block";
        } else {
          btn.classList.remove("active");
          pane.style.display = "none";
        }
      }
    });

    if (tabName === "samples") this.loadSamples();
    if (tabName === "review") this.loadReview();
    if (tabName === "annotate") this.loadAnnotations();
    if (tabName === "versions") this.loadVersions();
  },

  async uploadSample(file) {
    if (!this.activeTemplateId) return;
    window.toast.info(`Uploading & parsing sample: ${file.name}...`);
    try {
      const res = await window.api.templates.uploadSample(this.activeTemplateId, file);
      window.toast.success(`Sample '${res.sample.sample_id}' ingested successfully.`);
      this.loadSamples();
    } catch (err) {
      window.toast.error(`Sample ingestion error: ${err.message}`);
    }
  },

  async loadSamples() {
    if (!this.activeTemplateId) return;
    try {
      const samples = await window.api.templates.listSamples(this.activeTemplateId);
      const tbody = document.getElementById("samples-tbody");
      if (!samples || samples.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 20px;">No samples uploaded yet.</td></tr>`;
        return;
      }
      tbody.innerHTML = samples.map(s => `
        <tr>
          <td><code style="font-size: 11px;">${s.sample_id}</code></td>
          <td><strong>${s.filename}</strong></td>
          <td>${s.page_count} Pages</td>
          <td><code style="font-size: 11px; color: var(--text-muted);">${(s.file_hash || "").substring(0, 12)}...</code></td>
          <td><span class="badge badge-domain">${s.status}</span></td>
          <td>
            <button class="btn btn-outline btn-sm" onclick="window.TrainingView.deleteSample('${s.sample_id}')" style="color: var(--sev-critical); border-color: var(--sev-critical);">Delete</button>
          </td>
        </tr>
      `).join("");

      // Check cross-sample conflicts
      const varRes = await window.api.templates.sampleVariations(this.activeTemplateId);
      const banner = document.getElementById("sample-conflicts-banner");
      if (varRes && varRes.has_conflicts) {
        banner.style.display = "block";
        banner.innerHTML = `<strong>⚠️ Sample Conflicts Detected:</strong><br/>` + varRes.warnings.map(w => `• ${w}`).join("<br/>");
      } else {
        banner.style.display = "none";
      }
    } catch (err) {
      console.error("Error loading samples:", err);
    }
  },

  async deleteSample(sampleId) {
    if (!this.activeTemplateId) return;
    try {
      await window.api.templates.deleteSample(this.activeTemplateId, sampleId);
      window.toast.info("Sample removed.");
      this.loadSamples();
    } catch (err) {
      window.toast.error(`Failed to delete sample: ${err.message}`);
    }
  },

  async runLearning() {
    if (!this.activeTemplateId) return;
    window.toast.info("Running statistical profile learning across samples...");
    try {
      const res = await window.api.templates.learn(this.activeTemplateId);
      window.toast.success(`Profile learned with ${res.overall_confidence * 100}% overall confidence!`);
      const grid = document.getElementById("learned-cards-grid");
      const container = document.getElementById("learned-profile-results");
      container.style.display = "flex";

      const rules = res.summary_rules || {};
      grid.innerHTML = `
        <div style="padding: 14px; background: var(--bg-surface-sunken); border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
          <div style="font-size: 13px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px;">📏 Layout Rules</div>
          <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.6;">
            • Columns: <strong>${rules.layout?.column_count || 1}</strong> (${rules.layout?.expected_layout})<br/>
            • Page Width: <strong>${rules.layout?.dominant_width || 595} pt</strong><br/>
            • Page Height: <strong>${rules.layout?.dominant_height || 842} pt</strong>
          </div>
        </div>
        <div style="padding: 14px; background: var(--bg-surface-sunken); border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
          <div style="font-size: 13px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px;">🔤 Typography</div>
          <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.6;">
            • Font Family: <strong>${rules.typography?.font_family || "Standard"}</strong><br/>
            • Body Font Size: <strong>${rules.typography?.body_font_size || 10} pt</strong>
          </div>
        </div>
        <div style="padding: 14px; background: var(--bg-surface-sunken); border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
          <div style="font-size: 13px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px;">📑 Structure & Sections</div>
          <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.6;">
            • Numbering: <strong>${rules.structure?.numbering_style || "numeric"}</strong><br/>
            • Required Sections: <strong>${(rules.structure?.required_sections || []).join(", ") || "None"}</strong><br/>
            • Requires TOC: <strong>${rules.structure?.requires_toc ? "Yes" : "No"}</strong>
          </div>
        </div>
      `;
    } catch (err) {
      window.toast.error(`Learning failed: ${err.message}`);
    }
  },

  async loadReview() {
    if (!this.activeTemplateId) return;
    try {
      const summary = await window.api.templates.review(this.activeTemplateId);
      const container = document.getElementById("review-properties-container");
      container.innerHTML = `
        <div style="display: flex; gap: 14px; flex-wrap: wrap;">
          <div style="flex: 1; min-width: 280px; padding: 14px; background: var(--bg-surface-sunken); border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
            <div style="font-size: 13px; font-weight: 700; color: #10b981; margin-bottom: 8px;">✓ Automatically Learned Properties</div>
            <div style="display: flex; flex-direction: column; gap: 8px;">
              ${(summary.learned_properties || []).map(p => `
                <div style="font-size: 12px; display: flex; justify-content: space-between; border-bottom: 1px solid var(--border-subtle); padding-bottom: 4px;">
                  <span><code>${p.property_name}</code>: <strong>${JSON.stringify(p.learned_value)}</strong></span>
                  <span style="color: var(--text-muted);">${Math.round(p.confidence * 100)}% Conf</span>
                </div>
              `).join("") || '<span style="font-size: 12px; color: var(--text-muted);">Run Profile Learning first.</span>'}
            </div>
          </div>
          <div style="flex: 1; min-width: 280px; padding: 14px; background: var(--bg-surface-sunken); border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
            <div style="font-size: 13px; font-weight: 700; color: #f59e0b; margin-bottom: 8px;">⚠️ Uncertain / Conflicting Properties</div>
            <div style="display: flex; flex-direction: column; gap: 8px;">
              ${(summary.uncertain_properties || []).map(p => `
                <div style="font-size: 12px; display: flex; justify-content: space-between; border-bottom: 1px solid var(--border-subtle); padding-bottom: 4px;">
                  <span><code>${p.property_name}</code>: <strong>${JSON.stringify(p.learned_value)}</strong></span>
                  <span style="color: #f59e0b;">${Math.round(p.confidence * 100)}% Conf</span>
                </div>
              `).join("") || '<span style="font-size: 12px; color: #10b981;">No uncertain properties found.</span>'}
            </div>
          </div>
        </div>
      `;
    } catch (err) {
      console.error("Failed loading review:", err);
    }
  },

  async approveProfile() {
    if (!this.activeTemplateId) return;
    try {
      await window.api.templates.approve(this.activeTemplateId, "Quality Engineer");
      window.toast.success("Profile approved! Template can now be activated.");
      this.selectTemplate(this.activeTemplateId);
    } catch (err) {
      window.toast.error(`Approval failed: ${err.message}`);
    }
  },

  async activateTemplate() {
    if (!this.activeTemplateId) return;
    try {
      const res = await window.api.templates.activate(this.activeTemplateId);
      window.toast.success(`Template activated! Available in New Analysis.`);
      this.selectTemplate(this.activeTemplateId);
    } catch (err) {
      window.toast.error(`Activation failed: ${err.message}`);
    }
  },

  async loadAnnotations() {
    if (!this.activeTemplateId) return;
    try {
      const annots = await window.api.templates.listAnnotations(this.activeTemplateId);
      const tbody = document.getElementById("annotations-tbody");
      if (!annots || annots.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 20px;">No annotations recorded.</td></tr>`;
      } else {
        tbody.innerHTML = annots.map(a => `
          <tr>
            <td><code>${a.annotation_id}</code></td>
            <td>${a.sample_id}</td>
            <td>Page ${a.page_number}</td>
            <td><span class="badge badge-domain">${a.label}</span></td>
            <td><code style="font-size: 11px;">[${a.bbox.x0}, ${a.bbox.y0}, ${a.bbox.x1}, ${a.bbox.y1}]</code></td>
            <td><button class="btn btn-outline btn-sm" onclick="window.TrainingView.deleteAnnotation('${a.annotation_id}')">Delete</button></td>
          </tr>
        `).join("");
      }

      const summary = await window.api.templates.datasetSummary(this.activeTemplateId);
      const badge = document.getElementById("annotation-health-badge");
      if (summary.is_sufficient_for_ml) {
        badge.textContent = "✓ READY FOR ML";
        badge.style.background = "rgba(16, 185, 129, 0.15)";
        badge.style.color = "#10b981";
      } else {
        badge.textContent = "STATISTICAL PROFILE RECOMMENDED";
        badge.style.background = "rgba(245, 158, 11, 0.15)";
        badge.style.color = "#f59e0b";
      }
    } catch (err) {
      console.error("Failed loading annotations:", err);
    }
  },

  async deleteAnnotation(annotId) {
    if (!this.activeTemplateId) return;
    try {
      await window.api.templates.deleteAnnotation(this.activeTemplateId, annotId);
      this.loadAnnotations();
    } catch (err) {
      window.toast.error(`Failed to delete annotation: ${err.message}`);
    }
  },

  async trainMLModel() {
    if (!this.activeTemplateId) return;
    window.toast.info("Starting local supervised layout training...");
    try {
      const res = await window.api.templates.trainML(this.activeTemplateId, { epochs: 15 });
      const report = res.report;
      const resBox = document.getElementById("ml-training-results");
      resBox.style.display = "block";
      resBox.innerHTML = `
        <h4 style="margin: 0 0 10px 0; color: #10b981;">✓ Model Trained: ${report.model_id}</h4>
        <div style="font-size: 13px; color: var(--text-secondary); line-height: 1.6;">
          • Validation Accuracy: <strong>${Math.round(report.accuracy * 100)}%</strong><br/>
          • Macro F1 Score: <strong>${report.macro_f1}</strong><br/>
          • Train Partitions: <strong>${report.train_samples} samples</strong> | Validation Partitions: <strong>${report.val_samples} samples</strong>
        </div>
      `;
      window.toast.success("Model trained and registered locally!");
      this.loadModels();
    } catch (err) {
      window.toast.error(`Training error: ${err.message}`);
    }
  },

  async loadVersions() {
    if (!this.activeTemplateId) return;
    try {
      const versions = await window.api.templates.versions(this.activeTemplateId);
      const tbody = document.getElementById("versions-tbody");
      if (!versions || versions.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 20px;">No version snapshots yet.</td></tr>`;
        return;
      }
      tbody.innerHTML = versions.map(v => `
        <tr>
          <td><code style="font-weight: 700;">${v.version_tag}</code></td>
          <td>${new Date(v.created_at).toLocaleString()}</td>
          <td><span class="badge">${v.status}</span></td>
          <td style="color: var(--text-secondary);">${v.note || "Snapshot"}</td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick="window.TrainingView.rollbackVersion('${v.version_tag}')">Restore</button>
          </td>
        </tr>
      `).join("");
    } catch (err) {
      console.error("Failed loading versions:", err);
    }
  },

  async rollbackVersion(versionTag) {
    if (!this.activeTemplateId) return;
    try {
      await window.api.templates.rollback(this.activeTemplateId, versionTag);
      window.toast.success(`Restored version snapshot ${versionTag}.`);
      this.selectTemplate(this.activeTemplateId);
    } catch (err) {
      window.toast.error(`Rollback failed: ${err.message}`);
    }
  },

  async createTemplate() {
    const id = document.getElementById("modal-input-id").value.trim();
    const name = document.getElementById("modal-input-name").value.trim();
    const cat = document.getElementById("modal-input-cat").value.trim();
    const desc = document.getElementById("modal-input-desc").value.trim();

    if (!id || !name) {
      window.toast.error("Template ID and Name are required.");
      return;
    }

    try {
      await window.api.templates.create({
        template_id: id,
        name: name,
        category: cat || "Engineering Specification",
        description: desc
      });
      window.toast.success(`Template '${name}' created successfully.`);
      document.getElementById("modal-create-template").style.display = "none";
      this.activeTemplateId = id;
      await this.loadTemplates();
    } catch (err) {
      window.toast.error(`Creation failed: ${err.message}`);
    }
  },

  async loadModels() {
    try {
      const models = await window.api.models.list();
      const tbody = document.getElementById("models-tbody");
      if (!tbody) return;

      if (!models || models.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 32px;">
              No models currently registered in model_registry.json. Local deterministic rule fallbacks active.
            </td>
          </tr>
        `;
        return;
      }

      tbody.innerHTML = models.map((m) => {
        const isActive = m.is_active;
        return `
          <tr>
            <td><strong style="font-family: var(--font-mono); font-size: 12px;">${m.model_id}</strong></td>
            <td><span style="font-weight: 600;">${m.task || "NLP / NER"}</span></td>
            <td><span class="badge badge-domain">${m.domain || "General"}</span></td>
            <td style="font-family: var(--font-mono); font-size: 12px;">v${m.version || "1.0"}</td>
            <td>
              <span class="badge" style="background: ${isActive ? "rgba(16, 185, 129, 0.15)" : "var(--bg-surface-sunken)"}; color: ${isActive ? "#059669" : "var(--text-muted)"};">
                ${isActive ? "● ACTIVE" : "○ STANDBY"}
              </span>
            </td>
            <td>
              <code style="font-size: 11px; color: var(--text-muted);">${(m.sha256_hash || "").substring(0, 16)}...</code>
            </td>
            <td>
              <div style="display: flex; gap: 6px;">
                <button class="btn btn-secondary btn-sm" onclick="window.TrainingView.verifyHash('${m.model_id}')">
                  Verify SHA-256
                </button>
                <button class="btn ${isActive ? "btn-outline" : "btn-primary"} btn-sm" onclick="window.TrainingView.toggleActive('${m.model_id}', ${isActive})">
                  ${isActive ? "Deactivate" : "Activate"}
                </button>
              </div>
            </td>
          </tr>
        `;
      }).join("");
    } catch (err) {
      console.error("Error loading models:", err);
    }
  },

  async toggleActive(modelId, currentActive) {
    try {
      if (currentActive) {
        await window.api.models.deactivate(modelId);
        window.toast.info(`Model ${modelId} deactivated.`);
      } else {
        await window.api.models.activate(modelId);
        window.toast.success(`Model ${modelId} activated.`);
      }
      this.loadModels();
    } catch (err) {
      window.toast.error(`Operation failed: ${err.message}`);
    }
  },

  async verifyHash(modelId) {
    try {
      window.toast.info(`Computing SHA-256 for ${modelId}...`);
      const res = await window.api.models.verifyHash(modelId);
      if (res.is_valid) {
        window.toast.success(`Cryptographic hash verified! Match: ${res.computed_hash.substring(0, 16)}...`);
      } else {
        window.toast.error(`Hash mismatch or missing file! Details: ${res.error || "Corrupted"}`);
      }
    } catch (err) {
      window.toast.error(`Verification error: ${err.message}`);
    }
  }
};
