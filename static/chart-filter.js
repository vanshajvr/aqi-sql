document.addEventListener("DOMContentLoaded", () => {
  const filterBtn = document.getElementById("chart-filter-btn");
  const filterMenu = document.getElementById("chart-filter-menu");
  const emptyState = document.getElementById("chart-empty-state");
  const checkboxes = document.querySelectorAll(".chart-toggle");
  if (!filterBtn || !filterMenu || !checkboxes.length) return;

  function closeMenu() {
    filterMenu.hidden = true;
    filterBtn.setAttribute("aria-expanded", "false");
  }

  function openMenu() {
    filterMenu.hidden = false;
    filterBtn.setAttribute("aria-expanded", "true");
  }

  filterBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    if (filterMenu.hidden) openMenu();
    else closeMenu();
  });

  document.addEventListener("click", (e) => {
    if (!filterMenu.hidden && !filterMenu.contains(e.target) && e.target !== filterBtn) {
      closeMenu();
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !filterMenu.hidden) closeMenu();
  });

  function applyVisibility() {
    let anyVisible = false;
    checkboxes.forEach((cb) => {
      const card = document.querySelector(`.card[data-chart="${cb.value}"]`);
      if (!card) return;
      if (cb.checked) {
        card.classList.remove("chart-hidden");
        anyVisible = true;
        card.querySelectorAll(".plotly-graph-div").forEach((div) => {
          if (window.Plotly) Plotly.Plots.resize(div);
        });
      } else {
        card.classList.add("chart-hidden");
      }
    });
    if (emptyState) emptyState.hidden = anyVisible;
  }

  checkboxes.forEach((cb) => cb.addEventListener("change", applyVisibility));

  applyVisibility();
});