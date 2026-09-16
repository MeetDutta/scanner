/**
 * Accessible Modal Controller for SpecGuard
 */

class ModalController {
  constructor() {
    this.overlay = document.getElementById("global-modal-overlay");
    if (!this.overlay) {
      this.overlay = document.createElement("div");
      this.overlay.id = "global-modal-overlay";
      this.overlay.className = "modal-overlay";
      this.overlay.innerHTML = `
        <div class="modal-dialog" role="dialog" aria-modal="true">
          <div class="modal-header">
            <h3 class="modal-title" id="global-modal-title">Modal Title</h3>
            <button class="modal-close" id="global-modal-close" aria-label="Close">✕</button>
          </div>
          <div class="modal-body" id="global-modal-body"></div>
          <div class="modal-footer" id="global-modal-footer"></div>
        </div>
      `;
      document.body.appendChild(this.overlay);

      this.titleEl = this.overlay.querySelector("#global-modal-title");
      this.bodyEl = this.overlay.querySelector("#global-modal-body");
      this.footerEl = this.overlay.querySelector("#global-modal-footer");
      this.closeBtn = this.overlay.querySelector("#global-modal-close");

      this.closeBtn.onclick = () => this.close();
      this.overlay.onclick = (e) => {
        if (e.target === this.overlay) this.close();
      };

      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && this.isOpen()) this.close();
      });
    }
  }

  isOpen() {
    return this.overlay.classList.contains("open");
  }

  open({ title, body, footerButtons = [] }) {
    this.titleEl.textContent = title;

    if (typeof body === "string") {
      this.bodyEl.innerHTML = body;
    } else if (body instanceof HTMLElement) {
      this.bodyEl.innerHTML = "";
      this.bodyEl.appendChild(body);
    }

    this.footerEl.innerHTML = "";
    if (footerButtons.length === 0) {
      footerButtons = [{ label: "Close", class: "btn-secondary", onClick: () => this.close() }];
    }

    footerButtons.forEach((b) => {
      const btn = document.createElement("button");
      btn.className = `btn ${b.class || "btn-secondary"}`;
      btn.textContent = b.label;
      btn.onclick = () => {
        if (b.onClick) b.onClick();
        if (b.closeOnClick !== false) this.close();
      };
      this.footerEl.appendChild(btn);
    });

    this.overlay.classList.add("open");
  }

  close() {
    this.overlay.classList.remove("open");
  }

  confirm({ title = "Confirm Action", message, confirmLabel = "Confirm", onConfirm, isDanger = false }) {
    this.open({
      title,
      body: `<p style="line-height: 1.5;">${message}</p>`,
      footerButtons: [
        { label: "Cancel", class: "btn-secondary", closeOnClick: true },
        {
          label: confirmLabel,
          class: isDanger ? "btn-danger" : "btn-primary",
          onClick: onConfirm,
          closeOnClick: true
        }
      ]
    });
  }
}

window.modal = new ModalController();
