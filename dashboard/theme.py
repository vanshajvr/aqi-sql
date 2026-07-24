import plotly.io as pio

CARD_BG = "#161b22"
GRID = "#21262d"
TEXT = "#c9d1d9"
ACCENT = "#58a6ff"
ACCENT_2 = "#f0883e"
HOVER_BG = "#1c2333"
 
SEVERITY_ORDER = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]
SEVERITY_COLORS = {
    "Good": "#3fb950",
    "Satisfactory": "#7ee787",
    "Moderate": "#d29922",
    "Poor": "#db6d28",
    "Very Poor": "#f85149",
    "Severe": "#8b1a1a",
}
PERIOD_COLORS = {
    "rest of the year(Mar-Sep)": "#3fb950",
    "late_winter(Jan-Feb)": "#d29922",
    "stubble_season(Oct-Nov)": "#db6d28",
    "early_winter(Dec)": "#8b1a1a",
}
 
 
def base_layout(fig, height, top_margin=60):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=CARD_BG,
        plot_bgcolor=CARD_BG,
        font=dict(family="Inter, Helvetica, Arial, sans-serif", color=TEXT, size=13),
        margin=dict(l=50, r=30, t=top_margin, b=50),
        height=height,
        hovermode="closest",
        hoverlabel=dict(bgcolor=HOVER_BG, bordercolor=ACCENT,
                         font=dict(color="#ffffff", size=12)),
        xaxis=dict(gridcolor=GRID, zerolinecolor=GRID),
        yaxis=dict(gridcolor=GRID, zerolinecolor=GRID),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    return fig

def to_div(fig):
    return pio.to_html(fig, include_plotlyjs=False, full_html=False, config={"displaylogo": False})