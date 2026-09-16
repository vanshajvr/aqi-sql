from .theme import ACCENT, POSITIVE, NEGATIVE, WARNING

MONTH_LABELS = {"01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr", "05": "May", "06": "Jun",
                "07": "Jul", "08": "Aug", "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"}
 
PERIOD_LABELS = {
    "early_winter(Dec)": "Early Winter (Dec)",
    "stubble_season(Oct-Nov)": "Stubble Season (Oct-Nov)",
    "late_winter(Jan-Feb)": "Late Winter (Jan-Feb)",
    "rest of the year(Mar-Sep)": "Rest of Year (Mar-Sep)",
}

# Minimal line-style icons (Feather-icon proportions), fill="none" so they
# inherit color via currentColor - no image assets, no icon library.
ICON_WARNING = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>'
ICON_LEAF = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/></svg>'
ICON_FLAME = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/></svg>'
ICON_TREND_DOWN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/></svg>'
 
 
def build(df06, df04, df03):
    worst = df06.sort_values("overall_avg_aqi", ascending=False).iloc[0]
    best = df06.sort_values("overall_avg_aqi", ascending=True).iloc[0]
    peak_period = df04.sort_values("pct_severe", ascending=False).iloc[0]
    biggest_drop = df03.dropna(subset=["yoy_change"]).sort_values("yoy_change").iloc[0]
 
    cards = [
        ("Worst Station", worst["station_name"], f"Avg AQI {worst['overall_avg_aqi']:.1f}", NEGATIVE, ICON_WARNING),
        ("Best Station", best["station_name"], f"Avg AQI {best['overall_avg_aqi']:.1f}", POSITIVE, ICON_LEAF),
        ("Peak Severity Period", PERIOD_LABELS.get(peak_period["period"], peak_period["period"]),
         f"{peak_period['pct_severe']:.1f}% severe days", WARNING, ICON_FLAME),
        ("Sharpest YoY Drop",
         f"{MONTH_LABELS.get(biggest_drop['month'], biggest_drop['month'])} {biggest_drop['year']}",
         f"{biggest_drop['yoy_change']:.1f} AQI points \u2014 likely COVID lockdown", ACCENT, ICON_TREND_DOWN),
    ]
 
    html_cards = ""
    for label, value, sub, color, icon in cards:
        html_cards += f"""
        <div class="kpi-card">
          <div class="kpi-icon" style="color:{color}">{icon}</div>
          <div class="kpi-label">{label}</div>
          <div class="kpi-value" style="color:{color}">{value}</div>
          <div class="kpi-sub">{sub}</div>
        </div>"""
    return html_cards