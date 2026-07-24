from.theme import ACCENT

MONTH_LABELS = {"01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr", "05": "May", "06": "Jun",
                "07": "Jul", "08": "Aug", "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"}
 
PERIOD_LABELS = {
    "early_winter(Dec)": "Early Winter (Dec)",
    "stubble_season(Oct-Nov)": "Stubble Season (Oct-Nov)",
    "late_winter(Jan-Feb)": "Late Winter (Jan-Feb)",
    "rest of the year(Mar-Sep)": "Rest of Year (Mar-Sep)",
}
 
 
def build(df06, df04, df03):
    worst = df06.sort_values("overall_avg_aqi", ascending=False).iloc[0]
    best = df06.sort_values("overall_avg_aqi", ascending=True).iloc[0]
    peak_period = df04.sort_values("pct_severe", ascending=False).iloc[0]
    biggest_drop = df03.dropna(subset=["yoy_change"]).sort_values("yoy_change").iloc[0]
 
    cards = [
        ("Worst Station", worst["station_name"], f"Avg AQI {worst['overall_avg_aqi']:.1f}", "#f85149"),
        ("Best Station", best["station_name"], f"Avg AQI {best['overall_avg_aqi']:.1f}", "#3fb950"),
        ("Peak Severity Period", PERIOD_LABELS.get(peak_period["period"], peak_period["period"]),
         f"{peak_period['pct_severe']:.1f}% severe days", "#d29922"),
        ("Sharpest YoY Drop",
         f"{MONTH_LABELS.get(biggest_drop['month'], biggest_drop['month'])} {biggest_drop['year']}",
         f"{biggest_drop['yoy_change']:.1f} AQI points \u2014 likely COVID lockdown", ACCENT),
    ]
 
    html_cards = ""
    for label, value, sub, color in cards:
        html_cards += f"""
        <div class="kpi-card">
          <div class="kpi-label">{label}</div>
          <div class="kpi-value" style="color:{color}">{value}</div>
          <div class="kpi-sub">{sub}</div>
        </div>"""
    return html_cards
 