import plotly.graph_objects as go

from ..theme import ACCENT, CARD_BG, GRID, base_layout


def build(df10):
    # Widest spread at the top: local pollutants first, regional ones last
    order = (df10.groupby("pollutant")["pollutant_max_to_min"].first()
             .sort_values(ascending=True).index.tolist())
    d = df10.copy()
    d["short_name"] = d["station_name"].str.replace(r",\s*Delhi.*$", "", regex=True)

    fig = go.Figure(go.Scatter(
        x=d["index_vs_city_median"], y=d["pollutant"], mode="markers",
        marker=dict(size=10, color=ACCENT, opacity=0.75, line=dict(color=CARD_BG, width=2)),
        customdata=d[["short_name", "mean_value", "rank_in_pollutant"]].values,
        hovertemplate="<b>%{customdata[0]}</b><br>%{y}: %{x:.2f}x city median"
                      "<br>Mean %{customdata[1]}<br>Rank %{customdata[2]}<extra></extra>",
    ))
    # Spread goes in the row label, so it never collides with an outlier dot
    spread = d.groupby("pollutant")["pollutant_max_to_min"].first()
    row_labels = [f"{p} · {spread[p]:.1f}× apart" for p in order]
    x_max = d["index_vs_city_median"].max() + 0.2
    top = d.loc[d["index_vs_city_median"].idxmax()]
    fig.add_annotation(x=top["index_vs_city_median"], y=top["pollutant"], text=top["short_name"],
                       showarrow=False, yshift=16, font=dict(color="#c9d1d9", size=11))
    fig.add_vline(x=1.0, line=dict(color="#6e7681", width=1, dash="dot"),
                  annotation_text="city median", annotation_position="top",
                  annotation_font=dict(color="#8b949e", size=11))
    fig.update_layout(
        showlegend=False,
        xaxis=dict(title="Station mean / median of all stations (network days, 2018–2026)",
                   ticksuffix="x", gridcolor=GRID, range=[0, x_max]),
        yaxis=dict(categoryorder="array", categoryarray=order, title="",
                   tickvals=order, ticktext=row_labels),
    )
    return base_layout(fig, height=420, top_margin=50)
