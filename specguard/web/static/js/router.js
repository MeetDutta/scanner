/**
 * SpecGuard Single-Page Application Router
 * Manages hash-based routing, active view lifecycle, and breadcrumbs navigation.
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

    // Scroll container to top and configure route attributes
    if (this.container) {
      this.container.setAttribute("data-route", routeName);
      if (routeName === "viewer" || routeName === "findings") {
        this.container.classList.add("no-scroll-view");
      } else {
        this.container.classList.remove("no-scroll-view");
      }
      this.container.scrollTop = 0;
      this.container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⏳</div><div>Loading view...</div></div>`;
      routeConfig.view.render(this.container);
    }
  }
}

window.router = new Router();
