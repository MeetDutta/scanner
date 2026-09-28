/**
 * SpecGuard Reactive State Store & Event Bus
 * Manages local application state without external state management libraries.
 * Persistent rehydration source of truth: Backend / SQLite database.
 */

class AppState {
  constructor() {
    this.state = {
      theme: localStorage.getItem("specguard-theme") || "dark",
      currentView: "dashboard",
      activeDocument: null,
      activeDomain: null,
      activeSessionId: localStorage.getItem("specguard-active-session") || null,
      activeFindings: null,
      activeJobId: null,
      activePage: 1,
      totalPages: null,
      focusedFinding: null,
      stats: null,
      analysisStatus: "NO_ANALYSIS" // NO_ANALYSIS, ANALYZING, ANALYSIS_COMPLETE, ANALYSIS_FAILED
    };

    this.listeners = new Map();
    this._rehydratePromise = null;
  }

  get(key) {
    return this.state[key];
  }

  set(key, value) {
    const oldValue = this.state[key];
    this.state[key] = value;
    if (key === "activeSessionId") {
      if (value) {
        localStorage.setItem("specguard-active-session", value);
      } else {
        localStorage.removeItem("specguard-active-session");
      }
    }
    this.emit(key, { newValue: value, oldValue });
    this.emit("change", { key, newValue: value, oldValue });
  }

