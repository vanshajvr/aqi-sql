import plotly.graph_objects as go

from ..theme import ACCENT,PERIOD_COLORS,base_layout

LABELS = {
    "early_winter(Dec)": "Early Winter (Dec)",
    "stubble_season(Oct-Nov)": "Stubble Season (Oct-Nov)",
    "late_winter(Jan-Feb)": "Late Winter (Jan-Feb)",
    "rest of the year(Mar-Sep)": "Rest of Year (Mar-Sep)",
}
 
 
def build(df04):
    d = df04.sort_values("pct_severe", ascending=False)
    colors = [PERIOD_COLORS.get(p, ACCENT) for p in d["period"]]
    x_labels = [LABELS.get(p, p) for p in d["period"]]
 
    fig = go.Figure(go.Bar(
        x=x_labels, y=d["pct_severe"], marker_color=colors, width=0.5,
        text=d["pct_severe"].astype(str) + "%", textposition="outside",
        hovertemplate="<b>%{x}</b><br>%{y}%% severe days<extra></extra>",
    ))
    fig.update_layout(xaxis_title="", yaxis_title="% Days with Severe AQI (\u2265300)", bargap=0.4)
    return base_layout(fig, height=480, top_margin=50)
 