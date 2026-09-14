document.addEventListener("DOMContentLoaded", () => {
  const buttons = Array.from(document.querySelectorAll(".tab-btn"));
  const contents = document.querySelectorAll(".tab-content");

  function activateTab(btn) {
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

    const shown = document.getElementById("tab-" + btn.dataset.tab);
    shown.classList.add("active");

    shown.querySelectorAll(".plotly-graph-div").forEach(div => {
      if (window.Plotly) Plotly.Plots.resize(div);
    });

    if (btn.dataset.tab === "compare" && window.renderCompareChart) {
      requestAnimationFrame(() => window.renderCompareChart());
    }
  }

  buttons.forEach((btn, i) => {
    btn.tabIndex = btn.classList.contains("active") ? 0 : -1;

    btn.addEventListener("click", () => activateTab(btn));

    // WAI-ARIA tablist keyboard pattern: Left/Right (or Up/Down) moves
    // focus and activates the adjacent tab; Home/End jump to first/last.
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
        activateTab(target);
      }
    });
  });
});