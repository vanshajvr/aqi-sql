import pandas as pd
import plotly.graph_objects as go

from ..theme import ACCENT, ACCENT_2, GRID, TEXT, base_layout


def with_gaps(d, cols, max_days=14):
    """Insert an empty row wherever consecutive weekly points are far apart, so
    the line breaks at data gaps (e.g. Nov 2022 - Feb 2025) instead of bridging them."""
    d = d.sort_values("date").reset_index(drop=True)
    rows = []
    for i, r in d.iterrows():
        if i and (r["date"] - d.loc[i - 1, "date"]).days > max_days:
            rows.append({"date": r["date"] - pd.Timedelta(days=1), **{c: None for c in cols}})
        rows.append(r.to_dict())
    return pd.DataFrame(rows)


def build(df23, df21, station_names):
    """Weekly-sampled calendar 7- and 30-day rolling PM2.5 (query 23), one
    station at a time; stations ordered worst first by 2025-26 PM2.5."""
    order = (df21.sort_values("pm25_2025_26", ascending=False, na_position="last")["station_id"].tolist())
    data = df23.copy()
    data["date"] = pd.to_datetime(data["date"])

    fig = go.Figure()
    for i, sid in enumerate(order):
        d = with_gaps(data[data["station_id"] == sid], ["rolling_7day_pm25", "rolling_30day_pm25"])
        visible = i == 0
        fig.add_trace(go.Scatter(x=d["date"], y=d["rolling_7day_pm25"], mode="lines", connectgaps=False,
                                 line=dict(color=ACCENT, width=1.2), opacity=0.55, name="7-day average",
                                 visible=visible,
                                 hovertemplate="<b>%{x|%d %b %Y}</b><br>7-day: %{y:.0f} µg/m³<extra></extra>"))
        fig.add_trace(go.Scatter(x=d["date"], y=d["rolling_30day_pm25"], mode="lines", connectgaps=False,
                                 line=dict(color=ACCENT_2, width=2.2), name="30-day average",
                                 visible=visible,
                                 hovertemplate="<b>%{x|%d %b %Y}</b><br>30-day: %{y:.0f} µg/m³<extra></extra>"))

    buttons = []
    for i, sid in enumerate(order):
        vis = [False] * (len(order) * 2)
        vis[i * 2: i * 2 + 2] = [True, True]
        name = station_names.get(sid, sid).replace(", Delhi - ", " · ")
        buttons.append(dict(label=name, method="update", args=[{"visible": vis}]))

    fig.add_vrect(x0="2022-11-01", x1="2025-02-01", fillcolor="rgba(110,118,129,0.12)", line_width=0,
                  annotation_text="no data", annotation_position="top",
                  annotation_font=dict(color="#6e7681", size=11))
    fig.update_layout(
        xaxis_title="", yaxis_title="PM2.5 (µg/m³)",
        xaxis=dict(gridcolor=GRID, rangeslider=dict(visible=True, bgcolor="#21262d", thickness=0.06)),
        yaxis=dict(rangemode="tozero"),
        updatemenus=[dict(
            type="dropdown", direction="down", buttons=buttons,
            x=0, y=1.05, xanchor="left", yanchor="bottom",
            bgcolor="#21262d", bordercolor=GRID, font=dict(color=TEXT, size=12),
        )],
        legend=dict(orientation="h", y=1.05, yanchor="bottom", x=1, xanchor="right"),
    )
    return base_layout(fig, height=560, top_margin=70)
