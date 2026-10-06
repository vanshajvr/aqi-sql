"""
validate_backfill.py

Runs the pre-registered backfill tests in
analysis_plans/backfill_preregistration.md and writes the results, pass or
fail, to results/backfill_validation.csv.

Test A (Amendment 1): OpenAQ vs Kaggle on station-days present in both,
1 January - 30 June 2020.
  * daily PM2.5: Pearson r >= 0.95
  * daily PM10:  Pearson r >= 0.90
  * daily PM2.5: median absolute difference <= 15% of the Kaggle value
Information only (not a criterion): AQI computed with aqi.py from OpenAQ
concentrations vs the official Kaggle AQI, beside the baseline of the same
formula on Kaggle's own concentrations (MAE 28.5, 74.4% same category).

Test B: the US Embassy bridge, on two periods either side of the gap
(July 2020 - October 2022, February 2025 - latest), embassy vs the OpenAQ
city-wide daily PM2.5 (mean of >= 5 reporting stations), embassy cleaned by
the pre-registered rule (drop PM2.5 <= 0 or > 999, or < 16 observations).
  * daily log correlation >= 0.9 in each period
  * every winter month (Nov-Feb) with paired data: embassy x 1.04 within
    +/-15% of the city-wide monthly mean (means over the paired days)

Alert future test (analysis_plans/alert_future_preregistration.md): rule E
from query 17, translated to PM2.5, scored by query 24 on Jul 2020 - Oct 2022
and Feb 2025 - Oct 2026. Rule E passes only if, in BOTH periods, it stays
within the false-alert guardrail, warns >= 50% of first bad days, and beats
rules A and B on that. Written to results/alert_future_test.csv with Wilson
intervals.

Test C (analysis_plans/cpcb_gap_preregistration.md): the CPCB daily data
(readings_cpcb) vs OpenAQ on every station-day both have, with Test A's
criteria. Not blind (the agreement was seen before the plan was written); a
documented gate. Written to results/cpcb_validation.csv.

Eight-winter then vs now and the alert gap period
(analysis_plans/cpcb_gap_preregistration.md): the trend in query 25's
weather-adjusted ratio with a week-block bootstrap within each winter, the
Amendment 1 post-hoc checks and the 2025-26 source sensitivity
(results/then_vs_now_trend.csv); query 26's alert scores
(results/alert_gap_test.csv).

Fires day/night (analysis_plans/fires_daynight_preregistration.md): query
27's night share per season and pre-registered verdict, written to
results/fires_daynight_test.csv.

Usage (after fetch_data.py has built data/aqi.db with readings_openaq):
    python3 validate_backfill.py
"""
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from aqi import aqi, category

ROOT = Path(__file__).parent
DB_PATH = ROOT / "data" / "aqi.db"
OUT_PATH = ROOT / "results" / "backfill_validation.csv"


def test_a(conn):
    pairs = pd.read_sql_query("""
        SELECT k.station_id, k.date,
               k.pm25 AS k_pm25, o.pm25 AS o_pm25,
               k.pm10 AS k_pm10, o.pm10 AS o_pm10,
               k.aqi AS k_aqi,
               o.no2 AS o_no2, o.so2 AS o_so2, o.co AS o_co, o.o3 AS o_o3
        FROM readings k
        JOIN readings_openaq o ON o.station_id = k.station_id AND o.date = k.date
        WHERE k.date BETWEEN '2020-01-01' AND '2020-06-30'
    """, conn)
    rows = []

    def add(check, value, threshold, passed, n, kind="criterion"):
        rows.append({"test": "A", "check": check, "value": round(value, 3), "threshold": threshold,
                     "passed": passed, "n_station_days": n, "kind": kind})

    pm25 = pairs.dropna(subset=["k_pm25", "o_pm25"])
    r25 = np.corrcoef(pm25["k_pm25"], pm25["o_pm25"])[0, 1]
    add("PM2.5 Pearson r", r25, ">= 0.95", bool(r25 >= 0.95), len(pm25))

    pm10 = pairs.dropna(subset=["k_pm10", "o_pm10"])
    r10 = np.corrcoef(pm10["k_pm10"], pm10["o_pm10"])[0, 1]
    add("PM10 Pearson r", r10, ">= 0.90", bool(r10 >= 0.90), len(pm10))

    rel = ((pm25["o_pm25"] - pm25["k_pm25"]).abs() / pm25["k_pm25"]).median() * 100
    add("PM2.5 median absolute difference (%)", rel, "<= 15", bool(rel <= 15), len(pm25))

    # Information only: computed AQI from OpenAQ concentrations vs official AQI
    calc = pairs.apply(lambda r: aqi({"pm25": r.o_pm25, "pm10": r.o_pm10, "no2": r.o_no2,
                                      "so2": r.o_so2, "co": r.o_co, "o3": r.o_o3})[0], axis=1)
    ok = calc.notna() & pairs["k_aqi"].notna()
    mae = (calc[ok] - pairs.loc[ok, "k_aqi"]).abs().mean()
    same = (calc[ok].map(category) == pairs.loc[ok, "k_aqi"].map(category)).mean() * 100
    add("Computed AQI mean absolute error (baseline on Kaggle's own data: 28.5)", mae, "info", "", int(ok.sum()), "info")
    add("Computed AQI same category % (baseline: 74.4)", same, "info", "", int(ok.sum()), "info")
    return rows, pm25


