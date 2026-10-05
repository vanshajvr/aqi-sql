import plotly.graph_objects as go

from ..theme import ACCENT, GRID, WARNING, base_layout

LEVELS = ["fewest fires", "middle", "most fires"]
SERIES = [("north-westerly", "Wind from Punjab (north-west)", WARNING),
          ("other", "Other winds", ACCENT)]


def build(df18):
    """Excess PM2.5 by previous-day fire count and wind, Diwali weeks excluded."""
    d = df18[df18["scenario"] == "excluding Diwali"]
    fig = go.Figure()
    for wind, name, color in SERIES:
        sub = d[d["wind"] == wind].set_index("fire_level").reindex(LEVELS)
        fig.add_trace(go.Bar(
            x=["Fewest fires", "Middle", "Most fires"], y=sub["excess_ratio"], name=name,
            marker=dict(color=color, cornerradius=4, line=dict(width=0)),
            text=sub["excess_ratio"].map(lambda v: f"{v:.2f}×"), textposition="outside",
            customdata=sub[["n_days", "min_fires", "max_fires", "actual_pm25", "expected_pm25"]].values,
            hovertemplate="<b>%{x}, " + name.lower() + "</b>"
                          "<br>%{y:.2f}× what the weather predicts"
                          "<br>Fires the day before: %{customdata[1]:,}–%{customdata[2]:,}"
                          "<br>PM2.5 %{customdata[3]} vs %{customdata[4]} expected"
                          "<br>%{customdata[0]} days<extra></extra>",
        ))
    fig.add_hline(y=1.0, line=dict(color="#8b949e", width=1, dash="dot"))
    fig.update_layout(
        barmode="group", bargap=0.3, bargroupgap=0.08,
        xaxis=dict(title="Punjab/Haryana fires the day before (thirds)"),
        yaxis=dict(title="PM2.5 / weather-predicted", ticksuffix="×", gridcolor=GRID,
                   rangemode="tozero"),
        legend=dict(orientation="h", y=1.1, x=0, bgcolor="rgba(0,0,0,0)"),
    )
    return base_layout(fig, height=440, top_margin=60)
