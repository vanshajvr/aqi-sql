import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..theme import ACCENT, CARD_BG, GRID, WARNING, base_layout

GAP = "2022–25"          # placeholder category for the missing winters
MUTED = "#6e7681"
BEFORE = ["2018-19", "2019-20"]


def _winter_axis(df19):
    """Winters in order, with the data gap inserted before 2025-26."""
    labels = [w.replace("-", "–") for w in df19["winter"]]
    i = labels.index("2025–26")
    return labels[:i] + [GAP] + labels[i:]


def _gap_note(fig, y):
    fig.add_annotation(x=GAP, y=y, text="no data<br>(Nov 2022 –<br>Feb 2025)", showarrow=False,
                       font=dict(color=MUTED, size=11))


def build_winters(df19):
    """Two small charts: severe days, and weather-adjusted pollution, per winter."""
    order = _winter_axis(df19)
    d = df19.assign(label=[w.replace("-", "–") for w in df19["winter"]])
    colors = [MUTED if w in BEFORE else ACCENT for w in df19["winter"]]

    figs = []
    for col, title, fmt, ref_label in (
        ("pct_days_over_250", "Severe days (PM2.5 > 250)", "%{y:.1f}%", "pre-2020 average"),
        ("weather_adjusted_ratio", "PM2.5 / weather-predicted", "%{y:.2f}×", "pre-2020 average"),
    ):
        fig = go.Figure(go.Bar(
            x=d["label"], y=d[col], marker=dict(color=colors, cornerradius=4, line=dict(width=0)),
            text=d[col].map((lambda v: f"{v:.1f}%") if col.startswith("pct") else (lambda v: f"{v:.2f}×")),
            textposition="outside",
            customdata=d[["n_days", "source", "mean_pm25"]].values,
            hovertemplate="<b>Winter %{x}</b><br>" + title + ": " + fmt +
                          "<br>Mean PM2.5 %{customdata[2]}<br>%{customdata[0]} days, %{customdata[1]} data"
                          "<extra></extra>",
        ))
        ref = d[d["winter"].isin(BEFORE)][col].mean()
        fig.add_hline(y=ref, line=dict(color=MUTED, width=1, dash="dot"))   # 2018-20 average
        top = d[col].max()
        _gap_note(fig, top * 0.45)
        fig.update_layout(
            showlegend=False, bargap=0.35,
            xaxis=dict(categoryorder="array", categoryarray=order, title=""),
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
    fig.add_vrect(x0=2021.5, x1=2024.5, fillcolor="rgba(110,118,129,0.12)", line_width=0, row=2, col=1,
                  annotation_text="no PM2.5 data", annotation_position="top",
                  annotation_font=dict(color=MUTED, size=11))
    fig.update_layout(showlegend=False, bargap=0.3)
    fig.update_yaxes(title_text="Fires detected", gridcolor=GRID, row=1, col=1)
    fig.update_yaxes(title_text="Smoke-window PM2.5 /<br>weather-predicted", gridcolor=GRID,
                     rangemode="tozero", range=[0, d["weather_adjusted_ratio"].max() * 1.25],
                     ticksuffix="×", row=2, col=1)
    fig.update_xaxes(dtick=1, gridcolor="rgba(0,0,0,0)", row=2, col=1)
    return base_layout(fig, height=520, top_margin=30)
