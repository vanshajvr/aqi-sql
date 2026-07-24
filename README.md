# aqi-sql

Does Delhi's air actually get 7x worse in winter and can SQL alone prove it?

Real CPCB station data, 2015–2020. No pandas magic, no black-box charts,
just window functions, CTEs, and date logic doing the analytical heavy
lifting, with an interactive dashboard on top.

## Data

37 Delhi monitoring stations · ~36,000 daily readings · 2015–2020
Source: [CPCB via Kaggle](https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india) (real government data, not synthetic).

## Setup

```bash
# 1. Download the dataset, unzip into data/raw/ (need stations.csv + station_day.csv)
pip install -r requirements.txt
python3 fetch_data.py        # builds data/aqi.db
python3 build_dashboard.py   # builds dashboard.html
```
Open `dashboard.html` in your browser.

## The six queries

| # | File | SQL techniques | Question answered |
|---|---|---|---|
| 1 | `01_rolling_average.sql` | Window functions (`AVG() OVER ... ROWS BETWEEN`) | What's the 7-day/30-day AQI trend per station? |
| 2 | `02_station_ranking.sql` | CTEs, `RANK()`/`DENSE_RANK()` | Which stations are worst each month? |
| 3 | `03_yoy_comparison.sql` | Date functions, `LAG()` window function | Is the same month better or worse year over year? |
| 4 | `04_event_clustering.sql` | `CASE` bucketing, CTEs | Do severe-AQI days cluster around Diwali/stubble season? |
| 5 | `05_severity_breakdown.sql` | `CASE` bucketing, window functions | What % of days per station fall into each CPCB AQI category? |
| 6 | `06_pipeline_summary.sql` | Layered CTEs, joins, `ROW_NUMBER()` | Combined view: worst stations, worst month, year-over-year trend |

## What the data actually says

- **Anand Vihar is Delhi's worst station, no contest** — avg AQI 355.8, one December reading averaging 614.5, zero "Good" days in 5.5 years.
- **Winter is ~7x worse than the rest of the year.** 82% of December days hit "Severe" vs. 11.3% March–September. December beats even peak stubble-burning season — winter inversion trapping smoke seems to matter more than the burning itself.
- **April 2020 is the sharpest one-month drop in the dataset** (−105 AQI points) — the COVID lockdown, not a real trend.
- **Geography is destiny.** Industrial/traffic belt (Anand Vihar, Wazirpur, Mundka) vs. green IMD stations (Aya Nagar, Pusa) — the gap holds every single year.

## Dashboard

An interactive, tabbed dashboard built with Plotly:

- **Overview**: KPI cards (worst/best station, peak severity period, sharpest YoY drop) + worst-stations chart with a Top 10/15/20/All toggle
- **Trends**: city-wide AQI over time with a range slider, and the winter-vs-rest-of-year severity comparison
- **Station Explorer**: rolling 7-day/30-day average per station (dropdown-selectable) + severity category breakdown, worst/best toggle
- **Compare Stations**: pick any two stations and overlay their rolling averages, with side-by-side stats
- **Full Data**: sortable, searchable table of all 37 stations

## Structure
```
fetch_data.py # Kaggle CSVs → data/aqi.db
build_dashboard.py # orchestrator
queries/ # the six .sql files
dashboard/ # chart builders, KPIs, table (Python package)
templates/, static/ # HTML skeleton + CSS/JS
```
## Note on data quality
CPCB monitoring data has real-world gaps (missing dates, occasional
partial months) — these are preserved as-is rather than artificially
smoothed, since that's the honest state of the underlying government data.

## Data source
CPCB via [Kaggle](https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india). 
