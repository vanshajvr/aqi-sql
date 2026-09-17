document.addEventListener("DOMContentLoaded", () => {
  // Scoped per .subtabs group (by its parent container) rather than
  // globally, so Station Analysis's sub-nav and the Live section's
  // sub-nav - which share the same .subtab-btn/.subtab-content classes -
  // don't interfere with each other.
  document.querySelectorAll(".subtabs").forEach((subtabsBar) => {
    const buttons = Array.from(subtabsBar.querySelectorAll(".subtab-btn"));
    const parent = subtabsBar.parentElement;
    const contents = Array.from(parent.querySelectorAll(":scope > .subtab-content"));
    if (!buttons.length) return;

    function activateSubtab(btn) {
      buttons.forEach(b => {
        b.classList.remove("active");
        b.setAttribute("aria-selected", "false");
        b.tabIndex = -1;
      });
      contents.forEach(c => c.classList.remove("active"));

      btn.classList.add("active");
      btn.setAttribute("aria-selected", "true");
      btn.tabIndex = 0;
      btn.focus();

      const shown = document.getElementById("subtab-" + btn.dataset.subtab);
      if (!shown) return;
      shown.classList.add("active");

      shown.querySelectorAll(".plotly-graph-div").forEach(div => {
        if (window.Plotly) Plotly.Plots.resize(div);
      });

      if (btn.dataset.subtab === "compare" && window.renderCompareChart) {
        requestAnimationFrame(() => window.renderCompareChart());
      }
      if (btn.dataset.subtab === "live-map" && window.initLiveMap) {
        requestAnimationFrame(() => window.initLiveMap());
      }
    }

    buttons.forEach((btn, i) => {
      btn.tabIndex = btn.classList.contains("active") ? 0 : -1;
      btn.addEventListener("click", () => activateSubtab(btn));

      btn.addEventListener("keydown", (e) => {
        let target = null;
        if (e.key === "ArrowRight" || e.key === "ArrowDown") {
          target = buttons[(i + 1) % buttons.length];
        } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
          target = buttons[(i - 1 + buttons.length) % buttons.length];
        } else if (e.key === "Home") {
          target = buttons[0];
        } else if (e.key === "End") {
          target = buttons[buttons.length - 1];
        }
        if (target) {
          e.preventDefault();
          activateSubtab(target);
        }
      });
    });
  });
});