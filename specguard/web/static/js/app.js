/**
 * SpecGuard Master Application Bootstrap
 * Initializes theme, keyboard shortcuts, sidebar collapse, and router lifecycle.
 */

class SpecGuardApp {
  constructor() {
    this.initTheme();
    this.initSidebar();
    this.initShortcuts();
  }

  initTheme() {
    const savedTheme = localStorage.getItem("specguard-theme");
    const systemDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const theme = savedTheme || (systemDark ? "dark" : "light");
    this.setTheme(theme);

    // React to OS theme changes if user hasn't explicitly pinned
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
      if (!localStorage.getItem("specguard-theme")) {
        this.setTheme(e.matches ? "dark" : "light");
      }
    });
  }

  setTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("specguard-theme", theme);
    window.appState.set("theme", theme);

    // Update theme toggle icon in header
    const themeBtn = document.getElementById("header-theme-toggle");
    if (themeBtn) {
      themeBtn.innerHTML = theme === "dark" ? "☀️" : "🌙";
      themeBtn.title = theme === "dark" ? "Switch to Light Theme" : "Switch to Dark Theme";
    }
  }

  toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme") || "dark";
    this.setTheme(current === "dark" ? "light" : "dark");
  }

  initSidebar() {
    const sidebar = document.getElementById("app-sidebar");
    const toggleBtn = document.getElementById("sidebar-collapse-btn");

    if (toggleBtn && sidebar) {
      const isCollapsed = localStorage.getItem("specguard-sidebar-collapsed") === "true";
      if (isCollapsed) sidebar.classList.add("collapsed");

      toggleBtn.onclick = () => {
        sidebar.classList.toggle("collapsed");
        const collapsed = sidebar.classList.contains("collapsed");
        localStorage.setItem("specguard-sidebar-collapsed", collapsed);
      };
    }
  }

  initShortcuts() {
    document.addEventListener("keydown", (e) => {
      // Don't intercept when user is typing in form inputs
      if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) {
        return;
      }

      if (e.key === "d" && !e.ctrlKey && !e.metaKey) {
        window.router.navigate("dashboard");
      } else if (e.key === "n" && !e.ctrlKey && !e.metaKey) {
        window.router.navigate("new_analysis");
      } else if (e.key === "v" && !e.ctrlKey && !e.metaKey) {
        window.router.navigate("viewer");
      } else if (e.key === "f" && !e.ctrlKey && !e.metaKey) {
        window.router.navigate("findings");
      } else if (e.key === "h" && !e.ctrlKey && !e.metaKey) {
        window.router.navigate("history");
      }
    });
  }

  start() {
    window.router.init("main-view-container");
    console.log("SpecGuard 100% Offline Engineering Framework Initialized.");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  window.app = new SpecGuardApp();
  window.app.start();
});
