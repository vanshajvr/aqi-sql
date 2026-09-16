import pandas as pd


def build(df03, width=1200, height=180):
    """
    Renders the real city-wide monthly-average AQI trend as a very low-
    opacity SVG polyline+area, meant to sit behind the header text as an
    ambient visual - the page's actual data becomes its visual identity
    instead of a generic gradient. Pure SVG, no JS, generated once at
    build time from data already computed for the Trends chart.
    """
    d = df03.copy()
    d["date"] = pd.to_datetime(d["year"].astype(str) + "-" + d["month"] + "-01")
    d = d.sort_values("date")
    values = d["avg_aqi"].tolist()
    n = len(values)
    if n < 2:
        return ""

    vmin, vmax = min(values), max(values)
    vrange = (vmax - vmin) or 1
    # Leave headroom top/bottom so the line doesn't touch the SVG edges
    pad = height * 0.12

    points = []
    for i, v in enumerate(values):
        x = (i / (n - 1)) * width
        y = height - pad - ((v - vmin) / vrange) * (height - 2 * pad)
        points.append(f"{x:.1f},{y:.1f}")
    polyline_points = " ".join(points)
    area_path = f"M0,{height} L" + " L".join(points) + f" L{width},{height} Z"

    return f'''<svg class="hero-sparkline" viewBox="0 0 {width} {height}" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <defs>
    <linearGradient id="heroFade" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#58a6ff" stop-opacity="0"/>
      <stop offset="18%" stop-color="#58a6ff" stop-opacity="1"/>
      <stop offset="82%" stop-color="#58a6ff" stop-opacity="1"/>
      <stop offset="100%" stop-color="#58a6ff" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <path d="{area_path}" fill="url(#heroFade)" fill-opacity="0.07"/>
  <polyline points="{polyline_points}" fill="none" stroke="url(#heroFade)" stroke-width="2" stroke-opacity="0.4"/>
</svg>'''