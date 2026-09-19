/**
 * SpecGuard Analysis Workspace View
 * Live stage-based progress reporting, duration timer, and real log streaming.
 */

window.WorkspaceView = {
  pollInterval: null,
  eventSource: null,

  stagesList: [
    { name: "Acquiring and stream parsing document pages...", threshold: 10 },
    { name: "Reconstructing geometric reading order & layout...", threshold: 22 },
    { name: "Analyzing structural outline & section hierarchy...", threshold: 28 },
    { name: "Cross-checking Table of Contents & page drift...", threshold: 35 },
    { name: "Inspecting tables & multi-page split continuity...", threshold: 42 },
    { name: "Validating figures, drawings & caption placement...", threshold: 50 },
    { name: "Inspecting mathematical equations & labels...", threshold: 56 },
    { name: "Resolving document-wide citation & cross-reference graph...", threshold: 64 },
    { name: "Evaluating grammar, syntax & technical vocabulary...", threshold: 70 },
    { name: "Extracting engineering parameters & propositions...", threshold: 76 },
    { name: "Validating domain & IEEE compliance rules...", threshold: 84 },
    { name: "Detecting semantic propositions & contradictions...", threshold: 88 },
    { name: "Evaluating local engineering standards...", threshold: 93 },
    { name: "Computing severity scores & evidence ranking...", threshold: 98 },
    { name: "Analysis complete.", threshold: 100 }
  ],

  async render(container) {
    const jobId = window.appState.get("activeJobId");
    const activeDoc = window.appState.get("activeDocument");
    const activeDomain = window.appState.get("activeDomain") || "mechanical";

    if (!jobId) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">⚡</div>
          <div class="empty-state-title">No Active Verification Job</div>
          <div class="empty-state-desc">Select a document and domain to start a new verification pipeline.</div>
          <button class="btn btn-primary" onclick="window.router.navigate('new_analysis')">Start Analysis</button>
        </div>
      `;
      return;
    }

    container.innerHTML = `
      <div class="workspace-container">
        <!-- Header Info Bar -->
        <div class="workspace-header-bar">
          <div style="display: flex; align-items: center; gap: 14px;">
            <div class="status-indicator-pill">
              <span class="status-dot"></span>
              <span id="ws-status-text">RUNNING</span>
            </div>
            <div>
              <div style="font-weight: 800; font-size: 15px; color: var(--text-primary);" id="ws-doc-name">
                ${activeDoc ? activeDoc.filename : "Engineering Specification"}
              </div>
              <div style="font-size: 12px; color: var(--text-muted);">
                Domain: <strong style="text-transform: capitalize; color: var(--accent-primary);">${activeDomain}</strong>
                • Job: <code style="font-size: 11px;">${jobId}</code>
              </div>
            </div>
          </div>
          <button class="btn btn-danger btn-sm" id="btn-cancel-job">Cancel</button>
        </div>

        <!-- Stage Progression Card -->
        <div class="stage-tracker-card">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 13px; font-weight: 700; color: var(--text-secondary);" id="ws-stage-label">
              Initializing analysis engines...
            </span>
            <span style="font-size: 18px; font-weight: 800; color: var(--accent-primary);" id="ws-pct-label">
              0%
            </span>
          </div>

          <!-- Master Progress Bar -->
          <div class="progress-bar-container">
            <div class="progress-bar-fill" id="ws-progress-fill" style="width: 5%;"></div>
          </div>

          <!-- Detailed Stages List -->
          <div class="stage-list" id="ws-stage-list">
            ${this.stagesList.map((s, idx) => `
              <div class="stage-item pending" id="ws-stage-${idx}">
                <span class="stage-icon">○</span>
                <span style="flex: 1;">${s.name}</span>
                <span style="font-size: 11px; font-family: var(--font-mono); color: var(--text-muted);">${s.threshold}%</span>
              </div>
            `).join("")}
          </div>
        </div>

        <!-- Live Diagnostics & Logs -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">📜 Pipeline Activity Log</div>
          </div>
          <div class="card-body">
            <div class="live-log-box" id="ws-log-box">
              <div>[0.00s] Initializing SpecGuard offline analysis coordinator...</div>
            </div>
          </div>
        </div>
      </div>
    `;

    document.getElementById("btn-cancel-job").onclick = () => this.cancelJob(jobId);
    this.startTracking(jobId);
  },

  startTracking(jobId) {
    this.stopTracking();

    const updateUI = (job) => {
      if (!job) return;

      const pct = job.percent || 0;
      const stage = job.stage || "Processing...";
      const status = (job.status || "running").toUpperCase();

      const pctEl = document.getElementById("ws-pct-label");
      const stageEl = document.getElementById("ws-stage-label");
      const fillEl = document.getElementById("ws-progress-fill");
      const statusText = document.getElementById("ws-status-text");

      if (pctEl) pctEl.textContent = `${pct}%`;
      if (stageEl) stageEl.textContent = stage;
      if (fillEl) fillEl.style.width = `${Math.max(5, pct)}%`;
      if (statusText) statusText.textContent = status;

      // Update stage indicators
      this.stagesList.forEach((s, idx) => {
        const item = document.getElementById(`ws-stage-${idx}`);
        if (!item) return;

        if (pct >= s.threshold) {
          item.className = "stage-item completed";
          item.querySelector(".stage-icon").textContent = "✓";
        } else if (pct >= (idx > 0 ? this.stagesList[idx - 1].threshold : 0)) {
          item.className = "stage-item running";
          item.querySelector(".stage-icon").textContent = "▶";
        } else {
          item.className = "stage-item pending";
          item.querySelector(".stage-icon").textContent = "○";
        }
      });

      // Update activity logs
      const logBox = document.getElementById("ws-log-box");
      if (logBox && job.stages_log) {
        logBox.innerHTML = job.stages_log.map((entry) => `
          <div>[${entry.time}s] [${entry.percent}%] ${entry.stage}</div>
        `).join("");
        logBox.scrollTop = logBox.scrollHeight;
      }

      // Check for completion
      if (job.status === "completed") {
        this.stopTracking();
        window.toast.success(`Verification completed! Recorded ${job.total_findings || 0} findings.`);

        setTimeout(async () => {
          if (job.session_id) {
            window.appState.set("activeSessionId", job.session_id);
            // Fetch findings for session
            const res = await window.api.findings.list({ session_id: job.session_id, limit: 200 });
            window.appState.set("activeFindings", res.findings || []);
          }
          window.router.navigate("results");
        }, 800);
      } else if (job.status === "failed") {
        this.stopTracking();
        window.toast.error(`Analysis failed: ${job.error || "Unknown error"}`);
        if (statusText) {
          statusText.textContent = "FAILED";
          statusText.style.color = "var(--sev-critical)";
        }
      }
    };

    // Polling fallback every 350ms
    this.pollInterval = setInterval(async () => {
      try {
        const job = await window.api.analysis.getJob(jobId);
        updateUI(job);
      } catch (err) {
        console.error("Polling job error:", err);
      }
    }, 350);
  },

  stopTracking() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  },

  async cancelJob(jobId) {
    window.modal.confirm({
      title: "Cancel Verification",
      message: "Are you sure you want to stop the ongoing document analysis?",
      confirmLabel: "Yes, Cancel",
      isDanger: true,
      onConfirm: async () => {
        try {
          await window.api.analysis.cancel(jobId);
          this.stopTracking();
          window.toast.warning("Analysis cancelled.");
          window.router.navigate("dashboard");
        } catch (err) {
          window.toast.error(`Cancel failed: ${err.message}`);
        }
      }
    });
  }
};
