import json

import pandas as pd


def build_comparison_payload(df23, df21, df06, station_names):
    """Weekly 30-day rolling PM2.5 (query 23) for every station, with the
    then/now PM2.5 (query 21) and worst month (query 06) for the stat cards.
    Stations are ordered worst first by 2025-26 PM2.5."""
    ids = df21.sort_values("pm25_2025_26", ascending=False, na_position="last")["station_id"].tolist()
    periods = df21.set_index("station_id")
    worst = df06.set_index("station_id")

    def num(v, nd=1):
        return None if pd.isna(v) else round(float(v), nd)

    payload = {}
    for sid in ids:
        d = df23[df23["station_id"] == sid].sort_values("date")
        dates, values, prev = [], [], None
        for date, v in zip(d["date"], d["rolling_30day_pm25"]):
            # break the line across gaps longer than two weeks
            if prev is not None and (pd.Timestamp(date) - pd.Timestamp(prev)).days > 14:
                dates.append(date)
                values.append(None)
            dates.append(date)
            values.append(num(v))
            prev = date
        p = periods.loc[sid]
        payload[sid] = {
            "name": station_names.get(sid, sid),
            "dates": dates,
            "rolling_30": values,
            "pm25_then": num(p["pm25_2018_19"], 0),
            "pm25_now": num(p["pm25_2025_26"], 0),
            "change_pct": num(p["change_pct"], 0),
            "worst_month": worst.loc[sid, "worst_month"] if sid in worst.index else None,
        }
    # This string is embedded directly inside a <script> tag in the template;
    # escape "</" so a station name can't terminate the script element early.
    return json.dumps(payload).replace("</", "<\\/"), ids


def build_station_options(ids, station_names, selected_id):
    options = ""
    for sid in ids:
        sel = " selected" if sid == selected_id else ""
        options += f'<option value="{sid}"{sel}>{station_names.get(sid, sid)}</option>'
    return options