def test_c(conn):
    pairs = pd.read_sql_query("""
        SELECT c.pm25 AS c_pm25, o.pm25 AS o_pm25, c.pm10 AS c_pm10, o.pm10 AS o_pm10
        FROM readings_cpcb c
        JOIN readings_openaq o ON o.station_id = c.station_id AND o.date = c.date
    """, conn)
    rows = []

    def add(check, value, threshold, passed, n):
        rows.append({"test": "C", "check": check, "value": round(value, 3), "threshold": threshold,
                     "passed": passed, "n_station_days": n, "kind": "criterion"})

    pm25 = pairs.dropna(subset=["c_pm25", "o_pm25"])
    r25 = np.corrcoef(pm25["c_pm25"], pm25["o_pm25"])[0, 1]
    add("PM2.5 Pearson r", r25, ">= 0.95", bool(r25 >= 0.95), len(pm25))
    pm10 = pairs.dropna(subset=["c_pm10", "o_pm10"])
    r10 = np.corrcoef(pm10["c_pm10"], pm10["o_pm10"])[0, 1]
    add("PM10 Pearson r", r10, ">= 0.90", bool(r10 >= 0.90), len(pm10))
    rel = ((pm25["c_pm25"] - pm25["o_pm25"]).abs() / pm25["o_pm25"]).median() * 100
    add("PM2.5 median absolute difference (%)", rel, "<= 15", bool(rel <= 15), len(pm25))
    out = pd.DataFrame(rows)
    out.to_csv(OUT_PATH.with_name("cpcb_validation.csv"), index=False)
    return out


WINTER_SCALE = 1.04       # pre-registered: city / embassy winter median, Oct 2018 - Jun 2020
PERIODS = {"Jul 2020 - Oct 2022": ("2020-07-01", "2022-10-31"),
           "Feb 2025 - latest": ("2025-02-01", "2099-12-31")}


def test_b(conn):
    paired = pd.read_sql_query("""
        WITH city AS (
            SELECT date, AVG(pm25) AS city_pm25
            FROM readings_openaq
            WHERE pm25 IS NOT NULL
            GROUP BY date
            HAVING COUNT(*) >= 5
        )
        SELECT c.date, c.city_pm25, e.pm25 AS emb_pm25
        FROM city c
        JOIN embassy_pm25 e ON e.date = c.date
        WHERE e.pm25 > 0 AND e.pm25 <= 999 AND e.observed_count >= 16
    """, conn)
    rows, months = [], []
    for label, (start, end) in PERIODS.items():
        p = paired[(paired["date"] >= start) & (paired["date"] <= end)].copy()
        r = np.corrcoef(np.log(p["city_pm25"]), np.log(p["emb_pm25"]))[0, 1]
        rows.append({"test": "B", "check": f"Daily log correlation, {label}", "value": round(r, 3),
                     "threshold": ">= 0.9", "passed": bool(r >= 0.9), "n_station_days": len(p),
                     "kind": "criterion"})
        p["month"] = p["date"].str[:7]
        winter = p[p["date"].str[5:7].isin(["11", "12", "01", "02"])]
        for month, g in winter.groupby("month"):
            pct = 100 * (g["emb_pm25"].mean() * WINTER_SCALE - g["city_pm25"].mean()) / g["city_pm25"].mean()
            months.append({"period": label, "month": month, "paired_days": len(g),
                           "city_pm25": round(g["city_pm25"].mean(), 1),
                           "embassy_scaled": round(g["emb_pm25"].mean() * WINTER_SCALE, 1),
                           "pct_diff": round(pct, 1), "within_15": bool(abs(pct) <= 15)})
    m = pd.DataFrame(months)
    rows.append({"test": "B", "check": "Winter months within +/-15% (all required)",
                 "value": int(m["within_15"].sum()), "threshold": f"all {len(m)}",
                 "passed": bool(m["within_15"].all()), "n_station_days": int(m["paired_days"].sum()),
                 "kind": "criterion"})
    return rows, m


