import plotly.graph_objects as go

from ..theme import PERIOD_LABELS, SEVERITY_COLORS, base_layout

# 04 counts DAYS (city-wide mean PM2.5) on CPCB's PM2.5 bands, so the two series
# reuse the severity breakdown's own colors for the same categories.
SERIES = [
    ("pct_days_very_poor_plus", "n_days_very_poor_plus", "Very Poor+ (PM2.5 > 120)", "Very Poor"),
    ("pct_days_severe", "n_days_severe", "Severe (PM2.5 > 250)", "Severe"),
]


def build(df04):
    d = df04.sort_values("pct_days_very_poor_plus", ascending=False)
    x_labels = [PERIOD_LABELS.get(p, p) for p in d["period"]]

    fig = go.Figure()
    for pct_col, n_col, name, bucket in SERIES:
        fig.add_trace(go.Bar(
            x=x_labels, y=d[pct_col], name=name,
            marker=dict(color=SEVERITY_COLORS[bucket], cornerradius=4, line=dict(width=0)),
            text=d[pct_col].map(lambda v: f"{v:.1f}%"), textposition="outside",
            customdata=d[[n_col, "n_days"]].values,
            hovertemplate="<b>%{x}</b><br>" + name + ": %{y:.1f}% of days"
                          "<br>%{customdata[0]} of %{customdata[1]} days<extra></extra>",
        ))
    fig.update_layout(
        barmode="group", bargap=0.3, bargroupgap=0.08,
        xaxis_title="", yaxis_title="% of days (city-wide mean PM2.5)",
        legend=dict(orientation="h", y=1.08, x=0, bgcolor="rgba(0,0,0,0)"),
    )
    return base_layout(fig, height=480, top_margin=60)
