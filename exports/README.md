# BI exports (Tableau / Power BI)

Tidy CSVs for rebuilding this analysis in Tableau or Power BI. They cover
2015–2026 in PM2.5, from the same `readings_all` record the analysis uses
(Kaggle to mid-2020, then CPCB, with OpenAQ filling gaps). Generate them
from the repo root after building the database:

```bash
python3 fetch_data.py
python3 export_bi.py      # writes exports/*.csv
```

The CSVs are gitignored (they're regenerated from `data/aqi.db`); this guide
is tracked.

## Tables

### Base tables: for free exploration

**`city_daily.csv`**: one row per day, the city-wide picture plus weather.
Only days with at least 5 reporting stations (3,364 days, 2015–2026).

| Column | Meaning |
|---|---|
| `date`, `year`, `month` | Calendar day |
| `season` | Same buckets as the analysis: Stubble season (Oct–Nov), Early winter (Dec), Late winter (Jan–Feb), Rest of year (Mar–Sep) |
| `is_lockdown` | 1 for 25 March – 31 May 2020 (COVID lockdown); filter these out for "normal" comparisons |
| `n_stations` | Stations with a PM2.5 reading that day |
| `pm25`, `pm25_category` | Mean PM2.5 across stations, and its CPCB PM2.5 category (Good ≤ 30, Satisfactory ≤ 60, Moderate ≤ 90, Poor ≤ 120, Very Poor ≤ 250, Severe above) |
| `pm10`, `no2`, `co` | Mean concentration across stations (µg/m³; CO in mg/m³) |
| `pm25_over_india_limit`, `pm25_over_who_limit` | 1 if PM2.5 > 60 / > 15 µg/m³ (24-hour limits) |
| `temp_mean_c`, `temp_min_c`, `wind_speed_kmh`, `wind_dir_deg`, `rain_mm`, `humidity_pct` | Daily weather, central Delhi (ERA5 via Open-Meteo) |
| `mixing_height_mean_m` | Mean boundary layer height: how deep the air pollution can spread into (missing for January–June 2024 in the source) |

**`station_daily.csv`**: one row per station per day (105,853 rows, 2015–2026):
`station_id`, `date`, `pm25`, `pm10`, `no2`, `so2`, `co`, `o3`, `pm25_category`,
and `source` (Kaggle, CPCB or OpenAQ: where that day's PM2.5 came from).
Join to `stations.csv` on `station_id`. Known sensor faults are already blanked
(see the Data section of the main README).

**`stations.csv`**: one row per station (37):

| Column | Meaning |
|---|---|
| `station_name`, `short_name` | Full name, and the name without ", Delhi - OPERATOR" |
| `operator` | DPCC, CPCB or IMD |
| `latitude`, `longitude` | For map visuals (set as geographic roles in Tableau) |
| `avg_pm25`, `worst_overall_rank` | Mean PM2.5 on network days (2018–2026, days when at least 80% of stations reported), and rank (1 = worst) |
| `pct_months_top5` | % of eligible months the station was among the month's 5 worst |
| `worst_month`, `worst_month_avg_pm25` | Its single worst month on record (months with at least 15 days) |
| `n_days` | Network days behind the average |

### Finding tables: the exact numbers in FINDINGS.md

Each is the output of one query in [`queries/`](../queries/); the query file's
header explains the method.

| File | Query | Backs |
|---|---|---|
| `finding_season_days.csv` | 04 | Finding 1: share of Very Poor+ / Severe days by season |
| `finding_weather_by_month.csv` | 12 | Finding 1: PM2.5 vs mixing height, wind, rain by month |
| `finding_weather_excess.csv` | 13 | Finding 2: PM2.5 vs what the weather predicts, by half-month |
| `finding_health_limits.csv` | 11 | Finding 3: days above India / WHO PM2.5 limits, by year |
| `finding_station_fingerprint.csv` | 10 | Finding 4: each station vs the city median, per pollutant (long format) |
| `finding_lockdown_did.csv` | 09 | Finding 5: lockdown effect, difference-in-differences |
| `finding_lockdown_weather_adjusted.csv` | 15 | Finding 5: lockdown effect, weather-adjusted |
| `finding_diwali.csv` | 07 | Finding 6: PM2.5 around each year's Diwali |
| `finding_persistent_hotspots.csv` | 16 | Finding 7: months in the top 5 worst, per station |
| `finding_fires_and_wind.csv` | 18 | Finding 2: excess PM2.5 by previous-day crop fires and wind direction |
| `finding_alert_rules.csv` | 17 | Alert section: each rule's precision, recall and first-bad-day recall, train and test (official AQI, 2015–20) |
| `finding_alert_rules_future.csv` | 24 | Alert section: the pre-registered future test, 2020–22 and 2025–26 |
| `finding_alert_rules_gap.csv` | 26 | Alert section: the third unseen period, Nov 2022 – Jan 2025 |
| `finding_then_vs_now.csv` | 19 | Finding 8: the published five-winter comparison |
| `finding_then_vs_now_8_winters.csv` | 25 | Finding 8: eight winters, 2018–19 to 2025–26 |
| `finding_stubble_then_vs_now.csv` | 20 | Finding 8: fire counts and smoke-window PM2.5, by year |
| `finding_fires_daynight.csv` | 27 | Finding 8: night-pass share of fire detections, with the pre-registered verdict |
| `data_coverage.csv` | 08 | Caveats: % of days with data, per station per year |

## Power BI (in the browser, or Desktop)

Power BI in the browser makes a separate model from each uploaded CSV, and
separate models can't be joined. So upload **one workbook** instead:

```bash
python3 export_bi.py --excel     # writes exports/aqi_powerbi.xlsx (10 sheets)
```

It holds `station_daily`, `city_daily`, `stations`, a `dates` table (with
`season`, `winter` and `is_lockdown`) and six finding tables. Tables with a
`pm25_category` also have `pm25_category_order`, for sorting categories from
Good to Severe.

### 1. Load it

In app.powerbi.com, open **My workspace → Upload → Browse** and pick
`aqi_powerbi.xlsx`. Each sheet is an Excel table, which is what this upload
imports, and it doesn't need OneDrive.

The *Get data → Excel workbook* (Power Query) route needs OneDrive for
Business, including its "Upload file" option. Many student accounts don't
include it ("Your account does not have a license for SharePoint Online or
OneDrive for Business"). If neither route works, use Power BI Desktop on
Windows (a virtual machine on a Mac), where *Get data → Excel* reads the
local file. Menu names move around between Power BI updates.

### 2. Model it

Open the semantic model and choose **Open data model** (if it's missing,
turn on *Users can edit data models in the Power BI service* in the
workspace settings).

- **Relationships** (one-to-many, single direction):
  - `dates[date]` → `city_daily[date]`
  - `dates[date]` → `station_daily[date]`
  - `stations[station_id]` → `station_daily[station_id]`
  - `stations[station_id]` → `finding_station_fingerprint[station_id]`
- **Mark `dates` as the date table**, on `dates[date]`.
- **Sort by column:** `pm25_category` by `pm25_category_order` (in both
  tables), and `month_name` by `month`.
- **Measures:** copy them from [`measures.dax`](measures.dax), one *New
  measure* each, on the table named in its comment.

### 3. Build the report (4 pages)

1. **Overview**: cards for *Avg PM2.5*, *% days Very Poor or worse* and *%
   days over India limit*; a line chart of *Avg PM2.5* by `dates[year_month]`;
   a column chart of *% days Very Poor or worse* by `dates[season]`; and a
   year slicer.
2. **Why winter is worst**: a scatter from `finding_weather_by_month` (x =
   `mean_mixing_height_m`, y = `mean_pm25`, details = `month`), next to a
   column chart of `finding_weather_excess` (`half_month`, `excess_ratio`)
   with a constant line at 1.
3. **Stations**: a bar chart of *Network-day avg PM2.5* by
   `stations[short_name]` (top 15), and a map of `stations` (latitude,
   longitude, size = `avg_pm25`). Your organisation may switch map visuals
   off; the bar chart stands on its own. Add a **drill-through** page,
   *Station detail*, filtered on `short_name`: *Station avg PM2.5* by month,
   and a 100% stacked bar of station days by `pm25_category`.
4. **Then vs now**: columns from `finding_then_vs_now_8_winters`
   (`winter`, `pct_days_over_250` and `weather_adjusted_ratio`), plus
   `finding_fires_and_wind` as a clustered column chart (x = `fire_level`,
   legend = `wind`, filtered to `scenario = excluding Diwali`).

Use the CPCB category colours below so it matches the web dashboard.

### 4. Share it

- **Public link:** File → Embed report → **Publish to web**. If it's greyed
  out, your college's Power BI admin has switched it off.
- **Otherwise:** File → **Download this file** (.pbix) and commit it, export
  a PDF, and add screenshots to the main README. A short screen recording
  works well on LinkedIn.

Use the CPCB category colours (Good `#3fb950`, Satisfactory `#7ee787`,
Moderate `#d29922`, Poor `#db6d28`, Very Poor `#f85149`, Severe `#8b1a1a`) so
it matches the web dashboard.
