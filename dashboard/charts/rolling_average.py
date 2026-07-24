import pandas as pd
import plotly.graph_objects as go

from ..theme import ACCENT,ACCENT_2,GRID,TEXT,base_layout

def build(df01, df06, station_names):
    worst_ids = df06.sort_values("overall_avg_aqi", ascending=False).head(10)["station_id"].tolist()
 
    fig = go.Figure()
    for i, sid in enumerate(worst_ids):
        d = df01[df01["station_id"] == sid].copy()
        d["date"] = pd.to_datetime(d["date"])
        d = d.sort_values("date")
        visible = (i == 0)
        fig.add_trace(go.Scatter(x=d["date"], y=d["aqi"], mode="lines",
                                  line=dict(color="#30363d", width=1),
                                  name="Daily AQI", visible=visible, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=d["date"], y=d["rolling_7day_avg"], mode="lines",
                                  line=dict(color=ACCENT, width=2),
                                  name="7-day avg", visible=visible,
                                  hovertemplate="<b>%{x|%d %b %Y}</b><br>7d avg: %{y:.1f}<extra></extra>"))
        fig.add_trace(go.Scatter(x=d["date"], y=d["rolling_30day_avg"], mode="lines",
                                  line=dict(color=ACCENT_2, width=2),
                                  name="30-day avg", visible=visible,
                                  hovertemplate="<b>%{x|%d %b %Y}</b><br>30d avg: %{y:.1f}<extra></extra>"))
 
    buttons = []
    for i, sid in enumerate(worst_ids):
        vis = [False] * (len(worst_ids) * 3)
        vis[i * 3: i * 3 + 3] = [True, True, True]
        buttons.append(dict(label=station_names.get(sid, sid), method="update", args=[{"visible": vis}]))
 
    fig.update_layout(
        xaxis_title="", yaxis_title="AQI",
        xaxis=dict(gridcolor=GRID, rangeslider=dict(visible=True, bgcolor="#21262d", thickness=0.06)),
        updatemenus=[dict(
            type="dropdown", direction="down", buttons=buttons,
            x=0, y=1.05, xanchor="left", yanchor="bottom",
            bgcolor="#21262d", bordercolor=GRID, font=dict(color=TEXT, size=12),
        )],
        legend=dict(orientation="h", y=1.05, yanchor="bottom", x=1, xanchor="right"),
    )
    return base_layout(fig, height=560, top_margin=70)
 