/**
 * SpecGuard New Analysis View
 * Document upload, domain selection, standards configuration, and pipeline trigger.
 */

window.NewAnalysisView = {
  selectedFile: null,
  selectedDomain: "mechanical",
  selectedProfile: "mechanical",
  demoSamples: [],

  async render(container) {
    this.selectedFile = null;
    this.selectedDomain = window.appState.get("activeDomain") || "mechanical";
    this.selectedProfile = window.appState.get("activeProfile") || this.selectedDomain;

    container.innerHTML = `
      <div class="new-analysis-container">
        <!-- Step Indicator Header -->
        <div class="stepper">
          <div class="step-item active" id="step-doc-item">
            <span class="step-num">1</span>
            <span>Document Ingestion</span>
          </div>
          <div class="step-item" id="step-domain-item">
            <span class="step-num">2</span>
            <span>Domain & Standards</span>
          </div>
          <div class="step-item" id="step-run-item">
            <span class="step-num">3</span>
            <span>Verification Pipeline</span>
          </div>
        </div>

        <!-- 1. Document Upload / Selection Card -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">📄 Step 1: Select Engineering Specification Document</div>
          </div>
          <div class="card-body" style="display: flex; flex-direction: column; gap: 16px;">
            <!-- Dropzone -->
            <div class="dropzone" id="analysis-dropzone">
              <div class="dropzone-icon">📥</div>
              <div class="dropzone-prompt">Drag and drop engineering document here</div>
              <div class="dropzone-sub">Supports PDF, DOCX, XLSX, TXT, and Drawings (PNG, JPG, TIFF) • Max 100 MB</div>
              <button class="btn btn-secondary btn-sm" id="btn-browse-file" style="margin-top: 6px;">
                Browse Files
              </button>
              <input type="file" id="file-input-hidden" style="display: none;" accept=".pdf,.docx,.xlsx,.xls,.txt,.png,.jpg,.jpeg,.tiff,.tif" />
            </div>

            <!-- Selected Document Display (Hidden until selected) -->
            <div class="selected-file-pill" id="selected-file-display" style="display: none;">
              <div style="display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 24px;">📄</span>
                <div>
                  <div style="font-weight: 700; color: var(--text-primary);" id="sel-doc-name">document.pdf</div>
                  <div style="font-size: 11.5px; color: var(--text-muted);" id="sel-doc-meta">PDF • 2 Pages • 24.5 KB</div>
                </div>
              </div>
              <button class="btn btn-outline btn-sm" id="btn-remove-selected-file">✕ Remove</button>
            </div>

            <!-- Quick Demo Samples Selector -->
            <div style="border-top: 1px solid var(--border-subtle); padding-top: 12px;">
              <span style="font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">
                Or select a local verified demo sample:
              </span>
              <div id="demo-samples-container" style="display: flex; gap: 10px; flex-wrap: wrap; margin-top: 8px;">
                <span style="font-size: 12px; color: var(--text-muted);">Loading sample documents...</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 2. Domain Selection Card -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">⚙️ Step 2: Select Engineering Domain & Ruleset</div>
          </div>
          <div class="card-body" style="display: flex; flex-direction: column; gap: 16px;">
            <div class="domain-selection-grid" id="domain-cards-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px;">
              <!-- Mechanical -->
              <div class="domain-card ${this.selectedProfile === "mechanical" ? "selected" : ""}" data-domain="mechanical" data-profile="mechanical">
                <span class="domain-card-badge">${this.selectedProfile === "mechanical" ? "✓ SELECTED" : "SELECT"}</span>
                <div class="domain-icon">⚙️</div>
                <div class="domain-name">Mechanical</div>
                <span class="domain-standard-tag">ASME Y14 / GD&T</span>
                <p class="domain-desc">Tolerances, material specifications, pumps, pressure vessels, CAD layout drawing standards.</p>
              </div>

              <!-- Electrical -->
              <div class="domain-card ${this.selectedProfile === "electrical" ? "selected" : ""}" data-domain="electrical" data-profile="electrical">
                <span class="domain-card-badge">${this.selectedProfile === "electrical" ? "✓ SELECTED" : "SELECT"}</span>
                <div class="domain-icon">⚡</div>
                <div class="domain-name">Electrical</div>
                <span class="domain-standard-tag">IEC 60364 / Schematics</span>
                <p class="domain-desc">Wiring schematics, circuit protection, voltage drops, power distributions, cable sizing.</p>
              </div>

              <!-- Chemical -->
              <div class="domain-card ${this.selectedProfile === "chemical" ? "selected" : ""}" data-domain="chemical" data-profile="chemical">
                <span class="domain-card-badge">${this.selectedProfile === "chemical" ? "✓ SELECTED" : "SELECT"}</span>
                <div class="domain-icon">🧪</div>
                <div class="domain-name">Chemical</div>
                <span class="domain-standard-tag">Process Safety / P&ID</span>
                <p class="domain-desc">Flow diagrams, piping specifications, hazardous materials, instrumentation, valve tags.</p>
              </div>

              <!-- IEEE Research Paper -->
              <div class="domain-card ${this.selectedProfile === "ieee_research" ? "selected" : ""}" data-domain="academic" data-profile="ieee_research">
                <span class="domain-card-badge">${this.selectedProfile === "ieee_research" ? "✓ SELECTED" : "SELECT"}</span>
                <div class="domain-icon">📑</div>
                <div class="domain-name">IEEE Paper</div>
                <span class="domain-standard-tag">IEEE Journal & Conf</span>
                <p class="domain-desc">Two-column grid, Roman headings, abstract & keywords, bracket citations [1], Fig/Table rules.</p>
              </div>

              <!-- Generic Academic -->
              <div class="domain-card ${this.selectedProfile === "generic_academic" ? "selected" : ""}" data-domain="academic" data-profile="generic_academic">
                <span class="domain-card-badge">${this.selectedProfile === "generic_academic" ? "✓ SELECTED" : "SELECT"}</span>
                <div class="domain-icon">🎓</div>
                <div class="domain-name">Academic</div>
                <span class="domain-standard-tag">Theses & Reports</span>
                <p class="domain-desc">Multi-page structure, abstract, methodology, equations, cross-reference integrity graph.</p>
              </div>
            </div>

            <!-- Analysis Scope Options -->
            <div style="background-color: var(--bg-surface-sunken); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 14px;">
              <span style="font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">
                Verification Engines Enabled (All 14 Intelligence Engines Active)
              </span>
              <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 8px; margin-top: 8px; font-size: 12px; color: var(--text-secondary);">
                <span>✓ Reading Order Engine</span>
                <span>✓ Structural Hierarchy</span>
                <span>✓ TOC Cross-Validation</span>
                <span>✓ Tables & Multi-Page Split</span>
                <span>✓ Figures & Vector Diagrams</span>
                <span>✓ Mathematical Equations</span>
                <span>✓ Citation & Cross-Ref Graph</span>
                <span>✓ IEEE Compliance Mode</span>
                <span>✓ Technical Grammar</span>
                <span>✓ Parameter Extraction</span>
                <span>✓ Logical Contradictions</span>
                <span>✓ Local Standards KB</span>
                <span>✓ Severity Prioritization</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 3. Launch Action Bar -->
        <div style="display: flex; justify-content: flex-end; gap: 12px; margin-bottom: 24px;">
          <button class="btn btn-secondary" onclick="window.router.navigate('dashboard')">Cancel</button>
          <button class="btn btn-primary" id="btn-start-analysis" style="padding: 10px 24px; font-size: 14px;" disabled>
            🚀 Start Engineering Verification
          </button>
        </div>
      </div>
    `;

    this._bindEvents();
    await this.loadDemoSamples();
    await this.loadCustomProfiles();
  },

  _bindEvents() {
    const dropzone = document.getElementById("analysis-dropzone");
    const fileInput = document.getElementById("file-input-hidden");
    const browseBtn = document.getElementById("btn-browse-file");
    const removeBtn = document.getElementById("btn-remove-selected-file");
    const startBtn = document.getElementById("btn-start-analysis");

    browseBtn.onclick = () => fileInput.click();
    fileInput.onchange = (e) => {
      if (e.target.files && e.target.files[0]) {
        this.handleFileUpload(e.target.files[0]);
      }
    };

    dropzone.ondragover = (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    };
    dropzone.ondragleave = () => dropzone.classList.remove("dragover");
    dropzone.ondrop = (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        this.handleFileUpload(e.dataTransfer.files[0]);
      }
    };

    removeBtn.onclick = () => {
      this.selectedFile = null;
      document.getElementById("selected-file-display").style.display = "none";
      dropzone.style.display = "flex";
      startBtn.disabled = true;
    };

    // Domain selection cards
    document.querySelectorAll(".domain-card").forEach((card) => {
      card.onclick = () => {
        document.querySelectorAll(".domain-card").forEach((c) => {
          c.classList.remove("selected");
          c.querySelector(".domain-card-badge").textContent = "SELECT";
        });
        card.classList.add("selected");
        card.querySelector(".domain-card-badge").textContent = "✓ SELECTED";
        this.selectedDomain = card.getAttribute("data-domain");
        this.selectedProfile = card.getAttribute("data-profile") || this.selectedDomain;
        window.appState.set("activeDomain", this.selectedDomain);
        window.appState.set("activeProfile", this.selectedProfile);
      };
    });

    startBtn.onclick = () => this.startAnalysis();
  },

  async handleFileUpload(file) {
    try {
      window.toast.info(`Uploading & inspecting ${file.name}...`);
      const uploadRes = await window.api.analysis.upload(file);
      this.setDocument(uploadRes);
      window.toast.success(`Document loaded: ${uploadRes.filename}`);
    } catch (err) {
      window.toast.error(`Upload error: ${err.message}`);
    }
  },

  setDocument(docData) {
    this.selectedFile = docData;
    document.getElementById("sel-doc-name").textContent = docData.filename;
    document.getElementById("sel-doc-meta").textContent =
      `${docData.file_type} • ${docData.page_count} Pages • ${(docData.file_size / 1024).toFixed(1)} KB`;

    document.getElementById("analysis-dropzone").style.display = "none";
    document.getElementById("selected-file-display").style.display = "flex";
    document.getElementById("btn-start-analysis").disabled = false;
  },

  async loadDemoSamples() {
    try {
      const samples = await window.api.analysis.getSamples();
      this.demoSamples = samples;
      const container = document.getElementById("demo-samples-container");
      if (!container) return;

      if (samples.length === 0) {
        container.innerHTML = `<span style="font-size: 12px; color: var(--text-muted);">No demo files in demo_samples/</span>`;
        return;
      }

      container.innerHTML = samples.map((s, idx) => `
        <button class="btn btn-secondary btn-sm" id="btn-sample-${idx}" style="font-size: 11.5px;">
          ${s.domain === "mechanical" ? "⚙️" : s.domain === "electrical" ? "⚡" : s.domain === "academic" ? "📑" : "🧪"}
          ${s.filename}
        </button>
      `).join("");

      samples.forEach((s, idx) => {
        document.getElementById(`btn-sample-${idx}`).onclick = () => {
          this.setDocument({
            filename: s.filename,
            file_path: s.file_path,
            file_size: s.file_size,
            file_type: s.file_type,
            page_count: 2
          });

          // Auto-select domain matching sample
          if (s.domain) {
            const card = document.querySelector(`.domain-card[data-domain="${s.domain}"]`);
            if (card) card.click();
          }
        };
      });
    } catch (err) {
      console.warn("Could not load demo samples:", err);
    }
  },

  async startAnalysis() {
    if (!this.selectedFile) return;

    try {
      const startBtn = document.getElementById("btn-start-analysis");
      startBtn.disabled = true;
      startBtn.textContent = "Launching Pipeline...";

      const res = await window.api.analysis.start({
        file_path: this.selectedFile.file_path,
        domain: this.selectedDomain,
        profile: this.selectedProfile,
        selected_standards: []
      });

      window.appState.set("activeJobId", res.job_id);
      window.appState.set("activeDocument", this.selectedFile);
      window.appState.set("activeDomain", this.selectedDomain);

      window.toast.info("Analysis pipeline launched.");
      window.router.navigate("workspace");
    } catch (err) {
      window.toast.error(`Failed starting analysis: ${err.message}`);
      const startBtn = document.getElementById("btn-start-analysis");
      if (startBtn) {
        startBtn.disabled = false;
        startBtn.textContent = "🚀 Start Engineering Verification";
      }
    }
  },

  async loadCustomProfiles() {
    try {
      const activeTemplates = await window.api.templates.list("ACTIVE");
      const grid = document.getElementById("domain-cards-grid");
      if (!grid || !activeTemplates || activeTemplates.length === 0) return;

      activeTemplates.forEach((t) => {
        const card = document.createElement("div");
        card.className = `domain-card ${this.selectedProfile === t.template_id ? "selected" : ""}`;
        card.setAttribute("data-domain", "custom");
        card.setAttribute("data-profile", t.template_id);
        card.innerHTML = `
          <span class="domain-card-badge">${this.selectedProfile === t.template_id ? "✓ SELECTED" : "SELECT"}</span>
          <div class="domain-icon">📐</div>
          <div class="domain-name">${t.name}</div>
          <span class="domain-standard-tag">${t.category || "Custom Specification"}</span>
          <p class="domain-desc">${t.description || "Custom learned document template."}</p>
        `;
        card.onclick = () => {
          document.querySelectorAll(".domain-card").forEach((c) => {
            c.classList.remove("selected");
            c.querySelector(".domain-card-badge").textContent = "SELECT";
          });
          card.classList.add("selected");
          card.querySelector(".domain-card-badge").textContent = "✓ SELECTED";
          this.selectedDomain = "custom";
          this.selectedProfile = t.template_id;
          window.appState.set("activeDomain", this.selectedDomain);
          window.appState.set("activeProfile", this.selectedProfile);
        };
        grid.appendChild(card);
      });
    } catch (err) {
      console.warn("Could not load custom profiles in New Analysis:", err);
    }
  }
};
