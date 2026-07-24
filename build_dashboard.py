from pathlib import Path

from dashboard.data import load_all
from dashboard.kpi import build as build_kpi_cards
from dashboard.table import build as build_station_table
from dashboard.theme import to_div
from dashboard.charts import (
    worst_stations,
    yoy_trends,
    event_clustering,
    rolling_average,
    severity_breakdown,
    comparison,
)

ROOT = Path(__file__).parent
DB_PATH = ROOT / "data" / "aqi.db"
QUERIES_DIR = ROOT / "queries"
TEMPLATE_PATH = ROOT / "templates" / "dashboard.html"
OUTPUT_PATH = ROOT / "dashboard.html"


def main():
    data = load_all(DB_PATH, QUERIES_DIR)
    df01, df03, df04, df05, df06 = data["df01"], data["df03"], data["df04"], data["df05"], data["df06"]
    station_names = data["station_names"]

    compare_json, compare_ids = comparison.build_comparison_payload(df01, df05, df06, station_names)
    options_a = comparison.build_station_options(compare_ids, station_names, compare_ids[0])
    options_b = comparison.build_station_options(compare_ids, station_names, compare_ids[1])

    template = TEMPLATE_PATH.read_text()
    html = template.format(
        kpi_cards=build_kpi_cards(df06, df04, df03),
        worst_stations=to_div(worst_stations.build(df06)),
        yoy=to_div(yoy_trends.build(df03)),
        event=to_div(event_clustering.build(df04)),
        rolling=to_div(rolling_average.build(df01, df06, station_names)),
        severity=to_div(severity_breakdown.build(df05, df06, station_names)),
        table=build_station_table(df06, df05, station_names),
        compare_data_json=compare_json,
        station_options_a=options_a,
        station_options_b=options_b
    )

    OUTPUT_PATH.write_text(html)
    print(f"Dashboard written to {OUTPUT_PATH}")
    print(f"Open it directly in your browser: file://{OUTPUT_PATH.resolve()}")


if __name__ == "__main__":
    main()