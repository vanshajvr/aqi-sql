import plotly.graph_objects as go

from ..theme import base_layout

# Sequential single hue: empty (card background) -> full coverage (accent blue)
SCALE = [[0.0, "#161b22"], [0.5, "#1f4f8f"], [1.0, "#58a6ff"]]


def build(df08, station_names):
    d = df08.copy()
    d["station_name"] = d["station_id"].map(station_names).fillna(d["station_id"])
    pivot = d.pivot_table(index="station_name", columns="year",
                          values="pct_of_year_covered", fill_value=0)
    # Longest-running stations at the top
    first_year = d.groupby("station_name")["year"].min()
    order = first_year.sort_values(kind="stable").index.tolist()
    pivot = pivot.reindex(order[::-1])
    years = [str(y) for y in pivot.columns]

    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=years, y=pivot.index, zmin=0, zmax=100,
        colorscale=SCALE, xgap=2, ygap=2,
        colorbar=dict(title="% of days", ticksuffix="%", thickness=10),
        hovertemplate="<b>%{y}</b><br>%{x}: %{z:.0f}% of days with PM2.5<extra></extra>",
    ))
    fig.update_layout(xaxis=dict(type="category", side="top", gridcolor="rgba(0,0,0,0)"),
                      yaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=11)))
    return base_layout(fig, height=max(480, 22 * len(pivot) + 80), top_margin=60)
