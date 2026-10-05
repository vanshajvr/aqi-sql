import plotly.graph_objects as go
from ..theme import ACCENT, GRID, TEXT, base_layout

def build(df06):
    d = df06.sort_values("avg_aqi_2018_19", ascending=False).reset_index(drop=True)
    options = [10, 15, 20, len(d)]
    labels = ["Top 10", "Top 15", "Top 20", "All"]
    heights = [max(380, 32 * n + 140) for n in options]  # chart grows with the bar count
 
    fig = go.Figure()
    for i, n in enumerate(options):
        sub = d.head(n).iloc[::-1]
        fig.add_trace(go.Bar(
            x=sub["avg_aqi_2018_19"], y=sub["station_name"], orientation="h",
            marker=dict(color=sub["avg_aqi_2018_19"], colorscale=[[0, ACCENT], [1, "#f85149"]],
                        cornerradius=6, line=dict(width=0)),
            text=sub["avg_aqi_2018_19"].round(1), textposition="outside",
            visible=(i == 0),  # matches the Top 10 button, which Plotly highlights by default
            hovertemplate="<b>%{y}</b><br>Avg AQI: %{x:.1f}<extra></extra>",
        ))
 
    buttons = []
    for i, label in enumerate(labels):
        vis = [j == i for j in range(len(options))]
        buttons.append(dict(label=label, method="update", args=[{"visible": vis}, {"height": heights[i]}]))
 
    fig.update_layout(
        updatemenus=[dict(type="buttons", direction="right", x=1, y=1.05, xanchor="right", yanchor="bottom",
                           bgcolor="#21262d", bordercolor=GRID, font=dict(color=TEXT, size=11),
                           buttons=buttons, pad=dict(l=6, r=6, t=4, b=4))],
        xaxis_title="Average AQI, 2018-2019", yaxis_title="", bargap=0.35,
    )
    return base_layout(fig, height=heights[0], top_margin=70)