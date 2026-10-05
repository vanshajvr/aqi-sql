"""
uncertainty.py

95% confidence intervals for the headline numbers in FINDINGS.md, written to
results/confidence_intervals.csv.

How each number is resampled depends on where its uncertainty comes from:

  * Daily city-wide figures (December share, stubble-season excess):
    WEEK-BLOCK bootstrap. Bad days come in spells, so resampling single days
    would treat a 5-day smog episode as 5 independent coin flips and make the
    interval far too narrow. Whole calendar weeks are resampled instead.
  * Station comparisons (lockdown effect, local vs regional spread):
    STATION bootstrap. The answer depends on which stations exist, so
    stations are resampled with replacement and the REAL query file in
    queries/ is re-run on each resampled network. The intervals therefore
    come from exactly the logic that produced the published numbers.
  * The alert result is a count (onsets warned out of onsets), so it gets a
    Wilson score interval, the standard interval for a proportion.

The point estimates are recomputed here and checked against the SQL
outputs, so the resampling code can't silently drift from the queries.

Run after fetch_data.py (takes a few minutes; fixed seed, so reproducible):
    python3 uncertainty.py
"""
import math
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
DB_PATH = ROOT / "data" / "aqi.db"
QUERIES_DIR = ROOT / "queries"
OUT_PATH = ROOT / "results" / "confidence_intervals.csv"

SEED = 20261005
N_WEEK_RESAMPLES = 2000
N_STATION_RESAMPLES = 500
LOCKDOWN_START = "2020-03-25"


def sql(name):
    return (QUERIES_DIR / name).read_text()


# ---------------------------------------------------------------- helpers

def percentile_ci(samples):
    lo, hi = np.nanpercentile(samples, [2.5, 97.5])
    return float(lo), float(hi)


