def build(df06, df05, station_names):
    severe = df05[df05["computed_bucket"] == "Severe"].set_index("station_id")["pct_of_station_days"]
    d = df06.sort_values("overall_avg_aqi", ascending=False).reset_index(drop=True)
    d["severe_pct"] = d["station_id"].map(severe).fillna(0)
 
    rows = ""
    for i, r in d.iterrows():
        rows += f"""
        <tr>
          <td data-sort="{i + 1}">{i + 1}</td>
          <td data-sort="{r['station_name']}">{r['station_name']}</td>
          <td data-sort="{r['overall_avg_aqi']}">{r['overall_avg_aqi']:.1f}</td>
          <td data-sort="{r['severe_pct']}">{r['severe_pct']:.1f}%</td>
          <td data-sort="{r['worst_month']}">{r['worst_month']}</td>
          <td data-sort="{r['worst_month_avg_aqi']}">{r['worst_month_avg_aqi']:.1f}</td>
        </tr>"""
 
    return f"""
    <input type="text" id="station-search" class="search-box"
           placeholder="Search stations..." oninput="filterStations()">
    <table id="station-table">
      <thead>
        <tr>
          <th onclick="sortTable(0)">Rank</th>
          <th onclick="sortTable(1)">Station</th>
          <th onclick="sortTable(2)">Avg AQI</th>
          <th onclick="sortTable(3)">% Severe Days</th>
          <th onclick="sortTable(4)">Worst Month</th>
          <th onclick="sortTable(5)">Worst Month AQI</th>
        </tr>
      </thead>
      <tbody>{rows}
      </tbody>
    </table>
    """
 