  update(updates) {
    Object.entries(updates).forEach(([k, v]) => this.set(k, v));
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event).add(callback);
    return () => this.listeners.get(event).delete(callback);
  }

  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach((cb) => {
        try {
          cb(data);
        } catch (err) {
          console.error(`Error in state listener for '${event}':`, err);
        }
      });
    }
  }

  /**
   * Deterministic session rehydration from persistent backend.
   * Ensures browser refresh, direct URL navigation, and tab reopening reconstruct
   * identical state without relying purely on frontend in-memory variables.
   * Explicitly transitions between: LOADING, DATA_AVAILABLE, NO_ANALYSIS,
   * ANALYSIS_COMPLETE_ZERO_FINDINGS, ANALYSIS_FAILED, DATA_LOAD_FAILED.
   */
  async rehydrateSession(requestedSessionId = null) {
    this.set("analysisStatus", "LOADING");

    // 1. Resolve session ID by priority:
    // a. Explicitly passed parameter
    // b. URL parameter (hash or search)
    // c. Current activeSessionId in state
    // d. localStorage persisted session ID
    // e. Latest session from database
    let targetId = requestedSessionId;
    if (!targetId && window.router && typeof window.router.getParams === "function") {
      const p = window.router.getParams();
      targetId = p.session_id || p.sessionId;
    }
    if (!targetId) {
      const searchParams = new URLSearchParams(window.location.search);
      targetId = searchParams.get("session_id") || searchParams.get("sessionId");
    }
    if (!targetId && window.location.hash.includes("?")) {
      const q = window.location.hash.split("?")[1];
      const hashParams = new URLSearchParams(q);
      targetId = hashParams.get("session_id") || hashParams.get("sessionId");
    }
    if (!targetId) {
      targetId = this.get("activeSessionId");
    }
    if (!targetId) {
      targetId = localStorage.getItem("specguard-active-session");
    }

    // If still no session ID, attempt to fetch the latest session from database
    if (!targetId) {
      try {
        const recentRes = await window.api.dashboard.getRecent(1);
        if (recentRes && recentRes.recent_comparisons && recentRes.recent_comparisons.length > 0) {
          targetId = recentRes.recent_comparisons[0].comparison_id;
        }
      } catch (err) {
        console.warn("Could not check recent comparisons from database:", err);
      }
    }

    if (!targetId) {
      this.set("activeSessionId", null);
      this.set("activeDocument", null);
      this.set("activeFindings", null);
      this.set("analysisStatus", "NO_ANALYSIS");
      return null;
    }

    // 2. Query persistent session from backend
    try {
      const sessionData = await window.api.analysis.getSession(targetId);
      if (sessionData) {
        const sid = sessionData.comparison_id || sessionData.session_id || targetId;
        this.set("activeSessionId", sid);

        const doc = {
          filename: sessionData.document_filename || (sessionData.document && sessionData.document.filename) || "Engineering Document",
          file_hash: sessionData.document_sha256 || (sessionData.document && sessionData.document.file_hash),
          page_count: sessionData.page_count || (sessionData.document && sessionData.document.page_count) || 1,
          document_id: sessionData.document_id,
          revision: sessionData.revision,
          inspection_profile: sessionData.inspection_profile
        };
        this.set("activeDocument", doc);

        if (sessionData.domain) {
          this.set("activeDomain", sessionData.domain);
        }

        let findings = sessionData.findings;
        if (!Array.isArray(findings)) {
          const fRes = await window.api.findings.list({ session_id: sid, limit: 500 });
          findings = fRes.findings;
        }

        if (!Array.isArray(findings)) {
          throw new Error(`Invalid findings payload received for session ${sid}`);
        }

        this.set("activeFindings", findings);

        // Determine explicit state:
        const isComplete = (sessionData.status || "").toUpperCase() === "COMPLETED";
        const hasZeroFindings = (sessionData.total_findings === 0 || sessionData.findings_count === 0) && findings.length === 0;

        if (isComplete && hasZeroFindings) {
          this.set("analysisStatus", "ANALYSIS_COMPLETE_ZERO_FINDINGS");
        } else if (findings.length > 0) {
          this.set("analysisStatus", "DATA_AVAILABLE");
        } else {
          this.set("analysisStatus", "DATA_AVAILABLE");
        }

        // Sync URL query parameter without triggering full reload
        if (window.router && typeof window.router.syncUrlSession === "function") {
          window.router.syncUrlSession(sid);
        }

        return sessionData;
      }
    } catch (err) {
      console.warn(`Direct session API fetch failed for ${targetId}, falling back to history:`, err);
      try {
        const hist = await window.api.history.get(targetId);
        if (hist) {
          const sid = hist.comparison_id || targetId;
          this.set("activeSessionId", sid);
          const doc = {
            filename: hist.document_filename,
            file_hash: hist.document_sha256,
            page_count: hist.page_count || 1
          };
          this.set("activeDocument", doc);
          if (hist.domain) this.set("activeDomain", hist.domain);

          const fRes = await window.api.findings.list({ session_id: sid, limit: 500 });
          const findings = fRes.findings;
          if (!Array.isArray(findings)) {
            throw new Error(`Invalid findings payload in history for session ${sid}`);
          }
          this.set("activeFindings", findings);

          const hasZero = (hist.total_findings === 0) && findings.length === 0;
          if (hasZero) {
            this.set("analysisStatus", "ANALYSIS_COMPLETE_ZERO_FINDINGS");
          } else {
            this.set("analysisStatus", "DATA_AVAILABLE");
          }

          if (window.router && typeof window.router.syncUrlSession === "function") {
            window.router.syncUrlSession(sid);
          }
          return { ...hist, findings };
        }
      } catch (histErr) {
        console.error(`Session ${targetId} not found in database:`, histErr);
        // CRITICAL: Clear stale local state and localStorage so we do NOT show fake 0-finding dashboards
        this.set("activeSessionId", null);
        this.set("activeDocument", null);
        this.set("activeFindings", null);
        this.set("analysisStatus", "DATA_LOAD_FAILED");
        localStorage.removeItem("specguard-active-session");
        throw new Error(`Unable to load analysis session '${targetId}'. Backend returned: ${err.message || histErr.message}`);
      }
    }

    this.set("activeSessionId", null);
    this.set("activeDocument", null);
    this.set("activeFindings", null);
    this.set("analysisStatus", "DATA_LOAD_FAILED");
    localStorage.removeItem("specguard-active-session");
    throw new Error(`Unable to load analysis session '${targetId}'. Record not found.`);
  }
}

window.appState = new AppState();
