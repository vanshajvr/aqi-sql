import json
import pandas as pd

def build_comparison_payload(df01, df05, df06, station_names, top_n=20):
    ids = df06.sort_values("overall_avg_aqi", ascending=False).head(top_n)["station_id"].tolist()
    severe = df05[df05["computed_bucket"] == "Severe"].set_index("station_id")["pct_of_station_days"]
    df06_idx = df06.set_index("station_id")
 
    payload = {}
    for sid in ids:
        d = df01[df01["station_id"] == sid].sort_values("date")
        row = df06_idx.loc[sid]
        payload[sid] = {
            "name": station_names.get(sid, sid),
            "dates": d["date"].tolist(),
            "rolling_30": [None if pd.isna(v) else round(float(v), 1) for v in d["rolling_30day_avg"]],
            "avg_aqi": round(float(row["overall_avg_aqi"]), 1),
            "severe_pct": round(float(severe.get(sid, 0)), 1),
            "worst_month": row["worst_month"],
        }
    return json.dumps(payload), ids
 
 
def build_station_options(ids, station_names, selected_id):
    options = ""
    for sid in ids:
        sel = " selected" if sid == selected_id else ""
        options += f'<option value="{sid}"{sel}>{station_names.get(sid, sid)}</option>'
    return options
 