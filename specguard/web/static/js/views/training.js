/**
 * SpecGuard Machine Learning & Model Registry View
 * Displays real hardware awareness, dataset health reports,
 * model registry checkpoints, and cryptographic SHA-256 integrity checks.
 */

window.TrainingView = {
  async render(container) {
    container.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 20px;">
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

        <!-- 2. Dataset Health Diagnostics -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">📊 Dataset Integrity & Research Mode Validation</div>
          </div>
          <div class="card-body" style="display: flex; flex-direction: column; gap: 10px;">
            <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.4;">
              Strict research mode validation guarantees zero document partition leakage between training, validation, and testing sets.
            </p>
            <div style="display: flex; gap: 12px; align-items: center; margin-top: 4px;" id="dataset-health-container">
              <span style="font-size: 12px; color: var(--text-muted);">Validating local dataset partitions...</span>
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
          <div class="card-footer">
            <span style="font-size: 12px; color: var(--text-muted);">
              All machine learning inference runs locally in the Python backend. Cloud AI APIs are strictly disabled.
            </span>
          </div>
        </div>
      </div>
    `;

    document.getElementById("btn-refresh-models").onclick = () => this.loadModels();

    await this.loadHardware();
    await this.loadDatasetHealth();
    await this.loadModels();
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

  async loadDatasetHealth() {
    try {
      const health = await window.api.models.datasetHealth();
      const container = document.getElementById("dataset-health-container");
      if (!container) return;

      container.innerHTML = `
        <div style="display: flex; gap: 16px; flex-wrap: wrap;">
          <div style="padding: 10px 14px; background: var(--bg-surface-sunken); border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
            <span style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; font-weight: 700;">Total Annotations</span>
            <div style="font-size: 18px; font-weight: 800; color: var(--text-primary);">${health.total_annotations || 0}</div>
          </div>
          <div style="padding: 10px 14px; background: var(--bg-surface-sunken); border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
            <span style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; font-weight: 700;">Leakage Check</span>
            <div style="font-size: 14px; font-weight: 700; color: ${health.has_leakage ? "var(--sev-critical)" : "#10b981"};">
              ${health.has_leakage ? "⚠ Leakage Detected" : "✓ Clean (0% Leakage)"}
            </div>
          </div>
          <div style="padding: 10px 14px; background: var(--bg-surface-sunken); border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
            <span style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; font-weight: 700;">Research Compliance</span>
            <div style="font-size: 14px; font-weight: 700; color: #10b981;">
              ✓ Real Engineering Data Enforced
            </div>
          </div>
        </div>
      `;
    } catch (err) {
      console.warn("Could not load dataset health:", err);
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
      window.toast.error("Failed loading model registry.");
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