def alert_future(conn, query="24_alert_rules_future.sql", out_name="alert_future_test.csv"):
    from uncertainty import wilson_ci
    q = (ROOT / "queries" / query).read_text()
    df = pd.read_sql_query(q, conn)
    rows = []
    for r in df[df["rule"].str[0].isin(["A", "B", "E"])].itertuples():
        lo, hi = wilson_ci(int(r.n_onsets_warned), int(r.n_onsets))
        rows.append({"split": r.split, "rule": r.rule, "onsets_warned": int(r.n_onsets_warned),
                     "onsets": int(r.n_onsets), "onset_recall": r.onset_recall,
                     "onset_recall_ci_low": round(lo, 3), "onset_recall_ci_high": round(hi, 3),
                     "false_alerts_per_30d": r.false_alerts_per_30d,
                     "rule_e_pass": None if pd.isna(r.rule_e_pass) else bool(r.rule_e_pass)})
    out = pd.DataFrame(rows)
    out.to_csv(OUT_PATH.with_name(out_name), index=False)
    future = out[out["split"].str.startswith("future") & out["rule"].str.startswith("E")]
    return out, bool(future["rule_e_pass"].all())


TREND_SEED = 42
TREND_RESAMPLES = 2000


def slope(winters):
    """OLS slope of weather-adjusted ratio on winter start year."""
    from uncertainty import adjusted_ratio
    pts = [(y, adjusted_ratio(g)) for y, g in winters.groupby("season_start")]
    x, y = np.array(pts, dtype=float).T
    return float(np.polyfit(x, y, 1)[0])


def winter_bootstrap(days, stat, n, rng):
    """Week-block bootstrap within each winter: every winter keeps its own
    number of weeks, resampled from its own weeks."""
    blocks = {y: [g.index.to_numpy() for _, g in w.groupby("week")] for y, w in days.groupby("season_start")}
    out = np.empty(n)
    for i in range(n):
        idx = [b[j] for b in blocks.values() for j in rng.integers(0, len(b), len(b))]
        out[i] = stat(days.loc[np.concatenate(idx)])
    return out


