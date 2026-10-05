# BI exports (Tableau / Power BI)

Tidy CSVs for rebuilding this analysis in Tableau or Power BI. Generate them
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
Only days with at least 5 reporting stations (1,358 days).

| Column | Meaning |
|---|---|
| `date`, `year`, `month` | Calendar day |
| `season` | Same buckets as the analysis: Stubble season (Oct–Nov), Early winter (Dec), Late winter (Jan–Feb), Rest of year (Mar–Sep) |
| `is_lockdown` | 1 from 25 March 2020 (COVID lockdown); filter these out for "normal" comparisons |
| `n_stations` | Stations with an AQI reading that day |
| `aqi`, `aqi_category` | Mean AQI across stations, and its CPCB category |
| `pm25`, `pm10`, `no2`, `co` | Mean concentration across stations (µg/m³; CO in mg/m³) |
| `pm25_over_india_limit`, `pm25_over_who_limit` | 1 if PM2.5 > 60 / > 15 µg/m³ (24-hour limits), blank if no PM2.5 |
| `temp_mean_c`, `temp_min_c`, `wind_speed_kmh`, `wind_dir_deg`, `rain_mm`, `humidity_pct` | Daily weather, central Delhi (ERA5 via Open-Meteo) |
| `mixing_height_mean_m` | Mean boundary layer height: how deep the air pollution can spread into |

**`station_daily.csv`**: one row per station per day (36,107 rows):
`station_id`, `date`, `pm25`, `pm10`, `no2`, `so2`, `co`, `aqi`, `aqi_category`.
Join to `stations.csv` on `station_id`. Known sensor faults are already blanked
(see the Data section of the main README).

**`stations.csv`**: one row per station (37):

| Column | Meaning |
|---|---|
| `station_name`, `short_name` | Full name, and the name without ", Delhi - OPERATOR" |
| `operator` | DPCC, CPCB or IMD |
| `latitude`, `longitude` | For map visuals (set as geographic roles in Tableau) |
| `avg_aqi_2018_19`, `worst_overall_rank` | Mean AQI in the common 2018–19 window, and rank (1 = worst) |
| `pct_months_top5` | % of eligible months the station was among the month's 5 worst |
| `worst_month`, `worst_month_avg_aqi` | Its single worst month on record |
| `n_days_2018_19` | Days of data behind the average |

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
| `finding_diwali.csv` | 07 | Finding 6: AQI around each year's Diwali |
| `finding_persistent_hotspots.csv` | 16 | Finding 7: months in the top 5 worst, per station |
| `finding_alert_rules.csv` | 17 | Alert section: each rule's precision, recall and first-bad-day recall, train and test |
| `data_coverage.csv` | 08 | Caveats: % of days with data, per station per year |

## Suggested dashboard (4 pages)

1. **Overview**: KPI tiles from `city_daily` (% of days over the India limit;
   % of Dec days Very Poor+), a monthly PM2.5 line, and a station map from
   `stations` sized and coloured by `avg_aqi_2018_19`.
2. **Why winter is worst**: scatter from `finding_weather_by_month`
   (x = mixing height, y = PM2.5, label = month), next to a bar chart of
   `finding_weather_excess` with a reference line at 1.0.
3. **Local vs regional**: strip plot from `finding_station_fingerprint`
   (rows = pollutant, x = `index_vs_city_median`, one mark per station), and
   `finding_persistent_hotspots` as a bar chart.
4. **The lockdown test**: `finding_lockdown_did` (stacked bar: `pct_change_pre`
   + `lockdown_effect_pts`) with the `finding_lockdown_weather_adjusted`
   values as reference marks.

Use the CPCB category colours (Good `#3fb950`, Satisfactory `#7ee787`,
Moderate `#d29922`, Poor `#db6d28`, Very Poor `#f85149`, Severe `#8b1a1a`) so
it matches the web dashboard.
