document.addEventListener("DOMContentLoaded", () => {
  const buttons = document.querySelectorAll(".tab-btn");
  const contents = document.querySelectorAll(".tab-content");

  buttons.forEach(btn => {
    btn.addEventListener("click", () => {
      buttons.forEach(b => b.classList.remove("active"));
      contents.forEach(c => c.classList.remove("active"));

      btn.classList.add("active");
      const shown = document.getElementById("tab-" + btn.dataset.tab);
      shown.classList.add("active");

      shown.querySelectorAll(".plotly-graph-div").forEach(div => {
        if (window.Plotly) Plotly.Plots.resize(div);
      });

      if (btn.dataset.tab === "compare" && window.renderCompareChart) {
        requestAnimationFrame(() => window.renderCompareChart());
      }
    });
  });
});