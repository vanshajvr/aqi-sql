import plotly.graph_objects as go

from ..theme import ACCENT, GRID, TEXT, base_layout

THEN_COLOR = "#8b949e"


def build(df21):
    """Dumbbell: each station's PM2.5 in 2018-19 and 2025-26, worst now at the top.
    Raw change, not weather-adjusted (see the Then vs Now tab)."""
    d = df21.dropna(subset=["pm25_2025_26"]).copy()
    d["short"] = d["station_name"].str.replace(r",\s*(New )?Delhi.*$", "", regex=True)
    d = d.sort_values("pm25_2025_26", ascending=False).reset_index(drop=True)
    options = [("Top 15", 15), ("All", len(d))]
    heights = [max(380, 28 * n + 130) for _, n in options]

    fig = go.Figure()
    for i, (_, n) in enumerate(options):
        sub = d.head(n).iloc[::-1]
        xs, ys = [], []
        for r in sub.itertuples():
            xs += [r.pm25_2018_19, r.pm25_2025_26, None]
            ys += [r.short, r.short, None]
        visible = i == 0
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color="#30363d", width=3),
                                 hoverinfo="skip", showlegend=False, visible=visible))
        fig.add_trace(go.Scatter(
            x=sub["pm25_2018_19"], y=sub["short"], mode="markers", name="2018–19",
            marker=dict(size=10, color=THEN_COLOR, line=dict(color="#161b22", width=1.5)),
            visible=visible, showlegend=i == 0,
            hovertemplate="<b>%{y}</b><br>2018–19: %{x:.0f} µg/m³<extra></extra>"))
        fig.add_trace(go.Scatter(
            x=sub["pm25_2025_26"], y=sub["short"], mode="markers", name="2025–26",
            marker=dict(size=12, color=ACCENT, line=dict(color="#161b22", width=1.5)),
            customdata=sub[["change_pct"]].values, visible=visible, showlegend=i == 0,
            hovertemplate="<b>%{y}</b><br>2025–26: %{x:.0f} µg/m³ (%{customdata[0]:+.0f}%)<extra></extra>"))

    buttons = []
    for i, (label, _) in enumerate(options):
        vis = [j // 3 == i for j in range(3 * len(options))]
        buttons.append(dict(label=label, method="update", args=[{"visible": vis}, {"height": heights[i]}]))
    fig.add_vline(x=40, line=dict(color="#6e7681", width=1, dash="dot"),
                  annotation_text="India's annual limit", annotation_position="bottom right",
                  annotation_font=dict(color="#6e7681", size=11))
    fig.update_layout(
        updatemenus=[dict(type="buttons", direction="right", x=1, y=1.02, xanchor="right", yanchor="bottom",
                          bgcolor="#21262d", bordercolor=GRID, font=dict(color=TEXT, size=11),
                          buttons=buttons, pad=dict(l=6, r=6, t=4, b=4))],
        xaxis=dict(title="Mean PM2.5 (µg/m³)", gridcolor=GRID, rangemode="tozero"),
        yaxis=dict(title=""),
        legend=dict(orientation="h", y=1.02, x=0, yanchor="bottom", bgcolor="rgba(0,0,0,0)"),
    )
    return base_layout(fig, height=heights[0], top_margin=70)
