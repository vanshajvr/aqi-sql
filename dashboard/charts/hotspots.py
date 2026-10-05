import plotly.graph_objects as go

from ..theme import ACCENT, GRID, base_layout


def build(df16):
    d = df16[df16["n_months_top5"] > 0].copy()
    d["short_name"] = d["station_name"].str.replace(r",\s*Delhi.*$", "", regex=True)
    d = d.sort_values("pct_months_top5")  # highest at the top of a horizontal bar chart

    fig = go.Figure(go.Bar(
        x=d["pct_months_top5"], y=d["short_name"], orientation="h",
        marker=dict(color=ACCENT, cornerradius=4, line=dict(width=0)),
        text=[f"{t} of {n} months" for t, n in zip(d["n_months_top5"], d["n_months_eligible"])],
        textposition="outside", textfont=dict(color="#8b949e", size=11),
        customdata=d[["n_months_worst"]].values,
        hovertemplate="<b>%{y}</b><br>In the month's top 5 worst: %{x:.0f}% of months"
                      "<br>Worst station of the month: %{customdata[0]} times<extra></extra>",
    ))
    fig.update_layout(
        showlegend=False, bargap=0.3,
        xaxis=dict(title="% of months in that month's 5 worst stations (Feb 2018 - Jun 2020)",
                   ticksuffix="%", range=[0, 100], gridcolor=GRID),
        yaxis=dict(title=""),
    )
    return base_layout(fig, height=max(380, 30 * len(d) + 100), top_margin=30)
