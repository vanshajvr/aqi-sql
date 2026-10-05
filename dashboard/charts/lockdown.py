import plotly.graph_objects as go

from ..theme import ACCENT, GRID, base_layout

PRE_COLOR = "#6e7681"  # muted: the part of the drop that was already there


def build(df09):
    # Stacked so the two segments add up to the naive 2020-vs-2019 drop:
    # pct_change_lockdown = pct_change_pre + lockdown_effect_pts
    d = df09.sort_values("lockdown_effect_pts", ascending=False)  # biggest effect on top
    custom = d[["pct_change_lockdown", "n_stations"]].values

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=d["pollutant"], x=d["pct_change_pre"], orientation="h",
        name="Already lower before lockdown (1-21 Mar)",
        marker=dict(color=PRE_COLOR, cornerradius=4, line=dict(width=0)),
        customdata=custom,
        hovertemplate="<b>%{y}</b><br>Already lower before lockdown: %{x:.1f}%"
                      "<br>Total drop vs 2019: %{customdata[0]:.1f}%"
                      "<br>%{customdata[1]} stations<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        y=d["pollutant"], x=d["lockdown_effect_pts"], orientation="h",
        name="Attributable to lockdown (25 Mar - 3 May)",
        marker=dict(color=ACCENT, cornerradius=4, line=dict(width=0)),
        text=d["lockdown_effect_pts"].map(lambda v: f"{v:.0f} pts"), textposition="inside",
        insidetextanchor="start",
        customdata=custom,
        hovertemplate="<b>%{y}</b><br>Attributable to lockdown: %{x:.1f} pts"
                      "<br>Total drop vs 2019: %{customdata[0]:.1f}%"
                      "<br>%{customdata[1]} stations<extra></extra>",
    ))
    fig.update_layout(
        barmode="relative", bargap=0.35,
        xaxis=dict(title="Change vs same dates in 2019 (%)", ticksuffix="%", gridcolor=GRID,
                   zeroline=True, zerolinecolor="#6e7681"),
        yaxis_title="",
        legend=dict(orientation="h", y=1.1, x=0, bgcolor="rgba(0,0,0,0)"),
    )
    return base_layout(fig, height=420, top_margin=70)
