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
      hovertemplate: "<b>" + s.name + "</b><br>%{x|%d %b %Y}<br>30d avg: %{y:.1f}<extra></extra>",
    };
  }

  function renderStats(idA, idB) {
    const a = data[idA], b = data[idB];
    if (!a || !b) return;
    statsDiv.innerHTML = `
      <div class="compare-stat-card">
        <div class="compare-stat-name">${a.name}</div>
        <div class="compare-stat-row"><span>Avg AQI</span><b>${a.avg_aqi}</b></div>
        <div class="compare-stat-row"><span>% Severe Days</span><b>${a.severe_pct}%</b></div>
        <div class="compare-stat-row"><span>Worst Month</span><b>${a.worst_month}</b></div>
      </div>
      <div class="compare-stat-card">
        <div class="compare-stat-name">${b.name}</div>
        <div class="compare-stat-row"><span>Avg AQI</span><b>${b.avg_aqi}</b></div>
        <div class="compare-stat-row"><span>% Severe Days</span><b>${b.severe_pct}%</b></div>
        <div class="compare-stat-row"><span>Worst Month</span><b>${b.worst_month}</b></div>
      </div>`;
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
      margin: { l: 50, r: 30, t: 20, b: 50 },
      xaxis: { gridcolor: "#21262d" },
      yaxis: { title: "30-day Avg AQI", gridcolor: "#21262d" },
      legend: { orientation: "h", y: 1.1 },
      hovermode: "closest",
      hoverlabel: { bgcolor: "#1c2333", bordercolor: "#58a6ff", font: { color: "#ffffff", size: 12 } },
    };

    Plotly.react(chartDiv, traces, layout, { displaylogo: false, responsive: true });
    renderStats(idA, idB);
  }

  selectA.addEventListener("change", render);
  selectB.addEventListener("change", render);
  window.renderCompareChart = render;
});