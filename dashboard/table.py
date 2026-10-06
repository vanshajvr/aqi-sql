from html import escape

import pandas as pd


def build(df06, df21, station_names):
    """All stations: PM2.5 rank on network days (2018-26), PM2.5 then and now,
    and the raw change. Missing values sort last (data-sort=-1e9 / text)."""
    periods = df21.set_index("station_id")
    d = df06.sort_values("avg_pm25", ascending=False).reset_index(drop=True)

    def cell(v, fmt, missing="&ndash;"):
        if pd.isna(v):
            return f'<td data-sort="-1000000000">{missing}</td>'
        return f'<td data-sort="{v}">{fmt(v)}</td>'

    rows = ""
    for i, r in d.iterrows():
        name = escape(str(r["station_name"]), quote=True)
        p = periods.loc[r["station_id"]] if r["station_id"] in periods.index else {}
        change = p.get("change_pct") if len(p) else None
        if not pd.isna(change):
            change = round(change)          # colour by the shown value: +0.1% is "0%", not "worse"
        change_cls = "" if pd.isna(change) else (" class=\"better\"" if change < 0 else " class=\"worse\"" if change > 0 else "")
        # "2018-12" -> "201812" so the numeric sort keeps year *and* month
        worst_month = str(r["worst_month"])
        rows += f"""
        <tr>
          <td data-sort="{i + 1}">{i + 1}</td>
          <td data-sort="{name}">{name}</td>
          {cell(r['avg_pm25'], lambda v: f'{v:.0f}')}
          {cell(p.get('pm25_2018_19') if len(p) else None, lambda v: f'{v:.0f}')}
          {cell(p.get('pm25_2025_26') if len(p) else None, lambda v: f'{v:.0f}')}
          {cell(change, lambda v: f'{v:+.0f}%' if v else '0%').replace('<td', f'<td{change_cls}', 1)}
          <td data-sort="{worst_month.replace('-', '')}">{worst_month}</td>
        </tr>"""

    return f"""
    <input type="text" id="station-search" class="search-box"
           placeholder="Search stations..." oninput="filterStations()">
    <div class="table-scroll">
    <table id="station-table">
      <thead>
        <tr>
          <th onclick="sortTable(0)">Rank</th>
          <th onclick="sortTable(1)">Station</th>
          <th onclick="sortTable(2)">PM2.5 2018&ndash;26</th>
          <th onclick="sortTable(3)">PM2.5 2018&ndash;19</th>
          <th onclick="sortTable(4)">PM2.5 2025&ndash;26</th>
          <th onclick="sortTable(5)">Change</th>
          <th onclick="sortTable(6)">Worst month</th>
        </tr>
      </thead>
      <tbody>{rows}
      </tbody>
    </table>
    </div>
    """