def then_vs_now_trend(conn):
    """Pre-registered eight-winter trend (cpcb_gap_preregistration.md, 1) plus
    Amendment 1's post-hoc checks and the 2025-26 source sensitivity."""
    from uncertainty import query_rows
    days = query_rows(conn, "25_then_vs_now_8_winters.sql",
                      "SELECT date, month, season_start, pm25, rain_mm, expected_pm25 FROM winter")
    rng = np.random.default_rng(TREND_SEED)
    rows = []

    def verdict(lo, hi):
        return "improving" if hi < 0 else "worsening" if lo > 0 else "no clear trend"

    variants = [("primary (pre-registered)", "8 winters, Nov-Feb", days),
                ("post hoc", "8 winters, Nov-Dec only", days[days["month"].isin([11, 12])]),
                ("post hoc", "7 winters, without 2023-24", days[days["season_start"] != 2023])]
    for kind, label, d in variants:
        d = d.reset_index(drop=True)
        est = slope(d)
        lo, hi = np.percentile(winter_bootstrap(d, slope, TREND_RESAMPLES, rng), [2.5, 97.5])
        rows.append({"analysis": f"Trend in weather-adjusted ratio: {label}", "kind": kind,
                     "value": round(est, 4), "ci_low": round(lo, 4), "ci_high": round(hi, 4),
                     "unit": "ratio per winter", "result": verdict(lo, hi),
                     "n_winters": d["season_start"].nunique(), "n_days": len(d)})

    # Secondary: is 2025-26 the lowest weather-adjusted ratio of the eight?
    t25 = pd.read_sql_query((ROOT / "queries" / "25_then_vs_now_8_winters.sql").read_text(), conn)
    lowest = t25.loc[t25["weather_adjusted_ratio"].idxmin(), "winter"]
    rows.append({"analysis": "Lowest weather-adjusted ratio of the eight winters", "kind": "secondary",
                 "value": float(t25["weather_adjusted_ratio"].min()), "result": f"{lowest} "
                 f"({'is' if lowest == '2025-26' else 'not'} 2025-26)", "n_winters": len(t25)})

    # Post hoc (Amendment 1): 2023-24 on all its days, no weather needed
    full = query_rows(conn, "25_then_vs_now_8_winters.sql", """
        SELECT date, pm25 FROM city_daily
        WHERE month IN (11, 12, 1, 2) AND season_start = 2023""")
    for label, value in (("2023-24 mean PM2.5, all days", full["pm25"].mean()),
                         ("2023-24 % of days over 120, all days", 100 * (full["pm25"] > 120).mean()),
                         ("2023-24 % of days over 250, all days", 100 * (full["pm25"] > 250).mean())):
        rows.append({"analysis": label, "kind": "post hoc", "value": round(value, 1),
                     "n_days": len(full)})

    # Sensitivity: 2025-26 on CPCB (25) vs OpenAQ (19), within 5% on mean PM2.5
    t19 = pd.read_sql_query((ROOT / "queries" / "19_then_vs_now.sql").read_text(), conn).set_index("winter")
    cp, oa = t25.set_index("winter").loc["2025-26", "mean_pm25"], t19.loc["2025-26", "mean_pm25"]
    diff = 100 * (cp - oa) / oa
    rows.append({"analysis": "2025-26 mean PM2.5, CPCB vs OpenAQ (% difference)", "kind": "sensitivity",
                 "value": round(diff, 1), "result": "agree (within 5%)" if abs(diff) <= 5 else "differ (over 5%)"})
    out = pd.DataFrame(rows)
    out.to_csv(OUT_PATH.with_name("then_vs_now_trend.csv"), index=False)
    return out, t25


def main():
    conn = sqlite3.connect(DB_PATH)
    rows, pm25 = test_a(conn)
    rows_b, months_b = test_b(conn)
    conn.close()
    print(months_b.to_string(index=False), "\n")
    months_b.to_csv(OUT_PATH.with_name("backfill_bridge_months.csv"), index=False)
    rows += rows_b
    out = pd.DataFrame(rows)
    OUT_PATH.parent.mkdir(exist_ok=True)
    out.to_csv(OUT_PATH, index=False)
    print(out.to_string(index=False))
    for test in ("A", "B"):
        criteria = out[(out["kind"] == "criterion") & (out["test"] == test)]
        verdict = "PASS" if criteria["passed"].all() else "FAIL"
        print(f"Test {test}: {verdict}")

    conn = sqlite3.connect(DB_PATH)
    test_c_rows = test_c(conn)
    conn.close()
    print("\n" + test_c_rows.to_string(index=False))
    print(f"Test C (CPCB data): {'PASS' if test_c_rows['passed'].all() else 'FAIL'}")

    conn = sqlite3.connect(DB_PATH)
    alerts, passed = alert_future(conn)
    print("\n" + alerts.to_string(index=False))
    print(f"Alert future test (rule E): {'PASS' if passed else 'FAIL'}")

    gap, _ = alert_future(conn, "26_alert_rules_gap.sql", "alert_gap_test.csv")
    print("\n" + gap.to_string(index=False))
    e = gap[(gap["split"] == "future 2022-25") & gap["rule"].str.startswith("E")]
    print(f"Alert rule E on Nov 2022 - Jan 2025: {'PASS' if e['rule_e_pass'].all() else 'FAIL'}")

    trend, t25 = then_vs_now_trend(conn)
    # Day/night fire test (analysis_plans/fires_daynight_preregistration.md)
    dn = pd.read_sql_query((ROOT / "queries" / "27_fires_daynight.sql").read_text(), conn)
    dn.to_csv(OUT_PATH.with_name("fires_daynight_test.csv"), index=False)
    conn.close()
    print("\n" + dn.to_string(index=False))
    print(f"Fires day/night test: {dn['verdict'].iloc[0]}")
    print("\n" + t25.to_string(index=False))
    print("\n" + trend.to_string(index=False))


if __name__ == "__main__":
    main()