def wilson_ci(successes, n, z=1.96):
    """Wilson score interval for a proportion (well behaved near 0% and 100%)."""
    if n == 0:
        return float("nan"), float("nan")
    p = successes / n
    denom = 1 + z ** 2 / n
    centre = (p + z ** 2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / denom
    return centre - half, centre + half


def week_bootstrap(df, stat, n, rng):
    """Resample whole calendar weeks of rows with replacement; apply stat."""
    groups = [g.index.to_numpy() for _, g in df.groupby("week")]
    out = np.empty(n)
    for i in range(n):
        picks = rng.integers(0, len(groups), len(groups))
        out[i] = stat(df.loc[np.concatenate([groups[j] for j in picks])])
    return out


# ---------------------------------------------------------------- city-day data

def city_days(conn):
    """One row per day: city-wide mean AQI / PM2.5 (>= 5 stations each), with weather.
    Same rules as 04 (AQI) and 13 (PM2.5)."""
    df = pd.read_sql_query(f"""
        WITH a AS (
            SELECT date, AVG(aqi) AS aqi FROM readings
            WHERE aqi IS NOT NULL GROUP BY date HAVING COUNT(*) >= 5
        ),
        p AS (
            SELECT date, AVG(pm25) AS pm25 FROM readings
            WHERE pm25 IS NOT NULL GROUP BY date HAVING COUNT(*) >= 5
        )
        SELECT w.date, a.aqi, p.pm25, w.mixing_height_mean_m, w.wind_speed_kmh, w.rain_mm
        FROM weather w
        LEFT JOIN a ON a.date = w.date
        LEFT JOIN p ON p.date = w.date
        WHERE w.date < '{LOCKDOWN_START}'
    """, conn)
    dates = pd.to_datetime(df["date"])
    df["month"] = dates.dt.month
    df["week"] = dates.dt.strftime("%G-%V")          # ISO year-week: the resampling block
    df["half_month"] = (dates.dt.strftime("%m") + np.where(dates.dt.day <= 15, "-1", "-2"))
    # Same buckets as 13_weather_adjusted_excess.sql
    df["mixing_bin"] = np.digitize(df["mixing_height_mean_m"], [250, 350, 450, 600, 800]) + 1
    df["wind_bin"] = np.digitize(df["wind_speed_kmh"], [5, 8, 12]) + 1
    return df


def share_very_poor(df, months):
    d = df[df["month"].isin(months) & df["aqi"].notna()]
    return 100.0 * (d["aqi"] > 300).mean()


def excess_ratio(df, half_month):
    """Mirror of 13_weather_adjusted_excess.sql for one half-month."""
    dry = df[(df["rain_mm"] < 1) & df["pm25"].notna()]
    base = dry[~dry["month"].isin([10, 11])].groupby(["mixing_bin", "wind_bin"])["pm25"]
    expected = base.mean()[base.size() >= 10].rename("expected")
    target = dry[dry["half_month"] == half_month].join(expected, on=["mixing_bin", "wind_bin"], how="inner")
    if target.empty:
        return float("nan")
    return target["pm25"].mean() / target["expected"].mean()


# ---------------------------------------------------------------- station bootstrap

def station_bootstrap(conn, query_file, extract, n, rng):
    """Resample stations with replacement, rebuild an in-memory DB, re-run the
    real query, and apply extract(result_df) -> dict of numbers."""
    readings = pd.read_sql_query("SELECT * FROM readings", conn)
    stations = pd.read_sql_query("SELECT * FROM stations", conn)
    weather = pd.read_sql_query("SELECT * FROM weather", conn)
    ids = stations["station_id"].to_numpy()
    by_station = {sid: g for sid, g in readings.groupby("station_id")}
    query = sql(query_file)

    results = []
    for _ in range(n):
        picks = rng.choice(ids, size=len(ids), replace=True)
        # duplicate picks become distinct stations (S_0, S_1, ...) so the query
        # counts them separately, as a bootstrap requires
        r_parts, s_parts = [], []
        for k, sid in enumerate(picks):
            new_id = f"{sid}_{k}"
            r_parts.append(by_station.get(sid, readings.iloc[0:0]).assign(station_id=new_id))
            s_parts.append(stations[stations["station_id"] == sid].assign(station_id=new_id))
        mem = sqlite3.connect(":memory:")
        pd.concat(r_parts).to_sql("readings", mem, index=False)
        pd.concat(s_parts).to_sql("stations", mem, index=False)
        weather.to_sql("weather", mem, index=False)
        results.append(extract(pd.read_sql_query(query, mem)))
        mem.close()
    return pd.DataFrame(results)


def lockdown_effects(df09):
    e = df09.set_index("pollutant")["lockdown_effect_pts"]
    return {"NO2": e.get("NO2"), "PM10": e.get("PM10"), "PM2.5": e.get("PM2.5")}


def spreads(df10):
    s = df10.groupby("pollutant")["pollutant_max_to_min"].first()
    return {"NO2": s.get("NO2"), "PM2.5": s.get("PM2.5")}


# ---------------------------------------------------------------- main

def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"{DB_PATH} not found. Run fetch_data.py first.")
    rng = np.random.default_rng(SEED)
    conn = sqlite3.connect(DB_PATH)
    rows = []

    def add(metric, estimate, ci, method, unit, note=""):
        rows.append({"metric": metric, "estimate": round(estimate, 3), "ci_low": round(ci[0], 3),
                     "ci_high": round(ci[1], 3), "unit": unit, "method": method, "note": note})

    # 1. December vs March-September share of Very Poor+ days (finding 1)
    days = city_days(conn)
    sql04 = pd.read_sql_query(sql("04_event_clustering.sql"), conn).set_index("period")
    for label, months, period in (("December", [12], "early_winter(Dec)"),
                                  ("March-September", list(range(3, 10)), "rest of the year(Mar-Sep)")):
        est = share_very_poor(days, months)
        assert round(est, 1) == sql04.loc[period, "pct_days_very_poor_plus"], "drifted from 04"
        boot = week_bootstrap(days, lambda d, m=months: share_very_poor(d, m), N_WEEK_RESAMPLES, rng)
        add(f"% of {label} days Very Poor or worse", est, percentile_ci(boot),
            "week-block bootstrap", "% of days")
    print("1/5 season shares done")

    # 2. Stubble-season excess over weather (finding 2)
    sql13 = pd.read_sql_query(sql("13_weather_adjusted_excess.sql"), conn).set_index("half_month")
    for half, label in (("10-2", "late October"), ("11-1", "early November"), ("12-1", "early December")):
        est = excess_ratio(days, half)
        assert round(est, 2) == sql13.loc[half, "excess_ratio"], "drifted from 13"
        boot = week_bootstrap(days, lambda d, h=half: excess_ratio(d, h), N_WEEK_RESAMPLES, rng)
        add(f"PM2.5 vs weather-predicted, {label}", est, percentile_ci(boot),
            "week-block bootstrap", "ratio (1 = weather explains it)")
    print("2/5 weather excess done")

    # 3. Lockdown effect by pollutant, 09's lower-bound method (finding 5)
    point = lockdown_effects(pd.read_sql_query(sql("09_lockdown_pollutants.sql"), conn))
    boot = station_bootstrap(conn, "09_lockdown_pollutants.sql", lockdown_effects, N_STATION_RESAMPLES, rng)
    for p in ("NO2", "PM10", "PM2.5"):
        add(f"Lockdown effect on {p} (lower bound)", point[p], percentile_ci(boot[p]),
            "station bootstrap, re-running 09", "percentage points")
    gap = boot["NO2"] - boot["PM2.5"]
    add("Lockdown: NO2 effect minus PM2.5 effect", point["NO2"] - point["PM2.5"], percentile_ci(gap),
        "station bootstrap, re-running 09", "percentage points",
        f"negative = NO2 fell more; {100 * (gap < 0).mean():.1f}% of resamples")
    print("3/5 lockdown done")

    # 4. Local vs regional spread (finding 4)
    point = spreads(pd.read_sql_query(sql("10_station_fingerprint.sql"), conn))
    boot = station_bootstrap(conn, "10_station_fingerprint.sql", spreads, N_STATION_RESAMPLES, rng)
    for p in ("NO2", "PM2.5"):
        add(f"Dirtiest / cleanest station, {p}", point[p], percentile_ci(boot[p]),
            "station bootstrap, re-running 10", "ratio",
            "max/min of a resample is biased low; compare the two, not the levels")
    add("Spread ratio, NO2 / PM2.5", point["NO2"] / point["PM2.5"],
        percentile_ci(boot["NO2"] / boot["PM2.5"]), "station bootstrap, re-running 10", "ratio",
        f"NO2 spread wider in {100 * (boot['NO2'] > boot['PM2.5']).mean():.1f}% of resamples")
    print("4/5 spread done")

    # 5. Alert rule, test years (alert section)
    sql17 = pd.read_sql_query(sql("17_alert_rules.sql"), conn)
    test = sql17[sql17["split"] == "test"].set_index("rule")
    for rule in ("E today > 200 AND weather", "B today > 300"):
        r = test.loc[rule]
        k, n = int(r["n_onsets_warned"]), int(r["n_onsets"])
        add(f"First bad days warned, rule {rule[0]} (2018-20)", 100 * k / n,
            tuple(100 * x for x in wilson_ci(k, n)), "Wilson score interval", "% of onsets",
            f"{k} of {n} onsets")
    print("5/5 alert done")
    conn.close()

    out = pd.DataFrame(rows)
    OUT_PATH.parent.mkdir(exist_ok=True)
    out.to_csv(OUT_PATH, index=False)
    print(f"\nWrote {OUT_PATH.relative_to(ROOT)}\n")
    print(out[["metric", "estimate", "ci_low", "ci_high", "note"]].to_string(index=False))


if __name__ == "__main__":
    main()
