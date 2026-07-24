import plotly.graph_objects as go

from ..theme import SEVERITY_COLORS,SEVERITY_ORDER,GRID,TEXT,base_layout

def build(df05, df06, station_names):
    order_all = df06.sort_values("overall_avg_aqi", ascending=False)["station_id"].tolist()
    d = df05.copy()
    d["station_name"] = d["station_id"].map(station_names)
 
    def make_pivot(ids):
        sub = d[d["station_id"].isin(ids)]
        pivot = sub.pivot_table(index="station_name", columns="computed_bucket",
                                 values="pct_of_station_days", fill_value=0)
        pivot = pivot.reindex(columns=SEVERITY_ORDER, fill_value=0)
        name_order = [station_names[i] for i in ids if station_names.get(i) in pivot.index]
        return pivot.reindex(name_order[::-1])
 
    variants = {"Top 15 Worst": order_all[:15], "Top 15 Best": order_all[-15:]}
 
    fig = go.Figure()
    trace_groups = []
    trace_count = 0
    for vi, (label, ids) in enumerate(variants.items()):
        pivot = make_pivot(ids)
        group = []
        for cat in SEVERITY_ORDER:
            fig.add_trace(go.Bar(
                y=pivot.index, x=pivot[cat], name=cat, orientation="h",
                marker_color=SEVERITY_COLORS[cat], visible=(vi == 0),
                showlegend=False,
                hovertemplate=f"<b>%{{y}}</b><br>{cat}: " + "%{x:.1f}%<extra></extra>",
            ))
            group.append(trace_count)
            trace_count += 1
        trace_groups.append(group)
 
    # Permanent legend-proxy traces (Scatter markers, not empty Bar traces --
    # Plotly reliably keeps these in the legend even with no real coordinates)
    for cat in SEVERITY_ORDER:
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="markers",
            marker=dict(size=11, symbol="square", color=SEVERITY_COLORS[cat]),
            name=cat, showlegend=True, hoverinfo="skip",
        ))
 
    buttons = []
    for vi, label in enumerate(variants.keys()):
        vis = [False] * trace_count + [True] * len(SEVERITY_ORDER)
        for idx in trace_groups[vi]:
            vis[idx] = True
        buttons.append(dict(label=label, method="update", args=[{"visible": vis}]))
 
    fig.update_layout(
        barmode="stack", xaxis_title="% of Days", yaxis_title="",
        bargap=0.35,
        updatemenus=[dict(type="buttons", direction="right", x=1, y=1.20, xanchor="right", yanchor="bottom",
                           bgcolor="#21262d", bordercolor=GRID, font=dict(color=TEXT, size=11),
                           buttons=buttons, pad=dict(l=10, r=10, t=6, b=6))],
        legend=dict(orientation="h", y=1.05, yanchor="bottom", x=0, xanchor="left"),
    )
    return base_layout(fig, height=600, top_margin=130)
 