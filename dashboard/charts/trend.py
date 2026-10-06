import pandas as pd
import plotly.graph_objects as go

from ..theme import ACCENT, GRID, TEXT, base_layout

# Months with fewer stations than this are drawn muted: before 2018 the
# "city-wide" mean rests on a handful of stations (see 08_coverage.sql).
LOW_COVERAGE_STATIONS = 10
MUTED = "#6e7681"
GAP = ("2022-11-01", "2025-02-01")       # no data at all in the backfill


def build(df22):
    """Monthly city-wide PM2.5, 2015-2026, with the data gap left as a gap."""
    d = df22.copy()
    d["date"] = pd.to_datetime(d["year_month"] + "-01")
    d = d.sort_values("date").reset_index(drop=True)
    # Break the line wherever months are missing, instead of drawing across the gap
    breaks = d["date"].diff().dt.days > 62
    rows = []
    for i, r in d.iterrows():
        if breaks.iloc[i]:
            rows.append({"date": r["date"] - pd.Timedelta(days=15), "pm25": None, "n_stations": None, "source": None})
        rows.append(r.to_dict())
    line = pd.DataFrame(rows)

    fig = go.Figure(go.Scatter(
        x=line["date"], y=line["pm25"], mode="lines+markers", connectgaps=False,
        line=dict(color=ACCENT, width=2),
        marker=dict(size=7, line=dict(color="#161b22", width=1.5),
                    color=[MUTED if (n is not None and n == n and n < LOW_COVERAGE_STATIONS) else ACCENT
                           for n in line["n_stations"]]),
        customdata=line[["n_stations", "source"]].values,
        hovertemplate="<b>%{x|%b %Y}</b><br>PM2.5 %{y:.0f} µg/m³"
                      "<br>%{customdata[0]} stations, %{customdata[1]} data<extra></extra>",
    ))
    fig.add_vrect(x0=GAP[0], x1=GAP[1], fillcolor="rgba(110,118,129,0.12)", line_width=0,
                  annotation_text="no data", annotation_position="top",
                  annotation_font=dict(color=MUTED, size=11))
    fig.add_vline(x="2020-07-01", line=dict(color=MUTED, width=1, dash="dot"))
    fig.add_annotation(x="2020-07-01", y=1, yref="paper", text="OpenAQ data →", showarrow=False,
                       xanchor="left", font=dict(color=MUTED, size=11))
    fig.update_layout(
        showlegend=False,
        xaxis_title="", yaxis_title="City-wide PM2.5 (µg/m³)",
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
        yaxis=dict(rangemode="tozero"),
    )
    return base_layout(fig, height=480, top_margin=70)
