document.addEventListener("DOMContentLoaded", () => {
  const buttons = Array.from(document.querySelectorAll(".mode-btn"));
  const contents = document.querySelectorAll(".mode-content");
  if (!buttons.length) return;

  function activateMode(btn) {
    buttons.forEach(b => {
      b.classList.remove("active");
      b.setAttribute("aria-selected", "false");
    });
    contents.forEach(c => c.classList.remove("active"));

    btn.classList.add("active");
    btn.setAttribute("aria-selected", "true");

    const shown = document.getElementById("mode-" + btn.dataset.mode);
    if (!shown) return;
    shown.classList.add("active");

    shown.querySelectorAll(".plotly-graph-div").forEach(div => {
      if (window.Plotly) Plotly.Plots.resize(div);
    });

    // Live data is fetched lazily on first switch to Live mode, not on
    // page load - same reasoning as the historical map only initializing
    // on first click.
    if (btn.dataset.mode === "live" && window.initLiveData) {
      requestAnimationFrame(() => window.initLiveData());
    }
  }

  buttons.forEach((btn, i) => {
    btn.addEventListener("click", () => activateMode(btn));
    btn.addEventListener("keydown", (e) => {
      let target = null;
      if (e.key === "ArrowRight" || e.key === "ArrowDown") target = buttons[(i + 1) % buttons.length];
      else if (e.key === "ArrowLeft" || e.key === "ArrowUp") target = buttons[(i - 1 + buttons.length) % buttons.length];
      if (target) {
        e.preventDefault();
        activateMode(target);
        target.focus();
      }
    });
  });

  // Whichever mode is active by default on page load also needs its data
  // fetch triggered - activateMode() only runs on click, so the default
  // view would otherwise never load anything until the user clicks away
  // and back. Deferred scripts (including live.js) finish executing
  // before DOMContentLoaded fires, so window.initLiveData is guaranteed
  // to exist here.
  const defaultActive = buttons.find(b => b.classList.contains("active"));
  if (defaultActive && defaultActive.dataset.mode === "live" && window.initLiveData) {
    requestAnimationFrame(() => window.initLiveData());
  }
});