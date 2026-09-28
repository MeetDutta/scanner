/**
 * SpecGuard Single-Page Application Router
 * Manages hash-based routing with canonical query parameter preservation,
 * active view lifecycle, breadcrumbs navigation, and persistent route rehydration.
 */

class Router {
  constructor() {
    this.routes = {
      dashboard: { title: "Quality Dashboard", view: window.DashboardView },
      new_analysis: { title: "New Document Analysis", view: window.NewAnalysisView },
      progress: { title: "Analysis Progress", view: window.AnalysisProgressView },
      workspace: { title: "Analysis Progress", view: window.AnalysisProgressView },
      results: { title: "Analysis Results", view: window.ResultsView },
      findings: { title: "Document Findings", view: window.FindingsView },
      overview: { title: "Document Overview & Structure", view: window.DocumentInspectionView },
      viewer: { title: "Page Inspection", view: window.ViewerView },
      formatting: { title: "Formatting Issues", view: window.FormattingView },
      structural: { title: "Structural Issues", view: window.StructuralIssuesView },
      content: { title: "Content & Engineering Issues", view: window.ContentIssuesView },
      reports: { title: "Inspection Reports", view: window.ReportsView },
      history: { title: "Analysis History", view: window.HistoryView },
      standards: { title: "Standards & Rules", view: window.StandardsView },
      settings: { title: "Settings & Health", view: window.SettingsView }
    };

    this.RESULT_DEPENDENT_ROUTES = [
      "dashboard",
      "overview",
      "viewer",
      "findings",
      "reports",
      "results"
    ];

    this.container = null;
    this.currentRoute = null;
    this.params = {};

    window.addEventListener("hashchange", () => this._handleHashChange());
  }

  init(containerId) {
    this.container = document.getElementById(containerId);
    const initialRaw = window.location.hash || "dashboard";
    this.navigate(initialRaw);
  }

  getParams() {
    return { ...this.params };
  }

  _parseRoute(raw) {
    if (!raw) return { routeName: "dashboard", params: {} };
    let cleaned = raw.replace(/^#/, "").replace(/^\/+/, "");
    let routeName = cleaned;
    const params = {};

    // 1. Parse query params from hash if present (e.g. overview?session_id=CMP-123)
    if (cleaned.includes("?")) {
      const parts = cleaned.split("?");
      routeName = parts[0];
      const qs = parts.slice(1).join("?");
      new URLSearchParams(qs).forEach((v, k) => {
        params[k] = v;
      });
    }

    // 2. Also incorporate window.location.search parameters
    if (window.location.search) {
      new URLSearchParams(window.location.search).forEach((v, k) => {
        if (!params[k]) params[k] = v;
      });
    }

    // Default to dashboard if route name is empty
    if (!routeName) routeName = "dashboard";

    return { routeName, params };
  }

  navigate(routeName, extraParams = {}) {
    const { routeName: targetRoute, params: parsedParams } = this._parseRoute(routeName);
    const mergedParams = { ...parsedParams, ...extraParams };

    if (!this.routes[targetRoute]) {
      console.warn(`Route '${targetRoute}' not found, falling back to dashboard.`);
      this.navigate("dashboard", extraParams);
      return;
    }

    // If target route depends on an active session, preserve session_id
    if (this.RESULT_DEPENDENT_ROUTES.includes(targetRoute)) {
      if (!mergedParams.session_id) {
        const activeSid = (window.appState && window.appState.get("activeSessionId")) ||
                          localStorage.getItem("specguard-active-session");
        if (activeSid) {
          mergedParams.session_id = activeSid;
        }
      }
    }

    const qs = new URLSearchParams();
    Object.entries(mergedParams).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") {
        qs.append(k, v);
      }
    });

    const targetHash = qs.toString() ? `#${targetRoute}?${qs.toString()}` : `#${targetRoute}`;

    if (window.location.hash !== targetHash) {
      window.location.hash = targetHash;
      return;
    }

    this._renderRoute(targetRoute, mergedParams);
  }

  syncUrlSession(sessionId) {
    if (!sessionId) return;
    const { routeName } = this._parseRoute(window.location.hash);
    if (!this.RESULT_DEPENDENT_ROUTES.includes(routeName)) return;

    const currentParams = this.getParams();
    if (currentParams.session_id === sessionId) return;

    currentParams.session_id = sessionId;
    const qs = new URLSearchParams(currentParams).toString();
    const newHash = qs ? `#${routeName}?${qs}` : `#${routeName}`;

    try {
      window.history.replaceState(null, "", newHash);
      this.params = currentParams;
    } catch (_) {}
  }

  _handleHashChange() {
    const raw = window.location.hash || "dashboard";
    const { routeName, params } = this._parseRoute(raw);
    this._renderRoute(routeName, params);
  }

  _renderRoute(routeName, params = {}) {
    const routeConfig = this.routes[routeName] || this.routes.dashboard;
    this.currentRoute = routeName;
    this.params = { ...params };
    if (window.appState) {
      window.appState.set("currentView", routeName);
      if (params.session_id) {
        window.appState.set("activeSessionId", params.session_id);
      }
    }

    // Update active nav item styling
    document.querySelectorAll(".nav-item").forEach((el) => {
      const target = el.getAttribute("data-route");
      if (target === routeName) {
        el.classList.add("active");
      } else {
        el.classList.remove("active");
      }
    });

    // Update breadcrumbs
    const currentBreadcrumb = document.getElementById("breadcrumb-current-label");
    if (currentBreadcrumb) {
      currentBreadcrumb.textContent = routeConfig.title;
    }

    // Scroll container to top and configure route attributes
    if (this.container) {
      this.container.setAttribute("data-route", routeName);
      if (routeName === "viewer" || routeName === "findings") {
        this.container.classList.add("no-scroll-view");
      } else {
        this.container.classList.remove("no-scroll-view");
      }
      this.container.scrollTop = 0;
      this.container.innerHTML = `<div class="empty-state"><div class="spinner" style="margin: 0 auto 16px;"></div><div>Loading view...</div></div>`;
      routeConfig.view.render(this.container);
    }
  }
}

window.router = new Router();
