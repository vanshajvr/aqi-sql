import pandas as pd
import plotly.graph_objects as go

from ..theme import ACCENT,GRID,TEXT,base_layout

def build(df03):
    d = df03.copy()
    d["date"] = pd.to_datetime(d["year"].astype(str) + "-" + d["month"] + "-01")
    d = d.sort_values("date")
    fig = go.Figure(go.Scatter(
        x=d["date"], y=d["avg_aqi"], mode="lines+markers",
        line=dict(color=ACCENT, width=2), marker=dict(size=5, color=ACCENT),
        fill="tozeroy", fillcolor="rgba(88,166,255,0.08)",
        hovertemplate="<b>%{x|%b %Y}</b><br>Avg AQI: %{y:.1f}<extra></extra>",
    ))
    fig.update_layout(
        xaxis_title="", yaxis_title="City-wide Average AQI",
        xaxis=dict(
            gridcolor=GRID,
            rangeslider=dict(visible=True, bgcolor="#21262d", thickness=0.08),
            rangeselector=dict(
                buttons=[
                    dict(count=1, label="1y", step="year", stepmode="backward"),
                    dict(count=3, label="3y", step="year", stepmode="backward"),
                    dict(step="all", label="All"),
                ],
                bgcolor="#21262d", activecolor=ACCENT, font=dict(color=TEXT, size=11),
                y=1.05, yanchor="bottom", x=0, xanchor="left",
            ),
        ),
    )
    return base_layout(fig, height=480, top_margin=70)
 