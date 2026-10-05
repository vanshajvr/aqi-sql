import plotly.graph_objects as go

from ..theme import ACCENT, CARD_BG, GRID, WARNING, base_layout

MONTH_NAMES = {"01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr", "05": "May", "06": "Jun",
               "07": "Jul", "08": "Aug", "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"}
BURNING_MONTHS = {"10", "11"}
MUTED = "#6e7681"


def build_monthly(df12):
    """Each month as a point: shallower mixing height -> more PM2.5. Oct and Nov
    sit well above the other months at the same mixing height."""
    d = df12.copy()
    d["name"] = d["month"].map(MONTH_NAMES)
    is_burn = d["month"].isin(BURNING_MONTHS)

    fig = go.Figure()
    for mask, color, label in ((~is_burn, ACCENT, "Other months"),
                               (is_burn, WARNING, "Oct-Nov (stubble season)")):
        sub = d[mask]
        fig.add_trace(go.Scatter(
            x=sub["mean_mixing_height_m"], y=sub["mean_pm25"], mode="markers+text",
            name=label, text=sub["name"],
            # Dec and Jan sit almost on top of each other; push Jan's label below
            textposition=["bottom center" if m == "01" else "top center" for m in sub["month"]],
            textfont=dict(color="#c9d1d9", size=11),
            marker=dict(size=12, color=color, line=dict(color=CARD_BG, width=2)),
            customdata=sub[["mean_wind_kmh", "pct_rain_days"]].values,
            hovertemplate="<b>%{text}</b><br>PM2.5 %{y:.0f} µg/m³"
                          "<br>Mixing height %{x:.0f} m<br>Wind %{customdata[0]} km/h"
                          "<br>Rain days %{customdata[1]}%<extra></extra>",
        ))
    fig.update_layout(
        xaxis=dict(title="Mean mixing height (m): how deep the air pollution can spread into",
                   gridcolor=GRID),
        yaxis=dict(title="Mean PM2.5 (µg/m³)", gridcolor=GRID, rangemode="tozero"),
        legend=dict(orientation="h", y=1.08, x=0, bgcolor="rgba(0,0,0,0)"),
    )
    return base_layout(fig, height=440, top_margin=60)


HALF_LABELS = {"1": "early", "2": "late"}


def build_excess(df13):
    """Actual PM2.5 / PM2.5 expected from the day's weather, per half-month."""
    d = df13.copy()
    d["label"] = d["half_month"].map(
        lambda h: f"{HALF_LABELS[h[-1]]} {MONTH_NAMES[h[:2]]}")
    colors = [WARNING if r >= 1.3 else (ACCENT if r >= 0.9 else MUTED) for r in d["excess_ratio"]]

    fig = go.Figure(go.Bar(
        x=d["label"], y=d["excess_ratio"],
        marker=dict(color=colors, cornerradius=4, line=dict(width=0)),
        customdata=d[["actual_pm25", "expected_pm25", "n_days"]].values,
        hovertemplate="<b>%{x}</b><br>%{y:.2f}x what the weather predicts"
                      "<br>Actual PM2.5 %{customdata[0]}, expected %{customdata[1]}"
                      "<br>%{customdata[2]} dry days<extra></extra>",
    ))
    fig.add_hline(y=1.0, line=dict(color="#8b949e", width=1, dash="dot"))
    fig.update_layout(
        showlegend=False, bargap=0.25,
        xaxis=dict(title="", tickangle=-45, gridcolor="rgba(0,0,0,0)"),
        yaxis=dict(title="Actual PM2.5 / weather-predicted", ticksuffix="x",
                   gridcolor=GRID, rangemode="tozero"),
    )
    return base_layout(fig, height=440, top_margin=40)
