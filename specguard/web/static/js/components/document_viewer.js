/**
 * Interactive Document Viewer Canvas Component for DocReady / SpecGuard
 * Redesigned Professional Document Correction Workstation
 * 
 * Features:
 * - 100% Offline true responsive page scaling (Fit Page, Fit Width, Actual Size, Preset Zooms)
 * - Dynamic dimension calculation (A4, Letter, Legal, Landscape, Custom) with zero vertical clipping
 * - Collapsible multi-panel workstation layout (< Collapse Pages, Collapse Details >, Focus Document)
 * - Smart issue navigation (Issue X of Y, Jump to Issue, Zoom to Issue, Fit Page return)
 * - Professional Finding Details & Problem/Suggested/Reason cards
 * - Live Rectification Workstation with text replacement & formatting controls (Font, Size, Bold, Italic, Underline, Align)
 * - Debounced Autosave (750ms) to isolated session working copy (original document never modified)
 * - Revision tracking with immediate Undo and Redo
 * - Interactive Change History panel with click-to-navigate
 * - Multi-page issue distribution counter (Page 1 (9), Page 2 (3))
 */

class DocumentViewerComponent {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.docId = null;
    this.currentPage = 1;
    this.totalPages = 1;
    this.zoomLevel = 1.0;
    this.zoomMode = "fit-page"; // Default to FIT PAGE
    this.findings = [];
    this.focusedFinding = null;
    this.pageWidth = 595.28; // Standard A4 baseline, dynamically updated
    this.pageHeight = 841.89;
    this.onFindingSelected = null;

    // Filters and UI State
    this.activeCategoryFilter = "ALL";
    this.activeSeverityFilter = "ALL";
    this.exactOnlyFilter = false;
    this.legendVisible = false;

    // Panel collapse states
    this.leftCollapsed = false;
    this.rightCollapsed = false;
    this.focusMode = false;
    this.activeDrawerTab = "details"; // "details" | "history"

    // Live Rectification & Autosave State
    this.liveRectifyMode = false;
    this.editSaving = false;
    this.editRevision = 0;
    this.editChanges = [];
    this.autosaveTimer = null;
    this.autosaveStatus = "ready"; // "ready" | "saving" | "saved" | "error"

