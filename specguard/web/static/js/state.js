/**
 * SpecGuard Reactive State Store & Event Bus
 * Manages local application state without external state management libraries.
 */

class AppState {
  constructor() {
    this.state = {
      theme: localStorage.getItem("specguard-theme") || "dark",
      currentView: "dashboard",
      activeDocument: null,
      activeDomain: "mechanical",
      activeSessionId: null,
      activeFindings: [],
      activeJobId: null,
      activePage: 1,
      totalPages: 1,
      focusedFinding: null,
      stats: null
    };

    this.listeners = new Map();
  }

  get(key) {
    return this.state[key];
  }

  set(key, value) {
    const oldValue = this.state[key];
    this.state[key] = value;
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
}

window.appState = new AppState();
