import plotly.graph_objects as go

from ..theme import base_layout

# One hue, light -> dark: the three windows are ordered in time and AQI rises
# through them, so a sequential ramp reads correctly without a legend lookup.
WINDOWS = [
    ("baseline_aqi", "n_days_baseline", "3 weeks before", "#9ecbff"),
    ("week_before_aqi", "n_days_week_before", "Week before", "#58a6ff"),
    ("week_after_aqi", "n_days_week_after", "Diwali week", "#1f6feb"),
]


def build(df07):
    d = df07.copy()
    x = d["diwali_year"].replace({"all years": "All years"})

    fig = go.Figure()
    for col, n_col, name, color in WINDOWS:
        fig.add_trace(go.Bar(
            x=x, y=d[col], name=name,
            marker=dict(color=color, cornerradius=4, line=dict(width=0)),
            customdata=d[[n_col]].values,
            hovertemplate="<b>%{x}</b><br>" + name + "<br>Mean AQI %{y:.0f}"
                          "<br>%{customdata[0]} days with data<extra></extra>",
        ))
    # Ratio label above each year's group
    fig.add_trace(go.Scatter(
        x=x, y=d[["baseline_aqi", "week_before_aqi", "week_after_aqi"]].max(axis=1) + 25,
        mode="text", text=d["after_vs_baseline"].map(lambda v: f"{v:.2f}x"),
        textfont=dict(color="#c9d1d9", size=12), showlegend=False, hoverinfo="skip",
    ))
    fig.update_layout(
        barmode="group", bargap=0.25, bargroupgap=0.06,
        xaxis_title="", yaxis_title="City-wide mean AQI",
        legend=dict(orientation="h", y=1.1, x=0, bgcolor="rgba(0,0,0,0)"),
    )
    return base_layout(fig, height=460, top_margin=70)
