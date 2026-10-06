document.addEventListener("DOMContentLoaded", () => {
  const data = window.COMPARE_DATA || {};
  const selectA = document.getElementById("compare-a");
  const selectB = document.getElementById("compare-b");
  const chartDiv = document.getElementById("compare-chart");
  const statsDiv = document.getElementById("compare-stats");

  if (!selectA || !selectB || !chartDiv) return;

  function buildTrace(stationId, color) {
    const s = data[stationId];
    if (!s) return null;
    return {
      x: s.dates,
      y: s.rolling_30,
      mode: "lines",
      name: s.name,
      line: { color: color, width: 2 },
      connectgaps: false,
      hovertemplate: "<b>" + s.name + "</b><br>%{x|%d %b %Y}<br>30-day PM2.5: %{y:.0f} µg/m³<extra></extra>",
    };
  }

  function fmtChange(v) {
    if (v == null) return "no data";
    return `${v > 0 ? "+" : ""}${v}%`;
  }

  function statCard(s) {
    return `
      <div class="compare-stat-card">
        <div class="compare-stat-name">${s.name}</div>
        <div class="compare-stat-row"><span>PM2.5 2018&ndash;19</span><b>${s.pm25_then ?? "no data"}</b></div>
        <div class="compare-stat-row"><span>PM2.5 2025&ndash;26</span><b>${s.pm25_now ?? "no data"}</b></div>
        <div class="compare-stat-row"><span>Change (not weather-adjusted)</span><b>${fmtChange(s.change_pct)}</b></div>
        <div class="compare-stat-row"><span>Worst month on record</span><b>${s.worst_month ?? "&ndash;"}</b></div>
      </div>`;
  }

  function renderStats(idA, idB) {
    const a = data[idA], b = data[idB];
    if (!a || !b) return;
    statsDiv.innerHTML = statCard(a) + statCard(b);
  }

  function render() {
    const idA = selectA.value;
    const idB = selectB.value;
    const traces = [buildTrace(idA, "#58a6ff"), buildTrace(idB, "#f0883e")].filter(Boolean);

    const layout = {
      template: "plotly_dark",
      paper_bgcolor: "#161b22",
      plot_bgcolor: "#161b22",
      font: { family: "Inter, Helvetica, Arial, sans-serif", color: "#c9d1d9", size: 13 },
      margin: { l: 56, r: 36, t: 20, b: 56 },
      xaxis: { gridcolor: "#21262d", griddash: "dot", gridwidth: 1, zeroline: false },
      yaxis: { title: "30-day PM2.5 (µg/m³)", gridcolor: "#21262d", griddash: "dot", gridwidth: 1, zeroline: false, rangemode: "tozero" },
      shapes: [{ type: "rect", xref: "x", yref: "paper", x0: "2022-11-01", x1: "2025-02-01", y0: 0, y1: 1,
                 fillcolor: "rgba(110,118,129,0.12)", line: { width: 0 } }],
      legend: { orientation: "h", y: 1.1 },
      hovermode: "closest",
      hoverlabel: { bgcolor: "#1c2333", bordercolor: "#58a6ff", font: { color: "#ffffff", size: 12 } },
    };

    Plotly.react(chartDiv, traces, layout, { displaylogo: false, responsive: true });
    renderStats(idA, idB);
  }

  const swapBtn = document.getElementById("compare-swap");
  if (swapBtn) {
    swapBtn.addEventListener("click", () => {
      const tmp = selectA.value;
      selectA.value = selectB.value;
      selectB.value = tmp;
      swapBtn.classList.remove("spinning");
      void swapBtn.offsetWidth; // restart the animation if clicked repeatedly
      swapBtn.classList.add("spinning");
      render();
    });
  }

  selectA.addEventListener("change", render);
  selectB.addEventListener("change", render);
  window.renderCompareChart = render;
});