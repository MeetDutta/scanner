/**
 * Interactive Document Viewer Canvas Component for SpecGuard
 * Renders high-DPI document pages locally via PyMuPDF image endpoints,
 * overlays color-coded vector bounding box findings, and handles pan/zoom/finding navigation.
 */

class DocumentViewerComponent {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.docId = null;
    this.currentPage = 1;
    this.totalPages = 1;
    this.zoomLevel = 1.25;
    this.findings = [];
    this.focusedFinding = null;
    this.pageWidth = 612;
    this.pageHeight = 792;
    this.onFindingSelected = null;
  }

  async loadDocument(docId, totalPages = 1, findings = []) {
    this.docId = docId;
    this.totalPages = totalPages;
    this.currentPage = 1;
    this.findings = findings;
    this.activeTab = "pages";
    this.docDetails = null;
    this.render();
    try {
      this.docDetails = await window.api.documents.get(docId);
      if (this.docDetails && this.docDetails.page_count) {
        this.totalPages = this.docDetails.page_count;
      }
      this.renderSidebarContent();
      this.updateToolbar();
    } catch (e) {
      console.warn("Could not fetch document AST:", e);
    }
  }

  setPage(pageNum) {
    if (pageNum < 1 || pageNum > this.totalPages) return;
    this.currentPage = pageNum;
    this.renderPageCanvas();
    this.updateToolbar();
    this.renderSidebarContent();
  }

  setZoom(zoom) {
    this.zoomLevel = Math.max(0.5, Math.min(3.0, zoom));
    this.renderPageCanvas();
    this.updateToolbar();
  }

  focusFinding(finding) {
    this.focusedFinding = finding;
    if (finding.page && finding.page !== this.currentPage) {
      this.currentPage = finding.page;
    }
    this.renderPageCanvas();
    this.updateToolbar();
    this.renderSidebarContent();

    // Scroll canvas to center finding
    if (finding.bbox) {
      setTimeout(() => {
        const rectEl = this.container.querySelector(`[data-finding-id="${finding.finding_id}"]`);
        if (rectEl) {
          rectEl.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
        }
      }, 50);
    }
  }

  render() {
    if (!this.container) return;

    this.container.innerHTML = `
      <div class="viewer-layout">
        <!-- LEFT: Page Navigation Sidebar with Multi-Page Tabs -->
        <div class="viewer-pages-sidebar">
          <div class="viewer-sidebar-tabs" style="display: flex; border-bottom: 1px solid var(--border-default); background: var(--bg-surface-sunken);">
            <button class="v-tab ${this.activeTab === 'pages' ? 'active' : ''}" data-tab="pages" style="flex: 1; padding: 7px 2px; font-size: 11px; font-weight: 700; border: none; background: transparent; cursor: pointer; color: ${this.activeTab === 'pages' ? 'var(--accent-primary)' : 'var(--text-muted)'}; border-bottom: 2px solid ${this.activeTab === 'pages' ? 'var(--accent-primary)' : 'transparent'};">Pages</button>
            <button class="v-tab ${this.activeTab === 'structure' ? 'active' : ''}" data-tab="structure" style="flex: 1; padding: 7px 2px; font-size: 11px; font-weight: 700; border: none; background: transparent; cursor: pointer; color: ${this.activeTab === 'structure' ? 'var(--accent-primary)' : 'var(--text-muted)'}; border-bottom: 2px solid ${this.activeTab === 'structure' ? 'var(--accent-primary)' : 'transparent'};">Tree</button>
            <button class="v-tab ${this.activeTab === 'toc' ? 'active' : ''}" data-tab="toc" style="flex: 1; padding: 7px 2px; font-size: 11px; font-weight: 700; border: none; background: transparent; cursor: pointer; color: ${this.activeTab === 'toc' ? 'var(--accent-primary)' : 'var(--text-muted)'}; border-bottom: 2px solid ${this.activeTab === 'toc' ? 'var(--accent-primary)' : 'transparent'};">TOC</button>
            <button class="v-tab ${this.activeTab === 'assets' ? 'active' : ''}" data-tab="assets" style="flex: 1; padding: 7px 2px; font-size: 11px; font-weight: 700; border: none; background: transparent; cursor: pointer; color: ${this.activeTab === 'assets' ? 'var(--accent-primary)' : 'var(--text-muted)'}; border-bottom: 2px solid ${this.activeTab === 'assets' ? 'var(--accent-primary)' : 'transparent'};">Assets</button>
            <button class="v-tab ${this.activeTab === 'xrefs' ? 'active' : ''}" data-tab="xrefs" style="flex: 1; padding: 7px 2px; font-size: 11px; font-weight: 700; border: none; background: transparent; cursor: pointer; color: ${this.activeTab === 'xrefs' ? 'var(--accent-primary)' : 'var(--text-muted)'}; border-bottom: 2px solid ${this.activeTab === 'xrefs' ? 'var(--accent-primary)' : 'transparent'};">Refs</button>
          </div>
          <div class="pages-list" id="viewer-pages-list" style="overflow-y: auto; flex: 1; padding: 6px;"></div>
        </div>

        <!-- CENTER: Canvas Viewport -->
        <div class="viewer-center-pane">
          <div class="viewer-toolbar">
            <div style="display: flex; align-items: center; gap: 8px;">
              <button class="btn btn-secondary btn-sm" id="viewer-btn-prev">← Prev</button>
              <span id="viewer-page-counter" style="font-size: 12px; font-weight: 700; color: var(--text-primary);">
                Page 1 of 1
              </span>
              <button class="btn btn-secondary btn-sm" id="viewer-btn-next">Next →</button>
            </div>

            <div style="display: flex; align-items: center; gap: 8px;">
              <button class="btn btn-secondary btn-sm" id="viewer-zoom-out" title="Zoom Out">−</button>
              <span id="viewer-zoom-label" style="font-size: 12px; font-weight: 700; min-width: 44px; text-align: center;">125%</span>
              <button class="btn btn-secondary btn-sm" id="viewer-zoom-in" title="Zoom In">+</button>
              <button class="btn btn-secondary btn-sm" id="viewer-fit-width">Fit Width</button>
              <button class="btn btn-secondary btn-sm" id="viewer-fit-page">Fit Page</button>
            </div>
          </div>

          <div class="canvas-viewport" id="viewer-canvas-viewport">
            <div class="page-canvas-wrapper" id="viewer-page-wrapper">
              <img class="page-canvas-image" id="viewer-page-img" alt="Document Page" />
              <svg class="page-overlay-svg" id="viewer-overlay-svg" xmlns="http://www.w3.org/2000/svg"></svg>
            </div>
          </div>
        </div>

        <!-- RIGHT: Finding Details Drawer -->
        <div class="viewer-detail-drawer" id="viewer-detail-drawer">
          <div class="drawer-header">
            <span style="font-size: 12px; font-weight: 800; color: var(--text-primary); letter-spacing: 0.5px;">FINDING DETAILS</span>
            <button class="btn btn-secondary btn-sm" id="viewer-drawer-close" style="padding: 2px 6px;">✕</button>
          </div>
          <div class="drawer-content" id="viewer-drawer-content">
            <div class="empty-state" style="padding: 24px;">
              <div class="empty-state-icon">🔍</div>
              <div class="empty-state-title">No Finding Selected</div>
              <div class="empty-state-desc">Click any highlighted box on the document canvas to inspect details.</div>
            </div>
          </div>
        </div>
      </div>
    `;

    this._bindEvents();
    this.renderPageList();
    this.renderPageCanvas();
    this.updateToolbar();
  }

  _bindEvents() {
    this.container.querySelector("#viewer-btn-prev").onclick = () => this.setPage(this.currentPage - 1);
    this.container.querySelector("#viewer-btn-next").onclick = () => this.setPage(this.currentPage + 1);
    this.container.querySelector("#viewer-zoom-out").onclick = () => this.setZoom(this.zoomLevel - 0.25);
    this.container.querySelector("#viewer-zoom-in").onclick = () => this.setZoom(this.zoomLevel + 0.25);

    this.container.querySelector("#viewer-fit-width").onclick = () => {
      const viewport = this.container.querySelector("#viewer-canvas-viewport");
      if (viewport && this.pageWidth > 0) {
        const availableW = viewport.clientWidth - 48;
        this.setZoom(availableW / this.pageWidth);
      }
    };

    this.container.querySelector("#viewer-fit-page").onclick = () => {
      const viewport = this.container.querySelector("#viewer-canvas-viewport");
      if (viewport && this.pageHeight > 0) {
        const availableH = viewport.clientHeight - 48;
        this.setZoom(availableH / this.pageHeight);
      }
    };

    this.container.querySelector("#viewer-drawer-close").onclick = () => {
      this.closeDrawer();
    };
    this.container.querySelectorAll(".v-tab").forEach((tabBtn) => {
      tabBtn.onclick = () => {
        this.activeTab = tabBtn.getAttribute("data-tab");
        this.container.querySelectorAll(".v-tab").forEach((b) => {
          const isActive = b.getAttribute("data-tab") === this.activeTab;
          b.style.color = isActive ? "var(--accent-primary)" : "var(--text-muted)";
          b.style.borderBottom = isActive ? "2px solid var(--accent-primary)" : "transparent";
        });
        this.renderSidebarContent();
      };
    });
  }

  renderSidebarContent() {
    const listEl = this.container.querySelector("#viewer-pages-list");
    if (!listEl) return;
    listEl.innerHTML = "";

    if (this.activeTab === "pages") {
      for (let i = 1; i <= this.totalPages; i++) {
        const findingsOnPage = this.findings.filter((f) => f.page === i);
        const item = document.createElement("div");
        item.className = `page-thumb-item ${i === this.currentPage ? "active" : ""}`;
        item.innerHTML = `
          <span>Page ${i}</span>
          ${findingsOnPage.length > 0 ? `<span class="badge badge-critical" style="font-size: 9.5px; padding: 1px 5px;">${findingsOnPage.length}</span>` : ""}
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
        item.style.cssText = `padding: 6px 8px; font-size: 11px; cursor: pointer; border-radius: var(--radius-sm); margin-bottom: 2px; display: flex; justify-content: space-between; align-items: center; background: ${sec.page_num === this.currentPage ? 'var(--bg-surface-elevated)' : 'transparent'}; border-left: ${sec.level === 1 ? '3px solid var(--accent-primary)' : '1px solid var(--border-default)'}; margin-left: ${(sec.level - 1) * 10}px;`;
        item.innerHTML = `
          <span style="font-weight: ${sec.level === 1 ? '700' : '500'}; color: var(--text-primary); text-overflow: ellipsis; overflow: hidden; white-space: nowrap; max-width: 140px;">
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
          <span style="font-weight: ${item.level === 1 ? '700' : '500'}; text-overflow: ellipsis; overflow: hidden; white-space: nowrap; max-width: 140px;">${item.title}</span>
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
        figures.forEach((f) => {
          const el = document.createElement("div");
          el.style.cssText = "padding: 5px 8px; font-size: 11px; cursor: pointer; border-radius: var(--radius-sm); margin-bottom: 2px; display: flex; justify-content: space-between; align-items: center;";
          el.innerHTML = `<span>📊 ${f.label || 'Figure'}</span><span class="badge badge-outline" style="font-size: 9px;">P.${f.page_num}</span>`;
          el.onclick = () => this.setPage(f.page_num);
          listEl.appendChild(el);
        });
      }

      if (tables.length > 0) {
        addAssetHeader(`Tables (${tables.length})`);
        tables.forEach((t) => {
          const el = document.createElement("div");
          el.style.cssText = "padding: 5px 8px; font-size: 11px; cursor: pointer; border-radius: var(--radius-sm); margin-bottom: 2px; display: flex; justify-content: space-between; align-items: center;";
          el.innerHTML = `<span>📋 ${t.label || 'Table'}</span><span class="badge badge-outline" style="font-size: 9px;">P.${t.page_num}</span>`;
          el.onclick = () => this.setPage(t.page_num);
          listEl.appendChild(el);
        });
      }

      if (equations.length > 0) {
        addAssetHeader(`Equations (${equations.length})`);
        equations.forEach((eq) => {
          const el = document.createElement("div");
          el.style.cssText = "padding: 5px 8px; font-size: 11px; cursor: pointer; border-radius: var(--radius-sm); margin-bottom: 2px; display: flex; justify-content: space-between; align-items: center;";
          el.innerHTML = `<span>∑ ${eq.label || 'Equation'}</span><span class="badge badge-outline" style="font-size: 9px;">P.${eq.page_num}</span>`;
          el.onclick = () => this.setPage(eq.page_num);
          listEl.appendChild(el);
        });
      }
    } else if (this.activeTab === "xrefs") {
      const xrefs = this.docDetails?.cross_references || [];
      if (xrefs.length === 0) {
        listEl.innerHTML = `<div style="padding: 12px; font-size: 11.5px; color: var(--text-muted);">No cross-references detected.</div>`;
        return;
      }
      xrefs.forEach((xr) => {
        const el = document.createElement("div");
        el.style.cssText = "padding: 5px 8px; font-size: 11px; cursor: pointer; border-radius: var(--radius-sm); margin-bottom: 2px; display: flex; justify-content: space-between; align-items: center;";
        el.innerHTML = `
          <span style="font-weight: 600;">${xr.mention_text}</span>
          <span class="badge ${xr.is_resolved ? 'badge-success' : 'badge-danger'}" style="font-size: 8.5px;">
            ${xr.is_resolved ? '✓ OK' : '⚠ Broken'} (P.${xr.source_page})
          </span>
        `;
        el.onclick = () => this.setPage(xr.source_page);
        listEl.appendChild(el);
      });
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

    const imgUrl = window.api.documents.getPageImageUrl(this.docId, this.currentPage, this.zoomLevel);

    imgEl.onload = () => {
      // Set SVG dimensions matching loaded image natural size
      svgEl.setAttribute("viewBox", `0 0 ${imgEl.naturalWidth} ${imgEl.naturalHeight}`);
      svgEl.setAttribute("width", imgEl.naturalWidth);
      svgEl.setAttribute("height", imgEl.naturalHeight);
      this.renderHighlights(imgEl.naturalWidth, imgEl.naturalHeight);
    };

    imgEl.src = imgUrl;
    this.renderPageList();
  }

  renderHighlights(renderedWidth, renderedHeight) {
    const svgEl = this.container.querySelector("#viewer-overlay-svg");
    if (!svgEl) return;
    svgEl.innerHTML = "";

    const findingsOnPage = this.findings.filter((f) => f.page === this.currentPage && f.bbox);
    const rx = renderedWidth / this.pageWidth;
    const ry = renderedHeight / this.pageHeight;

    const severityColors = {
      Critical: { stroke: "#dc2626", fill: "rgba(220, 38, 38, 0.22)" },
      High: { stroke: "#ea580c", fill: "rgba(234, 88, 12, 0.22)" },
      Medium: { stroke: "#d97706", fill: "rgba(217, 119, 6, 0.20)" },
      Low: { stroke: "#2563eb", fill: "rgba(37, 99, 235, 0.18)" },
      Informational: { stroke: "#64748b", fill: "rgba(100, 116, 139, 0.15)" }
    };

    findingsOnPage.forEach((f) => {
      const bbox = f.bbox;
      const x = bbox.x0 * rx;
      const y = bbox.y0 * ry;
      const w = Math.max(8, (bbox.x1 - bbox.x0) * rx);
      const h = Math.max(8, (bbox.y1 - bbox.y0) * ry);

      const color = severityColors[f.severity] || severityColors.Medium;
      const isFocused = this.focusedFinding && this.focusedFinding.finding_id === f.finding_id;

      const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      rect.setAttribute("x", x);
      rect.setAttribute("y", y);
      rect.setAttribute("width", w);
      rect.setAttribute("height", h);
      rect.setAttribute("rx", "3");
      rect.setAttribute("ry", "3");
      rect.setAttribute("fill", color.fill);
      rect.setAttribute("stroke", color.stroke);
      rect.setAttribute("stroke-width", isFocused ? "3.5" : "2");
      rect.setAttribute("class", `finding-bbox-rect ${isFocused ? "focused" : ""}`);
      rect.setAttribute("data-finding-id", f.finding_id);

      // Tooltip
      const titleEl = document.createElementNS("http://www.w3.org/2000/svg", "title");
      titleEl.textContent = `[${f.severity}] ${f.finding_id}: ${f.category}\n${f.explanation}`;
      rect.appendChild(titleEl);

      rect.onclick = (e) => {
        e.stopPropagation();
        this.selectFinding(f);
      };

      svgEl.appendChild(rect);
    });
  }

  selectFinding(finding) {
    this.focusedFinding = finding;
    this.renderPageCanvas();
    this.showFindingInDrawer(finding);
    if (this.onFindingSelected) {
      this.onFindingSelected(finding);
    }
  }

  showFindingInDrawer(f) {
    const drawerContent = this.container.querySelector("#viewer-drawer-content");
    if (!drawerContent) return;

    const sevClass = `badge-${f.severity.toLowerCase()}`;

    drawerContent.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: space-between;">
        <span style="font-size: 14px; font-weight: 800; color: var(--text-primary);">${f.finding_id}</span>
        <span class="badge ${sevClass}">${f.severity}</span>
      </div>

      <div class="finding-prop-group">
        <span class="finding-prop-label">Category</span>
        <span class="finding-prop-value" style="font-weight: 600;">${f.category}</span>
      </div>

      <div class="finding-prop-group">
        <span class="finding-prop-label">Location / Section</span>
        <span class="finding-prop-value">Page ${f.page} • ${f.location || "General Text"}</span>
      </div>

      <div class="finding-prop-group">
        <span class="finding-prop-label">Detected Value / Phrase</span>
        <div class="finding-prop-code">${escapeHtml(String(f.detected_value || f.original_content || "N/A"))}</div>
      </div>

      <div class="finding-prop-group">
        <span class="finding-prop-label">Expected Engineering Spec</span>
        <div class="finding-prop-code" style="color: #10b981;">${escapeHtml(String(f.expected_value || "In accordance with standard"))}</div>
      </div>

      ${f.deviation ? `
        <div class="finding-prop-group">
          <span class="finding-prop-label">Deviation Magnitude</span>
          <span class="finding-prop-value" style="color: var(--sev-high); font-weight: 700;">${escapeHtml(f.deviation)}</span>
        </div>
      ` : ""}

      <div class="finding-prop-group">
        <span class="finding-prop-label">Technical Explanation</span>
        <p class="finding-prop-value" style="font-size: 12.5px; line-height: 1.45;">${escapeHtml(f.explanation || "No explanation provided.")}</p>
      </div>

      <div class="finding-prop-group">
        <span class="finding-prop-label">Remediation Guidance</span>
        <p class="finding-prop-value" style="color: var(--accent-primary); font-weight: 600;">
          💡 ${escapeHtml(f.suggested_correction || "Verify against domain guidelines.")}
        </p>
      </div>

      <div class="finding-prop-group">
        <span class="finding-prop-label">Engineering Standard Reference</span>
        <span class="finding-prop-value" style="font-size: 11.5px; color: var(--text-muted); font-family: var(--font-mono);">
          ${escapeHtml(f.rule_reference || "SpecGuard Core Rules")}
        </span>
      </div>

      <div style="margin-top: 10px; padding-top: 12px; border-top: 1px solid var(--border-subtle); display: flex; gap: 8px;">
        <button class="btn btn-secondary btn-sm" style="flex: 1;" onclick="window.toast.info('Finding marked as reviewed.')">Mark Reviewed</button>
      </div>
    `;

    const drawer = this.container.querySelector("#viewer-detail-drawer");
    if (drawer) drawer.classList.remove("hidden");
  }

  closeDrawer() {
    const drawer = this.container.querySelector("#viewer-detail-drawer");
    if (drawer) drawer.classList.add("hidden");
    this.focusedFinding = null;
    this.renderPageCanvas();
  }

  updateToolbar() {
    const counter = this.container.querySelector("#viewer-page-counter");
    if (counter) counter.textContent = `Page ${this.currentPage} of ${this.totalPages}`;

    const zoomLbl = this.container.querySelector("#viewer-zoom-label");
    if (zoomLbl) zoomLbl.textContent = `${Math.round(this.zoomLevel * 100)}%`;

    const btnPrev = this.container.querySelector("#viewer-btn-prev");
    if (btnPrev) btnPrev.disabled = this.currentPage <= 1;

    const btnNext = this.container.querySelector("#viewer-btn-next");
    if (btnNext) btnNext.disabled = this.currentPage >= this.totalPages;
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

window.DocumentViewerComponent = DocumentViewerComponent;
