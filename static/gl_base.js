// Shared by the two MapLibre maps (station_map.js and live.js): the vector
// basemap recoloured to the site palette, the default Delhi view, and short
// station names. Loaded before both.
(function () {
  const BASEMAP_STYLE = "https://tiles.openfreemap.org/styles/positron";
  const DELHI = { center: [77.15, 28.63], zoom: 9.6 };

  // Site palette (static/style.css)
  const PALETTE = {
    land: "#10161e", residential: "#131a23", park: "#122019", water: "#0d2238",
    waterway: "#123050", building: "#18202a",
    roadMotorway: "#4a5563", roadMajor: "#36404c", roadMinor: "#252d37", casing: "#0d1117",
    rail: "#2b333d", boundary: "#4a5563",
    labelMajor: "#c9d1d9", labelMinor: "#8b949e", labelRoad: "#6e7681", halo: "#0d1117",
  };

  const AMBIGUOUS = new Set(["Pusa"]);
  function shortStationName(name) {
    const short = name.replace(/,\s*(New )?Delhi.*$/, "");
    const op = name.match(/-\s*(DPCC|CPCB|IMD)\s*$/);
    return AMBIGUOUS.has(short) && op ? `${short} (${op[1]})` : short;
  }

  // ---------------------------------------------------------------- basemap

  function setPaint(map, id, prop, value) {
    try { map.setPaintProperty(id, prop, value); } catch (e) { /* layer lacks this property */ }
  }

  function recolourBasemap(map) {
    for (const layer of map.getStyle().layers) {
      const id = layer.id;
      if (layer.type === "background") setPaint(map, id, "background-color", PALETTE.land);
      else if (id === "water") setPaint(map, id, "fill-color", PALETTE.water);
      else if (id === "waterway") setPaint(map, id, "line-color", PALETTE.waterway);
      else if (id === "park" || id === "landcover_wood") {
        setPaint(map, id, "fill-color", PALETTE.park);
        setPaint(map, id, "fill-opacity", 0.9);
      } else if (/ice|glacier/.test(id)) map.setLayoutProperty(id, "visibility", "none");
      else if (id === "landuse_residential") setPaint(map, id, "fill-color", PALETTE.residential);
      else if (id === "building") {
        setPaint(map, id, "fill-color", PALETTE.building);
        setPaint(map, id, "fill-outline-color", PALETTE.land);
      } else if (/^aeroway/.test(id)) {
        setPaint(map, id, layer.type === "fill" ? "fill-color" : "line-color", PALETTE.roadMinor);
      } else if (layer.type === "line" && /casing/.test(id)) {
        setPaint(map, id, "line-color", PALETTE.casing);
      } else if (layer.type === "line" && /motorway/.test(id)) {
        setPaint(map, id, "line-color", PALETTE.roadMotorway);
      } else if (layer.type === "line" && /major/.test(id)) {
        setPaint(map, id, "line-color", PALETTE.roadMajor);
      } else if (layer.type === "line" && /minor|pier/.test(id)) {
        setPaint(map, id, "line-color", PALETTE.roadMinor);
      } else if (layer.type === "line" && /path/.test(id)) {
        map.setLayoutProperty(id, "visibility", "none");
      } else if (layer.type === "line" && /railway/.test(id)) {
        setPaint(map, id, "line-color", PALETTE.rail);
      } else if (/^boundary/.test(id)) {
        setPaint(map, id, "line-color", PALETTE.boundary);
      } else if (layer.type === "symbol") {
        if (/shield|airport/.test(id)) {
          map.setLayoutProperty(id, "visibility", "none");
          continue;
        }
        const major = /city|town|state|country/.test(id);
        const road = /highway|waterway|water_name/.test(id);
        setPaint(map, id, "text-color", road ? PALETTE.labelRoad : major ? PALETTE.labelMajor : PALETTE.labelMinor);
        setPaint(map, id, "text-halo-color", PALETTE.halo);
        setPaint(map, id, "text-halo-width", 1.4);
        setPaint(map, id, "text-opacity", major ? 0.85 : 0.65);
      }
    }
  }


  window.GLBase = { BASEMAP_STYLE, DELHI, PALETTE, shortStationName, recolourBasemap };
})();
