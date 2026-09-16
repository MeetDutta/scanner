/**
 * Toast Notification System for SpecGuard
 * Displays non-blocking, accessible system notifications.
 */

class ToastManager {
  constructor() {
    this.root = document.getElementById("toast-root");
    if (!this.root) {
      this.root = document.createElement("div");
      this.root.id = "toast-root";
      document.body.appendChild(this.root);
    }
  }

  show(message, type = "info", duration = 4000) {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;

    const iconMap = {
      success: "✓",
      error: "✕",
      warning: "⚠",
      info: "ℹ"
    };

    const icon = iconMap[type] || "•";

    toast.innerHTML = `
      <span style="font-weight: 800; font-size: 15px; color: inherit;">${icon}</span>
      <span style="flex: 1; line-height: 1.3;">${message}</span>
      <button style="background: none; border: none; font-size: 14px; cursor: pointer; color: var(--text-muted); padding: 2px;">✕</button>
    `;

    const closeBtn = toast.querySelector("button");
    closeBtn.onclick = () => this._remove(toast);

    this.root.appendChild(toast);

    if (duration > 0) {
      setTimeout(() => this._remove(toast), duration);
    }
  }

  success(msg, duration) { this.show(msg, "success", duration); }
  error(msg, duration = 6000) { this.show(msg, "error", duration); }
  warning(msg, duration) { this.show(msg, "warning", duration); }
  info(msg, duration) { this.show(msg, "info", duration); }

  _remove(toast) {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    toast.style.transition = "all 200ms ease";
    setTimeout(() => {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 200);
  }
}

window.toast = new ToastManager();
