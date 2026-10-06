import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..theme import ACCENT, CARD_BG, GRID, WARNING, base_layout

MUTED = "#6e7681"
BEFORE = ["2018-19", "2019-20"]
# The weather source has no mixing height for Jan - Jun 2024, so 2023-24 rests
# on November - December only (cpcb_gap_preregistration.md, Amendment 1)
PARTIAL = "2023-24"


def build_winters(df25):
    """Two small charts: severe days, and weather-adjusted pollution, per winter."""
    d = df25.assign(label=[w[2:].replace("-", "–") for w in df25["winter"]])   # "18–19": eight fit
    colors = [MUTED if w in BEFORE else ACCENT for w in df25["winter"]]
    opacity = [0.45 if w == PARTIAL else 1 for w in df25["winter"]]

    figs = []
    for col, title, fmt in (
        ("pct_days_over_250", "Severe days (PM2.5 > 250)", "%{y:.1f}%"),
        ("weather_adjusted_ratio", "PM2.5 / weather-predicted", "%{y:.2f}×"),
    ):
        fig = go.Figure(go.Bar(
            x=d["label"], y=d[col], marker=dict(color=colors, opacity=opacity, cornerradius=4, line=dict(width=0)),
            text=d[col].map((lambda v: f"{v:.1f}%") if col.startswith("pct") else (lambda v: f"{v:.2f}×")),
            textposition="outside",
            customdata=d[["n_days", "source", "mean_pm25"]].values,
            hovertemplate="<b>Winter 20%{x}</b><br>" + title + ": " + fmt +
                          "<br>Mean PM2.5 %{customdata[2]}<br>%{customdata[0]} days, %{customdata[1]} data"
                          "<extra></extra>",
        ))
        ref = d[d["winter"].isin(BEFORE)][col].mean()
        fig.add_hline(y=ref, line=dict(color=MUTED, width=1, dash="dot"))   # 2018-20 average
        top = d[col].max()
        fig.add_annotation(x=PARTIAL[2:].replace("-", "–"), y=0, yref="y", yanchor="bottom", text="Nov–Dec<br>only",
                           showarrow=False, font=dict(color="#c9d1d9", size=10))
        fig.update_layout(
            showlegend=False, bargap=0.3,
            xaxis=dict(title="", tickangle=0),
            yaxis=dict(title=title, gridcolor=GRID, rangemode="tozero", range=[0, top * 1.2],
                       ticksuffix="%" if col.startswith("pct") else "×"),
        )
        figs.append(base_layout(fig, height=380, top_margin=30))
    return figs


def build_stubble(df20):
    """Stacked panels sharing the year axis: fire counts, then the smoke-window excess."""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.12,
                        row_heights=[0.5, 0.5])
    fig.add_trace(go.Bar(
        x=df20["year"], y=df20["fires_15oct_30nov"], marker=dict(color=WARNING, cornerradius=3, line=dict(width=0)),
        hovertemplate="<b>%{x}</b><br>%{y:,} fires detected (15 Oct – 30 Nov)<extra></extra>",
    ), row=1, col=1)
    d = df20[df20["weather_adjusted_ratio"].notna()]
    fig.add_trace(go.Scatter(
        x=d["year"], y=d["weather_adjusted_ratio"], mode="markers+text",
        text=d["weather_adjusted_ratio"].map(lambda v: f"{v:.2f}×"), textposition="top center",
        textfont=dict(color="#c9d1d9", size=11),
        marker=dict(size=11, color=ACCENT, line=dict(color=CARD_BG, width=2)),
        customdata=d[["n_panel_days", "mean_pm25"]].values,
        hovertemplate="<b>%{x}</b><br>%{y:.2f}× what the weather predicts"
                      "<br>Mean PM2.5 %{customdata[1]}<br>%{customdata[0]} days<extra></extra>",
    ), row=2, col=1)
    fig.add_hline(y=1.0, line=dict(color=MUTED, width=1, dash="dot"), row=2, col=1)
    fig.update_layout(showlegend=False, bargap=0.3)
    fig.update_yaxes(title_text="Fires detected", gridcolor=GRID, row=1, col=1)
    fig.update_yaxes(title_text="Smoke-window PM2.5 /<br>weather-predicted", gridcolor=GRID,
                     rangemode="tozero", range=[0, d["weather_adjusted_ratio"].max() * 1.25],
                     ticksuffix="×", row=2, col=1)
    fig.update_xaxes(dtick=1, gridcolor="rgba(0,0,0,0)", row=2, col=1)
    return base_layout(fig, height=520, top_margin=30)
