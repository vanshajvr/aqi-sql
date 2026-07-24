import plotly.graph_objects as go
from ..theme import ACCENT, GRID, TEXT, base_layout

def build(df06):
    d = df06.sort_values("overall_avg_aqi", ascending=False).reset_index(drop=True)
    options = [10, 15, 20, len(d)]
    labels = ["Top 10", "Top 15", "Top 20", "All"]
    fixed_height = max(500, 24 * len(d) + 140)
 
    fig = go.Figure()
    for i, n in enumerate(options):
        sub = d.head(n).iloc[::-1]
        fig.add_trace(go.Bar(
            x=sub["overall_avg_aqi"], y=sub["station_name"], orientation="h",
            marker=dict(color=sub["overall_avg_aqi"], colorscale=[[0, ACCENT], [1, "#f85149"]]),
            text=sub["overall_avg_aqi"].round(1), textposition="outside",
            visible=(i == 1),
            hovertemplate="<b>%{y}</b><br>Avg AQI: %{x:.1f}<extra></extra>",
        ))
 
    buttons = []
    for i, label in enumerate(labels):
        vis = [j == i for j in range(len(options))]
        buttons.append(dict(label=label, method="update", args=[{"visible": vis}]))
 
    fig.update_layout(
        updatemenus=[dict(type="buttons", direction="right", x=1, y=1.05, xanchor="right", yanchor="bottom",
                           bgcolor="#21262d", bordercolor=GRID, font=dict(color=TEXT, size=11),
                           buttons=buttons, pad=dict(l=6, r=6, t=4, b=4))],
        xaxis_title="Overall Average AQI", yaxis_title="", bargap=0.28,
    )
    return base_layout(fig, height=fixed_height, top_margin=70)
 
