/**
 * SpecGuard Single-Page Application Router
 * Manages hash-based routing, active view lifecycle, and breadcrumbs navigation.
 */

class Router {
  constructor() {
    this.routes = {
      dashboard: { title: "Executive Dashboard", view: window.DashboardView },
      new_analysis: { title: "New Document Verification", view: window.NewAnalysisView },
      workspace: { title: "Analysis Workspace", view: window.WorkspaceView },
      results: { title: "Verification Results", view: window.ResultsView },
      viewer: { title: "Interactive Document Canvas", view: window.ViewerView },
      findings: { title: "Findings Management", view: window.FindingsView },
      history: { title: "Document History & Revisions", view: window.HistoryView },
      reports: { title: "Certified Reports Export", view: window.ReportsView },
      standards: { title: "Standards & Domain Templates", view: window.StandardsView },
      training: { title: "Machine Learning & Models", view: window.TrainingView },
      settings: { title: "Settings & System Health", view: window.SettingsView }
    };

    this.container = null;
    this.currentRoute = null;

    window.addEventListener("hashchange", () => this._handleHashChange());
  }

  init(containerId) {
    this.container = document.getElementById(containerId);
    const initialHash = window.location.hash.replace("#", "") || "dashboard";
    this.navigate(initialHash);
  }

  navigate(routeName) {
    const cleanRoute = routeName.replace("#", "");
    if (!this.routes[cleanRoute]) {
      console.warn(`Route '${cleanRoute}' not found, falling back to dashboard.`);
      window.location.hash = "#dashboard";
      return;
    }

    if (window.location.hash !== `#${cleanRoute}`) {
      window.location.hash = `#${cleanRoute}`;
      return;
    }

    this._renderRoute(cleanRoute);
  }

  _handleHashChange() {
    const hash = window.location.hash.replace("#", "") || "dashboard";
    this._renderRoute(hash);
  }

  _renderRoute(routeName) {
    const routeConfig = this.routes[routeName] || this.routes.dashboard;
    this.currentRoute = routeName;
    window.appState.set("currentView", routeName);

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

    // Scroll container to top
    if (this.container) {
      this.container.scrollTop = 0;
      this.container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⏳</div><div>Loading view...</div></div>`;
      routeConfig.view.render(this.container);
    }
  }
}

window.router = new Router();
