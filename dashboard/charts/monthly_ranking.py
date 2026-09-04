import plotly.graph_objects as go

from ..theme import ACCENT, ACCENT_2, GRID, TEXT, base_layout


def build(df02):
    months = sorted(df02["year_month"].unique())
    default_i = len(months) - 1  # default to most recent month

    fig = go.Figure()
    for i, ym in enumerate(months):
        d = df02[df02["year_month"] == ym].sort_values("worst_rank").head(15)
        visible = (i == default_i)
        fig.add_trace(go.Bar(
            x=d["station_name"], y=d["worst_rank"], name="RANK()",
            marker_color=ACCENT, visible=visible, offsetgroup=0,
            hovertemplate="<b>%{x}</b><br>RANK: %{y}<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            x=d["station_name"], y=d["worst_dense_rank"], name="DENSE_RANK()",
            marker_color=ACCENT_2, visible=visible, offsetgroup=1,
            hovertemplate="<b>%{x}</b><br>DENSE_RANK: %{y}<extra></extra>",
        ))

    buttons = []
    for i, ym in enumerate(months):
        vis = [False] * (len(months) * 2)
        vis[i * 2: i * 2 + 2] = [True, True]
        buttons.append(dict(label=ym, method="update", args=[{"visible": vis}]))

    fig.update_layout(
        barmode="group",
        xaxis_title="", yaxis_title="Rank (1 = worst AQI that month)",
        xaxis=dict(gridcolor=GRID, tickangle=-40),
        updatemenus=[dict(
            type="dropdown", direction="down", buttons=buttons,
            x=0, y=1.05, xanchor="left", yanchor="bottom",
            bgcolor="#21262d", bordercolor=GRID, font=dict(color=TEXT, size=12),
            active=default_i,
        )],
        legend=dict(orientation="h", y=1.05, yanchor="bottom", x=1, xanchor="right"),
    )
    return base_layout(fig, height=520, top_margin=70)