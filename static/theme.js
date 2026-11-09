// Light / dark theme. Loaded in <head> without defer, so the theme is set
// before the page paints (no flash). The choice is saved per browser; with no
// saved choice the page follows the system setting.
//
// CSS reads the theme from :root[data-theme] (style.css tokens). Plotly charts
// are built in Python with dark colours, so they're recoloured here, and the
// MapLibre maps listen for the "themechange" event (see gl_base.js).
(function () {
  const KEY = "aqi-theme";
  const root = document.documentElement;

  function saved() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }
  function systemTheme() {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  }
  root.dataset.theme = saved() || systemTheme();

  // Colours the Python chart code hard-codes for text on a dark card
  const DARK_TEXT = new Set(["#c9d1d9", "#f0f6fc", "#e6edf3"]);

  function colors() {
    const cs = getComputedStyle(root);
    const v = (name) => cs.getPropertyValue(name).trim();
    return { bg: v("--bg"), surface: v("--surface"), surface2: v("--surface-2"), border: v("--border"), text: v("--text"),
             strong: v("--text-strong"), muted: v("--text-muted"), accent: v("--accent") };
  }

  function themeChart(gd) {
    if (!window.Plotly || !gd.layout) return;
    const c = colors();
    const update = { paper_bgcolor: c.surface, plot_bgcolor: c.surface, "font.color": c.text };
    Object.keys(gd.layout).forEach((k) => {
      if (/^[xy]axis\d*$/.test(k)) {
        update[`${k}.gridcolor`] = c.border;
        update[`${k}.linecolor`] = c.border;
        update[`${k}.zerolinecolor`] = c.border;
        const ax = gd.layout[k];
        if (ax.rangeslider && ax.rangeslider.visible) update[`${k}.rangeslider.bgcolor`] = c.surface2;
        if (ax.rangeselector) {
          update[`${k}.rangeselector.bgcolor`] = c.surface2;
          update[`${k}.rangeselector.font.color`] = c.text;
          update[`${k}.rangeselector.activecolor`] = c.accent;
        }
      }
    });
    // Remember which annotations / traces used light-on-dark text, once
    if (!gd._aqiText) {
      gd._aqiText = {
        annotations: (gd.layout.annotations || []).map((a, i) =>
          (a.font && a.font.color && DARK_TEXT.has(String(a.font.color).toLowerCase()) ? i : -1)).filter((i) => i >= 0),
        traces: (gd.data || []).map((t, i) =>
          (t.textfont && typeof t.textfont.color === "string" && DARK_TEXT.has(t.textfont.color.toLowerCase()) ? i : -1))
          .filter((i) => i >= 0),
      };
    }
    gd._aqiText.annotations.forEach((i) => { update[`annotations[${i}].font.color`] = c.text; });
    Plotly.relayout(gd, update);
    if (gd._aqiText.traces.length) Plotly.restyle(gd, { "textfont.color": c.text }, gd._aqiText.traces);
  }

  function themeAllCharts() {
    document.querySelectorAll(".js-plotly-plot").forEach(themeChart);
  }

  function updateButton() {
    const btn = document.getElementById("theme-toggle");
    if (!btn) return;
    const light = root.dataset.theme === "light";
    btn.setAttribute("aria-label", light ? "Switch to dark theme" : "Switch to light theme");
    btn.setAttribute("title", light ? "Dark theme" : "Light theme");
    btn.dataset.mode = root.dataset.theme;
  }

  function set(theme, persist) {
    root.dataset.theme = theme;
    if (persist) { try { localStorage.setItem(KEY, theme); } catch (e) { /* private mode */ } }
    updateButton();
    themeAllCharts();
    window.dispatchEvent(new CustomEvent("themechange", { detail: theme }));
  }

  window.AQITheme = {
    get: () => root.dataset.theme,
    colors,
    themeChart,
    toggle: () => set(root.dataset.theme === "light" ? "dark" : "light", true),
  };

  // Follow the system setting while the visitor hasn't chosen
  if (window.matchMedia) {
    window.matchMedia("(prefers-color-scheme: light)").addEventListener("change", () => {
      if (!saved()) set(systemTheme(), false);
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    updateButton();
    const btn = document.getElementById("theme-toggle");
    if (btn) btn.addEventListener("click", () => window.AQITheme.toggle());
  });
  // Charts finish drawing after DOMContentLoaded; recolour them once they have
  window.addEventListener("load", () => { if (root.dataset.theme === "light") themeAllCharts(); });
})();