    // Resize observer
    this._resizeObserver = null;
    this._initialFitDone = false;
  }

  async loadDocument(docId, totalPages = 1, findings = []) {
    this.docId = docId;
    this.totalPages = totalPages;
    this.currentPage = 1;
    this.findings = findings;
    this.activeTab = "pages";
    this.docDetails = null;
    this.focusedFinding = null;
    this.zoomMode = "fit-page";
    this.liveRectifyMode = false;
    this._initialFitDone = false;

    this.render();

    try {
      this.docDetails = await window.api.documents.get(docId);
      if (this.docDetails && this.docDetails.page_count) {
        this.totalPages = this.docDetails.page_count;
      }
      this._syncPageDimensions();

      try {
        const sessionId = window.appState.get("activeSessionId");
        if (sessionId) {
          const editState = await window.api.editor.status(sessionId);
          this.editRevision = editState.revision || 0;
          this.editChanges = editState.changes || [];
        }
      } catch (_) {}

      this.renderSidebarContent();
      this.renderPageCanvas();
      this.updateToolbar();
      this._setupResizeObserver();

      // Ensure initial Fit Page calculation executes after layout settles
      setTimeout(() => {
        this.fitPage();
      }, 100);
    } catch (e) {
      console.warn("Could not fetch document details AST:", e);
      this.renderPageCanvas();
      this.updateToolbar();
      setTimeout(() => this.fitPage(), 100);
    }
  }

  _setupResizeObserver() {
    if (this._resizeObserver) {
      this._resizeObserver.disconnect();
    }
    const viewport = this.container ? this.container.querySelector("#viewer-canvas-viewport") : null;
    if (viewport && window.ResizeObserver) {
      this._resizeObserver = new ResizeObserver(() => {
        if (this.zoomMode === "fit-page") {
          this.fitPage(false);
        } else if (this.zoomMode === "fit-width") {
          this.fitWidth(false);
        }
      });
      this._resizeObserver.observe(viewport);
    }
  }

  _syncPageDimensions() {
    const pages = this.docDetails && this.docDetails.pages;
    const p = pages && pages[this.currentPage - 1];
    if (p) {
      this.pageWidth = Number(p.width) || this.pageWidth;
      this.pageHeight = Number(p.height) || this.pageHeight;
    }
  }

  setPage(pageNum) {
    if (pageNum < 1 || pageNum > this.totalPages) return;
    this.currentPage = pageNum;
    this._syncPageDimensions();
    this.renderPageCanvas();
    this.updateToolbar();
    this.renderSidebarContent();
    if (this.zoomMode === "fit-page") {
      this.fitPage(false);
    } else if (this.zoomMode === "fit-width") {
      this.fitWidth(false);
    }
  }

  fitPage(triggerRender = true) {
    const viewport = this.container ? this.container.querySelector("#viewer-canvas-viewport") : null;
    if (viewport && this.pageWidth > 0 && this.pageHeight > 0) {
      const availableW = Math.max(120, viewport.clientWidth - 32);
      const availableH = Math.max(120, viewport.clientHeight - 32);
      const scale = Math.min(availableW / this.pageWidth, availableH / this.pageHeight);
      this.zoomLevel = Math.max(0.2, Math.min(3.0, scale));
      this.zoomMode = "fit-page";
      if (triggerRender) this.renderPageCanvas();
      this.updateToolbar();
    }
  }

  fitWidth(triggerRender = true) {
    const viewport = this.container ? this.container.querySelector("#viewer-canvas-viewport") : null;
    if (viewport && this.pageWidth > 0) {
      const availableW = Math.max(120, viewport.clientWidth - 32);
      this.zoomLevel = Math.max(0.2, Math.min(3.0, availableW / this.pageWidth));
      this.zoomMode = "fit-width";
      if (triggerRender) this.renderPageCanvas();
      this.updateToolbar();
    }
  }

  actualSize() {
    this.zoomLevel = 1.0;
    this.zoomMode = "manual";
    this.renderPageCanvas();
    this.updateToolbar();
  }

  setZoom(zoom) {
    this.zoomLevel = Math.max(0.3, Math.min(3.0, zoom));
    this.zoomMode = "manual";
    this.renderPageCanvas();
    this.updateToolbar();
  }

  jumpToIssue() {
    if (!this.focusedFinding) return;
    const groupEl = this.container.querySelector(`[data-finding-id="${this.focusedFinding.finding_id}"]`);
    if (groupEl) {
      groupEl.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
    }
  }

  zoomToIssue() {
    if (!this.focusedFinding) return;
    this.setZoom(1.75);
    setTimeout(() => {
      this.jumpToIssue();
    }, 100);
  }

  getFilteredFindings() {
    return this.findings.filter((f) => {
      if (this.activeCategoryFilter !== "ALL" && f.category !== this.activeCategoryFilter) {
        return false;
      }
      if (this.activeSeverityFilter !== "ALL" && f.severity !== this.activeSeverityFilter) {
        return false;
      }
      if (this.exactOnlyFilter && (!f.location_precision || !f.location_precision.startsWith("EXACT"))) {
        return false;
      }
      return true;
    });
  }

  focusFinding(finding) {
    this.focusedFinding = finding;
    const targetPage = finding.page_number || finding.page || 1;
    if (targetPage !== this.currentPage) {
      this.currentPage = targetPage;
      this._syncPageDimensions();
    }

    if (this.focusMode) {
      this.toggleFocusMode();
    }
    if (this.rightCollapsed) {
      this.toggleRightPanel();
    }

    this.renderPageCanvas();
    this.updateToolbar();
    this.renderSidebarContent();
    this.showFindingInDrawer(finding);

    if (finding.bbox) {
      setTimeout(() => {
        this.jumpToIssue();
      }, 80);
    }
  }

  focusFindingById(findingId) {
    const target = this.findings.find((f) => f.finding_id === findingId);
    if (target) {
      this.focusFinding(target);
    }
  }

  nextFinding() {
    const list = this.getFilteredFindings();
    if (list.length === 0) return;
    if (!this.focusedFinding) {
      this.focusFinding(list[0]);
      return;
    }
    const idx = list.findIndex((f) => f.finding_id === this.focusedFinding.finding_id);
    const nextIdx = (idx + 1) % list.length;
    this.focusFinding(list[nextIdx]);
  }

  prevFinding() {
    const list = this.getFilteredFindings();
    if (list.length === 0) return;
    if (!this.focusedFinding) {
      this.focusFinding(list[list.length - 1]);
      return;
    }
    const idx = list.findIndex((f) => f.finding_id === this.focusedFinding.finding_id);
    const prevIdx = (idx - 1 + list.length) % list.length;
    this.focusFinding(list[prevIdx]);
  }

  toggleLeftPanel() {
    this.leftCollapsed = !this.leftCollapsed;
    const layout = this.container.querySelector(".viewer-layout");
    const sidebar = this.container.querySelector(".viewer-pages-sidebar");
    const toggleBtn = this.container.querySelector("#viewer-toggle-left");
    if (layout) layout.classList.toggle("left-collapsed", this.leftCollapsed);
    if (sidebar) sidebar.classList.toggle("collapsed", this.leftCollapsed);
    if (toggleBtn) toggleBtn.textContent = this.leftCollapsed ? "❯" : "❮";
    setTimeout(() => {
      if (this.zoomMode === "fit-page") this.fitPage(false);
      else if (this.zoomMode === "fit-width") this.fitWidth(false);
    }, 150);
  }

  toggleRightPanel() {
    this.rightCollapsed = !this.rightCollapsed;
    const layout = this.container.querySelector(".viewer-layout");
    const drawer = this.container.querySelector("#viewer-detail-drawer");
    const toggleBtn = this.container.querySelector("#viewer-toggle-right");
    if (layout) layout.classList.toggle("right-collapsed", this.rightCollapsed);
    if (drawer) drawer.classList.toggle("collapsed", this.rightCollapsed);
    if (toggleBtn) toggleBtn.textContent = this.rightCollapsed ? "❮ Finding Details" : "✕";
    setTimeout(() => {
      if (this.zoomMode === "fit-page") this.fitPage(false);
      else if (this.zoomMode === "fit-width") this.fitWidth(false);
    }, 150);
  }

  toggleFocusMode() {
    this.focusMode = !this.focusMode;
    const layout = this.container.querySelector(".viewer-layout");
    const focusBtn = this.container.querySelector("#viewer-btn-focus");
    if (layout) layout.classList.toggle("focus-mode", this.focusMode);
    if (focusBtn) {
      focusBtn.classList.toggle("active", this.focusMode);
      focusBtn.textContent = this.focusMode ? "✕ Exit Focus" : "⛶ Focus Document";
    }
    setTimeout(() => {
      this.fitPage(false);
    }, 150);
  }

  render() {
    if (!this.container) return;

    this.container.innerHTML = `
      <div class="viewer-layout">
        <!-- Floating Exit Focus Button for Fullscreen Mode -->
        <button class="btn btn-primary btn-sm viewer-exit-focus-btn" id="viewer-float-exit-focus" title="Exit Focus Mode">✕ Exit Focus</button>

        <!-- LEFT: Page Navigation Sidebar with Multi-Page Tabs -->
        <div class="viewer-pages-sidebar">
          <div class="pages-sidebar-header">
            <span>Pages</span>
            <button class="btn btn-secondary btn-sm" id="viewer-toggle-left" title="Collapse / Expand Page Navigator" style="padding: 2px 6px; font-size: 11px;">❮</button>
          </div>

          <div class="viewer-sidebar-tabs" style="display: flex; border-bottom: 1px solid var(--border-default); background: var(--bg-surface-sunken); min-width: 0;">
            <button class="v-tab ${this.activeTab === 'pages' ? 'active' : ''}" data-tab="pages" style="flex: 1; padding: 6px 2px; font-size: 11px; font-weight: 700; border: none; background: transparent; cursor: pointer; color: ${this.activeTab === 'pages' ? 'var(--accent-primary)' : 'var(--text-muted)'}; border-bottom: 2px solid ${this.activeTab === 'pages' ? 'var(--accent-primary)' : 'transparent'};">Pages</button>
            <button class="v-tab ${this.activeTab === 'structure' ? 'active' : ''}" data-tab="structure" style="flex: 1; padding: 6px 2px; font-size: 11px; font-weight: 700; border: none; background: transparent; cursor: pointer; color: ${this.activeTab === 'structure' ? 'var(--accent-primary)' : 'var(--text-muted)'}; border-bottom: 2px solid ${this.activeTab === 'structure' ? 'var(--accent-primary)' : 'transparent'};">Tree</button>
            <button class="v-tab ${this.activeTab === 'toc' ? 'active' : ''}" data-tab="toc" style="flex: 1; padding: 6px 2px; font-size: 11px; font-weight: 700; border: none; background: transparent; cursor: pointer; color: ${this.activeTab === 'toc' ? 'var(--accent-primary)' : 'var(--text-muted)'}; border-bottom: 2px solid ${this.activeTab === 'toc' ? 'var(--accent-primary)' : 'transparent'};">TOC</button>
            <button class="v-tab ${this.activeTab === 'assets' ? 'active' : ''}" data-tab="assets" style="flex: 1; padding: 6px 2px; font-size: 11px; font-weight: 700; border: none; background: transparent; cursor: pointer; color: ${this.activeTab === 'assets' ? 'var(--accent-primary)' : 'var(--text-muted)'}; border-bottom: 2px solid ${this.activeTab === 'assets' ? 'var(--accent-primary)' : 'transparent'};">Assets</button>
          </div>
          <div class="pages-list" id="viewer-pages-list"></div>
        </div>

        <!-- CENTER: Canvas Viewport Workstation -->
        <div class="viewer-center-pane">
          <!-- Comprehensive Responsive 2-Row Document Toolbar -->
          <div class="viewer-toolbar">
            <!-- Row 1: Page Navigation and Issue Navigation -->
            <div class="viewer-toolbar-row">
              <!-- Page Navigation -->
              <div class="toolbar-group">
                <button class="btn btn-secondary btn-sm" id="viewer-btn-prev" title="Previous Page">← Prev</button>
                <span id="viewer-page-counter" style="font-size: 11.5px; font-weight: 700; color: var(--text-primary); min-width: 65px; text-align: center; white-space: nowrap;">
                  Page 1 of 1
                </span>
                <button class="btn btn-secondary btn-sm" id="viewer-btn-next" title="Next Page">Next →</button>
              </div>

              <!-- Issue Navigation -->
              <div class="toolbar-group">
                <button class="btn btn-secondary btn-sm" id="viewer-issue-prev" title="Previous Issue">⏮ Prev Issue</button>
                <span id="viewer-issue-counter" style="font-size: 11px; font-weight: 700; color: var(--accent-primary); min-width: 65px; text-align: center; white-space: nowrap;">Issues</span>
                <button class="btn btn-secondary btn-sm" id="viewer-issue-next" title="Next Issue">Next Issue ⏭</button>
                <button class="btn btn-secondary btn-sm" id="viewer-btn-jump" title="Center viewport on issue without changing zoom" style="display:none;">📍 Jump</button>
                <button class="btn btn-secondary btn-sm" id="viewer-btn-zoom-issue" title="Zoom in on selected issue" style="display:none;">🔍 Zoom</button>
              </div>
            </div>

            <!-- Row 2: Category Filter, Zoom Controls, Modes, Legend -->
            <div class="viewer-toolbar-row">
              <!-- Category Filter -->
              <div class="toolbar-group">
                <select id="viewer-cat-filter" class="form-select" style="font-size: 11px; padding: 2px 6px; height: 26px; border-radius: var(--radius-sm); max-width: 140px;">
                  <option value="ALL">All Categories</option>
                  <option value="Formatting">Formatting</option>
                  <option value="Grammar & Spelling">Spelling & Grammar</option>
                  <option value="Figure">Figures & Diagrams</option>
                  <option value="Table">Data Tables</option>
                  <option value="Table of Contents">Table of Contents</option>
                  <option value="Document Structure">Section Hierarchy</option>
                  <option value="Cross-Reference & Citation">Cross-References</option>
                  <option value="Equation">Equations</option>
                  <option value="Engineering Parameter">Parameters</option>
                </select>
              </div>

              <!-- Zoom Controls -->
              <div class="toolbar-group">
                <button class="btn btn-secondary btn-sm" id="viewer-zoom-out" title="Zoom Out">−</button>
                <button class="btn btn-secondary btn-sm" id="viewer-zoom-75" title="75% Zoom" style="font-size:10px; padding:2px 5px;">75%</button>
                <button class="btn btn-secondary btn-sm" id="viewer-zoom-100" title="100% Actual Size" style="font-size:10px; padding:2px 5px;">100%</button>
                <button class="btn btn-secondary btn-sm" id="viewer-zoom-125" title="125% Zoom" style="font-size:10px; padding:2px 5px;">125%</button>
                <button class="btn btn-secondary btn-sm" id="viewer-zoom-in" title="Zoom In">+</button>
                <span id="viewer-zoom-label" style="font-size: 11px; font-weight: 700; min-width: 36px; text-align: center; color: var(--text-muted); white-space: nowrap;">100%</span>
              </div>

              <!-- Modes & Legend -->
              <div class="toolbar-group">
                <button class="btn btn-secondary btn-sm active" id="viewer-fit-page" title="Fit Entire Page Vertically & Horizontally">Fit Page</button>
                <button class="btn btn-secondary btn-sm" id="viewer-fit-width" title="Fit Page Width to Viewport">Fit Width</button>
                <button class="btn btn-secondary btn-sm" id="viewer-btn-focus" title="Maximize document viewport by hiding sidebars">⛶ Focus Document</button>
                <button class="btn btn-secondary btn-sm" id="viewer-legend-toggle" title="Toggle Annotation Visual Legend">🎨 Legend</button>
              </div>
            </div>
          </div>

          <!-- Collapsible Annotation Legend Popover -->
          <div class="annotation-legend-popover" id="viewer-legend-popover" style="display: none;">
            <div style="font-weight: 800; font-size: 11.5px; margin-bottom: 8px; border-bottom: 1px solid var(--border-default); padding-bottom: 4px; display: flex; justify-content: space-between;">
              <span>Annotation Visual Legend</span>
              <span id="viewer-legend-close" style="cursor: pointer;">✕</span>
            </div>
            <div class="legend-item">
              <span class="legend-swatch"><svg width="34" height="12"><path d="M 0 6 q 3 3 6 0 t 6 0 t 6 0 t 6 0 t 6 0" fill="none" stroke="#dc2626" stroke-width="2.2" /></svg></span>
              <span><strong>Red Wavy:</strong> Spelling error / typo</span>
            </div>
            <div class="legend-item">
              <span class="legend-swatch"><svg width="34" height="12"><path d="M 0 6 q 3 3 6 0 t 6 0 t 6 0 t 6 0 t 6 0" fill="none" stroke="#2563eb" stroke-width="2.2" /></svg></span>
              <span><strong>Blue Wavy:</strong> Grammar / repeated word</span>
            </div>
            <div class="legend-item">
              <span class="legend-swatch"><svg width="34" height="12"><line x1="0" y1="4" x2="34" y2="4" stroke="#f59e0b" stroke-width="1.6" /><line x1="0" y1="8" x2="34" y2="8" stroke="#f59e0b" stroke-width="1.6" /></svg></span>
              <span><strong>Orange Double:</strong> Duplicate label / number</span>
            </div>
            <div class="legend-item">
              <span class="legend-swatch"><svg width="34" height="12"><line x1="0" y1="6" x2="34" y2="6" stroke="#ea580c" stroke-width="2" stroke-dasharray="3,2" /></svg></span>
              <span><strong>Orange Dotted:</strong> Broken ref / TOC drift</span>
            </div>
            <div class="legend-item">
              <span class="legend-swatch"><svg width="34" height="12"><rect x="2" y="1" width="30" height="10" fill="rgba(217, 119, 6, 0.15)" stroke="#d97706" stroke-width="1.2" stroke-dasharray="3,2" rx="2" /></svg></span>
              <span><strong>Dashed Box:</strong> Formatting / Parameter</span>
            </div>
          </div>

          <!-- Document Canvas Viewport -->
          <div class="canvas-viewport" id="viewer-canvas-viewport">
            <div class="page-canvas-wrapper" id="viewer-page-wrapper">
              <img class="page-canvas-image" id="viewer-page-img" alt="Document Page" />
              <svg class="page-overlay-svg" id="viewer-overlay-svg" xmlns="http://www.w3.org/2000/svg"></svg>
            </div>
          </div>
        </div>

        <!-- RIGHT: Finding Details & Live Rectification Workstation Drawer -->
        <div class="viewer-detail-drawer" id="viewer-detail-drawer">
          <div class="drawer-header">
            <div style="display: flex; align-items: center; gap: 8px;">
              <button class="v-tab ${this.activeDrawerTab === 'details' ? 'active' : ''}" id="tab-drawer-details" style="padding: 3px 8px; font-size: 11px; font-weight: 800; border: none; background: transparent; cursor: pointer; color: ${this.activeDrawerTab === 'details' ? 'var(--accent-primary)' : 'var(--text-muted)'}; border-bottom: 2px solid ${this.activeDrawerTab === 'details' ? 'var(--accent-primary)' : 'transparent'};">FINDING DETAILS</button>
              <button class="v-tab ${this.activeDrawerTab === 'history' ? 'active' : ''}" id="tab-drawer-history" style="padding: 3px 8px; font-size: 11px; font-weight: 800; border: none; background: transparent; cursor: pointer; color: ${this.activeDrawerTab === 'history' ? 'var(--accent-primary)' : 'var(--text-muted)'}; border-bottom: 2px solid ${this.activeDrawerTab === 'history' ? 'var(--accent-primary)' : 'transparent'};">HISTORY (<span id="drawer-rev-count">${this.editRevision}</span>)</button>
            </div>
            <button class="btn btn-secondary btn-sm" id="viewer-toggle-right" title="Collapse Drawer" style="padding: 2px 6px; font-size: 11px;">✕</button>
          </div>

          <div class="drawer-content" id="viewer-drawer-content"></div>
        </div>
      </div>
    `;

    this._bindEvents();
    this.renderPageList();
    this.renderPageCanvas();
    this.updateToolbar();
    this.showFindingInDrawer(this.focusedFinding);
  }

  _bindEvents() {
    this.container.querySelector("#viewer-btn-prev").onclick = () => this.setPage(this.currentPage - 1);
    this.container.querySelector("#viewer-btn-next").onclick = () => this.setPage(this.currentPage + 1);

    this.container.querySelector("#viewer-issue-prev").onclick = () => this.prevFinding();
    this.container.querySelector("#viewer-issue-next").onclick = () => this.nextFinding();

    this.container.querySelector("#viewer-btn-jump").onclick = () => this.jumpToIssue();
    this.container.querySelector("#viewer-btn-zoom-issue").onclick = () => this.zoomToIssue();

    this.container.querySelector("#viewer-zoom-out").onclick = () => this.setZoom(this.zoomLevel - 0.2);
    this.container.querySelector("#viewer-zoom-in").onclick = () => this.setZoom(this.zoomLevel + 0.2);
    this.container.querySelector("#viewer-zoom-75").onclick = () => this.setZoom(0.75);
    this.container.querySelector("#viewer-zoom-100").onclick = () => this.actualSize();
    this.container.querySelector("#viewer-zoom-125").onclick = () => this.setZoom(1.25);

    this.container.querySelector("#viewer-fit-page").onclick = () => this.fitPage();
    this.container.querySelector("#viewer-fit-width").onclick = () => this.fitWidth();
    this.container.querySelector("#viewer-btn-focus").onclick = () => this.toggleFocusMode();
    const floatExitBtn = this.container.querySelector("#viewer-float-exit-focus");
    if (floatExitBtn) {
      floatExitBtn.onclick = () => this.toggleFocusMode();
    }

    this.container.querySelector("#viewer-toggle-left").onclick = () => this.toggleLeftPanel();
    this.container.querySelector("#viewer-toggle-right").onclick = () => this.toggleRightPanel();

    const catSelect = this.container.querySelector("#viewer-cat-filter");
    if (catSelect) {
      catSelect.onchange = (e) => {
        this.activeCategoryFilter = e.target.value;
        this.renderPageCanvas();
        this.updateToolbar();
      };
    }

    const legendToggle = this.container.querySelector("#viewer-legend-toggle");
    const legendPopover = this.container.querySelector("#viewer-legend-popover");
    const legendClose = this.container.querySelector("#viewer-legend-close");
    if (legendToggle && legendPopover) {
      legendToggle.onclick = () => {
        this.legendVisible = !this.legendVisible;
        legendPopover.style.display = this.legendVisible ? "block" : "none";
      };
      if (legendClose) {
        legendClose.onclick = () => {
          this.legendVisible = false;
          legendPopover.style.display = "none";
        };
      }
    }

    this.container.querySelector("#tab-drawer-details").onclick = () => {
      this.activeDrawerTab = "details";
      this._updateDrawerTabs();
      this.showFindingInDrawer(this.focusedFinding);
    };

    this.container.querySelector("#tab-drawer-history").onclick = () => {
      this.activeDrawerTab = "history";
      this._updateDrawerTabs();
      this.renderHistoryContent();
    };

    this.container.querySelectorAll(".v-tab[data-tab]").forEach((tabBtn) => {
      tabBtn.onclick = () => {
        this.activeTab = tabBtn.getAttribute("data-tab");
        this.container.querySelectorAll(".v-tab[data-tab]").forEach((b) => {
          const isActive = b.getAttribute("data-tab") === this.activeTab;
          b.style.color = isActive ? "var(--accent-primary)" : "var(--text-muted)";
          b.style.borderBottom = isActive ? "2px solid var(--accent-primary)" : "transparent";
        });
        this.renderSidebarContent();
      };
    });
  }

  _updateDrawerTabs() {
    const tDet = this.container.querySelector("#tab-drawer-details");
    const tHist = this.container.querySelector("#tab-drawer-history");
    if (tDet) {
      tDet.style.color = this.activeDrawerTab === "details" ? "var(--accent-primary)" : "var(--text-muted)";
      tDet.style.borderBottom = this.activeDrawerTab === "details" ? "2px solid var(--accent-primary)" : "transparent";
    }
    if (tHist) {
      tHist.style.color = this.activeDrawerTab === "history" ? "var(--accent-primary)" : "var(--text-muted)";
      tHist.style.borderBottom = this.activeDrawerTab === "history" ? "2px solid var(--accent-primary)" : "transparent";
    }
  }

  renderSidebarContent() {
    const listEl = this.container.querySelector("#viewer-pages-list");
    if (!listEl) return;
    listEl.innerHTML = "";

    const activeFindings = this.getFilteredFindings();

    if (this.activeTab === "pages") {
      for (let i = 1; i <= this.totalPages; i++) {
        const findingsOnPage = activeFindings.filter((f) => (f.page_number || f.page) === i);
        const item = document.createElement("div");
        item.className = `page-thumb-item ${i === this.currentPage ? "active" : ""}`;
        item.innerHTML = `
          <span>Page ${i}</span>
          ${findingsOnPage.length > 0 ? `<span class="badge badge-critical" style="font-size: 9.5px; padding: 1px 5px;">${findingsOnPage.length}</span>` : `<span class="badge badge-outline" style="font-size: 9px; padding: 1px 4px; color:var(--text-muted);">0</span>`}
        `;
        item.onclick = () => this.setPage(i);
        listEl.appendChild(item);
      }
    } else if (this.activeTab === "structure") {
      const sections = this.docDetails?.sections || [];
      if (sections.length === 0) {
        listEl.innerHTML = `<div style="padding: 12px; font-size: 11.5px; color: var(--text-muted);">No section headings detected.</div>`;
        return;
      }
      sections.forEach((sec) => {
        const item = document.createElement("div");
        item.style.cssText = `padding: 6px 8px; font-size: 11px; cursor: pointer; border-radius: var(--radius-sm); margin-bottom: 2px; display: flex; justify-content: space-between; align-items: center; background: ${sec.page_num === this.currentPage ? 'var(--bg-surface-elevated)' : 'transparent'}; border-left: ${sec.level === 1 ? '3px solid var(--accent-primary)' : '1px solid var(--border-default)'}; margin-left: ${(sec.level - 1) * 8}px;`;
        item.innerHTML = `
          <span style="font-weight: ${sec.level === 1 ? '700' : '500'}; color: var(--text-primary); text-overflow: ellipsis; overflow: hidden; white-space: nowrap; max-width: 125px;">
            ${sec.number_str ? sec.number_str + ' ' : ''}${sec.title}
          </span>
          <span class="badge badge-outline" style="font-size: 9px;">P.${sec.page_num}</span>
        `;
        item.onclick = () => this.setPage(sec.page_num);
        listEl.appendChild(item);
      });
    } else if (this.activeTab === "toc") {
      const toc = this.docDetails?.toc;
      if (!toc || !toc.items || toc.items.length === 0) {
        listEl.innerHTML = `<div style="padding: 12px; font-size: 11.5px; color: var(--text-muted);">No Table of Contents detected.</div>`;
        return;
      }
      toc.items.forEach((item) => {
        const el = document.createElement("div");
        el.style.cssText = `padding: 6px 8px; font-size: 11px; cursor: pointer; border-radius: var(--radius-sm); margin-bottom: 2px; display: flex; justify-content: space-between; align-items: center; margin-left: ${(item.level - 1) * 8}px;`;
        el.innerHTML = `
          <span style="font-weight: ${item.level === 1 ? '700' : '500'}; text-overflow: ellipsis; overflow: hidden; white-space: nowrap; max-width: 125px;">${item.title}</span>
          <span class="badge badge-domain" style="font-size: 9px;">P.${item.target_page_num || item.page_num}</span>
        `;
        el.onclick = () => this.setPage(item.target_page_num || item.page_num);
        listEl.appendChild(el);
      });
    } else if (this.activeTab === "assets") {
      const figures = this.docDetails?.figures || [];
      const tables = this.docDetails?.tables || [];
      const equations = this.docDetails?.equations || [];

      if (figures.length === 0 && tables.length === 0 && equations.length === 0) {
        listEl.innerHTML = `<div style="padding: 12px; font-size: 11.5px; color: var(--text-muted);">No figures, tables, or equations extracted.</div>`;
        return;
      }

      const addAssetHeader = (title) => {
        const h = document.createElement("div");
        h.style.cssText = "font-size: 10px; font-weight: 800; color: var(--text-muted); text-transform: uppercase; padding: 6px 4px; margin-top: 4px;";
        h.textContent = title;
        listEl.appendChild(h);
      };

      if (figures.length > 0) {
        addAssetHeader(`Figures (${figures.length})`);
        figures.forEach((fig) => {
          const el = document.createElement("div");
          el.style.cssText = "padding: 5px 8px; font-size: 11px; cursor: pointer; border-radius: var(--radius-sm); margin-bottom: 2px; display: flex; justify-content: space-between; align-items: center;";
          el.innerHTML = `<span>📊 ${fig.label || 'Figure'}</span><span class="badge badge-outline" style="font-size: 9px;">P.${fig.page_num}</span>`;
          el.onclick = () => this.setPage(fig.page_num);
          listEl.appendChild(el);
        });
      }

      if (tables.length > 0) {
        addAssetHeader(`Tables (${tables.length})`);
        tables.forEach((tbl) => {
          const el = document.createElement("div");
          el.style.cssText = "padding: 5px 8px; font-size: 11px; cursor: pointer; border-radius: var(--radius-sm); margin-bottom: 2px; display: flex; justify-content: space-between; align-items: center;";
          el.innerHTML = `<span>📋 ${tbl.label || 'Table'}</span><span class="badge badge-outline" style="font-size: 9px;">P.${tbl.page_num}</span>`;
          el.onclick = () => this.setPage(tbl.page_num);
          listEl.appendChild(el);
        });
      }
    }
  }

  renderPageList() {
    this.renderSidebarContent();
  }

  renderPageCanvas() {
    const imgEl = this.container.querySelector("#viewer-page-img");
    const svgEl = this.container.querySelector("#viewer-overlay-svg");
    const wrapper = this.container.querySelector("#viewer-page-wrapper");
    if (!imgEl || !this.docId) return;

    const sessionId = window.appState.get("activeSessionId");
    // Query page image with dynamic DPI scale matching current zoom
    const renderScale = Math.max(1.0, Math.min(2.5, this.zoomLevel * 1.3));
    const imgUrl = sessionId
      ? window.api.editor.pageImageUrl(sessionId, this.currentPage, renderScale)
      : window.api.documents.getPageImageUrl(this.docId, this.currentPage, renderScale);

    imgEl.onload = () => {
      const displayW = Math.round(this.pageWidth * this.zoomLevel);
      const displayH = Math.round(this.pageHeight * this.zoomLevel);

      if (wrapper) {
        wrapper.style.width = `${displayW}px`;
        wrapper.style.height = `${displayH}px`;
      }
      imgEl.style.width = `${displayW}px`;
      imgEl.style.height = `${displayH}px`;

      svgEl.setAttribute("viewBox", `0 0 ${displayW} ${displayH}`);
      svgEl.setAttribute("width", displayW);
      svgEl.setAttribute("height", displayH);

      this.renderHighlights(displayW, displayH);
    };

    imgEl.src = imgUrl;
    this.renderPageList();
  }

  generateSquigglyPath(x0, x1, y, wavelength = 6.0, amplitude = 2.0) {
    let d = `M ${x0.toFixed(1)} ${y.toFixed(1)}`;
    let curX = x0;
    let up = true;
    while (curX < x1) {
      const nextX = Math.min(x1, curX + wavelength / 2.0);
      const midX = (curX + nextX) / 2.0;
      const peakY = up ? (y - amplitude) : (y + amplitude);
      d += ` Q ${midX.toFixed(1)} ${peakY.toFixed(1)} ${nextX.toFixed(1)} ${y.toFixed(1)}`;
      curX = nextX;
      up = !up;
    }
    return d;
  }

  renderHighlights(renderedWidth, renderedHeight) {
    const svgEl = this.container.querySelector("#viewer-overlay-svg");
    if (!svgEl) return;
    svgEl.innerHTML = "";

    const filtered = this.getFilteredFindings();
    const findingsOnPage = filtered.filter((f) => (f.page_number || f.page) === this.currentPage && f.bbox);
    const rx = renderedWidth / this.pageWidth;
    const ry = renderedHeight / this.pageHeight;

    const severityColors = {
      Critical: { stroke: "#dc2626", fill: "rgba(220, 38, 38, 0.2)" },
      High: { stroke: "#ea580c", fill: "rgba(234, 88, 12, 0.18)" },
      Medium: { stroke: "#d97706", fill: "rgba(217, 119, 6, 0.16)" },
      Low: { stroke: "#2563eb", fill: "rgba(37, 99, 235, 0.15)" },
      Informational: { stroke: "#64748b", fill: "rgba(100, 116, 139, 0.12)" }
    };

    findingsOnPage.forEach((f) => {
      const isFocused = this.focusedFinding && this.focusedFinding.finding_id === f.finding_id;
      const sevColor = severityColors[f.severity] || severityColors.Medium;

      const it = f.issue_type || "";
      const isSpelling = it === "SPELLING_ERROR" || (f.category.includes("Grammar") && f.detected_value && !f.detected_value.includes("Repeated"));
      const isGrammar = it === "REPEATED_WORD" || it === "UNBALANCED_PUNCTUATION" || (f.category.includes("Grammar") && !isSpelling);
      const isDuplicate = it.includes("DUPLICATE");
      const isTocDrift = it === "TOC_PAGE_DRIFT" || f.finding_id.startsWith("TOC-PAG");
      const isBrokenRef = it.includes("UNRESOLVED");

      const boxes = (f.bounding_boxes && f.bounding_boxes.length > 0) ? f.bounding_boxes : [f.bbox];

      const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
      group.setAttribute("class", `finding-annotation-group ${isFocused ? "focused" : ""}`);
      group.setAttribute("data-finding-id", f.finding_id);

      const titleEl = document.createElementNS("http://www.w3.org/2000/svg", "title");
      titleEl.textContent = `[${f.severity}] ${f.finding_id}: ${f.issue_type || f.category}\n` +
        `Detected: "${f.matched_text || f.detected_value || f.original_content}"\n` +
        `Expected: "${f.expected_text || f.expected_value || ''}"`;
      group.appendChild(titleEl);

      boxes.forEach((box) => {
        if (!box) return;
        const x0 = box.x0 * rx;
        const y0 = box.y0 * ry;
        const x1 = box.x1 * rx;
        const y1 = box.y1 * ry;
        const w = Math.max(8, x1 - x0);
        const h = Math.max(8, y1 - y0);
        const lineY = y1 + 1.0;

        const hitRect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        hitRect.setAttribute("x", x0);
        hitRect.setAttribute("y", y0);
        hitRect.setAttribute("width", w);
        hitRect.setAttribute("height", h);
        hitRect.setAttribute("rx", "2");
        hitRect.setAttribute("ry", "2");
        hitRect.setAttribute("class", `annotation-interactive-box ${isFocused ? "focused" : ""}`);
        hitRect.setAttribute("fill", sevColor.stroke);
        hitRect.setAttribute("fill-opacity", isFocused ? "0.26" : "0.07");
        hitRect.setAttribute("stroke", sevColor.stroke);
        hitRect.setAttribute("stroke-opacity", isFocused ? "0.9" : "0.2");
        hitRect.setAttribute("stroke-width", isFocused ? "1.8" : "0.6");
        group.appendChild(hitRect);

        if (isSpelling) {
          const wavePath = document.createElementNS("http://www.w3.org/2000/svg", "path");
          wavePath.setAttribute("d", this.generateSquigglyPath(x0, x1, lineY, 5.5, 2.0));
          wavePath.setAttribute("class", "annotation-squiggly-path");
          wavePath.setAttribute("stroke", "#dc2626");
          wavePath.setAttribute("stroke-width", isFocused ? "2.6" : "1.8");
          group.appendChild(wavePath);
        } else if (isGrammar) {
          const wavePath = document.createElementNS("http://www.w3.org/2000/svg", "path");
          wavePath.setAttribute("d", this.generateSquigglyPath(x0, x1, lineY, 5.5, 2.0));
          wavePath.setAttribute("class", "annotation-squiggly-path");
          wavePath.setAttribute("stroke", "#2563eb");
          wavePath.setAttribute("stroke-width", isFocused ? "2.6" : "1.8");
          group.appendChild(wavePath);
        } else if (isDuplicate) {
          const l1 = document.createElementNS("http://www.w3.org/2000/svg", "line");
          l1.setAttribute("x1", x0);
          l1.setAttribute("y1", lineY - 1.5);
          l1.setAttribute("x2", x1);
          l1.setAttribute("y2", lineY - 1.5);
          l1.setAttribute("class", "annotation-double-line");
          l1.setAttribute("stroke", "#f59e0b");
          l1.setAttribute("stroke-width", isFocused ? "1.8" : "1.4");
          group.appendChild(l1);

          const l2 = document.createElementNS("http://www.w3.org/2000/svg", "line");
          l2.setAttribute("x1", x0);
          l2.setAttribute("y1", lineY + 1.5);
          l2.setAttribute("x2", x1);
          l2.setAttribute("y2", lineY + 1.5);
          l2.setAttribute("class", "annotation-double-line");
          l2.setAttribute("stroke", "#f59e0b");
          l2.setAttribute("stroke-width", isFocused ? "1.8" : "1.4");
          group.appendChild(l2);
        } else if (isTocDrift || isBrokenRef) {
          const dotLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
          dotLine.setAttribute("x1", x0);
          dotLine.setAttribute("y1", lineY);
          dotLine.setAttribute("x2", x1);
          dotLine.setAttribute("y2", lineY);
          dotLine.setAttribute("class", "annotation-dotted-line");
          dotLine.setAttribute("stroke", "#ea580c");
          dotLine.setAttribute("stroke-width", isFocused ? "2.5" : "1.8");
          dotLine.setAttribute("stroke-dasharray", "3.5, 2.5");
          group.appendChild(dotLine);
        } else {
          const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
          line.setAttribute("x1", x0);
          line.setAttribute("y1", lineY);
          line.setAttribute("x2", x1);
          line.setAttribute("y2", lineY);
          line.setAttribute("stroke", sevColor.stroke);
          line.setAttribute("stroke-width", isFocused ? "2.4" : "1.6");
          group.appendChild(line);
        }
      });

      group.onclick = (e) => {
        e.stopPropagation();
        this.selectFinding(f);
      };

      svgEl.appendChild(group);
    });
  }

  selectFinding(finding) {
    this.focusedFinding = finding;
    if (this.focusMode) {
      this.toggleFocusMode();
    }
    if (this.rightCollapsed) {
      this.toggleRightPanel();
    }
    this.renderPageCanvas();
    this.showFindingInDrawer(finding);
    this.updateToolbar();
    if (this.onFindingSelected) {
      this.onFindingSelected(finding);
    }
  }

  showFindingInDrawer(f) {
    const drawerContent = this.container.querySelector("#viewer-drawer-content");
    if (!drawerContent) return;

    if (!f) {
      const filteredList = this.getFilteredFindings();
      drawerContent.innerHTML = `
        <div class="empty-state" style="padding: 24px 12px; text-align: center; min-width: 0; max-width: 100%; box-sizing: border-box;">
          <div style="font-size: 28px; margin-bottom: 6px;">🔍</div>
          <div style="font-size: 14px; font-weight: 800; color: var(--text-primary); margin-bottom: 4px;">Finding Details</div>
          <div style="font-size: 11.5px; color: var(--text-muted); line-height: 1.45; margin-bottom: 14px; word-break: break-word;">
            Select a highlighted issue from the document or choose an issue from the issue navigator.
          </div>
          <div class="badge badge-domain" style="font-size: 10.5px; padding: 3px 8px; margin-bottom: 14px;">
            ${filteredList.length} Issues Detected
          </div>
          <div style="display: flex; gap: 6px; justify-content: center; flex-wrap: wrap;">
            <button class="btn btn-secondary btn-sm" id="empty-prev-issue">⏮ Previous</button>
            <button class="btn btn-primary btn-sm" id="empty-next-issue">Next Issue ⏭</button>
          </div>
        </div>
      `;
      const prevB = drawerContent.querySelector("#empty-prev-issue");
      const nextB = drawerContent.querySelector("#empty-next-issue");
      if (prevB) prevB.onclick = () => this.prevFinding();
      if (nextB) nextB.onclick = () => this.nextFinding();
      return;
    }

    const sevClass = `badge-${(f.severity || "medium").toLowerCase()}`;
    const precision = f.location_precision || "APPROXIMATE";
    const isExact = precision.startsWith("EXACT");

    // Check if this finding has been rectified in current session
    const isRectified = this.editChanges.some((c) => c.finding_id === f.finding_id && c.status === "APPLIED");
    const statusPill = isRectified
      ? `<span class="badge badge-success" style="font-size:9.5px; padding: 1px 5px;">✓ Rectified</span>`
      : `<span class="badge badge-outline" style="font-size:9.5px; padding: 1px 5px;">● Pending</span>`;

    const currentText = String(f.matched_text || f.detected_value || f.original_content || "N/A");
    const suggestedText = String(f.suggested_fix || f.suggested_correction || f.expected_text || f.expected_value || "In accordance with standard");
    const reasonText = String(f.explanation || f.message || "Document formatting standard violation detected.");
    const ruleRef = String(f.rule_reference || "DocReady Engineering Specification Standard");

    let workstationEditorHtml = "";
    if (this.liveRectifyMode) {
      const isFormat = f.category === "Formatting" || f.category.includes("Font") || suggestedText.includes("pt") || suggestedText.includes("font");
      workstationEditorHtml = `
        <div class="live-rectify-workstation" style="margin-top: 10px; padding: 10px; background: var(--bg-surface-sunken); border: 1px solid var(--accent-primary); border-radius: var(--radius-md); min-width: 0; max-width: 100%; box-sizing: border-box;">
          <div class="live-rectify-banner">
            <span style="display:inline-flex; align-items:center; gap:6px;">
              <span class="pulse-dot"></span> Live Rectification Mode
            </span>
            <span id="live-save-indicator" style="font-size:10px; font-weight:700; color:var(--text-muted);">
              ● Ready
            </span>
          </div>

          <div style="margin-top: 8px;">
            <label style="font-size: 10px; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">Editable Correction Content</label>
            <textarea id="live-editor-textarea" class="form-input" rows="3" style="font-family: var(--font-mono); font-size: 11px; width: 100%; max-width: 100%; margin-top: 4px; box-sizing: border-box; resize: vertical;" placeholder="Enter corrected text...">${escapeHtml(suggestedText)}</textarea>
          </div>

          ${isFormat ? `
            <div style="margin-top: 6px;">
              <label style="font-size: 10px; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">Typography & Alignment Controls</label>
              <div class="format-toolbar">
                <select id="live-font-select" class="form-select" style="font-size:10px; height:24px; padding:1px 3px; max-width:90px;">
                  <option value="Arial">Arial</option>
                  <option value="Helvetica">Helvetica</option>
                  <option value="Times New Roman">Times New Roman</option>
                  <option value="Courier New">Courier</option>
                  <option value="Calibri">Calibri</option>
                </select>
                <input id="live-size-input" class="form-input" type="number" value="11" min="6" max="72" style="width:44px; font-size:10px; height:24px; padding:1px 3px;" title="Font size (pt)" />
                <button type="button" class="format-btn-toggle" id="btn-bold" title="Bold">B</button>
                <button type="button" class="format-btn-toggle" id="btn-italic" title="Italic"><em>I</em></button>
                <button type="button" class="format-btn-toggle" id="btn-underline" title="Underline"><u>U</u></button>
                <button type="button" class="format-btn-toggle" id="btn-align-left" title="Align Left">⇤</button>
                <button type="button" class="format-btn-toggle" id="btn-align-center" title="Align Center">⇥⇤</button>
                <button type="button" class="format-btn-toggle" id="btn-align-right" title="Align Right">⇥</button>
              </div>
            </div>
          ` : ""}

          <div style="display: flex; gap: 5px; margin-top: 8px; flex-wrap: wrap;">
            <button class="btn btn-primary btn-sm" id="btn-live-save" style="flex: 1; min-width: 60px;">💾 Save</button>
            <button class="btn btn-secondary btn-sm" id="btn-live-apply-sugg" style="flex: 1; min-width: 90px;">✓ Apply</button>
            <button class="btn btn-secondary btn-sm" id="btn-live-undo" title="Undo latest edit" ${this.editChanges.length === 0 ? "disabled" : ""}>↶</button>
            <button class="btn btn-secondary btn-sm" id="btn-live-cancel" title="Exit live rectification">✕</button>
          </div>
          <div style="font-size: 9.5px; color: var(--text-muted); margin-top: 5px; line-height: 1.35; word-break: break-word;">
            Autosaves directly to session working copy. Original file remains protected.
          </div>
        </div>
      `;
    }

    drawerContent.innerHTML = `
      <!-- Header: ID, Category, Severity, Status -->
      <div style="display: flex; align-items: flex-start; justify-content: space-between; gap: 6px; min-width: 0; max-width: 100%; box-sizing: border-box;">
        <div style="min-width: 0; flex: 1;">
          <div style="font-size: 14px; font-weight: 800; color: var(--text-primary); letter-spacing: 0.3px; word-break: break-word; overflow-wrap: anywhere;">${f.finding_id}</div>
          <div style="font-size: 11px; color: var(--text-muted); margin-top: 1px; word-break: break-word; overflow-wrap: anywhere;">Page ${f.page_number || f.page} • ${escapeHtml(f.location || "Document Content")}</div>
        </div>
        <div style="display: flex; gap: 4px; align-items: center; flex-wrap: wrap; justify-content: flex-end; flex-shrink: 0;">
          <span class="badge ${isExact ? 'badge-success' : 'badge-outline'}" style="font-size: 9px; padding: 1px 5px;">${escapeHtml(precision)}</span>
          <span class="badge ${sevClass}" style="font-size: 9.5px; padding: 1px 5px;">${f.severity}</span>
          ${statusPill}
        </div>
      </div>

      <!-- PROBLEM Card -->
      <div class="finding-prop-group" style="margin-top: 4px; min-width: 0; max-width: 100%;">
        <span class="finding-prop-label">PROBLEM (CURRENT VALUE)</span>
        <div class="finding-prop-code" style="border-left: 3px solid var(--sev-critical); background: rgba(220, 38, 38, 0.06); word-break: break-word; overflow-wrap: anywhere; white-space: pre-wrap; max-width: 100%; box-sizing: border-box;">
          ${escapeHtml(currentText)}
        </div>
      </div>

      <!-- SUGGESTED CORRECTION Card -->
      <div class="finding-prop-group" style="min-width: 0; max-width: 100%;">
        <span class="finding-prop-label">SUGGESTED CORRECTION</span>
        <div class="finding-prop-code" style="border-left: 3px solid #10b981; color: #047857; background: rgba(16, 185, 129, 0.08); font-weight: 600; word-break: break-word; overflow-wrap: anywhere; white-space: pre-wrap; max-width: 100%; box-sizing: border-box;">
          ${escapeHtml(suggestedText)}
        </div>
      </div>

      <!-- REASON Card -->
      <div class="finding-prop-group" style="min-width: 0; max-width: 100%;">
        <span class="finding-prop-label">REASON & TECHNICAL STANDARD</span>
        <p class="finding-prop-value" style="font-size: 11.5px; line-height: 1.45; margin: 0; color: var(--text-secondary); word-break: break-word; overflow-wrap: anywhere;">
          ${escapeHtml(reasonText)}
        </p>
        <span style="font-size: 10.5px; color: var(--text-muted); font-family: var(--font-mono); margin-top: 3px; word-break: break-word; overflow-wrap: anywhere; display: block;">
          Reference: ${escapeHtml(ruleRef)}
        </span>
      </div>

      <!-- Main Action Buttons -->
      ${!this.liveRectifyMode ? `
        <div style="display: flex; gap: 6px; margin-top: 4px; min-width: 0; flex-wrap: wrap;">
          <button class="btn btn-primary btn-sm" id="viewer-btn-apply-suggested" style="flex: 1; min-width: 110px; padding: 6px 8px; font-weight: 700;">
            ✓ Apply Suggested
          </button>
          <button class="btn btn-secondary btn-sm" id="viewer-btn-start-rectify" style="flex: 1; min-width: 90px; padding: 6px 8px; font-weight: 700;">
            ✏️ Live Rectify
          </button>
        </div>
      ` : ""}

      <!-- Live Rectification Workstation Interface (if active) -->
      ${workstationEditorHtml}
    `;

    // Bind Apply Suggested button
    const applySuggBtn = drawerContent.querySelector("#viewer-btn-apply-suggested");
    if (applySuggBtn) {
      applySuggBtn.onclick = () => this.applySuggestedCorrection(f);
    }

    // Bind Start Live Rectify button
    const startRectifyBtn = drawerContent.querySelector("#viewer-btn-start-rectify");
    if (startRectifyBtn) {
      startRectifyBtn.onclick = () => {
        this.liveRectifyMode = true;
        this.showFindingInDrawer(f);
      };
    }

    // Bind Live Editor controls if in Live Rectify Mode
    if (this.liveRectifyMode) {
      const textarea = drawerContent.querySelector("#live-editor-textarea");
      const saveBtn = drawerContent.querySelector("#btn-live-save");
      const liveApplySugg = drawerContent.querySelector("#btn-live-apply-sugg");
      const liveUndo = drawerContent.querySelector("#btn-live-undo");
      const liveCancel = drawerContent.querySelector("#btn-live-cancel");

      if (textarea) {
        textarea.focus();
        textarea.oninput = () => {
          this._handleDebouncedAutosave(f, textarea.value);
        };
      }

      if (saveBtn) {
        saveBtn.onclick = () => {
          const val = textarea ? textarea.value : suggestedText;
          this.saveManualCorrection(f, val);
        };
      }

      if (liveApplySugg) {
        liveApplySugg.onclick = () => this.applySuggestedCorrection(f);
      }

      if (liveUndo) {
        liveUndo.onclick = () => this.undoLastCorrection();
      }

      if (liveCancel) {
        liveCancel.onclick = () => {
          this.liveRectifyMode = false;
          this.showFindingInDrawer(f);
        };
      }

      // Formatting toggle buttons
      drawerContent.querySelectorAll(".format-btn-toggle").forEach((btn) => {
        btn.onclick = () => {
          btn.classList.toggle("active");
          this._handleDebouncedAutosave(f, textarea ? textarea.value : suggestedText);
        };
      });
    }
  }

  _handleDebouncedAutosave(finding, value) {
    const indicator = this.container.querySelector("#live-save-indicator");
    if (indicator) {
      indicator.textContent = "● Editing...";
      indicator.style.color = "var(--text-muted)";
    }

    if (this.autosaveTimer) {
      clearTimeout(this.autosaveTimer);
    }

    this.autosaveTimer = setTimeout(() => {
      this.saveManualCorrection(finding, value, true);
    }, 750);
  }

  async saveManualCorrection(finding, value, isAutosave = false) {
    const sessionId = window.appState.get("activeSessionId");
    if (!sessionId) {
      window.toast.error("No active session found for live rectification.");
      return;
    }

    const indicator = this.container.querySelector("#live-save-indicator");
    if (indicator) {
      indicator.textContent = "⏳ Saving...";
      indicator.style.color = "var(--accent-primary)";
    }

    try {
      this.editSaving = true;
      const isNumber = !isNaN(parseFloat(value)) && isFinite(value);
      const field = isNumber ? "font_size" : "text";

      const payload = {
        finding_id: finding.finding_id,
        operation: isNumber ? "format" : "text",
        field: field,
        value: value,
        note: isAutosave ? "Live autosave modification" : "Manual user rectification"
      };

      const res = await window.api.editor.apply(sessionId, payload);
      this.editRevision = res.revision || (this.editRevision + 1);
      this.editChanges = res.changes || this.editChanges;

      if (indicator) {
        indicator.textContent = `✓ Saved (Rev ${this.editRevision})`;
        indicator.style.color = "#059669";
      }

      const revBadge = this.container.querySelector("#drawer-rev-count");
      if (revBadge) revBadge.textContent = this.editRevision;

      window.toast.success(`Change saved (${res.change?.change_id || 'CHG'}). Revision ${this.editRevision}.`);
      this.renderPageCanvas();
    } catch (err) {
      console.error("Autosave failure:", err);
      if (indicator) {
        indicator.innerHTML = `⚠ Save failed <button class="btn btn-secondary btn-sm" style="padding:1px 4px; font-size:9px;" onclick="window.currentViewer && window.currentViewer.saveManualCorrection(window.currentViewer.focusedFinding, '${escapeHtml(value)}')">Retry</button>`;
        indicator.style.color = "#dc2626";
      }
      window.toast.error(`Autosave failed: ${err.message}`);
    } finally {
      this.editSaving = false;
    }
  }

  async applySuggestedCorrection(finding) {
    const sessionId = window.appState.get("activeSessionId");
    if (!sessionId) {
      window.toast.error("No active session found for live rectification.");
      return;
    }

    try {
      this.editSaving = true;
      const payload = {
        finding_id: finding.finding_id,
        operation: "suggested",
        field: "auto",
        value: null,
        note: "Applied recommended correction"
      };

      const res = await window.api.editor.apply(sessionId, payload);
      this.editRevision = res.revision || (this.editRevision + 1);
      this.editChanges = res.changes || this.editChanges;

      const revBadge = this.container.querySelector("#drawer-rev-count");
      if (revBadge) revBadge.textContent = this.editRevision;

      window.toast.success(`Suggested correction applied (${res.change?.change_id || 'CHG'}). Revision ${this.editRevision}.`);
      this.renderPageCanvas();
      this.showFindingInDrawer(finding);
    } catch (err) {
      window.toast.error(`Could not apply suggestion: ${err.message}`);
    } finally {
      this.editSaving = false;
    }
  }

  async undoLastCorrection() {
    const sessionId = window.appState.get("activeSessionId");
    if (!sessionId) return;

    try {
      const res = await window.api.editor.undo(sessionId);
      this.editRevision = res.revision || 0;
      this.editChanges = res.changes || [];

      const revBadge = this.container.querySelector("#drawer-rev-count");
      if (revBadge) revBadge.textContent = this.editRevision;

      window.toast.info(`Reverted change ${res.reverted_change?.change_id || ''}. Now at Revision ${this.editRevision}.`);
      this.renderPageCanvas();
      if (this.focusedFinding) {
        this.showFindingInDrawer(this.focusedFinding);
      }
    } catch (err) {
      window.toast.error(`Undo failed: ${err.message}`);
    }
  }

  renderHistoryContent() {
    const drawerContent = this.container.querySelector("#viewer-drawer-content");
    if (!drawerContent) return;

    if (!this.editChanges || this.editChanges.length === 0) {
      drawerContent.innerHTML = `
        <div class="empty-state" style="padding: 24px; text-align: center;">
          <div style="font-size: 28px; margin-bottom: 8px;">⏱</div>
          <div style="font-size: 14px; font-weight: 800; color: var(--text-primary);">No Changes Recorded</div>
          <div style="font-size: 11.5px; color: var(--text-muted); margin-top: 4px;">
            Applied rectifications and edits will appear in this persistent change log.
          </div>
        </div>
      `;
      return;
    }

    const itemsHtml = this.editChanges.slice().reverse().map((c) => {
      const isUndone = c.status === "UNDONE";
      const statusBadge = isUndone
        ? `<span class="badge badge-danger" style="font-size:9px;">Reverted</span>`
        : `<span class="badge badge-success" style="font-size:9px;">✓ Applied</span>`;

      return `
        <div class="history-item" data-finding-id="${c.finding_id}" data-page="${c.page || 1}">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-weight: 800; font-size: 11.5px; color: var(--accent-primary);">${c.change_id} • Page ${c.page || 1}</span>
            ${statusBadge}
          </div>
          <div style="font-size: 11px; color: var(--text-muted); margin-top: 1px;">
            ${c.finding_id} • <code>${c.operation} (${c.field})</code>
          </div>
          <div style="font-size: 11px; margin-top: 3px; background: var(--bg-surface-sunken); padding: 4px 6px; border-radius: 3px; font-family: var(--font-mono); word-break: break-all;">
            <span style="color: #dc2626;">${escapeHtml(String(c.before || '—'))}</span> → <span style="color: #059669; font-weight: 700;">${escapeHtml(String(c.after || '—'))}</span>
          </div>
          <div style="font-size: 9.5px; color: var(--text-muted); margin-top: 2px;">
            ${new Date(c.timestamp).toLocaleTimeString()}
          </div>
        </div>
      `;
    }).join("");

    drawerContent.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <span style="font-size: 12px; font-weight: 800; color: var(--text-primary); text-transform: uppercase;">Revision Change Log</span>
        <button class="btn btn-secondary btn-sm" id="btn-history-undo" ${this.editChanges.length === 0 ? "disabled" : ""} style="padding: 2px 7px; font-size: 10px;">↶ Undo Latest</button>
      </div>
      <div style="display: flex; flex-direction: column; gap: 4px;">
        ${itemsHtml}
      </div>
    `;

    const undoBtn = drawerContent.querySelector("#btn-history-undo");
    if (undoBtn) {
      undoBtn.onclick = () => this.undoLastCorrection();
    }

    drawerContent.querySelectorAll(".history-item").forEach((el) => {
      el.onclick = () => {
        const pageNum = parseInt(el.getAttribute("data-page"), 10) || 1;
        const findingId = el.getAttribute("data-finding-id");
        if (pageNum !== this.currentPage) {
          this.setPage(pageNum);
        }
        if (findingId) {
          this.focusFindingById(findingId);
        }
      };
    });
  }

  updateToolbar() {
    const counter = this.container.querySelector("#viewer-page-counter");
    if (counter) counter.textContent = `Page ${this.currentPage} of ${this.totalPages}`;

    const zoomLbl = this.container.querySelector("#viewer-zoom-label");
    if (zoomLbl) zoomLbl.textContent = `${Math.round(this.zoomLevel * 100)}%`;

    const fitPageBtn = this.container.querySelector("#viewer-fit-page");
    if (fitPageBtn) fitPageBtn.classList.toggle("active", this.zoomMode === "fit-page");

    const fitWidthBtn = this.container.querySelector("#viewer-fit-width");
    if (fitWidthBtn) fitWidthBtn.classList.toggle("active", this.zoomMode === "fit-width");

    const btnPrev = this.container.querySelector("#viewer-btn-prev");
    if (btnPrev) btnPrev.disabled = this.currentPage <= 1;

    const btnNext = this.container.querySelector("#viewer-btn-next");
    if (btnNext) btnNext.disabled = this.currentPage >= this.totalPages;

    const issueCounter = this.container.querySelector("#viewer-issue-counter");
    const jumpBtn = this.container.querySelector("#viewer-btn-jump");
    const zoomIssueBtn = this.container.querySelector("#viewer-btn-zoom-issue");
    const filteredList = this.getFilteredFindings();

    if (issueCounter) {
      if (this.focusedFinding) {
        const curIdx = filteredList.findIndex((f) => f.finding_id === this.focusedFinding.finding_id);
        issueCounter.textContent = `Issue ${curIdx >= 0 ? curIdx + 1 : '1'} of ${filteredList.length}`;
        if (jumpBtn) jumpBtn.style.display = "inline-flex";
        if (zoomIssueBtn) zoomIssueBtn.style.display = "inline-flex";
      } else {
        issueCounter.textContent = `${filteredList.length} Issues`;
        if (jumpBtn) jumpBtn.style.display = "none";
        if (zoomIssueBtn) zoomIssueBtn.style.display = "none";
      }
    }
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

window.DocumentViewerComponent = DocumentViewerComponent;
