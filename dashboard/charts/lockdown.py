import plotly.graph_objects as go

from ..theme import ACCENT, CARD_BG, GRID, base_layout

PRE_COLOR = "#6e7681"  # muted: the part of the drop that was already there


def build(df09, df15=None):
    # Stacked so the two segments add up to the naive 2020-vs-2019 drop:
    # pct_change_lockdown = pct_change_pre + lockdown_effect_pts
    d = df09.sort_values("lockdown_effect_pts", ascending=False)  # biggest effect on top
    custom = d[["pct_change_lockdown", "n_stations"]].values

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=d["pollutant"], x=d["pct_change_pre"], orientation="h",
        name="Already lower before lockdown",
        marker=dict(color=PRE_COLOR, cornerradius=4, line=dict(width=0)),
        customdata=custom,
        hovertemplate="<b>%{y}</b><br>Already lower before lockdown: %{x:.1f}%"
                      "<br>Total drop vs 2019: %{customdata[0]:.1f}%"
                      "<br>%{customdata[1]} stations<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        y=d["pollutant"], x=d["lockdown_effect_pts"], orientation="h",
        name="Lockdown effect (lower bound)",
        marker=dict(color=ACCENT, cornerradius=4, line=dict(width=0)),
        text=d["lockdown_effect_pts"].map(lambda v: f"{v:.0f} pts"), textposition="inside",
        insidetextanchor="start",
        customdata=custom,
        hovertemplate="<b>%{y}</b><br>Attributable to lockdown: %{x:.1f} pts"
                      "<br>Total drop vs 2019: %{customdata[0]:.1f}%"
                      "<br>%{customdata[1]} stations<extra></extra>",
    ))
    if df15 is not None:
        adj = (df15[df15["win"] == "lockdown"]
               .set_index("pollutant")["weather_adjusted_change_pct"]
               .reindex(d["pollutant"]))
        fig.add_trace(go.Scatter(
            x=adj.values, y=adj.index, mode="markers",
            name="Weather-adjusted estimate",
            marker=dict(symbol="diamond", size=13, color="#f0f6fc",
                        line=dict(color=CARD_BG, width=2)),
            hovertemplate="<b>%{y}</b><br>Weather-adjusted change: %{x:.1f}%<extra></extra>",
        ))
    fig.update_layout(
        barmode="relative", bargap=0.35,
        xaxis=dict(title="Change vs same dates in 2019 (%)", ticksuffix="%", gridcolor=GRID,
                   zeroline=True, zerolinecolor="#6e7681"),
        yaxis_title="",
        legend=dict(orientation="h", y=1.1, x=0, bgcolor="rgba(0,0,0,0)"),
    )
    return base_layout(fig, height=420, top_margin=70)
